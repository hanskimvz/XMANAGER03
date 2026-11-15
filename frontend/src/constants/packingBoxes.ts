/**
 * 사내 표준 포장 박스 프리셋 (치수 cm).
 * 포장 명세(Packing List) 입력 시 박스 선택 → 가로·세로·높이 자동 입력에 사용.
 * 목록에 없는 박스는 종류를 직접 입력하고 치수를 수기로 넣는다.
 */
export interface BoxPreset {
  name: string
  l: number // 가로 length (cm)
  w: number // 세로 width (cm)
  h: number // 높이 height (cm)
}

export const BOX_PRESETS: BoxPreset[] = [
  { name: '소박스', l: 23, w: 15, h: 10 },
  { name: '중박스1', l: 33, w: 24, h: 20 },
  { name: '중박스2', l: 40, w: 30, h: 20 },
  { name: '2겹대박스', l: 45, w: 36, h: 33 },
  { name: 'GOC박스', l: 44, w: 34, h: 46 },
  { name: '500m 스틸 릴', l: 55, w: 43, h: 62 },
  { name: '1000m 스틸 릴', l: 56, w: 55, h: 65 },
]

export function findBoxPreset(name: string | null | undefined): BoxPreset | undefined {
  const n = (name || '').trim()
  return BOX_PRESETS.find((x) => x.name === n)
}
