# BOM 엑셀 업로드 기능 개발 요청서

## 1. 개요

BOM 관리 화면에서 엑셀 파일을 업로드하여 BOM 구조를 일괄 등록하는 기능 추가 요청

### 현재 상태
- BOM 등록: 수동으로 하위 부품을 하나씩 추가
- 엑셀 내보내기: 구현됨 (`bomApi.exportExcel`)

### 요청 기능
- 엑셀 파일 업로드 → BOM 트리 구조 자동 파싱 → DB 일괄 등록

---

## 2. 엑셀 양식 구조

### 헤더 영역 (1~7행)
```
행1: BOM (Bill of Materials)     ← 제목
행3: 상위 부품: HXB15-PSD-B-O4-S1-D55 [U]    ← 최상위 품번
행4: 품명: (품명)
행5: 규격: (규격)
행6: 출력일시: 2026-01-28 17:21:15
행8: [레벨] [품번] [품명] [규격] [수량] [단위] [비고]   ← 컬럼 헤더
```

### 데이터 영역 (9행~)
| 컬럼A | 컬럼B | 컬럼C | 컬럼D | 컬럼E | 컬럼F | 컬럼G |
|-------|-------|-------|-------|-------|-------|-------|
| 레벨 | 품번 | 품명 | 규격 | 수량 | 단위 | 비고 |
| L1 | HXB15-PSD-B-STD [K] | HXB15 PLUG AL 기본 | - | 1 | EA | |
| L2 | HB05-PLP-BBO-01-A6-HB [S] | 플러그 백쉘-부트 | - | 1 | EA | |
| L3 | HB05-PLP-BBO-01-A6-HB [C] | 플러그 백쉘-부트 | - | 1 | EA | |

### 레벨 규칙
- `L1`, `L2`, `L3`, `L4` ... 숫자로 계층 표현
- 같은 레벨 연속 = 형제 관계
- 레벨 증가 = 하위 (자식)
- 레벨 감소 = 상위로 복귀

### 예시 트리
```
L1 A        ← 루트
  L2 B      ← A의 자식
    L3 C    ← B의 자식
    L3 D    ← B의 자식 (C와 형제)
  L2 E      ← A의 자식 (B와 형제)
L1 F        ← 루트 (A와 형제)
```

---

## 3. 파싱 로직 (TypeScript 참고용)

```typescript
interface BomUploadItem {
  level: number;          // 레벨 숫자 (1, 2, 3...)
  part_no: string;        // 품번
  part_name: string;      // 품명
  spec: string;           // 규격
  qty: number;            // 수량
  unit: string;           // 단위
  remark: string;         // 비고
}

interface BomTreeNode extends BomUploadItem {
  children: BomTreeNode[];
}

function parseExcelToBomTree(rows: any[]): BomTreeNode[] {
  const tree: BomTreeNode[] = [];
  const stack: { level: number; node: BomTreeNode }[] = [];

  for (const row of rows) {
    const levelStr = String(row[0] || '').trim();
    if (!levelStr.startsWith('L')) continue;

    const level = parseInt(levelStr.replace('L', ''));
    const node: BomTreeNode = {
      level,
      part_no: String(row[1] || '').trim(),
      part_name: String(row[2] || '').trim(),
      spec: String(row[3] || '').trim(),
      qty: Number(row[4]) || 1,
      unit: String(row[5] || 'EA').trim(),
      remark: String(row[6] || '').trim(),
      children: [],
    };

    // 스택에서 현재 레벨보다 크거나 같은 것 제거
    while (stack.length > 0 && stack[stack.length - 1].level >= level) {
      stack.pop();
    }

    if (stack.length === 0) {
      tree.push(node);
    } else {
      stack[stack.length - 1].node.children.push(node);
    }

    stack.push({ level, node });
  }

  return tree;
}
```

---

## 4. API 요청 구조 (제안)

### 엔드포인트
```
POST /api/v1/bom/upload
Content-Type: multipart/form-data
```

### Request
```
file: (엑셀 파일)
parent_part_id: number (선택, 없으면 헤더의 상위품번 사용)
mode: 'replace' | 'append' (기존 BOM 처리 방식)
```

### Response
```json
{
  "success": true,
  "message": "57개 BOM 항목이 등록되었습니다.",
  "created_count": 57,
  "skipped_count": 0,
  "errors": []
}
```

### 에러 케이스
```json
{
  "success": false,
  "message": "품번을 찾을 수 없습니다.",
  "errors": [
    { "row": 15, "part_no": "INVALID-001 [R]", "error": "미등록 품번" }
  ]
}
```

---

## 5. UI 변경 사항

### BOMView.vue 수정

#### 버튼 추가 위치
```vue
<!-- 기존 버튼들 옆에 추가 -->
<button @click="openUploadModal" class="px-3 py-1 bg-purple-500 text-white text-sm rounded hover:bg-purple-600">
  📤 엑셀 업로드
</button>
```

#### 새 컴포넌트 필요
- `BOMUploadModal.vue`: 업로드 모달

### 모달 기능
1. 파일 선택 (드래그 앤 드롭 지원)
2. 미리보기 (파싱 결과 트리 표시)
3. 검증 결과 표시 (미등록 품번 등)
4. 업로드 모드 선택 (기존 BOM 덮어쓰기 / 추가)
5. 확인 후 등록

---

## 6. Backend 변경 사항

### 새 엔드포인트 추가
- `backend/app/api/v1/bom.py`에 `/upload` 엔드포인트 추가

### 서비스 로직
- `backend/app/services/bom_service.py`에 엑셀 파싱 및 일괄 등록 메서드 추가

### 검증 로직
1. 품번 존재 여부 확인 (parts 테이블)
2. 순환 참조 체크
3. 중복 BOM 체크

---

## 7. 첨부 파일

1. **BOM_C레벨이상_생성결과.xlsx**: 업로드 테스트용 샘플 파일
2. **BOM_2102_2.xlsx**: 실제 BOM 양식 참고용

---

## 8. 우선순위 및 일정

### 필수 기능 (1차)
- [ ] 엑셀 파일 업로드
- [ ] 레벨 기반 트리 파싱
- [ ] 품번 검증
- [ ] BOM 일괄 등록

### 추가 기능 (2차)
- [ ] 미리보기 트리 뷰
- [ ] 미등록 품번 자동 생성 옵션
- [ ] 업로드 히스토리

---

## 9. 문의사항

기능 관련 문의: (담당자)

