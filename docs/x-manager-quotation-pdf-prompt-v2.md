# X-Manager 견적서 PDF 생성 모듈 개발 (Phase 1)

## 프로젝트 컨텍스트

- **회사**: 엑스빔테크(XBEAM TECH) — 군용/방산 광섬유 커넥터 제조사
- **시스템**: X-Manager (사내 CRM/BOM/영업 관리 통합 시스템)
- **스택**: Vue.js 3 (frontend) + FastAPI (backend) + PostgreSQL + Caddy
- **배포 환경**: Windows 온프레미스 서버
- **주요 고객**: 국내 방산 + 16개국 이상 해외 수출 (한·영 양면 문서 필수)

## 이번 작업 목표 (Phase 1로 한정)

**견적서(Quotation) 1종**을 HTML 템플릿 + WeasyPrint로 PDF 생성하는 **백엔드 모듈**까지만 구현합니다. 이번 Phase에서 다루지 **않는** 것:

- PI(Proforma Invoice) — 다음 Phase
- Vue 프론트엔드 UI — 다음 Phase
- documents 테이블 자동 저장 — 다음 Phase
- 이메일 발송 — 다음 Phase

이번 Phase 종료 시점의 기대 결과물: **API 호출 한 번으로 견적서 PDF가 다운로드되는 상태**.

## 작업 시작 전 필수 확인

코드를 작성하기 전에 **반드시** 다음을 먼저 파악하고 보고:

1. 백엔드 디렉토리 구조 (`app/`, `api/`, `services/` 등의 위치와 명명 규칙)
2. 기존 FastAPI 라우터 등록 패턴 (예: `api/v1/__init__.py`에서 어떻게 모듈을 묶는지)
3. 의존성 주입 방식 (DB 세션, 인증 등이 어떻게 들어오는지)
4. Pydantic 모델 위치 및 명명 규칙
5. requirements.txt 또는 pyproject.toml의 현재 패키지 목록

이 파악이 끝난 뒤에 아래 Step 1부터 진행. 기존 컨벤션을 따라야 함.

## 기술 스택 (이번 모듈에 추가)

- **WeasyPrint** — HTML/CSS → PDF 변환
- **Jinja2** — 템플릿 엔진 (FastAPI에 이미 있을 가능성 높음)
- **한글 폰트** — 나눔고딕 또는 본고딕(Noto Sans KR), OFL/SIL 라이선스 안전

> Windows에 WeasyPrint를 설치할 때 GTK3 런타임 의존성이 필요합니다. 설치 절차도 README에 함께 정리해주세요.

## 견적서 양식 구성 요소

| 영역 | 내용 |
|------|------|
| 헤더 | 회사 로고 + 주소 + 연락처 + 견적서 번호 + 발행일자 + 유효기간 |
| 수신처 | 고객사명, 담당자, 주소, 연락처 |
| 품목 테이블 | P/N, 품명/사양, 수량, 단가, 합계 (강조 표시 지원) |
| 합계 | 소계, 부가세(국내만), 총액 — 통화 KRW/USD/EUR 지원 |
| 거래조건 | 결제조건, 인도조건(Incoterms), 견적 유효기간, 비고 |
| 서명란 | 담당자명 + 직인 이미지 자리 |
| 푸터 | 페이지 번호 (1/N), 회사 푸터 정보 |

## 강조 표시 기능 (Phase 1 포함)

방산 광커넥터 P/N은 옵션 코드가 길어서(예: `HXB11-08-SM9/125-FA`) 고객사가 핵심 차이점을 놓치는 경우가 있음. 이를 위해 영업담당자가 입력 단계에서 강조하고 싶은 부분을 마크업으로 지정하면 PDF 렌더링 시 색상·굵기·배경으로 표시되도록 함.

### 입력 문법 (인라인 마크업 방식)

| 문법 | 의미 | 적용 스타일 |
|------|------|------------|
| `[[텍스트]]` | 핵심 강조 (위험/주의) | 빨간색 + 굵게 |
| `{{텍스트}}` | 보조 강조 | 노란 배경 하이라이트 |
| `__텍스트__` | 사양 강조 | 빨간 밑줄 |

입력 예시:
```
HXB11-08-[[SM9/125]]-FA
[[MIL-DTL-38999]] Series III, {{Cadmium plated}}
Operating Temp: __-55°C ~ +125°C__
```

### 변환 처리

- Jinja2 **커스텀 필터** 또는 별도 유틸 함수로 구현 (예: `{{ item.part_number | highlight }}`)
- HTML 이스케이프를 **먼저** 적용한 뒤 마크업 변환 (XSS 방지)
- 변환 결과를 `<span class="...">...</span>`으로 출력
- 마크업 우선순위: `[[...]]` → `{{...}}` → `__...__` 순으로 처리

### 적용 범위 (Phase 1)

- 품목 테이블의 **part_number**, **description** 컬럼만
- 거래조건(terms) 본문, 비고란 등은 다음 Phase에서 확장

### CSS (quotation.css에 추가)

```css
.highlight-critical {
  color: #c00;
  font-weight: 700;
}
.highlight-warning {
  background-color: #fff3cd;
  padding: 0 2px;
  border-radius: 2px;
}
.highlight-spec {
  text-decoration: underline;
  text-decoration-color: #c00;
  text-decoration-thickness: 1.5px;
}
```

## 권장 파일 구조 (기존 컨벤션에 맞춰 조정)

```
backend/
  app/
    api/v1/
      quotations.py              # PDF 다운로드 엔드포인트
    services/
      pdf/
        __init__.py
        quotation_pdf.py         # PDF 생성 서비스
        fonts.py                 # 폰트 등록 유틸
        highlight.py             # 인라인 마크업 변환 유틸
    schemas/
      quotation.py               # Pydantic 모델 (이미 있다면 확장)
    templates/pdf/
      base.html                  # 공통 레이아웃 (@page, 푸터)
      quotation_ko.html
      quotation_en.html
      styles/
        common.css
        quotation.css
      assets/
        logo.png                 # placeholder 사용, 실제 파일은 추후 교체
        stamp.png                # placeholder
        fonts/                   # 폰트 파일 (라이선스 OK인 것만)
```

## 단계별 진행 (각 Step 끝날 때마다 보고 후 다음 진행)

### Step 1 — 환경 세팅
- WeasyPrint 및 의존성 설치
- requirements.txt 업데이트
- Windows GTK3 설치 가이드를 README에 추가
- 폰트 파일 배치 (라이선스 명시)

### Step 2 — 데이터 모델
- `QuotationPdfData` Pydantic 모델 (PDF 생성에 필요한 모든 필드)
- `QuotationLineItem` 모델 — `part_number`, `description` 필드는 마크업 문법 입력 허용
- 통화·언어·Incoterms enum 정의
- 테스트용 샘플 픽스처 1건 (HXB 시리즈 커넥터 견적, 강조 마크업 포함)
  - 예: `part_number="HXB11-08-[[SM9/125]]-FA"`

### Step 3 — 강조 마크업 변환 유틸
- `services/pdf/highlight.py`에 `apply_highlights(text: str) -> Markup` 함수
- 처리 순서:
  1. `html.escape()`로 안전 처리
  2. `[[...]]` → `<span class="highlight-critical">...</span>`
  3. `{{...}}` → `<span class="highlight-warning">...</span>`
  4. `__...__` → `<span class="highlight-spec">...</span>`
  5. Jinja2 `Markup`으로 감싸서 추가 이스케이프 방지
- Jinja2 환경에 `highlight` 커스텀 필터로 등록

### Step 4 — HTML/CSS 템플릿
- `base.html`: `@page` 규칙, 페이지 번호, 공통 푸터
- `quotation_ko.html`, `quotation_en.html`: 본문 (품목 컬럼은 `| highlight` 필터 적용)
- `quotation.css`: 강조 스타일 3종 + 일반 표·헤더 스타일
- A4 기준, 여백·폰트 사이즈는 인쇄 품질 우선
- WeasyPrint의 `@page` 규칙으로 페이지 번호 (1/N) 처리

### Step 5 — PDF 생성 서비스
- `QuotationPdfService` 클래스
  - `render(data: QuotationPdfData, lang: Literal["ko", "en"]) -> bytes`
- 폰트 등록은 `fonts.py`에서 한 번만
- Jinja2 환경에 `highlight` 필터 등록
- 에러 처리: 폰트 누락, 템플릿 누락, 데이터 누락, 잘못된 마크업 등

### Step 6 — API 엔드포인트
- `GET /api/v1/quotations/{id}/pdf?lang=ko` (기존 라우터 컨벤션에 맞춰 GET/POST 결정)
- 응답: `Content-Type: application/pdf`, `Content-Disposition: attachment`
- 인증·권한 체크는 기존 미들웨어 그대로 적용

### Step 7 — 검증
- pytest 단위 테스트
  - PDF bytes 길이, 매직넘버 `%PDF-` 확인
  - **강조 마크업 변환 테스트**: 각 문법별 입력 → 기대 HTML 출력
  - **XSS 방지 테스트**: `<script>alert(1)</script>` 같은 입력이 이스케이프되는지
  - 중첩/오류 마크업 처리(예: `[[unclosed`) 안전성
- 샘플 데이터로 ko/en 두 PDF 생성 후 실제 PDF 리더로 시각 확인
  - `HXB11-08-[[SM9/125]]-FA` → `SM9/125`만 빨간 굵은 글자로 출력되는지 확인
- 품목 30개 이상 케이스로 페이지 분할 확인
- 한글 깨짐, 직인/로고 위치, 통화 포맷 확인

## 주의사항

- **한 번에 전부 만들지 말 것.** 각 Step 끝나면 작동 확인 후 다음 Step으로.
- 직인·로고 이미지는 placeholder만 두고 실제 파일은 사용자가 교체.
- 폰트 라이선스 OFL/Apache/Noto 계열만 사용 (방산 고객 납품 문서이므로 라이선스 클린해야 함).
- 통화·소수점·천단위 구분자는 로케일에 맞춰 분기 (KRW는 정수, USD/EUR는 소수점 2자리).
- Incoterms는 enum으로 관리 (EXW, FCA, CPT, CIP, DAP, DPU, DDP, FAS, FOB, CFR, CIF).
- 견적서 번호 체계는 기존 X-Manager 규칙이 있으면 그대로 따름. 없으면 별도 논의.
- 영문 템플릿에서 한글이 섞일 수 있으므로(예: 한국 고객사 영문 견적서에 회사명 한글 병기) 한글 폰트는 양쪽 다 등록.
- **강조 마크업은 반드시 HTML 이스케이프 후에 변환**할 것 (XSS 방지). 입력값을 신뢰하지 말 것.
- 마크업 문법은 Phase 2 이후 키워드 자동 강조와 공존해야 하므로, 변환 로직을 한 곳(`highlight.py`)에 모아 둘 것.

## 다음 Phase 예고 (이번에 구현 X, 설계만 염두)

- **Phase 2**: 
  - PI 양식 추가 + base 템플릿 공통화 강화
  - 키워드 자동 강조 (사전 등록된 키워드 — `SM`, `MM`, 군사규격 번호 등 — 자동 빨간색 처리)
- **Phase 3**: 생성 PDF를 `documents` 테이블에 저장 + `sales_activities` 로그 연결
- **Phase 4**: 
  - Vue 프론트엔드 미리보기/다운로드 UI
  - 리치 텍스트 에디터(Quill/TipTap) 도입 검토 — 영업담당자가 엑셀처럼 직접 색상 지정
- **Phase 5**: Mailplug MCP 연동 이메일 발송

지금부터 **Step 1부터 차근차근** 진행해주세요. 각 Step 끝나면 결과 요약 후 다음 Step 진행 여부 확인해주세요.
