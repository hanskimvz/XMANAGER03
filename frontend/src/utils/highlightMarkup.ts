/**
 * 강조 마크업 ↔ HTML 양방향 변환
 *
 * Phase 4 리치 에디터(TipTap)와 백엔드 마크업 문법 간 어댑터.
 *
 *  마크업 → HTML : DB에서 불러와서 에디터에 표시할 때 사용
 *  HTML → 마크업 : 에디터 입력을 DB에 저장할 때 사용
 *
 * 백엔드 highlight.py 와 동일한 패턴/클래스를 사용해야 함.
 *
 * 지원 마크업:
 *   [[t]]      highlight-critical (빨간 굵게)
 *   {{t}}      highlight-warning  (노란 하이라이트)
 *   __t__      highlight-spec     (빨간 밑줄)
 *   **t**      <strong>           (단순 굵게)
 *   {color:t}  text-color-{color} (red/orange/green/blue/indigo/purple/gray)
 */

const PATTERN_CRITICAL = /\[\[(.+?)\]\]/gs
const PATTERN_WARNING = /\{\{(.+?)\}\}/gs
const PATTERN_SPEC = /__(.+?)__/gs
const PATTERN_BOLD = /\*\*(.+?)\*\*/gs

export const COLOR_NAMES = [
  'red', 'orange', 'green', 'blue', 'indigo', 'purple', 'gray',
] as const
export type ColorName = typeof COLOR_NAMES[number]

const PATTERN_COLOR = new RegExp(
  '\\{(' + COLOR_NAMES.join('|') + '):(.+?)\\}',
  'gs',
)

// 인라인 이미지 — {img:data:image/...} 형태. data URI만 허용(붙여넣기 이미지).
// base64 문자열에는 & < > " ' [ { * _ } 가 없으므로 다른 패턴/이스케이프와 충돌 없음.
const PATTERN_IMAGE = /\{img:(data:[^}]+)\}/gs

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/**
 * 마크업 문자열을 에디터 표시용 HTML로 변환.
 * 줄바꿈은 <br>로 변환됩니다.
 */
export function markupToHtml(text: string | null | undefined): string {
  if (!text) return ''
  let html = escapeHtml(text)
  // 이미지 먼저 복원(base64는 이스케이프 영향 없음)
  html = html.replace(PATTERN_IMAGE, '<img src="$1" class="markup-img" />')
  html = html.replace(PATTERN_CRITICAL, '<span class="highlight-critical">$1</span>')
  html = html.replace(PATTERN_WARNING, '<span class="highlight-warning">$1</span>')
  html = html.replace(PATTERN_SPEC, '<span class="highlight-spec">$1</span>')
  html = html.replace(PATTERN_BOLD, '<strong>$1</strong>')
  html = html.replace(PATTERN_COLOR, '<span class="text-color-$1">$2</span>')
  html = html.replace(/\n/g, '<br>')
  return html
}

/**
 * 에디터 HTML 출력을 DB 저장용 마크업으로 변환.
 * <span class="highlight-*">텍스트</span> → 마크업 문법
 * <span class="text-color-{name}">텍스트</span> → {name:텍스트}
 * <strong>텍스트</strong> → **텍스트**
 * <br>, </p><p>, </div><div> 등은 줄바꿈으로 변환
 */
export function htmlToMarkup(html: string | null | undefined): string {
  if (!html) return ''
  const div = document.createElement('div')
  div.innerHTML = html
  return convertNode(div).replace(/\n+$/, '') // 끝 줄바꿈 정리
}

function convertNode(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent || ''
  }

  if (node.nodeType !== Node.ELEMENT_NODE) {
    return ''
  }

  const el = node as HTMLElement
  const tag = el.tagName

  if (tag === 'BR') return '\n'

  // 인라인 이미지 — data URI만 마크업으로 보존
  if (tag === 'IMG') {
    const src = el.getAttribute('src') || ''
    return src.startsWith('data:') ? `{img:${src}}\n` : ''
  }

  let inner = ''
  for (const child of Array.from(el.childNodes)) {
    inner += convertNode(child)
  }

  // 강조 마크업 매핑
  const className = el.className || ''
  if (className.includes('highlight-critical')) return `[[${inner}]]`
  if (className.includes('highlight-warning')) return `{{${inner}}}`
  if (className.includes('highlight-spec')) return `__${inner}__`

  // 색상 매핑 — text-color-{name}
  const colorMatch = className.match(/text-color-(red|orange|green|blue|indigo|purple|gray)/)
  if (colorMatch) {
    return `{${colorMatch[1]}:${inner}}`
  }

  // 단순 굵게
  if (tag === 'STRONG' || tag === 'B') {
    return `**${inner}**`
  }

  // 블록 요소 끝에 줄바꿈
  const blockTags = new Set(['P', 'DIV', 'LI', 'BLOCKQUOTE'])
  if (blockTags.has(tag)) {
    return inner + '\n'
  }

  return inner
}
