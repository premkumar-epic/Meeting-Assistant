@echo off
echo ===================================================
echo Starting AI-Powered Meeting Assistant
echo ===================================================

echo.
echo Starting Backend Server (FastAPI)...
start "Backend Server" cmd /k "cd backend && call venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

echo Starting Frontend Server (Vite)...
start "Frontend Server" cmd /k "cd client && npm run dev"

echo.
echo Both servers are starting in separate windows.
echo - Backend will be available at http://localhost:8000
echo - Frontend will be available at http://localhost:5173 (default)
echo.
echo Close those windows to stop the servers.
pause
