"""Application FastAPI pour le système RAG Puls-Events.
Endpoints disponibles:
- GET  /                : status de l'API
- GET  /health         : vérification de l'état
- POST /ask             : poser une question au système RAG
- POST /rebuild         : reconstruire l'index FAISS
- POST /search          : recherche similaire dans l'index
- GET  /docs            : documentation Swagger

Déploiement via Docker + docker-compose.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import subprocess
import threading
import pathlib
import json
import logging
import os
from datetime import datetime

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
    """Retourne le modèle d'embedding (singleton avec cache)."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from langchain.embeddings import HuggingFaceEmbeddings
            logger.info("Initialisation du modèle d'embedding HuggingFace...")
            _embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            logger.info("✓ Modèle d'embedding chargé")
        except Exception as e:
            logger.warning(f"HuggingFace embeddings non disponible: {e}")
            _embedding_model = "error"
    
    return _embedding_model if _embedding_model != "error" else None


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


def embed_text(text: str) -> np.ndarray:
    """Vectorise un texte (768D pour matcher l'index FAISS)."""
    try:
        model = get_embedding_model()
        if model is None:
            # Fallback: vecteur aléatoire (shape: 1, 768 pour matcher build_index.py)
            logger.debug("Utilisation d'embeddings aléatoires 768D")
            return np.random.rand(1, 768).astype("float32")
        
        # Vectoriser avec HuggingFace (retourne 384D, pad à 768D)
        embedding = model.embed_query(text)
        # Pad embedding to 768D to match FAISS index
        if len(embedding) < 768:
            embedding = embedding + [0] * (768 - len(embedding))
        elif len(embedding) > 768:
            embedding = embedding[:768]
        return np.array([embedding], dtype="float32")
    except Exception as e:
        logger.error(f"Erreur embedding: {e}")
        return np.random.rand(1, 768).astype("float32")


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


def search_in_faiss(query: str, top_k: int = 3) -> List[SearchResult]:
    """Recherche les textes les plus similaires à la requête avec filtrage temporel."""
    try:
        index, metadata = get_faiss_index()
        
        if index is None or metadata is None:
            logger.warning("Index FAISS non chargé")
            return []
        
        # Vectoriser la question
        query_vector = embed_text(query)
        
        # Rechercher plus de résultats pour pouvoir en filtrer (on en demande 5x plus)
        k_search = min(top_k * 5, index.ntotal)
        distances, indices = index.search(query_vector, k_search)
        
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if 0 <= idx < len(metadata):
                meta = metadata[idx]
                
                # NOTE: Filtrage temporel désactivé car index contient principalement des événements 2024
                # À réactiver après reconstruction avec événements plus récents
                # if not is_event_valid(meta):
                #     logger.debug(f"Événement filtré (trop vieux): {meta.get('title')} - {meta.get('date')}")
                #     continue
                
                # Convertir distance L2 en score de similarité (0-1)
                score = 1.0 / (1.0 + dist)
                
                results.append(SearchResult(
                    score=float(score),
                    content=meta.get("text_preview", "")[:200],  # Max 200 chars
                    metadata={
                        "event_id": meta.get("event_id"),
                        "title": meta.get("title"),
                        "date": meta.get("date"),
                        "location": meta.get("location")
                    }
                ))
                
                # Arrêter une fois qu'on a assez de résultats
                if len(results) >= top_k:
                    break
        
        return results
    
    except Exception as e:
        logger.error(f"Erreur recherche FAISS: {e}")
        return []


def generate_answer(question: str, sources: List[SearchResult]) -> str:
    """Génère une réponse basée sur les sources avec Mistral."""
    try:
        # Construire le contexte à partir des sources
        context = "\n".join([
            f"- {s.metadata.get('title', 'N/A')} ({s.metadata.get('location', 'N/A')}, {s.metadata.get('date', 'N/A')}): {s.content}"
            for s in sources
        ])
        
        # Essayer d'utiliser Mistral
        api_key = os.environ.get("MISTRAL_API_KEY")
        if api_key:
            try:
                from mistral import Mistral
                client = Mistral(api_key=api_key)
                
                # Ajouter la date/heure actuelle au contexte pour interpréter "ce soir", "cette semaine", etc.
                current_date = datetime.now().strftime("%A %d %B %Y à %H:%M")
                
                prompt = f"""Tu es un assistant expert en événements culturels. 
Réponds à la question de l'utilisateur en utilisant le contexte fourni.
Sois concis et factuel.
Important: La date/heure actuelle est le {current_date}.
Si l'utilisateur dit "ce soir", "cet (après-)midi", "cette semaine", etc., réfère-toi à cette date.

CONTEXTE (événements trouvés):
{context}

QUESTION: {question}

RÉPONSE:"""
                
                message = client.chat.complete(
                    model="mistral-small-latest",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.choices[0].message.content
            except Exception as e:
                logger.warning(f"Mistral API failed: {e}")
        
        # Fallback: construire une réponse simple
        if sources:
            return f"Basé sur les événements trouvés: {context[:500]}..."
        else:
            return f"Désolé, je n'ai pas trouvé d'événement correspondant à: {question}"
    
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
    global _faiss_index
    global _metadata_list
    
    if REBUILD_IN_PROGRESS:
        return StatusResponse(
            status="in_progress",
            index_exists=index_exists(),
            message="Une reconstruction est déjà en cours..."
        )
    
    try:
        REBUILD_IN_PROGRESS = True
        
        def run():
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
    4. Génère une réponse avec Mistral
    5. Retourne réponse + sources
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
        logger.info(f"Question reçue: {q.question}")
        
        # 1. Rechercher les sources pertinentes
        sources = search_in_faiss(q.question, q.top_k)
        
        # 2. Générer la réponse
        answer = generate_answer(q.question, sources)
        
        logger.info(f"Réponse générée avec {len(sources)} sources")
        
        return AskResponse(
            question=q.question,
            answer=answer,
            sources=sources,
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
