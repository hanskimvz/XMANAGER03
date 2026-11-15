"""
Price Service (v0.18.0)
부품 가격 관리 및 원가 계산 서비스

- 가격 이력 관리
- 재고단가 계산 (이동평균법)
- 평균단가 계산 (기간별/건수별)
- 환율 관리
- BOM 기반 원가 계산 (v0.18.0 신규)
"""

from typing import Optional, List, Tuple, Dict, Set
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.price_history import PriceHistory, ExchangeRate
from app.models.parts import Part
from app.models.inventory import Inventory
from app.models.bom import BOM
from app.schemas.price_history import (
    PriceHistoryCreate,
    PartStandardPriceUpdate,
    AvgPriceRequest,
    AvgPriceResponse,
    PriceType,
    ExchangeRateCreate,
)
from app.core.exceptions import NotFoundException, ValidationException


class PriceService:
    """
    가격 서비스

    부품 가격 관련 비즈니스 로직을 처리합니다.
    - 가격 이력 기록
    - 재고단가 계산 (이동평균법)
    - 평균단가 계산
    - 환율 조회
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== 환율 관리 ====================

    def get_exchange_rate(self, currency_code: str, date: Optional[datetime] = None) -> Decimal:
        """
        환율 조회

        Args:
            currency_code: 통화 코드 (USD, EUR, JPY 등)
            date: 기준일 (없으면 현재)

        Returns:
            환율 (1 외화 = ? KRW)
        """
        if currency_code == "KRW":
            return Decimal(1)

        target_date = date or datetime.now()

        rate = self.db.query(ExchangeRate).filter(
            ExchangeRate.currency_code == currency_code,
            ExchangeRate.effective_date <= target_date,
            ExchangeRate.is_active == "Y"
        ).order_by(desc(ExchangeRate.effective_date)).first()

        if rate:
            return rate.rate

        # 기본 환율 (없으면 1로 반환)
        return Decimal(1)

    def convert_to_krw(self, amount: Decimal, currency: str, date: Optional[datetime] = None) -> Decimal:
        """금액을 원화로 환산"""
        if currency == "KRW":
            return amount
        rate = self.get_exchange_rate(currency, date)
        return amount * rate

    def create_exchange_rate(self, data: ExchangeRateCreate) -> ExchangeRate:
        """환율 등록"""
        rate = ExchangeRate(
            currency_code=data.currency_code,
            currency_name=data.currency_name,
            rate=data.rate,
            effective_date=data.effective_date,
            expiry_date=data.expiry_date,
            source=data.source,
            is_active="Y"
        )
        self.db.add(rate)
        self.db.commit()
        self.db.refresh(rate)
        return rate

    # ==================== 가격 이력 ====================

    def record_price_history(
        self,
        part_id: int,
        unit_price: Decimal,
        currency: str = "KRW",
        quantity: Optional[Decimal] = None,
        supplier_id: Optional[int] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        reference_date: Optional[datetime] = None,
        price_type: str = "PURCHASE",
        remarks: Optional[str] = None
    ) -> PriceHistory:
        """
        가격 이력 기록

        모든 가격 변동을 기록합니다.
        """
        # 환율 조회 및 원화 환산
        exchange_rate = self.get_exchange_rate(currency, reference_date)
        unit_price_krw = unit_price * exchange_rate if currency != "KRW" else unit_price

        history = PriceHistory(
            part_id=part_id,
            price_type=price_type,
            unit_price=unit_price,
            currency=currency,
            exchange_rate=exchange_rate,
            unit_price_krw=unit_price_krw,
            quantity=quantity,
            supplier_id=supplier_id,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_date=reference_date or datetime.now(),
            remarks=remarks
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history

    def get_price_history(
        self,
        part_id: int,
        price_type: Optional[str] = None,
        supplier_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[PriceHistory], int]:
        """가격 이력 조회"""
        query = self.db.query(PriceHistory).filter(PriceHistory.part_id == part_id)

        if price_type:
            query = query.filter(PriceHistory.price_type == price_type)
        if supplier_id:
            query = query.filter(PriceHistory.supplier_id == supplier_id)
        if from_date:
            query = query.filter(PriceHistory.created_at >= from_date)
        if to_date:
            query = query.filter(PriceHistory.created_at <= to_date)

        total = query.count()
        items = query.order_by(desc(PriceHistory.created_at)).offset(skip).limit(limit).all()

        return items, total

    # ==================== 재고단가 계산 (이동평균법) ====================

    def calculate_inventory_avg_price(
        self,
        part_id: int,
        new_quantity: Decimal,
        new_unit_price: Decimal,
        new_currency: str = "KRW"
    ) -> Decimal:
        """
        재고단가 계산 (이동평균법)

        공식: (기존 재고금액 + 신규 입고금액) / 총 수량

        Args:
            part_id: 부품 ID
            new_quantity: 신규 입고 수량
            new_unit_price: 신규 단가
            new_currency: 신규 단가 통화

        Returns:
            새로운 재고단가 (원화)
        """
        # 현재 재고 조회
        inventory = self.db.query(Inventory).filter(Inventory.part_id == part_id).first()
        current_qty = Decimal(inventory.quantity_on_hand) if inventory else Decimal(0)

        # 현재 부품 정보 조회
        part = self.db.query(Part).filter(Part.id == part_id).first()
        if not part:
            raise NotFoundException("부품", part_id)

        current_avg_price = Decimal(part.inventory_avg_price or 0)

        # 신규 단가 원화 환산
        new_unit_price_krw = self.convert_to_krw(new_unit_price, new_currency)

        # 이동평균 계산
        total_qty = current_qty + new_quantity

        if total_qty <= 0:
            return Decimal(0)

        current_value = current_qty * current_avg_price
        new_value = new_quantity * new_unit_price_krw
        total_value = current_value + new_value

        new_avg_price = total_value / total_qty

        return new_avg_price.quantize(Decimal("0.0001"))

    def update_part_prices_on_receive(
        self,
        part_id: int,
        received_quantity: Decimal,
        unit_price: Decimal,
        currency: str = "KRW",
        supplier_id: Optional[int] = None,
        po_number: Optional[str] = None
    ) -> Part:
        """
        입고 시 부품 가격 정보 업데이트

        1. 재고단가 (이동평균)
        2. 최근단가
        3. 가격 이력 기록

        Args:
            part_id: 부품 ID
            received_quantity: 입고 수량
            unit_price: 단가
            currency: 통화
            supplier_id: 공급업체 ID
            po_number: 발주번호

        Returns:
            업데이트된 부품
        """
        part = self.db.query(Part).filter(Part.id == part_id).first()
        if not part:
            raise NotFoundException("부품", part_id)

        now = datetime.now()

        # 1. 재고단가 계산 (이동평균)
        new_inventory_avg_price = self.calculate_inventory_avg_price(
            part_id, received_quantity, unit_price, currency
        )
        part.inventory_avg_price = new_inventory_avg_price
        part.inventory_avg_price_currency = "KRW"  # 항상 원화로 저장

        # 2. 최근단가 업데이트
        unit_price_krw = self.convert_to_krw(unit_price, currency)
        part.latest_price = unit_price
        part.latest_price_currency = currency
        part.latest_price_date = now
        part.latest_price_supplier_id = supplier_id

        # 3. 단가 갱신일 업데이트
        part.price_updated_at = now

        # 4. 가격 이력 기록
        self.record_price_history(
            part_id=part_id,
            unit_price=unit_price,
            currency=currency,
            quantity=received_quantity,
            supplier_id=supplier_id,
            reference_type="PO",
            reference_id=po_number,
            reference_date=now,
            price_type="PURCHASE",
            remarks=f"입고: {received_quantity}개 @ {unit_price} {currency}"
        )

        self.db.commit()
        self.db.refresh(part)

        return part

    # ==================== 평균단가 계산 ====================

    def calculate_avg_price(self, request: AvgPriceRequest) -> AvgPriceResponse:
        """
        평균단가 계산 (기간별/건수별)

        Args:
            request: 계산 요청 (기간 또는 건수)

        Returns:
            평균단가 정보
        """
        query = self.db.query(PriceHistory).filter(
            PriceHistory.part_id == request.part_id,
            PriceHistory.price_type == PriceType.PURCHASE.value
        )

        # 공급업체 필터
        if request.supplier_id:
            query = query.filter(PriceHistory.supplier_id == request.supplier_id)

        # 기간별 필터
        if request.from_date:
            query = query.filter(PriceHistory.created_at >= request.from_date)
        if request.to_date:
            query = query.filter(PriceHistory.created_at <= request.to_date)

        # 정렬
        query = query.order_by(desc(PriceHistory.created_at))

        # 건수별 제한
        if request.last_count:
            query = query.limit(request.last_count)

        histories = query.all()

        if not histories:
            return AvgPriceResponse(
                part_id=request.part_id,
                avg_price=Decimal(0),
                avg_price_krw=Decimal(0),
                currency="KRW",
                count=0,
                from_date=request.from_date,
                to_date=request.to_date,
                min_price=Decimal(0),
                max_price=Decimal(0)
            )

        # 원화 환산 단가 기준으로 계산
        prices_krw = [h.unit_price_krw or self.convert_to_krw(h.unit_price, h.currency) for h in histories]
        total_price = sum(prices_krw)
        count = len(prices_krw)
        avg_price_krw = total_price / count if count > 0 else Decimal(0)

        return AvgPriceResponse(
            part_id=request.part_id,
            avg_price=avg_price_krw,  # 원화 기준
            avg_price_krw=avg_price_krw,
            currency="KRW",
            count=count,
            from_date=request.from_date,
            to_date=request.to_date,
            min_price=min(prices_krw) if prices_krw else Decimal(0),
            max_price=max(prices_krw) if prices_krw else Decimal(0)
        )

    def update_avg_price_cache(self, part_id: int) -> Part:
        """
        평균단가 캐시 업데이트

        부품의 평균단가 필드들을 갱신합니다.
        - avg_price_30d: 최근 30일 평균
        - avg_price_90d: 최근 90일 평균
        - avg_price_last5: 최근 5건 평균
        - avg_price_last10: 최근 10건 평균
        """
        part = self.db.query(Part).filter(Part.id == part_id).first()
        if not part:
            raise NotFoundException("부품", part_id)

        now = datetime.now()

        # 최근 30일
        result_30d = self.calculate_avg_price(AvgPriceRequest(
            part_id=part_id,
            from_date=now - timedelta(days=30),
            to_date=now
        ))
        part.avg_price_30d = result_30d.avg_price_krw

        # 최근 90일
        result_90d = self.calculate_avg_price(AvgPriceRequest(
            part_id=part_id,
            from_date=now - timedelta(days=90),
            to_date=now
        ))
        part.avg_price_90d = result_90d.avg_price_krw

        # 최근 5건
        result_last5 = self.calculate_avg_price(AvgPriceRequest(
            part_id=part_id,
            last_count=5
        ))
        part.avg_price_last5 = result_last5.avg_price_krw

        # 최근 10건
        result_last10 = self.calculate_avg_price(AvgPriceRequest(
            part_id=part_id,
            last_count=10
        ))
        part.avg_price_last10 = result_last10.avg_price_krw

        self.db.commit()
        self.db.refresh(part)

        return part

    # ==================== 기준단가 관리 ====================

    def update_standard_price(self, part_id: int, data: PartStandardPriceUpdate) -> Part:
        """
        기준단가 업데이트

        Args:
            part_id: 부품 ID
            data: 기준단가 정보

        Returns:
            업데이트된 부품
        """
        part = self.db.query(Part).filter(Part.id == part_id).first()
        if not part:
            raise NotFoundException("부품", part_id)

        old_price = part.standard_price
        old_currency = part.standard_price_currency

        # 기준단가 업데이트
        part.standard_price = data.standard_price
        part.standard_price_currency = data.standard_price_currency
        part.price_updated_at = datetime.now()

        # 가격 이력 기록
        self.record_price_history(
            part_id=part_id,
            unit_price=data.standard_price,
            currency=data.standard_price_currency,
            price_type="STANDARD",
            remarks=f"기준단가 변경: {old_price} {old_currency} → {data.standard_price} {data.standard_price_currency}. {data.remarks or ''}"
        )

        self.db.commit()
        self.db.refresh(part)

        return part

    # ==================== 부품 원가 정보 조회 ====================

    def get_part_price_info(self, part_id: int) -> dict:
        """
        부품 원가 정보 조회

        Args:
            part_id: 부품 ID

        Returns:
            원가 정보 딕셔너리
        """
        part = self.db.query(Part).filter(Part.id == part_id).first()
        if not part:
            raise NotFoundException("부품", part_id)

        # 최근단가 공급업체명 조회
        latest_supplier_name = None
        if part.latest_price_supplier_id:
            from app.models.supplier import Supplier
            supplier = self.db.query(Supplier).filter(Supplier.id == part.latest_price_supplier_id).first()
            if supplier:
                latest_supplier_name = supplier.supplier_name

        return {
            "part_id": part.id,
            "part_number": part.part_number,
            "part_name": part.part_name,
            "standard_price": part.standard_price or Decimal(0),
            "standard_price_currency": part.standard_price_currency or "KRW",
            "inventory_avg_price": part.inventory_avg_price or Decimal(0),
            "inventory_avg_price_currency": part.inventory_avg_price_currency or "KRW",
            "latest_price": part.latest_price or Decimal(0),
            "latest_price_currency": part.latest_price_currency or "KRW",
            "latest_price_date": part.latest_price_date,
            "latest_price_supplier": latest_supplier_name,
            "avg_price_30d": part.avg_price_30d or Decimal(0),
            "avg_price_90d": part.avg_price_90d or Decimal(0),
            "avg_price_last5": part.avg_price_last5 or Decimal(0),
            "avg_price_last10": part.avg_price_last10 or Decimal(0),
            # BOM 원가 정보 (v0.18.0)
            "cost_type": part.cost_type or "MANUAL",
            "material_cost": part.material_cost or Decimal(0),
            "material_cost_currency": part.material_cost_currency or "KRW",
            "labor_cost": part.labor_cost or Decimal(0),
            "labor_cost_currency": part.labor_cost_currency or "KRW",
            "overhead_cost": part.overhead_cost or Decimal(0),
            "overhead_cost_currency": part.overhead_cost_currency or "KRW",
            "calculated_cost": part.calculated_cost or Decimal(0),
            "calculated_cost_currency": part.calculated_cost_currency or "KRW",
            "cost_calculated_at": part.cost_calculated_at,
        }

    # ==================== BOM 기반 원가 계산 (v0.18.0) ====================

    def get_part_unit_cost(self, part: Part) -> Decimal:
        """
        부품의 단위 원가 조회

        우선순위:
        1. BOM 있는 경우: calculated_cost (계산된 원가)
        2. BOM 없는 경우: standard_price > latest_price > inventory_avg_price

        Args:
            part: 부품 객체

        Returns:
            단위 원가 (KRW)
        """
        # BOM 구성품이 있으면 계산된 원가 사용
        has_bom = self.db.query(BOM).filter(
            BOM.parent_part_id == part.id,
            BOM.is_active == True
        ).first() is not None

        if has_bom and part.calculated_cost:
            return self.convert_to_krw(
                Decimal(part.calculated_cost),
                part.calculated_cost_currency or "KRW"
            )

        # 단품인 경우 우선순위대로
        if part.standard_price and part.standard_price > 0:
            return self.convert_to_krw(
                Decimal(part.standard_price),
                part.standard_price_currency or "KRW"
            )

        if part.latest_price and part.latest_price > 0:
            return self.convert_to_krw(
                Decimal(part.latest_price),
                part.latest_price_currency or "KRW"
            )

        if part.inventory_avg_price and part.inventory_avg_price > 0:
            return self.convert_to_krw(
                Decimal(part.inventory_avg_price),
                part.inventory_avg_price_currency or "KRW"
            )

        return Decimal(0)

    def calculate_bom_cost(
        self,
        part_id: int,
        visited: Optional[Set[int]] = None
    ) -> Dict:
        """
        BOM 기반 원가 계산 (재귀)

        조립품의 원가를 하위 BOM 구성품의 합산으로 계산합니다.
        - 재료비 = Σ(하위부품 단가 × 수량)
        - 총원가 = 재료비 + 가공비 + 경비

        순환 참조 감지를 위해 visited 집합을 사용합니다.

        Args:
            part_id: 부품 ID
            visited: 방문한 부품 ID 집합 (순환 참조 감지용)

        Returns:
            원가 계산 결과 딕셔너리:
            - material_cost: 재료비 (BOM 하위품목 합산)
            - labor_cost: 가공비
            - overhead_cost: 경비
            - total_cost: 총원가
            - bom_items: BOM 구성품 상세 목록
            - has_bom: BOM 존재 여부
        """
        if visited is None:
            visited = set()

        # 순환 참조 감지
        if part_id in visited:
            raise ValidationException(f"순환 참조 감지: 부품 ID {part_id}")

        visited.add(part_id)

        # 부품 조회
        part = self.db.query(Part).filter(Part.id == part_id).first()
        if not part:
            raise NotFoundException("부품", part_id)

        # BOM 하위품목 조회
        bom_items = self.db.query(BOM).filter(
            BOM.parent_part_id == part_id,
            BOM.is_active == True
        ).all()

        result = {
            "part_id": part_id,
            "part_number": part.part_number,
            "part_name": part.part_name,
            "cost_type": part.cost_type or "MANUAL",
            "material_cost": Decimal(0),
            "labor_cost": Decimal(part.labor_cost or 0),
            "overhead_cost": Decimal(part.overhead_cost or 0),
            "total_cost": Decimal(0),
            "bom_items": [],
            "has_bom": len(bom_items) > 0
        }

        if not bom_items:
            # BOM 없음 = 단품 → 기준단가 사용
            unit_cost = self.get_part_unit_cost(part)
            result["material_cost"] = unit_cost
            result["total_cost"] = unit_cost + result["labor_cost"] + result["overhead_cost"]
            result["cost_type"] = "MANUAL"
            return result

        # BOM 있음 = 조립품 → 하위 품목 합산
        result["cost_type"] = "BOM"
        total_material_cost = Decimal(0)

        for bom in bom_items:
            child_part = bom.child_part
            if not child_part:
                continue

            quantity = Decimal(bom.quantity or 1)

            # 하위 부품도 BOM이 있을 수 있음 → 재귀 계산
            child_result = self.calculate_bom_cost(bom.child_part_id, visited.copy())
            child_unit_cost = child_result["total_cost"]

            # 하위부품에 BOM이 없으면 단가 사용
            if not child_result["has_bom"]:
                child_unit_cost = self.get_part_unit_cost(child_part)

            line_cost = child_unit_cost * quantity
            total_material_cost += line_cost

            result["bom_items"].append({
                "bom_id": bom.id,
                "child_part_id": child_part.id,
                "child_part_number": child_part.part_number,
                "child_part_name": child_part.part_name,
                "quantity": float(quantity),
                "unit_cost": float(child_unit_cost),
                "line_cost": float(line_cost),
                "has_bom": child_result["has_bom"]
            })

        result["material_cost"] = total_material_cost
        result["total_cost"] = total_material_cost + result["labor_cost"] + result["overhead_cost"]

        return result

    def save_calculated_cost(self, part_id: int, cost_result: Optional[Dict] = None) -> Part:
        """
        계산된 원가를 부품에 저장

        Args:
            part_id: 부품 ID
            cost_result: 원가 계산 결과 (없으면 새로 계산)

        Returns:
            업데이트된 부품
        """
        if cost_result is None:
            cost_result = self.calculate_bom_cost(part_id)

        part = self.db.query(Part).filter(Part.id == part_id).first()
        if not part:
            raise NotFoundException("부품", part_id)

        # 원가 정보 저장
        part.cost_type = cost_result["cost_type"]
        part.material_cost = cost_result["material_cost"]
        part.material_cost_currency = "KRW"
        part.calculated_cost = cost_result["total_cost"]
        part.calculated_cost_currency = "KRW"
        part.cost_calculated_at = datetime.now()

        self.db.commit()
        self.db.refresh(part)

        return part

    def save_all_bom_costs(self, part_id: int, visited: Optional[Set[int]] = None) -> int:
        """
        BOM의 모든 하위 부품 원가를 재귀적으로 계산 및 저장

        하위 → 상위 순서로 계산하여 정확한 원가 합산이 이루어지도록 합니다.

        Args:
            part_id: 최상위 부품 ID
            visited: 순환 참조 방지용 방문 기록

        Returns:
            계산된 부품 수
        """
        if visited is None:
            visited = set()

        if part_id in visited:
            return 0

        visited.add(part_id)
        count = 0

        # 하위 BOM 조회
        bom_items = self.db.query(BOM).filter(
            BOM.parent_part_id == part_id,
            BOM.is_active == True
        ).all()

        # 하위 부품들 먼저 재귀적으로 처리 (하위 → 상위 순서)
        for bom in bom_items:
            count += self.save_all_bom_costs(bom.child_part_id, visited.copy())

        # 이 부품의 원가 계산 및 저장
        try:
            self.save_calculated_cost(part_id)
            count += 1
        except Exception as e:
            print(f"원가 저장 실패 (부품 ID: {part_id}): {e}")

        return count

    def update_labor_cost(
        self,
        part_id: int,
        labor_cost: Decimal,
        labor_cost_currency: str = "KRW"
    ) -> Part:
        """
        가공비 업데이트

        Args:
            part_id: 부품 ID
            labor_cost: 가공비
            labor_cost_currency: 통화

        Returns:
            업데이트된 부품
        """
        part = self.db.query(Part).filter(Part.id == part_id).first()
        if not part:
            raise NotFoundException("부품", part_id)

        part.labor_cost = labor_cost
        part.labor_cost_currency = labor_cost_currency

        self.db.commit()
        self.db.refresh(part)

        return part

    def update_overhead_cost(
        self,
        part_id: int,
        overhead_cost: Decimal,
        overhead_cost_currency: str = "KRW"
    ) -> Part:
        """
        경비 업데이트

        Args:
            part_id: 부품 ID
            overhead_cost: 경비
            overhead_cost_currency: 통화

        Returns:
            업데이트된 부품
        """
        part = self.db.query(Part).filter(Part.id == part_id).first()
        if not part:
            raise NotFoundException("부품", part_id)

        part.overhead_cost = overhead_cost
        part.overhead_cost_currency = overhead_cost_currency

        self.db.commit()
        self.db.refresh(part)

        return part

    def get_bom_cost_breakdown(self, part_id: int) -> Dict:
        """
        BOM 원가 분석 (상세 내역)

        다단계 BOM의 원가 구성을 트리 형태로 반환합니다.

        Args:
            part_id: 부품 ID

        Returns:
            원가 분석 결과:
            - part_info: 부품 정보
            - cost_summary: 원가 요약
            - bom_tree: BOM 트리 (재귀 구조)
        """
        cost_result = self.calculate_bom_cost(part_id)

        part = self.db.query(Part).filter(Part.id == part_id).first()

        return {
            "part_info": {
                "id": part.id,
                "part_number": part.part_number,
                "part_number_display": part.part_number_display,
                "part_name": part.part_name
            },
            "cost_summary": {
                "cost_type": cost_result["cost_type"],
                "material_cost": float(cost_result["material_cost"]),
                "labor_cost": float(cost_result["labor_cost"]),
                "overhead_cost": float(cost_result["overhead_cost"]),
                "total_cost": float(cost_result["total_cost"]),
                "currency": "KRW"
            },
            "has_bom": cost_result["has_bom"],
            "bom_items": cost_result["bom_items"]
        }
