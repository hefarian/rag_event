@echo off
REM Script Batch pour désindexer les événements passés (Version robuste)
REM POC RAG Puls-Events
REM
REM Usage:
REM   clean_old_events.bat                 Pour nettoyage normal
REM   clean_old_events.bat dry-run        Pour simulation

REM Set UTF-8 encoding pour les caractères spéciaux
chcp 65001 >nul

setlocal enabledelayedexpansion

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║   AGENT DE DÉSINDEXATION - Événements Passés            ║
echo ║   POC RAG Puls-Events                                   ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM Déterminer le répertoire du script
set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%scripts\clean_index_robust.py"

echo.
echo 📁 Répertoire: %SCRIPT_DIR%
echo 📝 Script: %PYTHON_SCRIPT%
echo.

REM Vérifier et activer le virtualenv
set "VENV_PATH=%SCRIPT_DIR%.venv"
set "PYTHON_EXE=%VENV_PATH%\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo.
    echo ❌ ERREUR: Virtualenv non trouvé
    echo    Chemin attendu: %VENV_PATH%\Scripts\python.exe
    echo.
    echo    Créez le virtualenv avec:
    echo    python -m venv .venv
    echo    .venv\Scripts\activate
    echo    pip install -r requirements.txt
    exit /b 1
)
echo 🐍 Virtualenv trouvé
echo   ✓ Python: %PYTHON_EXE%
echo.

REM Utiliser Python du virtualenv
set "PYTHON_CMD=%PYTHON_EXE% %PYTHON_SCRIPT%"

REM Ajouter les arguments si spécifiés
if "%1"=="dry-run" (
    echo 🔍 Mode SIMULATION (dry-run)
    set "PYTHON_CMD=!PYTHON_CMD! --dry-run"
)
echo.

REM Vérifier les fichiers d'index
echo 📋 Vérification des fichiers source...

set "INDEX_FILE=%SCRIPT_DIR%vectors\index.faiss"
set "METADATA_FILE=%SCRIPT_DIR%vectors\metadata.jsonl"

if not exist "%INDEX_FILE%" (
    echo.
    echo ❌ ERREUR: Index non trouvé
    echo    Chemin attendu: %INDEX_FILE%
    echo.
    echo    Vérifiez que le fichier existe dans: vectors\index.faiss
    exit /b 1
)
echo   ✓ Index trouvé: %INDEX_FILE%

if not exist "%METADATA_FILE%" (
    echo.
    echo ❌ ERREUR: Métadonnées non trouvées
    echo    Chemin attendu: %METADATA_FILE%
    echo.
    echo    Vérifiez que le fichier existe dans: vectors\metadata.jsonl
    exit /b 1
)
echo   ✓ Metadata trouvées: %METADATA_FILE%

echo.

REM Lancer le script Python
echo 🚀 Lancement du script de nettoyage...
echo.

cd /d "%SCRIPT_DIR%"
%PYTHON_CMD%

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ Erreur lors de l'exécution du script (code: %ERRORLEVEL%)
    exit /b %ERRORLEVEL%
)

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                     ✨ Terminé ✨                       ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

exit /b 0
