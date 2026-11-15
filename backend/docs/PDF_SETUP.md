# 견적서 PDF 생성 환경 세팅 (Windows)

WeasyPrint는 한글·CSS 렌더링에 GTK3 런타임 라이브러리(Pango/Cairo/GDK-PixBuf)를 사용합니다.
Windows에서는 GTK3를 시스템에 한 번만 설치하면 모든 PDF 생성이 동작합니다.

## 1. GTK3 런타임 설치 (서버/개발 PC 1회)

### 권장 경로 — MSYS2 (WeasyPrint 공식 권장)

WeasyPrint 공식 문서가 권장하는 가장 안정적인 방법입니다.

```powershell
# 1) MSYS2 설치 (관리자 권한 필요)
#    공식 사이트: https://www.msys2.org/
#    설치 위치 기본값(C:\msys64) 그대로 OK

# 2) MSYS2 셸 종류에 따라 패키지명이 다름. 현재 사용 중인 셸 확인 후 둘 중 하나 선택:

# 2-A) UCRT64 셸 (권장 — 최신·MS 공식 권장 런타임)
pacman -S mingw-w64-ucrt-x86_64-pango mingw-w64-ucrt-x86_64-gdk-pixbuf2 mingw-w64-ucrt-x86_64-libffi

# 2-B) MINGW64 셸
pacman -S mingw-w64-x86_64-pango mingw-w64-x86_64-gdk-pixbuf2 mingw-w64-x86_64-libffi

# 3) 시스템 환경변수 PATH에 추가 (영구)
#    제어판 → 시스템 → 고급 시스템 설정 → 환경 변수 → Path 편집 → 새로 만들기
#    UCRT64를 쓴 경우:    C:\msys64\ucrt64\bin
#    MINGW64를 쓴 경우:   C:\msys64\mingw64\bin

# 4) 추가 후 PowerShell/명령 프롬프트를 모두 새로 열어야 PATH 반영됨
```

### 대안 — GTK3 Standalone Installer (간편하지만 구버전 호환성 이슈 가능)

MSYS2 설치가 부담스러우면 다음 페이지에서 GTK3 Runtime Win64 인스톨러 사용:
- https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows

> **주의**: WeasyPrint 62.x는 비교적 최신 GTK가 필요하므로 MSYS2 경로를 권장합니다.
> Standalone installer로 설치할 경우 WeasyPrint 60.x로 다운그레이드해야 할 수 있습니다.

## 2. Python 패키지 설치

GTK3 설치 + PATH 반영(터미널 재시작) 후:

```powershell
cd c:\X-MANAGER_R0.1\backend
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 3. 설치 확인

```powershell
.\.venv\Scripts\python -c "import weasyprint; weasyprint.HTML(string='<h1>OK</h1>').write_pdf('test.pdf'); print('PDF 생성 성공')"
```

`PDF 생성 성공` 메시지가 나오고 `test.pdf` 파일이 생성되면 완료입니다.
오류 발생 시 메시지에 어떤 DLL이 누락되었는지 표시되니 그 라이브러리만 추가 설치하세요.

## 4. 폰트 배치

`backend/app/templates/pdf/assets/fonts/README.md` 참고하여
Noto Sans KR / Noto Sans 폰트 4종을 다운로드 후 배치합니다.

## 5. 알려진 이슈 — harfbuzz heap corruption

WeasyPrint 60+는 폰트 서브셋팅을 위해 시스템 harfbuzz를 ctypes로 호출하는데,
**MSYS2 ucrt64의 harfbuzz 13.x는 WeasyPrint와 ABI 비호환** 으로
heap corruption(0xc0000374) 크래시가 발생합니다.

해결 방법 — `app/services/pdf/__init__.py`에 다음 패치가 자동 적용되어 있습니다:

```python
from weasyprint.pdf import fonts as _wp_fonts
_wp_fonts.harfbuzz_subset = None  # fonttools 기반 fallback으로 전환
```

**`app.services.pdf` 모듈을 import해야** 패치가 활성화되니, 견적서 PDF 생성 코드는
반드시 이 모듈을 거쳐 사용해야 합니다. 직접 `import weasyprint`만 하면 크래시.

## 6. 운영 서버 적용

운영 서버에서도 동일하게 GTK3 설치 + PATH 추가 + `pip install` 필요합니다.
배포 시 체크리스트:
- [ ] MSYS2 + GTK3 패키지 설치 완료
- [ ] 시스템 PATH에 `C:\msys64\mingw64\bin` 추가
- [ ] 폰트 파일 4종 배치 완료
- [ ] `pip install -r requirements.txt` 실행 완료
- [ ] 백엔드 서비스 재시작
