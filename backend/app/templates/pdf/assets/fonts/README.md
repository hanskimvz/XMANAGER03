# PDF 폰트 디렉토리

견적서/PI/CI PDF 렌더링에 사용되는 한글·영문 폰트를 이 디렉토리에 배치합니다.

## 사용 폰트 (방산 외부 발송 문서용 — OFL 라이선스 필수)

다음 4개 파일을 이 디렉토리에 직접 배치:

```
NotoSansKR-Regular.ttf
NotoSansKR-Bold.ttf
NotoSans-Regular.ttf
NotoSans-Bold.ttf
```

## 다운로드 방법

### Noto Sans KR (한글)
- 출처: Google Fonts → https://fonts.google.com/noto/specimen/Noto+Sans+KR
- "Get font" → "Download all" → ZIP 압축 해제 후 `static/` 폴더의 Regular/Bold만 사용
- 라이선스: OFL 1.1 (재배포·임베딩 자유)

### Noto Sans (영문/숫자)
- 출처: Google Fonts → https://fonts.google.com/noto/specimen/Noto+Sans
- 동일하게 Regular/Bold만 사용

## 라이선스 파일

`LICENSE-OFL.txt`도 이 폴더에 함께 두세요. (Noto 폰트 ZIP 내 OFL.txt를 그대로 복사)

## 시스템 폰트 사용 금지

기존 발주서 PDF는 `C:/Windows/Fonts/malgun.ttf`(맑은 고딕)을 사용하지만,
견적서는 **외부 고객사 발송 문서**이므로 시스템 폰트(라이선스 회색지대) 대신
OFL 폰트만 사용합니다.
