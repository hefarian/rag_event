"""Tests unitaires pour l'API FastAPI RAG."""
from fastapi.testclient import TestClient
from api.app import app

# Client de test FastAPI
client = TestClient(app)


def test_ask_empty_question():
    """Teste que /ask rejette une question vide avec un code 400."""
    r = client.post('/ask', json={'question': ''})
    assert r.status_code == 400


def test_rebuild_endpoint():
    """Teste que /rebuild démarre sans erreur et retourne un statut."""
    r = client.post('/rebuild')
    assert r.status_code == 200
    assert 'status' in r.json()
