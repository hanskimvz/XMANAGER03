# X-Manager 프로젝트 지침

## 프로젝트 개요
**X-Manager**는 방산용 광학 커넥터 제조업체(엑스빔테크)의 전사 통합 관리 시스템입니다.
1단계로 **부품관리 + BOM 시스템**을 개발합니다.

## 기술 스택 (확정)
- **백엔드**: FastAPI + SQLAlchemy 2.0 + Pydantic 2.0 + Alembic
- **프론트엔드**: Vue.js 3 + Vite + Tailwind CSS + Pinia
- **데이터베이스**: PostgreSQL 15+
- **배포**: Docker + Nginx

## 개발 원칙
1. **초보자 친화적**: 사용자는 IT 비전공자이므로 코드와 설명을 쉽게 작성
2. **단계별 진행**: 한 번에 너무 많은 코드를 작성하지 않고, 단계별로 확인하며 진행
3. **모듈화**: 향후 확장을 위해 모듈 단위로 개발
4. **문서화**: 주요 코드에 한글 주석 추가

## 품번 체계
```
[대분류]-[소분류]-[품목코드]-[재질]-[레벨]
   1자리    3자리     4자리     2자리   1자리

예: D-TF1-CH01-A6-R (개발품, TFOCA, 커넥터홀더01, AL6061, 단품)
```
- 재질 미지정 시 'XX' 사용
- 시스템용: DTF1CH01A6R (하이픈 없음)
- 표시용: D-TF1-CH01-A6-R (하이픈 포함)

## 레벨 코드 (BOM 단계)
| 코드 | 명칭 | 단위 |
|------|------|------|
| F | 완제품 | FP |
| P | 패키지 | PKG |
| K | 키트 | KIT |
| S | 서브어셈블리 | SET |
| R | 단품 | EA |
| M | 조립공정 | EA |

## 조달 구분
- MFG: 가공품 (자체/외주 가공)
- PUR: 구매품 (외부 구매)
- INJ: 사출품
- SEM: 반제품 (중간 조립품)
- FIN: 완제품

## 권한 체계
- **기술팀**: 부품/BOM 최초 등록, 승인
- **생산팀**: 부품/BOM 운영, 수정, 승인
- **영업팀**: 조회만

## 프로젝트 폴더 구조
```
x-manager/
├── backend/           # FastAPI
│   ├── app/
│   │   ├── api/v1/   # API 라우터
│   │   ├── models/   # SQLAlchemy 모델
│   │   ├── schemas/  # Pydantic 스키마
│   │   ├── services/ # 비즈니스 로직
│   │   └── core/     # 설정, DB 연결
│   ├── alembic/      # DB 마이그레이션
│   └── requirements.txt
├── frontend/          # Vue.js 3
│   ├── src/
│   │   ├── api/      # API 호출
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/   # Pinia
│   │   └── router/
│   └── package.json
└── docs/              # 문서
```

## 개발 순서
1. 프로젝트 초기 설정 (폴더 구조, 패키지 설치)
2. DB 연결 및 코드 마스터 테이블 생성
3. 부품 마스터 API + 화면
4. 공정 마스터 API + 화면
5. 대체품 관리
6. BOM 관리 (재귀 구조)
7. 원가 계산
8. 승인 프로세스
9. 사용자/권한

## 참고 문서
- 개발기획서_v1.3.md: 전체 시스템 설계서 (DB 스키마, API, 화면 등)
- 개발환경_설치가이드.md: 소프트웨어 설치 방법
- Claude_Code_시작가이드.md: 개발 시작 프롬프트

## 주의사항
- PostgreSQL의 WITH RECURSIVE를 활용한 재귀 BOM 쿼리 사용
- 모든 API는 /api/v1/ 프리픽스 사용
- 프론트엔드는 Composition API 사용
- 한글 주석 필수
