<template>
  <div class="p-4">
    <!-- 검색/필터 -->
    <div class="bg-white rounded-lg shadow p-4 mb-4">
      <div class="flex flex-wrap gap-3">
        <!-- 키워드 검색 -->
        <div class="min-w-[160px] flex-1">
          <label class="block text-sm font-medium text-gray-700 mb-1">검색</label>
          <input
            v-model="filters.keyword"
            type="text"
            placeholder="요청번호, 고객주문번호"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
            @keyup.enter="loadData"
          />
        </div>

        <!-- 상태 필터 -->
        <div class="min-w-[100px] w-[100px]">
          <label class="block text-sm font-medium text-gray-700 mb-1">상태</label>
          <select
            v-model="filters.status"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
            @change="loadData"
          >
            <option value="">전체</option>
            <option v-for="(label, key) in prStatusLabels" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>

        <!-- 고객사 필터 (콤보박스) -->
        <div class="min-w-[150px] flex-1 max-w-[200px] relative">
          <label class="block text-sm font-medium text-gray-700 mb-1">고객사</label>
          <div class="relative">
            <input
              v-model="customerSearchText"
              type="text"
              placeholder="검색 또는 선택"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm pr-8"
              @focus="showCustomerDropdown = true"
              @input="onCustomerSearch"
            />
            <button
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              @click="toggleCustomerDropdown"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <!-- 드롭다운 목록 -->
            <div
              v-if="showCustomerDropdown"
              class="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto"
            >
              <div
                class="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                @click="selectCustomer(null, '전체')"
              >
                전체
              </div>
              <div
                v-for="c in filteredCustomers"
                :key="c.id"
                class="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm truncate"
                @click="selectCustomer(c.id, c.name)"
              >
                {{ c.name }}
              </div>
              <div v-if="filteredCustomers.length === 0" class="px-3 py-2 text-sm text-gray-400">
                검색 결과 없음
              </div>
            </div>
          </div>
        </div>

        <!-- 우선순위 필터 -->
        <div class="min-w-[90px] w-[90px]">
          <label class="block text-sm font-medium text-gray-700 mb-1">우선순위</label>
          <select
            v-model="filters.priority"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
            @change="loadData"
          >
            <option value="">전체</option>
            <option v-for="(label, key) in priorityLabels" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>

        <!-- 요청일 범위 -->
        <div class="min-w-[220px]">
          <label class="block text-sm font-medium text-gray-700 mb-1">요청일</label>
          <div class="flex gap-1">
            <input
              v-model="filters.from_date"
              type="date"
              class="flex-1 min-w-0 px-2 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
              @change="loadData"
            />
            <input
              v-model="filters.to_date"
              type="date"
              class="flex-1 min-w-0 px-2 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
              @change="loadData"
            />
          </div>
        </div>
      </div>

      <!-- 버튼 영역 (아래로 분리) -->
      <div class="mt-4 flex justify-end gap-2 border-t pt-4">
        <button
          @click="resetFilters"
          class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 border rounded-lg"
        >
          필터 초기화
        </button>
        <button
          @click="loadData"
          class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          검색
        </button>
      </div>
    </div>

    <!-- 등록 버튼 & 결과 요약 -->
    <div class="flex justify-between items-center mb-4">
      <div class="flex items-center gap-3">
        <div class="text-sm text-gray-500">총 {{ pagination.total }}건</div>
        <!-- 리스트/캘린더 전환(기본 리스트) -->
        <div class="inline-flex rounded-lg border overflow-hidden">
          <button @click="viewMode='list'" class="px-3 py-1.5 text-sm"
            :class="viewMode==='list' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'">리스트</button>
          <button @click="viewMode='calendar'" class="px-3 py-1.5 text-sm border-l"
            :class="viewMode==='calendar' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'">📅 캘린더</button>
        </div>
      </div>
      <button
        @click="openCreateModal"
        class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 flex items-center gap-2"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        생산 요청 등록
      </button>
    </div>

    <!-- 캘린더 뷰 (생산팀 온디맨드) -->
    <div v-if="viewMode==='calendar'" class="bg-white rounded-lg shadow p-3">
      <ProductionRequestCalendar @open-detail="openDetailModal" />
    </div>

    <!-- 테이블 -->
    <div v-else class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200 text-sm">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">요청번호</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">고객사</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">제품</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">요청수량</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">납기</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">상태</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-if="loading">
            <td colspan="6" class="px-4 py-4 text-center text-gray-500">로딩 중...</td>
          </tr>
          <tr v-else-if="requests.length === 0">
            <td colspan="6" class="px-4 py-4 text-center text-gray-500">데이터가 없습니다.</td>
          </tr>
          <tr
            v-for="pr in requests"
            :key="pr.id"
            class="hover:bg-gray-50 cursor-pointer"
            @click="openDetailModal(pr.id)"
          >
            <td class="px-4 py-3 whitespace-nowrap">
              <span class="font-medium text-blue-600">{{ pr.request_number }}</span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-gray-900">
              {{ pr.customer?.partner_name || '-' }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-gray-900">
              <span
                @mouseenter="pr.items && pr.items.length > 1 && showTooltip($event, pr)"
                @mouseleave="hideTooltip"
              >{{ getProductDisplay(pr) }}</span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-gray-900 text-right">
              {{ getQuantityDisplay(pr) }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-gray-500 text-center">
              {{ pr.due_date ? formatDate(pr.due_date) : '-' }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-center">
              <span :class="['px-2 py-0.5 text-xs rounded-full', prStatusStyles[pr.status]]">
                {{ prStatusLabels[pr.status] }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 페이지네이션 (리스트 뷰 전용) -->
    <div v-if="viewMode==='list'" class="mt-4 flex justify-between items-center text-sm">
      <div class="text-gray-500">
        총 {{ pagination.total }}건 중 {{ (pagination.skip || 0) + 1 }} - {{ Math.min((pagination.skip || 0) + requests.length, pagination.total) }}건
      </div>
      <div class="flex gap-2 items-center">
        <button
          @click="goToPage(currentPage - 1)"
          :disabled="currentPage === 1"
          class="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-50"
        >
          이전
        </button>
        <span class="px-3 py-1">{{ currentPage }} / {{ totalPages }}</span>
        <button
          @click="goToPage(currentPage + 1)"
          :disabled="!pagination.has_more"
          class="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-50"
        >
          다음
        </button>
      </div>
    </div>

    <!-- 등록/수정 모달 -->
    <ProductionRequestFormModal
      v-if="showFormModal"
      :request-id="selectedId"
      :customers="customers"
      @close="closeFormModal"
      @saved="handleSaved"
    />

    <!-- 상세 모달 -->
    <ProductionRequestDetailModal
      v-if="showDetailModal && selectedId !== null"
      :request-id="selectedId"
      @close="closeDetailModal"
      @edit="openEditModal"
      @approve="handleApprove"
      @reject="handleReject"
      @hold="handleHold"
      @release-hold="handleReleaseHold"
      @cancel="handleCancel"
      @delete="handleDelete"
    />

    <!-- 반려 사유 입력 모달 -->
    <div v-if="showRejectModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 class="text-lg font-bold mb-4">반려 사유 입력</h3>
        <textarea
          v-model="rejectReason"
          rows="4"
          class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          placeholder="반려 사유를 입력하세요"
        ></textarea>
        <div class="mt-4 flex justify-end gap-2">
          <button
            @click="showRejectModal = false"
            class="px-4 py-2 border rounded-lg hover:bg-gray-50"
          >
            취소
          </button>
          <button
            @click="confirmReject"
            :disabled="!rejectReason.trim()"
            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
          >
            반려
          </button>
        </div>
      </div>
    </div>

    <!-- 제품 목록 툴팁 (Teleport로 body에 렌더링하여 overflow 문제 방지) -->
    <Teleport to="body">
      <div
        v-if="tooltip.visible"
        class="fixed z-[9999] bg-gray-800 text-white text-xs rounded-lg py-2 px-3 shadow-lg whitespace-nowrap pointer-events-none"
        :style="{ top: tooltip.y + 'px', left: tooltip.x + 'px' }"
      >
        <div v-for="(item, idx) in tooltip.items" :key="idx" class="py-0.5">
          {{ item.name }} ({{ item.qty }})
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  productionRequestApi,
  prStatusLabels,
  prStatusStyles,
  priorityLabels,
  type ProductionRequestListItem,
  type ProductionRequestStatus
} from '@/api/productionRequest'
import { partnerApi } from '@/api/partner'
import ProductionRequestFormModal from '@/views/production/components/ProductionRequestFormModal.vue'
import ProductionRequestDetailModal from '@/views/production/components/ProductionRequestDetailModal.vue'
import ProductionRequestCalendar from '@/views/production/components/ProductionRequestCalendar.vue'

// 부모에게 이벤트 emit (생산 요청 등록/수정 시, 상태 변경 시)
const emit = defineEmits<{
  (e: 'request-saved'): void
  (e: 'data-changed'): void
}>()

// 상태
const loading = ref(false)
const requests = ref<ProductionRequestListItem[]>([])
const customers = ref<{ id: number; name: string }[]>([])
const pagination = ref({ total: 0, skip: 0, limit: 50, has_more: false })

// 고객사 콤보박스 상태
const showCustomerDropdown = ref(false)
const customerSearchText = ref('')

// 필터링된 고객사 목록
const filteredCustomers = computed(() => {
  if (!customerSearchText.value) return customers.value
  const search = customerSearchText.value.toLowerCase()
  return customers.value.filter(c => c.name.toLowerCase().includes(search))
})

// 필터
const filters = ref({
  keyword: '',
  status: '' as ProductionRequestStatus | '',
  customer_id: '' as number | '',
  priority: '' as number | '',
  from_date: '',
  to_date: ''
})

// 모달 상태
const showFormModal = ref(false)
const viewMode = ref<'list' | 'calendar'>('list')
const showDetailModal = ref(false)
const showRejectModal = ref(false)
const selectedId = ref<number | null>(null)
const rejectReason = ref('')
const rejectTargetId = ref<number | null>(null)

// 계산된 속성
const currentPage = computed(() => Math.floor((pagination.value.skip || 0) / pagination.value.limit) + 1)
const totalPages = computed(() => Math.ceil(pagination.value.total / pagination.value.limit) || 1)

// 데이터 로드
async function loadData() {
  loading.value = true
  try {
    const params: any = {
      skip: pagination.value.skip,
      limit: pagination.value.limit
    }
    if (filters.value.keyword) params.keyword = filters.value.keyword
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.customer_id) params.customer_id = filters.value.customer_id
    if (filters.value.priority !== '') params.priority = filters.value.priority
    if (filters.value.from_date) params.from_date = filters.value.from_date
    if (filters.value.to_date) params.to_date = filters.value.to_date

    const response = await productionRequestApi.getAll(params)
    requests.value = response.items
    pagination.value = {
      total: response.total,
      skip: response.skip,
      limit: response.limit,
      has_more: response.has_more
    }
  } catch (error) {
    console.error('데이터 로드 실패:', error)
  } finally {
    loading.value = false
  }
}

// 고객사 목록 로드
async function loadCustomers() {
  try {
    const response = await partnerApi.getAll({ partner_type: 'CUSTOMER', limit: 1000 })
    customers.value = response.data.items.map((p: any) => ({ id: p.id, name: p.partner_name }))
  } catch (error) {
    console.error('고객사 목록 로드 실패:', error)
  }
}

// 필터 초기화
function resetFilters() {
  filters.value = {
    keyword: '',
    status: '',
    customer_id: '',
    priority: '',
    from_date: '',
    to_date: ''
  }
  customerSearchText.value = ''
  pagination.value.skip = 0
  loadData()
}

// 고객사 콤보박스 함수들
function toggleCustomerDropdown() {
  showCustomerDropdown.value = !showCustomerDropdown.value
}

function selectCustomer(id: number | null, name: string) {
  filters.value.customer_id = id || ''
  customerSearchText.value = id ? name : ''
  showCustomerDropdown.value = false
  loadData()
}

function onCustomerSearch() {
  showCustomerDropdown.value = true
  // 검색어가 비어있으면 필터 초기화
  if (!customerSearchText.value) {
    filters.value.customer_id = ''
  }
}

// 외부 클릭 시 드롭다운 닫기
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.relative')) {
    showCustomerDropdown.value = false
  }
}

// 페이지 이동
function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  pagination.value.skip = (page - 1) * pagination.value.limit
  loadData()
}

// 모달 열기/닫기
function openCreateModal() {
  selectedId.value = null
  showFormModal.value = true
}

function openEditModal(id: number) {
  selectedId.value = id
  showDetailModal.value = false
  showFormModal.value = true
}

function openDetailModal(id: number) {
  selectedId.value = id
  showDetailModal.value = true
}

function closeFormModal() {
  showFormModal.value = false
  selectedId.value = null
}

function closeDetailModal() {
  showDetailModal.value = false
  selectedId.value = null
}

function handleSaved() {
  closeFormModal()
  loadData()
  // 부모에게 생산 요청이 등록/수정됨을 알림 (작업지시 탭 새로고침 용도)
  emit('request-saved')
}

// 상태 변경 처리
async function handleApprove(id: number) {
  if (!confirm('승인하시겠습니까?')) return
  try {
    await productionRequestApi.approve(id)
    loadData()
    emit('data-changed')
    if (showDetailModal.value) closeDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '승인 실패')
  }
}

function handleReject(id: number) {
  rejectTargetId.value = id
  rejectReason.value = ''
  showRejectModal.value = true
}

async function confirmReject() {
  if (!rejectTargetId.value || !rejectReason.value.trim()) return
  try {
    await productionRequestApi.reject(rejectTargetId.value, { rejection_reason: rejectReason.value })
    showRejectModal.value = false
    loadData()
    emit('data-changed')
    if (showDetailModal.value) closeDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '반려 실패')
  }
}

async function handleHold(id: number) {
  if (!confirm('보류 처리하시겠습니까?')) return
  try {
    await productionRequestApi.hold(id)
    loadData()
    emit('data-changed')
    if (showDetailModal.value) closeDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '보류 처리 실패')
  }
}

async function handleReleaseHold(id: number) {
  if (!confirm('보류를 해제하시겠습니까?')) return
  try {
    await productionRequestApi.releaseHold(id)
    loadData()
    emit('data-changed')
    if (showDetailModal.value) closeDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '보류 해제 실패')
  }
}

async function handleCancel(id: number) {
  const reason = prompt('취소 사유를 입력하세요:')
  if (reason === null) return
  try {
    await productionRequestApi.cancel(id, reason)
    loadData()
    emit('data-changed')
    if (showDetailModal.value) closeDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '취소 실패')
  }
}

// 완전 삭제 (CANCELLED/REJECTED 상태에서만)
async function handleDelete(id: number) {
  if (!confirm('생산 요청서를 완전히 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.')) return
  try {
    await productionRequestApi.delete(id)
    loadData()
    emit('data-changed')
    if (showDetailModal.value) closeDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '삭제 실패')
  }
}

// 툴팁 상태
const tooltip = ref<{
  visible: boolean
  x: number
  y: number
  items: { name: string; qty: string }[]
}>({ visible: false, x: 0, y: 0, items: [] })

function showTooltip(event: MouseEvent, pr: ProductionRequestListItem) {
  if (!pr.items || pr.items.length <= 1) return
  const rect = (event.target as HTMLElement).getBoundingClientRect()
  tooltip.value = {
    visible: true,
    x: rect.left,
    y: rect.top - 4,
    items: pr.items.map(item => ({
      name: item.product_part?.part_name || item.product_part?.part_number || '-',
      qty: formatNumber(item.requested_quantity)
    }))
  }
  // 다음 틱에서 높이 반영하여 위로 배치
  requestAnimationFrame(() => {
    const el = document.querySelector('[class*="z-\\[9999\\]"]') as HTMLElement
    if (el) {
      tooltip.value.y = rect.top - el.offsetHeight - 4
    }
  })
}

function hideTooltip() {
  tooltip.value.visible = false
}

// 제품 표시 (다중 제품: "제품명 외 N개")
function getProductDisplay(pr: ProductionRequestListItem): string {
  if (pr.items && pr.items.length > 0) {
    const firstName = pr.items[0]?.product_part?.part_name || pr.items[0]?.product_part?.part_number || '-'
    if (pr.items.length === 1) return firstName
    return `${firstName} 외 ${pr.items.length - 1}개`
  }
  return pr.product_part?.part_name || pr.product_part?.part_number || '-'
}

// 수량 표시 (다중 제품: "수량1/수량2/수량3")
function getQuantityDisplay(pr: ProductionRequestListItem): string {
  if (pr.items && pr.items.length > 0) {
    return pr.items.map(item => formatNumber(item.requested_quantity)).join('/')
  }
  return formatNumber(pr.requested_quantity || 0)
}

// 포맷팅 함수
function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('ko-KR')
}

function formatNumber(num: number): string {
  return num?.toLocaleString('ko-KR') || '0'
}

// 초기 로드
onMounted(() => {
  loadCustomers()
  loadData()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

// 부모 컴포넌트에서 호출 가능하도록 노출
defineExpose({
  loadData
})
</script>
