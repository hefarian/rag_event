"""Application FastAPI pour le système RAG Puls-Events.

QU'EST-CE QUE RAG?
RAG = "Retrieval Augmented Generation" (Génération Augmentée par Récupération)
Concept: Combiner la recherche d'information avec la génération de texte par IA

Flux RAG simplifié:
1. Utilisateur pose une question
2. FAISS recherche les événements les plus similaires (Retrieval = étape 1)
3. Mistral (IA) génère une réponse en se basant sur ces événements (Generation = étape 2)
4. API retourne la réponse augmentée d'informations réelles

ENDPOINTS DISPONIBLES:
- GET  /                : Statut de l'API (pour vérifier qu'elle répond)
- GET  /health         : Vérification détaillée de l'état
- POST /ask             : ⭐ Poser une question au système RAG
- POST /rebuild         : Reconstruire l'index FAISS (si données changent)
- POST /search          : Recherche similaire simple dans l'index
- GET  /docs            : Documentation interactive Swagger
- POST /chat/start      : Démarrer un chat conversationnel
- POST /chat/message    : Envoyer un message dans le chat

DÉPLOIEMENT:
- En local: python -m uvicorn api.app:app --reload
- En Docker: docker-compose up (recommandé)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Tuple
import subprocess
import threading
import pathlib
import json
import logging
import os
import re
from datetime import datetime, timedelta

# Import local Mistral wrapper
try:
    from .mistral_wrapper import call_mistral
except ImportError:
    from mistral_wrapper import call_mistral

# Import local conversation storage
try:
    from .conversation_storage import (
        create_conversation, add_message, get_conversation,
        get_conversation_messages, list_conversations, delete_conversation
    )
except ImportError:
    from conversation_storage import (
        create_conversation, add_message, get_conversation,
        get_conversation_messages, list_conversations, delete_conversation
    )

try:
    import faiss
    import numpy as np
except ImportError:
    faiss = None
    np = None

try:
    from langchain.vectorstores import FAISS as LangchainFAISS
    from langchain.embeddings import HuggingFaceEmbeddings
except ImportError:
    LangchainFAISS = None

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Créer l'application FastAPI avec documentation Swagger automatique
app = FastAPI(
    title="Puls-Events RAG API",
    description="Système RAG pour recherche et génération sur événements OpenAgenda",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# Ajouter CORS pour l'accès depuis Streamlit et autres clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MODÈLES PYDANTIC
# ============================================================================

class Query(BaseModel):
    question: str
    top_k: Optional[int] = 3
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "Quels concerts jazz à Paris cette semaine ?",
                "top_k": 3
            }
        }


class SearchResult(BaseModel):
    score: float
    content: str
    metadata: dict


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[SearchResult]
    timestamp: str


class StatusResponse(BaseModel):
    status: str
    index_exists: bool
    message: str


class ChatMessage(BaseModel):
    role: str  # "user" ou "assistant"
    content: str
    timestamp: Optional[str] = None


class ChatStartRequest(BaseModel):
    """Démarre une nouvelle conversation"""
    initial_message: Optional[str] = None


class ChatStartResponse(BaseModel):
    """Réponse quand une conversation est créée"""
    conversation_id: str
    created_at: str
    message: str


class ChatMessageRequest(BaseModel):
    """Envoie un message dans une conversation"""
    conversation_id: str
    message: str


class ChatMessageResponse(BaseModel):
    """Réponse à un message de chat"""
    conversation_id: str
    user_message: str
    assistant_response: str
    timestamp: str
    messages_count: int  # Total de messages dans la conversation


# ============================================================================
# CONSTANTES
# ============================================================================

INDEX_PATH = pathlib.Path("vectors/index.faiss")
METADATA_PATH = pathlib.Path("vectors/metadata.jsonl")
REBUILD_LOCK = threading.Lock()
REBUILD_IN_PROGRESS = False

# Cache pour l'index FAISS et les métadonnées
_faiss_index = None
_metadata_list = None
_embedding_model = None


# ============================================================================
# UTILITAIRES
# ============================================================================

def index_exists() -> bool:
    """Vérifie que l'index FAISS existe."""
    return INDEX_PATH.exists() and METADATA_PATH.exists()


def load_metadata() -> list:
    """Charge les métadonnées associées à l'index FAISS."""
    if not METADATA_PATH.exists():
        return []
    
    metadata = []
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    metadata.append(json.loads(line))
    except Exception as e:
        logger.error(f"Erreur lors du chargement des métadonnées: {e}")
    
    return metadata


def get_embedding_model():
    """Retourne le modèle d'embedding (singleton avec cache).
    Non utilisé directement — les embeddings passent par embed_text() via Mistral API.
    Conservé pour compatibilité.
    """
    return None


def get_faiss_index():
    """Charge l'index FAISS depuis le disque (avec cache)."""
    global _faiss_index
    global _metadata_list
    
    if _faiss_index is not None:
        return _faiss_index, _metadata_list
    
    if not index_exists():
        return None, None
    
    try:
        logger.info("Chargement de l'index FAISS...")
        _faiss_index = faiss.read_index(str(INDEX_PATH))
        _metadata_list = load_metadata()
        logger.info(f"✓ Index chargé: {_faiss_index.ntotal} vecteurs")
        return _faiss_index, _metadata_list
    except Exception as e:
        logger.error(f"Erreur lors du chargement de l'index: {e}")
        return None, None


# Dimension des embeddings Mistral (modèle mistral-embed)
EMBEDDING_DIM = 1024


def embed_text(text: str) -> np.ndarray:
    """Vectorise un texte via l'API Mistral embeddings (1024D)."""
    import requests as _requests
    try:
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            logger.error("MISTRAL_API_KEY non définie — embeddings impossibles")
            return np.zeros((1, EMBEDDING_DIM), dtype="float32")

        resp = _requests.post(
            "https://api.mistral.ai/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": "mistral-embed", "input": [text]},
            timeout=15,
        )

        if resp.status_code != 200:
            logger.error(f"Mistral embeddings {resp.status_code}: {resp.text[:200]}")
            return np.zeros((1, EMBEDDING_DIM), dtype="float32")

        embedding = resp.json()["data"][0]["embedding"]
        return np.array([embedding], dtype="float32")
    except Exception as e:
        logger.error(f"Erreur embedding Mistral: {e}")
        return np.zeros((1, EMBEDDING_DIM), dtype="float32")


def is_event_valid(metadata: dict) -> bool:
    """Vérifie que l'événement est valide (récent - moins de 1 an)."""
    try:
        from datetime import timedelta
        
        date_str = metadata.get("date", "")
        if not date_str:
            logger.debug("Pas de date trouvée, événement inclus par défaut")
            return True  # Si pas de date, inclure de toute façon
        
        # Parser les dates ISO 8601 (peut avoir timezone: 2026-04-05T20:00:00+02:00)
        try:
            # Supprimer la timezone si présente (prendre juste la date/heure locale)
            if 'T' in date_str:
                date_part = date_str.split('+')[0].split('Z')[0]
            else:
                date_part = date_str.split('+')[0]
            
            event_date = datetime.fromisoformat(date_part)
        except Exception as parse_err:
            logger.debug(f"Impossible de parser la date '{date_str}': {parse_err}, événement inclus")
            return True  # Si parse fail, inclure pour ne pas perdre de résultats
        
        now = datetime.now()
        max_age = timedelta(days=365)  # Fenêtre: - 1 an à +infini
        min_date = now - max_age
        
        is_valid = event_date >= min_date
        
        if not is_valid:
            logger.debug(f"Événement trop vieux filtré: {metadata.get('title', 'N/A')} ({date_str}, avant {min_date})")
        
        return is_valid
    
    except Exception as e:
        logger.debug(f"Erreur validation date: {e}, événement inclus")
        return True  # En cas d'erreur, inclure


def parse_temporal_query(question: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    DEPRECATED - Gardé pour compatibilité backwards
    Utiliser expand_temporal_query() à la place
    """
    return None, None


def expand_temporal_query(question: str) -> str:
    """
    Query Expansion: Reformule la question via Mistral pour enrichir le contexte temporel.
    
    Exemple:
    - Input: "demain ?"
    - Output: "Événements le 12 avril 2026"
    
    Cela permet au LLM de mieux comprendre les termes temporels relatifs
    et enrichit la recherche FAISS avec du contexte.
    """
    try:
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            logger.debug("Pas de MISTRAL_API_KEY, retour de la question originale")
            return question
        
        from mistralai.client import MistralClient
        from mistralai.models.chat_message import ChatMessage
        client = MistralClient(api_key=api_key)
        
        current_date = datetime.now().strftime("%d %B %Y à %H:%M")
        
        prompt = f"""Tu es un moteur de recherche d'événements culturels français.
La date/heure actuelle est le {current_date}.

Reformule cette question pour enrichir la recherche avec du contexte temporel.
Ajoute des termes explicites sur les dates si la question contient "demain", "cette semaine", "ce soir", etc.

Retourne UNIQUEMENT la question reformulée, concise et enrichie. Pas d'explications.

Question originale: "{question}"

Question reformulée:"""
        
        message = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        expanded = message.choices[0].message.content.strip()
        logger.info(f"Query Expansion: '{question}' -> '{expanded}'")
        return expanded
    
    except Exception as e:
        logger.warning(f"Query expansion échouée: {e}, retour de la question originale")
        return question


def parse_temporal_intent(question: str) -> Optional[Tuple[datetime, datetime]]:
    """
    Parse simple pour détecter les termes temporels manifestes.
    Retourne (date_start, date_end) si détecté, None sinon.
    """
    question_lower = question.lower().strip()
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # "aujourd'hui" / "aujourd hui" / "ce jour" - support multiple formats
    if re.search(r'(aujourd[\s\']*hui|ce jour|cet jour)', question_lower):
        return today, today + timedelta(days=1)
    
    # "demain"
    if re.search(r'\bdemain\b', question_lower):
        tomorrow = today + timedelta(days=1)
        return tomorrow, tomorrow + timedelta(days=1)
    
    # "hier"
    if re.search(r'\bhier\b', question_lower):
        yesterday = today - timedelta(days=1)
        return yesterday, today
    
    # "ce soir" / "cette nuit"
    if re.search(r'\b(ce soir|cette nuit)\b', question_lower):
        return today, today + timedelta(days=1)
    
    # "cette semaine"
    if re.search(r'\bcette\s+semaine\b', question_lower):
        # Jusqu'à dimanche
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour > 0:
            end = today + timedelta(days=1)
        else:
            end = today + timedelta(days=days_until_sunday + 1)
        return today, end
    
    # "la semaine prochaine"
    if re.search(r'\bla\s+semaine\s+prochaine\b', question_lower):
        next_monday = today + timedelta(days=(7 - today.weekday()))
        next_sunday = next_monday + timedelta(days=7)
        return next_monday, next_sunday
    
    # "ce week-end"
    if re.search(r'\bce\s+week[- ]?end\b', question_lower):
        days_until_sat = (5 - now.weekday()) % 7
        saturday = today + timedelta(days=days_until_sat) if days_until_sat > 0 else today
        sunday = saturday + timedelta(days=2)
        return saturday, sunday
    
    # "dans X jours"
    match = re.search(r'\bdans\s+(\d+)\s+jours?\b', question_lower)
    if match:
        days = int(match.group(1))
        target = today + timedelta(days=days)
        return target, target + timedelta(days=1)
    
    return None


def validate_temporal_results(question: str, results: List[SearchResult]) -> List[SearchResult]:
    """
    Filtre les résultats par la plage de dates détectée dans la question.
    Approche stricte basée sur regex + parsing de dates.
    """
    # 1. Essayer de détecter une plage de dates manifeste
    date_range = parse_temporal_intent(question)
    
    if not date_range:
        logger.debug("Pas de terme temporel détecté, passage de tous les résultats")
        return results
    
    date_start, date_end = date_range
    logger.info(f"Filtrage par date: {date_start.date()} à {date_end.date()}")
    
    filtered = []
    for result in results:
        try:
            date_str = result.metadata.get("date", "")
            if not date_str:
                logger.debug("Événement sans date, rejeté")
                continue
            
            # Parser la date ISO 8601
            if 'T' in date_str:
                date_part = date_str.split('+')[0].split('Z')[0]
            else:
                date_part = date_str.split('+')[0]
            
            event_date = datetime.fromisoformat(date_part)
            
            # Vérifier si l'événement est dans la plage
            if date_start <= event_date < date_end:
                filtered.append(result)
                logger.debug(f"✓ Accepted: {result.metadata.get('title')} ({date_str})")
            else:
                logger.debug(f"✗ Rejected: {result.metadata.get('title')} ({date_str}) - hors plage {date_start.date()}-{date_end.date()}")
        
        except Exception as e:
            logger.debug(f"Erreur parsing date '{date_str}': {e}")
            continue
    
    logger.info(f"Avant: {len(results)} résultats, Après: {len(filtered)} validés")
    
    return filtered


def search_in_faiss(query: str, top_k: int = 3) -> List[SearchResult]:
    """
    Recherche dans l'index FAISS pour trouver les événements similaires.
    
    COMMENT ÇA MARCHE?
    1. Convertir la question en vecteur (numéros) avec embed_text()
    2. FAISS compare ce vecteur à tous les événements indexés
    3. Retourner les top_k événements les plus proches
    
    Args:
        query: Question de l'utilisateur (ex: "concerts jazz")
        top_k: Nombre d'événements à retourner (défaut: 3)
        
    Returns:
        Liste de SearchResult (événements trouvés avec leur score de similarité)
    """
    try:
        # 1. Charger l'index FAISS depuis le disque et ses métadonnées
        index, metadata = get_faiss_index()
        
        if index is None or metadata is None:
            logger.warning("Index FAISS non chargé")
            return []
        
        # 2. Convertir la question en vecteur numérique
        # Exemple: "concerts" → [0.12, -0.45, 0.89, ...]
        query_vector = embed_text(query)
        logger.debug(f"Vecteur généré pour: '{query}'")
        
        # 3. FAISS cherche les top_k vecteurs les plus proches
        # distances: distance euclidienne entre la question et chaque événement
        # indices: numéro de position de chaque événement
        distances, indices = index.search(query_vector, min(top_k, index.ntotal))
        logger.info(f"FAISS: {len(indices[0])} résultats trouvés")
        
        # 4. Transformer les résultats bruts FAISS en SearchResult lisibles
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if 0 <= idx < len(metadata):
                # Récupérer les métadonnées complètes de l'événement
                meta = metadata[idx]
                
                # Convertir la distance en score de similarité (0 à 1)
                # Plus la distance est petite, plus la score est proche de 1
                score = 1.0 / (1.0 + dist)
                
                results.append(SearchResult(
                    score=float(score),
                    content=meta.get("text_preview", "")[:300],  # Descrip courte
                    metadata={
                        "event_id": meta.get("event_id"),
                        "title": meta.get("title"),
                        "date": meta.get("date"),
                        "location": meta.get("location")
                    }
                ))
        
        logger.info(f"FAISS: {len(results)} résultats pour '{query}' (scores: {[round(r.score, 2) for r in results]})")
        return results
    
    except Exception as e:
        logger.error(f"Erreur FAISS: {e}")
        import traceback
        traceback.print_exc()
        return []




def generate_answer(question: str, sources: List[SearchResult]) -> str:
    """
    Génère une réponse INTELLIGENTE basée sur la question et les sources.
    
    Utilise call_mistral() wrapper (HTTP-based, no SDK dependencies).
    """
    try:
        # S'il n'y a pas de sources, répondre honnêtement
        if not sources:
            logger.info("Pas de sources trouvées - appel Mistral pour réponse intelligente")
            
            current_date = datetime.now().strftime("%d %B %Y à %H:%M")
            user_prompt = f"""Tu es un assistant pour trouver des événements culturels français.
Date/heure actuelle: {current_date}
Question: "{question}"

AUCUN événement n'a été trouvé correspondant à cette recherche.

Réponds honnêtement et naturellement. Tu peux :
- Reformuler ta compréhension de leur recherche
- Suggérer des alternatives
- Être utile sans inventer de données

Réponse:"""
            
            answer = call_mistral(user_prompt)
            if answer:
                logger.info(f"Réponse générée (pas de sources): {len(answer)} caractères")
                return answer
            
            return "Désolé, je n'ai pas trouvé d'événements correspondant à votre recherche."
        
        # Avec sources : faire une vraie analyse intelligente
        logger.info(f"Analysing {len(sources)} sources with Mistral...")
        
        current_date = datetime.now().strftime("%d %B %Y à %H:%M")
        
        # Construire les sources avec contexte
        sources_text = "\n".join([
            f"- [{s.metadata.get('title', 'N/A')}] "
            f"({s.metadata.get('date', 'N/A')}) "
            f"\"{s.content[:100]}...\" "
            f"[score: {s.score:.3f}]"
            for s in sources
        ])
        
        user_prompt = f"""Tu es un assistant intelligent pour trouver des événements culturels en France.

Date/heure actuelle: {current_date}
Question utilisateur: "{question}"

Événements trouvés:
{sources_text}

IMPORTANT:
1. Analyse si les événements trouvés sont VRAIMENT pertinents pour la question
2. Si oui: résume et cite les événements pertinents
3. Si non: dis-le honnêtement ("Ces résultats ne correspondent pas à votre question")
4. Sois concis et naturel, pas robotique

Génère une réponse UTILE et HONNÊTE:"""
        
        answer = call_mistral(user_prompt)
        
        if answer:
            logger.info(f"Réponse générée: {len(answer)} caractères")
            return answer
        
        # Fallback : résumé simple
        logger.warning("Mistral API call failed - using fallback summary")
        summary = "\n".join([
            f"- {s.metadata.get('title', 'N/A')} ({s.metadata.get('date', 'N/A')})"
            for s in sources
        ])
        return f"Événements trouvés:\n{summary}"
    
    except Exception as e:
        logger.error(f"Erreur génération réponse: {e}")
        return f"Erreur lors de la génération de la réponse: {e}"


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", response_model=StatusResponse)
def root():
    """Endpoint racine - retourne le statut de l'API."""
    exists = index_exists()
    return StatusResponse(
        status="operational" if exists else "degraded",
        index_exists=exists,
        message="API Puls-Events RAG opérationnelle" if exists else "Index non trouvé - appelez /rebuild"
    )


@app.get("/health", response_model=StatusResponse)
def health():
    """Vérification de l'état (health check) pour les conteneurs."""
    exists = index_exists()
    return StatusResponse(
        status="healthy" if exists else "unhealthy",
        index_exists=exists,
        message="✓ API en bonne santé" if exists else "⚠ Index manquant"
    )


@app.post("/rebuild", response_model=StatusResponse)
def rebuild_index():
    """Lance la reconstruction de l'index FAISS (asynchrone, non-bloquant).
    
    Utilise un thread séparé pour ne pas bloquer les autres requêtes.
    """
    global REBUILD_IN_PROGRESS
    
    if REBUILD_IN_PROGRESS:
        return StatusResponse(
            status="in_progress",
            index_exists=index_exists(),
            message="Une reconstruction est déjà en cours..."
        )
    
    try:
        REBUILD_IN_PROGRESS = True
        
        def run():
            global _faiss_index
            global _metadata_list
            logger.info("Démarrage de la reconstruction de l'index...")
            try:
                result = subprocess.run(
                    ["python", "scripts/build_index.py"],
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                if result.returncode != 0:
                    logger.error(f"Erreur build_index: {result.stderr}")
                else:
                    logger.info("Reconstruction terminée avec succès")
                    # Réinitialiser le cache pour recharger
                    _faiss_index = None
                    _metadata_list = None
            except Exception as e:
                logger.error(f"Erreur subprocess: {e}")
            finally:
                REBUILD_IN_PROGRESS = False
        
        # Créer un thread daemon pour éviter de bloquer l'API
        t = threading.Thread(target=run, daemon=True)
        t.start()
        
        return StatusResponse(
            status="queued",
            index_exists=index_exists(),
            message="Reconstruction de l'index en cours (background)..."
        )
    
    except Exception as e:
        REBUILD_IN_PROGRESS = False
        logger.error(f"Erreur lors du démarrage de la reconstruction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask", response_model=AskResponse)
def ask(q: Query):
    """Traite une question utilisateur via le système RAG.
    
    1. Valide la question
    2. Vérifie que l'index FAISS existe
    3. Recherche des chunks similaires
    4. FILTRE par intention temporelle si détectée
    5. Génère une réponse avec Mistral
    6. Retourne réponse + sources
    """
    # Valider que la question n'est pas vide
    if not q.question or not q.question.strip():
        raise HTTPException(status_code=400, detail="Question vide - veuillez fournir une question valide")
    
    # Vérifie que l'index existe
    if not index_exists():
        raise HTTPException(
            status_code=503,
            detail="Index FAISS non trouvé. Appelez POST /rebuild pour créer vectors/index.faiss."
        )
    
    try:
        logger.info(f"❓ Question: {q.question}")
        
        # Pipeline:
        # 1. Recherche FAISS brute (TOP-K AUGMENTÉ pour queries temporelles)
        # Si intention temporelle détectée, on récupère plus de résultats
        # pour avoir plus de chances de trouver des événements dans la plage
        expanded_top_k = 50 if parse_temporal_intent(q.question) else q.top_k * 3
        sources = search_in_faiss(q.question, expanded_top_k)
        
        # 2. FILTRER par intention temporelle si détectée
        sources_filtered = validate_temporal_results(q.question, sources)
        
        # 3. Si filtrage temporel a réduit drastiquement à zéro résultats,
        #    c'est bon - Mistral donnera une réponse honnête
        #    (on NE retombe pas sur les généraux pour préserver la sémantique temporelle!)
        sources_final = sources_filtered[:q.top_k]
        
        # 4. Mistral génère une réponse intelligente (même si peu/pas de sources)
        answer = generate_answer(q.question, sources_final)
        
        logger.info(f"✓ Réponse avec {len(sources_final)} sources")
        
        return AskResponse(
            question=q.question,
            answer=answer,
            sources=sources_final,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=List[SearchResult])
def search(q: Query):
    """Effectue une recherche de similarité sans génération.
    
    Retourne les top-k chunks les plus similaires à la question.
    """
    if not q.question or not q.question.strip():
        raise HTTPException(status_code=400, detail="Question vide")
    
    if not index_exists():
        raise HTTPException(status_code=503, detail="Index non disponible")
    
    try:
        logger.info(f"Recherche pour: {q.question} (top-{q.top_k})")
        results = search_in_faiss(q.question, q.top_k)
        logger.info(f"Trouvé {len(results)} résultats")
        return results
    
    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS CHATBOT - Conversationnel avec historique
# ============================================================================

@app.post("/chat/start", response_model=ChatStartResponse)
def chat_start(req: ChatStartRequest):
    """Démarre une nouvelle conversation.
    
    Retourne un conversation_id à utiliser pour les messages suivants.
    """
    try:
        conversation_id = create_conversation(req.initial_message or "")
        
        conversation = get_conversation(conversation_id)
        
        return ChatStartResponse(
            conversation_id=conversation_id,
            created_at=conversation["created_at"],
            message=f"Conversation créée (ID: {conversation_id}). "
                   f"Vous pouvez maintenant envoyer des messages."
        )
    
    except Exception as e:
        logger.error(f"Erreur création conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/message", response_model=ChatMessageResponse)
def chat_message(req: ChatMessageRequest):
    """Envoie un message dans une conversation.
    
    L'API:
    1. Maintient l'historique
    2. Recherche les événements pertinents dans FAISS
    3. Envoie le contexte + sources à Mistral
    """
    try:
        # Vérifier que la conversation existe
        conversation = get_conversation(req.conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {req.conversation_id} not found"
            )
        
        # Mettre à jour avec le message utilisateur
        add_message(req.conversation_id, "user", req.message)
        
        # Récupérer l'historique COMPLET (sans le dernier message user qu'on vient d'ajouter)
        messages_history = get_conversation_messages(req.conversation_id)[:-1]
        
        # ============================================================================
        # NOUVELLE: Recherche dans FAISS pour obtenir les événements pertinents
        # ============================================================================
        logger.info(f"🔍 Recherche FAISS pour: {req.message}")
        
        # 1. Recherche FAISS brute (TOP-K AUGMENTÉ pour queries temporelles)
        expanded_top_k = 50 if parse_temporal_intent(req.message) else 9
        sources = search_in_faiss(req.message, expanded_top_k)
        
        # 2. FILTRER par intention temporelle si détectée
        sources_filtered = validate_temporal_results(req.message, sources)
        sources_final = sources_filtered[:3]  # Top 3 événements
        
        logger.info(f"  Trouvé {len(sources_final)} événements pertinents")
        
        # Construire le contexte des événements pour le prompt
        events_context = ""
        if sources_final and len(sources_final) > 0:
            events_context = "\n\n" + "🎭 ÉVÉNEMENTS DISPONIBLES DANS LA BASE (À UTILISER POUR RÉPONDRE):" + "\n"
            events_context += "=" * 70 + "\n"
            for i, src in enumerate(sources_final, 1):
                events_context += f"\nÉVÉNEMENT {i}:\n"
                events_context += f"  📌 Titre: {src.metadata.get('title', 'N/A')}\n"
                events_context += f"  📅 Date: {src.metadata.get('date', 'N/A')}\n"
                events_context += f"  📍 Lieu: {src.metadata.get('location', 'N/A') or 'Lieu non spécifié'}\n"
                events_context += f"  📝 Description: {src.content[:300]}\n"
            events_context += "\n" + "=" * 70 + "\n"
        else:
            events_context = "\n\n⚠️ Aucun événement pertinent trouvé dans la base."
        
        # Prompt système pour le chatbot avec contexte d'événements
        # On est TRÈS explicite: TU DOIS répondre basé sur CES événements
        system_prompt = f"""Tu es un assistant spécialisé dans la recommandation d'événements culturels en France.

**INSTRUCTIONS CRITIQUES:**
1. Tu DOIS baser ta réponse UNIQUEMENT sur les événements listés ci-dessous
2. Ne cherche PAS à demander plus d'infos - présente les événements disponibles
3. Si l'utilisateur demande quelque chose et il y a des événements, cite-LES avec détails
4. Si aucun événement trouvé, dis-le honnêtement mais proposes des alternatives
5. Sois amical, concis, et cite TOUJOURS le titre, la date et le lieu

{events_context}

Réponds maintenant à la question de l'utilisateur en utilisant CES événements comme source de vérité.
Si pertinent, recommande l'événement le plus adéquat."""
        
        # Appeler Mistral avec l'historique complet + contexte des événements
        response = call_mistral(
            user_message=req.message,
            system_message=system_prompt,
            messages_history=messages_history
        )
        
        if not response:
            raise HTTPException(
                status_code=500,
                detail="Mistral API call failed"
            )
        
        # Sauvegarder la réponse d'assistant
        add_message(req.conversation_id, "assistant", response)
        
        # Récupérer la conversation mise à jour
        updated_conversation = get_conversation(req.conversation_id)
        
        return ChatMessageResponse(
            conversation_id=req.conversation_id,
            user_message=req.message,
            assistant_response=response,
            timestamp=datetime.now().isoformat(),
            messages_count=len(updated_conversation["messages"])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur envoi message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/history/{conversation_id}")
def chat_history(conversation_id: str):
    """Récupère l'historique complet d'une conversation."""
    try:
        conversation = get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found"
            )
        
        return conversation
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération historique: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/list")
def chat_list():
    """Liste toutes les conversations en cours."""
    try:
        conversations = list_conversations()
        return {
            "conversations": conversations,
            "total": len(conversations)
        }
    except Exception as e:
        logger.error(f"Erreur listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat/{conversation_id}")
def chat_delete(conversation_id: str):
    """Supprime une conversation."""
    try:
        result = delete_conversation(conversation_id)
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found"
            )
        
        return {"message": f"Conversation {conversation_id} supprimée"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
