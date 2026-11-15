/**
 * 과제(국가 R&D) 구매기안서의 예산 항목 체계 — RCMS 비목/항목/세부항목.
 *
 * 출처: docs/261027_과제용 기안서 양식 변경 요청 (3번 슬라이드 표).
 * - 비목은 항목을 고르면 자동으로 정해진다(사용자가 고르지 않음).
 * - 세부항목 이름은 RCMS 세부항목과 같아야 한다.
 */

export interface RcmsItem {
  category: string   // 비목 (자동)
  name: string       // 항목
  details: string[]  // 세부항목
}

export const RCMS_BUDGET_ITEMS: RcmsItem[] = [
  {
    category: '직접비',
    name: '인건비',
    details: ['내부인건비', '외부인건비'],
  },
  {
    category: '직접비',
    name: '연구시설·장비 및 재료비',
    details: ['연구시설·장비구입비', '연구시설·장비임차비', '시약·재료구입비', '시작품제작비', '시제품제작비', '시험설비제작비'],
  },
  {
    category: '직접비',
    name: '연구활동비',
    details: ['국외여비', '기술정보수집비', '국내외교육훈련비', '시험분석검사비', '학회·세미나참가비', '복사비', '인쇄비'],
  },
  {
    category: '직접비',
    name: '연구과제추진비',
    details: ['국내여비', '사무용품비', '회의비', '야근식대'],
  },
  {
    category: '간접비',
    name: '간접비',
    details: ['지식재산권출원·등록비', '회계감사비', '기업신용평가비'],
  },
  {
    category: '위탁연구개발비',
    name: '위탁연구개발비',
    details: ['위탁연구개발비'],
  },
]

export function findRcmsItem(name: string | null | undefined): RcmsItem | undefined {
  if (!name) return undefined
  return RCMS_BUDGET_ITEMS.find((i) => i.name === name)
}
