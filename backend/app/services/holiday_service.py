"""
공휴일 조회 서비스 — 공공데이터포털(data.go.kr) 한국천문연구원 특일 정보(getRestDeInfo).

- 서비스키: config.json 의 "DATA.GO.KR".api_key (settings.DATA_GO_KR_API_KEY)
- 연도 단위로 조회해 메모리에 캐시한다(성공 24시간, 실패 10분).
- 외부 API 장애/키 미설정이어도 캘린더가 깨지지 않도록 예외를 던지지 않고 빈 목록을 돌려준다.
"""

import json
import logging
import threading
import time
import urllib.request
from datetime import date
from typing import Dict, List, Tuple
from urllib.parse import quote

from app.core.config import settings

logger = logging.getLogger(__name__)

_API_URL = "https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo"
_TIMEOUT_SEC = 5
_TTL_OK = 24 * 60 * 60   # 성공 결과 캐시 24시간(임시공휴일 지정 반영)
_TTL_FAIL = 10 * 60      # 실패 시 10분간 재시도 안 함(외부 API 반복 호출 방지)

# year -> (만료시각, [{"date": "YYYY-MM-DD", "name": "..."}])
_cache: Dict[int, Tuple[float, List[dict]]] = {}
_lock = threading.Lock()


def _service_key() -> str:
    """URL 에 넣을 서비스키. 포털의 'Encoding' 키(%2F 등 포함)는 그대로, 'Decoding' 키는 인코딩해서 쓴다."""
    key = (settings.DATA_GO_KR_API_KEY or "").strip()
    return key if "%" in key else quote(key, safe="")


def _fetch_year(year: int) -> List[dict]:
    """해당 연도의 공휴일을 외부 API 에서 조회. 실패 시 예외."""
    url = f"{_API_URL}?serviceKey={_service_key()}&solYear={year}&numOfRows=100&_type=json"
    with urllib.request.urlopen(url, timeout=_TIMEOUT_SEC) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # 키 오류 등은 _type=json 이어도 XML 오류문으로 온다
        raise RuntimeError(f"공휴일 API 오류 응답: {raw[:200]}")

    response = data.get("response") or {}
    header = response.get("header") or {}
    if str(header.get("resultCode")) != "00":
        raise RuntimeError(f"공휴일 API 오류: {header.get('resultCode')} {header.get('resultMsg')}")

    items = (response.get("body") or {}).get("items") or {}
    item = items.get("item") if isinstance(items, dict) else None
    if item is None:
        return []
    if isinstance(item, dict):  # 1건이면 배열이 아니라 객체로 온다
        item = [item]

    out: List[dict] = []
    for it in item:
        if str(it.get("isHoliday", "Y")).upper() != "Y":
            continue
        loc = str(it.get("locdate") or "")
        if len(loc) != 8:
            continue
        name = str(it.get("dateName") or "공휴일")
        if name == "1월1일":  # API 표기 → 통용 명칭
            name = "신정"
        out.append({"date": f"{loc[:4]}-{loc[4:6]}-{loc[6:]}", "name": name})
    out.sort(key=lambda h: h["date"])
    return out


def _holidays_of_year(year: int) -> List[dict]:
    now = time.time()
    with _lock:
        cached = _cache.get(year)
        if cached and cached[0] > now:
            return cached[1]

    try:
        result = _fetch_year(year)
        ttl = _TTL_OK
    except Exception as e:  # 네트워크/키/형식 오류 — 캘린더는 계속 동작해야 한다
        logger.warning("공휴일 조회 실패(%s년): %s", year, e)
        result = cached[1] if cached else []  # 만료된 이전 값이 있으면 그것이라도 사용
        ttl = _TTL_FAIL

    with _lock:
        _cache[year] = (now + ttl, result)
    return result


def list_holidays(date_from: date, date_to: date) -> List[dict]:
    """기간 내 공휴일 목록 [{"date": "YYYY-MM-DD", "name": "설날"}, ...] (양끝 포함)."""
    if not (settings.DATA_GO_KR_API_KEY or "").strip() or date_from > date_to:
        return []
    lo, hi = date_from.isoformat(), date_to.isoformat()
    out: List[dict] = []
    for year in range(date_from.year, date_to.year + 1):
        out.extend(h for h in _holidays_of_year(year) if lo <= h["date"] <= hi)
    return out
