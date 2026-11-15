# X-Manager 부품 코드 관리 기준서

**작성일**: 2026년 1월 9일  
**버전**: 1.1  
**목적**: 부품 마스터 코드 체계 정의 및 시스템 구현 가이드

---

## 1. 코드 체계 개요

부품 관리는 크게 3가지 영역으로 구분됩니다:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      부품 코드 관리 체계                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. 부품 코드 (Part Code) - 품번, 고유 식별자                      │   │
│  │    → 부품의 유일한 ID (Primary Key)                              │   │
│  │    → 구조: 대분류-소분류-품목코드-재질-후처리                      │   │
│  │    → 재질 또는 후처리가 다르면 별개의 부품                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 2. 부품 분류 (Classification) - 검색/필터용 속성                  │   │
│  │    → 부품 검색 및 관리를 위한 분류 체계                           │   │
│  │    → 분류1(개발구분), 분류2(부품유형-중복가능), 분류3(도면여부)    │   │
│  │    → 품번에 포함되지 않음, 별도 속성으로 관리                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 3. 부품 레벨 (Level) - BOM 구조용                                │   │
│  │    → BOM(자재명세서) 트리 구조에서의 위치                         │   │
│  │    → 품번에 포함되지 않음, 별도 속성으로 관리                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 부품 코드 (Part Code) - 품번 구조

### 2.1 품번 구성

```
[대분류 4자리]-[소분류 3자리]-[품목코드 5자리]-[재질 2자리]-[후처리 2자리]

예시: HB01-DCP-00001-A6-NK
      │     │     │     │   └─ 후처리: NK(니켈도금)
      │     │     │     └───── 재질: A6(AL6061)
      │     │     └─────────── 품목코드: 00001 (일련번호)
      │     └───────────────── 소분류: DCP(더스트캡부품)
      └─────────────────────── 대분류: HB01(HXB11 제품라인)

총 길이: 20자리 (하이픈 포함)
```

### 2.2 품번 저장 방식

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         품번 저장 구조                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DB 컬럼 구조:                                                          │
│  ┌──────────────────────┬──────────────────────┬─────────────────────┐ │
│  │ 컬럼명               │ 예시값               │ 설명                │ │
│  ├──────────────────────┼──────────────────────┼─────────────────────┤ │
│  │ part_number          │ HB01-DCP-00001-A6-NK │ 전체 품번 (UNIQUE)  │ │
│  │ product_line_id      │ 1 (FK)               │ 대분류 ID           │ │
│  │ part_group_id        │ 5 (FK)               │ 소분류 ID           │ │
│  │ item_code            │ 00001                │ 품목코드 (5자리)    │ │
│  │ material_id          │ 3 (FK)               │ 재질 ID             │ │
│  │ treatment_id         │ 2 (FK)               │ 후처리 ID           │ │
│  └──────────────────────┴──────────────────────┴─────────────────────┘ │
│                                                                         │
│  장점:                                                                  │
│  - 품번 파싱 불필요 (각 요소 별도 저장)                                  │
│  - 검색/필터 용이 (개별 FK로 조회)                                       │
│  - 코드 변경 시 품번 자동 재생성 가능                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.3 핵심 규칙

> **⚠️ 중요**: 재질 또는 후처리가 다르면 **별개의 부품**입니다.
> 
> ```
> HB01-DCP-00001-A6-NN  ← 후처리 전 부품 (재고 별도 관리)
> HB01-DCP-00001-A6-NK  ← 후처리 후 부품 (재고 별도 관리)
> ```
> 
> 후처리 공정도 BOM에서 관리됩니다:
> `후처리 전 부품 → [후처리 공정(M)] → 후처리 후 부품`

### 2.4 대분류 코드 (제품라인) - 4자리

> **관리자 모드**에서 추가/수정/삭제 가능

| 코드 | 설명 | 비고 |
|------|------|------|
| HB01 | HXB11 | Expanded Beam 11핀 |
| HB03 | HXB13 | Expanded Beam 13핀 |
| HB05 | HXB15 | Expanded Beam 15핀 |
| HB07 | HXB17 | Expanded Beam 17핀 |
| HB00 | HXB공용 | HXB 시리즈 공용 부품 |
| BI01 | XBI11 | 인서트 11핀 |
| BI03 | XBI13 | 인서트 13핀 |
| BI05 | XBI15 | 인서트 15핀 |
| BI07 | XBI17 | 인서트 17핀 |
| BI00 | XBI공용 | XBI 시리즈 공용 부품 |
| IK05 | XBI15K | XBI15 키트 |
| TF01 | TFOCA | TFOCA 커넥터 |
| COM0 | 공용 | 공용/상용 부품 |

**코드 규칙**:
- 길이: 4자리 (고정)
- 형식: 영문+숫자 조합
- 예약어: 없음

### 2.5 소분류 코드 (품목군) - 3자리

> **관리자 모드**에서 추가/수정/삭제 가능

| 코드 | 설명 | 비고 |
|------|------|------|
| DCP | 더스트캡 부품 | Dust Cap Parts |
| BIP | 인서트용 부품 | Insert Parts |
| CHP | 케이블홀더 | Cable Holder Parts |
| PLP | 플러그 부품 | Plug Parts |
| RCP | 리셉터클 부품 | Receptacle Parts |
| CMP | 화학소재 | Chemical Materials |
| MNP | 공정 | Manufacturing Process |
| CSP | 하우징 파트 | Casing Parts |
| ELP | 전자 부품 | Electronic Parts |
| OCP | 광학 부품 | Optical Parts |
| JIG | 지그류 | Jig & Fixture |
| OC2 | 광 2채널 | Optical 2ch |
| OC4 | 광 4채널 | Optical 4ch |
| OC6 | 광 6채널 | Optical 6ch |
| OC8 | 광 8채널 | Optical 8ch |
| HB2 | 광2/전2 (AWG16) | Hybrid 2ch |
| HB4 | 광4/전2 (AWG16) | Hybrid 4ch |
| CTM | 커스텀 | Custom |
| BLS | 볼렌즈 | Ball Lens |
| CRP | 크림프링 | Crimp Ring |
| BLT | 볼트/너트 | Bolt/Nut |
| SOR | 규격오링 | Standard O-Ring |
| NOR | 비규격오링 | Non-standard O-Ring |
| CBT | 케이블부트 | Cable Boot |
| WSR | 와셔 | Washer |

**코드 규칙**:
- 길이: 3자리 (고정)
- 형식: 영문+숫자 조합
- 예약어: 없음

### 2.6 품목코드 - 5자리

- **형식**: 숫자 5자리 (00001 ~ 99999)
- **입력방식**: 자동추천 + 수동입력 허용
- **자동추천**: 해당 대분류+소분류 내 최대값 + 1
- **중복체크**: 전체 품번 기준 중복 검증 (UNIQUE 제약)
- **수동입력 시**: 숫자 5자리 형식 검증 필수

```python
# 품목코드 검증 규칙
def validate_item_code(item_code: str) -> bool:
    """품목코드 형식 검증"""
    if len(item_code) != 5:
        return False
    if not item_code.isdigit():
        return False
    return True
```

### 2.7 재질 코드 - 2자리

> **관리자 모드**에서 추가/수정/삭제 가능

| 코드 | 재질명 | 설명 |
|------|--------|------|
| A6 | AL6061 | 알루미늄 6061 합금 |
| C8 | CR80 | 크롬강 80 |
| EP | EPDM | EPDM 고무 |
| NB | NBR | 니트릴 고무 |
| SI | SILICONE | 실리콘 |
| S4 | STS304 | 스테인리스 304 |
| S3 | SUS303 | 스테인리스 303 |
| S6 | SUS316 | 스테인리스 316 |
| BR | 황동 | Brass |
| L1 | LAK-10 | 광학 유리 |
| NR | NORAL | 노랄 |
| XX | 미지정 | 복합재질/미정의 |

**코드 규칙**:
- 길이: 2자리 (고정)
- 형식: 영문+숫자 조합

### 2.8 후처리 코드 - 2자리

> **관리자 모드**에서 추가/수정/삭제 가능

| 코드 | 후처리명 | 설명 |
|------|----------|------|
| NK | 니켈 | 니켈 도금 |
| NN | 없음 | 후처리 없음 |
| ZK | 징크-니켈 | 징크니켈 도금 |
| CM | 카드뮴 | 국방색 카드뮴 도금 |
| HB | 하드 블랙 | 하드 아노다이징 (블랙) |
| WA | 백색 아노다이징 | White Anodizing |
| A0 | AR코팅 | 반사방지 코팅 (850,1310,1550/Air) |

**코드 규칙**:
- 길이: 2자리 (고정)
- 형식: 영문+숫자 조합

---

## 3. 부품 분류 (Classification) - 검색/필터용

> **중요**: 부품 분류는 품번에 포함되지 않습니다. 검색과 필터링을 위한 별도 속성입니다.

### 3.1 분류1 - 개발구분 (필수, 단일선택)

> **관리자 모드**에서 추가/수정/삭제 가능

| 코드 | 영문명 | 한글명 | 설명 |
|------|--------|--------|------|
| D | Developed Part | 개발품 | 자체 설계/개발 부품 |
| S | Standard Part | 규격품 | 표준 규격 부품 |
| M | Market Part | 상용품 | 시중 구매 부품 |
| R | Raw Material | 원소재 | 원자재 |
| C | Custom Part | 주문품 | 고객 맞춤 부품 |
| P | Process | 공정 | 제조 공정 |

### 3.2 분류2 - 부품유형 (필수, **중복선택 가능**)

> **관리자 모드**에서 추가/수정/삭제 가능
> **저장 방식**: JSON 배열 (예: `["P", "O"]`)

| 코드 | 영문명 | 한글명 |
|------|--------|--------|
| P | Processed Part | 가공품 |
| E | Elastomer Part | 고무품 |
| O | Optical Part | 광학품 |
| M | Mold Part | 금형품 |
| G | General mechanic part | 일반기계부품 |
| I | Injection Part | 사출품 |
| W | Wire | 와이어류 |
| A | Assembly | 조립품 |
| C | Cable | 케이블류 |
| H | Hardware | 하드웨어 |
| X | Chemical Part | 화학품 |
| T | Tube | 수축튜브 |

**중복선택 예시**: 
- 광학 가공품 → `["O", "P"]`
- 고무 사출품 → `["E", "I"]`

**DB 저장**:
```sql
-- parts 테이블
part_types JSONB  -- ["P", "O"]

-- 검색 쿼리 (PostgreSQL)
SELECT * FROM parts WHERE part_types @> '["O"]';  -- 광학품 포함
```

### 3.3 분류3 - 도면여부 (필수, 단일선택)

> **관리자 모드**에서 추가/수정/삭제 가능

| 코드 | 영문명 | 한글명 | 설명 |
|------|--------|--------|------|
| D | Drawing | 도면 | 도면 있음 |
| S | Standard | 표준품번 | 표준 규격품 (도면 불필요) |
| N | None | 없음 | 도면 없음 |

---

## 4. 부품 레벨 (Level) - BOM 구조용

> **중요**: 부품 레벨은 품번에 포함되지 않습니다. BOM 트리 구조에서의 위치를 나타내는 별도 속성입니다.

### 4.1 레벨 코드 (필수, 단일선택)

> **관리자 모드**에서 추가/수정/삭제 가능

| 코드 | 영문명 | 한글명 | BOM 레벨 | 기본단위 |
|------|--------|--------|----------|----------|
| F | Finished Good | 완제품 | Level 0 | FP |
| P | Packaging | 패키지 | Level 1 | PKG |
| K | Kit | 키트 | Level 2 | KIT |
| S | Semi-Finished Good | 서브어셈블리 | Level 3 | SET |
| R | Raw/Component | 단품/원자재 | Level 4 | EA |
| M | Manufacturing | 조립공정 | 공정 | EA |

> **R(단품)과 M(조립공정)**: BOM 관리에 필수적인 레벨

---

## 5. 데이터베이스 스키마

### 5.1 테이블 구조 개요

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         데이터베이스 구조                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [품번 구성 코드 테이블]                                                  │
│  ├── product_line (대분류/제품라인) - 4자리                              │
│  ├── part_group (소분류/품목군) - 3자리                                  │
│  ├── material (재질) - 2자리                                            │
│  └── treatment (후처리) - 2자리                                         │
│                                                                         │
│  [분류 코드 테이블]                                                       │
│  ├── development_type (분류1/개발구분) - 1자리                           │
│  ├── part_type (분류2/부품유형) - 1자리, 중복선택                         │
│  └── drawing_type (분류3/도면여부) - 1자리                               │
│                                                                         │
│  [BOM 코드 테이블]                                                       │
│  └── level (레벨) - 1자리                                               │
│                                                                         │
│  [마스터 테이블]                                                         │
│  └── parts (부품 마스터)                                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 코드 테이블 공통 구조

모든 코드 테이블은 다음 공통 컬럼을 가집니다:

```sql
CREATE TABLE code_table_template (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10) NOT NULL UNIQUE,    -- 코드값
    name_ko     VARCHAR(100) NOT NULL,          -- 한글명
    name_en     VARCHAR(100),                   -- 영문명
    description TEXT,                           -- 설명
    sort_order  INT DEFAULT 0,                  -- 정렬순서
    is_active   BOOLEAN DEFAULT TRUE,           -- 사용여부
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP
);
```

### 5.3 parts 테이블 구조

```sql
CREATE TABLE parts (
    id                  SERIAL PRIMARY KEY,
    
    -- 품번 (자동생성, UNIQUE)
    part_number         VARCHAR(25) NOT NULL UNIQUE,  -- HB01-DCP-00001-A6-NK
    
    -- 품번 구성 요소 (FK)
    product_line_id     INT NOT NULL REFERENCES product_line(id),
    part_group_id       INT NOT NULL REFERENCES part_group(id),
    item_code           VARCHAR(5) NOT NULL,          -- 00001
    material_id         INT NOT NULL REFERENCES material(id),
    treatment_id        INT NOT NULL REFERENCES treatment(id),
    
    -- 기본 정보
    part_name           VARCHAR(200) NOT NULL,        -- 부품명
    part_name_en        VARCHAR(200),                 -- 영문 부품명
    description         TEXT,                         -- 설명
    
    -- 분류 속성 (검색용)
    development_type_id INT NOT NULL REFERENCES development_type(id),  -- 분류1
    part_types          JSONB DEFAULT '[]',           -- 분류2 (중복선택, ["P","O"])
    drawing_type_id     INT NOT NULL REFERENCES drawing_type(id),      -- 분류3
    
    -- 레벨 (BOM용)
    level_id            INT NOT NULL REFERENCES level(id),
    
    -- 규격 정보
    specification       VARCHAR(500),                 -- 규격
    unit_id             INT REFERENCES unit(id),      -- 단위
    
    -- 버전 관리
    version             VARCHAR(10) DEFAULT 'A0',
    revision            INT DEFAULT 0,
    revision_note       TEXT,
    
    -- 가격 정보
    unit_price          DECIMAL(15,2) DEFAULT 0,
    currency            VARCHAR(10) DEFAULT 'KRW',
    price_updated_at    TIMESTAMP,
    
    -- 조달 정보
    procurement_type_id INT REFERENCES procurement_type(id),
    supplier_id         INT REFERENCES business_partner(id),
    lead_time_days      INT,
    min_order_qty       INT DEFAULT 1,
    
    -- 첨부파일
    drawing_file        VARCHAR(500),
    photo_file          VARCHAR(500),
    document_files      JSONB,
    
    -- 승인 상태
    approval_status     VARCHAR(20) DEFAULT 'DRAFT',
    approved_by         INT,
    approved_at         TIMESTAMP,
    
    -- 상태
    status              VARCHAR(20) DEFAULT 'ACTIVE',
    is_active           BOOLEAN DEFAULT TRUE,
    
    -- 감사
    created_by          INT,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_by          INT,
    updated_at          TIMESTAMP,
    
    -- 비고
    remark              TEXT,
    
    -- 품번 중복 방지 (전체 조합이 UNIQUE)
    CONSTRAINT uq_part_number_components UNIQUE (
        product_line_id, part_group_id, item_code, material_id, treatment_id
    )
);
```

### 5.4 품번 자동생성 로직

```python
def generate_part_number(
    db: Session,
    product_line_id: int,
    part_group_id: int,
    item_code: str,          # 수동입력 또는 자동추천값
    material_id: int,
    treatment_id: int
) -> str:
    """
    품번 자동생성
    
    Args:
        db: 데이터베이스 세션
        product_line_id: 대분류 ID
        part_group_id: 소분류 ID
        item_code: 품목코드 (5자리 숫자)
        material_id: 재질 ID
        treatment_id: 후처리 ID
    
    Returns:
        생성된 품번 (예: HB01-DCP-00001-A6-NK)
    
    Raises:
        ValueError: 품목코드 형식 오류 또는 중복
    """
    
    # 1. 품목코드 형식 검증
    if not (len(item_code) == 5 and item_code.isdigit()):
        raise ValueError("품목코드는 숫자 5자리여야 합니다")
    
    # 2. 코드값 조회
    product_line = db.query(ProductLine).get(product_line_id)
    part_group = db.query(PartGroup).get(part_group_id)
    material = db.query(Material).get(material_id)
    treatment = db.query(Treatment).get(treatment_id)
    
    if not all([product_line, part_group, material, treatment]):
        raise ValueError("유효하지 않은 코드 ID")
    
    # 3. 품번 생성
    part_number = f"{product_line.code}-{part_group.code}-{item_code}-{material.code}-{treatment.code}"
    
    # 4. 중복 체크
    exists = db.query(Part).filter(Part.part_number == part_number).first()
    if exists:
        raise ValueError(f"이미 존재하는 품번입니다: {part_number}")
    
    return part_number


def suggest_next_item_code(
    db: Session,
    product_line_id: int,
    part_group_id: int
) -> str:
    """
    다음 품목코드 추천
    해당 대분류+소분류 내에서 가장 큰 품목코드 + 1
    """
    max_item_code = db.query(func.max(Part.item_code))\
        .filter(Part.product_line_id == product_line_id)\
        .filter(Part.part_group_id == part_group_id)\
        .scalar()
    
    if max_item_code:
        next_code = str(int(max_item_code) + 1).zfill(5)
    else:
        next_code = "00001"
    
    return next_code
```

---

## 6. 구현 작업 목록

### Phase 1: 코드 테이블 생성 (신규)

1. **품번 구성 코드 테이블 생성**
   - `product_line` (대분류/제품라인) - 4자리
   - `part_group` (소분류/품목군) - 3자리
   - `material` 테이블 유지, 데이터 확인/추가
   - `treatment` 테이블 유지, WA 코드 추가

2. **분류 코드 테이블 생성**
   - `development_type` (분류1/개발구분)
   - `part_type` (분류2/부품유형)
   - `drawing_type` (분류3/도면여부)

3. **BOM 코드 테이블 수정**
   - `level` 테이블에 R, M 코드 추가

4. **기존 테이블 정리**
   - `major_category` → 삭제 또는 비활성화
   - `middle_category` → 삭제 또는 비활성화
   - `minor_category` → 삭제 또는 비활성화
   - `sub_category` → 삭제 또는 비활성화
   - `item_code` → 삭제 또는 비활성화

### Phase 2: Parts 모델 수정

1. **모델 필드 변경**
   - 기존 FK 제거: major_category_id, middle_category_id, minor_category_id 등
   - 신규 FK 추가: product_line_id, part_group_id, development_type_id, drawing_type_id
   - item_code: FK → VARCHAR(5)로 변경
   - part_types: JSONB 필드 추가

2. **품번 생성 로직 수정**
   - 새 품번 구조 적용
   - 품목코드 자동추천 + 수동입력 지원
   - 전체 품번 중복 체크

### Phase 3: 스키마 및 API 수정

1. **Pydantic 스키마 수정**
   - PartCreate, PartUpdate 스키마 수정
   - part_types: List[str] 처리

2. **API 엔드포인트 수정**
   - 품번 생성 API
   - 품목코드 추천 API 추가
   - 분류 기반 검색 API

### Phase 4: 프론트엔드 수정

1. **코드 마스터 화면**
   - 신규 코드 테이블 관리 UI
   - 관리자 모드에서 코드 추가/수정/삭제

2. **부품 등록/수정 화면**
   - 새 품번 구조 반영
   - 품목코드 자동추천 + 수동입력 UI
   - 분류2 다중선택 UI (체크박스)
   - 분류3 드롭다운 추가

---

## 7. 관리자 기능

### 7.1 코드 마스터 관리

관리자는 다음 코드 테이블을 관리할 수 있습니다:

| 테이블 | 기능 | 주의사항 |
|--------|------|----------|
| product_line | 추가/수정/삭제 | 4자리 코드, 사용중인 코드 삭제 불가 |
| part_group | 추가/수정/삭제 | 3자리 코드, 사용중인 코드 삭제 불가 |
| material | 추가/수정/삭제 | 2자리 코드, 사용중인 코드 삭제 불가 |
| treatment | 추가/수정/삭제 | 2자리 코드, 사용중인 코드 삭제 불가 |
| development_type | 추가/수정/삭제 | 1자리 코드 |
| part_type | 추가/수정/삭제 | 1자리 코드 |
| drawing_type | 추가/수정/삭제 | 1자리 코드 |
| level | 추가/수정/삭제 | 1자리 코드 |

### 7.2 삭제 제한 규칙

```python
def can_delete_code(code_type: str, code_id: int, db: Session) -> bool:
    """
    코드 삭제 가능 여부 확인
    해당 코드를 사용하는 부품이 있으면 삭제 불가
    """
    if code_type == "product_line":
        count = db.query(Part).filter(Part.product_line_id == code_id).count()
    elif code_type == "part_group":
        count = db.query(Part).filter(Part.part_group_id == code_id).count()
    # ... 기타 코드 타입
    
    return count == 0
```

---

## 8. 변경 이력

| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-09 | 초안 작성 |
| 1.1 | 2026-01-09 | 대분류 4자리, 소분류 3자리로 변경. 분류2 JSON 배열 방식. 후처리 전/후 부품 별도 관리 명시. 관리자 모드 코드 관리 기능 추가. |

---

## 부록 A: 품번 예시

| 품번 | 분해 | 설명 |
|------|------|------|
| HB01-DCP-00001-A6-NK | HB01/DCP/00001/A6/NK | HXB11, 더스트캡부품, 1번, AL6061, 니켈 |
| BI03-PLP-00015-S4-NN | BI03/PLP/00015/S4/NN | XBI13, 플러그부품, 15번, STS304, 후처리없음 |
| TF01-OCP-00003-L1-A0 | TF01/OCP/00003/L1/A0 | TFOCA, 광학부품, 3번, LAK-10, AR코팅 |
| COM0-BLT-00001-S4-NN | COM0/BLT/00001/S4/NN | 공용, 볼트/너트, 1번, STS304, 후처리없음 |

## 부록 B: 후처리 전/후 부품 BOM 예시

```
[후처리 BOM 구조]

HB01-DCP-00001-A6-NK (니켈 도금 완료 부품) [R]
├─ HB01-DCP-00001-A6-NN (후처리 전 부품) [R] × 1EA
└─ 니켈 도금 공정 [M]

→ 재고는 각각 별도 관리
→ 후처리 전 부품 10개 + 후처리 후 부품 5개 = 총 15개
```
