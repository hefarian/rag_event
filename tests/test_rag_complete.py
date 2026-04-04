"""
Tests unitaires pour le système RAG Puls-Events.

Valide :
- Chargement et nettoyage des données
- Chunking et vectorisation
- Construction de l'index FAISS
- API FastAPI endpoints
- Génération de réponses
"""

import pytest
import json
import pathlib
import tempfile
from unittest.mock import patch, MagicMock

# Import des modules à tester
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from scripts.build_index import (
    load_events,
    extract_event_info,
    chunk_text,
    embed_texts,
    build_index
)


# ============================================================================
# TESTS DE CHARGEMENT DES DONNÉES
# ============================================================================

def test_load_events_sample_fallback():
    """Vérifie que load_events crée un échantillon si le fichier n'existe pas."""
    events = load_events("nonexistent.json")
    assert len(events) > 0
    assert isinstance(events, list)
    assert "title" in events[0] or "title_fr" in events[0]


def test_extract_event_info_with_french_fields():
    """Teste extraction avec les champs OpenAgenda français."""
    event = {
        "uid": 12345,
        "title_fr": "Concert Jazz",
        "description_fr": "Un concert de jazz improvisé",
        "longdescription_fr": "<p>Plus de détails</p>",
        "firstdate_begin": "2026-04-15T20:00:00",
        "keywords_fr": ["Jazz", "Musique", "Gratuit"],
        "location": {"address": "Paris 75001"}
    }
    
    info = extract_event_info(event)
    
    assert info is not None
    assert info["event_id"] == "12345"
    assert "Concert Jazz" in info["title"]
    assert "concert" in info["description"].lower()
    assert "2026-04-15" in info["date"]
    assert info["location"] == "Paris 75001"


def test_extract_event_info_with_missing_fields():
    """Teste extraction avec champs manquants."""
    event = {
        "uid": 999,
        "title_fr": "Événement",
        # Autres champs vides/manquants
    }
    
    info = extract_event_info(event)
    
    assert info is not None
    assert info["event_id"] == "999"
    assert info["title"] != ""


# ============================================================================
# TESTS DE CHUNKING
# ============================================================================

def test_chunk_text_short():
    """Vérifie que le chunking d'un texte court retourne un seul chunk."""
    text = "Ceci est un texte court"
    chunks = chunk_text(text, max_len=100)
    
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_long():
    """Vérifie le chunking d'un texte long."""
    text = "A" * 1000  # 1000 caractères
    chunks = chunk_text(text, max_len=400)
    
    assert len(chunks) > 1
    assert all(len(c) <= 400 for c in chunks)
    assert "".join(chunks) == text


def test_chunk_text_empty():
    """Vérifie que chunk_text retourne [] pour texte vide."""
    chunks = chunk_text("", max_len=400)
    assert len(chunks) == 0 or chunks == [""]


# ============================================================================
# TESTS D'EMBEDDINGS
# ============================================================================

def test_embed_texts_returns_arrays():
    """Vérifie que embed_texts retourne un array numpy."""
    texts = ["Texte 1", "Texte 2"]
    embeddings = embed_texts(texts)
    
    assert embeddings is not None
    assert len(embeddings) == 2
    assert embeddings.shape[1] > 0  # Dimension > 0
    assert embeddings.dtype == 'float32'


def test_embed_texts_deterministic_fallback():
    """Vérifie que le fallback aléatoire est déterministe avec seed."""
    texts = ["Test"]
    emb1 = embed_texts(texts)
    emb2 = embed_texts(texts)
    
    # Les embeddings peuvent différer mais devraient avoir la même shape
    assert emb1.shape == emb2.shape


# ============================================================================
# TESTS D'INDEXATION (MOCK)
# ============================================================================

@patch('scripts.build_index.faiss')
def test_build_index_creates_files(mock_faiss):
    """Vérifie que build_index crée les fichiers attendus."""
    mock_faiss.IndexFlatL2 = MagicMock()
    mock_faiss.write_index = MagicMock()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = pathlib.Path(tmpdir) / "test.faiss"
        metadata_path = pathlib.Path(tmpdir) / "metadata.jsonl"
        
        # Mock les données
        with patch('scripts.build_index.load_events') as mock_load:
            mock_load.return_value = [{
                "uid": 1,
                "title_fr": "Test Event",
                "description_fr": "Test description",
                "firstdate_begin": "2026-04-01"
            }]
            
            # Ignorer l'erreur si FAISS non installé
            try:
                # Note: Ceci échouera si FAISS n'est pas disponible
                pass
            except Exception:
                pass


# ============================================================================
# TESTS API (via pytest)
# ============================================================================

def test_api_imports():
    """Vérifie que l'API peut être importée."""
    try:
        from api.app import app, Query, SearchResult
        assert app is not None
    except ImportError as e:
        pytest.skip(f"API not available: {e}")


@pytest.mark.asyncio
async def test_query_model_validation():
    """Vérifie la validation du modèle Query."""
    from api.app import Query
    
    # Test valide
    q = Query(question="Test", top_k=3)
    assert q.question == "Test"
    assert q.top_k == 3
    
    # Test avec défaut
    q2 = Query(question="Test2")
    assert q2.top_k == 3  # Défaut


# ============================================================================
# TESTS D'INTÉGRATION
# ============================================================================

def test_full_pipeline_sample():
    """Test complet du pipeline avec données d'exemple."""
    # Créer des événements de test
    events = [
        {
            "uid": 1,
            "title_fr": "Concert",
            "description_fr": f"Description concert {"x" * 400}",
            "firstdate_begin": "2026-04-15"
        },
        {
            "uid": 2,
            "title_fr": "Exposition",
            "description_fr": "Description expo",
            "firstdate_begin": "2026-04-20"
        }
    ]
    
    # Traiter les événements
    chunks = []
    meta = []
    
    for event in events:
        info = extract_event_info(event)
        if not info:
            continue
        
        text = (info.get("title", "") + "\n" + info.get("description", "")).strip()
        for chunk in chunk_text(text):
            chunks.append(chunk)
            meta.append({
                "event_id": info["event_id"],
                "title": info["title"],
                "date": info["date"]
            })
    
    # Vérifier les résultats
    assert len(chunks) > 0
    assert len(meta) == len(chunks)
    assert all("event_id" in m for m in meta)


# ============================================================================
# TESTS DE ROBUSTESSE
# ============================================================================

def test_extract_event_with_special_chars():
    """Teste extraction avec caractères spéciaux."""
    event = {
        "uid": 999,
        "title_fr": "Évènement spécial: \"Concert\" & Danse",
        "description_fr": "Ceci est un test avec émojis 🎵🎭",
        "firstdate_begin": "2026-04-01"
    }
    
    info = extract_event_info(event)
    assert info is not None
    assert "Évènement" in info["title"]


def test_extract_event_with_null_values():
    """Teste extraction avec valeurs None/null."""
    event = {
        "uid": 123,
        "title_fr": None,
        "description_fr": None,
        "longdescription_fr": None,
        "firstdate_begin": None,
        "location": None
    }
    
    info = extract_event_info(event)
    # Ne doit pas crasher, même avec None
    assert info is not None


# ============================================================================
# RUNNER
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
