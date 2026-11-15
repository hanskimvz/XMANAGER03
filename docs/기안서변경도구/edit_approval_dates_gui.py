"""
전자결재 날짜 직접 수정 — 데스크톱 GUI (Tkinter)

edit_approval_dates.py(CLI)의 시간대 변환/저장 로직을 재사용한 그래픽 버전.
문서를 불러와 날짜를 칸에서 직접 고치고 [저장]만 누르면 된다.

⚠️ CLI 와 동일하게 approval_corrections(정정 이력)를 남기지 않는다.
   되돌릴 수 없으므로 실행 전 DB 백업 권장. 출시 전 초기/이관 데이터 정리 용도.

실행:
  cd backend
  python -m scripts.edit_approval_dates_gui
  (또는 backend/scripts/전자결재_날짜수정.bat 더블클릭)

운영 DB 대상이면 실행 전 환경변수: set APP_ENV=production
"""

import calendar
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

# 경로 부트스트랩: 이 파일이 있는 폴더(번들)를 import 경로에 추가 — 앱 비의존
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# CLI 모듈의 검증된 헬퍼 재사용 (tz 해석 포함 — tzdata 없는 Windows 폴백 공유)
from edit_approval_dates import DEFAULT_TZ, parse_local_to_utc, resolve_tz  # noqa: E402

# 독립 DB 계층(앱 패키지 비의존). DB URL 은 db_config.ini / XMANAGER_DB_URL 로 해석.
from approval_db import ApprovalDocument, get_session  # noqa: E402


def to_edit_string(dt, tz_name: str) -> str:
    """저장된 UTC datetime → 편집용 지역시간 문자열(빈 값은 '')."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(resolve_tz(tz_name))
    return dt.strftime("%Y-%m-%d %H:%M:%S")


_LOOSE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def parse_loose(text: str):
    """편집칸 문자열(지역시간) → naive datetime. 비었거나 해석 실패 시 None."""
    text = (text or "").strip()
    if not text:
        return None
    for fmt in _LOOSE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _attach_tooltip(widget, text):
    """간단한 호버 툴팁(순수 Tkinter)."""
    tip = {"win": None}

    def show(_e):
        if tip["win"] or not text:
            return
        x = widget.winfo_rootx() + 18
        y = widget.winfo_rooty() + 18
        win = tk.Toplevel(widget)
        win.wm_overrideredirect(True)
        win.wm_geometry(f"+{x}+{y}")
        tk.Label(win, text=text, bg="#333", fg="white", padx=6, pady=3,
                 font=("Segoe UI", 8), justify="left").pack()
        tip["win"] = win

    def hide(_e):
        if tip["win"]:
            tip["win"].destroy()
            tip["win"] = None

    widget.bind("<Enter>", show)
    widget.bind("<Leave>", hide)


class CalendarPopup(tk.Toplevel):
    """순수 Tkinter 달력 팝업 — 날짜 클릭 + 시:분 선택. 확인 시 콜백으로 문자열 전달."""

    _WEEK = ("일", "월", "화", "수", "목", "금", "토")

    def __init__(self, master, initial_text, on_pick):
        super().__init__(master)
        self.on_pick = on_pick
        self.title("날짜 선택")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        base = parse_loose(initial_text) or datetime.now().replace(microsecond=0)
        self.year = base.year
        self.month = base.month
        self.sel_day = base.day
        self.sec = base.second
        self.hour_var = tk.StringVar(value=f"{base.hour:02d}")
        self.min_var = tk.StringVar(value=f"{base.minute:02d}")
        self._day_btns = []

        self._build()
        self._render_month()
        # 팝업을 부모 근처에 배치
        self.update_idletasks()
        self.geometry(f"+{master.winfo_rootx() + 120}+{master.winfo_rooty() + 120}")

    def _build(self):
        # 월 이동 헤더
        head = ttk.Frame(self)
        head.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Button(head, text="◀", width=3, command=lambda: self._shift(-1)).pack(side="left")
        self.title_lbl = ttk.Label(head, text="", font=("Segoe UI", 10, "bold"), anchor="center")
        self.title_lbl.pack(side="left", expand=True)
        ttk.Button(head, text="▶", width=3, command=lambda: self._shift(1)).pack(side="left")

        # 요일 헤더
        wk = ttk.Frame(self)
        wk.pack(padx=8)
        for i, name in enumerate(self._WEEK):
            fg = "#c0392b" if i == 0 else ("#2471a3" if i == 6 else "#333")
            tk.Label(wk, text=name, width=4, fg=fg, font=("Segoe UI", 9, "bold")).grid(row=0, column=i, padx=1, pady=1)

        # 날짜 그리드
        self.grid_frame = ttk.Frame(self)
        self.grid_frame.pack(padx=8, pady=2)

        # 시:분 선택
        timef = ttk.Frame(self)
        timef.pack(fill="x", padx=8, pady=(6, 2))
        ttk.Label(timef, text="시각:").pack(side="left")
        ttk.Spinbox(timef, from_=0, to=23, width=4, textvariable=self.hour_var,
                    format="%02.0f", wrap=True).pack(side="left", padx=(4, 2))
        ttk.Label(timef, text=":").pack(side="left")
        ttk.Spinbox(timef, from_=0, to=59, width=4, textvariable=self.min_var,
                    format="%02.0f", wrap=True).pack(side="left", padx=2)

        # 하단 버튼
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=8, pady=(4, 8))
        ttk.Button(btns, text="오늘", command=self._today).pack(side="left")
        ttk.Button(btns, text="지우기(없음)", command=self._clear).pack(side="left", padx=4)
        ttk.Button(btns, text="확인", command=self._confirm).pack(side="right")

    def _shift(self, delta):
        m = self.month + delta
        y = self.year
        if m < 1:
            m = 12; y -= 1
        elif m > 12:
            m = 1; y += 1
        self.year, self.month = y, m
        self._render_month()

    def _today(self):
        now = datetime.now()
        self.year, self.month, self.sel_day = now.year, now.month, now.day
        self.hour_var.set(f"{now.hour:02d}")
        self.min_var.set(f"{now.minute:02d}")
        self.sec = 0
        self._render_month()

    def _render_month(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self._day_btns.clear()
        self.title_lbl.config(text=f"{self.year}년 {self.month}월")
        cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
        # 선택일이 이 달 범위를 벗어나면 보정
        last_day = calendar.monthrange(self.year, self.month)[1]
        if self.sel_day > last_day:
            self.sel_day = last_day
        for r, week in enumerate(cal.monthdayscalendar(self.year, self.month)):
            for c, day in enumerate(week):
                if day == 0:
                    tk.Label(self.grid_frame, text="", width=4).grid(row=r, column=c, padx=1, pady=1)
                    continue
                selected = (day == self.sel_day)
                fg = "#c0392b" if c == 0 else ("#2471a3" if c == 6 else "#000")
                b = tk.Button(
                    self.grid_frame, text=str(day), width=4,
                    relief="solid" if selected else "flat",
                    bg="#cfe3ff" if selected else "SystemButtonFace",
                    fg=fg, font=("Segoe UI", 9),
                    command=lambda d=day: self._select(d),
                )
                b.grid(row=r, column=c, padx=1, pady=1)
                self._day_btns.append(b)

    def _select(self, day):
        self.sel_day = day
        self._render_month()

    def _build_string(self):
        try:
            hh = max(0, min(23, int(self.hour_var.get() or 0)))
            mm = max(0, min(59, int(self.min_var.get() or 0)))
        except ValueError:
            hh, mm = 0, 0
        return f"{self.year:04d}-{self.month:02d}-{self.sel_day:02d} {hh:02d}:{mm:02d}:{self.sec:02d}"

    def _confirm(self):
        self.on_pick(self._build_string())
        self.destroy()

    def _clear(self):
        self.on_pick("")
        self.destroy()


class DateField(ttk.Frame):
    """편집 가능한 입력칸 + 달력(📅) 버튼. 기존 StringVar 에 그대로 바인딩.

    kind="input"   → ✏ 독립/입력값(기준). 사용자가 직접 정함.
    kind="derived" → 🔗 종속값. 기준값을 따라가야 함([시간 동기화]로 채움).
    """

    def __init__(self, master, var: tk.StringVar, width: int = 22, kind: str = "input"):
        super().__init__(master)
        self.var = var
        if kind == "derived":
            badge, color, tip = "🔗", "#2471a3", "종속값 — 기준 시간을 따라가야 함 ([시간 동기화]로 채움)"
        else:
            badge, color, tip = "✏", "#1e8449", "입력값(독립) — 직접 정하는 기준 시간"
        lbl = tk.Label(self, text=badge, fg=color, width=2)
        lbl.pack(side="left")
        _attach_tooltip(lbl, tip)
        self.entry = ttk.Entry(self, textvariable=var, width=width)
        self.entry.pack(side="left")
        ttk.Button(self, text="📅", width=3, command=self._open).pack(side="left", padx=(2, 0))

    def _open(self):
        CalendarPopup(self.winfo_toplevel(), self.var.get(), self.var.set)


class DateEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.tz_name = DEFAULT_TZ
        try:
            self.db = get_session()
        except Exception as e:
            messagebox.showerror("DB 연결 설정 필요", str(e))
            self.destroy()
            raise SystemExit
        self.doc = None
        self._line_vars = {}    # step_order -> StringVar
        self._action_vars = {}  # action_id -> StringVar
        self._line_meta = {}    # step_order -> {approver_id, status, approver_name}
        self._action_meta = {}  # action_id -> {actor_id, action, actor_name}

        self.title("전자결재 날짜 수정 도구")
        self.geometry("1080x740")
        self.minsize(940, 620)
        self.search_var = tk.StringVar()  # 선택된 문서 키(목록 선택 시 설정)
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.refresh_list()  # 시작 시 목록 채우기

    # ---------- UI 구성 ----------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # 경고 배너 (상단 전체 폭)
        env = os.getenv("APP_ENV", "(기본)")
        banner = tk.Label(
            self,
            text=(f"⚠️ 정정 이력 없이 직접 변경합니다 · 되돌릴 수 없음 · 실행 전 DB 백업 권장   "
                  f"[대상 환경: {env}]  [입력 시간대: {self.tz_name}]"),
            bg="#fff3cd", fg="#7a5b00", anchor="w", justify="left",
            font=("Segoe UI", 9), wraplength=1060,
        )
        banner.pack(fill="x")

        # 좌우 분할: 왼쪽 문서 목록 / 오른쪽 편집기
        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(paned, width=380)
        right = ttk.Frame(paned)
        paned.add(left, weight=0)
        paned.add(right, weight=1)

        self._build_list_panel(left)
        self._build_editor_panel(right)

    def _build_list_panel(self, parent):
        # 필터줄
        f = ttk.LabelFrame(parent, text="문서 목록 — 클릭하면 불러옵니다")
        f.pack(fill="both", expand=True)

        filt = ttk.Frame(f)
        filt.pack(fill="x", padx=6, pady=6)
        ttk.Label(filt, text="검색:").pack(side="left")
        self.filter_var = tk.StringVar()
        fent = ttk.Entry(filt, textvariable=self.filter_var, width=18)
        fent.pack(side="left", padx=4)
        fent.bind("<Return>", lambda e: self.refresh_list())
        self.status_filter = tk.StringVar(value="전체")
        ttk.Combobox(
            filt, textvariable=self.status_filter, width=12, state="readonly",
            values=["전체", "DRAFT", "IN_PROGRESS", "APPROVED", "REJECTED", "CANCELED"],
        ).pack(side="left", padx=2)
        ttk.Button(filt, text="조회", command=self.refresh_list).pack(side="left", padx=2)

        # 목록 (Treeview)
        cols = ("id", "doc_number", "status", "title")
        wrap = ttk.Frame(f)
        wrap.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        for c, (txt, w, anchor) in {
            "id": ("id", 48, "center"),
            "doc_number": ("문서번호", 110, "center"),
            "status": ("상태", 90, "center"),
            "title": ("제목", 200, "w"),
        }.items():
            self.tree.heading(c, text=txt)
            self.tree.column(c, width=w, anchor=anchor, stretch=(c == "title"))
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_list_select)

        self.list_count_var = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.list_count_var, foreground="#777").pack(anchor="w", padx=6, pady=(0, 4))

    def _build_editor_panel(self, parent):
        pad = {"padx": 8, "pady": 4}
        # 문서 정보
        info = ttk.LabelFrame(parent, text="문서 정보")
        info.pack(fill="x", **pad)
        self.lbl_doc = ttk.Label(info, text="왼쪽 목록에서 문서를 선택하세요.", font=("Segoe UI", 10, "bold"))
        self.lbl_doc.pack(anchor="w", padx=8, pady=6)

        # 문서 날짜 (created / drafted / completed)
        docdates = ttk.LabelFrame(parent, text="문서 날짜  (형식: YYYY-MM-DD HH:MM:SS · 비우면 '없음')")
        docdates.pack(fill="x", **pad)
        # 범례
        legend = ttk.Frame(docdates)
        legend.grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(2, 0))
        tk.Label(legend, text="✏ 입력(독립)", fg="#1e8449", font=("Segoe UI", 8)).pack(side="left")
        tk.Label(legend, text="   🔗 종속(자동 — [시간 동기화]로 채움)", fg="#2471a3",
                 font=("Segoe UI", 8)).pack(side="left")

        self.created_var = tk.StringVar()
        self.drafted_var = tk.StringVar()
        self.completed_var = tk.StringVar()
        self._date_row(docdates, "생성 (created_at)", self.created_var, 1, kind="input")
        self._date_row(docdates, "상신 (drafted_at)", self.drafted_var, 2, kind="input")
        self._date_row(docdates, "완료 (completed_at)", self.completed_var, 3, kind="derived")

        # 결재선
        lines_frame = ttk.LabelFrame(parent, text="결재선 — 처리 시각(acted_at) · 도장 날짜")
        lines_frame.pack(fill="both", expand=True, **pad)
        self.lines_inner = self._scrollable(lines_frame)

        # 감사이력
        actions_frame = ttk.LabelFrame(parent, text="감사이력(actions) — 행위 시각(acted_at)")
        actions_frame.pack(fill="both", expand=True, **pad)
        self.actions_inner = self._scrollable(actions_frame)

        # 하단 버튼
        bottom = ttk.Frame(parent)
        bottom.pack(fill="x", **pad)
        self.status_var = tk.StringVar(value="대기 중")
        ttk.Label(bottom, textvariable=self.status_var, foreground="#555").pack(side="left")
        ttk.Button(bottom, text="다시 불러오기", command=self.load_document).pack(side="right", padx=4)
        self.save_btn = ttk.Button(bottom, text="저장 (커밋)", command=self.save, state="disabled")
        self.save_btn.pack(side="right", padx=4)
        self.sync_btn = ttk.Button(bottom, text="🔗 시간 동기화", command=self.sync_times, state="disabled")
        self.sync_btn.pack(side="right", padx=4)
        self.check_btn = ttk.Button(bottom, text="🔍 무결성 검사", command=self.check_integrity, state="disabled")
        self.check_btn.pack(side="right", padx=4)

    # ---------- 목록 ----------
    def refresh_list(self):
        """필터 조건으로 문서 목록을 다시 조회해 Treeview 갱신 (최신 300건)."""
        self.db.expire_all()
        q = self.db.query(ApprovalDocument)
        kw = (self.filter_var.get() or "").strip()
        if kw:
            like = f"%{kw}%"
            q = q.filter(
                (ApprovalDocument.doc_number.ilike(like)) | (ApprovalDocument.title.ilike(like))
            )
        st = self.status_filter.get()
        if st and st != "전체":
            q = q.filter(ApprovalDocument.status == st)
        rows = q.order_by(ApprovalDocument.id.desc()).limit(300).all()

        self.tree.delete(*self.tree.get_children())
        for d in rows:
            self.tree.insert("", "end", iid=str(d.id),
                             values=(d.id, d.doc_number, d.status, d.title or ""))
        self.list_count_var.set(f"{len(rows)}건 표시 (최신순, 최대 300)")

    def on_list_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self.search_var.set(sel[0])  # iid = 문서 id
        self.load_document()

    def _date_row(self, parent, label, var, row, kind="input"):
        ttk.Label(parent, text=label, width=22).grid(row=row, column=0, sticky="w", padx=8, pady=3)
        DateField(parent, var, width=24, kind=kind).grid(row=row, column=1, sticky="w", pady=3)

    def _scrollable(self, parent):
        """세로 스크롤 가능한 내부 프레임 반환."""
        canvas = tk.Canvas(parent, highlightthickness=0, height=140)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return inner

    # ---------- 동작 ----------
    def load_document(self):
        key = self.search_var.get().strip()
        if not key:
            messagebox.showinfo("안내", "문서번호 또는 id 를 입력하세요.")
            return
        # 세션 캐시 회피 위해 새로 조회
        self.db.expire_all()
        q = self.db.query(ApprovalDocument)
        doc = None
        if key.isdigit():
            doc = q.filter(ApprovalDocument.id == int(key)).first()
        if doc is None:
            doc = q.filter(ApprovalDocument.doc_number == key).first()
        if not doc:
            messagebox.showerror("오류", f"문서를 찾을 수 없습니다: {key}")
            return

        self.doc = doc
        self.lbl_doc.config(
            text=f"#{doc.id}  {doc.doc_number}  [{doc.status}]   {doc.title or ''}"
        )
        self.created_var.set(to_edit_string(doc.created_at, self.tz_name))
        self.drafted_var.set(to_edit_string(doc.drafted_at, self.tz_name))
        self.completed_var.set(to_edit_string(doc.completed_at, self.tz_name))

        # 결재선 렌더
        for w in self.lines_inner.winfo_children():
            w.destroy()
        self._line_vars.clear()
        self._line_meta.clear()
        header = ttk.Frame(self.lines_inner); header.pack(fill="x")
        for t, w in (("순서", 6), ("상태", 10), ("결재자", 18), ("처리시각 acted_at", 26)):
            ttk.Label(header, text=t, width=w, font=("Segoe UI", 9, "bold")).pack(side="left", padx=2)
        for ln in sorted(doc.lines, key=lambda x: x.step_order):
            row = ttk.Frame(self.lines_inner); row.pack(fill="x", pady=1)
            approver = getattr(ln, "approver", None)
            who = f"{approver.name}" if approver else f"id={ln.approver_id}"
            ttk.Label(row, text=str(ln.step_order), width=6).pack(side="left", padx=2)
            ttk.Label(row, text=ln.status, width=10).pack(side="left", padx=2)
            ttk.Label(row, text=who, width=18).pack(side="left", padx=2)
            var = tk.StringVar(value=to_edit_string(ln.acted_at, self.tz_name))
            DateField(row, var, width=22, kind="input").pack(side="left", padx=2)
            self._line_vars[ln.step_order] = var
            self._line_meta[ln.step_order] = {
                "approver_id": ln.approver_id, "status": ln.status, "approver_name": who,
            }

        # 감사이력 렌더
        for w in self.actions_inner.winfo_children():
            w.destroy()
        self._action_vars.clear()
        self._action_meta.clear()
        header2 = ttk.Frame(self.actions_inner); header2.pack(fill="x")
        for t, w in (("id", 6), ("행위", 10), ("행위자", 18), ("행위시각 acted_at", 26)):
            ttk.Label(header2, text=t, width=w, font=("Segoe UI", 9, "bold")).pack(side="left", padx=2)
        for ac in sorted(doc.actions, key=lambda x: (x.acted_at or datetime.min.replace(tzinfo=timezone.utc))):
            row = ttk.Frame(self.actions_inner); row.pack(fill="x", pady=1)
            actor = getattr(ac, "actor", None)
            who = f"{actor.name}" if actor else f"id={ac.actor_id}"
            ttk.Label(row, text=str(ac.id), width=6).pack(side="left", padx=2)
            ttk.Label(row, text=ac.action, width=10).pack(side="left", padx=2)
            ttk.Label(row, text=who, width=18).pack(side="left", padx=2)
            var = tk.StringVar(value=to_edit_string(ac.acted_at, self.tz_name))
            DateField(row, var, width=22, kind="derived").pack(side="left", padx=2)
            self._action_vars[ac.id] = var
            self._action_meta[ac.id] = {
                "actor_id": ac.actor_id, "action": ac.action, "actor_name": who,
            }

        self.save_btn.config(state="normal")
        self.sync_btn.config(state="normal")
        self.check_btn.config(state="normal")
        self.status_var.set("불러옴 — 값을 고친 뒤 [저장]")

    def sync_times(self):
        """'같은 사건'인 시간들을 맞춤(미리보기 후 폼 값에 반영, 저장은 별도).

        규칙(결재선/문서 날짜 = master, 감사이력/완료시각이 따라감):
          A) 결재선 step.acted_at  →  같은 결재자의 APPROVE/REJECT 감사이력
          B) 문서 drafted_at(상신) →  최신 SUBMIT/RESUBMIT 감사이력
          C) 문서 completed_at(완료) ←  최종 처리된 결재선 step
        """
        if not self.doc:
            return

        def cur(var):
            return (var.get() or "").strip()

        plans = []   # (StringVar, new_text, desc)
        warns = []

        # A) 결재선(master) → 매칭 감사이력 (같은 결재자 + APPROVE/REJECT)
        for step, meta in sorted(self._line_meta.items()):
            if meta["status"] not in ("APPROVED", "REJECTED"):
                continue
            line_text = cur(self._line_vars[step])
            if not line_text:
                continue
            want = "APPROVE" if meta["status"] == "APPROVED" else "REJECT"
            cands = [aid for aid, am in self._action_meta.items()
                     if am["action"] == want and am["actor_id"] == meta["approver_id"]]
            if len(cands) == 1:
                aid = cands[0]
                if cur(self._action_vars[aid]) != line_text:
                    plans.append((self._action_vars[aid], line_text,
                                  f"감사이력#{aid} {want}({meta['approver_name']}) ← 결재선 step{step}"))
            elif len(cands) > 1:
                warns.append(f"step{step}({meta['approver_name']}) {want} 이력이 {len(cands)}건 → 수동 확인 필요")

        # B) 상신(drafted_at, master) → 최신 SUBMIT/RESUBMIT 감사이력
        submit_aids = [aid for aid, am in self._action_meta.items()
                       if am["action"] in ("SUBMIT", "RESUBMIT")]
        drafted_text = cur(self.drafted_var)
        if submit_aids and drafted_text:
            latest = max(submit_aids, key=lambda a: (parse_loose(cur(self._action_vars[a])) or datetime.min))
            if cur(self._action_vars[latest]) != drafted_text:
                plans.append((self._action_vars[latest], drafted_text,
                              f"감사이력#{latest} 상신 ← 문서.drafted_at"))

        # C) 완료(completed_at) ← 최종 처리된 결재선
        final_step = self._final_step()
        if final_step is not None:
            final_text = cur(self._line_vars[final_step])
            if final_text and cur(self.completed_var) != final_text:
                plans.append((self.completed_var, final_text,
                              f"문서.completed_at ← 결재선 step{final_step}(최종 처리)"))

        if not plans and not warns:
            messagebox.showinfo("시간 동기화", "이미 모든 참조 시간이 일치합니다.")
            return

        msg = "아래처럼 폼 값을 맞춥니다. (미리보기 — 아직 DB 반영 안 됨, [저장]으로 확정)\n\n"
        msg += "\n".join(f"• {d}" for _, _, d in plans) if plans else "(맞출 항목 없음)"
        if warns:
            msg += "\n\n⚠️ 수동 확인 필요:\n" + "\n".join(f"• {w}" for w in warns)
        msg += "\n\n적용할까요?"
        if not messagebox.askyesno("시간 동기화", msg):
            return
        for var, text, _ in plans:
            var.set(text)
        self.status_var.set(f"동기화 {len(plans)}건 반영(폼) — 확인 후 [저장]")

    def _final_step(self):
        """최종 처리된 결재선 step_order (완료시각의 기준). 없으면 None."""
        status = self.doc.status if self.doc else None
        if status == "REJECTED":
            rej = [s for s, m in self._line_meta.items() if m["status"] == "REJECTED"]
            return max(rej) if rej else None
        if status == "APPROVED":
            appr = [s for s, m in self._line_meta.items() if m["status"] == "APPROVED"]
            return max(appr) if appr else None
        return None

    def _collect_values(self):
        """폼의 모든 날짜칸을 파싱(UTC). 형식 오류 시 ValueError."""
        doc_new = {
            "created_at": self._coerce(self.created_var.get()),
            "drafted_at": self._coerce(self.drafted_var.get()),
            "completed_at": self._coerce(self.completed_var.get()),
        }
        line_new = {step: self._coerce(v.get()) for step, v in self._line_vars.items()}
        action_new = {aid: self._coerce(v.get()) for aid, v in self._action_vars.items()}
        return doc_new, line_new, action_new

    def _integrity_errors(self, doc_new, line_new, action_new):
        """저장 예정 값들의 정합성 검사. 위반 메시지 리스트 반환(비면 정상)."""
        MIN = datetime.min.replace(tzinfo=timezone.utc)
        errs = []
        status = self.doc.status if self.doc else None

        def af(dt):
            return to_edit_string(dt, self.tz_name) or "없음"

        # ----- 존재성 -----
        if status and status != "DRAFT" and doc_new["drafted_at"] is None:
            errs.append("상신(drafted_at)이 비어 있음 — 상신된 문서는 상신시각이 있어야 합니다.")
        if status in ("APPROVED", "REJECTED", "CANCELED") and doc_new["completed_at"] is None:
            errs.append("완료(completed_at)가 비어 있음 — 완료/반려/회수 문서는 완료시각이 있어야 합니다.")
        for step, meta in self._line_meta.items():
            if meta["status"] in ("APPROVED", "REJECTED") and line_new.get(step) is None:
                errs.append(f"결재선 step{step}({meta['approver_name']})은 처리됨인데 처리시각이 비어 있음.")

        # ----- 동일성(짝이 같아야 함) -----
        # E1: 상신 == 최신 SUBMIT/RESUBMIT 이력
        submit_aids = [a for a, m in self._action_meta.items() if m["action"] in ("SUBMIT", "RESUBMIT")]
        if submit_aids and doc_new["drafted_at"] is not None:
            latest = max(submit_aids, key=lambda a: action_new.get(a) or MIN)
            if action_new.get(latest) is None or _norm(doc_new["drafted_at"]) != _norm(action_new[latest]):
                errs.append(f"상신({af(doc_new['drafted_at'])}) ≠ SUBMIT 이력#{latest}({af(action_new.get(latest))}) — [시간 동기화] 필요")
        # E2: 결재선 == 같은 결재자의 APPROVE/REJECT 이력
        for step, meta in self._line_meta.items():
            if meta["status"] not in ("APPROVED", "REJECTED"):
                continue
            lv = line_new.get(step)
            if lv is None:
                continue
            want = "APPROVE" if meta["status"] == "APPROVED" else "REJECT"
            cands = [a for a, m in self._action_meta.items()
                     if m["action"] == want and m["actor_id"] == meta["approver_id"]]
            if len(cands) == 1:
                av = action_new.get(cands[0])
                if av is None or _norm(av) != _norm(lv):
                    errs.append(f"결재선 step{step}({meta['approver_name']} {af(lv)}) ≠ {want} 이력#{cands[0]}({af(av)}) — [시간 동기화] 필요")
        # E3: 완료 == 최종 결재선
        fs = self._final_step()
        if fs is not None and line_new.get(fs) is not None and doc_new["completed_at"] is not None:
            if _norm(line_new[fs]) != _norm(doc_new["completed_at"]):
                errs.append(f"완료({af(doc_new['completed_at'])}) ≠ 최종 결재선 step{fs}({af(line_new[fs])}) — [시간 동기화] 필요")

        # ----- 시간 순서 -----
        if doc_new["created_at"] and doc_new["drafted_at"] and doc_new["created_at"] > doc_new["drafted_at"]:
            errs.append(f"생성({af(doc_new['created_at'])}) > 상신({af(doc_new['drafted_at'])}): 생성이 더 늦습니다.")
        acted = [(s, line_new[s]) for s in sorted(line_new) if line_new.get(s) is not None]
        if doc_new["drafted_at"] and acted and doc_new["drafted_at"] > acted[0][1]:
            errs.append(f"상신({af(doc_new['drafted_at'])}) > 1차 결재 step{acted[0][0]}({af(acted[0][1])}): 결재가 상신보다 빠릅니다.")
        for i in range(len(acted) - 1):
            (s0, v0), (s1, v1) = acted[i], acted[i + 1]
            if v0 > v1:
                errs.append(f"결재 순서 역전: step{s0}({af(v0)}) > step{s1}({af(v1)})")
        return errs

    def check_integrity(self):
        """무결성 검사만 수행(저장 안 함). 결과를 알림으로 표시."""
        if not self.doc:
            return
        try:
            vals = self._collect_values()
        except ValueError as e:
            messagebox.showerror("날짜 형식 오류", str(e))
            return
        errs = self._integrity_errors(*vals)
        if errs:
            messagebox.showwarning("무결성 검사 — 문제 발견",
                                   "\n".join(f"• {e}" for e in errs))
            self.status_var.set(f"무결성 위반 {len(errs)}건 — 저장 불가")
        else:
            messagebox.showinfo("무결성 검사", "✅ 시간 정합성·순서가 모두 일치합니다.")
            self.status_var.set("무결성 OK")

    def _coerce(self, raw: str):
        """빈 문자열 → None, 아니면 UTC datetime."""
        raw = (raw or "").strip()
        if raw == "":
            return None
        return parse_local_to_utc(raw, self.tz_name)

    def save(self):
        if not self.doc:
            return
        try:
            # 1) 입력 전부 먼저 파싱 (오류 시 아무것도 반영 안 함)
            doc_new, line_new, action_new = self._collect_values()
        except ValueError as e:
            messagebox.showerror("날짜 형식 오류", str(e))
            return

        # 1.5) 무결성 검사 — 위반 시 저장 차단
        errs = self._integrity_errors(doc_new, line_new, action_new)
        if errs:
            messagebox.showerror(
                "무결성 위반 — 저장할 수 없습니다",
                "아래 문제를 해결한 뒤 저장하세요. 대부분 [🔗 시간 동기화]로 자동 해결됩니다.\n\n"
                + "\n".join(f"• {e}" for e in errs),
            )
            self.status_var.set(f"무결성 위반 {len(errs)}건 — 저장 차단됨")
            return

        # 2) 변경 요약
        changes = []
        for field, new in doc_new.items():
            old = getattr(self.doc, field)
            if _norm(old) != _norm(new):
                changes.append(f"문서.{field}: {to_edit_string(old, self.tz_name) or '없음'} → "
                               f"{to_edit_string(new, self.tz_name) or '없음'}")
        lines_by_step = {ln.step_order: ln for ln in self.doc.lines}
        for step, new in line_new.items():
            ln = lines_by_step[step]
            if _norm(ln.acted_at) != _norm(new):
                changes.append(f"결재선 step{step}.acted_at: {to_edit_string(ln.acted_at, self.tz_name) or '없음'} → "
                               f"{to_edit_string(new, self.tz_name) or '없음'}")
        actions_by_id = {ac.id: ac for ac in self.doc.actions}
        for aid, new in action_new.items():
            ac = actions_by_id[aid]
            if _norm(ac.acted_at) != _norm(new):
                changes.append(f"이력 id{aid}.acted_at: {to_edit_string(ac.acted_at, self.tz_name) or '없음'} → "
                               f"{to_edit_string(new, self.tz_name) or '없음'}")

        if not changes:
            messagebox.showinfo("안내", "변경된 항목이 없습니다.")
            return

        msg = ("아래 변경을 저장합니다. (정정 이력 없이 직접 반영 · 되돌릴 수 없음)\n\n"
               + "\n".join(changes[:30])
               + ("\n…" if len(changes) > 30 else ""))
        if not messagebox.askyesno("저장 확인", msg):
            return

        # 3) 반영 + 커밋
        try:
            for field, new in doc_new.items():
                setattr(self.doc, field, new)
            for step, new in line_new.items():
                lines_by_step[step].acted_at = new
            for aid, new in action_new.items():
                actions_by_id[aid].acted_at = new
            self.db.commit()
            self.db.refresh(self.doc)
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("저장 실패", str(e))
            self.status_var.set("저장 실패 — 롤백됨")
            return

        self.status_var.set(f"저장 완료 ({len(changes)}건)")
        messagebox.showinfo("완료", f"{len(changes)}건 저장되었습니다.")
        self.load_document()  # 갱신된 값 다시 표시

    def _on_close(self):
        try:
            self.db.close()
        finally:
            self.destroy()


def _norm(dt):
    """비교용: tz-aware UTC 로 정규화(없으면 None)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0)


if __name__ == "__main__":
    DateEditorApp().mainloop()
