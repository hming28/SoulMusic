# get_ffmpeg.ps1 - Automated FFmpeg static build downloader for SoulMusic
$baseDir = $PSScriptRoot
if (-not $baseDir) { $baseDir = Get-Location }

$zipPath = Join-Path $baseDir "ffmpeg.zip"
$tempDir = Join-Path $baseDir "ffmpeg_temp"
$url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

Write-Host "Downloading FFmpeg static build from yt-dlp/FFmpeg-Builds..."
Invoke-WebRequest -Uri $url -OutFile $zipPath

Write-Host "Extracting binaries..."
Expand-Archive -Path $zipPath -DestinationPath $tempDir -Force

$ffmpeg = Get-ChildItem -Path $tempDir -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
$ffplay = Get-ChildItem -Path $tempDir -Recurse -Filter "ffplay.exe" | Select-Object -First 1

if ($ffmpeg) { Copy-Item $ffmpeg.FullName (Join-Path $baseDir "ffmpeg.exe") -Force }
if ($ffplay) { Copy-Item $ffplay.FullName (Join-Path $baseDir "ffplay.exe") -Force }

Remove-Item $tempDir -Recurse -Force
Remove-Item $zipPath -Force

Write-Host "Done! ffmpeg exists: $(Test-Path (Join-Path $baseDir 'ffmpeg.exe'))"
Write-Host "ffplay exists: $(Test-Path (Join-Path $baseDir 'ffplay.exe'))"
