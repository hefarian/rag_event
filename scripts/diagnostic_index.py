#!/usr/bin/env python3
"""Script de diagnostic pour vérifier l'état de l'index FAISS et des métadonnées."""
import os
import json
import pathlib
from datetime import datetime
from typing import List, Dict

try:
    import faiss
except ImportError:
    print("❌ FAISS not installed. Run: pip install faiss-cpu")
    exit(1)

# Chemins
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

def analyze_index():
    """Analyse l'état de l'index."""
    print("=" * 70)
    print("DIAGNOSTIC DE L'INDEX FAISS")
    print("=" * 70)
    print()
    
    # Check files exist
    print("📋 Fichiers:")
    if not INDEX_PATH.exists():
        print(f"  ❌ Index: {INDEX_PATH} (NOT FOUND)")
        return
    else:
        size_mb = INDEX_PATH.stat().st_size / (1024 * 1024)
        print(f"  ✓ Index: {INDEX_PATH} ({size_mb:.2f} MB)")
    
    if not METADATA_PATH.exists():
        print(f"  ❌ Metadata: {METADATA_PATH} (NOT FOUND)")
        return
    else:
        size_kb = METADATA_PATH.stat().st_size / 1024
        print(f"  ✓ Metadata: {METADATA_PATH} ({size_kb:.2f} KB)")
    
    print()
    
    # Load data
    print("📖 Chargement...")
    try:
        index = load_index(INDEX_PATH)
        print(f"  ✓ Index chargé: {index.ntotal} vecteurs, dim={index.d}")
    except Exception as e:
        print(f"  ❌ Erreur index: {e}")
        return
    
    try:
        metadata = load_metadata(METADATA_PATH)
        print(f"  ✓ Metadata chargées: {len(metadata)} lignes")
    except Exception as e:
        print(f"  ❌ Erreur metadata: {e}")
        return
    
    print()
    
    # Check consistency
    print("🔍 Cohérence:")
    if index.ntotal != len(metadata):
        print(f"  ⚠️  INCOHÉRENCE: {index.ntotal} vectors ≠ {len(metadata)} metadata")
    else:
        print(f"  ✓ Cohérence OK: {index.ntotal} == {len(metadata)}")
    
    print()
    
    # Analyze dates
    print("📅 Analyse des dates:")
    today = datetime.now().date()
    print(f"  Référence: {today}")
    print()
    
    past_events = []
    future_events = []
    invalid_dates = []
    
    for idx, meta in enumerate(metadata):
        date_str = meta.get("date", "")
        title = meta.get("title", f"Event {idx}")[:60]
        
        if not date_str:
            invalid_dates.append((idx, title, "empty"))
            continue
        
        try:
            # Parse date
            if "T" in date_str:
                dt_str = date_str.split("+")[0].split("Z")[0]
                date_obj = datetime.fromisoformat(dt_str).date()
            else:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            if date_obj < today:
                days_ago = (today - date_obj).days
                past_events.append((idx, title, date_obj, days_ago))
            else:
                days_ahead = (date_obj - today).days
                future_events.append((idx, title, date_obj, days_ahead))
                
        except Exception as e:
            invalid_dates.append((idx, title, f"parse error: {e}"))
    
    print(f"  📍 Événements futurs: {len(future_events)}")
    if future_events:
        # Show next 5
        sorted_future = sorted(future_events, key=lambda x: x[2])[:5]
        for idx, title, date, days in sorted_future:
            print(f"    • [{idx}] {title}")
            print(f"      Date: {date} (+{days} days)")
    
    print()
    print(f"  ⏰ Événements passés: {len(past_events)}")
    if past_events:
        # Show oldest 5
        sorted_past = sorted(past_events, key=lambda x: x[2], reverse=False)[:5]
        for idx, title, date, days in sorted_past:
            print(f"    • [{idx}] {title}")
            print(f"      Date: {date} ({days} days ago) ⚠️  À NETTOYER!")
    
    print()
    if invalid_dates:
        print(f"  ⚠️  Dates invalides: {len(invalid_dates)}")
        for idx, title, reason in invalid_dates[:3]:
            print(f"    • [{idx}] {title} ({reason})")
        if len(invalid_dates) > 3:
            print(f"    ... et {len(invalid_dates) - 3} autres")
    
    print()
    print("=" * 70)
    print("RECOMMANDATIONS")
    print("=" * 70)
    
    if len(past_events) > 0:
        print(f"⚠️  {len(past_events)} événements passés détectés!")
        print()
        print("ACTIONS:")
        print("  1. Vérifier en mode simulation:")
        print("     .\clean_old_events.ps1 -DryRun")
        print()
        print("  2. Si OK, lancer le nettoyage:")
        print("     .\clean_old_events.ps1")
    else:
        print("✓ Aucun événement passé détecté")
    
    if index.ntotal != len(metadata):
        print()
        print("⚠️  INCOHÉRENCE INDEX/METADATA!")
        print()
        print("  Pour corriger:")
        print("    1. Sauvegarder données: copy vectors metadata.jsonl backup_metadata.jsonl")
        print("    2. Rebuilder l'index: python scripts/build_index.py")
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    try:
        analyze_index()
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
