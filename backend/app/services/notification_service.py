"""인앱 알림 서비스 (v0.54.0)

- create(): 알림 1건 생성. 기본은 commit 안 함(호출 트랜잭션에 편승).
- 전자결재 헬퍼: 상신/다음차례/최종승인/반려/참조 알림 생성.
  approval_service 에서 본 액션 commit 이후 best-effort 로 호출(실패해도 액션은 유지).
- 조회/읽음처리: 자체 commit.
"""

import logging
import re
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models.notification import Notification

logger = logging.getLogger(__name__)


def _plain_preview(html: Optional[str], limit: int = 70) -> str:
    """HTML 본문에서 태그를 걷어내고 공백 정리 후 미리보기 텍스트 반환."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:limit] + "…") if len(text) > limit else text


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    # ==================== 생성 ====================

    def create(
        self,
        *,
        recipient_id: Optional[int],
        type: str,
        title: str,
        message: Optional[str] = None,
        link: Optional[str] = None,
        related_type: Optional[str] = None,
        related_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        commit: bool = False,
        push: bool = True,
    ) -> Optional[Notification]:
        """알림 1건 생성. 수신자 없음/본인에게 발송 시 스킵."""
        if not recipient_id:
            return None
        if actor_id is not None and recipient_id == actor_id:
            return None  # 본인이 유발한 알림은 본인에게 보내지 않음
        n = Notification(
            recipient_id=recipient_id,
            type=type,
            title=title,
            message=message,
            link=link,
            related_type=related_type,
            related_id=related_id,
            actor_id=actor_id,
        )
        self.db.add(n)
        if commit:
            self.db.commit()
        # 웹푸시(앱 닫혀 있어도 OS 알림) — 백그라운드 데몬 스레드, best-effort.
        # push=False 는 다건 발송을 커밋 후 일괄 처리하려는 호출측(공지)이 사용.
        if push:
            try:
                from app.services import web_push_service
                web_push_service.send_to_user_async(recipient_id, title, message or "", link or "/")
            except Exception:
                pass
        return n

    # ==================== 전자결재 헬퍼 ====================

    @staticmethod
    def _approval_link(doc) -> str:
        return f"/approvals/{doc.id}"

    def notify_approval_submitted(self, doc) -> None:
        """상신: 1단계 결재자 + 참조자에게 알림."""
        link = self._approval_link(doc)
        first = next((ln for ln in (doc.lines or []) if ln.step_order == 1), None)
        if first:
            self.create(
                recipient_id=first.approver_id,
                type="APPROVAL_REQUEST",
                title=f"결재 요청: {doc.title}",
                message=f"{doc.doc_number} 결재를 요청받았습니다.",
                link=link,
                related_type="approval_document",
                related_id=doc.id,
                actor_id=doc.drafter_id,
            )
        for ref in (doc.references or []):
            self.create(
                recipient_id=ref.user_id,
                type="APPROVAL_REFERENCE",
                title=f"참조 문서: {doc.title}",
                message=f"{doc.doc_number} 문서에 참조자로 지정되었습니다.",
                link=link,
                related_type="approval_document",
                related_id=doc.id,
                actor_id=doc.drafter_id,
            )
        # 시행자(집행자): 참조자와 동급으로 상신 시점에도 알림.
        # (기존 '최종 승인 후 시행 요청' 알림은 그대로 유지)
        # 중복 방지: 1차 결재자·참조자와 겹치면 스킵(본인=기안자면 create 가 자동 스킵).
        exec_id = getattr(doc, "executor_id", None)
        if exec_id:
            ref_ids = {ref.user_id for ref in (doc.references or [])}
            if exec_id not in ref_ids and not (first and first.approver_id == exec_id):
                self.create(
                    recipient_id=exec_id,
                    type="APPROVAL_EXECUTION",
                    title=f"시행 예정 문서: {doc.title}",
                    message=f"{doc.doc_number} 문서의 시행자로 지정되었습니다. (최종 승인되면 시행 요청됩니다)",
                    link=link,
                    related_type="approval_document",
                    related_id=doc.id,
                    actor_id=doc.drafter_id,
                )

    def notify_approval_commented(self, doc, actor_id: int, preview: str) -> None:
        """결재 의견(댓글) 작성: 문서 연관자 전원에게 알림(작성 본인은 create()에서 자동 제외)."""
        link = self._approval_link(doc)
        rids = [doc.drafter_id]
        rids += [ln.approver_id for ln in (doc.lines or [])]
        rids += [ref.user_id for ref in (doc.references or [])]
        if getattr(doc, "executor_id", None):
            rids.append(doc.executor_id)
        for rid in dict.fromkeys(rids):  # 중복 제거, 순서 보존
            self.create(
                recipient_id=rid,
                type="APPROVAL_COMMENT",
                title=f"새 의견: {doc.title}",
                message=preview,
                link=link,
                related_type="approval_document",
                related_id=doc.id,
                actor_id=actor_id,
            )

    def notify_approval_next(self, doc, next_line, actor_id: int) -> None:
        """승인 후 다음 결재자에게 차례 알림."""
        self.create(
            recipient_id=next_line.approver_id,
            type="APPROVAL_REQUEST",
            title=f"결재 요청: {doc.title}",
            message=f"{doc.doc_number} 결재 차례가 되었습니다.",
            link=self._approval_link(doc),
            related_type="approval_document",
            related_id=doc.id,
            actor_id=actor_id,
        )

    def notify_approval_approved(self, doc, actor_id: int) -> None:
        """최종 승인: 기안자에게 알림."""
        self.create(
            recipient_id=doc.drafter_id,
            type="APPROVAL_APPROVED",
            title=f"결재 완료: {doc.title}",
            message=f"{doc.doc_number} 문서가 최종 승인되었습니다.",
            link=self._approval_link(doc),
            related_type="approval_document",
            related_id=doc.id,
            actor_id=actor_id,
        )

    def notify_approval_rejected(self, doc, actor_id: int) -> None:
        """반려: 기안자에게 알림."""
        self.create(
            recipient_id=doc.drafter_id,
            type="APPROVAL_REJECTED",
            title=f"반려됨: {doc.title}",
            message=f"{doc.doc_number} 문서가 반려되었습니다.",
            link=self._approval_link(doc),
            related_type="approval_document",
            related_id=doc.id,
            actor_id=actor_id,
        )

    def notify_approval_recalled(self, doc, recipient_ids, actor_id: int) -> None:
        """회수: 이미 승인했던 결재자들에게 문서가 기안자에 의해 회수(임시저장 전환)됐음을 알림."""
        for rid in dict.fromkeys(recipient_ids):  # 중복 제거, 순서 보존
            if rid is None:
                continue
            self.create(
                recipient_id=rid,
                type="APPROVAL_RECALLED",
                title=f"결재 회수됨: {doc.title}",
                message=f"{doc.doc_number} 문서가 기안자에 의해 회수되어 승인이 취소되었습니다.",
                link=self._approval_link(doc),
                related_type="approval_document",
                related_id=doc.id,
                actor_id=actor_id,
            )

    def notify_execution_requested(self, doc, actor_id: int) -> None:
        """최종 승인 후 시행자(집행자)에게 '시행하세요' 알림."""
        if not getattr(doc, "executor_id", None):
            return
        self.create(
            recipient_id=doc.executor_id,
            type="APPROVAL_EXECUTION",
            title=f"시행 요청: {doc.title}",
            message=f"{doc.doc_number} 문서가 승인되었습니다. 구매/집행(시행)을 진행해 주세요.",
            link=self._approval_link(doc),
            related_type="approval_document",
            related_id=doc.id,
            actor_id=actor_id,
        )

    def notify_execution_done(self, doc, actor_id: int) -> None:
        """시행 완료 시 기안자에게 알림."""
        self.create(
            recipient_id=doc.drafter_id,
            type="APPROVAL_EXECUTED",
            title=f"시행 완료: {doc.title}",
            message=f"{doc.doc_number} 구매/집행(시행)이 완료되었습니다.",
            link=self._approval_link(doc),
            related_type="approval_document",
            related_id=doc.id,
            actor_id=actor_id,
        )

    # ==================== 공지사항 ====================

    def notify_announcement(self, ann, author_id: int) -> dict:
        """공지 등록 시 대상(부서 지정 시 해당 부서, 미지정=전체) 활성 직원에게 알림. 작성자 제외.
        인앱 알림 행만 생성(push=False)하고, 웹푸시는 호출측이 '커밋 후' 일괄 발송하도록
        발송 페이로드({recipient_ids,title,body,url})를 반환한다.
        (커밋 전 발송 시 롤백되면 폰 푸시만 남는 phantom push 방지 + 스레드 폭증 방지)"""
        from app.models.user import User
        q = self.db.query(User).filter(User.is_active == True)  # noqa: E712
        tdepts = getattr(ann, "target_departments", None)
        if tdepts and len(tdepts) > 0:
            q = q.filter(User.department.in_(tdepts))
        title = (ann.title or "").strip()
        short = (title[:60] + "…") if len(title) > 60 else title
        notif_title = f"새 공지: {short}"          # 공지 제목을 헤드라인으로
        preview = _plain_preview(getattr(ann, "body", None)) or "새 공지사항이 등록되었습니다."
        link = f"/announcements?open={ann.id}"     # 종 알림 클릭 시 해당 공지 바로 열기(딥링크)
        recipient_ids = []
        for u in q.all():
            if u.id == author_id:
                continue
            self.create(
                recipient_id=u.id,
                type="ANNOUNCEMENT",
                title=notif_title,
                message=preview,
                link=link,
                related_type="announcement",
                related_id=ann.id,
                actor_id=author_id,
                push=False,   # 웹푸시는 커밋 후 일괄 발송
            )
            recipient_ids.append(u.id)
        return {"recipient_ids": recipient_ids, "title": notif_title, "body": preview, "url": link}

    # ==================== 생산요청 ====================

    def notify_production_requested(self, pr, recipient_ids, actor_id: int) -> None:
        """영업이 생산요청을 올렸을 때 지정된 생산팀 인원에게 알림."""
        cust = getattr(getattr(pr, "customer", None), "partner_name", None) or ""
        msg = f"{cust} · {pr.request_number} 생산요청이 등록되었습니다.".lstrip(" ·")
        for rid in dict.fromkeys(recipient_ids or []):
            self.create(
                recipient_id=rid,
                type="PRODUCTION_REQUEST",
                title=f"새 생산요청: {pr.request_number}",
                message=msg,
                link="/production",
                related_type="production_request",
                related_id=pr.id,
                actor_id=actor_id,
            )

    def notify_due_date_changed(self, pr, recipient_ids, actor_id: int, old_due, new_due) -> None:
        """영업이 납기일을 변경했을 때 생산팀(요청 단계 그룹)에 알림."""
        cust = getattr(getattr(pr, "customer", None), "partner_name", None) or ""
        def _d(x):
            try:
                return x.isoformat()
            except Exception:
                return str(x) if x else "미정"
        msg = f"{cust} · {pr.request_number} 납기일이 {_d(old_due)} → {_d(new_due)} 로 변경되었습니다.".lstrip(" ·")
        for rid in dict.fromkeys(recipient_ids or []):
            if rid is None:
                continue
            self.create(
                recipient_id=rid,
                type="PRODUCTION_DUE_CHANGED",
                title=f"납기 변경: {pr.request_number}",
                message=msg,
                link="/production",
                related_type="production_request",
                related_id=pr.id,
                actor_id=actor_id,
            )

    def notify_production_started(self, pr, recipient_ids, actor_id: int) -> None:
        """생산 시작(진행중 진입) 시 지정된 인원에게 알림."""
        cust = getattr(getattr(pr, "customer", None), "partner_name", None) or ""
        msg = f"{cust} · {pr.request_number} 생산이 시작되었습니다.".lstrip(" ·")
        for rid in dict.fromkeys(recipient_ids or []):
            self.create(
                recipient_id=rid,
                type="PRODUCTION_STARTED",
                title=f"생산 시작: {pr.request_number}",
                message=msg,
                link="/production",
                related_type="production_request",
                related_id=pr.id,
                actor_id=actor_id,
            )

    def notify_production_shipped_group(self, pr, recipient_ids, actor_id: int) -> None:
        """생산 출고 완료 시 지정된 인원(그룹)에게 알림. (영업 담당자 알림과 별개)"""
        cust = getattr(getattr(pr, "customer", None), "partner_name", None) or ""
        msg = f"{cust} · {pr.request_number} 생산 출고가 완료되었습니다.".lstrip(" ·")
        for rid in dict.fromkeys(recipient_ids or []):
            self.create(
                recipient_id=rid,
                type="PRODUCTION_SHIPPED",
                title=f"출고 완료: {pr.request_number}",
                message=msg,
                link="/production",
                related_type="production_request",
                related_id=pr.id,
                actor_id=actor_id,
            )

    def notify_review_requested(self, pr, actor_id: int) -> None:
        """생산팀이 검토를 요청(needs_review 켜기)했을 때 영업 담당자(생성자)에게 알림."""
        rid = getattr(pr, "created_by", None) or getattr(pr, "requested_by", None)
        if not rid:
            return
        note = (getattr(pr, "review_note", None) or "").strip()
        self.create(
            recipient_id=rid,
            type="PRODUCTION_REVIEW",
            title=f"검토 요청: {pr.request_number}",
            message=(f"생산팀 검토 요청 — {note}" if note else f"{pr.request_number} 건에 생산팀이 검토를 요청했습니다."),
            link="/sales",
            related_type="production_request",
            related_id=pr.id,
            actor_id=actor_id,
        )

    def notify_production_rejected(self, pr, actor_id: int) -> None:
        """생산팀이 생산요청서를 반려했을 때 영업 담당자(생성자)에게 알림."""
        rid = getattr(pr, "created_by", None) or getattr(pr, "requested_by", None)
        reason = (getattr(pr, "rejection_reason", None) or "").strip()
        self.create(
            recipient_id=rid,
            type="PRODUCTION_REJECTED",
            title=f"생산요청 반려: {pr.request_number}",
            message=(f"반려 사유: {reason}" if reason else f"{pr.request_number} 생산요청이 반려되었습니다."),
            link="/sales",
            related_type="production_request",
            related_id=pr.id,
            actor_id=actor_id,
        )

    def notify_production_shipped(self, pr, actor_id: int) -> None:
        """생산 출고 완료 시 해당 건 영업 담당자(생성자)에게 알림."""
        rid = getattr(pr, "created_by", None) or getattr(pr, "requested_by", None)
        self.create(
            recipient_id=rid,
            type="PRODUCTION_SHIPPED",
            title=f"출고 완료: {pr.request_number}",
            message=f"{pr.request_number} 생산 출고가 완료되었습니다. CI 발행/발송을 진행하세요.",
            link="/sales",
            related_type="production_request",
            related_id=pr.id,
            actor_id=actor_id,
        )

    # ==================== 조회 / 읽음 ====================

    def list_for_user(
        self, user_id: int, limit: int = 20, offset: int = 0, unread_only: bool = False
    ) -> Tuple[List[Notification], int, int]:
        base = self.db.query(Notification).filter(Notification.recipient_id == user_id)
        unread = base.filter(Notification.is_read == False).count()  # noqa: E712
        q = base
        if unread_only:
            q = q.filter(Notification.is_read == False)  # noqa: E712
        total = q.count()
        items = (
            q.order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total, unread

    def unread_count(self, user_id: int) -> int:
        return (
            self.db.query(Notification)
            .filter(Notification.recipient_id == user_id, Notification.is_read == False)  # noqa: E712
            .count()
        )

    def mark_read(self, notif_id: int, user_id: int) -> bool:
        n = (
            self.db.query(Notification)
            .filter(Notification.id == notif_id, Notification.recipient_id == user_id)
            .first()
        )
        if not n:
            return False
        if not n.is_read:
            n.is_read = True
            n.read_at = func.now()
            self.db.commit()
        return True

    def mark_all_read(self, user_id: int) -> int:
        cnt = (
            self.db.query(Notification)
            .filter(Notification.recipient_id == user_id, Notification.is_read == False)  # noqa: E712
            .update({Notification.is_read: True, Notification.read_at: func.now()},
                    synchronize_session=False)
        )
        self.db.commit()
        return cnt
