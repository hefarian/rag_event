# Script PowerShell pour désindexer les événements passés
# Usage:
#   .\clean_old_events.ps1                    # Nettoyage normal avec backup
#   .\clean_old_events.ps1 -DryRun            # Mode simulation
#   .\clean_old_events.ps1 -NoBackup          # Sans créer de backup
#   .\clean_old_events.ps1 -DryRun -Verbose

param(
    [switch]$DryRun = $false,
    [switch]$NoBackup = $false,
    [switch]$Verbose = $false,
    [string]$IndexPath = "vectors/index.faiss",
    [string]$MetadataPath = "vectors/metadata.jsonl"
)

# Couleurs pour le terminal
$Colors = @{
    Info    = 'Cyan'
    Success = 'Green'
    Warning = 'Yellow'
    Error   = 'Red'
}

function Write-Log {
    param([string]$Message, [string]$Level = 'Info')
    $Color = $Colors[$Level]
    Write-Host $Message -ForegroundColor $Color
}

function Test-VirtualEnv {
    # Vérifier si un venv existe
    if ((Test-Path ".venv\Scripts\Activate.ps1") -or (Test-Path "venv\Scripts\Activate.ps1")) {
        return $true
    }
    return $false
}

function Activate-VirtualEnv {
    if (Test-Path ".venv\Scripts\Activate.ps1") {
        Write-Log "Activation du virtualenv (.venv)..." -Level Info
        & ".venv\Scripts\Activate.ps1"
    } elseif (Test-Path "venv\Scripts\Activate.ps1") {
        Write-Log "Activation du virtualenv (venv)..." -Level Info
        & "venv\Scripts\Activate.ps1"
    } else {
        Write-Log "⚠ Aucun virtualenv trouvé (.venv ou venv)" -Level Warning
        return $false
    }
    return $true
}

# ==================== SCRIPT PRINCIPAL ====================

Write-Log "╔══════════════════════════════════════════════════════════╗" -Level Success
Write-Log "║   AGENT DE DÉSINDEXATION - Événements Passés            ║" -Level Success
Write-Log "║   POC RAG Puls-Events                                   ║" -Level Success
Write-Log "╚══════════════════════════════════════════════════════════╝" -Level Success

# Vérifier la position
$ProjectRoot = Get-Location
Write-Log "📁 Répertoire: $ProjectRoot" -Level Info

# Activer le virtualenv (optionnel mais recommandé)
$HasVenv = Test-VirtualEnv
if ($HasVenv) {
    Activate-VirtualEnv
    $Python = "python"
} else {
    Write-Log "⚠ Pas de virtualenv activé" -Level Warning
    $Python = "python"
}

# Construire la commande Python
$PythonScript = "scripts\clean_old_events.py"
$PythonCmd = @($PythonScript)

Write-Log "📝 Vérification du script..." -Level Info
if (-not (Test-Path $PythonScript)) {
    Write-Log "❌ Erreur: Le script $PythonScript n'existe pas" -Level Error
    exit 1
}
Write-Log "✓ Script trouvé: $PythonScript" -Level Success

# Ajouter les arguments
$PythonCmd += "--index-path", $IndexPath
$PythonCmd += "--metadata-path", $MetadataPath

if ($DryRun) {
    Write-Log "🔍 Mode SIMULATION (dry-run)" -Level Warning
    $PythonCmd += "--dry-run"
}

if ($NoBackup) {
    Write-Log "⚠ Les backups seront créés" -Level Warning
} else {
    Write-Log "💾 Les backups seront créés" -Level Info
}

# Vérifier les fichiers d'index
Write-Log "📋 Vérification des fichiers source..." -Level Info
if (-not (Test-Path $IndexPath)) {
    Write-Log "❌ Index non trouvé: $IndexPath" -Level Error
    exit 1
}
if (-not (Test-Path $MetadataPath)) {
    Write-Log "❌ Métadonnées non trouvées: $MetadataPath" -Level Error
    exit 1
}
Write-Log "✓ Fichiers source trouvés" -Level Success

# Afficher les informations de l'index actuel
Write-Log "📊 Informations actuelles:" -Level Info
try {
    $MetadataCount = (Get-Content $MetadataPath | Measure-Object -Line).Lines
    Write-Log "  • Métadonnées: $MetadataCount lignes" -Level Info
} catch {
    Write-Log "  ⚠ Impossible de lire les métadonnées" -Level Warning
}

# Lancer le script Python
Write-Log "🚀 Lancement du script de nettoyage..." -Level Success
Write-Log "Commande: $Python $($PythonCmd -join ' ')" -Level Info
Write-Host ""

& python @PythonCmd
$ExitCode = $?

if ($ExitCode) {
    Write-Log "✅ Script exécuté avec succès" -Level Success
} else {
    Write-Log "❌ Erreur lors de l'exécution du script" -Level Error
    exit 1
}

# Afficher les nouvelles infos après nettoyage
if (-not $DryRun) {
    Write-Log "📊 Vérification post-nettoyage..." -Level Info
    try {
        $NewMetadataCount = (Get-Content $MetadataPath | Measure-Object -Line).Lines
        Write-Log "  • Nouvelles métadonnées: $NewMetadataCount lignes" -Level Success
        if ($MetadataCount -gt 0) {
            $Removed = $MetadataCount - $NewMetadataCount
            Write-Log "  • Événements supprimés: $Removed" -Level Success
        }
    } catch {
        Write-Log "  ⚠ Impossible de lire les métadonnées" -Level Warning
    }
}

Write-Log "╔══════════════════════════════════════════════════════════╗" -Level Success
Write-Log "║                     ✨ Terminé ✨                       ║" -Level Success
Write-Log "╚══════════════════════════════════════════════════════════╝" -Level Success

exit 0
