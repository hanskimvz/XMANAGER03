<template>
  <div
    ref="modalOverlay"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    tabindex="-1"
    @keydown.escape="$emit('close')"
  >
    <div class="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] overflow-hidden" @click.stop>
      <!-- 헤더 -->
      <div class="flex justify-between items-center px-6 py-4 border-b bg-indigo-50">
        <div>
          <h2 class="text-xl font-bold text-gray-800">부품 출고 (로트 선택)</h2>
          <p class="text-sm text-gray-600">{{ workOrder?.wo_number }}</p>
        </div>
        <button @click="$emit('close')" class="text-gray-500 hover:text-gray-700">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 본문 -->
      <div class="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
        <!-- 로딩 -->
        <div v-if="loading" class="text-center py-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p class="mt-2 text-gray-500">로딩 중...</p>
        </div>

        <div v-else-if="workOrder">
          <!-- 기본 정보 -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
            <div>
              <label class="text-xs text-gray-500">완제품</label>
              <p class="font-medium">{{ workOrder.product_part?.part_name || '-' }}</p>
              <p class="text-xs text-gray-500 font-mono">{{ workOrder.product_part?.part_number_display || workOrder.product_part?.part_number }}</p>
            </div>
            <div>
              <label class="text-xs text-gray-500">지시수량</label>
              <p class="font-medium">{{ workOrder.order_quantity }}</p>
            </div>
            <div>
              <label class="text-xs text-gray-500">고객사</label>
              <p class="font-medium">{{ workOrder.customer?.partner_name || '-' }}</p>
            </div>
            <div>
              <label class="text-xs text-gray-500">상태</label>
              <span :class="['px-2 py-1 text-xs rounded-full', woStatusStyles[workOrder.status]]">
                {{ woStatusLabels[workOrder.status] }}
              </span>
            </div>
          </div>

          <!-- FIFO 기본 설정 -->
          <div class="mb-4 p-3 bg-blue-50 rounded-lg flex items-center justify-between">
            <div class="flex items-center gap-2">
              <label class="flex items-center cursor-pointer">
                <input
                  v-model="globalFifo"
                  type="checkbox"
                  class="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mr-2"
                />
                <span class="text-sm font-medium text-gray-700">전체 항목 FIFO 자동 적용</span>
              </label>
            </div>
            <button
              @click="fillAllIssue"
              class="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
            >
              가용수량 전체 출고
            </button>
          </div>

          <!-- 재고 부족 경고 -->
          <div v-if="hasInsufficientStock" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div class="flex items-center gap-2 text-red-700">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span class="font-medium">재고가 부족한 부품이 있습니다.</span>
            </div>
          </div>

          <!-- 출고 항목 테이블 -->
          <div class="mb-6">
            <h3 class="text-lg font-semibold mb-3">출고 항목</h3>
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">레벨</th>
                    <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">품번/품명</th>
                    <th class="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">필요</th>
                    <th class="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">가용</th>
                    <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">출고수량</th>
                    <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">FIFO</th>
                    <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">로트선택</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr
                    v-for="(item, index) in issueItems"
                    :key="item.item_id"
                    class="hover:bg-gray-50"
                    :class="{ 'bg-red-50': item.stock_status === 'INSUFFICIENT' }"
                  >
                    <td class="px-3 py-3 whitespace-nowrap text-sm text-gray-500">
                      <span :style="{ paddingLeft: (item.bom_level - 1) * 12 + 'px' }">
                        L{{ item.bom_level }}
                      </span>
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap">
                      <div class="text-sm font-mono text-blue-600">{{ item.part_number }}</div>
                      <div class="text-sm text-gray-600">{{ item.part_name }}</div>
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-sm text-right">
                      {{ item.required_quantity }}
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-sm text-right">
                      <span :class="item.stock_status === 'INSUFFICIENT' ? 'text-red-600 font-medium' : 'text-gray-900'">
                        {{ item.current_stock }}
                      </span>
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-center">
                      <input
                        v-model.number="item.issue_quantity"
                        type="number"
                        min="0"
                        :max="item.current_stock"
                        class="w-20 px-2 py-1 border border-gray-300 rounded text-center focus:ring-2 focus:ring-indigo-500"
                        @input="validateIssueQuantity(index)"
                      />
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-center">
                      <input
                        v-model="item.use_fifo"
                        type="checkbox"
                        class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-center">
                      <button
                        v-if="!item.use_fifo && item.issue_quantity > 0"
                        @click="openLotSelection(index)"
                        class="px-2 py-1 text-xs bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200"
                      >
                        {{ item.lot_selections?.length ? `${item.lot_selections.length}개 로트` : '선택' }}
                      </button>
                      <span v-else-if="item.use_fifo" class="text-xs text-gray-400">자동</span>
                      <span v-else class="text-xs text-gray-400">-</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 요약 -->
          <div class="p-4 bg-indigo-50 rounded-lg">
            <div class="grid grid-cols-3 gap-4 text-center">
              <div>
                <p class="text-sm text-gray-600">총 출고 항목</p>
                <p class="text-2xl font-bold text-gray-800">{{ issueItems.filter(i => i.issue_quantity > 0).length }} / {{ issueItems.length }}</p>
              </div>
              <div>
                <p class="text-sm text-gray-600">FIFO 자동</p>
                <p class="text-2xl font-bold text-blue-600">{{ issueItems.filter(i => i.use_fifo && i.issue_quantity > 0).length }}</p>
              </div>
              <div>
                <p class="text-sm text-gray-600">수동 선택</p>
                <p class="text-2xl font-bold text-indigo-600">{{ issueItems.filter(i => !i.use_fifo && i.issue_quantity > 0).length }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 푸터 -->
      <div class="flex justify-end gap-3 px-6 py-4 border-t bg-gray-50">
        <button
          @click="$emit('close')"
          class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          취소
        </button>
        <button
          @click="handleIssue"
          :disabled="saving || !canIssue"
          class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ saving ? '처리 중...' : '부품 출고' }}
        </button>
      </div>
    </div>

    <!-- 로트 선택 모달 -->
    <LotSelectionModal
      :show="showLotSelection"
      :part-id="selectedItem?.part_id || 0"
      :part-number="selectedItem?.part_number || ''"
      :part-name="selectedItem?.part_name || ''"
      :required-quantity="selectedItem?.issue_quantity || 0"
      @close="showLotSelection = false"
      @confirm="handleLotSelectionConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import {
  workOrderApi,
  type WorkOrder,
  type BOMPreviewResponse,
  woStatusLabels,
  woStatusStyles,
} from '@/api/workOrder'
import {
  workOrderLotApi,
  inventoryLotApi,
  type WorkOrderIssueRequest,
  type WorkOrderItemIssueRequest,
  type LotIssueItem,
} from '@/api/inventoryLot'
import LotSelectionModal from './LotSelectionModal.vue'

// Props
const props = defineProps<{
  workOrderId: number
}>()

// Emits
const emit = defineEmits<{
  close: []
  issued: []
}>()

// 상태
const loading = ref(false)
const saving = ref(false)
const workOrder = ref<WorkOrder | null>(null)
const bomPreview = ref<BOMPreviewResponse | null>(null)
const globalFifo = ref(true)

// 로트 선택 모달
const showLotSelection = ref(false)
const selectedItemIndex = ref(-1)

// 출고 항목 타입
interface IssueItem {
  item_id: number
  part_id: number
  part_number: string
  part_name: string
  bom_level: number
  required_quantity: number
  current_stock: number
  issue_quantity: number
  stock_status: 'SUFFICIENT' | 'INSUFFICIENT'
  use_fifo: boolean
  lot_selections?: LotIssueItem[]
}

const issueItems = ref<IssueItem[]>([])

// 선택된 항목
const selectedItem = computed(() => {
  if (selectedItemIndex.value >= 0 && selectedItemIndex.value < issueItems.value.length) {
    return issueItems.value[selectedItemIndex.value]
  }
  return null
})

// 계산된 속성
const hasInsufficientStock = computed(() => {
  return issueItems.value.some(item => item.stock_status === 'INSUFFICIENT')
})

const canIssue = computed(() => {
  const hasItems = issueItems.value.some(item => item.issue_quantity > 0)
  if (!hasItems) return false

  // 수동 선택 항목 중 로트 미선택 항목이 있는지 확인
  const invalidManual = issueItems.value.some(item =>
    !item.use_fifo && item.issue_quantity > 0 && (!item.lot_selections || item.lot_selections.length === 0)
  )

  return !invalidManual
})

// 전체 FIFO 토글
watch(globalFifo, (newVal) => {
  issueItems.value.forEach(item => {
    item.use_fifo = newVal
  })
})

// 데이터 로드
async function loadData() {
  loading.value = true
  try {
    // 작업지시서 조회
    workOrder.value = await workOrderApi.getById(props.workOrderId)

    // BOM 미리보기 조회 (현재고 정보 포함)
    bomPreview.value = await workOrderApi.getWorkOrderBOMPreview(props.workOrderId)

    // 출고 항목 초기화
    if (workOrder.value.items && bomPreview.value) {
      const stockMap = new Map(
        bomPreview.value.items.map(item => [item.part_id, item])
      )

      issueItems.value = workOrder.value.items.map(item => {
        const stockInfo = stockMap.get(item.part_id)
        const currentStock = stockInfo?.current_stock ?? 0
        const pendingQty = item.required_quantity - item.issued_quantity
        const stockStatus: 'SUFFICIENT' | 'INSUFFICIENT' = currentStock >= pendingQty ? 'SUFFICIENT' : 'INSUFFICIENT'

        return {
          item_id: item.id,
          part_id: item.part_id,
          part_number: item.part?.part_number_display || item.part?.part_number || '-',
          part_name: item.part?.part_name || '-',
          bom_level: item.bom_level,
          required_quantity: pendingQty,
          current_stock: currentStock,
          issue_quantity: Math.min(pendingQty, currentStock),
          stock_status: stockStatus,
          use_fifo: true,
          lot_selections: undefined,
        }
      }).filter(item => item.required_quantity > 0)
    }
  } catch (error) {
    console.error('작업지시서 조회 실패:', error)
    alert('작업지시서 정보를 불러오는데 실패했습니다.')
    emit('close')
  } finally {
    loading.value = false
  }
}

// 수량 검증
function validateIssueQuantity(index: number) {
  const item = issueItems.value[index]
  if (!item) return

  if (item.issue_quantity < 0) {
    item.issue_quantity = 0
  }
  // BOM 수량 초과 허용 - 불량 대응용
  const maxQty = item.current_stock
  if (item.issue_quantity > maxQty) {
    item.issue_quantity = maxQty
  }
  // 수량 변경 시 로트 선택 초기화
  item.lot_selections = undefined
}

// 가용수량 전체 출고
function fillAllIssue() {
  issueItems.value.forEach(item => {
    item.issue_quantity = Math.min(item.required_quantity, item.current_stock)
  })
}

// 로트 선택 모달 열기
function openLotSelection(index: number) {
  selectedItemIndex.value = index
  showLotSelection.value = true
}

// 로트 선택 확정
function handleLotSelectionConfirm(data: { use_fifo: boolean; issue_quantity: number; lot_selections?: LotIssueItem[] }) {
  if (selectedItemIndex.value >= 0) {
    const item = issueItems.value[selectedItemIndex.value]
    if (item) {
      item.use_fifo = data.use_fifo
      item.issue_quantity = data.issue_quantity
      item.lot_selections = data.lot_selections
    }
  }
  showLotSelection.value = false
}

// 출고 처리
async function handleIssue() {
  if (!canIssue.value) return

  // 출고 요청 생성
  const items: WorkOrderItemIssueRequest[] = issueItems.value
    .filter(item => item.issue_quantity > 0)
    .map(item => ({
      item_id: item.item_id,
      issue_quantity: item.issue_quantity,
      use_fifo: item.use_fifo,
      lot_selections: item.use_fifo ? undefined : item.lot_selections,
    }))

  if (items.length === 0) {
    alert('출고할 항목이 없습니다.')
    return
  }

  const request: WorkOrderIssueRequest = { items }

  saving.value = true
  try {
    await workOrderLotApi.issueWithLots(props.workOrderId, request)
    alert('부품 출고가 완료되었습니다. 로트별로 재고가 차감되었습니다.')
    emit('issued')
  } catch (error: any) {
    console.error('부품 출고 실패:', error)
    alert(error.response?.data?.detail?.message || '부품 출고에 실패했습니다.')
  } finally {
    saving.value = false
  }
}

// 초기화
onMounted(() => {
  loadData()
})
</script>
