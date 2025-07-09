@echo off
echo Starting AI Power BI Dashboard Generator...
echo.

echo [1/3] Activating Python environment...
call venv\Scripts\activate

echo [2/3] Starting Backend Server...
start "Backend" cmd /k "python main.py"

echo [3/3] Starting Frontend...
timeout /t 3 /nobreak > nul
cd frontend
start "Frontend" cmd /k "npm start"

echo.
echo ✅ Both services are starting...
echo 🌐 Frontend will be available at: http://localhost:3000
echo 📚 API Documentation at: http://127.0.0.1:8001/docs
echo.
echo Press any key to exit...
pause > nul