"""견적 원가 소스 (Phase 1 = 인터림 Price List 표).

사양서 §5·§8의 '교체 이음새': 커넥터 원가 조회를 인터페이스로 격리한다.
Phase 1 = InterimCostSource(번들 CSV 표), Phase 2 = BomCostSource(price_service).
케이블/조립비/엔드페이스 인터림 표도 함께 로드한다. 값은 ₩·$ 병기(옵션 B — 통화별 표 유지).

데이터 출처: docs/견적기능/인터림_원가데이터/ → backend/app/data/quote/ 로 번들.
"""
import csv
from pathlib import Path
from typing import Optional, Dict, Tuple

_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "quote"


def _read_csv(name: str):
    with open(_DATA_DIR / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _channel_group(channel: int) -> str:
    """케이블 표의 채널 그룹: 2·4 / 6·8."""
    return "6·8" if channel in (6, 8) else "2·4"


class InterimCostSource:
    """인터림 표(A~D) 기반 원가·단가 조회. 프로세스당 1회 로드."""

    def __init__(self):
        # A: 커넥터 원가 {(size, form, core, mode): cost_krw}
        self._connector: Dict[Tuple[str, str, str, str], float] = {}
        for r in _read_csv("A_connector_cost_al.csv"):
            key = (r["size"].strip(), r["form"].strip(), r["core"].strip(), r["mode"].strip())
            self._connector[key] = float(r["cost_krw"])
        # B: 케이블 미터당 {(mode_letter, channel_group): {krw, usd}}
        # CSV mode = 'SM' / 'M3(MM)'  → 오더코드 모드 앞글자 S/M 로 매핑
        self._cable: Dict[Tuple[str, str], Dict[str, float]] = {}
        for r in _read_csv("B_cable_per_m.csv"):
            m = r["mode"].strip()
            letter = "S" if m.upper().startswith("SM") else "M"
            grp = r["channel"].strip()  # '2·4' / '6·8'
            self._cable[(letter, grp)] = {"krw": float(r["krw_per_m"]), "usd": float(r["usd_per_m"])}
        # C: 조립비 {channel: {krw_1, krw_2, usd_1, usd_2}}
        self._assembly: Dict[int, Dict[str, float]] = {}
        for r in _read_csv("C_assembly.csv"):
            ch = int(r["channel"].strip().replace("ch", ""))
            self._assembly[ch] = {
                "krw_1": float(r["krw_1단"]), "krw_2": float(r["krw_2단"]),
                "usd_1": float(r["usd_1단"]), "usd_2": float(r["usd_2단"]),
            }
        # D: 엔드페이스(커넥터B) 채널당 단가
        d = _read_csv("D_endface.csv")[0]
        self._endface = {"krw": float(d["krw_per_ch"]), "usd": float(d["usd_per_ch"])}

    # ---- 교체 이음새: 커넥터 원가 (Phase 2에서 이 메서드만 BOM 롤업으로 교체) ----
    def get_connector_cost(self, size: str, form: str, core: str, mode: str) -> Optional[float]:
        """(size, form, core, mode) → 커넥터 원가(₩). 없으면 None.
        RJN=RJS / RQN=RQS 는 CSV에 동일값 별도행으로 존재해 별도 처리 불필요."""
        return self._connector.get((size, form, core, mode))

    # ---- 인터림 참조 표 (Phase 1) ----
    def get_cable_rate(self, mode: str, channel: int, currency: str) -> Optional[float]:
        row = self._cable.get((mode, _channel_group(channel)))
        if not row:
            return None
        return row["usd"] if currency == "USD" else row["krw"]

    def get_assembly_cost(self, channel: int, stages: int, currency: str) -> Optional[float]:
        row = self._assembly.get(channel)
        if not row:
            return None
        stg = 2 if stages >= 2 else 1
        return row[f"usd_{stg}"] if currency == "USD" else row[f"krw_{stg}"]

    def get_endface_rate(self, currency: str) -> float:
        return self._endface["usd"] if currency == "USD" else self._endface["krw"]


# 프로세스 전역 싱글턴(표는 불변)
_INTERIM: Optional[InterimCostSource] = None


def get_interim_cost_source() -> InterimCostSource:
    global _INTERIM
    if _INTERIM is None:
        _INTERIM = InterimCostSource()
    return _INTERIM
