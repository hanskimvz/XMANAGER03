# X-Manager 개발 기획서 v1.3

## 부품관리 및 BOM 시스템

**작성일**: 2025년 6월  
**회사명**: 엑스빔테크  
**문서버전**: 1.3 (BOM 실제 데이터 반영)

---

## 1. 프로젝트 개요

### 1.1 목적
방산용 광학 커넥터 제조업체의 전사적 자원 관리를 위한 통합 시스템 구축.  
1단계로 **부품 마스터 관리**, **공정 관리**, **BOM(Bill of Materials) 구성** 기능을 개발한다.

### 1.2 범위 (1단계)

| 구분 | 기능 | 우선순위 |
|------|------|----------|
| 코드관리 | 분류 코드 체계 관리 | ★★★ |
| 부품관리 | 부품 마스터 등록/수정/조회/승인 | ★★★ |
| 공정관리 | 공정 마스터 등록/수정/조회 | ★★★ |
| 대체품관리 | 대체품 그룹 및 매핑 관리 | ★★★ |
| BOM관리 | 재귀형 BOM 구성 및 조회 | ★★★ |
| 원가계산 | BOM 기반 원가 산출 | ★★☆ |
| 승인관리 | 부품/BOM 승인 워크플로우 | ★★☆ |

### 1.3 예상 데이터 규모

- 부품 마스터: 약 1,000건
- 공정 마스터: 약 50~100건
- BOM: 약 200~500건 (제품/서브어셈블리 기준)
- 대체품 그룹: 약 100~200건

---

## 2. 기술 스택 (확정)

### 2.1 기술 스택 개요

```
┌─────────────────────────────────────────────────────────────────────┐
│                     X-Manager 기술 스택                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   프론트엔드     Vue.js 3.4+  +  Tailwind CSS 3.4+  +  Pinia 2.1+   │
│                 Vite, Vue Router, Axios                            │
│                                                                     │
│   백엔드        FastAPI 0.110+  +  SQLAlchemy 2.0+  +  Pydantic 2.0+│
│                 Uvicorn, Alembic, Python-Jose                      │
│                                                                     │
│   데이터베이스   PostgreSQL 15+                                      │
│                 (WITH RECURSIVE, JSONB, Full-text Search)          │
│                                                                     │
│   배포          Docker 24+  +  Nginx 1.24+                         │
│                 Docker Compose                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 코드 체계 정의

### 3.1 분류 체계 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                        부품 분류 체계                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [상위분류]                                                          │
│  ├── 대분류 (Major): 개발구분 - D/S/M/R/C/P                          │
│  ├── 중분류 (Middle): 부품유형 - P/E/O/M/G/C/B/I/W/A/F/H/X/T         │
│  └── 상세요구 (Detail): 도면여부 - D/N/S                             │
│                                                                     │
│  [하위분류]                                                          │
│  ├── 소분류 (Minor): 제품라인 - HB1/HB3/HB5/TF1/IS1/CRP 등          │
│  ├── 세분류 (Sub): 부품군 - DC/BI/PP/RP/CH/CM/PS/HP 등               │
│  └── 품목코드 (Item): 세부품목 - CB00/GP00/LN00/SF00 등              │
│                                                                     │
│  [속성분류]                                                          │
│  ├── 재질 (Material): A6/S4/NB/AB/BR 등 (생략시 'XX')               │
│  ├── 후처리 (Treatment): NK/ZK/HB/CD/WA/NN 등                       │
│  └── 레벨 (Level): F/P/K/S/R/M                                      │
│                                                                     │
│  [조달분류]                                                          │
│  └── 조달구분: 가공품/구매품/사출품/반제품/완제품                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 대분류 코드 (개발구분)

| 코드 | 영문명 | 한글명 | 설명 |
|------|--------|--------|------|
| D | Developed Part | 개발품 | 자체 설계/개발 부품 |
| S | Standard Part | 규격품 | 표준 규격 부품 |
| M | Market Part | 상용품 | 시중 구매 부품 |
| R | Raw Material | 원소재 | 원자재 |
| C | Custom Part | 주문품 | 고객 맞춤 부품 |
| P | Process | 공정 | 제조 공정 |

### 3.3 중분류 코드 (부품유형)

| 코드 | 영문명 | 한글명 |
|------|--------|--------|
| P | Processed Part | 가공품 |
| E | Elastomer Part | 고무품 |
| O | Optical Part | 광학품 |
| M | Mold Part | 금형품 |
| G | Mechanical | 기계류 |
| C | Die-cast Part | 다이캐스트품 |
| B | Bearing | 베어링 |
| I | Injection Part | 사출품 |
| W | Wire | 와이어류 |
| A | Assembly | 조립품 |
| F | Fastener | 체결품 |
| H | Hardware | 하드웨어 |
| X | Chemical Part | 화학품 |
| T | Tube | 수축튜브 |

### 3.4 소분류 코드 (제품라인)

| 코드 | 제품라인 | 설명 |
|------|----------|------|
| HB1 | HXB11 | Expanded Beam 11핀 |
| HB3 | HXB13 | Expanded Beam 13핀 |
| HB5 | HXB15 | Expanded Beam 15핀 |
| HB7 | HXB17 | Expanded Beam 17핀 |
| HB0 | HXB공용 | HXB 시리즈 공용 |
| **TF1** | **TFOCA** | **TFOCA 커넥터** |
| IS1 | XBI11 | 인서트 11핀 |
| IS3 | XBI13 | 인서트 13핀 |
| IS5 | XBI15 | 인서트 15핀 |
| IS7 | XBI17 | 인서트 17핀 |
| IS0 | XBI공용 | XBI 시리즈 공용 |
| CRP | 케이블류 | 케이블류 부품 |
| COM | 상용품 | 상용 구매품 |

### 3.5 재질 코드 (확장)

| 코드 | 재질명 | 설명 |
|------|--------|------|
| A6 | AL6061 | 알루미늄 6061 합금 |
| S4 | STS304 / AISI 304 | 스테인리스 304 |
| S3 | SUS303 | 스테인리스 303 |
| S6 | SUS316 | 스테인리스 316 |
| NB | NBR | 니트릴 고무 |
| EP | EPDM | EPDM 고무 |
| SI | Silicone | 실리콘 |
| AB | ABS | ABS 플라스틱 |
| BR | Brass | 황동 |
| L1 | LAK-10 | 광학 유리 |
| **XX** | **미지정** | 복합재질/미정의 |

### 3.6 후처리 코드 (확장)

| 코드 | 후처리명 | 설명 |
|------|----------|------|
| NK | 니켈 | 니켈 도금 |
| ZK | 징크-니켈 | 징크니켈 도금 |
| **CD** | **카드뮴** | **국방색 카드뮴 도금** |
| HB | 하드 블랙 | 하드 아노다이징 (블랙) |
| **WA** | **백색 아노다이징** | **White Anodizing** |
| A0 | AR코팅 | 반사방지 코팅 |
| **NN** | **없음** | **후처리 없음** |

### 3.7 레벨 코드 (BOM 단계) - 확장

| 코드 | 영문명 | 한글명 | BOM레벨 | 기본단위 |
|------|--------|--------|---------|----------|
| F | Finished Good | 완제품 | Level 0 | FP |
| P | Package | 패키지 | Level 1 | PKG |
| K | Kit | 키트 | Level 2 | KIT |
| S | Sub-Assembly | 서브어셈블리/세트 | Level 3 | SET |
| R | Raw/Component | 단품/원자재 | Level 4 | EA |
| **M** | **Manufacturing** | **조립공정** | 공정 | EA |

> ⚠️ **M (조립공정)**: BOM 내에서 조립 단계를 표시. 부품이 아닌 작업을 나타냄.

### 3.8 조달 구분 코드 (신규)

| 코드 | 구분 | 설명 | 예시 |
|------|------|------|------|
| MFG | 가공품 | 자체/외주 기계가공 | 커넥터홀더, 인서트 |
| PUR | 구매품 | 외부 구매 완제품 | 오링, 볼트, 너트 |
| INJ | 사출품 | 사출 성형품 | 스페이서, 고무부트 |
| SEM | 반제품 | 중간 조립품 | 커넥터 아세이, 더스트캡 아세이 |
| FIN | 완제품 | 최종 제품 | TFOCA PLUG ASSEMBLY |

### 3.9 단위 코드 (신규)

| 코드 | 명칭 | 설명 |
|------|------|------|
| EA | Each | 개별 단품 |
| SET | Set | 세트 (서브어셈블리) |
| KIT | Kit | 키트 |
| PKG | Package | 패키지 |
| FP | Finished Product | 완제품 |
| M | Meter | 미터 (케이블류) |
| MM | Millimeter | 밀리미터 |
| G | Gram | 그램 (화학품) |
| ML | Milliliter | 밀리리터 |

---

## 4. 품번 체계 (확정)

### 4.1 품번 생성 규칙

```
┌─────────────────────────────────────────────────────────────────────┐
│                         품번 구성 (11~12자리)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│    [대분류] - [소분류] - [품목코드] - [재질] - [레벨]                  │
│       1자리     3자리      4자리      2자리    1자리                  │
│                                                                     │
│    예시: D - TF1 - PG01 - A6 - S                                    │
│          │    │     │     │    │                                    │
│          │    │     │     │    └── 레벨: S(서브어셈블리)              │
│          │    │     │     └─────── 재질: A6(AL6061)                 │
│          │    │     └───────────── 품목: PG01(플러그 #01)            │
│          │    └─────────────────── 소분류: TF1(TFOCA)               │
│          └──────────────────────── 대분류: D(개발품)                 │
│                                                                     │
│    최종 품번: D-TF1-PG01-A6-S  (표시용)                              │
│              DTF1PG01A6S       (시스템용)                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 품번 예시

| 품번 | 분해 | 설명 |
|------|------|------|
| D-TF1-PG01-A6-F | D/TF1/PG01/A6/F | 개발품, TFOCA, 플러그01, AL6061, 완제품 |
| D-TF1-CH01-A6-R | D/TF1/CH01/A6/R | 개발품, TFOCA, 커넥터홀더01, AL6061, 단품 |
| M-COM-OR16-NB-R | M/COM/OR16/NB/R | 상용품, 공용, 오링AN016, NBR, 단품 |
| D-TF1-DC01-A6-K | D/TF1/DC01/A6/K | 개발품, TFOCA, 더스트캡01, AL6061, 키트 |

---

## 5. 데이터베이스 설계

### 5.1 ERD 개요

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           데이터베이스 구조                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [코드 마스터]                                                           │
│  major_category, minor_category, item_code, material,                   │
│  treatment, level, procurement_type, unit                               │
│                              │                                          │
│                              ▼                                          │
│  [핵심 마스터]                                                           │
│  ┌──────────────┐              ┌──────────────┐                        │
│  │    parts     │◄────────────▶│   process    │                        │
│  └───────┬──────┘              └──────────────┘                        │
│          │                                                              │
│  ┌───────┴───────┐                                                     │
│  ▼               ▼                                                     │
│ supplier     alt_part_group ──▶ alt_part_mapping                       │
│                                                                         │
│  [BOM 구조 - 재귀]                                                       │
│  bom_header ──▶ bom_detail (child_bom_id로 재귀 참조)                   │
│       │              │                                                  │
│       │              └──▶ [M] 조립공정 포함                              │
│       │                                                                 │
│       └──▶ bom_process                                                 │
│                                                                         │
│  [가격 이력]                                                             │
│  price_history (단가 변동 이력 관리)                                     │
│                                                                         │
│  [승인 관리]                                                             │
│  approval_workflow ──▶ approval_history                                │
│                                                                         │
│  [사용자]                                                                │
│  users ──▶ permissions                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 테이블 정의 (업데이트)

#### 5.2.1 부품 마스터 테이블 (확장)

```sql
CREATE TABLE parts (
    id                  SERIAL PRIMARY KEY,
    
    -- 품번 (자동생성)
    part_number         VARCHAR(20) NOT NULL UNIQUE,
    part_number_display VARCHAR(25),                -- 하이픈 포함 표시용
    
    -- 기본 정보
    part_name           VARCHAR(200) NOT NULL,
    part_name_en        VARCHAR(200),
    description         TEXT,
    
    -- 분류 코드 (FK)
    major_category_id   INT NOT NULL,               -- 대분류
    middle_category_id  INT,                        -- 중분류
    minor_category_id   INT NOT NULL,               -- 소분류 (제품라인)
    sub_category_id     INT,                        -- 세분류
    item_code_id        INT NOT NULL,               -- 품목코드
    material_id         INT,                        -- 재질 (NULL이면 'XX')
    treatment_id        INT,                        -- 후처리
    level_id            INT NOT NULL,               -- 레벨
    
    -- 조달 정보 (신규)
    procurement_type_id INT,                        -- 조달구분 (FK)
    
    -- 규격 정보
    specification       VARCHAR(500),               -- 규격 (AN016, SER-20 등)
    unit_id             INT,                        -- 단위 (FK)
    
    -- 버전 관리
    version             VARCHAR(10) DEFAULT 'A0',
    revision            INT DEFAULT 0,              -- 리비전 번호 (0, 1, 2...)
    revision_note       TEXT,
    
    -- 가격 정보
    unit_price          DECIMAL(15,2) DEFAULT 0,
    currency            VARCHAR(10) DEFAULT 'KRW',
    price_updated_at    TIMESTAMP,                  -- 단가 기입 날짜
    
    -- 조달 정보
    supplier_id         INT,                        -- 주 공급업체
    lead_time_days      INT,
    min_order_qty       INT DEFAULT 1,
    
    -- 대체품 그룹
    alt_part_group_id   INT,
    
    -- 첨부파일
    file_name           VARCHAR(500),               -- 도면 파일명 (신규)
    drawing_file        VARCHAR(500),               -- 도면 파일 경로
    photo_file          VARCHAR(500),               -- 사진 파일 경로
    document_files      JSONB,                      -- 기타 문서
    
    -- 승인 상태
    approval_status     VARCHAR(20) DEFAULT 'DRAFT',
    approved_by         INT,
    approved_at         TIMESTAMP,
    
    -- 상태
    status              VARCHAR(20) DEFAULT 'ACTIVE',
    is_active           BOOLEAN DEFAULT TRUE,
    
    -- 감사
    created_by          INT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by          INT,
    updated_at          TIMESTAMP,
    
    -- 비고
    remark              TEXT,                       -- 비고 (신규)
    
    -- 외래키
    FOREIGN KEY (major_category_id) REFERENCES major_category(id),
    FOREIGN KEY (minor_category_id) REFERENCES minor_category(id),
    FOREIGN KEY (item_code_id) REFERENCES item_code(id),
    FOREIGN KEY (level_id) REFERENCES level(id),
    FOREIGN KEY (procurement_type_id) REFERENCES procurement_type(id),
    FOREIGN KEY (unit_id) REFERENCES unit(id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(id),
    FOREIGN KEY (alt_part_group_id) REFERENCES alt_part_group(id)
);
```

#### 5.2.2 조달구분 코드 테이블 (신규)

```sql
CREATE TABLE procurement_type (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10) NOT NULL UNIQUE,    -- 'MFG', 'PUR', 'INJ' 등
    name_ko     VARCHAR(50) NOT NULL,           -- '가공품', '구매품' 등
    name_en     VARCHAR(50),
    description TEXT,
    sort_order  INT DEFAULT 0,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 초기 데이터
INSERT INTO procurement_type (code, name_ko, name_en) VALUES
('MFG', '가공품', 'Manufactured'),
('PUR', '구매품', 'Purchased'),
('INJ', '사출품', 'Injection'),
('SEM', '반제품', 'Semi-finished'),
('FIN', '완제품', 'Finished');
```

#### 5.2.3 단위 코드 테이블 (신규)

```sql
CREATE TABLE unit (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10) NOT NULL UNIQUE,    -- 'EA', 'SET', 'KIT' 등
    name_ko     VARCHAR(50) NOT NULL,
    name_en     VARCHAR(50),
    description TEXT,
    sort_order  INT DEFAULT 0,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 초기 데이터
INSERT INTO unit (code, name_ko, name_en) VALUES
('EA', '개', 'Each'),
('SET', '세트', 'Set'),
('KIT', '키트', 'Kit'),
('PKG', '패키지', 'Package'),
('FP', '완제품', 'Finished Product'),
('M', '미터', 'Meter'),
('G', '그램', 'Gram'),
('ML', '밀리리터', 'Milliliter');
```

#### 5.2.4 가격 이력 테이블 (신규)

```sql
CREATE TABLE price_history (
    id              SERIAL PRIMARY KEY,
    
    part_id         INT NOT NULL,               -- 부품 (FK)
    
    -- 가격 정보
    unit_price      DECIMAL(15,2) NOT NULL,     -- 단가
    currency        VARCHAR(10) DEFAULT 'KRW',
    
    -- 변경 정보
    effective_date  DATE NOT NULL,              -- 적용일
    expire_date     DATE,                       -- 만료일
    
    -- 출처
    source          VARCHAR(100),               -- 견적서, 계약서 등
    supplier_id     INT,                        -- 공급업체
    
    -- 감사
    created_by      INT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remark          TEXT,
    
    FOREIGN KEY (part_id) REFERENCES parts(id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(id)
);

CREATE INDEX idx_price_history_part ON price_history(part_id, effective_date DESC);
```

#### 5.2.5 BOM 상세 테이블 (업데이트)

```sql
CREATE TABLE bom_detail (
    id              SERIAL PRIMARY KEY,
    
    bom_header_id   INT NOT NULL,               -- BOM 헤더 (FK)
    
    -- 하위 항목 (부품, 하위 BOM, 또는 공정)
    child_part_id   INT,                        -- 하위 부품 (FK)
    child_bom_id    INT,                        -- 하위 BOM (FK) - 재귀 참조
    
    -- 항목 유형
    item_type       VARCHAR(10) NOT NULL,       -- 'PART', 'BOM', 'PROCESS'
    
    -- BOM 트리 위치
    tree_level      INT DEFAULT 1,              -- 트리 레벨 (1,2,3,4,5)
    tree_position   INT DEFAULT 0,              -- 동일 레벨 내 순서 (1,2,3...)
    parent_detail_id INT,                       -- 상위 BOM 상세 (트리 구조용)
    
    -- 수량 정보
    quantity        DECIMAL(10,4) NOT NULL,
    unit_id         INT,                        -- 단위 (FK)
    
    -- 대체품 사용 설정
    allow_alternative BOOLEAN DEFAULT TRUE,
    
    -- 비고
    remark          VARCHAR(500),
    
    -- 원가 (자동 계산)
    unit_cost       DECIMAL(15,2),
    extended_cost   DECIMAL(15,2),              -- 단가 × 수량
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP,
    
    FOREIGN KEY (bom_header_id) REFERENCES bom_header(id) ON DELETE CASCADE,
    FOREIGN KEY (child_part_id) REFERENCES parts(id),
    FOREIGN KEY (child_bom_id) REFERENCES bom_header(id),
    FOREIGN KEY (unit_id) REFERENCES unit(id),
    FOREIGN KEY (parent_detail_id) REFERENCES bom_detail(id),
    
    CONSTRAINT chk_item_type CHECK (
        (item_type = 'PART' AND child_part_id IS NOT NULL AND child_bom_id IS NULL) OR
        (item_type = 'BOM' AND child_bom_id IS NOT NULL AND child_part_id IS NULL) OR
        (item_type = 'PROCESS' AND child_part_id IS NULL AND child_bom_id IS NULL)
    )
);

-- 트리 조회용 인덱스
CREATE INDEX idx_bom_detail_tree ON bom_detail(bom_header_id, tree_level, tree_position);
```

### 5.3 BOM 트리 조회 쿼리 (PostgreSQL)

```sql
-- 재귀 CTE를 사용한 BOM 전개
WITH RECURSIVE bom_tree AS (
    -- 시작점: 최상위 BOM
    SELECT 
        bd.id,
        bd.bom_header_id,
        bd.child_part_id,
        bd.child_bom_id,
        bd.item_type,
        bd.tree_level,
        bd.quantity,
        bd.extended_cost,
        p.part_name,
        p.part_number,
        1 as depth,
        ARRAY[bd.tree_position] as path
    FROM bom_detail bd
    LEFT JOIN parts p ON bd.child_part_id = p.id
    WHERE bd.bom_header_id = :bom_id
    AND bd.parent_detail_id IS NULL
    
    UNION ALL
    
    -- 재귀: 하위 항목
    SELECT 
        bd.id,
        bd.bom_header_id,
        bd.child_part_id,
        bd.child_bom_id,
        bd.item_type,
        bd.tree_level,
        bd.quantity,
        bd.extended_cost,
        p.part_name,
        p.part_number,
        bt.depth + 1,
        bt.path || bd.tree_position
    FROM bom_detail bd
    LEFT JOIN parts p ON bd.child_part_id = p.id
    JOIN bom_tree bt ON bd.parent_detail_id = bt.id
)
SELECT * FROM bom_tree
ORDER BY path;
```

---

## 6. BOM 구조 상세

### 6.1 BOM 트리 구조 예시 (실제 데이터 기반)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TFOCA PLUG CONNECTOR BOM                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  L0 [F] TFOCA PLUG ASSEMBLY ────────────────────── 완제품 ¥125,465  │
│  │                                                                  │
│  └─ L1 [P] TFOCA PLUG PACKAGING ────────────────── 패키지           │
│     │                                                               │
│     ├─ L2 [K] 커넥터 KIT ───────────────────────── 키트 ¥68,100     │
│     │  │                                                            │
│     │  ├─ L3 [S] 커넥터 아세이-1 ────────────────── SET ¥60,050     │
│     │  │  ├─ L4 [R] 커넥터홀더 ────── A6/WA ── x1 ¥10,000          │
│     │  │  ├─ L4 [R] 인서트 ────────── S4/NN ── x1 ¥30,000          │
│     │  │  ├─ L4 [R] 픽스볼트 ──────── S4/NN ── x2 ¥12,000          │
│     │  │  ├─ L4 [R] 백플레이트 ────── A6/WA ── x1 ¥8,000           │
│     │  │  ├─ L4 [R] 오링 AN016 ───── NB ───── x1 ¥50              │
│     │  │  ├─ L4 [R] 스페이서 ──────── AB ───── x2 ¥0               │
│     │  │  ├─ L4 [R] TFOCA 패롤 ───── S4 ───── x4 ¥0               │
│     │  │  └─ L4 [R] 볼트 M2.5-8mm ── S4 ───── x2 ¥0               │
│     │  │                                                            │
│     │  ├─ L3 [S] 스트레인 아세이 ─────────────────── SET ¥8,050     │
│     │  │  ├─ L4 [R] 스트레인 릴리프 ── A6/WA ── x1 ¥8,000          │
│     │  │  ├─ L4 [R] 클램프링 ──────── BR/NN ── x1 ¥0   (사내재고)   │
│     │  │  └─ L4 [R] 오링 AN019 ───── NB ───── x1 ¥50              │
│     │  │                                                            │
│     │  └─ L3 [M] ◆ 조립 공정 ──────────────────────────────────    │
│     │                                                               │
│     ├─ L2 [K] 더스트캡 KIT ─────────────────────── 키트 ¥25,767     │
│     │  ├─ L3 [S] 더스트캡 ASSY ─────────────────── SET             │
│     │  │  ├─ L4 [S] 더스트캡 ASSY-1 ─────────────                   │
│     │  │  │  ├─ L5 [R] 캡바디 ────── A6/CD ── x1 ¥8,000            │
│     │  │  │  ├─ L5 [R] 오링 AN123 ── NB ───── x1 ¥77              │
│     │  │  │  ├─ L5 [R] 오링 AN317 ── NB ───── x1 ¥140             │
│     │  │  │  └─ L5 [R] 더스트실 ──── NB ───── x1 ¥1,500           │
│     │  │  ├─ L4 [S] 더스트캡 ASSY-2 ─────────────                   │
│     │  │  │  ├─ L5 [R] 이너바디 ──── A6/CD ── x1 ¥8,000            │
│     │  │  │  └─ L5 [R] 오링 AN018 ── NB ───── x1 ¥50              │
│     │  │  └─ L4 [M] ◆ 조립 공정                                     │
│     │  ├─ L3 [R] 더스트캡 커버 ────── A6/CD ── x1 ¥8,000            │
│     │  └─ L3 [M] ◆ 조립 공정                                        │
│     │                                                               │
│     ├─ L2 [K] 메인바디 KIT ─────────────────────── 키트 ¥22,373     │
│     │  └─ ...                                                       │
│     │                                                               │
│     ├─ L2 [R] 오링 AN319 ────────── NB ───── x1 ¥125               │
│     ├─ L2 [R] 고무 부트 ─────────── NB ───── x1 ¥1,100             │
│     ├─ L2 [R] 부트 와셔 ─────────── S4/NN ── x1 ¥0                 │
│     ├─ L2 [R] 백쉘 ───────────── A6/CD ── x1 ¥8,000               │
│     │                                                               │
│     └─ L2 [M] ◆ 최종 조립 공정                                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

범례: [F]=완제품, [P]=패키지, [K]=키트, [S]=서브어셈블리, [R]=단품, [M]=조립공정
      A6=AL6061, S4=STS304, NB=NBR, BR=황동, AB=ABS
      WA=백색아노다이징, CD=카드뮴도금, NN=후처리없음
```

### 6.2 원가 계산 로직

```python
def calculate_bom_cost(bom_header_id):
    """
    BOM 원가 계산 (재귀)
    - 재료비: 하위 부품/BOM 단가 × 수량 합계
    - 공정비: 조립 공정 비용 합계
    """
    
    total_material = 0
    total_process = 0
    
    for item in bom_details:
        if item.item_type == 'PART':
            # 단품: 단가 × 수량
            cost = item.part.unit_price * item.quantity
            total_material += cost
            item.extended_cost = cost
            
        elif item.item_type == 'BOM':
            # 하위 BOM: 재귀 호출
            sub_cost = calculate_bom_cost(item.child_bom_id)
            cost = sub_cost['total'] * item.quantity
            total_material += sub_cost['material'] * item.quantity
            total_process += sub_cost['process'] * item.quantity
            item.extended_cost = cost
            
        elif item.item_type == 'PROCESS':
            # 조립 공정: 공정 비용
            proc = get_process(item.remark)  # 공정명으로 조회
            if proc:
                total_process += proc.std_cost
    
    # BOM 공정 테이블의 공정비 추가
    for bom_proc in bom_processes:
        total_process += bom_proc.process_cost
    
    return {
        'material': total_material,
        'process': total_process,
        'total': total_material + total_process
    }
```

---

## 7. 화면 설계 (업데이트)

### 7.1 부품 등록 화면 (확장)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        부품 등록                         [임시저장]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─── 기본 정보 ───────────────────────────────────────────────────┐ │
│  │ 부품명*: [커넥터홀더                ]                            │ │
│  │ 영문명:  [Connector Holder         ]                            │ │
│  │ 설명:    [                                                  ]  │ │
│  │ 도면파일명: [83526V4_Connector_Holder_rev1        ] [파일찾기]   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─── 품번 생성 ───────────────────────────────────────────────────┐ │
│  │                                                                 │ │
│  │  대분류*: [D: 개발품   ▼]   소분류*: [TF1: TFOCA  ▼]            │ │
│  │  품목코드*: [CH01       ▼]  [+ 신규]                            │ │
│  │  재질:     [A6: AL6061  ▼]  ☐ 복합재질                          │ │
│  │  레벨*:    [R: 단품     ▼]                                      │ │
│  │                                                                 │ │
│  │  ▶ 자동생성 품번:  D-TF1-CH01-A6-R                              │ │
│  │  ▶ 중복 확인:      ✅ 사용 가능                                  │ │
│  │                                                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─── 속성 정보 ───────────────────────────────────────────────────┐ │
│  │  후처리: [WA: 백색 아노다이징 ▼]                                  │ │
│  │  규격:   [                                                  ]   │ │
│  │  조달구분*: [MFG: 가공품 ▼]    단위*: [EA: 개 ▼]                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─── 가격/조달 ───────────────────────────────────────────────────┐ │
│  │  단가*: [10,000    ] 원    단가기입일: [2025-12-19]              │ │
│  │  공급업체: [           ▼]  리드타임: [   ] 일                    │ │
│  │  비고: [                                                    ]   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─── 첨부파일 ────────────────────────────────────────────────────┐ │
│  │  도면: [파일선택]  사진: [파일선택]  기타: [파일선택]              │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│              [취소]  [임시저장]  [저장]  [저장 및 승인요청]           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 BOM 구성 화면 (트리 뷰)

```
┌─────────────────────────────────────────────────────────────────────┐
│  BOM 구성: TFOCA PLUG ASSEMBLY                    [저장] [승인요청] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─── BOM 정보 ────────────────────────────────────────────────────┐│
│  │ BOM코드: BOM-TF1-PG01-001  버전: 1.0  상태: [작성중]             ││
│  │ 제품: D-TF1-PG01-XX-F (TFOCA PLUG ASSEMBLY)                     ││
│  │ 작성일: 2025.12.19  리비전: 0  작성자: 홍길동                    ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ┌─── BOM 트리 ────────────────────────────── 총원가: ¥125,465 ────┐│
│  │                                                                 ││
│  │ ▼ 📦 TFOCA PLUG ASSEMBLY [F]                         ¥125,465  ││
│  │   ▼ 📦 TFOCA PLUG PACKAGING [P]                      ¥125,465  ││
│  │     ▼ 📁 커넥터 KIT [K]                     x1        ¥68,100  ││
│  │       ▼ 📁 커넥터 아세이-1 [S]              x1        ¥60,050  ││
│  │         ├─ 🔧 커넥터홀더 [R]      A6/WA    x1 EA      ¥10,000  ││
│  │         ├─ 🔧 인서트 [R]          S4/NN    x1 EA      ¥30,000  ││
│  │         ├─ 🔧 픽스볼트 [R]        S4/NN    x2 EA      ¥12,000  ││
│  │         ├─ 🔧 백플레이트 [R]      A6/WA    x1 EA       ¥8,000  ││
│  │         ├─ 🔧 오링 AN016 [R]      NB       x1 EA          ¥50  ││
│  │         ├─ 🔧 스페이서 [R]        AB       x2 EA           ¥0  ││
│  │         ├─ 🔧 TFOCA 패롤 [R]      S4       x4 EA           ¥0  ││
│  │         └─ 🔧 볼트 M2.5 [R]       S4       x2 EA           ¥0  ││
│  │       ▶ 📁 스트레인 아세이 [S]              x1         ¥8,050  ││
│  │       └─ ⚙️ 조립 [M]                                      ¥0  ││
│  │     ▶ 📁 더스트캡 KIT [K]                   x1        ¥25,767  ││
│  │     ▶ 📁 메인바디 KIT [K]                   x1        ¥22,373  ││
│  │     ├─ 🔧 오링 AN319 [R]          NB       x1 EA         ¥125  ││
│  │     ├─ 🔧 고무 부트 [R]           NB       x1 EA       ¥1,100  ││
│  │     ├─ 🔧 부트 와셔 [R]           S4/NN    x1 EA           ¥0  ││
│  │     ├─ 🔧 백쉘 [R]                A6/CD    x1 EA       ¥8,000  ││
│  │     └─ ⚙️ 최종 조립 [M]                                   ¥0  ││
│  │                                                                 ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ┌─── 항목 추가 ───────────────────────────────────────────────────┐│
│  │ ○ 부품  ○ 하위BOM  ○ 조립공정                                   ││
│  │ 검색: [                    ] [검색]  수량: [  ] [추가]          ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ┌─── 원가 요약 ───────────────────────────────────────────────────┐│
│  │ 재료비: ¥117,465    공정비: ¥8,000    총원가: ¥125,465          ││
│  │ 목표 판매가: ¥180,000 (마진율: 30.3%)                           ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. 권한 체계

*(v1.2와 동일)*

---

## 9. 개발 일정

### 9.1 1단계: 부품관리 + BOM (14주)

| 주차 | 작업 내용 | 산출물 |
|------|----------|--------|
| 1-2주 | 개발환경 구축, DB 스키마 생성 | 개발환경, DB |
| 3-4주 | 인증/권한, 코드 마스터 API | 로그인, 코드관리 |
| 5-6주 | 부품 마스터 API + 화면 | 부품 CRUD |
| 7-8주 | 공정 마스터, 대체품 관리 | 공정/대체품 기능 |
| 9-10주 | BOM 관리 (트리 구조) | BOM 구성 화면 |
| 11-12주 | 원가 계산, 가격 이력 | 원가/가격 기능 |
| 13-14주 | 승인 프로세스, 테스트, 배포 | 운영 배포 |

---

## 10. 문서 양식 (신규)

### 10.1 BOM 문서 양식

시스템에서 출력할 BOM 문서 양식 (엑셀 기반):

**표지**
- 모델명, 날짜(Rev.), 리비전 이력
- 제품 단가
- 결재란 (담당/팀장/이사/대표)
- 배포 (품질/구매/생산/영업)

**Partlist 시트**
- No, 사진, File Name, 품명
- 레벨, 품번, 파트넘버
- 재질, 후처리, 사양
- 수량, 단위, 조달
- 공급업체, 도번, Revision
- 비고, 단가 기입 날짜, 단가, 비용

**제작레벨 시트**
- 트리 구조 시각화 (들여쓰기)
- 레벨별 원가 소계

---

## 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2025-06 | Claude | 초안 작성 |
| 1.1 | 2025-06 | Claude | 품번체계, 재귀BOM, 대체품, 승인, 권한 추가 |
| 1.2 | 2025-06 | Claude | 기술 스택 확정 (FastAPI + Vue.js 3 + PostgreSQL) |
| 1.3 | 2025-06 | Claude | **BOM 실제 데이터 반영** - 레벨코드(M추가), 조달구분, 단위코드, 가격이력, 트리구조, 후처리코드 확장 |

