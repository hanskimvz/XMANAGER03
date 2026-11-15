"""Nextcloud 연동 서비스 (로컬 동기화 폴더 방식, v0.60.0).

X-Manager 서버(=이 컴퓨터)의 Nextcloud 동기화 폴더(NEXTCLOUD_BASE_PATH) 아래에
문서를 저장하면 데스크톱 클라이언트가 자동으로 xcloud 로 동기화한다.

폴더 구조:
  해외(거래처 국가≠한국): 수출/{YYYY}년 거래처별 수출/{국가}_{거래처명}/{문의건폴더}/
  국내(거래처 국가=한국):  국내판매/{YYYY}년 국내판매/{거래처명}/{문의건폴더}/
"""
import os
import re
import logging
from datetime import date

from app.core.config import settings

logger = logging.getLogger(__name__)

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_DOMESTIC_KEYS = ("한국", "대한민국", "국내")

# 폴더 규칙은 한글 국가명 기준 — 영문/코드로 등록된 경우를 위한 방어 매핑(엑셀 일괄등록 등 대비).
# 거래처 country_name 이 영문이면 한글로 정규화, 비어있으면 country_code(ISO)로 보완.
_EN_TO_KO = {
    "vietnam": "베트남", "germany": "독일", "hong kong": "홍콩", "hongkong": "홍콩",
    "uae": "아랍에미리트", "united arab emirates": "아랍에미리트", "japan": "일본",
    "china": "중국", "usa": "미국", "us": "미국", "united states": "미국",
    "united states of america": "미국", "uk": "영국", "united kingdom": "영국",
    "england": "영국", "india": "인도", "poland": "폴란드", "turkey": "튀르키예",
    "türkiye": "튀르키예", "turkiye": "튀르키예", "czech": "체코", "czech republic": "체코",
    "czechia": "체코", "israel": "이스라엘", "russia": "러시아", "spain": "스페인",
    "norway": "노르웨이", "korea": "대한민국", "south korea": "대한민국",
    "republic of korea": "대한민국", "romania": "루마니아", "italy": "이탈리아",
    "estonia": "에스토니아", "turkmenistan": "투르크메니스탄", "slovakia": "슬로바키아",
    "belarus": "벨라루스", "pakistan": "파키스탄", "egypt": "이집트", "sweden": "스웨덴",
    "netherlands": "네덜란드", "australia": "호주", "france": "프랑스", "taiwan": "대만",
    "thailand": "태국", "indonesia": "인도네시아", "malaysia": "말레이시아",
    "singapore": "싱가포르", "philippines": "필리핀", "canada": "캐나다", "mexico": "멕시코",
    "brazil": "브라질", "switzerland": "스위스", "austria": "오스트리아", "belgium": "벨기에",
    "denmark": "덴마크", "finland": "핀란드", "portugal": "포르투갈", "greece": "그리스",
    "ukraine": "우크라이나", "saudi arabia": "사우디아라비아",
}
_CODE_TO_KO = {
    "VN": "베트남", "DE": "독일", "HK": "홍콩", "AE": "아랍에미리트", "JP": "일본",
    "CN": "중국", "US": "미국", "GB": "영국", "UK": "영국", "IN": "인도", "PL": "폴란드",
    "TR": "튀르키예", "CZ": "체코", "IL": "이스라엘", "RU": "러시아", "ES": "스페인",
    "NO": "노르웨이", "KR": "대한민국", "RO": "루마니아", "IT": "이탈리아", "EE": "에스토니아",
    "TM": "투르크메니스탄", "SK": "슬로바키아", "BY": "벨라루스", "PK": "파키스탄",
    "EG": "이집트", "SE": "스웨덴", "NL": "네덜란드", "AU": "호주", "FR": "프랑스",
    "TW": "대만", "TH": "태국", "ID": "인도네시아", "MY": "말레이시아", "SG": "싱가포르",
    "PH": "필리핀", "CA": "캐나다", "MX": "멕시코", "BR": "브라질", "CH": "스위스",
    "AT": "오스트리아", "BE": "벨기에", "DK": "덴마크", "FI": "핀란드", "PT": "포르투갈",
    "GR": "그리스", "UA": "우크라이나", "SA": "사우디아라비아",
}


def normalize_country_ko(country_code=None, country_name=None) -> str:
    """폴더용 한글 국가명으로 정규화. 영문명이면 한글로, 이름이 비면 코드로 보완."""
    name = (country_name or "").strip()
    if name:
        mapped = _EN_TO_KO.get(name.lower())
        if mapped:
            return mapped
        return name  # 이미 한글(또는 매핑 없음)이면 그대로
    cc = (country_code or "").strip().upper()
    return _CODE_TO_KO.get(cc, "")


def enabled() -> bool:
    return bool((settings.NEXTCLOUD_BASE_PATH or "").strip())


def sanitize(name: str, limit: int = 150) -> str:
    """OS 폴더/파일명 금지문자 제거 + 공백 정리."""
    s = _INVALID.sub(" ", name or "").strip().strip(".")
    s = re.sub(r"\s+", " ", s)
    return s[:limit] or "무제"


def is_domestic(country_code: str = None, country_name: str = None) -> bool:
    if country_code and country_code.strip().upper() == "KR":
        return True
    if country_name and any(k in country_name for k in _DOMESTIC_KEYS):
        return True
    return False


def build_customer_relpath(country_code, country_name, partner_name, year: int = None) -> str:
    """거래처 폴더까지의 상대경로(베이스 기준). 예: '수출/2026년 거래처별 수출/폴란드_CELLCO'."""
    y = year or date.today().year
    pn = sanitize(partner_name or "거래처")
    if is_domestic(country_code, country_name):
        return os.path.join("국내판매", f"{y}년 국내판매", pn)
    cn = sanitize(normalize_country_ko(country_code, country_name) or "기타", limit=40)
    return os.path.join("수출", f"{y}년 거래처별 수출", f"{cn}_{pn}")


def create_project_folder(customer_relpath: str, folder_name: str) -> str:
    """거래처 폴더 + 문의건 폴더를 생성(존재하면 그대로). 베이스 기준 상대경로 반환."""
    if not enabled():
        raise RuntimeError("NEXTCLOUD_BASE_PATH 미설정 — Nextcloud 연동 비활성")
    rel = os.path.join(customer_relpath, sanitize(folder_name))
    full = os.path.join(settings.NEXTCLOUD_BASE_PATH, rel)
    os.makedirs(full, exist_ok=True)  # 상위(거래처) 폴더도 함께 생성
    return rel.replace("\\", "/")


def save_file(rel_folder: str, filename: str, data: bytes) -> bool:
    """rel_folder(베이스 기준) 안에 파일 저장. best-effort(실패해도 예외 안 냄)."""
    if not enabled() or not rel_folder:
        return False
    try:
        folder = os.path.join(settings.NEXTCLOUD_BASE_PATH, rel_folder)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, sanitize(filename, limit=200)), "wb") as f:
            f.write(data)
        return True
    except Exception:
        logger.exception("Nextcloud 파일 저장 실패: %s/%s", rel_folder, filename)
        return False


# ==================== 파일 허브 (거래처 우선 트리) v0.81.0 ====================

# 주문/프로젝트 표준 하위 폴더
ORDER_SUBFOLDERS = [
    "01_견적·산출자료",
    "02_영업문서",
    "03_도면·사양",
    "04_생산·검사",
    "05_포장·출하",
    "06_기타",
]
# 생성 문서(견적/PI/CI PDF) 자동 사본이 저장되는 하위 폴더
ORDER_SALES_DOC_SUBFOLDER = "02_영업문서"


def _stored(relpath) -> str:
    return (relpath or "").replace("\\", "/").strip("/")


# X-Manager가 자동 관리하는 전용 루트(신규 트리). 이 밖의 경로는 '수동 링크된 레거시'로 간주.
MANAGED_ROOTS = ("국내업체", "해외업체")


def is_managed_root(relpath) -> bool:
    """경로가 X-Manager 전용 트리(국내업체/·해외업체/) 소속인지. 아니면 수동 링크(레거시)."""
    r = _stored(relpath)
    return any(r == m or r.startswith(m + "/") for m in MANAGED_ROOTS)


def resolve_customer_root(partner) -> str:
    """거래처 루트 — 저장값(nextcloud_folder) 우선, 없으면 결정적 계산.

    최초 생성 시 API 계층에서 저장한다. 저장 후엔 거래처명이 바뀌어도 링크 불변.
    """
    stored = _stored(getattr(partner, "nextcloud_folder", None))
    if stored:
        return stored
    return build_customer_root(
        getattr(partner, "country_code", None),
        getattr(partner, "country_name", None),
        getattr(partner, "partner_name", None),
    ).replace("\\", "/")


def resolve_order_relpath(doc, customer, activity=None) -> str:
    """영업문서 폴더 — 저장값 > 연결된 영업대응건 폴더 > 문서별(폴백) 순.

    영업대응건(sales_activity)에 연결된 문서는 그 대응건 폴더 하나로 묶는다
    (문서마다 폴더를 새로 만들지 않음). 대응건 미연결 문서만 문서번호 폴더로 폴백.
    """
    stored = _stored(getattr(doc, "nextcloud_folder", None))
    if stored:
        return stored
    cc = getattr(customer, "country_code", None) if customer else None
    cn = getattr(customer, "country_name", None) if customer else None
    pn = (getattr(customer, "partner_name", None) if customer else None) or "거래처"
    # 1) 연결된 영업대응건이 있으면 그 대응건 폴더 하나로 묶음(문서별 폴더 생성 안 함)
    if activity is not None:
        act_stored = _stored(getattr(activity, "nextcloud_folder", None))
        if act_stored:
            return act_stored
        apn = pn if (customer and getattr(customer, "partner_name", None)) else (getattr(activity, "customer_name", None) or pn)
        ad = getattr(activity, "created_at", None)
        ayear = ad.year if ad else (getattr(getattr(doc, "document_date", None), "year", None) or date.today().year)
        return build_activity_relpath(cc, cn, apn, ayear, getattr(activity, "title", None))
    # 2) 폴백: 대응건 미연결 문서 → 문서번호 폴더
    d = getattr(doc, "document_date", None)
    year = d.year if d else date.today().year
    order_name = getattr(doc, "document_number", None) or f"DOC-{getattr(doc, 'id', '')}"
    return build_order_relpath(cc, cn, pn, year, order_name).replace("\\", "/")


def build_customer_root(country_code=None, country_name=None, partner_name=None) -> str:
    """거래처 루트(연도 무관, 거래처 우선). X-Manager 전용 신규 트리.

    레거시(수출/국내판매)와 겹치지 않게 '국내업체/해외업체'로 분리한다.
    예: '해외업체/폴란드_CELLCO' / '국내업체/가나상사'.
    """
    pn = sanitize(partner_name or "거래처")
    if is_domestic(country_code, country_name):
        return os.path.join("국내업체", pn)
    cn = sanitize(normalize_country_ko(country_code, country_name) or "기타", limit=40)
    return os.path.join("해외업체", f"{cn}_{pn}")


def build_common_relpath(country_code=None, country_name=None, partner_name=None) -> str:
    """거래처 상시자료 폴더(_공통)."""
    return os.path.join(build_customer_root(country_code, country_name, partner_name), "_공통")


def build_order_relpath(country_code, country_name, partner_name, year, order_name) -> str:
    """주문/프로젝트 폴더. 예: '수출/폴란드_CELLCO/2026/PI-CL250408'."""
    root = build_customer_root(country_code, country_name, partner_name)
    return os.path.join(root, str(year), sanitize(order_name or "주문"))


def build_activity_relpath(country_code, country_name, partner_name, year, activity_name) -> str:
    """영업 대응건(문의건) 폴더. 한 대응건의 모든 문서(Q/PI/CI)를 이 폴더 하나로 묶는다.

    예: '해외업체/이스라엘_APPLETEC/2026/단선발생 클레임'.
    """
    root = build_customer_root(country_code, country_name, partner_name)
    return os.path.join(root, str(year), sanitize(activity_name or "영업대응건")).replace("\\", "/")


def safe_abs(relpath: str, base: str = None) -> str:
    """베이스 내부로 제한 — ../ 탈출 차단. 절대경로 반환.

    base 미지정 시 NEXTCLOUD_BASE_PATH(GBT). 납품 트리는 NEXTCLOUD_DELIVERY_PATH를 넘긴다.
    """
    base_raw = (base if base is not None else (settings.NEXTCLOUD_BASE_PATH or "")).strip()
    if not base_raw:
        raise ValueError("베이스 경로 미설정 — 파일 연동 비활성")
    base_abs = os.path.realpath(base_raw)
    target = os.path.realpath(os.path.join(base_abs, (relpath or "").lstrip("/\\")))
    if target != base_abs and not target.startswith(base_abs + os.sep):
        raise ValueError("허용 범위를 벗어난 경로")
    return target


def ensure_dir(relpath: str, base: str = None) -> str:
    """베이스 기준 폴더 보장(생성). relpath(정규화) 반환."""
    full = safe_abs(relpath, base=base)
    os.makedirs(full, exist_ok=True)
    return (relpath or "").replace("\\", "/").strip("/")


def ensure_order_skeleton(order_relpath: str) -> str:
    """주문 폴더 + 01~06 표준 하위 폴더 생성(존재 시 그대로)."""
    ensure_dir(order_relpath)
    for sub in ORDER_SUBFOLDERS:
        ensure_dir(os.path.join(order_relpath, sub))
    return order_relpath.replace("\\", "/").strip("/")


def list_dir(relpath: str, base: str = None) -> list:
    """폴더 내용 목록 [{name, is_dir, size, mtime}] — 폴더 먼저, 이름순."""
    full = safe_abs(relpath, base=base)
    if not os.path.isdir(full):
        return []
    out = []
    for name in os.listdir(full):
        p = os.path.join(full, name)
        try:
            st = os.stat(p)
            out.append({
                "name": name,
                "is_dir": os.path.isdir(p),
                "size": st.st_size,
                "mtime": st.st_mtime,
            })
        except OSError:
            continue
    out.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return out


# ==================== 납품/포장사진 (별도 DELIVERY 베이스) v0.86.0 ====================

_IMAGE_EXT = re.compile(r"\.(png|jpe?g|gif|webp|bmp|heic|heif|tiff?)$", re.IGNORECASE)

# 측정자료(손실값측정 엑셀 등) 문서 업로드 허용 확장자 — 실행파일/스크립트는 차단
_DOC_EXT = re.compile(
    r"\.(xlsx?|xlsm|xlsb|csv|pdf|docx?|hwpx?|pptx?|txt|zip|png|jpe?g|gif|webp|bmp|heic|heif|tiff?)$",
    re.IGNORECASE,
)

# 납품 폴더 하위 표준 subfolder
MEASUREMENT_SUBFOLDER = "측정자료"  # 손실값측정 엑셀 등


def is_image_name(name: str) -> bool:
    return bool(_IMAGE_EXT.search(name or ""))


def is_allowed_doc_name(name: str) -> bool:
    """측정자료 등 문서 업로드 허용 확장자인지(실행파일·스크립트 차단)."""
    return bool(_DOC_EXT.search(name or ""))


def list_delivery_files(relpath: str) -> list:
    """납품 폴더(포장 폴더 하위 포함) 내 파일 목록 — 폴더 제외, 확장자 무관."""
    items = list_dir(relpath, base=_delivery_base())
    return [it for it in items if not it["is_dir"]]


def delivery_enabled() -> bool:
    return bool((settings.NEXTCLOUD_DELIVERY_PATH or "").strip())


def _delivery_base() -> str:
    return settings.NEXTCLOUD_DELIVERY_PATH


def _delivery_year(request_number: str) -> int:
    """생산요청번호(YY-NNN)에서 연도 산출. 예 '26-158' → 2026."""
    try:
        yy = int((request_number or "").split("-")[0])
        return 2000 + yy
    except (ValueError, TypeError, IndexError):
        return date.today().year


def resolve_packing_folder(pr, create: bool = True) -> str:
    """포장사진 폴더(납품 베이스 기준 상대경로) 해석.

    우선순위: 저장값(pr.packing_folder) → 번호 prefix로 기존 폴더 매칭 → 없으면 {번호}_{기업명} 생성.
    '{연도} 납품 리스트/{폴더}' 형태. 기존 폴더명이 제각각이라 번호 prefix로만 매칭(추측 금지 원칙과 동일).
    """
    stored = _stored(getattr(pr, "packing_folder", None))
    if stored:
        return stored

    rn = (getattr(pr, "request_number", None) or "").strip()
    base = _delivery_base()
    list_rel = f"{_delivery_year(rn)} 납품 리스트"

    # 번호 prefix로 기존 폴더 탐색(예: '26-158_...', '26-158 ...')
    found = None
    try:
        list_abs = safe_abs(list_rel, base=base)
        if rn and os.path.isdir(list_abs):
            for name in os.listdir(list_abs):
                if not os.path.isdir(os.path.join(list_abs, name)):
                    continue
                if name == rn or name.startswith(rn + "_") or name.startswith(rn + " "):
                    found = name
                    break
    except ValueError:
        pass

    if found:
        return f"{list_rel}/{found}"

    # 없으면 생성
    cust = ""
    c = getattr(pr, "customer", None)
    if c is not None:
        cust = getattr(c, "partner_name", "") or ""
    folder = f"{rn}_{sanitize(cust or '거래처', limit=60)}" if rn else sanitize(cust or '거래처', limit=60)
    rel = f"{list_rel}/{folder}"
    if create:
        ensure_dir(rel, base=base)
    return rel


def list_packing_photos(relpath: str) -> list:
    """포장사진 폴더의 이미지 파일만 목록(납품 베이스)."""
    items = list_dir(relpath, base=_delivery_base())
    return [it for it in items if not it["is_dir"] and is_image_name(it["name"])]


def save_packing_photo(rel_folder: str, filename: str, data: bytes) -> str:
    """포장사진 저장(납품 베이스). 동일명은 (n) 접미사. 저장된 파일명 반환."""
    folder_abs = safe_abs(rel_folder, base=_delivery_base())
    os.makedirs(folder_abs, exist_ok=True)
    safe_name = sanitize(filename or "photo", limit=200)
    dest = os.path.join(folder_abs, safe_name)
    if os.path.exists(dest):
        stem, ext = os.path.splitext(safe_name)
        i = 1
        while os.path.exists(os.path.join(folder_abs, f"{stem} ({i}){ext}")):
            i += 1
        safe_name = f"{stem} ({i}){ext}"
        dest = os.path.join(folder_abs, safe_name)
    with open(dest, "wb") as f:
        f.write(data)
    return safe_name


def packing_photo_abs(rel_folder: str, name: str) -> str:
    """포장사진 파일 절대경로(납품 베이스, 경로안전). 파일명만 허용(하위경로 금지)."""
    safe_name = os.path.basename(name or "")
    return safe_abs(f"{rel_folder}/{safe_name}", base=_delivery_base())


def save_delivery_file(pr, subfolder, filename, data):
    """생산요청 도면/첨부를 납품 폴더(그 하위 subfolder)에 저장(best-effort).

    납품 베이스 미설정이면 조용히 무시. 성공 시 저장 상대경로, 실패 시 None.
    """
    if not delivery_enabled():
        return None
    try:
        rel = resolve_packing_folder(pr, create=True)  # {연도} 납품 리스트/{번호_기업명}
        target = f"{rel}/{subfolder}" if subfolder else rel
        name = save_packing_photo(target, filename or "file", data)  # 폴더 보장 + 동일명 (n)
        return f"{target}/{name}"
    except Exception:
        logger.exception("납품 폴더 도면/첨부 저장 실패")
        return None
