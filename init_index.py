#!/usr/bin/env python3
"""
Script d'initialisation - Puls-Events RAG Index Builder

APPROCHE:
---------
1. Filtre les événements source pour garder uniquement les dates 2026+
2. Génère un fichier de travail nettoyé (evenements-2026plus.json)
3. Indexe ce dataset nettoyé avec FAISS
4. Sauvegarde l'index (vectors/index.faiss) et métadonnées (vectors/metadata.jsonl)

PROBLÈME RÉSOLU:
----------------
Avant: Index contenait 90% d'événements 2024 → Requête "demain" retournait des événements passés
Après: Index contient 100% d'événements 2026+ → Requête "demain" retourne des événements futurs pertinents

USAGE:
------
  python init_index.py                    # Filtre + indexe tout d'un coup
  python init_index.py --filter-only      # Génère juste evenements-2026plus.json
  python init_index.py --index-only       # Indexe depuis fichier filtré existant
  python init_index.py --input-file FILE  # Utilise un fichier source custom
"""

import json
import pathlib
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chemins par défaut
DATAIN_DIR = pathlib.Path("DATAIN")
DEFAULT_INPUT = DATAIN_DIR / "evenements-publics-openagenda.json"
FILTERED_OUTPUT = DATAIN_DIR / "evenements-2026plus.json"
VECTORS_DIR = pathlib.Path("vectors")


def filter_events(
    input_path: pathlib.Path,
    output_path: pathlib.Path,
    min_year: int = 2026
) -> int:
    """
    Filtre les événements pour garder uniquement ceux à partir de min_year.
    
    POURQUOI CE FILTRE?
    Le fichier JSON OpenAgenda contient 90% d'événements 2023-2024 (passés)
    Si on indexe tout:
    - Q: "Demain y-a-t-il un événement?"
    - R: "Oui: Concert le 15 janvier 2024" (PASSÉ!)
    
    Avec le filtre 2026+:
    - Q: "Demain?"
    - R: "Jazz Night le 15 avril 2026" (FUTUR!)
    
    Args:
        input_path: Chemin du fichier JSON source (1M+ événements bruts)
        output_path: Chemin du fichier filtré (couche)
        min_year: Année minimale à conserver (défaut: 2026)
    
    Returns:
        Nombre d'événements sauvegardés (après filtre)
    """
    logger.info("=" * 70)
    logger.info(f"ÉTAPE 1: Filtrage des événements ({min_year}+)")
    logger.info("=" * 70)
    
    # Vérifier que le fichier source existe
    if not input_path.exists():
        logger.error(f"Fichier source non trouvé: {input_path}")
        return 0
    
    # Charger tous les événements du fichier JSON
    logger.info(f"Lecture du fichier source: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        all_events = json.load(f)
    
    logger.info(f"  Total événements: {len(all_events):,}")
    
    # Filtrer pour garder uniquement les événements 2026+
    filtered = []
    # OpenAgenda peut avoir différents noms de champs de date
    date_fields = ['date', 'firstdate_begin', 'startDate', 'begin']
    
    for i, evt in enumerate(all_events):
        # Afficher la progression tous les 100k événements
        if (i + 1) % 100000 == 0:
            logger.info(f"  Traitement: {i + 1:,} / {len(all_events):,}")
        
        try:
            # Chercher un champ date selon la structure OpenAgenda
            # Essayer chaque nom possible de champ de date
            date_str = None
            for field in date_fields:
                if field in evt and evt[field]:
                    date_str = str(evt[field])
                    break
            
            # Si on a une date, vérifier que c'est 2026+
            if date_str:
                # Extraire l'année: "2026-04-15..." → "2026"
                year = int(date_str[:4])
                if year >= min_year:
                    # C'est bon! On le garde
                    filtered.append(evt)
        except Exception as e:
            # Si une erreur d'extraction de date, juste passer
            logger.debug(f"Erreur extraction date event {i}: {e}")
            pass
    
    logger.info(f"✓ Événements conservés: {len(filtered):,}")
    
    # Statistiques
    year_distribution = {}
    for evt in filtered:
        date_str = None
        for field in date_fields:
            if field in evt and evt[field]:
                date_str = str(evt[field])
                break
        if date_str:
            year = int(date_str[:4])
            year_distribution[year] = year_distribution.get(year, 0) + 1
    
    logger.info("  Distribution par année:")
    for year in sorted(year_distribution.keys()):
        count = year_distribution[year]
        pct = (count / len(filtered)) * 100
        logger.info(f"    {year}: {count:6,} ({pct:5.1f}%)")
    
    # Sauvegarder le fichier filtré
    logger.info(f"Sauvegarde: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered, f, ensure_ascii=False, indent=1)
    
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"✓ Fichier filtré sauvegardé: {file_size_mb:.1f} MB")
    
    return len(filtered)


def build_index_from_filtered(filtered_path: pathlib.Path) -> int:
    """
    Construit l'index FAISS à partir du fichier filtré.
    
    Args:
        filtered_path: Chemin du fichier filtré (evenements-2026plus.json)
    
    Returns:
        Nombre de vecteurs créés
    """
    logger.info("\n" + "=" * 70)
    logger.info("ÉTAPE 2: Construction de l'index FAISS")
    logger.info("=" * 70)
    
    try:
        from scripts.build_index import build_index
        
        logger.info(f"Indexation: {filtered_path}")
        num_vectors = build_index(
            data_path=str(filtered_path),
            max_events=None,  # Indexer TOUS les événements du fichier filtré
        )
        
        logger.info(f"✓ Index créé: {num_vectors:,} vecteurs")
        
        # Vérifier les fichiers de sortie
        index_file = VECTORS_DIR / "index.faiss"
        metadata_file = VECTORS_DIR / "metadata.jsonl"
        
        if index_file.exists() and metadata_file.exists():
            index_size_mb = index_file.stat().st_size / (1024 * 1024)
            metadata_size_mb = metadata_file.stat().st_size / (1024 * 1024)
            logger.info(f"  Fichiers générés:")
            logger.info(f"    index.faiss: {index_size_mb:.1f} MB")
            logger.info(f"    metadata.jsonl: {metadata_size_mb:.1f} MB")
        
        return num_vectors
    
    except ImportError as e:
        logger.error(f"Erreur import build_index: {e}")
        logger.error("Vérifiez que scripts/build_index.py existe")
        return 0
    except Exception as e:
        logger.error(f"Erreur lors de la construction: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Initialiser l'index FAISS Puls-Events (données 2026+)"
    )
    parser.add_argument(
        '--filter-only',
        action='store_true',
        help="Générer juste le fichier filtré (sans indexer)"
    )
    parser.add_argument(
        '--index-only',
        action='store_true',
        help="Indexer depuis fichier filtré existant"
    )
    parser.add_argument(
        '--input-file',
        type=pathlib.Path,
        default=DEFAULT_INPUT,
        help=f"Fichier source (défaut: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        '--min-year',
        type=int,
        default=2026,
        help="Année minimale pour filtrage (défaut: 2026)"
    )
    
    args = parser.parse_args()
    
    logger.info("\n🚀 INITIALISATION INDEX PULS-EVENTS")
    logger.info(f"   Mode: {'--filter-only' if args.filter_only else '--index-only' if args.index_only else 'complet'}")
    logger.info(f"   Input: {args.input_file}")
    logger.info(f"   Min year: {args.min_year}")
    
    try:
        # Étape 1: Filtrage
        if not args.index_only:
            if not args.input_file.exists():
                logger.error(f"❌ Fichier source introuvable: {args.input_file}")
                return 1
            
            num_filtered = filter_events(
                input_path=args.input_file,
                output_path=FILTERED_OUTPUT,
                min_year=args.min_year
            )
            
            if num_filtered == 0:
                logger.error("❌ Aucun événement filtré. Vérifiez le fichier source.")
                return 1
            
            if args.filter_only:
                logger.info("\n✓ Filtrage terminé. Fichier prêt pour indexation.")
                logger.info(f"  Commande suivante: python init_index.py --index-only")
                return 0
        
        # Étape 2: Indexation
        if not args.filter_only:
            if not FILTERED_OUTPUT.exists():
                logger.error(f"❌ Fichier filtré introuvable: {FILTERED_OUTPUT}")
                logger.error("   Exécutez d'abord: python init_index.py --filter-only")
                return 1
            
            num_vectors = build_index_from_filtered(FILTERED_OUTPUT)
            
            if num_vectors == 0:
                logger.error("❌ Erreur lors de la construction de l'index.")
                return 1
        
        logger.info("\n" + "=" * 70)
        logger.info("✓ SUCCÈS - Index Puls-Events prêt!")
        logger.info("=" * 70)
        logger.info("Prochaines étapes:")
        logger.info("  1. Démarrer les services: docker-compose up -d")
        logger.info("  2. Tester l'API: curl -X POST http://localhost:8000/ask ...")
        logger.info("  3. Accéder à Streamlit: http://localhost:8501")
        
        return 0
    
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Interruption de l'utilisateur")
        return 130
    except Exception as e:
        logger.error(f"\n❌ Erreur non gérée: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
