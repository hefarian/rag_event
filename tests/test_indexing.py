"""Tests unitaires pour la construction de l'index FAISS."""
import os
import importlib


def test_build_index_function_exists():
    """Vérifie que la fonction build_index existe."""
    mod = importlib.import_module('scripts.build_index')
    assert hasattr(mod, 'build_index')


def test_build_index_runs(tmp_path):
    """Teste que build_index s'exécute sans erreur inattendue.
    Crée l'index vectors/ uniquement si faiss est disponible.
    """
    # Importer et exécuter build_index
    mod = importlib.import_module('scripts.build_index')
    try:
        mod.build_index()
    except RuntimeError:
        # Acceptable si aucun chunk trouvé
        pass
    except Exception:
        # Le script ne doit pas lever d'exceptions inattendues
        assert False
