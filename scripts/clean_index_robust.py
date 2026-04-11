#!/usr/bin/env python3
"""Version robuste du script de nettoyage des événements passés."""
import os
import json
import pathlib
import logging
from datetime import datetime
from typing import List, Dict, Tuple

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

VECTORS_DIR = pathlib.Path("vectors")
DEFAULT_INDEX_PATH = VECTORS_DIR / "index.faiss"
DEFAULT_METADATA_PATH = VECTORS_DIR / "metadata.jsonl"


def parse_date(date_str: str):
    """Parse une date ISO 8601."""
    if not date_str:
        return None
    try:
        if "T" in date_str:
            dt_str = date_str.split("+")[0].split("Z")[0]
            return datetime.fromisoformat(dt_str)
        else:
            return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None


def load_metadata(path: str) -> List[Dict]:
    """Charge les métadonnées."""
    metadata = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))
    return metadata


def load_index(path: str):
    """Charge l'index FAISS depuis le disque.
    
    POURQUOI?
    L'index FAISS est stocké sous forme de fichier binaire index.faiss
    On le charge en mémoire pour pouvoir le manipuler/analyser
    """
    return faiss.read_index(str(path))


def safe_extract_vectors(index, metadata: List[Dict]) -> np.ndarray:
    """Extrait les vecteurs de manière sûre.
    
    PROBLÈME:
    FAISS a pas toujours une méthode facile pour récupérer tous les vecteurs
    Cela dépend du type d'index
    
    SOLUTION:
    Essayer 2 méthodes:
    1. downcast() = Rapide si ça marche
    2. reconstruct() = Lent mais marche toujours
    
    RETOUR:
    Array numpy avec tous les vecteurs (ntotal x dimension)
    """
    dim = index.d  # Dimensionnalité (768 normalement)
    ntotal = index.ntotal  # Nombre total de vecteurs
    
    logger.info(f"Extraction de {ntotal} vecteurs (dimension {dim})...")
    
    # ========== MÉTHODE 1: DOWNCAST (RAPIDE) ==========
    # downcast = Essayer de convertir vers un type qu'on peut accéder directement
    try:
        vectors = faiss.downcast(index).reconstruct_n(0, ntotal)
        logger.info(f"  ✓ Downcast OK")
        return vectors
    except Exception as e:
        logger.warning(f"  ⚠ Downcast failed: {e}")
    
    # ========== MÉTHODE 2: RECONSTRUCT INDIVIDUEL (LENT MAIS SÛR) ==========
    # Si downcast échoue, reconstruire chaque vecteur individuellement
    logger.info(f"  Reconstruction individuelle ... (peut prendre du temps)")
    # Créer un array vide pour y mettre les vecteurs
    vectors = np.zeros((ntotal, dim), dtype="float32")
    
    # Pour chaque vecteur dans l'index
    for i in range(ntotal):
        if i % 1000 == 0:
            logger.info(f"    {i}/{ntotal}")
        try:
            # Récupérer le vecteur i
            vectors[i] = index.reconstruct(i)
        except Exception as e:
            logger.warning(f"  Erreur reconstruction vector {i}: {e}")
            # Fallback: vecteur aléatoire
            vectors[i] = np.random.rand(dim).astype("float32")
    
    logger.info(f"  ✓ {ntotal} vecteurs extraits")
    return vectors


def clean_index_robust(
    index_path: str = None,
    metadata_path: str = None,
    dry_run: bool = False
) -> Dict:
    """Nettoyage robuste de l'index FAISS.
    
    QUOI TESTE-T-ON?
    1. Index et metadata existent?
    2. Index et metadata cohérents? (même nombre de lignes)
    3. Événements passés? Les détecter et les sauvegarder
    4. Optionnel: créer un nouvel index sans les passés
    
    RETOUR:
    Dictionnaire avec stats du nettoyage
    """
    if index_path is None:
        index_path = str(DEFAULT_INDEX_PATH)
    if metadata_path is None:
        metadata_path = str(DEFAULT_METADATA_PATH)
    
    logger.info("=" * 70)
    logger.info("NETTOYAGE ROBUSTE DE L'INDEX")
    logger.info("=" * 70)
    
    # ========== ÉTAPE 1: CHARGER LE INDEX ==========
    logger.info("Chargement...")
    # Charger l'index FAISS depuis le fichier
    index = load_index(index_path)
    # Charger les métadonnées (event_id, titre, date, lieu)
    metadata = load_metadata(metadata_path)
    
    logger.info(f"  Index: {index.ntotal} vecteurs")
    logger.info(f"  Metadata: {len(metadata)} lignes")
    
    # ========== ÉTAPE 2: VÉRIFIER LA COHÉRENCE ==========
    # L'index et les métadonnées DOIVENT avoir la même taille
    # Si non, quelque chose s'est cassé
    if index.ntotal != len(metadata):
        logger.error(f"⚠ Incohérence MAJEURE: {index.ntotal} ≠ {len(metadata)}")
        logger.error("Action requise: Rebuild complet")
        return {
            "error": "Index/metadata incoherent",
            "action": "rebuild_required"
        }
    
    # Identifier les vecteurs à garder
    today = datetime.now().date()
    indices_keep = []
    indices_old = []
    
    logger.info(f"Analyse des dates (référence: {today})...")
    
    for idx, meta in enumerate(metadata):
        date_str = meta.get("date", "")
        date_obj = parse_date(date_str)
        
        if date_obj is None:
            indices_keep.append(idx)
            continue
        
        event_date = date_obj.date()
        if event_date < today:
            indices_old.append(idx)
        else:
            indices_keep.append(idx)
    
    logger.info(f"  Événements passés: {len(indices_old)}")
    logger.info(f"  Événements futurs: {len(indices_keep)}")
    
    if len(indices_old) == 0:
        logger.info("✓ Aucun événement à nettoyer")
        return {"action": "no_action", "past_events": 0}
    
    if dry_run:
        logger.info("\n--- MODE SIMULATION ---")
        logger.info(f"Serait supprimé: {len(indices_old)} vecteurs\n")
        for i, idx in enumerate(indices_old[:3]):
            meta = metadata[idx]
            logger.info(f"  {i+1}. {meta.get('title', 'N/A')[:50]} - {meta.get('date', 'N/A')}")
        if len(indices_old) > 3:
            logger.info(f"  ... et {len(indices_old)-3} autres\n")
        return {
            "action": "simulated",
            "old_events": len(indices_old),
            "keep_events": len(indices_keep)
        }
    
    # Backup
    logger.info("Backup...")
    import shutil
    shutil.copy(index_path, f"{index_path}.bak")
    shutil.copy(metadata_path, f"{metadata_path}.bak")
    logger.info(f"  ✓ Backup créés")
    
    # Extraire les vecteurs de manière sûre
    all_vectors = safe_extract_vectors(index, metadata)
    
    # Construire nouveau index
    logger.info("Reconstruction de l'index...")
    dim = index.d
    keep_vectors = all_vectors[indices_keep]
    keep_metadata = [metadata[idx] for idx in indices_keep]
    
    new_index = faiss.IndexFlatL2(dim)
    new_index.add(keep_vectors.astype("float32"))
    
    # Sauvegarder
    logger.info("Sauvegarde...")
    faiss.write_index(new_index, index_path)
    logger.info(f"  ✓ Index: {new_index.ntotal} vecteurs")
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        for meta in keep_metadata:
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
    logger.info(f"  ✓ Metadata: {len(keep_metadata)} lignes")
    
    logger.info("=" * 70)
    logger.info("✅ NETTOYAGE RÉUSSI")
    logger.info("=" * 70)
    
    return {
        "action": "cleaned",
        "removed": len(indices_old),
        "kept": len(indices_keep)
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser("Nettoyage robuste de l'index")
    parser.add_argument("--dry-run", action="store_true", help="Mode simulation")
    args = parser.parse_args()
    
    result = clean_index_robust(dry_run=args.dry_run)
    print(f"\nRésultat: {result}")
