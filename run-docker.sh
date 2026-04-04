#!/bin/bash

# Script de démarrage rapide pour Puls-Events RAG sur Linux/Mac
# Usage: ./run-docker.sh

set -e

echo "============================================"
echo " Puls-Events RAG - Docker Deployment"
echo "============================================"
echo ""

# Vérifier si Docker est installé
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker n'est pas installé"
    exit 1
fi

echo "[1/4] Vérification de Docker..."
docker --version

# Vérifier Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose n'est pas installé"
    exit 1
fi

echo "[2/4] Vérification de Docker Compose..."
docker-compose --version

# Vérifier le fichier .env
echo "[3/4] Vérification de la configuration..."
if [ ! -f .env ]; then
    echo "WARNING: Fichier .env non trouvé"
    echo "Copie de .env.example -> .env"
    cp .env.example .env
    echo "NOTE: Veuillez éditer .env avec vos clés API"
fi

echo "[4/4] Construction et démarrage des services..."
docker-compose up -d

echo ""
echo "Vérification du statut des services..."
docker-compose ps

echo ""
echo "============================================"
echo " Puls-Events RAG est maintenant disponible!"
echo "============================================"
echo ""
echo "URLs d'accès:"
echo "  - Interface Streamlit: http://localhost:8501"
echo "  - API FastAPI (Swagger): http://localhost:8000/docs"
echo "  - API Santé: http://localhost:8000/health"
echo ""
echo "Commandes utiles:"
echo "  - Arrêter: docker-compose down"
echo "  - Voir les logs (API): docker-compose logs -f api"
echo "  - Voir les logs (UI): docker-compose logs -f streamlit"
echo "  - Reconstruire l'index: docker-compose exec api python scripts/build_index.py"
echo ""
