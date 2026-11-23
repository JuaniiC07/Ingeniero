@echo off
setlocal
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
    echo [Ingeniero] Creando entorno virtual de Python...
    python -m venv backend\.venv
    backend\.venv\Scripts\python.exe -m pip install --upgrade pip
    backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
)

if not exist "frontend\dist\index.html" (
    echo [Ingeniero] Instalando y compilando el frontend...
    pushd frontend
    call npm install
    call npm run build
    popd
)

echo [Ingeniero] Iniciando el backend en http://127.0.0.1:8000 ...
start "Ingeniero backend" backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend

timeout /t 4 /nobreak >nul
start "" http://127.0.0.1:8000
echo [Ingeniero] Listo. Cerra la ventana "Ingeniero backend" para apagarlo.
pause
