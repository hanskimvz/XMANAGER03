"""
전자결재 인쇄(HTML) 렌더 서비스 (v0.34.0)

approval_ko.html(Jinja2) → HTML 문자열. weasyprint 미사용(브라우저 인쇄용 HTML).
도장은 seal_service.make_seal_svg 로 승인된 결재 라인 칸에 삽입한다.
검증번호 = SHA256(doc_number+content) 앞 4 hex 대문자.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from markupsafe import Markup

from app.core.config import settings
from app.core.storage_paths import resolve_approval_path
from app.models.approval import ApprovalDocument
from app.services import seal_service
from app.services.pdf.highlight import apply_highlights

# 템플릿 디렉토리 — backend/app/templates/pdf
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "pdf"

_env: Optional[Environment] = None


def _get_env() -> Environment:
    global _env
    if _env is None:
        _env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )
    return _env


def _verify_code(doc_number: str, content: Optional[str]) -> str:
    raw = (doc_number or "") + (content or "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:4].upper()


def _fmt_dt(dt) -> str:
    if not dt:
        return ""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M")
    return str(dt)


def _fmt_date(dt) -> str:
    if not dt:
        return ""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d")
    return str(dt)


def _fmt_num(v) -> str:
    """천단위 콤마 + 소수 최대 2자리(불필요한 0 제거). 1000→'1,000', 3.5→'3.5', 0.30000000000000004→'0.3'."""
    try:
        n = round(float(v or 0), 2)
    except (TypeError, ValueError):
        return str(v)
    if n.is_integer():
        return f"{int(n):,}"
    return f"{n:,.2f}".rstrip("0").rstrip(".")


def _fmt_date_kr(dt) -> str:
    """YYYY년 M월 D일 (서명부용). 문자열(YYYY-MM-DD)도 허용."""
    if not dt:
        return ""
    d = dt
    if not isinstance(d, datetime):
        try:
            d = datetime.strptime(str(dt)[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return str(dt)
    return f"{d.year}년 {d.month}월 {d.day}일"


_STATUS_LABEL = {
    "DRAFT": "임시저장",
    "IN_PROGRESS": "결재중",
    "APPROVED": "승인완료",
    "REJECTED": "반려",
    "CANCELED": "회수",
}


def render_html(
    doc: ApprovalDocument,
    show_history: bool = True,
    show_references: bool = True,
    show_print_date: bool = True,
    show_attachments: bool = True,
    show_doc_number: bool = True,
) -> str:
    """결재 문서 → 인쇄용 HTML 문자열. 각 show_* 옵션으로 섹션 출력 여부 제어.

    show_doc_number=False 면 상단 메타표·하단 푸터의 문서번호/검증번호를 숨긴다.
    """
    drafter = doc.drafter
    form = doc.form

    # 결재란 칸: 기안 + 결재선 단계들
    cells = []
    cells.append({
        "role": "기안",
        "name": drafter.name if drafter else "",
        "seal_svg": seal_service.make_seal_svg(
            (drafter.seal_text or drafter.name) if drafter else "",
            _fmt_date(doc.drafted_at or doc.created_at),
        ) if (drafter and doc.drafted_at) else "",
        "date": _fmt_date(doc.drafted_at),
        "pending": False,
    })
    _sorted_lines = sorted(doc.lines, key=lambda l: l.step_order)
    _last_idx = len(_sorted_lines) - 1
    for _idx, line in enumerate(_sorted_lines):
        approver = line.approver
        name = line.approver_name or (approver.name if approver else "")
        position = line.approver_position or (approver.position if approver else "")
        approved = line.status == "APPROVED" and line.acted_at
        seal_svg = ""
        if approved:
            seal_name = name or (approver.seal_text if approver else "") or ""
            seal_svg = seal_service.make_seal_svg(seal_name, _fmt_date(line.acted_at))
        # 단계 표기: 마지막은 '최종', 그 외는 'N단'
        step_role = "최종" if _idx == _last_idx else f"{_idx + 1}단"
        cells.append({
            "role": step_role,
            "name": name,
            "seal_svg": seal_svg,
            "date": _fmt_date(line.acted_at),
            "pending": line.status in ("WAITING", "PENDING"),
        })

    # 양식 필드(form_data) → 라벨/값 표
    form_rows = []
    if form and form.fields_schema:
        data = doc.form_data or {}
        # 통화(구매기안서/지출결의서) — 금액 표기 단위
        _cur = str(data.get("currency") or "KRW")
        _cur_sfx = {"KRW": "원", "USD": "USD", "JPY": "JPY", "CNY": "CNY", "EUR": "EUR"}.get(_cur, _cur)
        for field in form.fields_schema:
            if not isinstance(field, dict):
                continue
            key = field.get("key")
            val = data.get(key) if key else None
            if val is None:
                val = ""
            _vat_note = "부가세 포함 금액" if data.get("vat_included") else "부가세 별도 (VAT 미포함)"
            if key == "items" and data.get("items_mode") == "FREE":
                # 자유형식 품목: 자유 텍스트 그대로 출력(표 아님) + 부가세 표시
                val = str(data.get("items_free") or "")
                val = (val + "\n" if val else "") + f"※ {_vat_note}"
            elif key == "items" and isinstance(val, (list, tuple)):
                # 품목 표: "품목  수량 x 단가 = 금액" 줄 + 합계
                lines = []
                total = 0
                for v in val:
                    if not isinstance(v, dict):
                        lines.append(str(v))
                        continue
                    nm = v.get("name", "")
                    qty = v.get("qty", 0) or 0
                    up = v.get("unit_price", 0) or 0
                    amt = v.get("amount", (qty or 0) * (up or 0)) or 0
                    total += amt
                    note = (v.get("note") or "").strip()
                    line = f"{nm}  {qty} x {_fmt_num(up)} = {_fmt_num(amt)}"
                    if note:
                        line += f"  ({note})"
                    lines.append(line)
                if lines:
                    lines.append(f"합계: {_fmt_num(total)} {_cur_sfx}  (※ {_vat_note})")
                val = "\n".join(lines)
            elif isinstance(val, (list, tuple)):
                # 참석자 등 객체 배열: 각 항목의 값을 공백으로(예: 소속 이름 직책), 항목은 줄바꿈으로
                parts = []
                for v in val:
                    if isinstance(v, dict):
                        parts.append(" ".join(str(x) for x in v.values() if x not in (None, "")))
                    else:
                        parts.append(str(v))
                val = "\n".join(p for p in parts if p)
            elif field.get("type") == "number" and key != "days" and isinstance(val, (int, float)):
                # 금액계열 스칼라(number, 휴가 일수 제외): 천단위 + 통화 단위
                val = f"{_fmt_num(val)} {_cur_sfx}"
            form_rows.append({"label": field.get("label") or key, "value": val})
            # 과제 구매기안서: 품목 바로 아래 RCMS 항목(비목)·세부항목
            if key == "items" and data.get("budget_item"):
                cat = str(data.get("budget_category") or "").strip()
                item = str(data.get("budget_item") or "").strip()
                form_rows.append({"label": "항목", "value": f"[{cat}] {item}" if cat else item})
                form_rows.append({"label": "세부항목", "value": str(data.get("budget_detail") or "-")})

    # 처리 이력
    history = []
    action_label = {
        "SUBMIT": "상신", "APPROVE": "승인", "REJECT": "반려",
        "CANCEL": "회수", "RESUBMIT": "재상신",
    }
    for act in sorted(doc.actions, key=lambda a: (a.acted_at or datetime.min)):
        actor = act.actor
        history.append({
            "time": _fmt_dt(act.acted_at),
            "label": action_label.get(act.action, act.action),
            "actor": actor.name if actor else "",
            "comment": act.comment or "",
        })

    references = [
        {
            "name": ref.user.name if ref.user else "",
            "position": ref.user.position if ref.user else "",
        }
        for ref in doc.references
    ]
    import base64
    attachments = []
    for att in doc.attachments:
        ct = (att.content_type or "").lower()
        name_lower = (att.original_name or "").lower()
        is_image = ct.startswith("image/") or name_lower.endswith(
            (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
        )
        is_pdf = ct == "application/pdf" or name_lower.endswith(".pdf")
        data_uri = None
        if show_attachments and is_image:
            try:
                abs_path = resolve_approval_path(att.stored_path)
                with open(abs_path, "rb") as f:
                    raw = f.read()
                mime = ct if ct.startswith("image/") else "image/png"
                data_uri = f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
            except Exception:
                data_uri = None
        attachments.append({
            "original_name": att.original_name,
            "file_size": att.file_size,
            "is_image": is_image,
            "is_pdf": is_pdf,
            "data_uri": data_uri,
        })

    ctx = {
        "doc": doc,
        "company_name": settings.COMPANY_NAME,
        "form_name": form.name if form else "일반 기안서",
        "drafter_name": drafter.name if drafter else "",
        "drafter_dept": drafter.department if drafter else "",
        "drafter_position": drafter.position if drafter else "",
        "drafted_at": _fmt_date(doc.drafted_at),
        "created_at": _fmt_date(doc.created_at),
        "drafted_at_kr": _fmt_date_kr(doc.drafted_at or doc.created_at),
        # 프로젝트 — 작성 화면과 같은 "[코드] 이름" 표기 (지정된 문서만 출력)
        "project_name": (
            (f"[{doc.project.code}] {doc.project.name}" if doc.project.code else doc.project.name)
            if getattr(doc, "project", None) is not None else ""
        ),
        "status_label": _STATUS_LABEL.get(doc.status, doc.status),
        "cells": cells,
        "form_rows": form_rows,
        "history": history,
        "show_history": show_history,
        "show_references": show_references,
        "show_print_date": show_print_date,
        "show_attachments": show_attachments,
        "show_doc_number": show_doc_number,
        "references": references,
        "attachments": attachments,
        "verify_code": _verify_code(doc.doc_number, doc.content),
        "print_date": datetime.now().strftime("%Y-%m-%d"),
        # 본문 마크업 → HTML(하이라이트) + 줄바꿈(\n→<br>) 변환
        "content_html": Markup(str(apply_highlights(doc.content)).replace("\n", "<br>")) if doc.content else "",
    }

    template = _get_env().get_template("approval_ko.html")
    return template.render(**ctx)
