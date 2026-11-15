"""WeasyPrint 폰트 환경 — Phase 1 Step 5

본 모듈 import 시:
1. MSYS2 harfbuzz 13.x ABI 비호환 우회 (fonttools 기반 fallback 활성화)
2. (옵션) verify_fonts()로 필수 폰트 파일 존재 여부 점검

폰트 등록 자체는 templates/pdf/styles/common.css 의 @font-face가 담당.
WeasyPrint가 base_url 기준으로 자동 해석.
"""

from pathlib import Path
from typing import List

# (1) harfbuzz subset 우회 — heap corruption 방지
#     상세 사유: docs/PDF_SETUP.md 5번 섹션 참고
from weasyprint.pdf import fonts as _wp_fonts
_wp_fonts.harfbuzz_subset = None


REQUIRED_FONTS = (
    "NotoSans-Regular.ttf",
    "NotoSans-Bold.ttf",
    "NotoSansKR-Regular.ttf",
    "NotoSansKR-Bold.ttf",
)


def verify_fonts(template_dir: Path) -> List[str]:
    """필수 폰트 파일 누락 여부 점검. 누락 파일명 리스트 반환 (정상 시 빈 리스트)."""
    fonts_dir = template_dir / "assets" / "fonts"
    return [name for name in REQUIRED_FONTS if not (fonts_dir / name).exists()]
