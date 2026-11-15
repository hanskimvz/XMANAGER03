# X-Manager 리눅스 이전 검토서

**작성일**: 2026-11-12
**대상**: X-Manager 운영 환경을 Ubuntu 24.04 전용 서버로 이전하는 작업의 사전 검토
**범위**: 현재 환경 실측, 발견된 문제점, 이전 공수 추정, Nextcloud 의존성 분석, 결정 사항

---

## 1. 요약

- 현재 X-Manager는 Windows 11 PC 한 대에서 **백엔드(venv/uvicorn, 네이티브) + 웹서버(Docker Caddy) + DB(PostgreSQL 18, 네이티브)** 로 운영 중이다. Nextcloud, OnlyOffice도 같은 PC의 Docker(WSL2)에서 돈다.
- 계획은 **X-Manager만 먼저** 별도 Ubuntu 24.04 전용 서버(VM 아님)로 옮기고, Docker 없이 **nginx + FastAPI(uvicorn, systemd) + PostgreSQL** 로 운영하는 것이다. Nextcloud는 당분간 현재 PC에 남긴다.
- 코드의 OS 의존은 두 곳뿐이라 이전 자체는 가볍다. 핵심 쟁점은 **X-Manager가 Nextcloud 동기화 폴더에 직접 파일을 쓰는 구조**이며, 서버가 분리되면 이 연결이 끊긴다. 이전 전에 연결 방식을 정해야 한다.
- 추정 공수: X-Manager 단독 이전 **6~10 인일**. MongoDB 전환은 **40~70 인일**로 별도 프로젝트이며 비권장.

---

## 2. 현재 환경 (2026-11-12 실측)

### 2.1 하드웨어 / OS

| 항목 | 값 |
|---|---|
| OS | Windows 11 Pro 10.0.26200 |
| 보드 / CPU | ASRock Z890 Nova WiFi, 논리 20코어 |
| 메모리 | 64 GB |
| 디스크 | C: 1.8 TB (여유 898 GB), E: 1.8 TB "server" (여유 285 GB) |
| 공인 도메인 | xmanager.xbeamtech.co.kr → 175.113.135.21 |

### 2.2 구성요소별 실행 방식

| 구성요소 | 실행 방식 | 런타임 | 포트 | 자동시작 |
|---|---|---|---|---|
| 백엔드 (FastAPI 0.110, SQLAlchemy 2.0.27, Alembic 1.13.1) | `backend\.venv` 의 uvicorn 0.27.1. `run-backend-prod.bat` 감시루프를 `start-backend-hidden.vbs` 로 숨김 실행 | Windows 네이티브, Python 3.12.0 | 8000 (0.0.0.0) | 작업 스케줄러 `X-Manager-AutoStart`(로그온), `X-Manager-Watchdog`(15분마다) |
| 웹서버 / 리버스프록시 (Caddy 2) | Docker 컨테이너 `caddy_proxy`. compose: `E:\DockerServices\caddy-proxy` | Docker Desktop → WSL2 (linux/amd64, engine 28.1.1) | 80 / 443 | restart=always, Docker Desktop 자동시작 |
| 프론트엔드 (Vue 3.5, Vite 7, TypeScript 5.9) | `frontend\dist` 정적 빌드를 Caddy 컨테이너에 바인드마운트. `/api/*` 는 `host.docker.internal:8000` 으로 프록시 | 빌드는 Windows Node v24.14.1 | (Caddy가 서빙) | 빌드 파일 교체만 |
| DB (PostgreSQL 18.3) | Windows 서비스 `postgresql-x64-18`, 데이터 `C:\Program Files\PostgreSQL\18\data` | Windows 네이티브 (msvc 빌드) | 5432 (listen_addresses=*) | 서비스 Automatic |
| 개발 환경 | `start-dev.bat`: 같은 .venv 로 :8001 + Vite :5174, DB `xmanager_dev` | 동일 PC | 8001 / 5174 | 수동 |
| Nextcloud 31.0.4 + MariaDB + Redis + OnlyOffice | Docker 컨테이너 7개. compose: `E:\DockerServices\nextcloud`, `onlyoffice` | WSL2 | 80(내부), 3306, 8080, 9080/9443 | restart=always |

- DB: `xmanager`(운영, 55 MB), `xmanager_dev`(21 MB). 역할 `xmanager`(운영/개발 공유), `ro_migrate`(외부 접속 허용, scram). 두 DB 모두 alembic 버전 `xm_v1000_disb_cols`.
- `docker/docker-compose.yml` 의 PostgreSQL 16 컨테이너는 **미사용**(다른 PC용 로컬 테스트 DB 세팅 스크립트).
- 부가 작업: 매시간 `scripts/backup-db.bat` (pg_dump → `storage\backups`), 매일 04:00 `run-auto-hold.bat`(영업건 자동보류).
- PDF: WeasyPrint 65.1 이 MSYS2 UCRT64 GTK 런타임(`C:\msys64\ucrt64\bin`)에 의존.
- 자원 점유: WSL VM(vmmemWSL) 5.5 GB, Docker Desktop 약 1 GB, PostgreSQL 0.5 GB. Docker 이미지 70 GB 중 62 GB 회수 가능.

### 2.3 코드 규모

| 항목 | 수 |
|---|---|
| 백엔드 Python 파일 (`app/`) | 167 (약 4.8만 줄) |
| API 라우터 모듈 | 35 |
| SQLAlchemy 모델 | 35 (relationship 125개) |
| Alembic 리비전 | 125 |
| 프론트 .vue/.ts 파일 | 181 (약 6.6만 줄) |
| 커밋 (2026-06-22 이관 이후) | 249 |

### 2.4 문서와 실제의 불일치

README, `docs/CLAUDE.md`, `docs/서버_설치_가이드.md`, `docs/배포_및_운영_가이드.md` 의 기술 스택 표기(Nginx, PostgreSQL 15/17, 네이티브 Caddy `C:\Caddy`, venv 폴더명 `venv`, 프론트 :5173)는 현재 구성(Docker Caddy, PG 18, `.venv`, 정적 dist 서빙)과 다르다. 이전 후 문서를 새 구성 기준으로 갱신해야 한다.

---

## 3. 검토에서 발견된 문제점

| # | 문제 | 영향 | 비고 |
|---|---|---|---|
| 1 | alembic head `xm_v1010_appr_min` 이 운영·개발 DB 모두 미적용 | 결재 시각 컬럼의 DB 기본값만 바꾸는 리비전이라 앱은 동작 | 적용 여부 결정 후 `alembic upgrade head` 직접 실행 |
| 2 | `backend-prod.log` 265 MB, 회전 없음 | 디스크 증가 | 리눅스 이전 시 logrotate 로 해결 |
| 3 | PostgreSQL `listen_addresses=*` + `ro_migrate` 역할 0.0.0.0/0 허용 | 방화벽 "PostgreSQL 5432 (LAN only)" 규칙에만 의존 | 보안 잔여 항목 |
| 4 | 80/443/8000 포트 규칙 없음. Docker·python.exe **프로그램 규칙(Public 프로필)** 에 의존 | 네트워크 프로필 변경·Docker 재설치 시 외부 접속 단절 위험 | 2026-06 장애와 같은 유형 |
| 5 | Caddyfile 한글 주석 인코딩 깨짐, `scripts/sync-db-to-dev.bat` PG 17 경로 | 실행 시 실패 | |
| 6 | 백업이 운영 데이터와 같은 PC·같은 디스크에만 존재 | 디스크 장애 시 동반 유실 | |
| 7 | **Nextcloud 데스크톱 클라이언트가 2026-11-11 20:31 재부팅 후 미실행** | 이후 X-Manager 가 쓴 파일 14개 미동기화 | 클라이언트 재실행 시 자동 복구. 단일 장애점 확인 |

---

## 4. 목표 구성

```
[사용자 브라우저]
      │ HTTPS 443
      ▼
[Ubuntu 24.04 전용 서버]
  nginx ──── /            → /var/www/xmanager/dist (정적)
        └─── /api/*, /health → unix:/run/xmanager.sock
                                  │
                           uvicorn (FastAPI)  ← systemd xmanager.service (Restart=always)
                                  │
                           PostgreSQL 18 (localhost)
                                  │
                           /srv/xmanager/storage (업로드·PDF·백업)
                                  │
                           Nextcloud 연동 경로 2개 ← 5장 참조
```

- Docker 미사용. 모든 프로세스는 systemd 유닛.
- 백엔드는 FastAPI 그대로. nginx 가 유닉스 소켓으로 uvicorn 에 리버스 프록시(현재 Caddy → host.docker.internal:8000 과 같은 구조).
- 백업·자동보류는 systemd timer. 감시루프(bat/vbs)와 Watchdog 작업은 systemd `Restart=always` 로 대체되어 폐기.

### 4.1 Ubuntu 24.04 와의 궁합

| 항목 | 24.04 기본 | 대응 |
|---|---|---|
| Python | 3.12 | 현재 venv 와 동일. `requirements.txt` 그대로 설치 |
| PostgreSQL | 16 | 18 로 맞추려면 PGDG apt 저장소 추가 (덤프 복원은 16 도 가능) |
| Node | 18 | Vite 7 에 부족. NodeSource 22+ 설치, 또는 Windows 에서 빌드 후 dist 만 전송 |
| nginx | 1.24 | 기본 저장소 |
| certbot | snap/apt | Caddy 자동 TLS 대체 |
| WeasyPrint 의존 | libpango, libcairo, libgdk-pixbuf | 기본 저장소. MSYS2 때문에 고정한 65.1 제약 해제 가능 |
| PHP | 8.3 | (향후 Nextcloud 네이티브 이전 시) Nextcloud 31 호환 |

### 4.2 코드 수정 지점

| 파일 | 내용 |
|---|---|
| `backend/app/services/pdf_service.py:37` | `C:/Windows/Fonts/malgun.ttf` 하드코딩 → 리눅스 폰트 경로(Noto CJK 또는 맑은고딕 복사) |
| `backend/app/api/v1/admin.py:127` | `subprocess.run` 호출 내용 확인 후 리눅스 명령으로 조정 |
| `backend/.env.production` | DATABASE_URL, STORAGE_PATH, NEXTCLOUD_BASE_PATH, NEXTCLOUD_DELIVERY_PATH 를 리눅스 경로로 |
| `backend/app/core/config.py:14` | `PGCLIENTENCODING` 강제는 리눅스에서 무해. 유지 가능 |

그 외 백슬래시 처리 코드는 이미 양쪽 OS 를 고려해 작성되어 있다. 프론트엔드는 코드 변경 없음(`client.ts` 가 운영에서는 같은 origin 의 `/api/v1` 사용).

### 4.3 주의 사항

- **대소문자**: Windows 는 파일명 대소문자를 구분하지 않지만 리눅스는 구분한다. DB 에 저장된 파일명과 디스크 실제 파일명이 대소문자만 다른 경우를 이전 전 검사해야 한다(storage 28.9 GB, backend/uploads).
- **한글 파일명**: 양쪽 모두 UTF-8 이라 문제 없음. 단 NFC/NFD 정규화 차이가 있을 수 있어 복사 후 샘플 검증.
- **현재 PC는 전환이 끝날 때까지 그대로 운영**. 롤백은 DNS A 레코드를 되돌리는 것으로 끝난다.

---

## 5. Nextcloud 의존성 분석

### 5.1 결론

X-Manager 백엔드는 Nextcloud 서버와 **직접 통신하지 않는다**(HTTP, WebDAV, occ 호출 없음). 의존은 **이 PC 의 Nextcloud 동기화 폴더 두 곳에 파일을 읽고 쓰는 것** 이 전부이며, 서버로 올리는 역할은 Windows Nextcloud 데스크톱 클라이언트가 맡는다. X-Manager 를 다른 서버로 옮기면 이 연결이 끊어진다.

### 5.2 의존 경로와 사용 기능

| 설정 | 현재 경로 | 사용 기능 | 규모 |
|---|---|---|---|
| `NEXTCLOUD_BASE_PATH` | `C:\Users\xbeam\Nextcloud\GBT` | 영업 파일허브(거래처·주문 폴더 탐색·미리보기·업로드·삭제), 견적/PI/CI PDF 자동 저장, 영업대응건 폴더 생성 | 78 GB, 33,090 파일 |
| `NEXTCLOUD_DELIVERY_PATH` | `C:\Users\xbeam\Nextcloud\XBT_공용\생산_영업_관리파일` | 생산요청 포장사진, 계측파일, 도면 첨부 → `{연도} 납품 리스트/{번호_기업명}` | 14 GB, 4,430 파일 |

### 5.3 코드 위치

| 파일 | 역할 |
|---|---|
| `backend/app/services/nextcloud_service.py` | 약 400줄. 순수 파일시스템 함수(경로 조립, makedirs, open, listdir). 외부 라이브러리 없음 |
| `backend/app/api/v1/cloud_files.py` | 파일허브 라우터. 엔드포인트 9개: entry, link, unlink, list, preview, download, upload, mkdir, delete |
| `backend/app/api/v1/sales_document.py:423-442` | 견적/PI/CI PDF 생성 시 주문 폴더 `02_영업문서` 에 자동 저장 (best-effort) |
| `backend/app/api/v1/production_request.py:1163-1623` | 도면 첨부, 포장사진, 계측파일 저장·목록·다운로드·삭제 |
| `backend/app/api/v1/sales_activity.py:370-404` | 영업대응건 Nextcloud 폴더 생성 |

프론트엔드: `api/cloudFiles.ts`, `components/CloudFileBrowser.vue`, `sales/OrderFilesModal.vue`, `production/PackingPhotos.vue`, `production/MeasurementFiles.vue`, `sales-activity/SalesActivityDetailModal.vue`. 모두 백엔드 API 만 호출하며 Nextcloud 주소를 직접 쓰지 않는다.

### 5.4 DB 저장 형태

| 테이블.컬럼 | 저장 건수 / 전체 |
|---|---|
| `business_partner.nextcloud_folder` | 1 / 143 |
| `sales_activity.nextcloud_folder` | 187 / 362 |
| `sales_document.nextcloud_folder` | 359 / 943 |
| `production_request.packing_folder` | 96 / 96 |

모두 **베이스 기준 상대경로** 다. 베이스 경로(.env)만 바꾸면 되고 DB 수정은 필요 없다.

### 5.5 동기화 주체 (현재 PC)

- Nextcloud 데스크톱 클라이언트 33.0.5. 계정 **yhsung**, 로컬 `C:\Users\xbeam\Nextcloud\` ↔ 서버 `/` 전체 동기화.
- `GBT` 폴더는 서버 사용자 **cp** 의 `1GBT` 를 공유받은 것. 서버 데이터 실제 위치: `E:\NextcloudData\cp\files\1GBT\...`
- 2026-11-11 X-Manager 가 저장한 CI PDF 가 위 위치에 존재함을 확인(동기화 정상 작동 확인).
- 단, 2026-11-11 20:31 재부팅 이후 클라이언트가 실행되지 않아 14개 파일이 미동기화 상태(3장 7번).

### 5.6 미설정 시 동작

- `NEXTCLOUD_BASE_PATH` 비어 있음 → 파일허브 API 503, 영업대응건 폴더 생성 503, PDF 자동 저장은 조용히 건너뜀.
- `NEXTCLOUD_DELIVERY_PATH` 비어 있음 → 포장사진·계측파일 화면 "연동 비활성" 표시, 도면 첨부의 납품 폴더 복사는 건너뜀.

### 5.7 X-Manager 단독 이전 시 선택지

| 안 | 방법 | 코드 변경 | 장점 | 단점 |
|---|---|---|---|---|
| A | 새 서버에도 Nextcloud 동기화 클라이언트(`nextcloudcmd` 또는 headless 데스크톱 클라이언트) 설치 | 없음 | 현재 구조 그대로 | 92 GB 복제본이 서버마다 생김. 클라이언트 중단 = 단일 장애점 유지 |
| B | **WebDAV 마운트 (davfs2 또는 rclone mount)** 로 두 경로를 xcloud 서버에 직접 마운트 | 없음 | 복제본 없음, 설정만으로 완료, 롤백 쉬움 | 폴더 목록·미리보기가 네트워크 왕복. 대용량 업로드 타임아웃 조정 필요. 두 서버가 같은 LAN 이어야 체감 속도 확보 |
| C | `nextcloud_service.py` 를 WebDAV API 호출로 재작성 | 약 400줄 + 호출부 4개 모듈 | 가장 견고. Nextcloud 위치와 무관 | 1~3 인일 |

**권장: B 로 시작**. 향후 Nextcloud 도 리눅스 네이티브로 옮기면 X-Manager 서버의 폴더를 Nextcloud **외부저장소(local 또는 SFTP)** 로 붙이는 것이 동기화 클라이언트 없는 최종형이다.

---

## 6. 공수 추정

### 6.1 1단계: X-Manager 단독 이전 (Ubuntu 24.04 전용 서버)

| 작업 | 인일 | 비고 |
|---|---|---|
| 리눅스 기본 설치, nginx, PostgreSQL 18(PGDG), certbot, ufw | 1~2 | |
| 백엔드 systemd 유닛, 유닉스 소켓, .env, 폰트·admin.py 수정 | 1~2 | |
| 프론트 빌드(Node 22+) 및 nginx 정적 서빙 | 0.5 | |
| 데이터 이전: pg_dump/restore(55 MB), storage 28.9 GB rsync, 대소문자·NFC 검증 | 1~2 | |
| Nextcloud 연동 경로 마운트 (B안) | 0.5~1 | C안 선택 시 +1~3 |
| 백업 timer, 자동보류 timer, logrotate | 0.5~1 | |
| 통합 테스트, 전환(DNS), 롤백 계획 | 1~2 | |
| **합계** | **6~10 인일** | 1인 기준 달력 2주 내외 |

Nextcloud·OnlyOffice·기타 vhost(forti, nas) 는 현재 PC 에 남으므로 이번 범위에서 제외. Caddy 는 그대로 두고 xmanager 블록만 제거하면 된다.

### 6.2 (참고) 향후 Nextcloud 네이티브 이전

| 작업 | 인일 |
|---|---|
| Nextcloud 네이티브(PHP-FPM 8.3, Redis, DB), 데이터 223 GB 이전, 외부저장소 연결 | 3~5 |
| OnlyOffice 네이티브 (.deb 가 자체 PostgreSQL·RabbitMQ 요구) | 1~2 |
| 나머지 vhost, Caddy 완전 제거, Docker Desktop 제거 | 0.5~1 |

### 6.3 2단계: PostgreSQL → MongoDB (비권장)

| 영향 범위 | 수 |
|---|---|
| SQLAlchemy 모델 / relationship | 35 / 125 |
| ORM 쿼리 호출 지점 | 664 |
| join·집계·JSONB 사용 | 289 |
| Alembic 마이그레이션 (폐기 대상) | 125 |
| 서비스 계층 코드 | 약 1만 8천 줄 |

추정 **40~70 인일**. 전자결재 승인선, 재고 FIFO 로트, BOM 재귀 트리, 지출결의 선행문서 연결이 트랜잭션·외래키 무결성에 의존하며, 이 시스템은 관계형 ERP/PLM 워크로드라 전환 이득이 없다. 유연 필드는 이미 PostgreSQL JSONB 로 처리 중이다. 전환을 원하는 구체적 이유가 있다면 그 이유에 맞는 다른 방법을 먼저 검토할 것을 권한다.

---

## 7. 결정 사항

| 항목 | 상태 | 내용 |
|---|---|---|
| 서버 | **결정** | 별도 전용 리눅스 서버, VM 아님, Ubuntu 24.04 네이티브 |
| 웹서버 / 백엔드 | **결정** | nginx + FastAPI(uvicorn, systemd). Docker 미사용 |
| DB | **결정** | PostgreSQL 유지 (MongoDB 는 후순위, 비권장 전달) |
| 이전 범위 | **결정** | X-Manager 만 먼저. Nextcloud·OnlyOffice 는 현재 PC 에 잔류 |
| Nextcloud 연동 방식 | 미결 | 5.7 의 A/B/C 중 선택. 권장 B |
| 새 서버 사양·네트워크 | 미결 | CPU, RAM, 디스크 구성, 현재 PC 와 같은 LAN 인지 |

---

## 8. 다음 단계

1. 현재 PC 에서 Nextcloud 데스크톱 클라이언트 재실행 → 미동기화 14개 파일 반영 확인.
2. Nextcloud 연동 방식(A/B/C) 결정, 새 서버 사양·네트워크 확정.
3. 단계별 이전 계획서 작성: 설치 순서, systemd·nginx 설정 파일, 데이터 이전 절차, 전환일 체크리스트, 롤백 절차.
4. 이전 후 문서 갱신: README, `docs/CLAUDE.md`, `docs/서버_설치_가이드.md`, `docs/배포_및_운영_가이드.md`.

---

## 부록: 현재 운영 스크립트와 리눅스 대응

| 현재 (Windows) | 리눅스 대응 |
|---|---|
| `start-prod.bat`, `start-backend-hidden.vbs`, `run-backend-prod.bat` (감시루프) | `xmanager.service` (systemd, Restart=always) |
| `stop-backend.bat` | `systemctl stop xmanager` |
| 작업 스케줄러 `X-Manager-Watchdog` (15분) | 불필요 (systemd 가 대체) |
| `run-auto-hold.bat` + 작업 스케줄러 (매일 04:00) | `xmanager-auto-hold.timer` |
| `scripts/backup-db.bat` (매시간), `cleanup-backups.bat` | `xmanager-backup.timer` + 보관 정책 스크립트 |
| `scripts/sync-db-to-dev.bat` | 쉘 스크립트 (dev DB 는 새 서버 또는 개발 PC 에 유지) |
| `view-logs.bat` | `journalctl -u xmanager -f` |
| Caddy `xmanager.xbeamtech.co.kr` 블록 | nginx server 블록 + certbot |
