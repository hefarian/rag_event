"""Pytest configuration and fixtures."""
import sys
import os

# Ajouter la racine du projet au path Python pour les imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
