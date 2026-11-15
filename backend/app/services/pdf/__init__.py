"""견적서/PI/CI PDF 생성 모듈 (WeasyPrint 기반)

기존 발주서 PDF는 services/pdf_service.py (reportlab) — 이 모듈과 분리됨.

본 모듈을 import하면 services.pdf.fonts가 로드되며,
WeasyPrint의 harfbuzz subset 비호환 우회 패치가 자동 적용됩니다.
직접 weasyprint를 import하기 전에 반드시 이 모듈이 먼저 로드되어야 합니다.
"""
from app.services.pdf import fonts  # noqa: F401  -- 폰트 환경 설정 트리거 (필수)
