# Build a shareable Riftbreak Smash .exe (Windows PowerShell).
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File pc_build\build_exe.ps1
# Output: dist\RiftbreakSmash.exe — zip that file + relay_url.txt to share.
# Friends on different homes / different Wi-Fi use ONLINE > INTERNET ROOM.
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
Write-Host "== RiftbreakSmash exe build ==" -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install pygame websocket-client pyinstaller
# sanity: real-time relay imports (no MQTT dependency)
python -c "import ast; ast.parse(open('pc_build/main.py').read()); ast.parse(open('pc_build/netrelay.py').read()); ast.parse(open('pc_build/netplay.py').read()); print('py syntax ok')"
python -c "import sys; sys.path.insert(0,'pc_build'); import netrelay; print('relay service:', netrelay.service_url(), '| websocket available:', netrelay.available())"
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
pyinstaller RiftbreakSmash.spec
# Ship the relay URL next to the exe so a downloaded copy needs no env vars.
Copy-Item pc_build\relay_url.txt dist\relay_url.txt -Force
Write-Host ""
Write-Host "DONE: dist\RiftbreakSmash.exe + dist\relay_url.txt" -ForegroundColor Green
Write-Host "Share both files. Host: ONLINE > INTERNET ROOM > HOST ROOM, send the 8-char code."
Write-Host "Guest: ONLINE > INTERNET ROOM > JOIN ROOM, type the code. Different Wi-Fi OK."
Write-Host "Server needs REDIS_URL (Upstash) + long-lived relay: npm install; REDIS_URL=... RELAY_WS_URL=wss://<relay-host> (see relay/server.js)."
