<#
.SYNOPSIS
    One-command installer & launcher for SoulMusic on Windows.
.EXAMPLE
    irm https://raw.githubusercontent.com/hming28/SoulMusic/main/install.ps1 | iex
#>

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$RepoUrl = if ($env:SOULMUSIC_REPO) { $env:SOULMUSIC_REPO } else { "https://github.com/hming28/SoulMusic.git" }
$RepoZipUrl = if ($env:SOULMUSIC_ZIP_URL) { $env:SOULMUSIC_ZIP_URL } else { "https://github.com/hming28/SoulMusic/archive/refs/heads/main.zip" }
$InstallDir = if ($env:SOULMUSIC_DIR) { $env:SOULMUSIC_DIR } else { Join-Path $env:USERPROFILE "SoulMusic" }
$NoLaunch = ($env:SOULMUSIC_NO_LAUNCH -eq "1")
$NoShortcut = ($env:SOULMUSIC_NO_SHORTCUT -eq "1")

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  SoulMusic One-Command Installer" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Install directory: $InstallDir"
Write-Host ""

function Refresh-SessionPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = @($machinePath, $userPath) -join ";"
}

function Find-Python {
    $candidates = @()
    foreach ($cmdName in @("py", "python", "python3")) {
        $cmd = Get-Command $cmdName -ErrorAction SilentlyContinue
        if ($cmd) { $candidates += $cmd.Source }
    }
    $searchPatterns = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python3*\python.exe"),
        "C:\Program Files\Python3*\python.exe",
        "C:\Python3*\python.exe"
    )
    foreach ($pattern in $searchPatterns) {
        Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | ForEach-Object {
            $candidates += $_.FullName
        }
    }

    foreach ($exe in ($candidates | Select-Object -Unique)) {
        try {
            if ([System.IO.Path]::GetFileNameWithoutExtension($exe) -eq "py") {
                $resolved = & $exe -3 -c "import sys; print(sys.executable if sys.version_info >= (3, 9) else '')" 2>$null
            } else {
                $resolved = & $exe -c "import sys; print(sys.executable if sys.version_info >= (3, 9) else '')" 2>$null
            }
            $resolved = ($resolved | Select-Object -First 1)
            if ($resolved -and (Test-Path $resolved)) {
                return $resolved.Trim()
            }
        } catch {
            continue
        }
    }
    return $null
}

# 1. Ensure Python 3.9+
Write-Host "[1/5] Checking Python 3.9+..." -ForegroundColor Yellow
$pythonExe = Find-Python
if (-not $pythonExe) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "  Python 3.9+ not found. Installing Python 3.12 via winget..." -ForegroundColor Cyan
        & $winget.Source install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent
        Refresh-SessionPath
        $pythonExe = Find-Python
    }
}
if (-not $pythonExe) {
    Write-Host "ERROR: Python 3.9+ is required. Please install Python from https://www.python.org/downloads/ (check 'Add Python to PATH') and re-run." -ForegroundColor Red
    return
}
Write-Host "  Using Python: $pythonExe" -ForegroundColor Green

# 2. Download or update project files
Write-Host "[2/5] Downloading SoulMusic..." -ForegroundColor Yellow
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($gitCmd) {
    if (Test-Path (Join-Path $InstallDir ".git")) {
        Write-Host "  Existing git repository found, pulling latest updates..."
        $dirty = & $gitCmd.Source -C $InstallDir status --porcelain
        if (-not $dirty) {
            & $gitCmd.Source -C $InstallDir pull --ff-only
            if ($LASTEXITCODE -ne 0) { throw "git pull failed with exit code $LASTEXITCODE" }
        } else {
            Write-Host "  Local changes detected; skipping git pull to preserve your files." -ForegroundColor DarkYellow
        }
    } else {
        if ((Test-Path $InstallDir) -and ((Get-ChildItem $InstallDir -Force | Measure-Object).Count -gt 0)) {
            $backupDir = "$InstallDir.backup.$(Get-Date -Format 'yyyyMMddHHmmss')"
            Write-Host "  Non-empty directory exists, backing up to $backupDir..." -ForegroundColor DarkYellow
            Move-Item -Path $InstallDir -Destination $backupDir
        }
        & $gitCmd.Source clone --depth 1 $RepoUrl $InstallDir
        if ($LASTEXITCODE -ne 0) { throw "git clone failed with exit code $LASTEXITCODE" }
    }
} else {
    Write-Host "  Git not found, downloading ZIP archive..."
    $tempZip = Join-Path $env:TEMP "soulmusic-main.zip"
    $tempExtract = Join-Path $env:TEMP "soulmusic-extract-$([guid]::NewGuid().ToString('N').Substring(0,8))"
    try {
        Invoke-WebRequest -Uri $RepoZipUrl -OutFile $tempZip
        Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force
        $extractedRoot = Get-ChildItem -Path $tempExtract -Directory | Select-Object -First 1
        if (-not $extractedRoot) {
            throw "Failed to locate extracted repository folder."
        }
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
        Get-ChildItem -Path $extractedRoot.FullName -Force | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $InstallDir -Recurse -Force
        }
    } finally {
        Remove-Item -Path $tempZip -Force -ErrorAction SilentlyContinue
        Remove-Item -Path $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# 3. Create .venv & install Python dependencies
Write-Host "[3/5] Setting up virtual environment and dependencies..." -ForegroundColor Yellow
$venvDir = Join-Path $InstallDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPythonw = Join-Path $venvDir "Scripts\pythonw.exe"
$requirementsPath = Join-Path $InstallDir "requirements.txt"

if (-not (Test-Path $venvPython)) {
    & $pythonExe -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { throw "Failed to create virtual environment at $venvDir" }
}

& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r $requirementsPath
if ($LASTEXITCODE -ne 0) { throw "pip install failed with exit code $LASTEXITCODE" }

# 4. Ensure FFmpeg & FFplay
Write-Host "[4/5] Checking FFmpeg..." -ForegroundColor Yellow
$localFfmpeg = Join-Path $InstallDir "ffmpeg.exe"
$localFfplay = Join-Path $InstallDir "ffplay.exe"
$hasFfmpeg = (Test-Path $localFfmpeg) -or [bool](Get-Command ffmpeg -ErrorAction SilentlyContinue)
$hasFfplay = (Test-Path $localFfplay) -or [bool](Get-Command ffplay -ErrorAction SilentlyContinue)

if (-not ($hasFfmpeg -and $hasFfplay)) {
    $ffmpegScript = Join-Path $InstallDir "get_ffmpeg.ps1"
    if (Test-Path $ffmpegScript) {
        try {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $ffmpegScript
        } catch {
            Write-Host "  Warning: Automatic FFmpeg download failed ($($_.Exception.Message)). You can run get_ffmpeg.ps1 later." -ForegroundColor DarkYellow
        }
    }
} else {
    Write-Host "  FFmpeg is ready." -ForegroundColor Green
}

# 5. Create Desktop shortcut & launch
Write-Host "[5/5] Creating shortcut and launching SoulMusic..." -ForegroundColor Yellow
if (-not $NoShortcut) {
    try {
        $desktopDir = [Environment]::GetFolderPath("Desktop")
        if ($desktopDir -and (Test-Path $desktopDir)) {
            $shortcutPath = Join-Path $desktopDir "SoulMusic.lnk"
            $wsh = New-Object -ComObject WScript.Shell
            $shortcut = $wsh.CreateShortcut($shortcutPath)
            $shortcut.TargetPath = Join-Path $InstallDir "run.bat"
            $shortcut.WorkingDirectory = $InstallDir
            $shortcut.Description = "Launch SoulMusic"
            $shortcut.Save()
            Write-Host "  Desktop shortcut created: $shortcutPath" -ForegroundColor Green
        }
    } catch {
        Write-Host "  Skipped desktop shortcut: $($_.Exception.Message)" -ForegroundColor DarkYellow
    }
}

$mainScript = Join-Path $InstallDir "soulmusic.py"
Write-Host ""
Write-Host "SoulMusic is installed at: $InstallDir" -ForegroundColor Green

if (-not $NoLaunch) {
    $launchExe = if (Test-Path $venvPythonw) { $venvPythonw } else { $venvPython }
    Start-Process -FilePath $launchExe -ArgumentList "`"$mainScript`"" -WorkingDirectory $InstallDir
    Write-Host "SoulMusic launched!" -ForegroundColor Cyan
}
