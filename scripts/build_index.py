"""Script pour construire l'index du POC RAG Puls-Events.
- Lit `DATAIN/evenements-publics-openagenda.json` (données réelles OpenAgenda)
- Découpe le texte en chunks (fragments de texte)
- Génère les embeddings (vecteurs) avec Mistral ou nombres aléatoires
- Construit un index FAISS et écrit `vectors/index.faiss` + `vectors/metadata.jsonl`

Utilise les données fournies par OpenAgenda.
"""
import os
import json
import pathlib
import random
import logging
from datetime import datetime
from typing import List, Dict, Any

try:
    import numpy as np
    import faiss
except Exception as e:
    faiss = None
    print(f"Warning: FAISS not available: {e}")

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Répartoire de stockage des vecteurs
VECTORS_DIR = pathlib.Path("vectors")
VECTORS_DIR.mkdir(exist_ok=True)

# Fichier de données source
DATAIN_DIR = pathlib.Path("DATAIN")
DEFAULT_DATA_PATH = DATAIN_DIR / "evenements-publics-openagenda.json"


def load_events(path: str = None) -> List[Dict[str, Any]]:
    """Charge les événements depuis le fichier JSON OpenAgenda.
    
    Args:
        path: Chemin vers le fichier JSON (défaut: DATAIN/evenements-publics-openagenda.json)
    
    Returns:
        Liste des événements ou échantillon si fichier manquant
    """
    if path is None:
        path = str(DEFAULT_DATA_PATH)
    
    p = pathlib.Path(path)
    
    if not p.exists():
        logger.warning(f"Fichier {path} non trouvé. Création d'un échantillon minimale...")
        # Échantillon pour tests
        sample = [{
            "id": "sample-1",
            "slug": "jazz-night",
            "title": "Jazz Night",
            "description": "A cozy jazz concert featuring local artists.",
            "location": {"address": "Paris, France"},
            "dates": [{
                "start": "2025-03-01T20:00:00+02:00",
                "end": "2025-03-01T23:00:00+02:00"
            }]
        }]
        return sample
    
    try:
        logger.info(f"Chargement des événements depuis {path}...")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Vérifier le format
        if isinstance(data, list):
            logger.info(f"✓ Loaded {len(data)} events (list format)")
            return data
        elif isinstance(data, dict) and "events" in data:
            events = data["events"]
            logger.info(f"✓ Loaded {len(events)} events (dict.events format)")
            return events
        else:
            logger.warning(f"Format inconnu. Type: {type(data)}")
            return data if isinstance(data, list) else []
    
    except json.JSONDecodeError as e:
        logger.error(f"Erreur JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur lors du chargement: {e}")
        raise


def extract_event_info(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extrait les informations pertinentes d'un événement OpenAgenda.
    
    Format OpenAgenda officiel avec suffixes _fr pour le français.
    
    Args:
        event: Dictionnaire d'événement OpenAgenda
    
    Returns:
        Dictionnaire avec champs standardisés (title, description, date, location, etc.)
    """
    try:
        # Extraire les champs OpenAgenda (avec suffixe _fr pour français)
        event_id = event.get("uid") or event.get("id") or event.get("slug") or "unknown"
        title = event.get("title_fr") or event.get("title") or ""
        description = event.get("description_fr") or event.get("description") or ""
        long_description = event.get("longdescription_fr") or ""
        
        # Combiner les descriptions pour avoir plus de contexte
        full_description = f"{description}\n{long_description}".strip()
        
        # Extraire la location/lieu
        location = ""
        if "location" in event and isinstance(event["location"], dict):
            location = event["location"].get("address", "") or \
                      event["location"].get("name", "")
        
        # Extraire la date
        date_str = ""
        if "firstdate_begin" in event:
            date_str = event["firstdate_begin"]
        elif "dates" in event and isinstance(event["dates"], list) and event["dates"]:
            first_date = event["dates"][0]
            if isinstance(first_date, dict) and "start" in first_date:
                date_str = first_date["start"]
        
        # Keywords et tags
        keywords = event.get("keywords_fr", [])
        if isinstance(keywords, list):
            keywords_str = ", ".join(keywords[:5])  # Max 5 keywords
        else:
            keywords_str = ""
        
        return {
            "event_id": str(event_id),
            "title": title,
            "description": full_description,
            "location": location,
            "date": date_str,
            "keywords": keywords_str,
            "original_event": event  # Garder l'original pour référence
        }
    except Exception as e:
        logger.warning(f"Erreur extraction événement {event.get('uid', 'unknown')}: {e}")
        return None


def chunk_text(text: str, max_len: int = 400) -> List[str]:
    """Découpe un texte en fragments (chunks) de taille maximale.
    Utilisé pour diviser les descriptions d'événements avant vectorisation.
    
    POURQUOI? Les embeddings (vecteurs) fonctionnent mieux sur du texte court (~400 chars)
    plutôt que sur de longues descriptions (1000+ chars).
    
    EXEMPLE:
    Input: "Jazz Night le 15 avril à Paris. Un superbe concert avec..."
    Output: ["Jazz Night le 15 avril à Paris...", "avec musiciens...", ...]
    
    Args:
        text: Texte à découper
        max_len: Taille maximale d'un chunk (défaut 400 chars = ~100 mots)
    
    Returns:
        Liste des chunks (fragments)
    """
    # Si le texte est vide ou déjà court, retourner tel quel
    if not text or len(text) <= max_len:
        return [text] if text else []
    
    # Découper le texte en fragments de max_len caractères
    parts = []
    i = 0
    while i < len(text):
        # Prendre max_len caractères à partir de position i
        parts.append(text[i:i+max_len])
        # Avancer i pour la prochaine itération
        i += max_len
    
    return parts


def embed_texts(texts: List[str]) -> np.ndarray:
    """Génère les embeddings (vecteurs) pour une liste de textes.
    
    UN EMBEDDING C'EST QUOI?
    Un embedding est une représentation numérique d'un texte.
    Exemple: "Jazz" → [0.12, -0.45, 0.89, ...] (768 nombres)
    
    CÀ SERT À QUOI?
    FAISS compare ces vecteurs pour trouver les textes similaires.
    "Jazz" et "Musique jazz" ont des vecteurs proches → Découverte!
    
    COMMENT ÇA MARCHE?
    Option 1: Utiliser Mistral API (API cloud) - Meilleur mais coûteux
    Option 2: Vecteurs aléatoires - Rapide mais moins bon (fallback)
    
    Args:
        texts: Liste des textes à vectoriser ("Jazz Night", "Concert...", etc.)
    
    Returns:
        Matrice numpy de vecteurs (shape: len(texts) x 768)
    """
    try:
        # Essayer d'utiliser Mistral pour générer les embeddings
        from mistral import MistralClient
        api_key = os.environ.get("MISTRAL_API_KEY")
        
        if not api_key:
            logger.warning("MISTRAL_API_KEY non définie. Utilisation de vecteurs aléatoires.")
            raise ValueError("No API key")
        
        logger.info("Utilisation de Mistral pour les embeddings...")
        mc = MistralClient(api_key=api_key)
        
        # Générer un embedding pour chaque texte
        embs = []
        for i, text in enumerate(texts):
            # Afficher la progression tous les 100 textes
            if i % 100 == 0:
                logger.info(f"  Embedding {i}/{len(texts)}...")
            try:
                # Appeler Mistral API pour générer le vecteur
                emb = mc.embed(text)
                embs.append(emb)
            except Exception as e:
                logger.warning(f"  Erreur embedding texte {i}: {e}")
                # Si Mistral échoue pour ce texte, utiliser un vecteur aléatoire
                embs.append(np.random.rand(768).astype("float32"))
        
        return np.array(embs, dtype="float32")
    
    except Exception as e:
        # Fallback: Mistral indisponible, utiliser vecteurs aléatoires
        logger.info(f"Mistral non disponible ({e}). Utilisation de vecteurs aléatoires...")
        
        # Dimension standard des embeddings (768 = taille standard Mistral)
        dim = 768
        # RNG = Random Number Generator avec seed fixe pour reproductibilité
        rng = np.random.RandomState(42)
        # Générer len(texts) vecteurs aléatoires de dimension 768
        return rng.rand(len(texts), dim).astype("float32")


def build_index(
    data_path: str = None,
    index_path: str = "vectors/index.faiss",
    metadata_path: str = "vectors/metadata.jsonl",
    max_events: int = None,
    min_text_len: int = 10
) -> int:
    """Construit l'index FAISS complet :
    1. Charge les événements
    2. Découpe les descriptions en chunks
    3. Génère les embeddings
    4. Crée l'index FAISS et sauvegarde les métadonnées
    
    Args:
        data_path: Chemin vers le fichier JSON
        index_path: Où sauvegarder l'index FAISS
        metadata_path: Où sauvegarder les métadonnées
        max_events: Nombre max d'événements à traiter (None = tous)
        min_text_len: Longueur minimale du texte pour créer un chunk
    
    Returns:
        Nombre de vecteurs créés
    """
    if data_path is None:
        data_path = str(DEFAULT_DATA_PATH)
    
    logger.info("=" * 60)
    logger.info("CONSTRUCTION DE L'INDEX FAISS")
    logger.info("=" * 60)
    
    # Charger les événements
    events = load_events(data_path)
    logger.info(f"Total d'événements chargés: {len(events)}")
    
    if max_events:
        # Prioritiser les événements 2025+ pour inclure dates récentes
        def get_event_date_sortkey(event_dict):
            try:
                date_str = event_dict.get("date", "")
                if date_str:
                    # Extract year from ISO format (2026-04-05...)
                    year = date_str[:4]
                    return (-int(year), date_str)  # Negative year = descending sort
                return (-1900, "")  # Events without dates go last
            except:
                return (-1900, "")
        
        events = sorted(events, key=get_event_date_sortkey)[:max_events]
        logger.info(f"Limité à {max_events} événements pour ce POC")
    
    chunks = []
    meta = []
    failed_events = 0
    
    # ========== ÉTAPE 1: TRAITER CHAQUE ÉVÉNEMENT ==========
    # Pour chaque événement OpenAgenda:
    # 1. Extraire les infos (titre, description, date, lieu)
    # 2. Découper la description en chunks (fragments)
    # 3. Garder les métadonnées pour chaque chunk
    
    for idx, event in enumerate(events):
        # Afficher la progression tous les 1000 événements
        if idx % 1000 == 0:
            logger.info(f"Traitement événement {idx}/{len(events)}...")
        
        try:
            # Extraire les infos pertinentes du format OpenAgenda
            info = extract_event_info(event)
            if not info:
                failed_events += 1
                continue
            
            # Combiner titre + description pour avoir un texte complet
            # Exemple: "Jazz Night\nA cozy jazz concert featuring..."
            text = (info.get("title", "") + "\n" + info.get("description", "")).strip()
            
            # Ignorer les événements sans texte significatif
            # (Au moins 10 caractères)
            if len(text) < min_text_len:
                continue
            
            # Découper le texte en chunks (fragments)
            # "Jazz Night 20h. Super concert. Musique live..." 
            # → ["Jazz Night 20h. Super concert...", "Musique live..." ]
            for chunk in chunk_text(text):
                if len(chunk) >= min_text_len:
                    # Sauvegarder le chunk (texte à vectoriser)
                    chunks.append(chunk)
                    
                    # Sauvegarder les métadonnées (pour récupération ultérieure)
                    # Exemple: {"event_id": "123", "title": "Jazz Night", "date": "2026-04-15"}
                    meta.append({
                        "event_id": info.get("event_id"),
                        "title": info.get("title"),
                        "date": info.get("date"),
                        "location": info.get("location"),
                        "text_preview": chunk[:100]  # Aperçu du chunk pour débogger
                    })
        
        except Exception as e:
            logger.warning(f"Erreur traitement événement {idx}: {e}")
            failed_events += 1
            continue
    
    logger.info(f"Événements traités avec succès: {len(events) - failed_events}/{len(events)}")
    logger.info(f"Chunks créés: {len(chunks)}")
    
    if not chunks:
        logger.error("Aucun chunk à indexer!")
        raise RuntimeError("No chunks created")
    
    if faiss is None:
        logger.error("FAISS non disponible. Installez: pip install faiss-cpu")
        raise RuntimeError("FAISS not installed")
    
    # ========== ÉTAPE 2: GÉNÉRER LES EMBEDDINGS ==========
    # Convertir les textes + en vecteurs numériques
    # Exemple: "Jazz Night" → [0.12, -0.45, 0.89, ...]
    logger.info("Génération des embeddings...")
    vectors = embed_texts(chunks)
    dim = vectors.shape[1]  # Dimensionalité (normalement 768)
    logger.info(f"Vecteurs générés: shape={vectors.shape}, dim={dim}")
    
    # ========== ÉTAPE 3: CRÉER L'INDEX FAISS ==========
    # FAISS crée un "Google" pour chercher rapidement le vecteur le plus proche
    # IndexFlatL2 = Distance Euclidienne (L2) = Mesure de similarité
    # 
    # Comment FAISS fonctionne:
    # Index FAISS = Structure mathématique qui organise 50,000 vecteurs
    #               pour chercher les k plus proches en < 1ms
    logger.info("Construction de l'index FAISS...")
    index = faiss.IndexFlatL2(dim)  # Créer un index L2 (distance)
    index.add(vectors)  # Ajouter tous les vecteurs au index
    
    # ========== ÉTAPE 4: SAUVEGARDER L'INDEX ==========
    # Sauvegarder l'index FAISS sur disque (fichier binaire)
    # Format: .faiss (propriétaire Facebook/Meta)
    faiss.write_index(index, index_path)
    logger.info(f"✓ Index sauvegardé: {index_path}")
    
    # ========== ÉTAPE 5: SAUVEGARDER LES MÉTADONNÉES ==========
    # Sauvegarder aussi les infos de chaque chunk (titre, date, lieu)
    # Format: JSONL (JSON Lines = une ligne JSON = une métadonnée)
    # Utilisé pour récupérer event_id, titre, etc quand FAISS retourne une index
    with open(metadata_path, "w", encoding="utf-8") as f:
        for m in meta:
            # Écrire une ligne JSON pour chaque chunk
            # Exemple: {"event_id": "123", "title": "Jazz Night", "date": "2026-04-15"}
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    logger.info(f"✓ Métadonnées sauvegardées: {metadata_path}")
    
    logger.info("=" * 60)
    logger.info(f"INDEX CRÉÉ: {vectors.shape[0]} vecteurs")
    logger.info("=" * 60)
    
    return vectors.shape[0]


# Point d'entrée : exécuter la construction de l'index
if __name__ == "__main__":
    try:
        start_time = datetime.now()
        num_vectors = build_index(
            data_path=str(DEFAULT_DATA_PATH),
            max_events=50000,  # Limiter à 50k pour POC (évite OOM + assez events)
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Temps d'exécution: {elapsed:.2f}s")
        logger.info("✓ Index construction completed successfully!")
    except Exception as e:
        logger.error(f"✗ Build failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
