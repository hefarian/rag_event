#!/usr/bin/env python3
"""Vérifier si le nettoyage a vraiment fonctionné et réparer si nécessaire."""
import json
import pathlib
from datetime import datetime
from typing import List, Dict

try:
    import faiss
    import numpy as np
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

VECTORS_DIR = pathlib.Path("vectors")
INDEX_PATH = VECTORS_DIR / "index.faiss"
METADATA_PATH = VECTORS_DIR / "metadata.jsonl"

def load_metadata(path: str) -> List[Dict]:
    """Charge les métadonnées."""
    metadata = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))
    return metadata

def load_index(path: str):
    """Charge l'index FAISS."""
    return faiss.read_index(str(path))

def parse_date(date_str: str) -> datetime:
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

def verify_cleanup():
    """Vérifie l'état de l'index après nettoyage."""
    print("=" * 70)
    print("VÉRIFICATION DU NETTOYAGE")
    print("=" * 70)
    print()
    
    # Load
    print("📖 Chargement...")
    try:
        index = load_index(INDEX_PATH)
        metadata = load_metadata(METADATA_PATH)
        print(f"  ✓ Index: {index.ntotal} vecteurs")
        print(f"  ✓ Metadata: {len(metadata)} lignes")
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False
    
    print()
    
    # Check consistency
    if index.ntotal != len(metadata):
        print(f"⚠️  INCOHÉRENCE: {index.ntotal} ≠ {len(metadata)}")
        print("   Le nettoyage a peut-être échoué")
        return False
    
    # Check for past events
    print("📅 Vérification des dates...")
    today = datetime.now().date()
    past_events = []
    
    for idx, meta in enumerate(metadata):
        date_str = meta.get("date", "")
        date_obj = parse_date(date_str)
        
        if date_obj:
            event_date = date_obj.date()
            if event_date < today:
                title = meta.get("title", "")[:50]
                days_ago = (today - event_date).days
                past_events.append({
                    "idx": idx,
                    "title": title,
                    "date": date_obj,
                    "days_ago": days_ago
                })
    
    print()
    if past_events:
        print(f"⚠️  {len(past_events)} ÉVÉNEMENTS PASSÉS TROUVÉS!")
        print()
        for evt in sorted(past_events, key=lambda x: x['days_ago'], reverse=True)[:5]:
            print(f"  [{evt['idx']}] {evt['title']}")
            print(f"      Date: {evt['date']} ({evt['days_ago']} days ago)")
        
        if len(past_events) > 5:
            print(f"  ... et {len(past_events) - 5} autres")
        
        print()
        print("❌ LE NETTOYAGE N'A PAS FONCTIONNÉ!")
        print()
        print("SOLUTION:")
        print("  1. Sauvegarder l'index actuel:")
        print("     copy vectors\\index.faiss vectors\\index.faiss.broken")
        print()
        print("  2. Rebuild complètement:")
        print("     python scripts/build_index.py")
        print()
        print("  3. Redémarrer l'API:")
        print("     docker-compose restart api")
        
        return False
    else:
        print("✅ AUCUN ÉVÉNEMENT PASSÉ DÉTECTÉ - NETTOYAGE OK!")
        return True

if __name__ == "__main__":
    success = verify_cleanup()
    exit(0 if success else 1)
