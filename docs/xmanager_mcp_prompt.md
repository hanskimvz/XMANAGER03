# X-Manager MCP 설계·구현 프롬프트 (1단계: 조회 전용)

> 사용법: 아래 "프롬프트" 블록 전체를 X-Manager MCP를 만들 Claude 세션(또는 개발 담당자)에게 그대로 전달한다.
> - 최신 코드: GitHub `xbeamtechcop/xmanager`의 `main` 브랜치. 운영 서버가 이 브랜치로 돌고 있다 (2026-11-10 확인).
> - 3번 조사표는 2026-11-10 운영 서버 기준으로 미리 채워 두었다. 받는 쪽은 최신 `main`에서 다시 확인만 하면 된다.
> - 확정된 결정: ① 다른 PC에서 HTTPS로 X-Manager REST API를 조회(DB 직접 접속 금지) ② 고객사 상세 정보는 넘기지 않음(메일에서 이미 수집 중) ③ 공용 조회 계정 1개로 운영(1단계는 관리자 혼자 사용).
> - 조회 계정은 2026-11-11에 만들어 두었다: 역할 "MCP 조회"(코드 MCP_READONLY) + 계정 `mcp_reader`. 비밀번호는 이 문서에 넣지 않고 따로 전달한다.

---

## 프롬프트

```
너는 사내 업무 시스템 X-Manager의 "영업 진행 현황"을 Claude가 조회할 수 있게 해 주는 MCP 서버를 설계하고 구현한다.
1단계 목표는 "조회 전용"이다. 데이터 추가·수정·삭제 기능은 만들지 않으며, 구조적으로도 불가능해야 한다.

## 1. 배경

- X-Manager: X-BeamTech(광통신 확장빔 커넥터·케이블 제조)의 사내 시스템. 거래처, 견적·PI·CI, 영업 대응, 생산요청을 관리한다.
  - 코드: GitHub xbeamtechcop/xmanager main (FastAPI 백엔드 + Vue 프론트). 운영 주소: https://xmanager.xbeamtech.co.kr (API는 /api/v1).
  - 테이블·필드 이름은 이 문서의 조사표를 출발점으로 쓰되, 구현 전에 최신 main의 API 응답 스키마(app/schemas, app/api/v1)로 다시 확인한다.
- 사용처: 영업 메일 점검 시스템. 메일플러그 메일을 AI로 분석해 업체별 진행 현황과 할 일을 보여 주는 로컬 도구이며, X-Manager 서버와는 다른 PC에서 돈다.
  메일 내용(연락처·주소·담당자 등)은 이미 그 도구가 수집한다. MCP는 메일로는 알 수 없는 "X-Manager에 기록된 현재 진행 상태"만 보강한다.
  - 견적·PI·CI·Invoice 발행 여부, 상태, 금액, 입금 상태
  - 생산요청 진행 단계, 희망 납기, 출고·발송 시각, CI 발행·선적, 분할선적 진행
  - 영업 대응 현황(프로젝트): 상태, 담당, 코멘트 이력
  - 같은 거래처·품목의 과거 견적 단가 (판매가만)
- 범위 밖: 고객사 상세 정보(주소, 전화, 이메일, 담당자 개인정보, 사업자번호, 은행 정보 등), 원가·마진, 재고, 구매.
- 사용자: 1단계는 X-Manager 관리자 1명(혼자 사용). Claude Desktop / Claude Code에서 자연어로 질문한다.

## 2. 반드시 지킬 원칙

1. 접속은 X-Manager REST API의 조회(GET)만 쓴다. DB에 직접 접속하지 않는다 (DB 포트는 외부에 열지 않는다).
   조회 전용을 세 겹으로 보장한다.
   - 계정: 공용 조회 계정 `mcp_reader` 하나를 쓴다 (2026-11-11 생성 완료). 역할 "MCP 조회"(MCP_READONLY)만 부여돼 있고, 권한은 조회 4개뿐이다:
     sales:view, sales_activity:view, partner:view, production:view (price:view=원가는 없다).
     운영 서버는 권한 강제(enforce) 모드라 이 계정의 쓰기 호출은 403으로 막힌다.
     생성 시 검증 결과: 로그인·토큰 갱신 200 / 거래처·영업문서·생산요청·영업대응 목록 200 /
     재고·구매·원가·사용자·역할 관리 GET 403 / 거래처·영업문서·생산요청·영업대응 POST 403.
     GET /api/v1/auth/me의 permissions가 위 4개인지 MCP 시작 시 확인하고, 다르면(특히 쓰기 권한이 있으면) 기동을 거부한다.
   - 코드: 호출할 API를 허용 목록(3번 표의 API)으로 고정한다. 목록 밖 경로, GET 이외의 메서드는 HTTP 클라이언트 단에서 거부한다.
     예외는 로그인·토큰 갱신(POST /api/v1/auth/login, /api/v1/auth/refresh) 두 개뿐이다.
     주의: GET인데도 서버에 저장하는 API가 있다 — GET /api/v1/sales-documents/{id}/pdf, GET /api/v1/cloud-files/entry. 허용 목록에 넣지 않는다.
     파일 다운로드·미리보기 API(…/download, …/preview, packing-photos, measurement-files)도 넣지 않는다.
   - 도구: 임의 경로나 임의 쿼리를 호출하는 도구는 만들지 않는다. 정해진 조회 도구만 제공한다.
2. 응답은 필드 허용 목록 방식으로 최소화한다. API 응답을 그대로 넘기지 않는다.
   - 거래처: 식별 정보만 — id, 코드, 이름, 국가, 고객/공급 구분, 국내/해외, 활성 여부.
     주소·전화·팩스·이메일·담당자·사업자번호·은행·신용·할인율·마진율·메모·첨부는 내보내지 않는다.
   - 메일 주소는 도메인 매칭에만 MCP 내부에서 쓰고, 어떤 응답에도 넣지 않는다.
   - 영업문서: 결제·납품 조건과 인코텀즈는 거래 조건이라 포함한다.
     은행 정보(bank_name, bank_address, swift_code, account_name, account_number — 우리 회사 계좌지만 제외),
     작성자 이메일, 수취인 상세(ship_to_* — "배송지 지정 여부" 불린만), 파일·폴더 경로(po_attachment_files, shipping_invoice_files, nextcloud_folder — 개수만)는 제외한다.
   - 생산요청: 상태·날짜·수량·생산기간은 포함한다. SHIPPING MARK·CONSIGNEE·DESTINATION 텍스트는 주소가 들어 있으므로 "등록 여부"만,
     첨부·사진·측정파일·고객 요구사항 텍스트·생산팀 메모는 제외한다.
   - 영업 대응: 제목, 거래처, 국가, 담당자, 상태, 문의 유형, 중요 표시, 현재/다음 단계, 지연 사유, 갱신일, 코멘트(작성자·일시·내용). 코멘트 첨부는 제외.
   - 원가·마진은 1단계에서 열지 않는다. 판매가(견적·PI 품목 단가)만.
3. 접속 정보는 환경변수(.env)에서만 읽는다: XMANAGER_BASE_URL, XMANAGER_USERNAME, XMANAGER_PASSWORD.
   토큰·비밀번호가 코드·로그·도구 응답에 절대 나오지 않게 한다. HTTPS 인증서 검증은 끄지 않는다.
4. 응답은 작게. 목록은 기본 20건, 최대 100건. 더 있으면 truncated: true와 다음 페이지 정보를 준다.
5. 모든 도구 호출을 로그로 남긴다 (시각, 도구, 인자, 호출한 API 경로, 응답 코드. 결과 본문은 남기지 않음).
6. X-Manager 저장소는 고치지 않는다. MCP는 별도 저장소(별도 Python 가상환경)로 만든다.
   X-Manager 쪽 변경이 꼭 필요하면 설계 문서에 "X-Manager 요청 사항"으로 따로 적는다.

## 3. 사전 조사 결과 (2026-11-10 운영 서버 기준 — 구현 전 최신 main에서 재확인)

| 필요한 정보 | API (GET, 접두어 /api/v1) | 데이터 현황 | 비고 |
|---|---|---|---|
| 이름·코드로 거래처 찾기 | /partners?keyword=&is_customer=&is_active=&limit(≤1000) | 거래처 142곳 | keyword는 코드·이름만 검색. 영문명 칸은 거의 비어 있음(2곳) |
| 메일 주소·도메인으로 거래처 찾기 (가장 중요) | 전용 API 없음 → /partners 응답의 email·manager_email + /partners/{id}/contacts의 email로 MCP 내부 색인 | 메일 정보가 전혀 없는 고객사 14곳 | 색인은 캐시(예: 6시간)하고 주기적으로 갱신. 공용 도메인(gmail 8곳, 163·naver·outlook 각 1곳)은 도메인이 아니라 주소 전체가 같을 때만 매칭. 한 도메인이 여러 거래처에 걸릴 수 있으므로(ardyx.eu → 2곳) 결과는 항상 후보 목록 |
| 거래처 최근 거래 요약 | /partners/{id}/recent-orders?limit | | 응답에서 허용 필드만 |
| 견적·PI·CI·Invoice 목록 | /sales-documents/?document_type=&customer_id=&status=&payment_status=&keyword=&include_old_versions=false&skip=&limit(≤200) | 934건 (견적 453, PI 283, CI 190, Invoice 8) | 견적은 버전 관리 → 기본은 최신 버전만. is_quote_only=true인 PI(견적 대용 PI, 7건)는 주문 집계에서 제외 |
| 문서 상세(품목·수량·단가·금액·통화·고객 PO·조건) | /sales-documents/{id} | 품목 2,249줄, 고객 PO 번호 395건 | 수량·단가가 TBD면 0과 *_text('TBD') — 텍스트 우선 표시 |
| 견적 → PI → CI 연결 | /sales-documents/{id}/related | 연결 564건 + 원본 문서 ID 397건 | 합배송(여러 PI → CI 1장)·분할선적(PI 1장 → CI 여러 장) 모두 있음 |
| 입금 상태·입금액·입금일 | 문서 상세의 payment_status(UNPAID/PARTIAL/PAID), paid_amount, paid_date / 미수 요약: /sales-documents/collection/summary, /collection/documents | PI: 완납 236, 부분 3, 미입금 44. 입금일은 88건만 기록 | 입금은 PI 기준으로 관리한다. CI·견적의 payment_status는 의미 없음 → CI는 원본 PI의 입금 상태를 보여 준다 |
| 주문 진행(요약) | /sales-documents/{PI id}/process-status | | PI발송→입금→생산요청→생산완료→CI발행→출하 6단계 done 플래그. 날짜가 없고 생산요청·CI는 첫 건만 본다 → 분할 생산·분할선적이면 아래 상세로 보정 |
| 주문 진행(상세) | /production-requests?keyword=&customer_id=&pr_status=&from_date=&to_date=&limit / /production-requests/{id} | 생산요청 96건, PI와 연결 94건 (pi_number, 품목별 pi_document_id) | 상태: IN_PROGRESS·SHIPPED·DELIVERED 사용 중(정의는 9종, 아래 라벨). 시각: requested_at(요청), due_date(희망 납기), insert_shipped_at(인서트출고, insert_not_applicable이면 해당 없음), production_shipped_at(생산출고), shipped_at(출고 완료), delivered_at(발송 완료). production_period(생산기간, 예 "5주") |
| 분할선적 진행 | 생산요청 상세의 품목 requested_quantity / ci_quantity | | 품목별 남은 수량 = 요청 − CI 발행 누적 |
| 단계별 예정일 (부품출고·작업·검사·포장·출하) | 없음 | 작업지시는 사용하지 않음(0건). 단계별 예정일 칸은 모두 작업지시에 있다 | 예정일은 생산요청의 희망 납기(due_date) 하나뿐. 지연 = 희망 납기가 지났는데 출고 전 |
| CI 선적 | 문서 상세의 document_date, shipment_date, shipping_invoice_files | CI 190건 중 선적일 128건, 운송장 첨부 57건 | 운송장은 첨부 개수만 |
| 영업 대응(프로젝트)·코멘트 이력 | /sales-activities?status=&assigned_to=&customer_id=&keyword=&limit(≤200) / /sales-activities/{id} / /{id}/logs / /{id}/documents / /sales-activities/assignees | 360건, 최근 30일 코멘트 262건·작성자 9명 (활발히 사용) | current_step·next_step·pending_reason·expected_amount는 대부분 비어 있음(24·13·3·4건) → 코멘트 이력이 핵심 정보 |
| 영업 담당자 | 거래처의 sales_rep은 비어 있음(0곳) | | 대신 영업활동 assigned_to, 문서 prepared_by(작성자명), 생산요청 prepared_by_name을 쓴다 |
| 같은 거래처·품목의 과거 견적 단가 | /sales-documents/price-history/{customer_id}?product_code= / /sales-documents/last-price/{customer_id}/{product_code} | 판매가만 반환(확인함) | 작성중·구버전 문서도 섞여 나온다 → 문서 상태·날짜를 같이 보여 준다. price_history 테이블(기준단가=원가)은 쓰지 않는다 |
| 상태 코드 라벨 | 프론트 코드에 정의 (아래) | | 응답에 코드 + 한국어 라벨을 함께 |
| X-Manager 화면 주소(url) | 프론트 라우트 | | 문서: /sales?tab={quotations|pi|ci|invoice}&open_doc_id={id} · 생산요청: /production-requests?edit_id={id} · 거래처·영업활동은 상세 링크가 없어 /sales?tab=activity&customer_id={거래처 id}로 대신 |

상태 라벨 (frontend/src/api/*.ts 기준, 구현 시 재확인):
- 영업문서 status: DRAFT 작성중, SENT 발송, CONFIRMED 확정, CANCELLED 취소
- 입금 payment_status: UNPAID 미입금, PARTIAL 부분입금, PAID 완납
- 생산요청 status (productionRequest.ts prStatusLabels): REQUESTED 요청됨, HOLD 보류, REJECTED 반려됨, APPROVED 생산부 확인, IN_PROGRESS 생산 진행중, COMPLETED 생산 완료, SHIPPED 출고 완료, DELIVERED 발송 완료, CANCELLED 취소됨
- 영업 대응 status (salesActivity.ts activityStatusLabels): IN_PROGRESS 진행중, WAITING 대기, COMPLETED 완료, ON_HOLD 보류, DROPPED 무산
- 국내 거래처(trade_type=DOMESTIC)는 화면에서 "PI발송→발송", "CI발행→명세서발행", "출하→납품"으로 부른다

1단계에서 제외(데이터가 없거나 운영하지 않음): 재고(재고가 있는 품목 7개, 예약·가용 0, 마지막 입출고 2026-09-11), 구매 발주(5건), 작업지시(0건), 거래처 배송지 목록(1건), 거래처 잔액(0건).

## 4. 도구 설계 (1단계)

이름은 동사_대상. 날짜는 ISO(YYYY-MM-DD), 금액은 숫자 + currency. 각 결과에 X-Manager 화면 url.
도구 설명(description)에는 Claude가 언제 쓰는지 알 수 있게 한국어 예시 질문을 1~2개 넣는다.

1. find_partner(query?, email_or_domain?, country?, limit?)
   — 이름·코드 부분일치, 또는 메일 주소/도메인으로 거래처 후보 찾기. 반환: 식별 정보 + 매칭 근거(name/domain/email). 메일 주소 자체는 반환하지 않는다.
2. get_partner_overview(id | code)
   — 거래처 식별 정보 + 영업 현황 요약: 진행 중 영업 대응(최근 것 몇 건), 최근 문서(유형별), 미입금 PI, 출고 전 생산요청. 연락처·주소는 없음.
3. list_sales_documents(partner?, type?, status?, payment_status?, date_from?, date_to?, query?, limit?, cursor?)
4. get_sales_document(id | number)
   — 헤더(번호, 유형, 날짜, 상태+라벨, 거래처, 고객 PO, 통화, 합계, 결제·납품 조건, 인코텀즈, CI 선적일) + 품목(오더코드, 설명, 수량, 단위, 단가, 금액)
     + 연결 문서(Q→PI→CI) + 입금 상태(CI는 원본 PI 기준) + 배송지 지정 여부.
5. get_order_status(pi_number? | customer_po? | document_number? | partner?) ← 핵심
   — 주문 하나를 PI → 생산요청(여러 건일 수 있음) → CI(여러 건일 수 있음)로 묶어:
     현재 단계, 단계별 완료 시각(3번 표의 생산요청 시각 + CI 날짜·선적일), 희망 납기와 지연 여부, 입금 상태,
     분할선적이면 품목별 주문/CI 발행/남은 수량, 출고 정보(CONSIGNEE·SHIPPING MARK) 등록 여부.
     process-status는 참고만 하고, 분할 생산·분할선적은 생산요청·연결 문서로 직접 계산한다.
   — 예: "Focon PI-FN261106 지금 어디까지 왔어?"
6. list_open_orders(partner?, sales_rep?, due_before?, limit?)
   — 아직 발송 완료(DELIVERED)가 아닌 생산요청 + 생산요청이 없는 확정 PI. 예: "다음 주 납기인 주문 뭐 있어?"
7. list_sales_activities(partner?, status?, assigned_to?, query?, limit?) / get_sales_activity(id, comments_limit?)
   — 영업 대응과 최근 코멘트 이력. 예: "Focon 건 최근 대응 내용 요약해 줘"
8. get_quoted_price_history(partner, product_code?)
   — 과거 견적·PI 단가 이력(판매가). 문서번호·날짜·상태·수량·통화 포함.

리소스(선택): 상태 코드 라벨표.

1차 구현 범위: 1, 4, 5, 7 → 그다음 2, 3, 6, 8.

## 5. 기술 선택

- Python + 공식 MCP SDK(PyPI `mcp` 패키지). 버전에 따라 고수준 서버 클래스 이름이 다르다(FastMCP / MCPServer) — 설치한 버전 문서를 따른다.
  전송은 stdio(영업메일점검 PC에서 로컬 실행).
- HTTP 클라이언트(httpx 등)로 XMANAGER_BASE_URL에 HTTPS 접속.
  - 인증: POST /api/v1/auth/login → access 토큰(60분) + refresh 토큰(7일). 만료되면 /auth/refresh, 그것도 실패하면 다시 로그인.
  - 로그인은 5회 실패하면 15분 잠긴다(IP+계정). 로그인 실패 시 자동 재시도 루프를 돌지 말고 즉시 오류를 돌려준다.
  - 응답 코드 처리: 401 → 토큰 갱신 1회 후 재시도, 403 → "권한 없음"(역할 설정 확인 안내), 5xx·연결 실패 → 짧은 오류 메시지.
- X-Manager가 계속 바뀌므로 schema_check 테스트를 꼭 둔다: 허용 목록 API를 실제로 호출해서
  (1) MCP가 쓰는 응답 필드가 모두 있는지, (2) 금지 필드가 MCP 응답에 새어 나오지 않는지 확인한다.
  X-Manager 업데이트 후 이 테스트만 돌리면 MCP가 깨졌는지 알 수 있어야 한다.
- 검증 대상: 조회 전용이므로 운영 주소로 바로 검증해도 된다(개발 DB는 운영 데이터가 다 들어 있지 않음).

## 6. 영업메일점검과의 연결 (설계만, 구현은 2단계)

- 업체 매핑표: 메일 도메인 ↔ X-Manager 거래처. find_partner(email_or_domain=...)로 후보를 찾고 사람이 확정한다.
- 체크리스트 보강: 문서 발행·입금 상태, 생산 진행(희망 납기·출고·발송), 분할선적 남은 수량을 MCP 결과로 보여 준다.
- AI 분석 보강: 메일에 "PI 보냈다/입금했다/출고했다"가 나오면 X-Manager 문서·입금·생산 상태와 대조해 할 일을 판단한다.
- 이 연결은 조회만 한다. 메일 분석 결과를 X-Manager에 쓰지 않는다.

## 7. 산출물

1. 설계 문서: 3번 조사표(최신 main 재확인 결과), 도구 목록(인자·반환 예시 JSON), API 허용 목록, 필드 허용 목록, 코드 라벨 매핑, 권한 모델, 2단계 확장안
2. 코드: MCP 서버 저장소 (server, tools, xmanager_client(허용 목록·인증), shaping(필드 허용 목록), labels, config, README)
3. 조회 계정 점검 방법 안내 (계정은 이미 있음: mcp_reader. /auth/me로 권한 4개 확인, 비밀번호 변경은 X-Manager 관리자 화면의 비밀번호 초기화)
4. 테스트
   - 각 도구 정상 조회, 없는 값, 빈 결과, limit·페이지 처리
   - 쓰기 시도가 거부되는지: 조회 계정으로 본문 없이 POST /api/v1/partners → 403이어야 한다
     (권한이 잘못 설정돼 있으면 422가 나오는데, 이 경우도 본문 검증 실패라 아무것도 만들어지지 않는다)
   - 허용 목록 밖 경로·메서드가 클라이언트에서 거부되는지
   - 민감 필드가 어떤 응답에도 없는지 (응답 전체를 금지 필드·이메일 패턴으로 검사)
   - schema_check
5. Claude Desktop / Claude Code 연결 설정 예시 (비밀번호 없이, 환경변수 이름만)

## 8. 결정 사항

확정:
1. 접속 방식: 영업메일점검 PC에서 HTTPS로 X-Manager REST API 조회. DB 직접 접속 금지.
2. 고객사 상세 정보는 넘기지 않는다. 영업 진행 현황만.
3. 원가·마진·은행 정보: 1단계 비공개.
4. 계정: 공용 조회 계정 1개(mcp_reader). 1단계는 관리자 혼자 사용. 다른 직원이 쓰게 되면 그때 사람별 계정으로 바꿀지 다시 정한다.

메일·메시지를 보내거나 X-Manager 데이터를 바꾸는 작업은 어떤 경우에도 하지 않는다.
```
