# X-Manager 환경 설정 가이드

**작성일**: 2026-01-08
**버전**: 0.1.0
**대상**: 신규 개발자, 새로운 환경 구축

---

## 📋 목차

1. [사전 요구사항](#사전-요구사항)
2. [백엔드 환경 설정](#백엔드-환경-설정)
3. [프론트엔드 환경 설정](#프론트엔드-환경-설정)
4. [데이터베이스 설정](#데이터베이스-설정)
5. [IDE 설정](#ide-설정)
6. [실행 및 테스트](#실행-및-테스트)
7. [문제 해결](#문제-해결)

---

## 사전 요구사항

### 필수 소프트웨어

#### 1. Python 3.12.10
```bash
# 버전 확인
python --version

# 출력: Python 3.12.10
```

**설치**:
- [Python 공식 사이트](https://www.python.org/downloads/)에서 다운로드
- "Add Python to PATH" 체크 필수

#### 2. Node.js 24.12.0 & npm 11.6.2
```bash
# 버전 확인
node --version   # v24.12.0
npm --version    # 11.6.2
```

**설치**:
- [Node.js 공식 사이트](https://nodejs.org/)에서 LTS 버전 다운로드

#### 3. PostgreSQL 17.7
```bash
# 버전 확인
psql --version

# 출력: psql (PostgreSQL) 17.7
```

**설치**:
- [PostgreSQL 공식 사이트](https://www.postgresql.org/download/)에서 다운로드
- 설치 시 포트: 5432 (기본값)
- 설치 시 슈퍼유저 비밀번호 설정 필요

#### 4. Git
```bash
# 버전 확인
git --version
```

**설치**:
- [Git 공식 사이트](https://git-scm.com/downloads)에서 다운로드

### 권장 도구

- **IDE**: Visual Studio Code
- **DB 클라이언트**: DBeaver, pgAdmin, TablePlus
- **API 테스트**: Postman, Thunder Client (VS Code Extension)

---

## 백엔드 환경 설정

### 1. 프로젝트 클론 (또는 다운로드)

```bash
# Git 클론 (저장소가 있는 경우)
git clone <repository-url>
cd X-MANAGER_R0.1

# 또는 ZIP 파일 다운로드 후 압축 해제
```

### 2. Python 가상환경 생성

```bash
cd backend

# Windows
python -m venv venv

# Linux/Mac
python3 -m venv venv
```

### 3. 가상환경 활성화

```bash
# Windows (PowerShell)
.\venv\Scripts\activate

# Windows (CMD)
venv\Scripts\activate.bat

# Linux/Mac
source venv/bin/activate
```

**PowerShell 실행 정책 오류 시**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. 패키지 설치

```bash
pip install -r requirements.txt
```

**설치되는 주요 패키지**:
- FastAPI 0.110.0
- SQLAlchemy 2.0.27
- Pydantic 2.6.1
- Alembic 1.13.1
- psycopg2-binary 2.9.9
- uvicorn 0.27.1
- python-dotenv 1.0.1
- python-multipart 0.0.9

### 5. 환경변수 설정

```bash
# .env.example을 .env로 복사
cp .env.example .env

# 또는 Windows
copy .env.example .env
```

**.env 파일 수정**:
```ini
# 데이터베이스 연결 정보
DATABASE_URL=postgresql://postgres:xmanager1014@localhost:5432/xmanager

# JWT 설정 (나중에 사용)
SECRET_KEY=xmanager-secret-key-please-change-in-production-2026
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 환경
ENVIRONMENT=development
DEBUG=True

# CORS (프론트엔드 URL)
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

**중요**:
- `DATABASE_URL`의 비밀번호를 PostgreSQL 설치 시 설정한 비밀번호로 변경
- `SECRET_KEY`는 운영 환경에서 반드시 변경 필요

### 6. 데이터베이스 마이그레이션

```bash
# 마이그레이션 적용
.\venv\Scripts\alembic upgrade head

# 성공 시 출력:
# INFO  [alembic.runtime.migration] Running upgrade  -> 2d08f8b18929, Create code master tables
# INFO  [alembic.runtime.migration] Running upgrade 2d08f8b18929 -> 9d7270623377, Add supplier and parts tables
```

### 7. 초기 데이터 입력

```bash
# PostgreSQL에 접속하여 초기 데이터 입력
psql -U postgres -d xmanager -f seeds/01_initial_codes.sql

# 성공 시 출력:
# INSERT 0 6
# INSERT 0 5
# ...
```

**또는 수동 입력**:
```bash
# psql 접속
psql -U postgres

# 데이터베이스 선택
\c xmanager

# SQL 파일 실행
\i 'h:/Xcloud/2_Xmanager/X-MANAGER_R0.1/backend/seeds/01_initial_codes.sql'

# 종료
\q
```

---

## 프론트엔드 환경 설정

### 1. 디렉토리 이동

```bash
cd ../frontend
```

### 2. 패키지 설치

```bash
npm install
```

**설치되는 주요 패키지**:
- vue: ^3.4.0
- vue-router: ^4.0.0
- pinia: ^2.1.0
- axios: ^1.6.5
- tailwindcss: ^3.4.0
- typescript: ~5.3.0
- vite: ^7.3.1

### 3. 환경변수 설정

```bash
# frontend/.env 파일 생성
echo VITE_API_URL=http://localhost:8000/api/v1 > .env

# 또는 수동으로 생성
```

**frontend/.env**:
```ini
VITE_API_URL=http://localhost:8000/api/v1
```

---

## 데이터베이스 설정

### 1. PostgreSQL 데이터베이스 생성

```bash
# psql 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE xmanager;

# 데이터베이스 목록 확인
\l

# 연결 테스트
\c xmanager

# 종료
\q
```

### 2. 데이터베이스 구조 확인

```bash
# psql로 xmanager DB 접속
psql -U postgres -d xmanager

# 테이블 목록 확인
\dt

# 출력 예시:
#                 List of relations
#  Schema |        Name        | Type  |  Owner
# --------+--------------------+-------+----------
#  public | alembic_version    | table | postgres
#  public | item_code          | table | postgres
#  public | level              | table | postgres
#  public | major_category     | table | postgres
#  public | material           | table | postgres
#  public | middle_category    | table | postgres
#  public | minor_category     | table | postgres
#  public | parts              | table | postgres
#  public | procurement_type   | table | postgres
#  public | sub_category       | table | postgres
#  public | supplier           | table | postgres
#  public | treatment          | table | postgres
#  public | unit               | table | postgres

# 특정 테이블 구조 확인
\d major_category

# 데이터 확인
SELECT * FROM major_category;
```

### 3. 데이터베이스 백업/복원 (선택사항)

**백업**:
```bash
pg_dump -U postgres -d xmanager > xmanager_backup.sql
```

**복원**:
```bash
psql -U postgres -d xmanager < xmanager_backup.sql
```

---

## IDE 설정

### Visual Studio Code 권장 확장

#### 백엔드 (Python)
1. **Python** (Microsoft)
   - Python 언어 지원

2. **Pylance** (Microsoft)
   - Python 언어 서버

3. **Python Debugger** (Microsoft)
   - 디버깅 지원

4. **autoDocstring** (Nils Werner)
   - 독스트링 자동 생성

#### 프론트엔드 (Vue/TypeScript)
1. **Vue - Official** (Vue)
   - Vue 3 언어 지원, TypeScript 통합

2. **TypeScript Vue Plugin (Volar)** (Vue)
   - Vue에서 TypeScript 지원 향상

3. **Tailwind CSS IntelliSense** (Tailwind Labs)
   - Tailwind 클래스 자동완성

#### 데이터베이스
1. **PostgreSQL** (Chris Kolkman)
   - PostgreSQL 구문 강조

2. **SQLTools** (Matheus Teixeira)
   - 데이터베이스 관리

#### 일반
1. **Thunder Client** (Thunder Client)
   - API 테스트 (Postman 대체)

2. **GitLens** (GitKraken)
   - Git 향상 도구

3. **Prettier - Code formatter** (Prettier)
   - 코드 포매팅

4. **ESLint** (Microsoft)
   - JavaScript/TypeScript 린팅

### VS Code 설정 (settings.json)

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true
  },
  "[vue]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "files.associations": {
    "*.css": "tailwindcss"
  },
  "tailwindCSS.experimental.classRegex": [
    ["class:\\s*?[\"'`]([^\"'`]*).*?[\"'`]", "[\"'`]([^\"'`]*).*?[\"'`]"]
  ]
}
```

---

## 실행 및 테스트

### 1. 백엔드 서버 실행

```bash
cd backend

# 가상환경 활성화 (아직 안했다면)
.\venv\Scripts\activate

# 서버 실행
uvicorn app.main:app --reload

# 출력:
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process [xxxxx] using WatchFiles
# INFO:     Started server process [xxxxx]
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
```

**브라우저에서 확인**:
- API 문서 (Swagger): http://localhost:8000/docs
- API 문서 (ReDoc): http://localhost:8000/redoc
- 헬스체크: http://localhost:8000/

### 2. 프론트엔드 서버 실행

```bash
# 새 터미널 열기
cd frontend

# 개발 서버 실행
npm run dev

# 출력:
#   VITE v7.3.1  ready in xxx ms
#
#   ➜  Local:   http://localhost:5173/
#   ➜  Network: use --host to expose
#   ➜  press h + enter to show help
```

**브라우저에서 확인**:
- 홈페이지: http://localhost:5173/
- 코드 관리: http://localhost:5173/codes

### 3. API 테스트

#### Swagger UI에서 테스트
1. http://localhost:8000/docs 접속
2. `GET /api/v1/codes/major-categories` 확장
3. "Try it out" 클릭
4. "Execute" 클릭
5. 응답 확인

#### curl로 테스트
```bash
# 대분류 목록 조회
curl http://localhost:8000/api/v1/codes/major-categories

# 출력 (JSON):
# [
#   {
#     "id": 1,
#     "code": "D",
#     "name_ko": "개발품",
#     "name_en": "Developed Part",
#     ...
#   }
# ]

# 대분류 생성
curl -X POST http://localhost:8000/api/v1/codes/major-categories \
  -H "Content-Type: application/json" \
  -d "{\"code\":\"T\",\"name_ko\":\"테스트\",\"name_en\":\"Test\"}"
```

### 4. 프론트엔드 기능 테스트

**코드 관리 화면** (http://localhost:5173/codes):

1. **목록 조회**
   - "대분류" 탭 클릭
   - 데이터 로딩 확인

2. **추가 기능**
   - "추가" 버튼 클릭
   - 모달 열림 확인
   - 데이터 입력 (코드: "T", 한글명: "테스트")
   - "추가" 버튼 클릭
   - 토스트 알림 확인
   - 목록에 추가된 항목 확인

3. **수정 기능**
   - "수정" 버튼 클릭
   - 모달에 데이터 로딩 확인
   - 데이터 수정
   - "수정" 버튼 클릭
   - 토스트 알림 확인

4. **삭제 기능**
   - "삭제" 버튼 클릭
   - 확인 다이얼로그 확인
   - "확인" 클릭
   - 토스트 알림 확인
   - 목록에서 제거 확인

---

## 문제 해결

### 백엔드 문제

#### 1. 가상환경 활성화 실패
**문제**:
```
.\venv\Scripts\activate : 이 시스템에서 스크립트를 실행할 수 없으므로...
```

**해결**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 2. 패키지 설치 실패
**문제**:
```
ERROR: Could not find a version that satisfies the requirement...
```

**해결**:
```bash
# pip 업그레이드
python -m pip install --upgrade pip

# 재시도
pip install -r requirements.txt
```

#### 3. psycopg2 설치 오류 (Windows)
**문제**:
```
Error: pg_config executable not found.
```

**해결**:
- `psycopg2` 대신 `psycopg2-binary` 사용 (이미 requirements.txt에 포함)

#### 4. 데이터베이스 연결 실패
**문제**:
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**해결**:
```bash
# 1. PostgreSQL 서비스 실행 확인
# Windows: 서비스 앱에서 postgresql 확인

# 2. .env 파일 확인
# DATABASE_URL의 비밀번호, 포트, DB명 확인

# 3. 수동 연결 테스트
psql -U postgres -d xmanager
```

#### 5. Alembic 마이그레이션 오류
**문제**:
```
Target database is not up to date.
```

**해결**:
```bash
# 현재 버전 확인
.\venv\Scripts\alembic current

# 최신 버전으로 업그레이드
.\venv\Scripts\alembic upgrade head

# 또는 롤백 후 재시도
.\venv\Scripts\alembic downgrade base
.\venv\Scripts\alembic upgrade head
```

### 프론트엔드 문제

#### 1. npm install 실패
**문제**:
```
npm ERR! code ERESOLVE
```

**해결**:
```bash
# 레거시 피어 종속성 허용
npm install --legacy-peer-deps

# 또는 캐시 정리 후 재시도
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

#### 2. Tailwind CSS 디렉티브 오류
**문제**:
```
Unknown at rule @tailwindcss
```

**해결**:
```bash
# Tailwind CSS 3.4로 다운그레이드
npm uninstall tailwindcss
npm install -D tailwindcss@^3.4.0 postcss autoprefixer
```

#### 3. Vite 포트 충돌
**문제**:
```
Port 5173 is in use
```

**해결**:
```bash
# 다른 포트 사용
npm run dev -- --port 5174

# 또는 vite.config.ts 수정
# server: { port: 5174 }
```

#### 4. API 호출 CORS 오류
**문제**:
```
Access to XMLHttpRequest blocked by CORS policy
```

**해결**:
```python
# backend/app/main.py 확인
# CORSMiddleware 설정 확인

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 프론트엔드 URL 확인
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 데이터베이스 문제

#### 1. 데이터베이스 생성 실패
**문제**:
```
ERROR:  database "xmanager" already exists
```

**해결**:
```sql
-- 기존 DB 삭제 후 재생성 (주의: 데이터 손실)
DROP DATABASE xmanager;
CREATE DATABASE xmanager;

-- 또는 기존 DB 사용
\c xmanager
```

#### 2. 권한 오류
**문제**:
```
ERROR:  permission denied for table...
```

**해결**:
```sql
-- postgres 사용자로 접속했는지 확인
-- 또는 권한 부여
GRANT ALL PRIVILEGES ON DATABASE xmanager TO postgres;
```

#### 3. 테이블이 없음
**문제**:
```
relation "major_category" does not exist
```

**해결**:
```bash
# 마이그레이션 실행 확인
cd backend
.\venv\Scripts\alembic upgrade head

# 테이블 확인
psql -U postgres -d xmanager -c "\dt"
```

---

## 추가 설정 (선택사항)

### Git 설정

```bash
# Git 초기화 (아직 안했다면)
git init

# .gitignore 확인
# Python, Node.js, 환경변수 파일이 제외되어 있는지 확인

# 첫 커밋
git add .
git commit -m "Initial commit"
```

### 개발용 스크립트 추가

**backend/start.sh** (Linux/Mac):
```bash
#!/bin/bash
source venv/bin/activate
uvicorn app.main:app --reload
```

**backend/start.bat** (Windows):
```batch
@echo off
call venv\Scripts\activate
uvicorn app.main:app --reload
```

**frontend/package.json**에 이미 포함:
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  }
}
```

---

## 환경 확인 체크리스트

### 설치 확인
- [ ] Python 3.12.10 설치 확인
- [ ] Node.js 24.12.0 설치 확인
- [ ] PostgreSQL 17.7 설치 확인
- [ ] Git 설치 확인

### 백엔드 확인
- [ ] 가상환경 생성
- [ ] 가상환경 활성화
- [ ] 패키지 설치 완료
- [ ] .env 파일 생성 및 설정
- [ ] 데이터베이스 생성
- [ ] 마이그레이션 적용
- [ ] 초기 데이터 입력
- [ ] 백엔드 서버 실행 (http://localhost:8000)
- [ ] Swagger 문서 접속 (http://localhost:8000/docs)

### 프론트엔드 확인
- [ ] 패키지 설치 완료
- [ ] .env 파일 생성 및 설정
- [ ] 프론트엔드 서버 실행 (http://localhost:5173)
- [ ] 코드 관리 화면 접속 (http://localhost:5173/codes)

### 기능 확인
- [ ] 대분류 목록 조회
- [ ] 대분류 추가
- [ ] 대분류 수정
- [ ] 대분류 삭제
- [ ] 재질 목록 조회

---

## 다음 단계

환경 설정이 완료되었다면:

1. **문서 읽기**
   - [개발기획서 v1.3](./X-Manager_개발기획서_v1.3.md)
   - [프로젝트 지침](./X-Manager_프로젝트_지침.md)
   - [Claude 개발 가이드](./claude.md)

2. **개발 시작**
   - 나머지 코드 마스터 API 완성
   - 부품 마스터 개발
   - 검색 및 페이지네이션 추가

3. **협업 준비**
   - Git 리포지토리 설정
   - 브랜치 전략 수립
   - 코드 리뷰 프로세스 정의

---

**최종 업데이트**: 2026-01-08
