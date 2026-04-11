@echo off
REM Script Batch pour désindexer les événements passés
REM POC RAG Puls-Events
REM
REM Usage:
REM   clean_old_events.bat                 Pour nettoyage normal
REM   clean_old_events.bat dry-run        Pour simulation
REM   clean_old_events.bat dry-run no-backup

setlocal enabledelayedexpansion

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║   AGENT DE DÉSINDEXATION - Événements Passés            ║
echo ║   POC RAG Puls-Events                                   ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM Déterminer le répertoire du script
set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%scripts\clean_old_events.py"

REM Construire la commande Python
set "PYTHON_CMD=python %PYTHON_SCRIPT%"

REM Ajouter les arguments
if "%1"=="dry-run" (
    echo 🔍 Mode SIMULATION (dry-run)
    set "PYTHON_CMD=!PYTHON_CMD! --dry-run"
)

if "%2"=="no-backup" (
    echo ⚠ Les backups NE seront PAS créés
    set "PYTHON_CMD=!PYTHON_CMD! --no-backup"
)

echo.
echo 📁 Répertoire: %SCRIPT_DIR%
echo 📝 Script: %PYTHON_SCRIPT%
echo.

REM Vérifier que le script existe
if not exist "%PYTHON_SCRIPT%" (
    echo ❌ Erreur: Le script %PYTHON_SCRIPT% n'existe pas
    exit /b 1
)

REM Vérifier les fichiers d'index
if not exist "%SCRIPT_DIR%vectors\index.faiss" (
    echo ❌ Erreur: Index non trouvé (vectors/index.faiss)
    exit /b 1
)

if not exist "%SCRIPT_DIR%vectors\metadata.jsonl" (
    echo ❌ Erreur: Métadonnées non trouvées (vectors/metadata.jsonl)
    exit /b 1
)

echo ✓ Fichiers source trouvés
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
