@echo off
setlocal
cd /d "%~dp0"

echo [Ingeniero] Modo desarrollo: Vite en :5173, backend en :8000
start "Ingeniero backend" backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend --reload
pushd frontend
start "Ingeniero frontend" cmd /c "npm run dev"
popd

timeout /t 4 /nobreak >nul
start "" http://127.0.0.1:5173
echo Deja ambas ventanas abiertas mientras desarrollas.
pause
