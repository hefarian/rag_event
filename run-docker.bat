@echo off
REM Script de démarrage rapide pour Puls-Events RAG sur Windows
REM Usage: run-docker.bat

echo ============================================
echo  Puls-Events RAG - Docker Deployment
echo ============================================
echo.

REM Vérifier si Docker est installé
docker --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker n'est pas installé ou pas dans le PATH
    exit /b 1
)

echo [1/4] Vérification de Docker Compose...
docker-compose --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker Compose n'est pas installé
    exit /b 1
)

echo [2/4] Vérification du fichier .env...
if not exist .env (
    echo WARNING: Fichier .env non trouvé
    echo Copie de .env.example -> .env
    copy .env.example .env
    echo NOTE: Veuillez éditer .env avec vos clés API
)

echo [3/4] Construction des images...
docker-compose build
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: La construction a échoué
    exit /b 1
)

echo [4/4] Démarrage des services...
docker-compose up -d

echo.
echo ============================================
echo  Services en cours de démarrage...
echo ============================================
echo.

REM Attendre un peu avant de vérifier
timeout /t 5 /nobreak

echo Vérification du statut des services...
docker-compose ps

echo.
echo ============================================
echo  Puls-Events RAG est maintenant disponible!
echo ============================================
echo.
echo URLs d'accès:
echo   - Interface Streamlit: http://localhost:8501
echo   - API FastAPI (Swagger): http://localhost:8000/docs
echo   - API Santé: http://localhost:8000/health
echo.
echo Commandes utiles:
echo   - Arrêter: docker-compose down
echo   - Voir les logs (API): docker-compose logs -f api
echo   - Voir les logs (UI): docker-compose logs -f streamlit
echo.
pause
