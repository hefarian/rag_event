"""Tests unitaires pour l'API FastAPI RAG.

QU'EST-CE QU'UN TEST?
Un test vérifie qu'une fonction fonctionne correctement.
Exemple: "Si je demande 'jazz', j'utilise /ask, après je reçois une réponse valide"

POURQUOI LES TESTS?
- Vérifier que le code fonctionne avant de le déployer
- Éviter de casser du code existant quand on modifie
- Documenter le comportement attendu

COMMENT LANCER LES TESTS?
  pytest tests/test_api.py -v          # Tous les tests ce fichier
  pytest tests/test_api.py::test_ask_empty_question -v  # Un test spécifique
  pytest tests/ -v                      # Tous les tests du projet
"""
from fastapi.testclient import TestClient
from api.app import app

# ============================================================================
# SETUP DU CLIENT DE TEST
# ============================================================================
# TestClient() = Crée un client HTTP simulé pour tester l'API sans la lancer
# C'est utile pour les tests car on n'a pas besoin de docker
client = TestClient(app)


def test_ask_empty_question():
    """Teste que /ask rejette une question vide avec un code 400.
    
    QUOI TESTE-T-ON?
    - Endpoint: POST /ask
    - Entrée: question vide: {'question': ''}
    - Comportement attendu: API retourne code 400 (Bad Request)
    
    POURQUOI?
    Si on permet des questions vides, on réchauffe l'IA sans raison
    
    ERREUR SI FAIL?
    Si ce test échoue: /ask accepte les questions vides (BUG!)
    """
    # Envoyer une requête POST avec question vide
    r = client.post('/ask', json={'question': ''})
    
    # Vérifier que l'API répond 400 (Bad Request, pas 200 OK)
    assert r.status_code == 400


def test_rebuild_endpoint():
    """Teste que /rebuild démarre sans erreur et retourne un statut.
    
    QUOI TESTE-T-ON?
    - Endpoint: POST /rebuild
    - Fonctionnalité: Reconstruire l'index FAISS
    - Comportement attendu: Code 200 + réponse contient clé 'status'
    
    POURQUOI?
    On veut s'assurer que /rebuild ne crash pas et retourne au moins un status
    
    ERREUR SI FAIL?
    Si ce test échoue: /rebuild crash ou ne retourne pas de statut
    """
    # Envoyer une requête pour reconstruire l'index
    r = client.post('/rebuild')
    
    # Vérifier qu'on reçoit 200 OK (pas 500 server error)
    assert r.status_code == 200
    
    # Vérifier que la réponse JSON contient la clé 'status'
    # (Au moins on sait qu'on a une réponse structurée)
    assert 'status' in r.json()
