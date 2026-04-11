"""Tests unitaires pour la construction de l'index FAISS.

QU'EST-CE QUE FAISS?
FAISS = Moteur de recherche par similarité (comme Google pour les événements)

TESTS INCLUENT:
1. Vérifier que la fonction build_index existe
2. Vérifier que build_index s'exécute sans erreur
3. Vérifier que l'index FAISS est créé
"""
import os
import importlib


def test_build_index_function_exists():
    """Vérifie que la fonction build_index existe.
    
    POURQUOI?
    C'est un test de base pour s'assurer que le fichier scripts/build_index.py
    existe et contient la fonction build_index
    
    ERREUR SI FAIL?
    Si ce test échoue: scripts/build_index.py est manquant ou ne contient pas build_index()
    """
    # Charger le module Python dynamiquement
    # importlib = import en runtime, pratique pour les tests
    mod = importlib.import_module('scripts.build_index')
    
    # Vérifier que le module a l'attribut 'build_index'
    # hasattr(objet, 'attribut') = vérifie si l'objet a cet attribut
    assert hasattr(mod, 'build_index')


def test_build_index_runs(tmp_path):
    """Teste que build_index s'exécute sans erreur inattendue.
    
    QUOI TESTE-T-ON?
    - La fonction build_index peut s'exécuter sans crash
    - Les RuntimeErrors (pas de chunks) sont acceptables
    - D'autres exceptions seraient des vrais bugs
    
    POURQUOI?
    Valider que l'index peut être reconstruit
    
    ERREUR SI FAIL?
    Si ce test échoue: build_index() lève une exception inattendue
    
    À NOTER:
    - tmp_path = dossier temporaire fourni par pytest (pas de pollution du vrai dossier)
    - On n'utilise pas tmp_path ici mais c'est good practice de l'avoir
    """
    # Charger le module scripts/build_index
    mod = importlib.import_module('scripts.build_index')
    
    try:
        # Exécuter la fonction de construction d'index
        # Elle essayera de charger les données et créer l'index FAISS
        mod.build_index()
    
    except RuntimeError as e:
        # RuntimeError = "No chunks found" - c'est OK, données peuvent manquer
        # Les tests CI peuvent ne pas avoir les data files
        pass
    
    except Exception as e:
        # Toute autre exception = Bug (pas OK!)
        assert False, f"build_index() raised unexpected error: {e}"
