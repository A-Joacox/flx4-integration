# Fase 0: setup del entorno Python en Windows 11
# Uso: .\setup.ps1  (desde la raíz del repo)

$ErrorActionPreference = "Stop"

Write-Host "== Creando venv ==" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) { python -m venv .venv }
}

Write-Host "== Instalando dependencias ==" -ForegroundColor Cyan
& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "`n== Verificando MIDI (FLX4) ==" -ForegroundColor Cyan
& .venv\Scripts\python.exe -c "import mido; ports = mido.get_input_names(); print('Puertos:', ports or 'NINGUNO')"

Write-Host "`n== Verificando WASAPI loopback ==" -ForegroundColor Cyan
& .venv\Scripts\python.exe -c @"
import pyaudiowpatch as pa
with pa.PyAudio() as p:
    devs = list(p.get_loopback_device_info_generator())
    print(f'{len(devs)} dispositivos loopback encontrados')
    for d in devs: print(' -', d['name'])
"@

Write-Host "`nSetup OK. Siguientes pasos:" -ForegroundColor Green
Write-Host "  .venv\Scripts\Activate.ps1"
Write-Host "  python midi\check_midi.py       (con el FLX4 conectado)"
Write-Host "  python audio\check_loopback.py  (con música sonando)"
