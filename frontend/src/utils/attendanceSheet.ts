/**
 * 참석자 서명부 인쇄 유틸
 * 회의 등에서 참석자 명단 + 서명을 받기 위한 인쇄용 시트를 새 창에 생성한다.
 * (백엔드 변경 없이 클라이언트에서 HTML 을 작성해 window.print() 호출)
 */

export interface AttendanceAttendee {
  org?: string
  name?: string
  title?: string
}

export interface AttendanceSheetOptions {
  title: string
  dateStr?: string
  attendees: AttendanceAttendee[]
  /** 입력 인원 외에 현장 추가 서명을 위한 여분 빈 행 수 (기본 3) */
  extraRows?: number
}

// HTML 특수문자 이스케이프 (사용자 입력이 HTML 로 주입되므로 필수)
function esc(v: unknown): string {
  const s = v == null ? '' : String(v)
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/**
 * 참석자 서명부를 새 창에 인쇄한다. 팝업이 차단되면 Error 를 throw 한다.
 */
export function printAttendanceSheet(opts: AttendanceSheetOptions): void {
  const extraRows = opts.extraRows ?? 3
  const filled = (opts.attendees || []).filter(
    (a) => (a.org && a.org.trim()) || (a.name && a.name.trim()) || (a.title && a.title.trim()),
  )

  const dataRows = filled
    .map(
      (a, i) => `
        <tr>
          <td class="no">${i + 1}</td>
          <td class="org">${esc(a.org)}</td>
          <td class="name">${esc(a.name)}</td>
          <td class="title">${esc(a.title)}</td>
          <td class="sign"></td>
        </tr>`,
    )
    .join('')

  const blankRows = Array.from({ length: Math.max(0, extraRows) })
    .map(
      (_, i) => `
        <tr>
          <td class="no">${filled.length + i + 1}</td>
          <td class="org"></td>
          <td class="name"></td>
          <td class="title"></td>
          <td class="sign"></td>
        </tr>`,
    )
    .join('')

  const dateLine = opts.dateStr
    ? `<div class="meta">일시: ${esc(opts.dateStr)}</div>`
    : ''

  const html = `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<title>참석자 서명부 - ${esc(opts.title)}</title>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
    margin: 0;
    padding: 24px;
    color: #1f2937;
  }
  .sheet { max-width: 800px; margin: 0 auto; }
  h1 { font-size: 22px; text-align: center; margin: 0 0 4px; }
  .subtitle { text-align: center; font-size: 14px; color: #4b5563; margin-bottom: 16px; }
  .meta { font-size: 13px; color: #374151; margin-bottom: 12px; }
  table { width: 100%; border-collapse: collapse; }
  th, td {
    border: 1px solid #4b5563;
    padding: 8px 10px;
    font-size: 13px;
    text-align: center;
  }
  th { background: #f3f4f6; font-weight: 600; }
  td.org, td.name, td.title { text-align: left; }
  td.sign { height: 48px; }
  .no { width: 44px; }
  .name { width: 120px; }
  .title { width: 120px; }
  .sign { width: 180px; }
  .toolbar { text-align: center; margin: 16px 0; }
  .toolbar button {
    padding: 8px 18px; font-size: 14px; cursor: pointer;
    border: 1px solid #2563eb; background: #2563eb; color: #fff; border-radius: 6px;
  }
  @media print {
    body { padding: 0; }
    .toolbar { display: none; }
    @page { size: A4; margin: 18mm; }
  }
</style>
</head>
<body>
  <div class="sheet">
    <h1>참석자 서명부</h1>
    <div class="subtitle">${esc(opts.title)}</div>
    ${dateLine}
    <table>
      <thead>
        <tr>
          <th class="no">No</th>
          <th>소속</th>
          <th>이름</th>
          <th>직책</th>
          <th>서명</th>
        </tr>
      </thead>
      <tbody>
        ${dataRows}${blankRows}
      </tbody>
    </table>
    <div class="toolbar">
      <button type="button" onclick="window.print()">인쇄</button>
    </div>
  </div>
  <script>
    window.onload = function () {
      window.focus();
      window.print();
    };
  <\/script>
</body>
</html>`

  const win = window.open('', '_blank')
  if (!win) {
    throw new Error('팝업이 차단되었습니다')
  }
  win.document.open()
  win.document.write(html)
  win.document.close()
}
