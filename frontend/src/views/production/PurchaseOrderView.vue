<template>
  <div class="p-6">
    <!-- 헤더 -->
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">발주서 관리</h1>
      <button
        @click="openCreateModal"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        발주서 등록
      </button>
    </div>

    <!-- 검색/필터 -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <!-- 키워드 검색 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">검색</label>
          <input
            v-model="filters.keyword"
            type="text"
            placeholder="발주번호, 비고"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            @keyup.enter="loadData"
            @input="debouncedSearch"
          />
        </div>

        <!-- 상태 필터 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">상태</label>
          <select
            v-model="filters.status"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            @change="loadData"
          >
            <option value="">전체</option>
            <option v-for="(label, key) in poStatusLabels" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>

        <!-- 공급업체 필터 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">공급업체</label>
          <select
            v-model="filters.supplier_id"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            @change="loadData"
          >
            <option value="">전체</option>
            <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>

        <!-- 발주일 범위 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">발주일</label>
          <div class="flex gap-2">
            <input
              v-model="filters.from_date"
              type="date"
              class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              @change="loadData"
            />
            <input
              v-model="filters.to_date"
              type="date"
              class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              @change="loadData"
            />
          </div>
        </div>
      </div>

      <div class="mt-4 flex justify-end">
        <button
          @click="resetFilters"
          class="px-4 py-2 text-gray-600 hover:text-gray-800"
        >
          필터 초기화
        </button>
        <button
          @click="loadData"
          class="ml-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          검색
        </button>
      </div>
    </div>

    <!-- 테이블 -->
    <!-- #8 선택 → 지출결의 묶기 바 -->
    <div v-if="selectedPoIds.size > 0" class="mb-3 flex items-center justify-between px-4 py-2.5 bg-emerald-50 border border-emerald-200 rounded-lg">
      <span class="text-sm text-emerald-800"><b>{{ selectedPoIds.size }}</b>건 선택됨 — 하나의 지출결의서로 묶어 집행 결재를 올립니다.</span>
      <div class="flex gap-2">
        <button @click="clearPoSelection" class="px-3 py-1 text-sm text-gray-600 border border-gray-300 rounded hover:bg-gray-100">선택 해제</button>
        <button @click="handleCreateDisbursement" :disabled="disbursing" class="px-3 py-1 text-sm bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50">
          {{ disbursing ? '생성 중…' : '💳 선택 항목 지출결의로 묶기' }}
        </button>
      </div>
    </div>

    <div class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-3 py-3 w-10 text-center"><input type="checkbox" :checked="allSelected" @change="toggleSelectAll" class="w-4 h-4 rounded cursor-pointer" title="전체 선택" /></th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">발주번호</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">공급업체</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">발주일</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">납기예정일</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">금액</th>
            <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">항목수</th>
            <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">상태</th>
            <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">대금지급</th>
            <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">작업</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-if="loading">
            <td colspan="10" class="px-6 py-4 text-center text-gray-500">로딩 중...</td>
          </tr>
          <tr v-else-if="purchaseOrders.length === 0">
            <td colspan="10" class="px-6 py-4 text-center text-gray-500">데이터가 없습니다.</td>
          </tr>
          <tr
            v-for="po in purchaseOrders"
            :key="po.id"
            class="hover:bg-gray-50 cursor-pointer"
            @click="openDetailModal(po.id)"
          >
            <td class="px-3 py-4 text-center" @click.stop>
              <input type="checkbox" :checked="selectedPoIds.has(po.id)" @change="togglePoSelect(po.id)" class="w-4 h-4 rounded cursor-pointer" />
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="text-sm font-medium text-blue-600">{{ po.po_number }}</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ po.supplier?.partner_name || '-' }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ formatDate(po.order_date) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ po.expected_delivery_date ? formatDate(po.expected_delivery_date) : '-' }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
              {{ formatCurrency(po.total_amount) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
              {{ po.item_count || 0 }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-center">
              <span :class="['px-2 py-1 text-xs rounded-full', poStatusStyles[po.status]]">
                {{ poStatusLabels[po.status] }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-center" @click.stop>
              <span v-if="po.is_paid" class="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-700" title="지출결의(집행) 완료로 지급 완료">지급 완료</span>
              <span v-else-if="po.disbursement_id" @click="goDisbursement(po.disbursement_id!)" class="px-2 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-700 cursor-pointer hover:bg-amber-200" title="지출결의 진행 중 — 클릭하여 열기">지급 대기</span>
              <span v-else class="px-2 py-1 text-xs text-gray-400" title="아직 지출결의로 묶이지 않음">미청구</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-center">
              <div class="flex justify-center gap-2" @click.stop>
                <button
                  v-if="po.status === 'DRAFT'"
                  @click="handleOrder(po.id)"
                  class="text-blue-600 hover:text-blue-800 text-sm"
                  title="주문 확정"
                >
                  주문확정
                </button>
                <button
                  v-if="po.status === 'ORDERED' || po.status === 'CONFIRMED'"
                  @click="openReceiveModal(po.id)"
                  class="text-green-600 hover:text-green-800 text-sm"
                  title="입고 처리"
                >
                  입고
                </button>
                <button
                  v-if="!po.sent_at && po.status !== 'DRAFT' && po.status !== 'CANCELLED'"
                  @click="handleMarkSent(po.id, true)"
                  class="text-sky-600 hover:text-sky-800 text-sm"
                  title="공급업체에 발송 완료 처리(발송일 기록)"
                >
                  📤 발송
                </button>
                <span
                  v-else-if="po.sent_at"
                  @click="handleMarkSent(po.id, false)"
                  class="text-sky-700 text-xs cursor-pointer"
                  :title="'발송 취소'"
                >
                  ✅ 발송 {{ formatSentDate(po.sent_at) }}
                </span>
                <button
                  v-if="canRollback(po.status)"
                  @click="handleRollback(po.id, po.status)"
                  class="text-yellow-600 hover:text-yellow-800 text-sm"
                  title="이전 상태로 롤백"
                >
                  롤백
                </button>
                <button
                  @click="createApprovalFromPo(po)"
                  class="text-indigo-600 hover:text-indigo-800 text-sm"
                  title="이 발주건으로 구매기안서(임시저장) 생성"
                >
                  구매기안
                </button>
                <button
                  v-if="po.status === 'DRAFT'"
                  @click="handleDelete(po.id)"
                  class="text-red-600 hover:text-red-800 text-sm"
                  title="삭제"
                >
                  삭제
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 페이지네이션 -->
    <div class="mt-4 flex justify-between items-center">
      <div class="text-sm text-gray-500">
        총 {{ pagination.total }}건 중 {{ (pagination.skip || 0) + 1 }} - {{ Math.min((pagination.skip || 0) + purchaseOrders.length, pagination.total) }}건
      </div>
      <div class="flex gap-2">
        <button
          @click="goPage(currentPage - 1)"
          :disabled="currentPage <= 1"
          class="px-3 py-1 border rounded disabled:opacity-50"
        >
          이전
        </button>
        <span class="px-3 py-1">{{ currentPage }} / {{ totalPages }}</span>
        <button
          @click="goPage(currentPage + 1)"
          :disabled="currentPage >= totalPages"
          class="px-3 py-1 border rounded disabled:opacity-50"
        >
          다음
        </button>
      </div>
    </div>

    <!-- 발주서 등록/상세 모달 -->
    <PurchaseOrderFormModal
      v-if="showFormModal"
      :purchase-order-id="selectedPOId"
      :suppliers="suppliers"
      @close="showFormModal = false"
      @saved="handleSaved"
    />

    <!-- 입고 처리 모달 -->
    <PurchaseOrderReceiveModal
      v-if="showReceiveModal && receivePOId"
      :purchase-order-id="receivePOId"
      @close="showReceiveModal = false"
      @received="handleReceived"
    />
  </div>
</template>

<script setup lang="ts">
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import { ref, reactive, computed, onMounted } from 'vue'
import {
  purchaseOrderApi,
  type PurchaseOrderListItem,
  type PurchaseOrderSearchParams,
  poStatusLabels,
  poStatusStyles,
} from '@/api/purchaseOrder'
import { partnerApi } from '@/api/partner'
import PurchaseOrderFormModal from '@/views/production/components/PurchaseOrderFormModal.vue'
import PurchaseOrderReceiveModal from '@/views/production/components/PurchaseOrderReceiveModal.vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// 상태
const loading = ref(false)
const purchaseOrders = ref<PurchaseOrderListItem[]>([])
const suppliers = ref<any[]>([])
const pagination = reactive({ total: 0, skip: 0, limit: 20 })

// 필터
const filters = reactive<PurchaseOrderSearchParams>({
  keyword: '',
  status: undefined,
  supplier_id: undefined,
  from_date: '',
  to_date: '',
})

// 모달
const showFormModal = ref(false)
const selectedPOId = ref<number | null>(null)
const showReceiveModal = ref(false)
const receivePOId = ref<number | null>(null)

// 계산된 속성
const currentPage = computed(() => Math.floor((pagination.skip || 0) / pagination.limit) + 1)
const totalPages = computed(() => Math.ceil(pagination.total / pagination.limit) || 1)

// 데이터 로드
const debouncedSearch = useDebouncedSearch(() => loadData())
async function loadData() {
  loading.value = true
  try {
    const params: PurchaseOrderSearchParams = {
      ...filters,
      skip: pagination.skip,
      limit: pagination.limit,
    }
    // 빈 문자열을 undefined로 변환
    if (!params.keyword) params.keyword = undefined
    if (!params.status) params.status = undefined
    if (!params.supplier_id) params.supplier_id = undefined
    if (!params.from_date) params.from_date = undefined
    if (!params.to_date) params.to_date = undefined

    const response = await purchaseOrderApi.getAll(params)
    purchaseOrders.value = response.items
    pagination.total = response.total
  } catch (error) {
    console.error('발주서 목록 조회 실패:', error)
    alert('발주서 목록을 불러오는데 실패했습니다.')
  } finally {
    loading.value = false
  }
}

// 공급업체 목록 로드
async function loadSuppliers() {
  try {
    const response = await partnerApi.getAll({ is_supplier: true, limit: 1000 })
    suppliers.value = response.data.items
  } catch (error) {
    console.error('공급업체 목록 조회 실패:', error)
  }
}

// 필터 초기화
function resetFilters() {
  filters.keyword = ''
  filters.status = undefined
  filters.supplier_id = undefined
  filters.from_date = ''
  filters.to_date = ''
  pagination.skip = 0
  loadData()
}

// 페이지 이동
function goPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  pagination.skip = (page - 1) * pagination.limit
  loadData()
}

// 모달
function openCreateModal() {
  selectedPOId.value = null
  showFormModal.value = true
}

function openDetailModal(id: number) {
  selectedPOId.value = id
  showFormModal.value = true
}

function openReceiveModal(id: number) {
  receivePOId.value = id
  showReceiveModal.value = true
}

// 액션
async function handleOrder(id: number) {
  if (!confirm('주문을 확정하시겠습니까?')) return
  try {
    await purchaseOrderApi.order(id)
    alert('주문이 확정되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('주문 확정 실패:', error)
    alert(error.response?.data?.detail?.message || '주문 확정에 실패했습니다.')
  }
}

// 이 발주건으로 구매기안서(임시저장) 생성 → 편집화면으로 이동
async function createApprovalFromPo(po: PurchaseOrderListItem) {
  if (!confirm(`발주서 ${po.po_number} 건으로 구매기안서를 생성하시겠습니까?\n업체·품목이 자동 등록되어 임시저장됩니다.`)) return
  try {
    const res = await purchaseOrderApi.createApproval(po.id)
    alert(`구매기안서 ${res.doc_number}(임시저장)가 생성되었습니다. 결재선을 지정한 뒤 상신하세요.`)
    router.push(`/approvals/${res.approval_id}/edit`)
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || error.response?.data?.detail || '구매기안서 생성에 실패했습니다.')
  }
}

async function handleDelete(id: number) {
  if (!confirm('발주서를 삭제하시겠습니까?')) return
  try {
    await purchaseOrderApi.delete(id)
    alert('발주서가 삭제되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('삭제 실패:', error)
    alert(error.response?.data?.detail?.message || '삭제에 실패했습니다.')
  }
}

// 롤백 관련
const rollbackLabels: Record<string, string> = {
  ORDERED: '작성중으로',
  CONFIRMED: '주문완료로',
  RECEIVED: '납기확정으로',
  COMPLETED: '입고완료로', // 기존 데이터 호환용
}

function canRollback(status: string): boolean {
  return status === 'ORDERED' || status === 'CONFIRMED' || status === 'RECEIVED' || status === 'COMPLETED'
}

async function handleRollback(id: number, currentStatus: string) {
  const label = rollbackLabels[currentStatus] || '이전 상태로'
  const message = currentStatus === 'RECEIVED'
    ? `${label} 롤백하시겠습니까?\n입고완료 상태에서 롤백 시 재고가 차감됩니다.`
    : `${label} 롤백하시겠습니까?`

  if (!confirm(message)) return

  try {
    await purchaseOrderApi.rollback(id)
    alert('롤백이 완료되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('롤백 실패:', error)
    alert(error.response?.data?.detail?.message || '롤백에 실패했습니다.')
  }
}

// 대금 지급 = 지출결의(집행)로 연동. 연결된 지출결의서 열기
function goDisbursement(disbursementId: number) {
  router.push({ path: `/approvals/${disbursementId}` })
}

// #7 발주서 발송 완료/취소 (발송일 기록)
async function handleMarkSent(id: number, sent: boolean) {
  if (!sent && !confirm('발송 완료를 취소하시겠습니까?')) return
  try {
    const updated = await purchaseOrderApi.markSent(id, sent)
    const po = purchaseOrders.value.find(p => p.id === id)
    if (po) po.sent_at = updated.sent_at ?? null
  } catch (error: any) {
    console.error('발송 처리 실패:', error)
    alert(error.response?.data?.detail?.message || '발송 처리에 실패했습니다.')
  }
}
function formatSentDate(dt?: string | null): string {
  if (!dt) return ''
  try { return new Date(dt).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }) } catch { return '' }
}

// #8 발주 다중선택 → 지출결의서 묶기
const selectedPoIds = ref<Set<number>>(new Set())
const disbursing = ref(false)
const allSelected = computed(() => purchaseOrders.value.length > 0 && purchaseOrders.value.every(p => selectedPoIds.value.has(p.id)))
function togglePoSelect(id: number) {
  const s = new Set(selectedPoIds.value)
  s.has(id) ? s.delete(id) : s.add(id)
  selectedPoIds.value = s
}
function toggleSelectAll() {
  if (allSelected.value) selectedPoIds.value = new Set()
  else selectedPoIds.value = new Set(purchaseOrders.value.map(p => p.id))
}
function clearPoSelection() { selectedPoIds.value = new Set() }
async function handleCreateDisbursement() {
  const ids = Array.from(selectedPoIds.value)
  if (ids.length === 0) return
  if (!confirm(`선택한 ${ids.length}건의 발주서를 하나의 지출결의서로 묶어 생성합니다. 계속할까요?`)) return
  disbursing.value = true
  try {
    const res = await purchaseOrderApi.createDisbursement(ids)
    clearPoSelection()
    alert('지출결의서(임시저장)가 생성됐습니다. 결재선·시행자를 지정해 상신하세요.')
    // 생성된 지출결의서 작성 화면으로 이동(편집)
    router.push({ path: `/approvals/${res.id}/edit` })
  } catch (error: any) {
    console.error('지출결의 생성 실패:', error)
    alert(error.response?.data?.detail?.message || error.response?.data?.detail || '지출결의 생성에 실패했습니다.')
  } finally {
    disbursing.value = false
  }
}

function handleSaved() {
  showFormModal.value = false
  loadData()
}

function handleReceived() {
  showReceiveModal.value = false
  loadData()
}

// 포맷
function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('ko-KR')
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW', minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(amount || 0)
}

// 초기화
onMounted(() => {
  loadSuppliers()
  loadData()
})
</script>
