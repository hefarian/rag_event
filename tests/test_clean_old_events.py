#!/usr/bin/env python3
"""Script de test pour vérifier que l'agent clean_old_events fonctionne correctement."""
import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, str(os.path.dirname(__file__)))

# Test import
print("=" * 70)
print("TEST : Import du module clean_old_events")
print("=" * 70)

try:
    from scripts.clean_old_events import (
        parse_date,
        load_metadata,
        load_index,
        identify_old_events,
        clean_index
    )
    print("✓ Tous les imports sont OK")
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)

# Test 1: parse_date
print("\n" + "=" * 70)
print("TEST 1 : Parsing des dates")
print("=" * 70)

test_dates = [
    ("2025-03-15T20:00:00+02:00", "ISO 8601 avec timezone"),
    ("2026-04-11", "Format simple"),
    ("2024-12-25T10:30:00Z", "ISO 8601 avec Z"),
    ("", "Date vide"),
    (None, "None"),
]

for date_str, description in test_dates:
    result = parse_date(date_str)
    status = "✓" if result or date_str in ("", None) else "❌"
    print(f"  {status} {description}: {date_str} -> {result}")

# Test 2: Vérifier que les fichiers d'index existent
print("\n" + "=" * 70)
print("TEST 2 : Fichiers d'index")
print("=" * 70)

from pathlib import Path

index_path = Path("vectors/index.faiss")
metadata_path = Path("vectors/metadata.jsonl")

print(f"  Index: {index_path}")
print(f"    -> {'✓ Existe' if index_path.exists() else '❌ N\\'existe pas'}")

print(f"  Métadonnées: {metadata_path}")
print(f"    -> {'✓ Existe' if metadata_path.exists() else '❌ N\\'existe pas'}")

# Test 3: Charger les métadonnées (si elles existent)
if metadata_path.exists():
    print("\n" + "=" * 70)
    print("TEST 3 : Chargement des métadonnées")
    print("=" * 70)
    
    try:
        metadata = load_metadata(str(metadata_path))
        print(f"✓ Métadonnées chargées: {len(metadata)} lignes")
        
        if metadata:
            print("\n  Premiers éléments:")
            for i, m in enumerate(metadata[:3]):
                print(f"    [{i+1}] {m.get('title', 'N/A')} - {m.get('date', 'N/A')}")
                
            # Test identify_old_events
            print("\n" + "=" * 70)
            print("TEST 4 : Identification des événements passés")
            print("=" * 70)
            
            try:
                indices_old, indices_keep = identify_old_events(metadata)
                print(f"✓ Analyse OK")
                print(f"  • Événements passés: {len(indices_old)}")
                print(f"  • Événements futurs: {len(indices_keep)}")
                
                if indices_old:
                    print(f"\n  Exemples d'événements à supprimer:")
                    for idx in indices_old[:3]:
                        m = metadata[idx]
                        print(f"    • {m.get('title', 'N/A')} ({m.get('date', 'N/A')})")
                        
            except Exception as e:
                print(f"❌ Erreur: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 70)
print("✨ Tests complétés")
print("=" * 70)
