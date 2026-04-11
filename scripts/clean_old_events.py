"""Script pour désindexer les événements passés.
- Charge l'index FAISS existant et les métadonnées
- Filtre les événements dont la date est passée
- Reconstruit l'index avec seulement les événements futurs
- Sauvegarde le nouvel index et les métadonnées mises à jour

Utilisation:
    python scripts/clean_old_events.py [--index-path vectors/index.faiss] [--metadata-path vectors/metadata.jsonl] [--dry-run]
"""
import os
import json
import pathlib
import logging
import argparse
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

# Chemins par défaut
VECTORS_DIR = pathlib.Path("vectors")
DEFAULT_INDEX_PATH = VECTORS_DIR / "index.faiss"
DEFAULT_METADATA_PATH = VECTORS_DIR / "metadata.jsonl"


def parse_date(date_str: str) -> datetime:
    """Parse une date ISO 8601 ou d'autres formats.
    
    Args:
        date_str: Chaîne de date (ex: "2025-03-15T20:00:00+02:00" ou "2025-03-15")
    
    Returns:
        Objet datetime
    """
    if not date_str:
        return None
    
    try:
        # Format ISO 8601 avec timezone
        if "T" in date_str:
            # Enlever la timezone (garder juste la date/heure)
            dt_str = date_str.split("+")[0].split("Z")[0]
            return datetime.fromisoformat(dt_str)
        else:
            # Format simple YYYY-MM-DD
            return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception as e:
        logger.warning(f"Impossible de parser la date '{date_str}': {e}")
        return None


def load_metadata(metadata_path: str) -> List[Dict]:
    """Charge les métadonnées depuis le fichier JSONL.
    
    Args:
        metadata_path: Chemin vers metadata.jsonl
    
    Returns:
        Liste des dictionnaires de métadonnées
    """
    metadata = []
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    metadata.append(json.loads(line))
        logger.info(f"✓ Chargé {len(metadata)} lignes de métadonnées")
        return metadata
    except Exception as e:
        logger.error(f"Erreur lors du chargement des métadonnées: {e}")
        raise


def load_index(index_path: str) -> faiss.Index:
    """Charge l'index FAISS.
    
    Args:
        index_path: Chemin vers index.faiss
    
    Returns:
        Index FAISS
    """
    try:
        if not os.path.exists(index_path):
            logger.error(f"Index non trouvé: {index_path}")
            raise FileNotFoundError(f"Index not found: {index_path}")
        
        index = faiss.read_index(index_path)
        logger.info(f"✓ Index chargé: {index.ntotal} vecteurs")
        return index
    except Exception as e:
        logger.error(f"Erreur lors du chargement de l'index: {e}")
        raise


def identify_old_events(
    metadata: List[Dict],
    today: datetime = None
) -> Tuple[List[int], List[int]]:
    """Identifie les indices des événements passés et futurs.
    
    Args:
        metadata: Liste des métadonnées
        today: Date de référence (défaut: aujourd'hui)
    
    Returns:
        Tuple (indices_old, indices_keep)
    """
    if today is None:
        today = datetime.now()
    
    # Juste la date (sans heure)
    today_date = today.date()
    
    indices_old = []
    indices_keep = []
    
    # Track problematic dates for logging
    parsing_errors = 0
    past_events_list = []
    future_events_list = []
    
    for idx, meta in enumerate(metadata):
        date_str = meta.get("date", "")
        date_obj = parse_date(date_str)
        
        if date_obj is None:
            # Si pas de date, on garde (par sécurité)
            if not date_str:
                logger.debug(f"  Event {idx} missing date, keeping")
            else:
                logger.warning(f"  Event {idx} invalid date format: {date_str}")
                parsing_errors += 1
            indices_keep.append(idx)
            continue
        
        event_date = date_obj.date()
        title = meta.get("title", "Unknown")[:50]
        
        if event_date < today_date:
            indices_old.append(idx)
            past_events_list.append({
                "idx": idx,
                "date": event_date,
                "title": title,
                "days_ago": (today_date - event_date).days
            })
        else:
            indices_keep.append(idx)
            future_events_list.append({
                "idx": idx,
                "date": event_date,
                "title": title,
                "days_ahead": (event_date - today_date).days
            })
    
    # Log details about found events
    if past_events_list:
        logger.info(f"  Top past events (to remove):")
        for evt in sorted(past_events_list, key=lambda x: x['days_ago'], reverse=True)[:5]:
            logger.info(f"    • {evt['title']} ({evt['date']}) - {evt['days_ago']} days ago")
    
    if parsing_errors > 0:
        logger.warning(f"  {parsing_errors} events with unparseable dates (kept for safety)")
    
    return indices_old, indices_keep


def clean_index(
    index_path: str = None,
    metadata_path: str = None,
    dry_run: bool = False,
    backup: bool = True
) -> Dict:
    """Désindexe les événements passés.
    
    Args:
        index_path: Chemin vers index.faiss
        metadata_path: Chemin vers metadata.jsonl
        dry_run: Si True, simule sans modifier
        backup: Si True, sauvegarde l'ancien index en .bak
    
    Returns:
        Dictionnaire avec statistiques de nettoyage
    """
    if index_path is None:
        index_path = str(DEFAULT_INDEX_PATH)
    if metadata_path is None:
        metadata_path = str(DEFAULT_METADATA_PATH)
    
    logger.info("=" * 70)
    logger.info("NETTOYAGE DE L'INDEX (SUPPRESSION DES ÉVÉNEMENTS PASSÉS)")
    logger.info("=" * 70)
    
    # Charger les données existantes
    logger.info("Chargement des données existantes...")
    index = load_index(index_path)
    metadata = load_metadata(metadata_path)
    
    # Vérifier la cohérence
    if index.ntotal != len(metadata):
        logger.warning(
            f"⚠ Incohérence: index={index.ntotal} vecteurs, "
            f"metadata={len(metadata)} lignes"
        )
    
    # Identifier les événements passés
    logger.info(f"Analyse des dates (référence: {datetime.now().date()})...")
    indices_old, indices_keep = identify_old_events(metadata)
    
    logger.info(f"Événements passés: {len(indices_old)}")
    logger.info(f"Événements futurs: {len(indices_keep)}")
    
    if len(indices_old) == 0:
        logger.info("✓ Aucun événement à nettoyer")
        return {
            "total_vectors": len(metadata),
            "old_vectors_removed": 0,
            "remaining_vectors": len(metadata),
            "dry_run": dry_run,
            "action": "no_action"
        }
    
    if dry_run:
        logger.info("\n--- MODE SIMULATION (DRY-RUN) ---")
        logger.info(f"Serait supprimé: {len(indices_old)} vecteurs")
        
        # Afficher un aperçu
        logger.info("\nAperçu des 5 premiers événements à supprimer:")
        for i, idx in enumerate(indices_old[:5]):
            meta = metadata[idx]
            logger.info(f"  [{i+1}] {meta.get('title', 'N/A')} - {meta.get('date', 'N/A')}")
        
        if len(indices_old) > 5:
            logger.info(f"  ... et {len(indices_old) - 5} autres")
        
        return {
            "total_vectors": len(metadata),
            "old_vectors_removed": len(indices_old),
            "remaining_vectors": len(indices_keep),
            "dry_run": True,
            "action": "simulated"
        }
    
    # Sauvegarder un backup
    if backup and os.path.exists(index_path):
        backup_index = f"{index_path}.bak"
        backup_metadata = f"{metadata_path}.bak"
        
        logger.info(f"Création d'une sauvegarde...")
        import shutil
        shutil.copy(index_path, backup_index)
        shutil.copy(metadata_path, backup_metadata)
        logger.info(f"✓ Backup créé: {backup_index}, {backup_metadata}")
    
    # Construire le nouvel index avec seulement les vecteurs à garder
    logger.info("Reconstruction de l'index...")
    
    # Charger tous les vecteurs depuis l'index
    dim = index.d
    all_vectors = faiss.downcast(index).reconstruct_n(0, index.ntotal)
    
    # Vérifier la cohérence
    if len(all_vectors) != len(metadata):
        logger.warning(
            f"⚠ Incohérence détectée: {len(all_vectors)} vecteurs "
            f"vs {len(metadata)} métadonnées. Reconstruction en cours..."
        )
    
    # Sélectionner les vecteurs à garder dans le bon ordre
    keep_vectors_list = []
    keep_metadata = []
    
    for idx in indices_keep:
        if idx < len(all_vectors):
            keep_vectors_list.append(all_vectors[idx])
            keep_metadata.append(metadata[idx])
        else:
            logger.warning(f"⚠ Index {idx} hors limites (max: {len(all_vectors)-1})")
    
    keep_vectors = np.array(keep_vectors_list, dtype="float32")
    
    logger.info(f"  • Vecteurs à conserver: {len(keep_vectors)}")
    logger.info(f"  • Métadonnées à conserver: {len(keep_metadata)}")
    
    if len(keep_vectors) == 0:
        logger.error("Aucun vecteur à conserver ! Annulation.")
        return {
            "total_vectors_before": len(metadata),
            "old_vectors_removed": len(indices_old),
            "remaining_vectors": 0,
            "dry_run": False,
            "action": "error_no_vectors"
        }
    
    # Créer le nouvel index
    new_index = faiss.IndexFlatL2(dim)
    new_index.add(keep_vectors.astype("float32"))
    
    # Sauvegarder le nouvel index
    faiss.write_index(new_index, index_path)
    logger.info(f"✓ Nouvel index sauvegardé: {new_index.ntotal} vecteurs")
    
    # Sauvegarder les nouvelles métadonnées
    with open(metadata_path, "w", encoding="utf-8") as f:
        for meta in keep_metadata:
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
    logger.info(f"✓ Métadonnées mises à jour: {len(keep_metadata)} lignes")
    
    logger.info("=" * 70)
    logger.info(f"NETTOYAGE COMPLÉTÉ")
    logger.info(f"  Vecteurs supprimés: {len(indices_old)}")
    logger.info(f"  Vecteurs conservés: {len(indices_keep)}")
    logger.info("=" * 70)
    
    return {
        "total_vectors_before": len(metadata),
        "old_vectors_removed": len(indices_old),
        "remaining_vectors": len(indices_keep),
        "dry_run": False,
        "action": "cleaned"
    }


def main():
    """Point d'entrée du script."""
    parser = argparse.ArgumentParser(
        description="Désindexe les événements passés de l'index FAISS"
    )
    parser.add_argument(
        "--index-path",
        type=str,
        default=str(DEFAULT_INDEX_PATH),
        help=f"Chemin vers index.faiss (défaut: {DEFAULT_INDEX_PATH})"
    )
    parser.add_argument(
        "--metadata-path",
        type=str,
        default=str(DEFAULT_METADATA_PATH),
        help=f"Chemin vers metadata.jsonl (défaut: {DEFAULT_METADATA_PATH})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation: ne modifie rien"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Ne pas créer de backup"
    )
    
    args = parser.parse_args()
    
    try:
        result = clean_index(
            index_path=args.index_path,
            metadata_path=args.metadata_path,
            dry_run=args.dry_run,
            backup=not args.no_backup
        )
        
        # Afficher le résultat final
        print("\n" + "=" * 70)
        print("RÉSUMÉ:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        print("=" * 70)
        
        return 0
    
    except Exception as e:
        logger.error(f"Erreur: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
