# Claude Code 시작 가이드

## X-Manager 프로젝트 개발 시작하기

---

## 1. Claude Code 실행 방법

### 1.1 VS Code에서 실행
1. VS Code로 프로젝트 폴더 열기: `C:\Projects\x-manager`
2. 터미널 열기: `Ctrl + `` (백틱)
3. Claude Code 실행:
```bash
claude
```

### 1.2 Claude Code 기본 명령어
```bash
# Claude Code 시작
claude

# 특정 파일과 함께 시작
claude src/main.py

# 도움말
claude --help

# 종료
/exit 또는 Ctrl+C
```

---

## 2. 프로젝트 초기 설정 프롬프트

Claude Code가 실행되면, 아래 프롬프트를 복사해서 붙여넣으세요.

### 2.1 첫 번째 프롬프트: 프로젝트 구조 생성

```
X-Manager 프로젝트를 초기 설정해줘.

기술 스택:
- 백엔드: FastAPI + SQLAlchemy + Pydantic
- 프론트엔드: Vue.js 3 + Vite + Tailwind CSS + Pinia
- 데이터베이스: PostgreSQL

해야 할 것:
1. 프로젝트 폴더 구조 생성 (backend/, frontend/)
2. 백엔드 Python 가상환경 생성 및 기본 패키지 설치
3. 프론트엔드 Vue.js 프로젝트 생성
4. 기본 설정 파일 생성 (.env, .gitignore 등)

먼저 현재 폴더 구조를 확인하고, 단계별로 진행해줘.
```

---

### 2.2 두 번째 프롬프트: 데이터베이스 설정

```
PostgreSQL 데이터베이스를 설정해줘.

정보:
- 데이터베이스 이름: xmanager
- 사용자: xmanager
- 비밀번호: (설치 시 설정한 비밀번호)
- 포트: 5432

해야 할 것:
1. PostgreSQL에 데이터베이스 생성
2. 사용자 생성 및 권한 부여
3. backend/.env 파일에 DATABASE_URL 설정
4. SQLAlchemy 연결 테스트
```

---

### 2.3 세 번째 프롬프트: 코드 마스터 테이블 생성

```
기획서에 맞게 코드 마스터 테이블들을 생성해줘.

필요한 테이블:
1. major_category (대분류: D/S/M/R/C/P)
2. middle_category (중분류: P/E/O/M/G/C/B/I/W/A/F/H/X/T)
3. minor_category (소분류: HB1/HB3/HB5/TF1/IS1/CRP/COM 등)
4. item_code (품목코드)
5. material (재질: A6/S4/NB/AB/BR 등)
6. treatment (후처리: NK/ZK/CD/WA/HB/NN 등)
7. level (레벨: F/P/K/S/R/M)
8. procurement_type (조달구분: MFG/PUR/INJ/SEM/FIN)
9. unit (단위: EA/SET/KIT/PKG/FP/M/G/ML)

각 테이블은 공통으로:
- id, code, name_ko, name_en, description, sort_order, is_active, created_at

Alembic 마이그레이션으로 생성하고, 초기 데이터도 넣어줘.
```

---

### 2.4 네 번째 프롬프트: 부품 마스터 API

```
부품 마스터 API를 만들어줘.

기능:
1. 부품 목록 조회 (GET /api/v1/parts)
   - 페이징, 검색, 필터 지원
2. 부품 상세 조회 (GET /api/v1/parts/{id})
3. 부품 등록 (POST /api/v1/parts)
   - 품번 자동 생성: [대분류]-[소분류]-[품목코드]-[재질]-[레벨]
4. 부품 수정 (PUT /api/v1/parts/{id})
5. 부품 삭제 (DELETE /api/v1/parts/{id})

테이블 구조는 기획서 참조.
Pydantic 스키마와 함께 만들어줘.
```

---

## 3. 개발 진행 순서

```
1주차: 환경설정
├── 개발 환경 설치 ✓
├── 프로젝트 초기 설정
├── DB 연결 설정
└── 기본 구조 확인

2주차: 코드 마스터
├── 코드 테이블 생성
├── 코드 API 개발
├── 코드 관리 화면
└── 초기 데이터 입력

3-4주차: 부품 마스터
├── 부품 테이블 생성
├── 품번 자동생성 로직
├── 부품 API 개발
└── 부품 등록/목록 화면

5-6주차: 공정 마스터
├── 공정 테이블 생성
├── 공정 API 개발
└── 공정 관리 화면

7-8주차: BOM 관리
├── BOM 테이블 생성 (재귀)
├── BOM API 개발
├── BOM 트리 화면
└── 원가 계산

9-10주차: 마무리
├── 승인 프로세스
├── 사용자/권한
├── 테스트
└── 배포
```

---

## 4. 자주 사용할 명령어

### 백엔드 (Python/FastAPI)
```bash
# 가상환경 활성화 (Windows)
cd backend
.\venv\Scripts\activate

# 서버 실행
uvicorn app.main:app --reload

# 패키지 설치
pip install -r requirements.txt

# DB 마이그레이션
alembic upgrade head
alembic revision --autogenerate -m "설명"
```

### 프론트엔드 (Vue.js)
```bash
# 개발 서버 실행
cd frontend
npm run dev

# 패키지 설치
npm install

# 빌드
npm run build
```

### 데이터베이스
```bash
# PostgreSQL 접속
psql -U xmanager -d xmanager

# pgAdmin 4 실행 (GUI)
Windows 검색 → pgAdmin 4
```

---

## 5. 프로젝트 파일 구조 (목표)

```
C:\Projects\x-manager\
│
├── backend\                      # FastAPI 백엔드
│   ├── app\
│   │   ├── api\
│   │   │   └── v1\
│   │   │       ├── parts.py
│   │   │       ├── bom.py
│   │   │       ├── process.py
│   │   │       └── codes.py
│   │   ├── models\
│   │   ├── schemas\
│   │   ├── services\
│   │   ├── core\
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   └── main.py
│   ├── alembic\
│   ├── tests\
│   ├── requirements.txt
│   ├── .env
│   └── alembic.ini
│
├── frontend\                     # Vue.js 프론트엔드
│   ├── src\
│   │   ├── api\
│   │   ├── components\
│   │   ├── views\
│   │   ├── stores\
│   │   ├── router\
│   │   ├── App.vue
│   │   └── main.js
│   ├── public\
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── docs\                         # 문서
│   ├── 개발기획서_v1.3.md
│   └── 설치가이드.md
│
├── .gitignore
└── README.md
```

---

## 6. 기획서 참조

Claude Code에서 기획서를 참조하려면:

```
기획서 파일 경로: C:\Projects\x-manager\docs\개발기획서_v1.3.md

이 파일을 읽고 참조해서 개발해줘.
```

---

## 7. 문제 발생 시

Claude Code에게 이렇게 물어보세요:

```
# 오류 해결
"이런 오류가 발생했어: [오류 메시지]. 어떻게 해결해?"

# 코드 설명
"이 코드가 뭐하는 건지 설명해줘"

# 기능 추가
"여기에 페이징 기능을 추가해줘"

# 디버깅
"왜 이게 동작 안 하는지 확인해줘"
```

---

**이제 설치 완료 후 Claude Code를 실행하고 첫 번째 프롬프트부터 시작하세요!**

