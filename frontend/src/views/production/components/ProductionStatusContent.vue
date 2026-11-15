<template>
  <div class="p-4">
    <!-- 로딩 -->
    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
    </div>

    <div v-else>
      <!-- 상태별 요약 카드 -->
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <!-- 요청됨 -->
        <div class="bg-white rounded-lg shadow p-4 border-l-4 border-blue-400">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">요청됨</p>
              <p class="text-2xl font-bold text-blue-600">{{ statusCounts.REQUESTED || 0 }}</p>
            </div>
            <div class="p-3 bg-blue-100 rounded-full">
              <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          </div>
        </div>

        <!-- 승인됨 -->
        <div class="bg-white rounded-lg shadow p-4 border-l-4 border-green-400">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">승인됨</p>
              <p class="text-2xl font-bold text-green-600">{{ statusCounts.APPROVED || 0 }}</p>
            </div>
            <div class="p-3 bg-green-100 rounded-full">
              <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>

        <!-- 보류 -->
        <div class="bg-white rounded-lg shadow p-4 border-l-4 border-yellow-400">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">보류</p>
              <p class="text-2xl font-bold text-yellow-600">{{ statusCounts.HOLD || 0 }}</p>
            </div>
            <div class="p-3 bg-yellow-100 rounded-full">
              <svg class="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>

        <!-- 완료 -->
        <div class="bg-white rounded-lg shadow p-4 border-l-4 border-gray-400">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">완료</p>
              <p class="text-2xl font-bold text-gray-600">{{ statusCounts.COMPLETED || 0 }}</p>
            </div>
            <div class="p-3 bg-gray-100 rounded-full">
              <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
        </div>

        <!-- 취소/반려 -->
        <div class="bg-white rounded-lg shadow p-4 border-l-4 border-red-400">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">취소/반려</p>
              <p class="text-2xl font-bold text-red-600">{{ (statusCounts.CANCELLED || 0) + (statusCounts.REJECTED || 0) }}</p>
            </div>
            <div class="p-3 bg-red-100 rounded-full">
              <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- 최근 요청 목록 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- 처리 대기 요청 -->
        <div class="bg-white rounded-lg shadow">
          <div class="px-4 py-3 border-b bg-blue-50">
            <h2 class="text-lg font-semibold text-blue-800">처리 대기 요청</h2>
          </div>
          <div class="divide-y max-h-96 overflow-y-auto">
            <div
              v-for="request in pendingRequests"
              :key="request.id"
              class="px-4 py-3 hover:bg-blue-50 cursor-pointer transition-colors"
              @click="openRequestDetail(request.id)"
            >
              <div class="flex justify-between items-start">
                <div>
                  <p class="font-medium text-blue-600 hover:underline">{{ request.request_number }}</p>
                  <p class="text-sm text-gray-500">{{ request.customer?.partner_name || '-' }} / {{ request.product_part?.part_number || '-' }}</p>
                </div>
                <span :class="getStatusBadgeClass(request.status)">
                  {{ getStatusLabel(request.status) }}
                </span>
              </div>
              <div class="mt-1 flex justify-between text-xs text-gray-400">
                <span>수량: {{ formatNumber(request.requested_quantity ?? 0) }}</span>
                <span>{{ request.created_at ? formatDate(request.created_at) : '' }}</span>
              </div>
            </div>
            <div v-if="pendingRequests.length === 0" class="px-4 py-8 text-center text-gray-500">
              처리 대기 중인 요청이 없습니다.
            </div>
          </div>
        </div>

        <!-- 진행 중인 작업 지시 (승인 ~ 포장 완료) -->
        <div class="bg-white rounded-lg shadow">
          <div class="px-4 py-3 border-b bg-green-50">
            <h2 class="text-lg font-semibold text-green-800">진행 중인 작업 지시</h2>
          </div>
          <div class="divide-y max-h-[500px] overflow-y-auto">
            <div
              v-for="workOrder in inProgressWorkOrders"
              :key="workOrder.id"
              class="px-4 py-3 hover:bg-green-50 cursor-pointer transition-colors"
              :class="{ 'bg-yellow-50': workOrder.source_request_modified }"
              @click="openWorkOrderDetail(workOrder.id)"
            >
              <div class="flex justify-between items-start">
                <div class="flex items-center gap-2">
                  <p class="font-medium text-blue-600 hover:underline">{{ workOrder.wo_number }}</p>
                  <!-- v0.21.0: 원본 요청서 수정됨 배지 -->
                  <span
                    v-if="workOrder.source_request_modified"
                    class="px-1.5 py-0.5 text-xs bg-yellow-500 text-white rounded animate-pulse"
                    title="원본 생산요청서가 수정되었습니다"
                  >
                    수정됨
                  </span>
                </div>
                <span :class="getWorkOrderStatusBadgeClass(workOrder.status)">
                  {{ getWorkOrderStatusLabel(workOrder.status) }}
                </span>
              </div>
              <div class="text-sm text-gray-500">{{ getWorkOrderProductInfo(workOrder) }}</div>
              <div class="mt-1 flex justify-between text-xs text-gray-400">
                <span>수량: {{ formatNumber(getWorkOrderQuantity(workOrder)) }}</span>
                <span>{{ formatDate(workOrder.created_at) }}</span>
              </div>
            </div>
            <div v-if="inProgressWorkOrders.length === 0" class="px-4 py-8 text-center text-gray-500">
              진행 중인 작업 지시가 없습니다.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 생산 요청 상세 모달 -->
    <ProductionRequestDetailModal
      v-if="showRequestDetailModal && selectedRequestId !== null"
      :request-id="selectedRequestId"
      @close="closeRequestDetailModal"
      @approve="handleRequestApprove"
      @reject="handleRequestReject"
      @hold="handleRequestHold"
      @release-hold="handleRequestReleaseHold"
      @cancel="handleRequestCancel"
      @edit="handleRequestEdit"
    />

    <!-- 작업지시 상세/수정 모달 -->
    <WorkOrderFormModal
      v-if="showWorkOrderModal"
      :work-order-id="selectedWorkOrderId"
      @close="closeWorkOrderModal"
      @saved="handleWorkOrderSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { productionRequestApi, type ProductionRequestListItem } from '@/api/productionRequest'
import { workOrderApi, type WorkOrderListItem } from '@/api/workOrder'
import ProductionRequestDetailModal from '@/views/production/components/ProductionRequestDetailModal.vue'
import WorkOrderFormModal from '@/views/production/components/WorkOrderFormModal.vue'

// 부모에게 데이터 변경 알림
const emit = defineEmits<{
  (e: 'data-changed'): void
}>()

// 상태
const loading = ref(true)
const allRequests = ref<ProductionRequestListItem[]>([])
const allWorkOrders = ref<WorkOrderListItem[]>([])

// 모달 상태
const showRequestDetailModal = ref(false)
const selectedRequestId = ref<number | null>(null)
const showWorkOrderModal = ref(false)
const selectedWorkOrderId = ref<number | null>(null)

// 상태별 카운트
const statusCounts = computed(() => {
  return allRequests.value.reduce((acc: Record<string, number>, req) => {
    acc[req.status] = (acc[req.status] || 0) + 1
    return acc
  }, {})
})

// 처리 대기 요청 (REQUESTED, HOLD)
const pendingRequests = computed(() => {
  return allRequests.value
    .filter(r => r.status === 'REQUESTED' || r.status === 'HOLD')
    .slice(0, 10)
})

// 진행 중인 작업 지시 (승인 ~ 포장 완료)
const activeWorkOrderStatuses = ['APPROVED', 'ISSUED', 'IN_PROGRESS', 'INSPECTION', 'PACKED']
const inProgressWorkOrders = computed(() => {
  return allWorkOrders.value
    .filter(w => activeWorkOrderStatuses.includes(w.status))
    .sort((a, b) => {
      // 상태 우선순위로 정렬
      const statusOrder = activeWorkOrderStatuses.indexOf(a.status) - activeWorkOrderStatuses.indexOf(b.status)
      if (statusOrder !== 0) return statusOrder
      // 같은 상태면 생성일 기준 정렬
      return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
    })
    .slice(0, 20)
})

// 데이터 로드
const loadData = async () => {
  loading.value = true
  try {
    // 생산 요청 전체 목록
    const requestsRes = await productionRequestApi.getAll({ limit: 1000 })
    allRequests.value = requestsRes.items || []

    // 작업 지시 전체 목록
    const workOrdersRes = await workOrderApi.getAll({ limit: 1000 })
    allWorkOrders.value = workOrdersRes.items || []

  } catch (error) {
    console.error('데이터 로드 실패:', error)
  } finally {
    loading.value = false
  }
}

// 상태 라벨
const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    REQUESTED: '요청됨',
    APPROVED: '승인',
    HOLD: '보류',
    REJECTED: '반려',
    COMPLETED: '완료',
    CANCELLED: '취소'
  }
  return labels[status] || status
}

// 상태 배지 클래스
const getStatusBadgeClass = (status: string) => {
  const classes: Record<string, string> = {
    REQUESTED: 'px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800',
    APPROVED: 'px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-800',
    HOLD: 'px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-800',
    REJECTED: 'px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-800',
    COMPLETED: 'px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-800',
    CANCELLED: 'px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-800'
  }
  return classes[status] || 'px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-800'
}

// 작업지시 상태 라벨
const getWorkOrderStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    RECEIVED: '접수',
    APPROVED: '승인',
    ISSUED: '출고',
    IN_PROGRESS: '작업중',
    INSPECTION: '검사',
    PACKED: '포장',
    SHIPPED: '출하',
    CANCELLED: '취소'
  }
  return labels[status] || status
}

// 작업지시 상태 배지 클래스
const getWorkOrderStatusBadgeClass = (status: string) => {
  const classes: Record<string, string> = {
    RECEIVED: 'px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-800',
    APPROVED: 'px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800',
    ISSUED: 'px-2 py-0.5 text-xs rounded-full bg-indigo-100 text-indigo-800',
    IN_PROGRESS: 'px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-800',
    INSPECTION: 'px-2 py-0.5 text-xs rounded-full bg-orange-100 text-orange-800',
    PACKED: 'px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-800',
    SHIPPED: 'px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-800',
    CANCELLED: 'px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-800'
  }
  return classes[status] || 'px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-800'
}

// 작업지시 제품 정보 (다중 제품 지원)
const getWorkOrderProductInfo = (workOrder: WorkOrderListItem) => {
  if (workOrder.products && workOrder.products.length > 0) {
    const firstProduct = workOrder.products[0]
    const partNumber = firstProduct?.product_part?.part_number_display || firstProduct?.product_part?.part_number || '-'
    if (workOrder.products.length > 1) {
      return `${partNumber} 외 ${workOrder.products.length - 1}종`
    }
    return partNumber
  }
  return workOrder.product_part?.part_number || '-'
}

// 작업지시 수량 (다중 제품 지원)
const getWorkOrderQuantity = (workOrder: WorkOrderListItem) => {
  if (workOrder.products && workOrder.products.length > 0) {
    return workOrder.products.reduce((sum: number, p: any) => sum + Number(p.order_quantity || 0), 0)
  }
  return workOrder.order_quantity || 0
}

// 날짜 포맷
const formatDate = (dateString: string) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
}

// 숫자 포맷
const formatNumber = (num: number) => {
  return num?.toLocaleString('ko-KR') || '0'
}

// 생산 요청 상세 모달 열기
function openRequestDetail(id: number) {
  selectedRequestId.value = id
  showRequestDetailModal.value = true
}

function closeRequestDetailModal() {
  showRequestDetailModal.value = false
  selectedRequestId.value = null
}

// 생산 요청 상태 변경 핸들러
async function handleRequestApprove(id: number) {
  if (!confirm('승인하시겠습니까?')) return
  try {
    await productionRequestApi.approve(id)
    loadData()
    emit('data-changed')
    closeRequestDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '승인 실패')
  }
}

async function handleRequestReject(id: number) {
  const reason = prompt('반려 사유를 입력하세요:')
  if (!reason) return
  try {
    await productionRequestApi.reject(id, { rejection_reason: reason })
    loadData()
    emit('data-changed')
    closeRequestDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '반려 실패')
  }
}

async function handleRequestHold(id: number) {
  if (!confirm('보류 처리하시겠습니까?')) return
  try {
    await productionRequestApi.hold(id)
    loadData()
    emit('data-changed')
    closeRequestDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '보류 처리 실패')
  }
}

async function handleRequestReleaseHold(id: number) {
  if (!confirm('보류를 해제하시겠습니까?')) return
  try {
    await productionRequestApi.releaseHold(id)
    loadData()
    emit('data-changed')
    closeRequestDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '보류 해제 실패')
  }
}

async function handleRequestCancel(id: number) {
  const reason = prompt('취소 사유를 입력하세요:')
  if (reason === null) return
  try {
    await productionRequestApi.cancel(id, reason)
    loadData()
    emit('data-changed')
    closeRequestDetailModal()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '취소 실패')
  }
}

function handleRequestEdit(id: number) {
  // 수정은 생산 요청서 관리 탭으로 이동해서 처리
  closeRequestDetailModal()
  emit('data-changed')
}

// 작업지시 상세 모달 열기
function openWorkOrderDetail(id: number) {
  selectedWorkOrderId.value = id
  showWorkOrderModal.value = true
}

function closeWorkOrderModal() {
  showWorkOrderModal.value = false
  selectedWorkOrderId.value = null
}

function handleWorkOrderSaved() {
  closeWorkOrderModal()
  loadData()
  emit('data-changed')
}

onMounted(() => {
  loadData()
})

// 부모 컴포넌트에서 호출할 수 있도록 expose
defineExpose({
  loadData
})
</script>
