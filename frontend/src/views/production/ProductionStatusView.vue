<template>
  <div class="max-w-screen-2xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
    <!-- 헤더 -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">요청 현황</h1>
      <p class="mt-1 text-sm text-gray-500">생산 요청 및 작업 지시 현황을 한눈에 확인합니다.</p>
    </div>

    <!-- 로딩 -->
    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
    </div>

    <div v-else>
      <!-- 상태별 요약 카드 -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <!-- 대기 중 -->
        <div class="bg-white rounded-lg shadow p-4 border-l-4 border-yellow-400">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">대기 중</p>
              <p class="text-2xl font-bold text-yellow-600">{{ statusCounts.PENDING || 0 }}</p>
            </div>
            <div class="p-3 bg-yellow-100 rounded-full">
              <svg class="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>

        <!-- 승인됨 -->
        <div class="bg-white rounded-lg shadow p-4 border-l-4 border-blue-400">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">승인됨</p>
              <p class="text-2xl font-bold text-blue-600">{{ statusCounts.APPROVED || 0 }}</p>
            </div>
            <div class="p-3 bg-blue-100 rounded-full">
              <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>

        <!-- 진행 중 -->
        <div class="bg-white rounded-lg shadow p-4 border-l-4 border-green-400">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">진행 중</p>
              <p class="text-2xl font-bold text-green-600">{{ statusCounts.IN_PROGRESS || 0 }}</p>
            </div>
            <div class="p-3 bg-green-100 rounded-full">
              <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
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
      </div>

      <!-- 최근 요청 목록 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- 최근 생산 요청 -->
        <div class="bg-white rounded-lg shadow">
          <div class="px-4 py-3 border-b flex justify-between items-center">
            <h2 class="text-lg font-semibold text-gray-800">최근 생산 요청</h2>
            <RouterLink to="/production/requests" class="text-sm text-blue-600 hover:underline">
              전체 보기 →
            </RouterLink>
          </div>
          <div class="divide-y">
            <div
              v-for="request in recentRequests"
              :key="request.id"
              class="px-4 py-3 hover:bg-gray-50 cursor-pointer"
            >
              <div class="flex justify-between items-start">
                <div>
                  <p class="font-medium text-gray-900">{{ request.request_number }}</p>
                  <p class="text-sm text-gray-500">{{ request.product_part?.part_number || '-' }}</p>
                </div>
                <span :class="getStatusBadgeClass(request.status)">
                  {{ getStatusLabel(request.status) }}
                </span>
              </div>
              <div class="mt-1 flex justify-between text-xs text-gray-400">
                <span>수량: {{ request.requested_quantity }}</span>
                <span>{{ request.created_at ? formatDate(request.created_at) : '' }}</span>
              </div>
            </div>
            <div v-if="recentRequests.length === 0" class="px-4 py-8 text-center text-gray-500">
              최근 요청이 없습니다.
            </div>
          </div>
        </div>

        <!-- 최근 작업 지시 -->
        <div class="bg-white rounded-lg shadow">
          <div class="px-4 py-3 border-b flex justify-between items-center">
            <h2 class="text-lg font-semibold text-gray-800">최근 작업 지시</h2>
            <RouterLink to="/production/work-orders" class="text-sm text-blue-600 hover:underline">
              전체 보기 →
            </RouterLink>
          </div>
          <div class="divide-y">
            <div
              v-for="workOrder in recentWorkOrders"
              :key="workOrder.id"
              class="px-4 py-3 hover:bg-gray-50 cursor-pointer"
            >
              <div class="flex justify-between items-start">
                <div>
                  <p class="font-medium text-gray-900">{{ workOrder.wo_number }}</p>
                  <p class="text-sm text-gray-500">{{ workOrder.product_part?.part_number || '-' }}</p>
                </div>
                <span :class="getWorkOrderStatusBadgeClass(workOrder.status)">
                  {{ getWorkOrderStatusLabel(workOrder.status) }}
                </span>
              </div>
              <div class="mt-1 flex justify-between text-xs text-gray-400">
                <span>수량: {{ workOrder.order_quantity }}</span>
                <span>{{ formatDate(workOrder.created_at) }}</span>
              </div>
            </div>
            <div v-if="recentWorkOrders.length === 0" class="px-4 py-8 text-center text-gray-500">
              최근 작업 지시가 없습니다.
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { productionRequestApi, type ProductionRequestListItem } from '@/api/productionRequest'
import { workOrderApi, type WorkOrderListItem } from '@/api/workOrder'

// 상태
const loading = ref(true)
const statusCounts = ref<Record<string, number>>({})
const recentRequests = ref<ProductionRequestListItem[]>([])
const recentWorkOrders = ref<WorkOrderListItem[]>([])

// 데이터 로드
const loadData = async () => {
  loading.value = true
  try {
    // 생산 요청 목록 (최근 5개)
    const requestsRes = await productionRequestApi.getAll({ limit: 5 })
    recentRequests.value = requestsRes.items || []

    // 상태별 카운트 계산
    const allRequestsRes = await productionRequestApi.getAll({ limit: 1000 })
    const allRequests = allRequestsRes.items || []
    statusCounts.value = allRequests.reduce((acc: Record<string, number>, req: ProductionRequestListItem) => {
      acc[req.status] = (acc[req.status] || 0) + 1
      return acc
    }, {})

    // 작업 지시 목록 (최근 5개)
    const workOrdersRes = await workOrderApi.getAll({ limit: 5 })
    recentWorkOrders.value = workOrdersRes.items || []

  } catch (error) {
    console.error('데이터 로드 실패:', error)
  } finally {
    loading.value = false
  }
}

// 상태 라벨
const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    PENDING: '대기',
    APPROVED: '승인',
    IN_PROGRESS: '진행중',
    COMPLETED: '완료',
    CANCELLED: '취소'
  }
  return labels[status] || status
}

// 상태 배지 클래스
const getStatusBadgeClass = (status: string) => {
  const classes: Record<string, string> = {
    PENDING: 'px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-800',
    APPROVED: 'px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800',
    IN_PROGRESS: 'px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-800',
    COMPLETED: 'px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-800',
    CANCELLED: 'px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-800'
  }
  return classes[status] || 'px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-800'
}

// 작업지시 상태 라벨
const getWorkOrderStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    DRAFT: '초안',
    PENDING: '대기',
    IN_PROGRESS: '진행중',
    COMPLETED: '완료',
    CANCELLED: '취소'
  }
  return labels[status] || status
}

// 작업지시 상태 배지 클래스
const getWorkOrderStatusBadgeClass = (status: string) => {
  const classes: Record<string, string> = {
    DRAFT: 'px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-800',
    PENDING: 'px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-800',
    IN_PROGRESS: 'px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-800',
    COMPLETED: 'px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800',
    CANCELLED: 'px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-800'
  }
  return classes[status] || 'px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-800'
}

// 날짜 포맷
const formatDate = (dateString: string) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
}

onMounted(() => {
  loadData()
})
</script>
