# X-Manager ↔ Nextcloud 파일 시스템 연동 설계

> 작성일: 2026-04-22
> 상태: 설계 완료, 구현 대기

## 1. 목적

영업팀이 X-Manager에서 문서(Q/PI/CI) 업로드 시, Nextcloud 동기화 폴더에 자동 저장되어
모든 사원이 기존 파일 탐색기 방식으로 파일에 접근할 수 있도록 한다.

## 2. 현재 환경

- **Nextcloud 서버**: xcloud.xbeamtech.co.kr
- **사용자 계정**: 사원 개인별 Nextcloud 계정 보유
- **로컬 동기화**: 각 사원 PC에 Nextcloud 데스크톱 클라이언트 설치, 로컬 폴더 동기화
- **기존 폴더 구조**: `C:\Users\{사용자}\Nextcloud\GBT\수출\{년도}\{국가}_{거래처명}_{거래처코드}\{문의건}`

## 3. 구현 방식

### 핵심 아이디어
X-Manager **운영 서버**에 Nextcloud 동기화 폴더를 마운트하고, 파일 저장 경로를 해당 폴더로 지정.
서버에서 파일 저장 → Nextcloud 자동 동기화 → 모든 사원 PC에 반영.

### 아키텍처
```
사용자 브라우저
  ↓ 파일 업로드
X-Manager 서버
  ↓ 파일 저장
Nextcloud 동기화 폴더 (서버 로컬)
  예: E:\Nextcloud\GBT\수출\2026\인도_HTL Limited_HT\0416 커넥터\PI-HT260416.xlsx
  ↓ Nextcloud 자동 동기화
xcloud.xbeamtech.co.kr (Nextcloud 서버)
  ↓ 동기화
각 사원 PC 로컬 폴더
  C:\Users\{사용자}\Nextcloud\GBT\수출\2026\...
```

## 4. 폴더 경로 규칙

### 자동 생성 경로
```
{NEXTCLOUD_BASE}/GBT/수출/{년도}/{국가}_{거래처명}_{거래처코드}/{문의건폴더명}/
```

### 경로 구성 요소
| 구간 | 데이터 소스 | 예시 |
|------|-----------|------|
| 년도 | 문서 날짜 (document_date.year) | 2026 |
| 국가 | business_partner.country_name | 인도 |
| 거래처명 | business_partner.partner_name | HTL Limited |
| 거래처코드 | business_partner.partner_code | HT |
| 문의건 | 엑셀 "소속 폴더" 또는 영업활동 제목 | 0416 커넥터 140개 |

### 결정 필요 사항
- **문의건 폴더명**: 자동 생성 규칙 확정 필요
  - 옵션 A: 문서번호 기반 (`PI-HT260416`)
  - 옵션 B: 영업활동 제목 기반
  - 옵션 C: 데이터 추출 엑셀의 "소속 폴더" 활용 (기존 폴더 구조 유지)
  - 옵션 D: 사용자가 폴더명 직접 지정

## 5. 구현 범위

### Phase 1: 기본 연동
- [ ] 운영 서버에 Nextcloud 클라이언트 설치 또는 WebDAV 마운트
- [ ] 환경 변수에 Nextcloud 베이스 경로 설정 (`NEXTCLOUD_BASE_PATH`)
- [ ] 파일 업로드 시 자동 경로 생성 + 파일 저장
- [ ] 폴더 없으면 자동 생성 (`os.makedirs`)

### Phase 2: UI 연동
- [ ] 문서 상세 모달에 "관련 파일" 섹션 추가
- [ ] 해당 폴더의 파일 목록 표시 (서버에서 `os.listdir`)
- [ ] 파일 다운로드/미리보기 링크
- [ ] 파일 업로드 버튼 (문서 상세에서 직접 업로드)

### Phase 3: 거래처/영업활동 연동
- [ ] 거래처 상세에서 해당 거래처의 모든 파일 탐색
- [ ] 영업활동 상세에서 관련 파일 표시
- [ ] 생산요청서 첨부파일도 동일 경로에 저장

## 6. 서버 사전 준비

### 운영 서버 (Windows)
```powershell
# Nextcloud 데스크톱 클라이언트 설치
# 또는 WebDAV를 네트워크 드라이브로 마운트:
net use N: "https://xcloud.xbeamtech.co.kr/remote.php/dav/files/공용계정/" /user:공용계정 비밀번호 /persistent:yes
```

### 환경 변수 (.env.production)
```
NEXTCLOUD_BASE_PATH=E:\Nextcloud\GBT\수출
# 또는 네트워크 드라이브
NEXTCLOUD_BASE_PATH=N:\GBT\수출
```

## 7. 영향받는 기존 코드

| 파일 | 변경 내용 |
|------|----------|
| backend/app/services/sales_excel_service.py | 엑셀 생성 후 Nextcloud 폴더에도 저장 |
| backend/app/api/v1/files.py | 파일 저장 경로를 Nextcloud 폴더로 변경 |
| backend/app/api/v1/sales_document.py | 문서별 파일 경로 매핑 |
| backend/app/api/v1/production_request.py | 생산요청 첨부파일 경로 변경 |
| frontend/src/components/sales/SalesDocumentFormModal.vue | 관련 파일 섹션 UI 추가 |

## 8. 리스크 및 주의사항

- **동기화 충돌**: 서버와 사용자 PC에서 동시에 같은 파일 수정 시 충돌 가능 → Nextcloud 충돌 해결에 위임
- **서버 디스크**: 모든 파일이 서버에도 저장되므로 스토리지 확인 필요
- **권한**: 공용 계정 사용 시 모든 파일 접근 가능 → 부서별 권한 분리 불가
- **Nextcloud 장애**: Nextcloud 서버 다운 시 동기화 지연 → X-Manager 자체 파일 저장은 영향 없음
- **폴더명 특수문자**: 거래처명에 특수문자 포함 시 OS 호환 문제 → 폴더명 sanitize 필요
