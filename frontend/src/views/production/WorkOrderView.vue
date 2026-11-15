<template>
  <div class="p-6">
    <!-- 헤더 -->
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">작업지시서 관리</h1>
      <p class="text-xs text-gray-400">생산 요청을 처리하고 작업지시서를 관리합니다.</p>
      <button
        @click="openCreateModal"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        작업지시서 등록
      </button>
    </div>

    <!-- 대기 중인 생산요청 (v0.20.0) -->
    <div v-if="pendingRequests.length > 0" class="bg-yellow-50 border border-yellow-200 rounded-lg shadow p-4 mb-6">
      <div class="flex justify-between items-center mb-3">
        <h2 class="text-lg font-semibold text-yellow-800 flex items-center gap-2">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          대기 중인 생산요청 ({{ pendingRequests.length }}건)
        </h2>
        <button
          @click="showPendingSection = !showPendingSection"
          class="text-yellow-600 hover:text-yellow-800 text-sm"
        >
          {{ showPendingSection ? '접기' : '펼치기' }}
        </button>
      </div>
      <div v-if="showPendingSection" class="overflow-x-auto">
        <table class="min-w-full divide-y divide-yellow-200">
          <thead>
            <tr>
              <th class="px-3 py-2 text-left text-xs font-medium text-yellow-700">요청번호</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-yellow-700">고객사</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-yellow-700">제품</th>
              <th class="px-3 py-2 text-right text-xs font-medium text-yellow-700">수량</th>
              <th class="px-3 py-2 text-center text-xs font-medium text-yellow-700">납기</th>
              <th class="px-3 py-2 text-center text-xs font-medium text-yellow-700">우선순위</th>
              <th class="px-3 py-2 text-center text-xs font-medium text-yellow-700">작업</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-yellow-100">
            <tr v-for="pr in pendingRequests" :key="pr.id" class="hover:bg-yellow-100">
              <td class="px-3 py-2 text-sm">
                <button @click="openPRDetail(pr.id)" class="text-blue-600 font-medium hover:underline hover:text-blue-800">
                  {{ pr.request_number }}
                </button>
              </td>
              <td class="px-3 py-2 text-sm">{{ pr.customer?.partner_name || '-' }}</td>
              <td class="px-3 py-2 text-sm">{{ pr.product_part?.part_name || pr.product_part?.part_number || '-' }}</td>
              <td class="px-3 py-2 text-sm text-right">{{ formatNumber(pr.requested_quantity ?? 0) }}</td>
              <td class="px-3 py-2 text-sm text-center">{{ pr.due_date ? formatDate(pr.due_date) : '-' }}</td>
              <td class="px-3 py-2 text-center">
                <span :class="['px-2 py-0.5 text-xs rounded-full', prPriorityStyles[pr.priority]]">
                  {{ prPriorityLabels[pr.priority] }}
                </span>
              </td>
              <td class="px-3 py-2 text-center">
                <div class="flex justify-center gap-2">
                  <button
                    @click="handleApprovePR(pr)"
                    class="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                    title="승인 및 작업지시서 생성"
                  >
                    승인
                  </button>
                  <button
                    @click="handleRejectPR(pr.id)"
                    class="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
                    title="반려"
                  >
                    반려
                  </button>
                  <button
                    @click="handleHoldPR(pr.id)"
                    class="px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200"
                    title="보류"
                  >
                    보류
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
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
            placeholder="지시번호, 고객주문번호"
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
            <option v-for="(label, key) in woStatusLabels" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>

        <!-- 거래처 필터 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">거래처</label>
          <select
            v-model="filters.customer_id"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            @change="loadData"
          >
            <option value="">전체</option>
            <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.partner_name }}</option>
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
            <option value="2">긴급</option>
            <option value="1">높음</option>
            <option value="0">보통</option>
          </select>
        </div>

        <!-- 출하예정일 범위 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">출하예정일</label>
          <div class="flex gap-2">
            <input
              v-model="filters.from_date"
              type="date"
              class="flex-1 px-2 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
              @change="loadData"
            />
            <input
              v-model="filters.to_date"
              type="date"
              class="flex-1 px-2 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
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
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">지시번호</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">완제품</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">고객사</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">지시수량</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">완료수량</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">우선순위</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">상태</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">출하예정</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">작업</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-if="loading">
            <td colspan="9" class="px-4 py-4 text-center text-gray-500">로딩 중...</td>
          </tr>
          <tr v-else-if="workOrders.length === 0">
            <td colspan="9" class="px-4 py-4 text-center text-gray-500">데이터가 없습니다.</td>
          </tr>
          <tr
            v-for="wo in workOrders"
            :key="wo.id"
            class="hover:bg-gray-50 cursor-pointer"
            @click="openDetailModal(wo.id)"
          >
            <td class="px-4 py-3 whitespace-nowrap">
              <span class="text-sm font-medium text-blue-600">{{ wo.wo_number }}</span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
              <!-- v0.19.0: 다중 제품 표시 -->
              <template v-if="wo.products && wo.products.length > 1">
                <div class="text-sm text-gray-900">
                  {{ wo.products[0]?.product_part?.part_name || '-' }}
                  <span class="text-xs text-blue-600 ml-1">외 {{ wo.products.length - 1 }}종</span>
                </div>
                <div class="text-xs text-gray-500 font-mono">
                  {{ wo.products[0]?.product_part?.part_number_display || wo.products[0]?.product_part?.part_number || '' }}
                </div>
              </template>
              <template v-else-if="wo.products && wo.products.length === 1">
                <div class="text-sm text-gray-900">{{ wo.products[0]?.product_part?.part_name || '-' }}</div>
                <div class="text-xs text-gray-500 font-mono">{{ wo.products[0]?.product_part?.part_number_display || wo.products[0]?.product_part?.part_number || '' }}</div>
              </template>
              <template v-else>
                <div class="text-sm text-gray-900">{{ wo.product_part?.part_name || '-' }}</div>
                <div class="text-xs text-gray-500 font-mono">{{ wo.product_part?.part_number_display || wo.product_part?.part_number || '' }}</div>
              </template>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
              {{ wo.customer?.name || '-' }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
              <!-- v0.19.0: 다중 제품 수량 표시 -->
              <template v-if="wo.products && wo.products.length > 0">
                {{ wo.products.reduce((sum, p) => sum + Number(p.order_quantity || 0), 0) }}
              </template>
              <template v-else>
                {{ wo.order_quantity }}
              </template>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-right">
              <span :class="getCompletedQty(wo) > 0 ? 'text-green-600' : 'text-gray-400'">
                {{ getCompletedQty(wo) }}
              </span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-center">
              <span :class="['px-2 py-1 text-xs rounded-full', priorityStyles[wo.priority as 0|1|2] || priorityStyles[0]]">
                {{ priorityLabels[wo.priority as 0|1|2] || '보통' }}
              </span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-center">
              <span :class="['px-2 py-1 text-xs rounded-full', woStatusStyles[wo.status]]">
                {{ woStatusLabels[wo.status] }}
              </span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500 text-center">
              {{ wo.shipping_scheduled_date ? formatDate(wo.shipping_scheduled_date) : '-' }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-center">
              <div class="flex justify-center gap-1" @click.stop>
                <!-- 상태별 다음 단계 버튼 -->
                <button
                  v-if="wo.status === 'RECEIVED'"
                  @click="handleApprove(wo.id)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100 transition-colors"
                  title="승인하기"
                >
                  승인
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <button
                  v-if="wo.status === 'APPROVED'"
                  @click="openIssueModal(wo.id)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-indigo-700 bg-indigo-50 rounded hover:bg-indigo-100 transition-colors"
                  title="부품 출고하기"
                >
                  출고
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <button
                  v-if="wo.status === 'ISSUED'"
                  @click="handleStartProduction(wo.id)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-yellow-700 bg-yellow-50 rounded hover:bg-yellow-100 transition-colors"
                  title="작업 시작하기"
                >
                  작업
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <button
                  v-if="wo.status === 'IN_PROGRESS'"
                  @click="openProductionCompleteModal(wo.id)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-orange-700 bg-orange-50 rounded hover:bg-orange-100 transition-colors"
                  title="작업 완료하기"
                >
                  완료
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <button
                  v-if="wo.status === 'INSPECTION'"
                  @click="handleCompleteInspection(wo.id)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-green-700 bg-green-50 rounded hover:bg-green-100 transition-colors"
                  title="검사 완료하기"
                >
                  검사
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <button
                  v-if="wo.status === 'PACKED'"
                  @click="handleShip(wo.id)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-purple-700 bg-purple-50 rounded hover:bg-purple-100 transition-colors"
                  title="출하 처리하기"
                >
                  출하
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <!-- 롤백 버튼 (SHIPPED, CANCELLED, RECEIVED 제외) -->
                <button
                  v-if="canRollback(wo.status)"
                  @click="handleRollback(wo.id, wo.status)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
                  title="이전 상태로 되돌리기"
                >
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                  </svg>
                  롤백
                </button>
                <!-- 완료 또는 취소된 경우 표시 -->
                <span
                  v-if="wo.status === 'SHIPPED'"
                  class="inline-flex items-center px-2 py-1 text-xs font-medium text-gray-500 bg-gray-100 rounded"
                >
                  완료
                </span>
                <!-- 취소됨: 복원 + 완전삭제 버튼 -->
                <template v-if="wo.status === 'CANCELLED'">
                  <button
                    @click="handleRestore(wo.id)"
                    class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-green-700 bg-green-50 rounded hover:bg-green-100 transition-colors"
                    title="작업지시서 복원하기"
                  >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    복원
                  </button>
                  <button
                    @click="handlePermanentDelete(wo.id)"
                    class="ml-1 p-1 text-red-400 hover:text-red-600 transition-colors"
                    title="완전 삭제"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </template>
                <!-- 취소 버튼 (출하완료, 취소 상태 제외) -->
                <button
                  v-if="wo.status !== 'SHIPPED' && wo.status !== 'CANCELLED'"
                  @click="handleCancel(wo.id)"
                  class="ml-1 p-1 text-gray-400 hover:text-red-600 transition-colors"
                  title="취소"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
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
        총 {{ pagination.total }}건 중 {{ (pagination.skip || 0) + 1 }} - {{ Math.min((pagination.skip || 0) + workOrders.length, pagination.total) }}건
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

    <!-- 작업지시서 등록/상세 모달 -->
    <WorkOrderFormModal
      v-if="showFormModal"
      :work-order-id="selectedWOId"
      @close="showFormModal = false"
      @saved="handleSaved"
    />

    <!-- 부품 출고 모달 -->
    <WorkOrderIssueModal
      v-if="showIssueModal && issueWOId"
      :work-order-id="issueWOId"
      @close="showIssueModal = false"
      @issued="handleIssued"
    />

    <!-- 작업 완료 모달 -->
    <WorkOrderCompleteModal
      v-if="showCompleteModal && completeWOId"
      :work-order-id="completeWOId"
      @close="showCompleteModal = false"
      @completed="handleCompleted"
    />

    <!-- 생산요청 상세 모달 -->
    <ProductionRequestDetailModal
      v-if="showPRDetailModal && prDetailId"
      :request-id="prDetailId"
      @close="showPRDetailModal = false"
      @edit="showPRDetailModal = false"
      @approve="handlePRStatusChanged"
      @reject="handlePRStatusChanged"
      @hold="handlePRStatusChanged"
      @release-hold="handlePRStatusChanged"
      @cancel="handlePRStatusChanged"
      @delete="handlePRStatusChanged"
    />
  </div>
</template>

<script setup lang="ts">
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import { ref, reactive, computed, onMounted } from 'vue'
import {
  workOrderApi,
  type WorkOrderListItem,
  type WorkOrderSearchParams,
  woStatusLabels,
  woStatusStyles,
  priorityLabels,
  priorityStyles,
} from '@/api/workOrder'
import { partnerApi } from '@/api/partner'
import {
  productionRequestApi,
  priorityLabels as prPriorityLabels,
  priorityStyles as prPriorityStyles,
  type ProductionRequest
} from '@/api/productionRequest'
import WorkOrderFormModal from '@/views/production/components/WorkOrderFormModal.vue'
import WorkOrderIssueModal from '@/views/production/components/WorkOrderIssueModal.vue'
import WorkOrderCompleteModal from '@/views/production/components/WorkOrderCompleteModal.vue'
import ProductionRequestDetailModal from '@/views/production/components/ProductionRequestDetailModal.vue'

// 상태
const loading = ref(false)
const workOrders = ref<WorkOrderListItem[]>([])
const customers = ref<any[]>([])
const pagination = reactive({ total: 0, skip: 0, limit: 20 })

// 대기 중인 생산요청 (v0.20.0)
const pendingRequests = ref<ProductionRequest[]>([])
const showPendingSection = ref(true)
const showPRDetailModal = ref(false)
const prDetailId = ref<number | null>(null)

// 필터
const filters = reactive<WorkOrderSearchParams>({
  keyword: '',
  status: undefined,
  customer_id: undefined,
  priority: undefined,
  from_date: '',
  to_date: '',
})

// 모달
const showFormModal = ref(false)
const selectedWOId = ref<number | null>(null)
const showIssueModal = ref(false)
const issueWOId = ref<number | null>(null)
const showCompleteModal = ref(false)
const completeWOId = ref<number | null>(null)

// 계산된 속성
const currentPage = computed(() => Math.floor((pagination.skip || 0) / pagination.limit) + 1)
const totalPages = computed(() => Math.ceil(pagination.total / pagination.limit) || 1)

// 데이터 로드
const debouncedSearch = useDebouncedSearch(() => loadData())
async function loadData() {
  loading.value = true
  try {
    const params: WorkOrderSearchParams = {
      ...filters,
      skip: pagination.skip,
      limit: pagination.limit,
    }
    // 빈 문자열을 undefined로 변환
    if (!params.keyword) params.keyword = undefined
    if (!params.status) params.status = undefined
    if (!params.customer_id) params.customer_id = undefined
    if (params.priority === undefined || params.priority === null || (params.priority as unknown) === '') {
      params.priority = undefined
    } else {
      params.priority = Number(params.priority)
    }
    if (!params.from_date) params.from_date = undefined
    if (!params.to_date) params.to_date = undefined

    const response = await workOrderApi.getAll(params)
    workOrders.value = response.items
    pagination.total = response.total
  } catch (error) {
    console.error('작업지시서 목록 조회 실패:', error)
    alert('작업지시서 목록을 불러오는데 실패했습니다.')
  } finally {
    loading.value = false
  }
}

// 거래처 목록 로드 (공급사+고객사 통합)
async function loadCustomers() {
  try {
    const response = await partnerApi.getAll({ limit: 1000 })
    customers.value = response.data.items
  } catch (error) {
    console.error('거래처 목록 조회 실패:', error)
  }
}

// 생산요청 상세 보기
function openPRDetail(id: number) {
  prDetailId.value = id
  showPRDetailModal.value = true
}

function handlePRStatusChanged() {
  showPRDetailModal.value = false
  loadPendingRequests()
  loadData()
}

// 대기 중인 생산요청 로드 (v0.20.0)
async function loadPendingRequests() {
  try {
    pendingRequests.value = await productionRequestApi.getPending(0, 20)
  } catch (error) {
    console.error('대기 중인 생산요청 조회 실패:', error)
  }
}

// 생산요청 승인 후 작업지시서 생성 (v0.20.0, v0.22.0 개선)
async function handleApprovePR(pr: ProductionRequest) {
  if (!confirm(`[${pr.request_number}] 요청에 대한 작업지시서를 생성하시겠습니까?`)) return
  try {
    // v0.22.0: PR 상세 조회 (다중 제품 + 첨부파일 포함)
    // 승인은 WO 등록 완료 시점에 수행 (모달에서 처리)
    const prDetail = await productionRequestApi.getById(pr.id)

    selectedWOId.value = null
    sessionStorage.setItem('createFromPR', JSON.stringify({
      production_request_id: prDetail.id,
      customer_id: prDetail.customer_id,
      customer_order_no: prDetail.customer_order_no,
      items: prDetail.items || [],
      attachment_files: prDetail.attachment_files || [],
      product_part_id: prDetail.product_part_id,
      order_quantity: prDetail.requested_quantity,
    }))
    showFormModal.value = true
    // 대기 목록은 새로고침하지 않음 (WO 등록 완료 후 갱신)
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '요청 정보 조회에 실패했습니다.')
  }
}

// 생산요청 반려 (v0.20.0)
async function handleRejectPR(id: number) {
  const reason = prompt('반려 사유를 입력하세요:')
  if (!reason) return
  try {
    await productionRequestApi.reject(id, { rejection_reason: reason })
    alert('반려되었습니다.')
    loadPendingRequests()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '반려에 실패했습니다.')
  }
}

// 생산요청 보류 (v0.20.0)
async function handleHoldPR(id: number) {
  if (!confirm('보류 처리하시겠습니까?')) return
  try {
    await productionRequestApi.hold(id)
    alert('보류되었습니다.')
    loadPendingRequests()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '보류 처리에 실패했습니다.')
  }
}

// 필터 초기화
function resetFilters() {
  filters.keyword = ''
  filters.status = undefined
  filters.customer_id = undefined
  filters.priority = undefined
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
  selectedWOId.value = null
  showFormModal.value = true
}

function openDetailModal(id: number) {
  selectedWOId.value = id
  showFormModal.value = true
}

function openIssueModal(id: number) {
  issueWOId.value = id
  showIssueModal.value = true
}

function openProductionCompleteModal(id: number) {
  completeWOId.value = id
  showCompleteModal.value = true
}

// 액션
async function handleApprove(id: number) {
  if (!confirm('작업지시를 승인하시겠습니까?')) return
  try {
    await workOrderApi.approve(id)
    alert('승인되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('승인 실패:', error)
    alert(error.response?.data?.detail?.message || '승인에 실패했습니다.')
  }
}

async function handleStartProduction(id: number) {
  if (!confirm('작업을 시작하시겠습니까?')) return
  try {
    await workOrderApi.startProduction(id)
    alert('작업이 시작되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('작업 시작 실패:', error)
    alert(error.response?.data?.detail?.message || '작업 시작에 실패했습니다.')
  }
}

async function handleCompleteInspection(id: number) {
  if (!confirm('검사를 완료하시겠습니까?')) return
  try {
    await workOrderApi.completeInspection(id)
    alert('검사가 완료되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('검사 완료 실패:', error)
    alert(error.response?.data?.detail?.message || '검사 완료에 실패했습니다.')
  }
}

async function handleShip(id: number) {
  if (!confirm('출하 처리하시겠습니까?')) return
  try {
    await workOrderApi.ship(id)
    alert('출하가 완료되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('출하 실패:', error)
    alert(error.response?.data?.detail?.message || '출하에 실패했습니다.')
  }
}

// 취소 처리 (휴지통 클릭 시)
async function handleCancel(id: number) {
  if (!confirm('작업지시서를 취소하시겠습니까?\n출고된 부품은 재고로 복구됩니다.')) return

  const reason = prompt('취소 사유를 입력하세요 (선택사항):')
  if (reason === null) return // prompt 취소됨

  try {
    await workOrderApi.cancel(id, reason || undefined)
    alert('작업지시서가 취소되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('취소 실패:', error)
    alert(error.response?.data?.detail?.message || '취소에 실패했습니다.')
  }
}

// 완전 삭제 (취소된 작업지시서만)
async function handlePermanentDelete(id: number) {
  if (!confirm('작업지시서를 완전히 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.')) return
  try {
    await workOrderApi.delete(id)
    alert('삭제되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('삭제 실패:', error)
    alert(error.response?.data?.detail?.message || '삭제에 실패했습니다.')
  }
}

// 롤백 가능 여부 확인
function canRollback(status: string): boolean {
  // SHIPPED, CANCELLED, RECEIVED는 롤백 불가
  return !['SHIPPED', 'CANCELLED', 'RECEIVED'].includes(status)
}

// 상태 롤백 처리
const rollbackLabels: Record<string, string> = {
  'APPROVED': '접수 상태로',
  'ISSUED': '승인 상태로 (재고 복구)',
  'IN_PROGRESS': '출고 상태로',
  'INSPECTION': '작업중 상태로',
  'PACKED': '검사 상태로',
}

async function handleRollback(id: number, currentStatus: string) {
  const label = rollbackLabels[currentStatus] || '이전 상태로'
  if (!confirm(`${label} 롤백하시겠습니까?
출고 상태에서 롤백 시 재고가 복구됩니다.`)) return
  try {
    await workOrderApi.rollback(id)
    alert('롤백이 완료되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('롤백 실패:', error)
    alert(error.response?.data?.detail?.message || '롤백에 실패했습니다.')
  }
}

async function handleRestore(id: number) {
  if (!confirm('취소된 작업지시서를 복원하시겠습니까?\n출고 상태였던 경우 승인 상태로 복원됩니다.')) return
  try {
    await workOrderApi.restore(id)
    alert('작업지시서가 복원되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('복원 실패:', error)
    alert(error.response?.data?.detail?.message || '복원에 실패했습니다.')
  }
}

function handleSaved() {
  showFormModal.value = false
  loadData()
  loadPendingRequests()  // v0.20.0: 생산요청 목록 새로고침
}

function handleIssued() {
  showIssueModal.value = false
  loadData()
}

function handleCompleted() {
  showCompleteModal.value = false
  loadData()
}

// v0.19.0: 다중 제품 완료수량 합계
function getCompletedQty(wo: WorkOrderListItem): number {
  if (wo.products && wo.products.length > 0) {
    return wo.products.reduce((sum, p) => sum + Number(p.completed_quantity || 0), 0)
  }
  return Number(wo.completed_quantity || 0)
}

// 포맷
function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('ko-KR')
}

// 포맷 (숫자)
function formatNumber(num: number): string {
  return num?.toLocaleString('ko-KR') || '0'
}

// 초기화
onMounted(() => {
  loadCustomers()
  loadPendingRequests()  // v0.20.0: 대기 중인 생산요청 로드
  loadData()
})
</script>
