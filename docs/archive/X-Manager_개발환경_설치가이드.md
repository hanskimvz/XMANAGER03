# X-Manager 개발 환경 설치 가이드

## Windows 기준 설치 가이드

**작성일**: 2025년 6월  
**대상**: IT 초보자

---

## 1. Git 설치

Git은 코드 버전 관리 도구입니다.

### 1.1 다운로드
1. https://git-scm.com/download/win 접속
2. "Click here to download" 클릭
3. 다운로드된 파일 실행

### 1.2 설치 옵션
설치 중 대부분 **기본값(Next)** 클릭하면 됩니다.  
아래 항목만 확인:

- **Select Components**: 기본값 유지
- **Default editor**: VS Code 선택 (나중에 설치 후 변경 가능)
- **PATH environment**: "Git from the command line and also from 3rd-party software" 선택
- 나머지: 기본값

### 1.3 설치 확인
1. Windows 검색에서 "cmd" 입력 → 명령 프롬프트 실행
2. 아래 명령어 입력:
```bash
git --version
```
3. `git version 2.xx.x` 출력되면 성공!

---

## 2. Python 설치

### 2.1 다운로드
1. https://www.python.org/downloads/ 접속
2. "Download Python 3.12.x" (또는 3.11.x) 클릭
3. 다운로드된 파일 실행

### 2.2 설치 옵션 (중요!)
⚠️ **설치 첫 화면에서 반드시 체크:**
- ✅ **"Add python.exe to PATH"** ← 매우 중요!
- ✅ "Use admin privileges when installing py.exe"

그 후 "Install Now" 클릭

### 2.3 설치 확인
명령 프롬프트에서:
```bash
python --version
```
`Python 3.12.x` 출력되면 성공!

추가 확인:
```bash
pip --version
```
`pip 24.x.x` 출력되면 성공!

---

## 3. Node.js 설치

### 3.1 다운로드
1. https://nodejs.org/ 접속
2. **LTS** 버전 다운로드 (예: 20.x.x LTS)
3. 다운로드된 파일 실행

### 3.2 설치 옵션
- 모든 옵션 **기본값** 유지
- "Automatically install the necessary tools" 체크하면 추가 도구도 설치됨 (선택사항)

### 3.3 설치 확인
명령 프롬프트 **새로 열고**:
```bash
node --version
```
`v20.x.x` 출력되면 성공!

```bash
npm --version
```
`10.x.x` 출력되면 성공!

---

## 4. PostgreSQL 설치

### 4.1 다운로드
1. https://www.postgresql.org/download/windows/ 접속
2. "Download the installer" 클릭
3. Windows x86-64 버전 다운로드 (최신 버전, 예: 16.x)
4. 다운로드된 파일 실행

### 4.2 설치 옵션
1. **Installation Directory**: 기본값 유지
2. **Select Components**: 
   - ✅ PostgreSQL Server
   - ✅ pgAdmin 4 (DB 관리 도구)
   - ✅ Command Line Tools
3. **Data Directory**: 기본값 유지
4. **Password**: 
   - ⚠️ **비밀번호 설정 (꼭 기억하세요!)**
   - 예: `xmanager2025` (본인이 기억하기 쉬운 것으로)
5. **Port**: 기본값 `5432` 유지
6. **Locale**: Korean, Korea 또는 기본값

### 4.3 설치 확인
1. Windows 검색에서 "pgAdmin" 실행
2. 왼쪽 트리에서 "Servers" → "PostgreSQL 16" 클릭
3. 설치 시 입력한 비밀번호 입력
4. 연결되면 성공!

### 4.4 환경 변수 설정 (선택)
명령 프롬프트에서 PostgreSQL 명령어 사용하려면:

1. Windows 검색 → "환경 변수" → "시스템 환경 변수 편집"
2. "환경 변수" 버튼 클릭
3. "시스템 변수"에서 "Path" 선택 → "편집"
4. "새로 만들기" → `C:\Program Files\PostgreSQL\16\bin` 추가
5. 확인 → 확인

---

## 5. VS Code 설치

### 5.1 다운로드
1. https://code.visualstudio.com/ 접속
2. "Download for Windows" 클릭
3. 다운로드된 파일 실행

### 5.2 설치 옵션
- ✅ "Add to PATH" (기본 체크됨)
- ✅ "Register Code as an editor for supported file types"
- ✅ "Add 'Open with Code' action to Windows Explorer file context menu"
- ✅ "Add 'Open with Code' action to Windows Explorer directory context menu"

### 5.3 필수 확장 프로그램 설치
VS Code 실행 후, 왼쪽 사이드바에서 **확장(Extensions)** 아이콘 클릭 (또는 `Ctrl+Shift+X`)

아래 확장 프로그램 검색 후 설치:

| 확장 프로그램 | 검색어 | 용도 |
|--------------|--------|------|
| Python | python | Python 개발 |
| Pylance | pylance | Python 타입 체크 |
| Vue - Official | vue | Vue.js 개발 |
| Tailwind CSS IntelliSense | tailwind | CSS 자동완성 |
| PostgreSQL | postgresql | DB 연결 |
| Thunder Client | thunder client | API 테스트 |
| GitLens | gitlens | Git 이력 확인 |
| Korean Language Pack | korean | 한국어 지원 |

### 5.4 VS Code 설정
1. `Ctrl + ,` (설정 열기)
2. 검색창에 "format on save" 입력
3. "Editor: Format On Save" 체크 ✅

---

## 6. Claude Code 설치

### 6.1 Claude Code란?
터미널에서 AI와 대화하며 코딩하는 도구입니다.

### 6.2 설치 방법

**방법 1: npm으로 설치 (권장)**

명령 프롬프트 또는 PowerShell에서:
```bash
npm install -g @anthropic-ai/claude-code
```

**방법 2: Anthropic 공식 사이트**

1. https://claude.ai/code 접속
2. 설치 가이드 따라 진행

### 6.3 Claude Code 인증
```bash
claude login
```
Anthropic 계정으로 로그인

### 6.4 VS Code에서 Claude Code 사용

VS Code 터미널에서 (`Ctrl + `` 또는 메뉴 → 터미널 → 새 터미널):
```bash
claude
```

또는 프로젝트 폴더에서:
```bash
cd C:\Projects\x-manager
claude
```

---

## 7. 프로젝트 폴더 생성

### 7.1 작업 폴더 만들기
1. 탐색기에서 `C:\` 드라이브 열기
2. 새 폴더 만들기: `Projects`
3. `Projects` 폴더 안에 새 폴더: `x-manager`

최종 경로: `C:\Projects\x-manager`

### 7.2 VS Code에서 폴더 열기
1. VS Code 실행
2. 파일 → 폴더 열기
3. `C:\Projects\x-manager` 선택

---

## 8. 설치 확인 체크리스트

터미널(명령 프롬프트)에서 아래 명령어들이 모두 동작하는지 확인:

```bash
# Git
git --version
# 예상 출력: git version 2.xx.x

# Python
python --version
# 예상 출력: Python 3.12.x

# pip
pip --version
# 예상 출력: pip 24.x.x

# Node.js
node --version
# 예상 출력: v20.x.x

# npm
npm --version
# 예상 출력: 10.x.x

# PostgreSQL (환경변수 설정한 경우)
psql --version
# 예상 출력: psql (PostgreSQL) 16.x
```

---

## 9. 문제 해결

### 9.1 "명령어를 찾을 수 없습니다" 오류
- 해당 프로그램이 PATH에 추가되지 않은 경우
- 해결: 프로그램 재설치 시 "Add to PATH" 옵션 체크
- 또는: 환경 변수에 수동 추가

### 9.2 Python 설치 후 `python` 명령 안 됨
- Windows Store 버전과 충돌 가능
- 해결: `python3` 또는 `py` 명령어 시도
- 또는: Windows 설정 → 앱 → 앱 실행 별칭 → Python 끄기

### 9.3 PostgreSQL 연결 안 됨
- 서비스가 실행 중인지 확인
- Windows 검색 → "서비스" → "postgresql-x64-16" 상태 확인
- "시작"되어 있어야 함

### 9.4 VS Code 터미널에서 명령어 안 됨
- VS Code 재시작
- 새 터미널 열기 (`Ctrl + Shift + ``)
- PowerShell 대신 Command Prompt 사용해보기

---

## 10. 다음 단계

모든 설치가 완료되면:

1. VS Code에서 `C:\Projects\x-manager` 폴더 열기
2. 터미널 열기 (`Ctrl + ``)
3. Claude Code 실행:
   ```bash
   claude
   ```
4. Claude에게 프로젝트 초기 설정 요청

---

## 설치 완료 후 폴더 구조

```
C:\Projects\x-manager\
├── backend\           # FastAPI 백엔드 (나중에 생성)
├── frontend\          # Vue.js 프론트엔드 (나중에 생성)
├── docs\              # 문서
└── README.md          # 프로젝트 설명
```

---

## 버전 정보 (2025년 6월 기준 권장)

| 소프트웨어 | 권장 버전 |
|-----------|----------|
| Git | 2.45+ |
| Python | 3.11 ~ 3.12 |
| Node.js | 20 LTS |
| PostgreSQL | 15 ~ 16 |
| VS Code | 최신 버전 |

---

**설치 중 문제가 생기면 Claude Code에서 물어보세요!**

