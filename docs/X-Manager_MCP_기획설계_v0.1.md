# X-Manager MCP 서버 기획·설계 v0.1

작성일: 2026-11-04 · 상태: 기획/설계(구현 전)

---

## 1. 결론

**가능합니다.** X-Manager는 이미 REST API(약 500개 엔드포인트), JWT 로그인, 모듈별 RBAC(운영 `enforce`), 감사 로그를 갖추고 있습니다. 그래서 MCP 서버는 **기존 API 앞에 얹는 얇은 어댑터**로 만들 수 있습니다. 업무 로직이나 DB 구조는 건드리지 않습니다.

권장 방향은 네 가지입니다.

1. **별도 프로세스, 별도 가상환경**으로 만듭니다. 백엔드 venv에 넣으면 안 됩니다(근거는 3.2).
2. **DB를 직접 읽지 않고 REST API를 거칩니다.** 사용자 본인 권한(RBAC), 감사 로그, 업무 규칙이 그대로 적용됩니다.
3. **도구는 업무 단위로 골라서 만듭니다.** 엔드포인트 500개를 1:1로 노출하지 않고, 질문 단위로 약 25개를 만듭니다.
4. **읽기 전용부터 시작합니다.** 쓰기는 마지막 단계에서 "초안 작성"까지만 엽니다.

| 단계 | 내용 | 사용처 |
|---|---|---|
| Phase 0 | 개인 MCP 토큰(PAT) 발급·폐기 기능 (백엔드) | — |
| Phase 1 | 로컬(stdio) MCP 서버, 읽기 전용 핵심 도구 | Claude Code, Claude Desktop (사내 PC) |
| Phase 2 | 원격(Streamable HTTP) + OAuth 로그인 | claude.ai 웹·모바일 커스텀 커넥터 |
| Phase 3 | 제한적 쓰기 (초안 작성까지만) | 전체 |

---

## 2. 목표와 사용 시나리오

Claude에서 자연어로 X-Manager 데이터를 조회하고 분석합니다. 화면을 여러 개 오가며 엑셀로 옮겨 정리하던 일을 대화 한 번으로 줄이는 것이 목표입니다.

예시 질문과 내부 동작:

- "ETM1GM-S1 50대 만들려면 부족한 자재가 뭐야?" → BOM 전개 + 재고 + 생산 가능 여부 확인
- "HXB13 커넥터가 들어가는 제품 전부 찾아줘" → 역전개(Where-used)
- "EDM1GM-S2 원가 구성에서 비싼 순으로 10개" → BOM 원가 내역
- "이번 달 생산요청 중 출하 예정일 지난 건 정리해줘" → 생산요청 목록 + 상태
- "○○ 거래처 최근 거래와 미수금" → 거래처 타임라인·잔액
- "내 결재 대기 문서 요약해줘" → 결재함

MCP와 사내 AI 기능은 다른 것입니다. 사내 AI 기능은 X-Manager 화면 안에 Claude API를 넣는 방식입니다. MCP는 이미 쓰고 있는 Claude 앱(Claude Code, Desktop, claude.ai)에 X-Manager를 "연결"하는 방식이라 화면 개발이 필요 없습니다.

---

## 3. 아키텍처

### 3.1 구성도

```
[Claude Code / Claude Desktop]            [claude.ai 웹·모바일]
        │ stdio (Phase 1)                         │ HTTPS + OAuth (Phase 2)
        ▼                                         ▼
┌──────────────────────────┐        Caddy  xmanager.xbeamtech.co.kr/mcp
│ xmanager-mcp (별도 venv)  │◀─────────────────────┘
│  - 도구/리소스/프롬프트    │
│  - 응답 다듬기(필드·한도)  │
└──────────┬───────────────┘
           │ HTTPS  Authorization: Bearer xmp_…(개인 토큰)
           ▼
┌──────────────────────────┐
│ X-Manager 백엔드 :8000    │  ← RBAC(module_guard)·감사 로그·업무 규칙 그대로 적용
└──────────┬───────────────┘
           ▼
     PostgreSQL 18 (xmanager)
```

### 3.2 핵심 결정과 근거

| 결정 | 근거 |
|---|---|
| **별도 프로세스·별도 venv** | 2026-11-04에 백엔드 venv로 `pip install --dry-run mcp`를 실행해 봤습니다. 최신 SDK(mcp 2.3.0)를 설치하면 pydantic 2.6.1→2.14, **starlette 0.36→1.10**, uvicorn 0.27→0.54로 강제 업그레이드됩니다. FastAPI 0.110은 starlette 0.36대에 묶여 있어서 **운영 백엔드가 깨질 수 있습니다.** MCP 서버를 분리하면 서로의 업그레이드에 영향을 주지 않습니다. |
| **REST 경유, DB 직접 접근 금지** | RBAC는 라우터 단위 가드(`module_guard`)에서 검사하고, 업무 규칙은 서비스 계층에 있습니다. DB를 직접 읽으면 권한(원가·연차 등)을 우회하게 됩니다. `pr_dict`를 손으로 조립하는 식의 응답 가공 로직도 중복됩니다. REST를 거치면 "사용자가 화면에서 볼 수 있는 것만 Claude도 본다"가 자동으로 보장됩니다. |
| **업무 단위 도구 약 25개** | 도구가 수백 개면 Claude가 고르기 어렵고 컨텍스트를 낭비합니다. "부품 검색 → BOM 전개 → 재고"처럼 질문 단위로 묶고, 응답은 필요한 필드만 남깁니다. |
| **읽기 우선** | AI가 실수로 결재 승인, 재고 조정, 삭제를 하는 위험을 처음부터 없앱니다. 쓰기는 Phase 3에서 "초안"까지만 엽니다(7장). |

### 3.3 기술 스택

- **언어**: Python 3.12. 백엔드와 같은 언어라 유지보수가 쉽습니다.
- **SDK**: 공식 MCP Python SDK `mcp` 2.x.
  - `from mcp.server import MCPServer`, `@mcp.tool()`, `@mcp.resource(...)`를 씁니다.
  - stdio와 streamable-http 전송을 모두 지원합니다.
  - 세부 API는 착수할 때 SDK 문서로 다시 확인합니다.
- **REST 호출**: SDK가 함께 설치하는 `httpx2` 비동기 클라이언트를 씁니다.
- **위치**: 저장소 루트에 `mcp-server/`를 두고, 독립된 `pyproject.toml`과 `.venv`를 갖습니다.

```
mcp-server/
├── pyproject.toml
├── xmanager_mcp/
│   ├── __main__.py      # 진입점: --transport stdio|http
│   ├── server.py        # MCPServer 생성, 도구 등록
│   ├── client.py        # X-Manager REST 클라이언트(토큰, 오류 변환, 타임아웃)
│   ├── tools/           # parts.py, bom.py, inventory.py, production.py, sales.py, approval.py …
│   ├── shaping.py       # 응답 필드 축소·한글 라벨·화면 링크
│   └── resources.py     # 코드 마스터·품번 체계 리소스
└── tests/
```

도구 하나의 모양(개념 예시):

```python
@mcp.tool()
async def get_bom_tree(part_number: str, depth: int = 3) -> dict:
    """완제품·어셈블리의 BOM을 전개한다. part_number 는 품번 또는 모델명(예: ETM1GM-S1)."""
    part = await xm.get_part_by_number(part_number)      # GET /parts/by-number/{pn}
    tree = await xm.get(f"/bom/tree/{part['id']}")        # GET /bom/tree/{id}
    return shape_bom_tree(tree, max_depth=depth)          # 필요한 필드만, 깊이 제한
```

---

## 4. 인증·권한 설계

### 4.1 현재 상태 (확인 결과)

- **로그인**: 아이디·비밀번호로 로그인하면 access JWT(60분)와 refresh JWT(7일)를 받습니다. IP+ID 기준 5회 실패 시 15분 잠금됩니다.
- **권한**: `module:action` 형식(예: `part:view`, `price:view`)이고, 운영은 `RBAC_MODE=enforce`입니다.
  - 연차(`leave`)는 항상 enforce입니다.
  - 결재, 관리자, 권한, 인증 라우터는 자체적으로 인증합니다.
- **API 토큰**: 기계용 장기 토큰 개념은 **없습니다.**

### 4.2 Phase 0 — 개인 MCP 토큰(PAT) 신설

MCP 서버가 사용자 대신 API를 호출하려면 사용자 신원이 필요합니다. 고려한 방법은 세 가지입니다.

| 방법 | 판단 |
|---|---|
| 설정 파일에 아이디·비밀번호 저장 | ✗ 평문 비밀번호가 PC에 남습니다. 비밀번호를 바꾸면 깨지고, 잠금 정책과도 충돌합니다. |
| 만료가 긴 JWT 발급 | ✗ 개별 폐기가 불가능합니다. SECRET_KEY가 유출되면 모든 토큰이 위험해집니다. |
| **개인 토큰(PAT)** | ✓ 사용자별 발급, 범위 지정, 만료, 즉시 폐기, 마지막 사용 시각 기록이 가능합니다. Phase 2 OAuth 토큰도 같은 테이블을 재사용합니다. |

**구현 개요**

1. **테이블** `api_tokens`
   - 컬럼: `id, user_id, name, prefix, token_hash, scopes, expires_at, last_used_at, revoked_at, created_at`
   - 원문은 저장하지 않고 sha256 해시만 저장합니다. 토큰은 32바이트 난수라 sha256으로 충분합니다.
   - Alembic 마이그레이션은 만들기만 하고, `upgrade`는 운영자가 직접 실행합니다.
2. **토큰 형식**: `xmp_<prefix>_<secret>`. 접두어가 있어 로그나 깃에 섞여도 식별할 수 있습니다.
3. **인증 분기**: `core/auth.py`의 `get_current_user`에서 Bearer 값이 `xmp_`로 시작하면 PAT로 조회합니다.
   - 폐기, 만료, 비활성 사용자는 거부합니다.
   - 통과하면 해당 User를 돌려줍니다.
   - 이후 RBAC는 기존 로직이 그대로 적용됩니다.
4. **범위(scope)**: Phase 1은 `read`만 둡니다. 미들웨어 한 곳에서 **read 토큰의 GET/HEAD 외 요청은 403**으로 막습니다.
   - 결재처럼 자체 인증하는 라우터까지 한 지점에서 막힙니다.
   - 부작용: 읽기 전용이지만 POST로 만든 헬퍼(설명 자동조합 등)는 read 토큰으로 호출할 수 없습니다. MCP v1에는 필요 없는 헬퍼입니다.
5. **발급 UI**: "내 정보"에 "MCP 토큰" 카드를 추가합니다.
   - 이름, 만료(기본 90일)를 정해 발급합니다. 원문은 **발급 순간 한 번만** 보여줍니다.
   - 목록에서 마지막 사용 시각을 보고 폐기할 수 있습니다.
   - 관리자는 전 직원의 토큰 목록을 보고 강제 폐기할 수 있습니다.
6. **감사**: MCP 서버는 모든 요청에 `X-XM-Client: mcp/<도구명>` 헤더를 붙입니다. 감사 미들웨어가 이를 읽어 `[작업] 홍길동(MCP:get_bom_tree) · …`처럼 구분해 남깁니다.

**선택 사항: 모듈 제한.** 관리자(ADMIN, 와일드카드 권한) 계정의 토큰은 모든 데이터를 볼 수 있습니다. 필요하면 `api_tokens.modules`에 허용 모듈을 넣어 토큰 단위로 더 좁힐 수 있습니다(예: 원가 제외).

### 4.3 Phase 2 — OAuth (claude.ai 커스텀 커넥터)

claude.ai는 원격 MCP 서버에 OAuth로 연결합니다. 사용자가 커넥터를 추가하면 X-Manager 로그인 창이 뜨고, 로그인과 동의를 마치면 연결됩니다.

- X-Manager 백엔드가 **인가 서버** 역할을 합니다.
  - 메타데이터: `/.well-known/oauth-authorization-server`, `/.well-known/oauth-protected-resource`
  - `/oauth/authorize`: X-Manager 로그인 + "Claude가 내 X-Manager 데이터를 조회하도록 허용" 동의 화면
  - `/oauth/token`: PKCE 필수
  - `/oauth/register`: 동적 클라이언트 등록
- 발급하는 액세스 토큰은 4.2의 PAT 테이블을 그대로 씁니다(`name="claude.ai"`, 단기 만료 + refresh).
- MCP 서버는 받은 Bearer 토큰을 그대로 X-Manager API에 전달합니다. 토큰을 검증하는 주체는 백엔드 하나입니다.
- OAuth 스펙 세부(메타데이터 필드, 동적 등록 필수 여부, claude.ai 플랜별 커넥터 지원)는 **착수할 때 MCP 인증 스펙과 claude.ai 문서로 다시 확인합니다.**

---

## 5. 도구 설계 (v1, 읽기 전용)

### 5.1 도구 목록

호출 API는 현재 라우터 기준으로 확인한 경로입니다(접두어 `/api/v1`). 필요 권한은 사용자에게 없으면 403이 납니다.

| 도구 | 설명 | 호출 API | 권한 |
|---|---|---|---|
| `search_parts` | 품번·품명·키워드·분류로 부품 검색 | `GET /parts` | part:view |
| `get_part` | 부품 상세(품번 또는 id) | `GET /parts/{id}`, `/parts/by-number/{pn}` | part:view |
| `get_bom_tree` | BOM 전개(깊이 제한) | `GET /bom/tree/{id}` | bom:view |
| `find_where_used` | 역전개(이 부품을 쓰는 상위품) | `GET /bom/parents/{id}` | bom:view |
| `get_bom_cost` | BOM 원가 산출 내역 | `GET /prices/parts/{id}/bom-cost/breakdown` | price:view |
| `get_price_history` | 단가 이력(기준·발주·평균) | `GET /prices/parts/{id}/history` | price:view |
| `get_stock` | 부품 재고·LOT | `GET /inventory/part/{id}`, `/inventory/{part_id}/lots` | inventory:view |
| `list_stock_alerts` | 안전재고 미달·재고 없음 | `GET /inventory/low-stock`, `/inventory/out-of-stock` | inventory:view |
| `get_stock_history` | 입출고 이력 | `GET /inventory/part/{id}/transactions` | inventory:view |
| `check_build_availability` | N대 생산 시 자재 충족 여부 | `GET /work-orders/check-availability` (파라미터는 구현 시 확인) | workorder:view |
| `list_production_requests` | 생산요청 목록(상태·기간·거래처) | `GET /production-requests` | production:view |
| `get_production_request` | 생산요청 상세 | `GET /production-requests/{id}` | production:view |
| `list_work_orders` | 작업지시 목록 | `GET /work-orders` | workorder:view |
| `get_work_order` | 작업지시 상세 + 공정 이력 | `GET /work-orders/{id}`, `/{id}/process-logs` | workorder:view |
| `list_purchase_orders` | 발주 목록 | `GET /purchase-orders` | purchase:view |
| `get_purchase_order` | 발주 상세 | `GET /purchase-orders/{id}` | purchase:view |
| `search_partners` | 거래처 검색 | `GET /partners` | partner:view |
| `get_partner` | 거래처 상세 + 타임라인·잔액 | `GET /partners/{id}`, `/{id}/timeline`, `/{id}/balance` | partner:view |
| `list_sales_documents` | 견적·PI·CI 목록 | `GET /sales-documents/` | sales:view |
| `get_sales_document` | 영업문서 상세·진행상태 | `GET /sales-documents/{id}`, `/{id}/process-status` | sales:view |
| `get_sales_summary` | 매출·수금 요약 | `GET /sales-documents/analytics/summary`, `/collection/summary` | sales:view |
| `list_sales_activities` | 영업 대응 현황 | `GET /sales-activities` | sales_activity:view |
| `get_sales_activity` | 대응 건 상세 + 로그 | `GET /sales-activities/{id}`, `/{id}/logs` | sales_activity:view |
| `list_my_approvals` | 내 결재 대기·기안 문서 | `GET /approvals`, `/approvals/pending-count` | 결재 자체 인증 |
| `get_approval` | 결재 문서 상세·의견 | `GET /approvals/{id}`, `/{id}/comments` | 결재 자체 인증 |
| `get_dashboard` | 대시보드 요약 | `GET /dashboard/summary` | dashboard:view |

모든 도구에 MCP 도구 주석 `readOnlyHint: true`를 붙입니다.

### 5.2 리소스·프롬프트

- **리소스** (Claude가 품번 체계를 이해하도록 제공하는 참조 자료)
  - `xmanager://codes/{종류}`: 제품라인, 품목군, 레벨, 단위, 재질, 후처리, 조달유형 코드표(`/code-master` 조회)
  - `xmanager://docs/part-numbering`: 부품코드 관리기준서 요약. 품번 구성은 `HB01-DCP-001-01-A6-NK [R]` 같은 형식입니다.
- **프롬프트** (자주 쓰는 분석의 시작 템플릿)
  - "자재 부족 점검": 제품과 수량을 입력하면 부족 자재와 발주 필요량을 정리합니다.
  - "BOM 원가 분석": 원가 상위 항목, 단가가 없는 부품, 최근 단가 변동을 봅니다.
  - "주간 생산·영업 현황": 생산요청, 작업지시, 영업 대응 건의 주간 요약입니다.

### 5.3 응답 설계

- **필드 축소**: API 응답을 그대로 넘기지 않습니다. 도구마다 필요한 필드만 남기고, 내부 id는 후속 호출에 필요한 것만 유지합니다.
- **한도**: 목록 기본 20건, 최대 100건(API의 `page_size ≤ 100`과 같음)입니다. 잘렸으면 `"전체 N건 중 20건 표시"`를 함께 돌려줍니다. BOM 전개는 기본 깊이 3입니다.
- **화면 링크**: 상세 화면이 있는 항목은 링크를 붙입니다(`/bom/{id}/edit`, `/approvals/{id}` 등). 나머지는 목록 화면 링크로 대신합니다. 사용자는 Claude 답변에서 바로 X-Manager로 이동할 수 있습니다.
- **오류 변환**: HTTP 코드를 사람이 이해할 문장으로 바꿉니다.
  - 401: "토큰이 만료·폐기되었습니다. 내 정보에서 재발급하세요"
  - 403: "`price:view` 권한이 없습니다. 관리자에게 요청하세요"
  - 404: "해당 품번을 찾을 수 없습니다. `search_parts`로 먼저 검색하세요"
- **품번 해석**: `ETM1GM-S1`처럼 접미사 `[F]` 없이 입력해도 찾아야 합니다. 정확히 일치하는 것이 없으면 검색 후보를 돌려줍니다.

### 5.4 v1 제외 범위

- **연차·인사**(`leave`): 민감 정보라 제외합니다.
- **사용자, 권한, 시스템 설정, 백업**: 관리자 기능이라 제외합니다.
- **파일 원본**(도면 PDF, 첨부, 패킹 사진): 바이너리라 제외합니다. 필요하면 Phase 2 이후에 "파일 목록 + 화면 링크"만 제공합니다.
- **알림, 푸시, 공지 작성**
- **모든 쓰기**: 7장 참조.

---

## 6. 보안·운영 고려사항

| 항목 | 대응 |
|---|---|
| **데이터 반출** | 도구 결과는 Claude 대화에 들어갑니다. 원가, 단가, 고객 정보가 외부 AI 서비스로 전달된다는 뜻입니다. 어떤 모듈을 허용할지는 **회사 차원의 결정**이 필요합니다(8장). 결정에 따라 PAT 모듈 제한(4.2 선택 사항)으로 강제합니다. |
| 권한 | 토큰 주인의 RBAC가 그대로 적용됩니다. MCP가 권한을 넓히는 일은 없습니다. |
| 토큰 유출 | 해시만 저장하고, 만료(기본 90일)를 두며, 즉시 폐기와 마지막 사용 기록을 제공합니다. 접두어 `xmp_`로 깃 커밋 검사(시크릿 스캔)에 걸리게 합니다. |
| 감사 | 모든 호출이 기존 감사 로그에 사용자와 도구명으로 남습니다. |
| 과다 호출 | MCP 서버에서 토큰별 초당 호출 수를 제한하고, REST 타임아웃을 10초로 둡니다. 백엔드는 단일 프로세스이므로 무거운 조회(전체 엑셀 내보내기 등)는 도구로 만들지 않습니다. |
| 프롬프트 인젝션 | 비고, 의견, 영업 로그 같은 자유 텍스트는 "데이터"로 취급합니다. v1은 쓰기 도구가 없어 영향이 조회에 그칩니다. Phase 3에서 쓰기를 열 때는 사용자 확인이 필수입니다. |
| 개발 → 운영 | 개발 백엔드(:8001, xmanager_dev DB)로 먼저 검증한 뒤 운영(:8000)에 연결합니다. 대상은 `XM_BASE_URL` 환경변수로 바꿉니다. |

---

## 7. Phase 3 — 쓰기 도구 원칙 (후보)

- **열 수 있는 것** (초안·기록 성격, 되돌리기 쉬움)
  - 영업 대응 로그 추가
  - 미분류 부품 최소등록: 이름만 넣으면 PT-UID로 채번되고, 이후 분류를 승격합니다.
  - 기안서 **임시저장**
- **열지 않는 것**: 결재 승인·반려·상신, 재고 입출고·조정, 삭제, 단가 확정, 발주 확정, 사용자·권한 변경
- **조건**
  - 토큰 scope에 `write`가 있어야 합니다.
  - 도구에 `destructiveHint`·`idempotentHint` 주석을 붙입니다.
  - 응답에 "생성된 초안 링크 — 화면에서 확인 후 확정하세요"를 넣어 사람이 최종 확정하게 합니다.

---

## 8. 결정이 필요한 사항

1. **사용 범위**: 우선 본인(개발·관리)만 Claude Code·Desktop에서 쓸지(Phase 1까지), 직원들도 claude.ai에서 쓰게 할지(Phase 2 필요) 정해야 합니다.
2. **데이터 허용 범위**: Claude로 조회를 허용할 모듈을 정해야 합니다. 특히 **원가·단가**(`price`), **거래처·매출**(`partner`, `sales`), **결재 문서 본문**이 대상입니다.
3. **쓰기 허용 여부**: v1을 읽기 전용으로 하는 데 동의하는지, 그리고 Phase 3 후보(7장) 중 실제로 원하는 것이 있는지 정해야 합니다.

---

## 9. 단계별 작업 계획

| 단계 | 작업 | 완료 기준 |
|---|---|---|
| **Phase 0** | `api_tokens` 모델·마이그레이션, `get_current_user` PAT 분기, read 토큰 쓰기 차단 미들웨어, 내 정보 토큰 발급·폐기 UI, 감사 로그 MCP 표시 | 개발 서버에서 PAT로 `GET /parts` 200, `POST`는 403, 폐기 직후 401 |
| **Phase 1** | `mcp-server/` 골격(별도 venv), REST 클라이언트·오류 변환, 핵심 도구 10개(search_parts, get_part, get_bom_tree, find_where_used, get_bom_cost, get_stock, check_build_availability, list/get_production_request, list_my_approvals), Claude Code·Desktop 연결 안내 | 2장 시나리오 중 앞의 3개가 개발 DB에서 정답과 일치. 권한 없는 계정으로 원가 조회 시 403 안내 문구 확인 |
| **Phase 1.5** | 나머지 도구, 리소스, 프롬프트, 응답 다듬기 튜닝 | 2장 시나리오 전체 통과 |
| **Phase 2** | streamable-http 실행(:8010, 감시 루프 bat), Caddy `/mcp`·`/.well-known/oauth-*` 라우팅, 백엔드 OAuth 엔드포인트·동의 화면 | claude.ai에서 커넥터 추가 → X-Manager 로그인 → 조회 성공. 토큰 폐기 시 즉시 차단 |
| **Phase 3** | 합의된 쓰기 도구만 | 초안 생성 후 화면에서 확인·확정되는 흐름 |

**테스트**

- 단위: REST 응답을 목(mock)으로 두고 도구별 응답 다듬기와 오류 변환을 검증합니다(pytest).
- 프로토콜: MCP Inspector(`mcp dev`)로 도구 목록과 스키마를 확인합니다.
- 시나리오: 개발 DB에서 2장 질문을 실제 Claude로 실행하고, 결과를 화면 값과 대조합니다. 예를 들어 1채널 원가 804,789원과 대조합니다.

**연결 예시 (Phase 1, 확정 전)**

```bash
# Claude Code
claude mcp add xmanager \
  --env XM_BASE_URL=https://xmanager.xbeamtech.co.kr/api/v1 \
  --env XM_TOKEN=xmp_xxxx \
  -- C:\X-MANAGER_R0.1\mcp-server\.venv\Scripts\python.exe -m xmanager_mcp
```

Claude Desktop은 `claude_desktop_config.json`의 `mcpServers`에 같은 명령과 환경변수를 넣습니다.
