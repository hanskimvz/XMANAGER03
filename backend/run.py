"""
X-Manager 백엔드 실행 스크립트

config.json 의 server.host / server.port 로 uvicorn 을 띄운다.
    cd backend && python3 run.py
"""

import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.SERVER_HOST, port=settings.SERVER_PORT)
