"""
무의존 로그인 무차별 대입 방어 (in-memory sliding window + 임시 잠금).
운영 백엔드가 단일 프로세스(uvicorn, no --reload)이므로 프로세스 메모리로 충분.
다중 워커/수평 확장 시에는 Redis 기반으로 교체 권장.
"""
import time
from collections import defaultdict
from threading import Lock


class LoginLimiter:
    def __init__(self, max_attempts: int = 5, window_sec: int = 300, lockout_sec: int = 900):
        self.max = max_attempts          # 윈도우 내 허용 실패 횟수
        self.window = window_sec         # 실패 집계 윈도우(초)
        self.lockout = lockout_sec       # 초과 시 잠금 시간(초)
        self._fails: dict[str, list[float]] = defaultdict(list)
        self._locked: dict[str, float] = {}
        self._lock = Lock()

    def locked_for(self, key: str) -> int:
        """잠금 중이면 남은 초, 아니면 0."""
        now = time.time()
        with self._lock:
            until = self._locked.get(key)
            if until and now < until:
                return int(until - now) + 1
            if until:
                self._locked.pop(key, None)
            return 0

    def record_fail(self, key: str) -> None:
        now = time.time()
        with self._lock:
            arr = [t for t in self._fails[key] if now - t < self.window]
            arr.append(now)
            self._fails[key] = arr
            if len(arr) >= self.max:
                self._locked[key] = now + self.lockout
                self._fails[key] = []

    def record_success(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)
            self._locked.pop(key, None)


# 로그인/리프레시 공용 인스턴스
login_limiter = LoginLimiter(max_attempts=5, window_sec=300, lockout_sec=900)


def client_key(request, username: str = "") -> str:
    """IP + (선택)사용자명 조합 키."""
    ip = "?"
    try:
        ip = request.client.host if request and request.client else "?"
        # 리버스 프록시(Caddy) 뒤이면 X-Forwarded-For 우선
        xff = request.headers.get("x-forwarded-for") if request else None
        if xff:
            ip = xff.split(",")[0].strip()
    except Exception:
        pass
    return f"{ip}|{username.lower()}"
