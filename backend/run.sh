echo ==========================================
echo    X-Manager Backend Server
echo    http://localhost:5198
echo ==========================================

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 5198 --reload
