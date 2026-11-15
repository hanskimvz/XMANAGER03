<template>
  <div class="p-6">
    <!-- 헤더 -->
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">생산 요청서 관리</h1>
      <button
        @click="openCreateModal"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        생산 요청 등록
      </button>
    </div>

    <!-- 검색/필터 -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <!-- 키워드 검색 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">검색</label>
          <input
            v-model="filters.keyword"
            type="text"
            placeholder="요청번호, 고객주문번호"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            @keyup.enter="loadData"
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
            <option v-for="(label, key) in prStatusLabels" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>

        <!-- 고객사 필터 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">고객사</label>
          <select
            v-model="filters.customer_id"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            @change="loadData"
          >
            <option value="">전체</option>
            <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>

        <!-- 우선순위 필터 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">우선순위</label>
          <select
            v-model="filters.priority"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            @change="loadData"
          >
            <option value="">전체</option>
            <option v-for="(label, key) in priorityLabels" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>

        <!-- 요청일 범위 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">요청일</label>
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
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">요청번호</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">고객사</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">제품</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">요청수량</th>
            <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">납기</th>
            <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">상태</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-if="loading">
            <td colspan="6" class="px-6 py-4 text-center text-gray-500">로딩 중...</td>
          </tr>
          <tr v-else-if="requests.length === 0">
            <td colspan="6" class="px-6 py-4 text-center text-gray-500">데이터가 없습니다.</td>
          </tr>
          <tr
            v-for="pr in requests"
            :key="pr.id"
            class="hover:bg-gray-50 cursor-pointer"
            @click="openDetailModal(pr.id)"
          >
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="text-sm font-medium text-blue-600">{{ pr.request_number }}</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ pr.customer?.partner_name || '-' }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              <div class="relative group inline-block">
                <span>{{ getProductDisplay(pr) }}</span>
                <!-- 다중 제품 툴팁 -->
                <div
                  v-if="pr.items && pr.items.length > 1"
                  class="absolute left-0 top-full mt-1 z-50 hidden group-hover:block bg-gray-800 text-white text-xs rounded-lg shadow-lg py-2 px-3 min-w-[200px] whitespace-normal"
                >
                  <div class="font-medium mb-1 pb-1 border-b border-gray-600">제품 목록 ({{ pr.items.length }}종)</div>
                  <ul class="space-y-1">
                    <li v-for="(item, idx) in pr.items" :key="idx" class="flex justify-between gap-4">
                      <span class="break-words max-w-[250px]">{{ item.product_part?.part_name || item.product_part?.part_number || '-' }}</span>
                      <span class="text-gray-300 flex-shrink-0">{{ formatNumber(item.requested_quantity) }}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
              {{ formatNumber(getTotalQuantity(pr)) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
              {{ pr.due_date ? formatDate(pr.due_date) : '-' }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-center">
              <span :class="['px-2 py-1 text-xs rounded-full', prStatusStyles[pr.status]]">
                {{ prStatusLabels[pr.status] }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 페이지네이션 -->
    <div class="mt-4 flex justify-between items-center">
      <div class="text-sm text-gray-500">
        총 {{ pagination.total }}건 중 {{ (pagination.skip || 0) + 1 }} - {{ Math.min((pagination.skip || 0) + requests.length, pagination.total) }}건
      </div>
      <div class="flex gap-2">
        <button
          @click="goToPage(currentPage - 1)"
          :disabled="currentPage === 1"
          class="px-3 py-1 border rounded disabled:opacity-50"
        >
          이전
        </button>
        <span class="px-3 py-1">{{ currentPage }} / {{ totalPages }}</span>
        <button
          @click="goToPage(currentPage + 1)"
          :disabled="!pagination.has_more"
          class="px-3 py-1 border rounded disabled:opacity-50"
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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

const route = useRoute()
const router = useRouter()

// 상태
const loading = ref(false)
const requests = ref<ProductionRequestListItem[]>([])
const customers = ref<{ id: number; name: string }[]>([])
const pagination = ref({ total: 0, skip: 0, limit: 50, has_more: false })

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
    customers.value = response.data.items.map(p => ({ id: p.id, name: p.partner_name }))
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
  pagination.value.skip = 0
  loadData()
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
}

// 상태 변경 처리
async function handleApprove(id: number) {
  if (!confirm('승인하시겠습니까?')) return
  try {
    await productionRequestApi.approve(id)
    loadData()
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
    if (showDetailModal.value) closeDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '취소 실패')
  }
}

async function handleDelete(id: number) {
  if (!confirm('삭제하시겠습니까?')) return
  try {
    await productionRequestApi.delete(id)
    loadData()
    if (showDetailModal.value) closeDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '삭제 실패')
  }
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

// v0.22.0: 다중 제품 표시
function getProductDisplay(pr: ProductionRequestListItem): string {
  // items가 있으면 다중 제품 처리
  if (pr.items && pr.items.length > 0) {
    const firstItem = pr.items[0]
    const firstName = firstItem?.product_part?.part_name || firstItem?.product_part?.part_number || '-'
    if (pr.items.length > 1) {
      return `${firstName} 외 ${pr.items.length - 1}종`
    }
    return firstName
  }
  // 레거시: 단일 제품 (deprecated)
  return pr.product_part?.part_name || pr.product_part?.part_number || '-'
}

// v0.22.0: 총 요청 수량 계산
function getTotalQuantity(pr: ProductionRequestListItem): number {
  // items가 있으면 합계 계산
  if (pr.items && pr.items.length > 0) {
    return pr.items.reduce((sum, item) => sum + Number(item.requested_quantity || 0), 0)
  }
  // 레거시: 단일 수량 (deprecated)
  return Number(pr.requested_quantity) || 0
}

// edit_id 쿼리 파라미터 처리 (PI/PI 모달에서 이동 시)
function handleEditIdQuery(editId: any) {
  if (editId) {
    selectedId.value = Number(editId)
    showFormModal.value = true
    // URL에서 쿼리 파라미터 제거
    router.replace({ path: route.path })
  }
}

// route.query 변경 감지 (이미 마운트된 상태에서 다른 페이지에서 이동했을 때)
watch(() => route.query.edit_id, (newId) => {
  handleEditIdQuery(newId)
})

// 초기 로드
onMounted(async () => {
  loadCustomers()
  await loadData()
  handleEditIdQuery(route.query.edit_id)
})
</script>
