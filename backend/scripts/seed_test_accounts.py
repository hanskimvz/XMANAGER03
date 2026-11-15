"""
전자결재 테스트 계정 시드 (개발/스테이징 전용)

현재 DB(보통 xmanager_dev)에 더미 테스트 계정을 upsert 한다. 기존 실데이터는 건드리지 않음.
- admin : 비번을 admin1234 로 (재)설정 (role 유지/ADMIN)
- hong  : 기안자 (기본결재자 1차=kim, 2차=lee)
- kim/lee/park : 결재 1/2/3차
worker 4명에는 RBAC 'FULL' 역할 배정(RBAC_MODE 무관하게 동작). admin 은 role=ADMIN(와일드카드).

실행:  cd backend && set APP_ENV=development && .venv\\Scripts\\python.exe scripts\\seed_test_accounts.py
⚠️ 운영(production) DB 에는 절대 실행하지 말 것.
"""
import os
import sys
# backend/ 를 import 경로에 추가 → `python scripts/seed_test_accounts.py` 로 바로 실행 가능
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APP_ENV", "development")

from app.core.database import SessionLocal
from app.core.auth import hash_password
from app.models.user import User
from app.models.rbac import Role, UserRole

# (username, name, role, dept, position, password)
WORKERS = [
    ("hong", "홍길동", "USER", "SALES", "사원", "test1234"),
    ("kim", "김팀장", "USER", "SALES", "팀장", "test1234"),
    ("lee", "이이사", "USER", "MANAGEMENT", "이사", "test1234"),
    ("park", "박대표", "USER", "MANAGEMENT", "대표", "test1234"),
]


def _upsert(db, username, name, role, dept, position, password):
    u = db.query(User).filter(User.username == username).first()
    if u is None:
        u = User(username=username)
        db.add(u)
    u.password_hash = hash_password(password)
    u.name = name
    u.role = role
    u.department = dept
    u.position = position
    u.is_active = True
    db.commit(); db.refresh(u)
    return u


def main():
    db = SessionLocal()
    try:
        # admin 비번만 알려진 값으로 재설정(없으면 생성)
        admin = db.query(User).filter(User.username == "admin").first()
        if admin is None:
            admin = _upsert(db, "admin", "관리자", "ADMIN", "MANAGEMENT", "CTO", "admin1234")
        else:
            admin.password_hash = hash_password("admin1234"); admin.is_active = True
            db.commit()

        users = {un: _upsert(db, un, nm, ro, dp, ps, pw) for un, nm, ro, dp, ps, pw in WORKERS}

        # 결재선: hong 의 디폴트 결재자 1차=kim, 2차=lee (park 은 결재선에서 수동 추가해 3차 테스트)
        users["hong"].approver_id = users["kim"].id
        users["hong"].approver2_id = users["lee"].id
        db.commit()

        # RBAC: worker 4명에 FULL 역할(있으면) 배정 → RBAC_MODE 무관하게 동작
        full = db.query(Role).filter(Role.code == "FULL").first()
        if full is not None:
            for u in users.values():
                db.query(UserRole).filter(UserRole.user_id == u.id).delete()
                db.add(UserRole(user_id=u.id, role_id=full.id))
            db.commit()

        print("[SEED] 완료: admin/admin1234, hong/kim/lee/park = test1234")
        print(f"[SEED] 결재선: hong(기안) -> kim(1차) -> lee(2차) [+ park 수동 3차]")
        print(f"[SEED] FULL 역할 배정: {'OK' if full else 'SKIP(FULL 역할 미존재 — 서버 1회 부팅 후 재실행)'}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
