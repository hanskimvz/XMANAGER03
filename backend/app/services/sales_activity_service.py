"""
영업 대응 현황 서비스
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func as sa_func, case, or_

from app.models.sales_activity import SalesActivity, SalesActivityLog
from app.models.business_partner import BusinessPartner
from app.schemas.sales_activity import SalesActivityCreate, SalesActivityUpdate, SalesActivityLogCreate


class SalesActivityService:
    def __init__(self, db: Session):
        self.db = db

    def get_list(
        self,
        statuses: Optional[List[str]] = None,
        assigned_to: Optional[str] = None,
        customer_id: Optional[int] = None,
        country: Optional[str] = None,
        inquiry_type: Optional[str] = None,
        keyword: Optional[str] = None,
        urgent: Optional[bool] = None,
        important: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SalesActivity], int]:
        query = self.db.query(SalesActivity).options(
            joinedload(SalesActivity.customer)
        )

        # 상태 다중 선택(합집합). 빈 리스트는 호출측에서 걸러 아무 것도 안 부르도록 처리.
        if statuses:
            query = query.filter(SalesActivity.status.in_(statuses))
        # 우선도 필터(별개 축) — 둘 다 선택 시 OR(긴급이거나 중요)
        flag_conds = []
        if urgent:
            flag_conds.append(SalesActivity.is_urgent == True)   # noqa: E712
        if important:
            flag_conds.append(SalesActivity.is_important == True)  # noqa: E712
        if flag_conds:
            query = query.filter(or_(*flag_conds))
        if assigned_to:
            # 콤마 구분 다중 담당자 지원 (예: "홍길동,김민정")
            # assigned_to가 "김민정, 유현성"처럼 다중 인원 문자열일 수 있어
            # 정확 일치가 아닌 포함(ilike) 매칭 — 선택한 인원이 한 명이라도
            # 들어있는 활동을 모두 노출한다.
            names = [n.strip() for n in assigned_to.split(",") if n.strip()]
            if names:
                query = query.filter(
                    or_(*[SalesActivity.assigned_to.ilike(f"%{n}%") for n in names])
                )
        if customer_id:
            query = query.filter(SalesActivity.customer_id == customer_id)
        if country:
            query = query.filter(SalesActivity.country.ilike(f"%{country}%"))
        if inquiry_type:
            query = query.filter(SalesActivity.inquiry_type == inquiry_type)
        if keyword:
            kw = f"%{keyword}%"
            query = query.filter(
                (SalesActivity.title.ilike(kw)) |
                (SalesActivity.customer_name.ilike(kw))
            )

        total = query.count()

        # 정렬 우선순위(전 페이지 통틀어 최상단부터):
        #  0~2: 활성(진행중/대기/보류) 중 긴급·중요 → 긴급 → 중요 (1페이지 최상단 보장)
        #  3~5: 나머지 활성(진행중→대기→보류)  6: 완료  7: 무산  8: 그 외
        active = SalesActivity.status.in_(["IN_PROGRESS", "WAITING", "ON_HOLD"])
        order_rank = case(
            (active & (SalesActivity.is_urgent == True) & (SalesActivity.is_important == True), 0),  # noqa: E712
            (active & (SalesActivity.is_urgent == True), 1),   # noqa: E712
            (active & (SalesActivity.is_important == True), 2),  # noqa: E712
            (SalesActivity.status == "IN_PROGRESS", 3),
            (SalesActivity.status == "WAITING", 4),
            (SalesActivity.status == "ON_HOLD", 5),
            (SalesActivity.status == "COMPLETED", 6),
            (SalesActivity.status == "DROPPED", 7),
            else_=8,
        )
        items = query.order_by(
            order_rank,
            desc(SalesActivity.updated_at),
            desc(SalesActivity.created_at),
        ).offset(skip).limit(limit).all()

        # 로그 카운트/최근날짜를 별도 조회
        if items:
            ids = [a.id for a in items]
            log_stats = self.db.query(
                SalesActivityLog.activity_id,
                sa_func.count(SalesActivityLog.id).label("log_count"),
                sa_func.max(SalesActivityLog.created_at).label("last_log_date"),
            ).filter(
                SalesActivityLog.activity_id.in_(ids)
            ).group_by(SalesActivityLog.activity_id).all()

            stats_map = {s.activity_id: {"log_count": s.log_count, "last_log_date": s.last_log_date} for s in log_stats}
            for item in items:
                s = stats_map.get(item.id, {})
                item.log_count = s.get("log_count", 0)
                item.last_log_date = s.get("last_log_date")

        return items, total

    def get_by_id(self, activity_id: int) -> Optional[SalesActivity]:
        return self.db.query(SalesActivity).options(
            joinedload(SalesActivity.customer),
            joinedload(SalesActivity.logs),
        ).filter(SalesActivity.id == activity_id).first()

    def create(self, data: SalesActivityCreate) -> SalesActivity:
        # 거래처 선택 시 자동으로 나라/거래처명 채움
        if data.customer_id and (not data.customer_name or not data.country):
            bp = self.db.query(BusinessPartner).filter(BusinessPartner.id == data.customer_id).first()
            if bp:
                if not data.customer_name:
                    data.customer_name = bp.partner_name
                if not data.country:
                    data.country = bp.country_name

        activity = SalesActivity(**data.model_dump())
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def update(self, activity_id: int, data: SalesActivityUpdate, logged_by: Optional[str] = None) -> Optional[SalesActivity]:
        """
        영업활동 수정 + 변경 사항 자동 로그 (v0.31.0)

        다음 필드 변경 시 자동으로 SalesActivityLog에 기록:
        - status (상태) → STATUS
        - inquiry_type (문의 유형) → INQUIRY_TYPE
        - next_step (다음 단계) → NEXT_STEP
        - pending_reason (지연 사유) → PENDING_REASON
        - assigned_to (담당자) → ASSIGNEE
        """
        activity = self.db.query(SalesActivity).filter(SalesActivity.id == activity_id).first()
        if not activity:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # 변경 전 값 저장
        old_values = {
            'status': activity.status,
            'inquiry_type': activity.inquiry_type,
            'current_step': activity.current_step,
            'next_step': activity.next_step,
            'pending_reason': activity.pending_reason,
            'assigned_to': activity.assigned_to,
        }

        # 필드별 로그 설정
        STATUS_LABELS = {
            'IN_PROGRESS': '진행중',
            'WAITING': '대기',
            'COMPLETED': '완료',
            'ON_HOLD': '보류',
        }
        INQUIRY_TYPE_LABELS = {
            'GENERAL': '일반 문의',
            'TECHNICAL': '기술 문의',
            'QUOTATION': '견적 문의',
            'SAMPLE': '샘플 요청',
            'CLAIM': '클레임',
            'OTHER': '기타',
        }

        # 업데이트 적용
        for key, value in update_data.items():
            setattr(activity, key, value)

        # 변경 사항 로그 생성
        logs_to_add = []

        if 'status' in update_data and old_values['status'] != activity.status:
            old_label = STATUS_LABELS.get(old_values['status'] or '', old_values['status'] or '없음')
            new_label = STATUS_LABELS.get(activity.status or '', activity.status or '없음')
            logs_to_add.append(SalesActivityLog(
                activity_id=activity_id,
                log_type='STATUS',
                content=f"{old_label} → {new_label}",
                logged_by=logged_by,
            ))

        if 'inquiry_type' in update_data and old_values['inquiry_type'] != activity.inquiry_type:
            old_label = INQUIRY_TYPE_LABELS.get(old_values['inquiry_type'] or '', old_values['inquiry_type'] or '없음')
            new_label = INQUIRY_TYPE_LABELS.get(activity.inquiry_type or '', activity.inquiry_type or '없음')
            logs_to_add.append(SalesActivityLog(
                activity_id=activity_id,
                log_type='INQUIRY_TYPE',
                content=f"{old_label} → {new_label}",
                logged_by=logged_by,
            ))

        # 현재 단계 변경만 로그 기록 (다음 단계는 로그 안 남김)
        current_changed = 'current_step' in update_data and (old_values['current_step'] or '') != (activity.current_step or '')
        next_changed = 'next_step' in update_data and (old_values['next_step'] or '') != (activity.next_step or '')

        # "진행" 동작 감지: 이전 next_step이 새 current_step이 되고, next_step이 비워진 경우
        is_advance = (
            current_changed and next_changed
            and old_values['next_step']
            and (activity.current_step or '') == (old_values['next_step'] or '')
            and not activity.next_step
        )

        if is_advance:
            old_current = old_values['current_step'] or '(시작)'
            logs_to_add.append(SalesActivityLog(
                activity_id=activity_id,
                log_type='STEP_UPDATE',
                content=f"{old_current} → {activity.current_step}",
                logged_by=logged_by,
            ))
        elif current_changed and activity.current_step:
            logs_to_add.append(SalesActivityLog(
                activity_id=activity_id,
                log_type='STEP_UPDATE',
                content=f"현재: {activity.current_step}",
                    logged_by=logged_by,
                ))

        if 'pending_reason' in update_data and (old_values['pending_reason'] or '') != (activity.pending_reason or ''):
            new_value = activity.pending_reason or '(비움)'
            logs_to_add.append(SalesActivityLog(
                activity_id=activity_id,
                log_type='PENDING_REASON',
                content=new_value,
                logged_by=logged_by,
            ))

        if 'assigned_to' in update_data and (old_values['assigned_to'] or '') != (activity.assigned_to or ''):
            old_value = old_values['assigned_to'] or '없음'
            new_value = activity.assigned_to or '없음'
            logs_to_add.append(SalesActivityLog(
                activity_id=activity_id,
                log_type='ASSIGNEE',
                content=f"{old_value} → {new_value}",
                logged_by=logged_by,
            ))

        for log in logs_to_add:
            self.db.add(log)

        self.db.commit()
        self.db.refresh(activity)
        return activity

    def delete(self, activity_id: int) -> bool:
        activity = self.db.query(SalesActivity).filter(SalesActivity.id == activity_id).first()
        if not activity:
            return False
        # 연결된 영업문서(견적서/PI/CI)는 삭제하지 않고 연결만 해제 — FK(RESTRICT) 위반 방지, 문서 보존
        from app.models.sales_document import SalesDocument
        self.db.query(SalesDocument).filter(
            SalesDocument.sales_activity_id == activity_id
        ).update({SalesDocument.sales_activity_id: None}, synchronize_session=False)
        self.db.delete(activity)  # logs 는 cascade(all, delete-orphan)로 함께 삭제
        self.db.commit()
        return True

    # ==================== 코멘트 ====================

    def add_log(self, activity_id: int, data: SalesActivityLogCreate) -> Optional[SalesActivityLog]:
        activity = self.db.query(SalesActivity).filter(SalesActivity.id == activity_id).first()
        if not activity:
            return None

        # NEXT_STEP은 필드만 업데이트, 로그 안 남김
        if data.log_type == "NEXT_STEP":
            activity.next_step = data.content
            self.db.commit()
            return None

        log = SalesActivityLog(
            activity_id=activity_id,
            log_type=data.log_type or "COMMENT",
            content=data.content,
            logged_by=data.logged_by,
        )
        self.db.add(log)

        # 현재 단계/지연 사유는 로그 + 본 필드도 업데이트
        if data.log_type == "CURRENT_STATUS":
            activity.current_step = data.content
        elif data.log_type == "PENDING_REASON":
            activity.pending_reason = data.content

        self.db.commit()
        self.db.refresh(log)
        return log

    def get_logs(self, activity_id: int) -> List[SalesActivityLog]:
        return self.db.query(SalesActivityLog).filter(
            SalesActivityLog.activity_id == activity_id
        ).order_by(desc(SalesActivityLog.created_at)).all()

    # ==================== 담당자 목록 ====================

    def get_assignees(self) -> List[str]:
        """등록된 담당자 목록 (개별 인원 단위, 중복 제거)

        assigned_to는 자유 텍스트로 "김민정, 유현성"처럼 다중 담당자가
        콤마로 묶여 저장될 수 있어, 콤마 단위로 분해해 개별 이름을 반환한다.
        """
        results = self.db.query(SalesActivity.assigned_to).filter(
            SalesActivity.assigned_to.isnot(None),
            SalesActivity.assigned_to != "",
        ).distinct().all()
        names: set[str] = set()
        for (raw,) in results:
            for name in (raw or "").split(","):
                cleaned = name.strip()
                if cleaned:
                    names.add(cleaned)
        return sorted(names)

    # ==================== 자동 보류 (배치) ====================

    def auto_hold_stale(self, days: int = 180) -> dict:
        """마지막 활동(히스토리 로그, 없으면 생성일)이 days일 이전인 진행중/대기 건을
        자동으로 보류(ON_HOLD)로 전환하고, 각 건 타임라인에 AUTO_HOLD 로그를 남긴다.
        - 대상 상태: IN_PROGRESS, WAITING (완료/보류/무산 제외 → 이미 보류된 건은 재처리 안 됨)
        - 자동 복귀 없음(수동). 반환=처리 요약."""
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        # 활동별 마지막 로그 시각
        last_log_sq = (
            self.db.query(
                SalesActivityLog.activity_id.label("activity_id"),
                sa_func.max(SalesActivityLog.created_at).label("last_log"),
            )
            .group_by(SalesActivityLog.activity_id)
            .subquery()
        )
        activities = (
            self.db.query(SalesActivity)
            .outerjoin(last_log_sq, last_log_sq.c.activity_id == SalesActivity.id)
            .filter(SalesActivity.status.in_(["IN_PROGRESS", "WAITING"]))
            .filter(sa_func.coalesce(last_log_sq.c.last_log, SalesActivity.created_at) < cutoff)
            .all()
        )
        held = []
        for a in activities:
            a.status = "ON_HOLD"
            self.db.add(SalesActivityLog(
                activity_id=a.id,
                log_type="AUTO_HOLD",
                content=f"{days}일 미활동으로 자동 보류 처리됨",
                logged_by="시스템",
            ))
            held.append({"id": a.id, "title": a.title})
        self.db.commit()
        return {"held_count": len(held), "cutoff": cutoff.isoformat(), "held": held}
