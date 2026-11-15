<script setup lang="ts">
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { hasPermStrict } from '@/stores/auth'
import { loadDepartments, departmentLabel } from '@/api/department'
import Pagination from '@/components/Pagination.vue'
import AnnouncementFormModal from './AnnouncementFormModal.vue'
import {
  announcementApi,
  type AnnouncementListItem,
  type AnnouncementDetail,
  type ReadReceiptList,
} from '@/api/announcement'

const { success, error } = useToast()
const isManager = computed(() => hasPermStrict('announcement:manage'))

const items = ref<AnnouncementListItem[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const q = ref('')
const includeInactive = ref(false)
const loading = ref(false)

const detail = ref<AnnouncementDetail | null>(null)

// 첨부 열기 — 인증 토큰을 실어 blob 으로 받아 새 탭에서 표시(PDF/이미지 바로 보임). 일반 링크는 401.
async function openAttachment(att: { id: number; original_name: string; content_type?: string | null }) {
  if (!detail.value) return
  try {
    const res = await announcementApi.downloadAttachment(detail.value.id, att.id)
    const blob = new Blob([res.data as BlobPart], att.content_type ? { type: att.content_type } : undefined)
    const url = window.URL.createObjectURL(blob)
    window.open(url, '_blank')
    setTimeout(() => window.URL.revokeObjectURL(url), 60_000)
  } catch {
    error('첨부파일을 열지 못했습니다')
  }
}
const showForm = ref(false)
const editTarget = ref<AnnouncementDetail | null>(null)
const receipts = ref<ReadReceiptList | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await announcementApi.list({
      page: page.value, size: size.value,
      q: q.value || undefined,
      include_inactive: isManager.value ? includeInactive.value : undefined,
    })
    items.value = res.items
    total.value = res.total
  } catch (e: any) {
    error(e?.response?.data?.detail || '목록 로드 실패')
  } finally {
    loading.value = false
  }
}

const openingId = ref<number | null>(null)
async function open(id: number) {
  if (openingId.value !== null) return  // 연타/중복요청 방지(로딩 중 재클릭 무시)
  openingId.value = id
  try {
    const row = items.value.find((i) => i.id === id)
    const wasUnread = row?.is_unread === true
    detail.value = await announcementApi.detail(id)
    // 열람 → 미열람 표시 즉시 해제 + 탭 배지 갱신(새로고침 없이)
    if (row) row.is_unread = false
    if (wasUnread) window.dispatchEvent(new Event('xm:announce-refresh'))
  } catch (e: any) {
    error(e?.response?.data?.detail || '공지 로드 실패')
  } finally {
    openingId.value = null
  }
}

function fmtDate(s: string) {
  return s ? s.slice(0, 10) : ''
}

function targetLabel(codes?: string[] | null) {
  if (!codes || codes.length === 0) return '전체'
  return codes.map(departmentLabel).join(', ')
}

function newAnnouncement() {
  editTarget.value = null
  showForm.value = true
}

function editAnnouncement() {
  editTarget.value = detail.value
  showForm.value = true
}

async function onSaved() {
  showForm.value = false
  const openId = editTarget.value?.id || detail.value?.id
  await load()
  if (openId) await open(openId)
}

async function removeAnnouncement() {
  if (!detail.value) return
  if (!confirm(`공지 '${detail.value.title}' 를 삭제할까요? (보관 처리)`)) return
  try {
    await announcementApi.remove(detail.value.id, false)
    success('공지 삭제됨(보관)')
    detail.value = null
    await load()
    // 삭제(보관)된 공지가 미열람이었다면 탭 배지도 즉시 갱신
    window.dispatchEvent(new Event('xm:announce-refresh'))
  } catch (e: any) {
    error(e?.response?.data?.detail || '삭제 실패')
  }
}

async function showReceipts() {
  if (!detail.value) return
  try {
    receipts.value = await announcementApi.reads(detail.value.id)
  } catch (e: any) {
    error(e?.response?.data?.detail || '읽음 현황 로드 실패')
  }
}

// 공지 출력(인쇄) — 볼 수 있는 사람 누구나. 인쇄용 새 창을 열어 window.print()
function printAnnouncement() {
  const d = detail.value
  if (!d) return
  const esc = (s: any) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const atts = (d.attachments || []).map((a) => `<li>📎 ${esc(a.original_name)}</li>`).join('')
  const html = `<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>${esc(d.title)}</title>
<style>
  *{box-sizing:border-box}
  body{font-family:'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif;color:#1a2432;margin:28px;line-height:1.7}
  h1{font-size:20px;margin:0 0 6px;font-weight:700}
  .meta{font-size:12px;color:#6b7280;border-bottom:2px solid #e5e7eb;padding-bottom:12px;margin-bottom:18px}
  .body{font-size:14px}
  .body img{max-width:100%;height:auto}
  .body mark{padding:0 2px;color:inherit;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .body table{border-collapse:collapse}
  .body td,.body th{border:1px solid #d1d5db;padding:4px 8px}
  .att{margin-top:22px;border-top:1px solid #e5e7eb;padding-top:10px}
  .att-title{font-weight:600;color:#6b7280;font-size:12px;margin-bottom:4px}
  .att ul{margin:0;padding-left:18px;font-size:13px}
  @media print{ body{margin:12mm} }
</style></head><body>
  <h1>${d.is_pinned ? '📌 ' : ''}${esc(d.title)}</h1>
  <div class="meta">${esc(d.author_name || '-')} · ${esc(fmtDate(d.published_at))} · 대상 ${esc(targetLabel(d.target_departments))}</div>
  <div class="body">${d.body || ''}</div>
  ${atts ? `<div class="att"><div class="att-title">첨부파일</div><ul>${atts}</ul></div>` : ''}
  <script>window.onload=function(){window.print()}<\/script>
</body></html>`
  const w = window.open('', '_blank')
  if (!w) { error('팝업이 차단되었습니다. 브라우저에서 팝업을 허용해 주세요.'); return }
  w.document.write(html)
  w.document.close()
}

const debouncedSearch = useDebouncedSearch(() => onSearch())
function onSearch() {
  page.value = 1
  load()
}

const route = useRoute()
// 종 알림 딥링크(/announcements?open=id): 해당 공지를 바로 상세로 연다
async function handleOpenQuery() {
  const raw = route.query.open
  const id = raw ? Number(raw) : NaN
  if (id && !Number.isNaN(id)) await open(id)
}
watch(() => route.query.open, () => { handleOpenQuery() })

onMounted(async () => {
  loadDepartments()
  await load()
  handleOpenQuery()
})
</script>

<template>
  <div class="max-w-screen-xl mx-auto px-4 py-6">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-xl font-bold text-gray-800">공지사항</h1>
        <p class="text-xs text-gray-500 mt-0.5">회사 공지 · 부서 대상 · 읽음 확인</p>
      </div>
      <button v-if="isManager" class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700" @click="newAnnouncement">+ 새 공지</button>
    </div>

    <!-- 필터 -->
    <div class="bg-white rounded-lg shadow border p-3 mb-4 flex flex-wrap items-center gap-2">
      <input v-model="q" @keyup.enter="onSearch" @input="debouncedSearch" placeholder="제목 검색" class="inp flex-1 min-w-[12rem]" />
      <button class="px-3 py-1.5 bg-gray-600 text-white text-sm rounded-md hover:bg-gray-700" @click="onSearch">검색</button>
      <label v-if="isManager" class="inline-flex items-center gap-1.5 text-sm text-gray-600 ml-2">
        <input type="checkbox" v-model="includeInactive" @change="onSearch" /> 보관 포함
      </label>
    </div>

    <!-- 모바일 카드 목록 (lg 미만 전용) -->
    <div class="lg:hidden space-y-2">
      <div v-if="loading" class="bg-white rounded-lg shadow border p-6 text-center text-gray-400 text-sm">로딩 중...</div>
      <div v-else-if="!items.length" class="bg-white rounded-lg shadow border p-6 text-center text-gray-400 text-sm">공지가 없습니다</div>
      <button
        v-for="a in items"
        :key="'m' + a.id"
        type="button"
        class="w-full text-left bg-white rounded-lg shadow border p-3 active:bg-blue-50 transition-opacity"
        :class="{ 'bg-amber-50/40': !a.is_active, 'opacity-50 pointer-events-none': openingId === a.id }"
        @click="open(a.id)"
      >
        <div class="flex items-start gap-1.5">
          <span v-if="a.is_pinned" title="고정">📌</span>
          <span class="flex-1 break-words" :class="a.is_unread ? 'font-bold text-gray-900' : 'text-gray-700'">{{ a.title }}</span>
          <span v-if="a.is_unread" class="mt-1.5 shrink-0 inline-block w-1.5 h-1.5 rounded-full bg-red-500"></span>
        </div>
        <div class="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500">
          <span>{{ targetLabel(a.target_departments) }}</span>
          <span>{{ a.author_name || '-' }}</span>
          <span>{{ fmtDate(a.published_at) }}</span>
          <span v-if="a.attachment_count">📎{{ a.attachment_count }}</span>
          <span v-if="isManager">읽음 {{ a.read_count }}</span>
          <span v-if="!a.is_active" class="text-amber-600">보관</span>
        </div>
      </button>
      <Pagination v-if="total > 0" class="bg-white rounded-lg shadow border" :total="total" :page-size="size" :current-page="page"
                  @update:current-page="(p) => { page = p; load() }"
                  @update:page-size="(s) => { size = s; page = 1; load() }" />
    </div>

    <!-- 목록 (데스크톱 테이블, lg 이상 전용 — 기존 UI 보존) -->
    <div class="hidden lg:block bg-white rounded-lg shadow border overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400 text-sm">로딩 중...</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 text-gray-500 text-xs">
          <tr>
            <th class="px-3 py-2 text-left w-10"></th>
            <th class="px-3 py-2 text-left">제목</th>
            <th class="px-3 py-2 text-left w-28">대상</th>
            <th class="px-3 py-2 text-left w-24">작성자</th>
            <th class="px-3 py-2 text-center w-24">발행일</th>
            <th v-if="isManager" class="px-3 py-2 text-center w-16">읽음</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in items" :key="a.id"
              class="border-t hover:bg-blue-50 cursor-pointer"
              :class="{ 'bg-amber-50/40': !a.is_active, 'opacity-50 pointer-events-none': openingId === a.id }"
              @click="open(a.id)">
            <td class="px-3 py-2 text-center">
              <span v-if="a.is_pinned" title="고정">📌</span>
            </td>
            <td class="px-3 py-2">
              <span :class="a.is_unread ? 'font-bold text-gray-900' : 'text-gray-700'">{{ a.title }}</span>
              <span v-if="a.is_unread" class="ml-1 align-middle inline-block w-1.5 h-1.5 rounded-full bg-red-500"></span>
              <span v-if="a.attachment_count" class="ml-1 text-xs text-gray-400">📎{{ a.attachment_count }}</span>
              <span v-if="!a.is_active" class="ml-1 text-[10px] text-amber-600">(보관)</span>
            </td>
            <td class="px-3 py-2 text-gray-500 text-xs">{{ targetLabel(a.target_departments) }}</td>
            <td class="px-3 py-2 text-gray-500 text-xs">{{ a.author_name || '-' }}</td>
            <td class="px-3 py-2 text-center text-gray-500 text-xs">{{ fmtDate(a.published_at) }}</td>
            <td v-if="isManager" class="px-3 py-2 text-center text-gray-500 text-xs">{{ a.read_count }}</td>
          </tr>
          <tr v-if="!items.length">
            <td :colspan="isManager ? 6 : 5" class="px-3 py-8 text-center text-gray-400">공지가 없습니다</td>
          </tr>
        </tbody>
      </table>
      <Pagination v-if="total > 0" :total="total" :page-size="size" :current-page="page"
                  @update:current-page="(p) => { page = p; load() }"
                  @update:page-size="(s) => { size = s; page = 1; load() }" />
    </div>

    <!-- 상세 모달 (바깥 클릭으로 닫히지 않음 — 닫기[✕]로만) -->
    <div v-if="detail" class="fixed inset-0 bg-black/40 flex items-center justify-center z-40 p-4">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[92vh]">
        <div class="flex items-start justify-between px-5 py-3 border-b">
          <div>
            <h3 class="text-lg font-semibold text-gray-800">
              <span v-if="detail.is_pinned">📌 </span>{{ detail.title }}
            </h3>
            <p class="text-xs text-gray-400 mt-0.5">
              {{ detail.author_name || '-' }} · {{ fmtDate(detail.published_at) }}
              · 대상 {{ targetLabel(detail.target_departments) }}
              <span v-if="!detail.is_active" class="text-amber-600">· 보관됨</span>
            </p>
          </div>
          <button @click="detail = null" class="text-gray-400 hover:text-gray-600" aria-label="닫기">✕</button>
        </div>

        <div class="px-5 py-4 overflow-y-auto">
          <div class="announce-body max-w-none text-sm text-gray-800" v-html="detail.body"></div>

          <div v-if="detail.attachments.length" class="mt-4 border-t pt-3">
            <div class="text-xs font-semibold text-gray-500 mb-1">첨부파일</div>
            <ul class="space-y-1">
              <li v-for="att in detail.attachments" :key="att.id">
                <button type="button" @click="openAttachment(att)" class="text-sm text-blue-600 hover:underline text-left">
                  📎 {{ att.original_name }}
                </button>
              </li>
            </ul>
          </div>
        </div>

        <div class="px-5 py-3 border-t flex items-center justify-between">
          <div class="flex items-center gap-3">
            <!-- 출력: 볼 수 있는 사람 누구나 -->
            <button class="px-3 py-1.5 text-sm text-gray-700 border rounded hover:bg-gray-50" @click="printAnnouncement">🖨 출력</button>
            <button v-if="isManager" class="text-sm text-gray-600 hover:underline" @click="showReceipts">읽음 현황 ({{ detail.read_count }})</button>
          </div>
          <div v-if="isManager" class="flex gap-2">
            <button class="px-3 py-1.5 text-sm text-gray-700 border rounded hover:bg-gray-50" @click="editAnnouncement">수정</button>
            <button class="px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded hover:bg-red-50" @click="removeAnnouncement">삭제</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 읽음 현황 모달 -->
    <div v-if="receipts" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" @click.self="receipts = null">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-md flex flex-col max-h-[85vh]">
        <div class="flex items-center justify-between px-5 py-3 border-b">
          <h3 class="text-base font-semibold text-gray-800">읽음 현황</h3>
          <button @click="receipts = null" class="text-gray-400 hover:text-gray-600" aria-label="닫기">✕</button>
        </div>
        <div class="px-5 py-4 overflow-y-auto text-sm">
          <p class="text-gray-600 mb-3">대상 {{ receipts.total_targeted }}명 중 <b class="text-blue-700">{{ receipts.read_count }}명</b> 읽음</p>
          <div class="mb-3">
            <div class="text-xs font-semibold text-gray-500 mb-1">읽음</div>
            <ul class="space-y-0.5">
              <li v-for="r in receipts.read" :key="'r' + r.user_id" class="flex justify-between">
                <span>{{ r.name }} <span class="text-xs text-gray-400">{{ departmentLabel(r.department) }}</span></span>
                <span class="text-xs text-gray-400">{{ fmtDate(r.read_at) }}</span>
              </li>
              <li v-if="!receipts.read.length" class="text-gray-400 text-xs">아직 읽은 사람이 없습니다</li>
            </ul>
          </div>
          <div>
            <div class="text-xs font-semibold text-gray-500 mb-1">안 읽음</div>
            <ul class="space-y-0.5">
              <li v-for="u in receipts.unread" :key="'u' + u.user_id" class="text-gray-600">
                {{ u.name }} <span class="text-xs text-gray-400">{{ departmentLabel(u.department) }}</span>
              </li>
              <li v-if="!receipts.unread.length" class="text-gray-400 text-xs">전원 읽음 완료</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- 작성/수정 모달 -->
    <AnnouncementFormModal v-if="showForm" :announcement="editTarget" @close="showForm = false" @saved="onSaved" />
  </div>
</template>

<style scoped>
.inp { @apply px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500; }

/* 공지 본문(리치텍스트 HTML) — 문단 간격 + 빈 문단(빈 줄) 보이도록.
   Tailwind preflight 가 p margin 을 0으로 리셋하므로 여기서 복원. */
.announce-body :deep(p) { margin: 0; line-height: 1.7; }
.announce-body :deep(p:empty) { min-height: 1.1em; }   /* 빈 문단 = 한 줄 공백 */
.announce-body :deep(ul) { list-style: disc; padding-left: 1.4em; margin: 0.3em 0; }
.announce-body :deep(ol) { list-style: decimal; padding-left: 1.4em; margin: 0.3em 0; }
.announce-body :deep(strong) { font-weight: 700; }
.announce-body :deep(a) { color: #2563eb; text-decoration: underline; }
/* 새 에디터 서식: 형광펜 / 본문 이미지 */
.announce-body :deep(mark) { padding: 0 2px; border-radius: 2px; color: inherit; }
.announce-body :deep(img) { max-width: 100%; height: auto; border-radius: 6px; margin: 0.5rem 0; }
</style>
