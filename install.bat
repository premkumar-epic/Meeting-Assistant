@echo off
echo ===================================================
echo Installing AI-Powered Meeting Assistant Dependencies
echo ===================================================

echo.
echo [1/2] Installing Backend Dependencies...
cd backend
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt
cd ..

echo.
echo [2/2] Installing Frontend Dependencies...
cd client
call npm install
cd ..

echo.
echo ===================================================
echo Installation Complete!
echo You can now run the app using start.bat
echo ===================================================
pause
