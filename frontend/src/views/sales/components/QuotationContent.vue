<template>
  <div class="p-4 sm:p-6">
    <!-- 헤더 -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
      <h2 class="text-xl font-bold text-gray-900">견적서 관리</h2>
      <button
        @click="showFormModal = true; editingDoc = null"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
      >
        + 신규 견적서
      </button>
    </div>

    <!-- 필터 -->
    <div class="bg-white rounded-lg shadow-sm border p-4 mb-4">
      <div class="flex flex-wrap gap-3 items-center">
        <div class="relative">
          <input
            v-model="customerFilterSearch"
            @focus="showCustomerFilter = true; highlightedIndex = 0"
            @input="showCustomerFilter = true; highlightedIndex = 0"
            @blur="hideCustomerFilterDelayed"
            @keydown.down.prevent="moveHighlight(1)"
            @keydown.up.prevent="moveHighlight(-1)"
            @keydown.enter.prevent="handleEnter"
            @keydown.escape="showCustomerFilter = false"
            class="border rounded-md px-3 py-2 text-sm w-48"
            :placeholder="filters.customer_id ? customers.find(c => c.id === filters.customer_id)?.partner_name || '고객사' : '고객사 검색...'"
          />
          <div v-if="showCustomerFilter && filteredCustomerOptions.length > 0"
            class="absolute z-10 w-64 mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
            <div @mousedown.prevent="filters.customer_id = undefined; customerFilterSearch = ''; showCustomerFilter = false; loadData()"
              class="px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 text-gray-400">전체 고객사</div>
            <div v-for="(c, idx) in filteredCustomerOptions" :key="c.id"
              @mousedown.prevent="filters.customer_id = c.id; customerFilterSearch = c.partner_name; showCustomerFilter = false; loadData()"
              @mouseenter="highlightedIndex = idx"
              class="px-3 py-2 text-sm cursor-pointer"
              :class="highlightedIndex === idx ? 'bg-blue-100' : 'hover:bg-blue-50'">
              {{ c.partner_name }}
            </div>
          </div>
        </div>
        <select v-model="filters.status" @change="loadData" class="border rounded-md px-3 py-2 text-sm">
          <option :value="undefined">전체 상태</option>
          <option value="DRAFT">작성중</option>
          <option value="SENT">발송완료</option>
          <option value="CONFIRMED">확정</option>
          <option value="CANCELLED">취소</option>
        </select>
        <input
          v-model="filters.keyword"
          @input="debouncedLoad"
          placeholder="문서번호 검색..."
          class="border rounded-md px-3 py-2 text-sm flex-1 min-w-[200px]"
        />
        <label class="inline-flex items-center text-xs text-gray-500 cursor-pointer select-none">
          <input type="checkbox" v-model="showAllVersions" @change="currentPage = 1; loadData()" class="w-3.5 h-3.5 mr-1.5 rounded" />
          이전 버전 포함
        </label>
        <button @click="resetFilters" type="button"
          class="px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 whitespace-nowrap">
          🔄 초기화
        </button>
      </div>
    </div>

    <!-- 다중 선택 액션 바 -->
    <div v-if="selectedIds.size > 0" class="mb-3 flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
      <span class="text-sm text-blue-700 font-medium">{{ selectedIds.size }}건 선택</span>
      <button @click="startConvertMultiple"
        class="px-3 py-1 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700">
        선택 항목 → PI 전환
      </button>
      <button @click="selectedIds.clear()" class="text-xs text-gray-500 hover:text-gray-700">선택 해제</button>
    </div>

    <!-- 목록 -->
    <div class="bg-white rounded-lg shadow-sm border overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400">로딩 중...</div>
      <div v-else-if="documents.length === 0" class="p-8 text-center text-gray-400">
        <p>견적서가 없습니다.</p>
      </div>
      <div v-else>
      <!-- 모바일 카드 목록 (lg 미만 전용) -->
      <div class="lg:hidden divide-y divide-gray-100">
        <div v-for="doc in documents" :key="'m' + doc.id" class="p-3 active:bg-blue-50 cursor-pointer" @click="openDetail(doc)">
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-medium text-blue-600 truncate">{{ doc.document_number }}</span>
            <span :class="statusClass(doc.status)" class="px-2 py-0.5 text-[11px] font-medium rounded-full whitespace-nowrap">{{ statusLabel(doc.status) }}</span>
          </div>
          <div class="mt-1 text-sm text-gray-900">{{ doc.customer?.partner_name || '-' }}</div>
          <div class="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-gray-500">
            <span v-if="doc.representative_product" class="font-mono truncate max-w-[55%]">{{ doc.representative_product }}<span v-if="(doc.item_count || 0) > 1"> 외 {{ (doc.item_count || 1) - 1 }}건</span></span>
            <span>{{ formatDate(doc.document_date) }}</span>
            <span class="font-medium text-gray-700">{{ doc.currency }} {{ formatNumber(doc.total_amount, doc.currency) }}</span>
          </div>
        </div>
      </div>
      <!-- 데스크톱 테이블 (lg 이상 전용 — 기존 UI 보존) -->
      <table class="min-w-full divide-y divide-gray-200 hidden lg:table">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-3 py-3 w-8">
              <input type="checkbox" @change="toggleSelectAll" :checked="isAllSelected" class="w-4 h-4 rounded" />
            </th>
            <th @click="toggleSort('document_number')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">Q No.{{ sortIndicator('document_number') }}</th>
            <th @click="toggleSort('document_date')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">날짜{{ sortIndicator('document_date') }}</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">고객사</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">제품</th>
            <th @click="toggleSort('total_amount')" class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">금액{{ sortIndicator('total_amount') }}</th>
            <th @click="toggleSort('status')" class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">상태{{ sortIndicator('status') }}</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">액션</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          <tr v-for="doc in documents" :key="doc.id" class="hover:bg-gray-50"
            :class="selectedIds.has(doc.id) ? 'bg-blue-50' : ''">
            <td class="px-3 py-3">
              <input type="checkbox" :checked="selectedIds.has(doc.id)" @change="toggleSelect(doc.id)"
                class="w-4 h-4 rounded" />
            </td>
            <td class="px-4 py-3 text-sm font-medium text-blue-600 cursor-pointer" @click="openDetail(doc)">
              {{ doc.document_number }}
            </td>
            <td class="px-4 py-3 text-sm text-gray-600">{{ formatDate(doc.document_date) }}</td>
            <td class="px-4 py-3 text-sm text-gray-900">{{ doc.customer?.partner_name || '-' }}</td>
            <td class="px-4 py-3 text-xs text-gray-600">
              <div v-if="doc.representative_product" class="max-w-[200px]">
                <span class="font-mono truncate block" :title="doc.representative_product">{{ doc.representative_product }}</span>
                <span v-if="(doc.item_count || 0) > 1" class="text-gray-400 text-[10px]">외 {{ (doc.item_count || 1) - 1 }}건</span>
              </div>
              <span v-else class="text-gray-400">-</span>
            </td>
            <td class="px-4 py-3 text-sm text-right font-medium">
              {{ doc.currency }} {{ formatNumber(doc.total_amount, doc.currency) }}
            </td>
            <td class="px-4 py-3 text-center">
              <span :class="statusClass(doc.status)" class="inline-block px-2 py-1 text-xs font-medium rounded-full whitespace-nowrap">
                {{ statusLabel(doc.status) }}
              </span>
            </td>
            <td class="px-4 py-3">
              <RowActionMenu :actions="quotationActions(doc)" />
            </td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>

    <!-- 페이지네이션 -->
    <div v-if="totalPages > 1" class="flex items-center justify-between px-4 py-3 bg-white border-t">
      <span class="text-xs text-gray-500">총 {{ totalCount }}건 중 {{ (currentPage - 1) * PAGE_SIZE + 1 }}~{{ Math.min(currentPage * PAGE_SIZE, totalCount) }}건</span>
      <div class="flex items-center gap-1">
        <button @click="goToPage(1)" :disabled="currentPage === 1"
          class="px-2 py-1 text-xs border rounded hover:bg-gray-50 disabled:opacity-30">«</button>
        <button @click="goToPage(currentPage - 1)" :disabled="currentPage === 1"
          class="px-2 py-1 text-xs border rounded hover:bg-gray-50 disabled:opacity-30">‹</button>
        <template v-for="p in pageNumbers" :key="p">
          <button @click="goToPage(p)"
            :class="p === currentPage ? 'bg-blue-600 text-white border-blue-600' : 'hover:bg-gray-50'"
            class="px-3 py-1 text-xs border rounded">{{ p }}</button>
        </template>
        <button @click="goToPage(currentPage + 1)" :disabled="currentPage === totalPages"
          class="px-2 py-1 text-xs border rounded hover:bg-gray-50 disabled:opacity-30">›</button>
        <button @click="goToPage(totalPages)" :disabled="currentPage === totalPages"
          class="px-2 py-1 text-xs border rounded hover:bg-gray-50 disabled:opacity-30">»</button>
      </div>
    </div>

    <!-- 생성/편집 모달 -->
    <SalesDocumentFormModal
      v-if="showFormModal"
      :document="editingDoc"
      document-type="QUOTATION"
      :preset-customer-id="presetCustomerId || undefined"
      :preset-activity-id="presetActivityId || undefined"
      :copy-from-doc-id="copyFromDocId || undefined"
      @close="onFormClose"
      @saved="handleSaved"
      @navigate="(payload) => $emit('navigate-doc', payload)"
    />

    <!-- PDF 미리보기 모달 -->
    <PdfPreviewModal
      v-if="pdfPreview"
      :doc-id="pdfPreview.id"
      :doc-number="pdfPreview.number"
      doc-type="QUOTATION"
      :lang="pdfPreview.lang"
      :version="pdfPreview.version"
      @close="pdfPreview = null"
    />

    <!-- PI 전환 모달 -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showConvertModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" >
          <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <h3 class="text-lg font-bold mb-4">PI로 전환</h3>
            <p class="text-sm text-gray-600 mb-4">
              <template v-if="convertSourceIds.length === 1 && convertingDoc">
                {{ convertingDoc.document_number }} → PI 전환
              </template>
              <template v-else>
                {{ convertSourceIds.length }}건의 견적서 → 통합 PI 전환
              </template>
            </p>
            <div class="space-y-3">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">PO 번호 (선택)</label>
                <input v-model="convertForm.customer_po_number" class="w-full border rounded-md px-3 py-2 text-sm"
                  placeholder="PO 번호 또는 메일 주문 참조" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">PO 날짜 (선택)</label>
                <input v-model="convertForm.customer_po_date" type="date" class="w-full border rounded-md px-3 py-2 text-sm" />
              </div>

              <!-- PO 파일 첨부 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">PO 첨부파일 (선택)</label>
                <input
                  ref="poFileInput"
                  type="file"
                  multiple
                  accept=".pdf,.xlsx,.xls,.doc,.docx,.png,.jpg,.jpeg"
                  @change="onPoFilesSelected"
                  class="w-full border rounded-md px-3 py-2 text-sm"
                />
                <ul v-if="poFiles.length > 0" class="mt-2 space-y-1">
                  <li v-for="(f, idx) in poFiles" :key="idx" class="flex items-center justify-between bg-gray-50 rounded px-2 py-1 text-xs">
                    <span class="truncate">📎 {{ f.name }}</span>
                    <button @click="removePoFile(idx)" class="text-red-500 hover:text-red-700 ml-2">삭제</button>
                  </li>
                </ul>
              </div>

              <p class="text-xs text-gray-400">※ PO 없이 메일 주문인 경우 비워두거나 참조 메모를 기입하세요</p>

              <!-- 견적 대용 PI: 매출/미수 집계 제외 -->
              <label class="flex items-start gap-2 p-2 rounded-md border border-orange-200 bg-orange-50/50 cursor-pointer">
                <input type="checkbox" v-model="convertForm.is_quote_only" class="mt-0.5 w-4 h-4 rounded" />
                <span class="text-xs">
                  <span class="font-medium text-orange-700">견적 대용 PI (집계 제외)</span>
                  <span class="block text-gray-500 mt-0.5">실주문이 아니라 견적서 대용으로 보내는 PI면 체크하세요. 매출·미수(미실현/미입금) 집계에서 제외됩니다.</span>
                </span>
              </label>
            </div>
            <div class="flex justify-end gap-2 mt-6">
              <button @click="cancelConvert" class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">취소</button>
              <button @click="executeConvert" :disabled="converting" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {{ converting ? '전환 중...' : 'PI 전환' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { salesDocumentApi, type SalesDocument } from '@/api/salesDocument'
import { formatAmount } from '@/api/price'
import { useToast } from '@/composables/useToast'
import { useAuth } from '@/stores/auth'
import SalesDocumentFormModal from './SalesDocumentFormModal.vue'
import PdfPreviewModal from './PdfPreviewModal.vue'
import RowActionMenu, { type RowAction } from '@/components/common/RowActionMenu.vue'
import apiClient from '@/api/client'

interface Props {
  initialCustomerId?: number
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'data-changed'): void
  (e: 'navigate-doc', payload: { docId: number; docType: string }): void
}>()
const { showToast } = useToast()
const { isAdmin } = useAuth()  // 삭제는 관리자만

// 상태
const loading = ref(false)
const documents = ref<SalesDocument[]>([])
const customers = ref<{ id: number; partner_name: string }[]>([])
const showFormModal = ref(false)
const editingDoc = ref<SalesDocument | null>(null)
const presetCustomerId = ref<number | null>(null)
const presetActivityId = ref<number | null>(null)
const copyFromDocId = ref<number | null>(null)
const pdfPreview = ref<{ id: number; number: string; lang: 'ko' | 'en'; version?: number } | null>(null)
const PAGE_SIZE = 20
const currentPage = ref(1)
const totalCount = ref(0)
const sortKey = ref('document_date')
const sortDesc = ref(true)

function toggleSort(key: string) {
  if (sortKey.value === key) sortDesc.value = !sortDesc.value
  else { sortKey.value = key; sortDesc.value = true }
  currentPage.value = 1
  loadData()
}
function sortIndicator(key: string) {
  if (sortKey.value !== key) return ''
  return sortDesc.value ? ' ↓' : ' ↑'
}
const totalPages = computed(() => Math.ceil(totalCount.value / PAGE_SIZE))
const pageNumbers = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const pages: number[] = []
  let start = Math.max(1, current - 2)
  let end = Math.min(total, start + 4)
  start = Math.max(1, end - 4)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})
const showAllVersions = ref(false)
const showConvertModal = ref(false)
const convertingDoc = ref<SalesDocument | null>(null)
const convertForm = ref({ customer_po_number: '', customer_po_date: '', is_quote_only: false })
const convertSourceIds = ref<number[]>([])  // 다중 전환용

// 다중 선택
const selectedIds = ref(new Set<number>())
const isAllSelected = computed(() => documents.value.length > 0 && documents.value.every(d => selectedIds.value.has(d.id)))
function toggleSelect(id: number) {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id)
  else selectedIds.value.add(id)
}
function toggleSelectAll() {
  if (isAllSelected.value) selectedIds.value.clear()
  else documents.value.forEach(d => selectedIds.value.add(d.id))
}
function startConvertMultiple() {
  const ids = Array.from(selectedIds.value)
  if (ids.length === 0) return
  convertSourceIds.value = ids
  convertForm.value = { customer_po_number: '', customer_po_date: '', is_quote_only: false }
  poFiles.value = []
  showConvertModal.value = true
  convertingDoc.value = null  // 다중 모드
}
const poFiles = ref<File[]>([])
const poFileInput = ref<HTMLInputElement | null>(null)
const converting = ref(false)

const customerFilterSearch = ref('')
const showCustomerFilter = ref(false)
const highlightedIndex = ref(0)

function moveHighlight(delta: number) {
  const list = filteredCustomerOptions.value
  if (list.length === 0) return
  highlightedIndex.value = (highlightedIndex.value + delta + list.length) % list.length
}

function handleEnter() {
  const list = filteredCustomerOptions.value
  if (list.length === 1) {
    filters.value.customer_id = list[0]!.id; customerFilterSearch.value = list[0]!.partner_name; showCustomerFilter.value = false; loadData()
    return
  }
  if (list.length > 0 && highlightedIndex.value >= 0) {
    const c = list[highlightedIndex.value]!
    filters.value.customer_id = c.id; customerFilterSearch.value = c.partner_name; showCustomerFilter.value = false; loadData()
  }
}

function hideCustomerFilterDelayed() { setTimeout(() => { showCustomerFilter.value = false }, 200) }
const filteredCustomerOptions = computed(() => {
  if (!customerFilterSearch.value) return customers.value
  const q = customerFilterSearch.value.toLowerCase()
  return customers.value.filter(c => c.partner_name.toLowerCase().includes(q))
})

const filters = ref<{
  customer_id?: number
  status?: string
  keyword?: string
}>({
  customer_id: props.initialCustomerId,
})

// 데이터 로드
async function loadData() {
  loading.value = true
  try {
    const res = await salesDocumentApi.getList({
      document_type: 'QUOTATION',
      ...filters.value,
      skip: (currentPage.value - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
      order_by: sortKey.value,
      order_desc: sortDesc.value,
      include_old_versions: showAllVersions.value || undefined,
    })
    documents.value = res.data.items
    totalCount.value = res.data.total || 0
  } catch (err) {
    showToast('견적서 목록을 불러오는데 실패했습니다', 'error')
  } finally {
    loading.value = false
  }
}

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadData()
}

async function loadCustomers() {
  try {
    const res = await apiClient.get('/partners', { params: { is_customer: true, limit: 500 } })
    customers.value = (res.data.items || res.data).map((c: any) => ({ id: c.id, partner_name: c.partner_name }))
  } catch { /* ignore */ }
}

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedLoad() {
  currentPage.value = 1
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadData, 300)
}

function resetFilters() {
  filters.value = { customer_id: undefined, status: undefined, keyword: undefined }
  customerFilterSearch.value = ''
  loadData()
}

// 액션
async function openDetail(doc: SalesDocument) {
  try {
    const res = await salesDocumentApi.getById(doc.id)
    editingDoc.value = res.data
    showFormModal.value = true
  } catch {
    showToast('문서 상세 정보를 불러오는데 실패했습니다', 'error')
  }
}

async function downloadExcel(doc: SalesDocument) {
  try {
    const res = await salesDocumentApi.exportExcel(doc.id)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `${doc.document_number}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
    showToast('엑셀 파일을 다운로드했습니다', 'success')
  } catch {
    showToast('다운로드에 실패했습니다', 'error')
  }
}

function openPdfPreview(doc: SalesDocument, lang: 'ko' | 'en') {
  pdfPreview.value = {
    id: doc.id,
    number: doc.document_number,
    lang,
    version: doc.version,
  }
}

// 고객사 국적 기준으로 PDF 언어 버튼 표시 여부 결정
// - country_code === 'KR' 또는 trade_type === 'DOMESTIC' → 국내 (한글만)
// - 그 외 (해외) → 영문만
// - 정보 누락 (둘 다 없음) → 둘 다 표시 (안전 기본값)
function isDomesticCustomer(doc: any): boolean | null {
  const c = doc.customer
  if (!c) return null
  if (c.country_code) return c.country_code === 'KR'
  if (c.trade_type) return c.trade_type === 'DOMESTIC'
  return null
}
function showKoPdf(doc: any): boolean {
  const d = isDomesticCustomer(doc)
  return d === null || d === true
}
function showEnPdf(doc: any): boolean {
  const d = isDomesticCustomer(doc)
  return d === null || d === false
}

// 견적서 행 액션 메뉴 구성
function quotationActions(doc: SalesDocument): RowAction[] {
  return [
    { label: 'PDF (한글)', icon: '📄', show: showKoPdf(doc), onClick: () => openPdfPreview(doc, 'ko') },
    { label: 'PDF (영문)', icon: '📄', show: showEnPdf(doc), onClick: () => openPdfPreview(doc, 'en') },
    { label: '엑셀', icon: '📊', onClick: () => downloadExcel(doc) },
    { label: 'PI 전환', icon: '🔄', show: doc.status === 'SENT' || doc.status === 'DRAFT', onClick: () => startConvert(doc) },
    { label: '발송', icon: '📤', show: doc.status === 'DRAFT', onClick: () => updateStatus(doc, 'SENT') },
    { divider: true },
    { label: '삭제', icon: '🗑', variant: 'danger', show: isAdmin.value, onClick: () => deleteDoc(doc) },
  ]
}

async function updateStatus(doc: SalesDocument, status: string) {
  try {
    await salesDocumentApi.updateStatus(doc.id, status)
    showToast('상태가 변경되었습니다', 'success')
    loadData()
    emit('data-changed')
  } catch {
    showToast('상태 변경에 실패했습니다', 'error')
  }
}

function startConvert(doc: SalesDocument) {
  convertingDoc.value = doc
  convertSourceIds.value = [doc.id]
  convertForm.value = { customer_po_number: '', customer_po_date: '', is_quote_only: false }
  poFiles.value = []
  showConvertModal.value = true
}

function cancelConvert() {
  showConvertModal.value = false
  poFiles.value = []
  converting.value = false
}

function onPoFilesSelected(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files) {
    poFiles.value = [...poFiles.value, ...Array.from(target.files)]
    target.value = ''
  }
}

function removePoFile(idx: number) {
  poFiles.value.splice(idx, 1)
}

async function executeConvert() {
  if (convertSourceIds.value.length === 0) return
  converting.value = true
  try {
    const data: any = {}
    if (convertForm.value.customer_po_number) data.customer_po_number = convertForm.value.customer_po_number
    if (convertForm.value.customer_po_date) data.customer_po_date = convertForm.value.customer_po_date
    if (convertForm.value.is_quote_only) data.is_quote_only = true

    // N:M 전환 API 사용 (단일/다중 모두 동일)
    const res = await salesDocumentApi.convertMultiple(convertSourceIds.value, data)
    const newDocId = res.data?.id

    // PO 파일 업로드 (있는 경우)
    if (newDocId && poFiles.value.length > 0) {
      for (const file of poFiles.value) {
        try {
          await salesDocumentApi.uploadPoAttachment(newDocId, file)
        } catch {
          showToast(`${file.name} 업로드에 실패했습니다`, 'error')
        }
      }
    }

    const count = convertSourceIds.value.length
    showToast(`견적서 ${count}건이 PI로 전환되었습니다`, 'success')
    selectedIds.value.clear()
    cancelConvert()
    loadData()
    emit('data-changed')
  } catch {
    showToast('PI 전환에 실패했습니다', 'error')
  } finally {
    converting.value = false
  }
}

function onFormClose() {
  showFormModal.value = false
  presetCustomerId.value = null
  presetActivityId.value = null
  copyFromDocId.value = null
}

function handleSaved() {
  showFormModal.value = false
  presetCustomerId.value = null
  presetActivityId.value = null
  copyFromDocId.value = null
  loadData()
  emit('data-changed')
}

async function deleteDoc(doc: SalesDocument) {
  if (!confirm(`${doc.document_number}을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) return
  try {
    await salesDocumentApi.delete(doc.id, true)
    showToast('삭제되었습니다', 'success')
    loadData()
    emit('data-changed')
  } catch (err: any) {
    showToast(err.response?.data?.detail || '삭제에 실패했습니다', 'error')
  }
}

// 유틸
function formatDate(d: string) { return d ? d.replace(/-/g, '.') : '-' }
// 통화 인식형 금액 표기 (원/엔/위안 정수, 달러/유로 2자리, 천 단위 콤마)
function formatNumber(n: number | null | undefined, currency = 'KRW') {
  if (n == null || isNaN(Number(n))) return '0'
  return formatAmount(Number(n), currency)
}
function statusLabel(s: string) {
  const map: Record<string, string> = { DRAFT: '작성중', SENT: '발송완료', CONFIRMED: '확정', CANCELLED: '취소' }
  return map[s] || s
}
function statusClass(s: string) {
  const map: Record<string, string> = {
    DRAFT: 'bg-gray-100 text-gray-700',
    SENT: 'bg-blue-100 text-blue-700',
    CONFIRMED: 'bg-green-100 text-green-700',
    CANCELLED: 'bg-red-100 text-red-700',
  }
  return map[s] || 'bg-gray-100 text-gray-700'
}

// 초기 로드
watch(() => props.initialCustomerId, (id) => {
  if (id) filters.value.customer_id = id
})

const route = useRoute()
const router = useRouter()

function handleQueryTriggers() {
  // new_quotation=1 → 신규 견적서 모달 오픈
  if (route.query.new_quotation === '1') {
    const customerId = route.query.customer_id ? Number(route.query.customer_id) : undefined
    const activityId = route.query.activity_id ? Number(route.query.activity_id) : undefined
    const copyDocId = route.query.copy_from_doc ? Number(route.query.copy_from_doc) : undefined
    editingDoc.value = null
    if (customerId) presetCustomerId.value = customerId
    if (activityId) presetActivityId.value = activityId
    if (copyDocId) copyFromDocId.value = copyDocId
    showFormModal.value = true
    router.replace({ path: route.path, query: { tab: 'quotations' } })
    return
  }

  // open_doc_id → 특정 견적서 모달 오픈 (quotations 탭일 때만 — 다른 탭과 동시 발화 방지)
  if (route.query.open_doc_id && route.query.tab === 'quotations') {
    const docId = Number(route.query.open_doc_id)
    if (docId) {
      openDocumentById(docId)
      router.replace({ path: route.path, query: { tab: 'quotations' } })
    }
  }
}

onMounted(async () => {
  await loadData()
  await loadCustomers()
  handleQueryTriggers()
})

// 쿼리 변화 감지 (탭 전환으로 이미 마운트된 상태에서 이동한 경우)
watch(() => route.query.new_quotation, (val) => {
  if (val === '1') handleQueryTriggers()
})
watch(() => route.query.open_doc_id, (val) => {
  if (val) handleQueryTriggers()
})

// 외부에서 특정 문서 ID로 모달 열기 (양방향 링크용)
async function openDocumentById(docId: number) {
  try {
    const res = await salesDocumentApi.getById(docId)
    editingDoc.value = res.data
    showFormModal.value = true
  } catch {
    showToast('문서를 불러오는데 실패했습니다', 'error')
  }
}

defineExpose({ loadData, openDocumentById })
</script>
