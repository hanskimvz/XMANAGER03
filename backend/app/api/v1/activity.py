"""사용자 활동(화면 열람) 로그 — 프론트가 화면 이동 시 화면명을 보내면 로그로 남긴다.

목적: view-logs 창에서 "누가 어느 화면을 봤는지" 확인.
- 로그인만 요구(민감 데이터 없음). DB에 저장하지 않고 로그로만 남김(app.audit).
- 예: INFO:app.audit:[화면] 유현성(yhs) → 영업 관리
"""
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import require_auth
from app.models.user import User

router = APIRouter(prefix="/activity", tags=["활동 로그"])
_audit = logging.getLogger("app.audit")


class PageViewIn(BaseModel):
    page: str = Field(..., max_length=120, description="사람이 읽을 화면/탭 이름")


@router.post("/view")
def log_page_view(body: PageViewIn, actor: User = Depends(require_auth)):
    """화면 열람 기록(로그만). 프론트 라우터가 이동 시 호출."""
    page = (body.page or "").strip()[:120]
    if page:
        _audit.info("[화면] %s(%s) → %s", actor.name, actor.username, page)
    return {"ok": True}
