<template>
  <div
    ref="modalOverlay"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    tabindex="-1"
    @keydown.escape="$emit('close')"
  >
    <div class="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] overflow-hidden" @click.stop>
      <!-- 헤더 -->
      <div class="flex justify-between items-center px-6 py-4 border-b bg-green-50">
        <div>
          <h2 class="text-xl font-bold text-gray-800">입고 처리</h2>
          <p class="text-sm text-gray-600">{{ purchaseOrder?.po_number }}</p>
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

        <div v-else-if="purchaseOrder">
          <!-- 기본 정보 -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
            <div>
              <label class="text-xs text-gray-500">공급업체</label>
              <p class="font-medium">{{ purchaseOrder.supplier?.partner_name || '-' }}</p>
            </div>
            <div>
              <label class="text-xs text-gray-500">발주일</label>
              <p class="font-medium">{{ formatDate(purchaseOrder.order_date) }}</p>
            </div>
            <div>
              <label class="text-xs text-gray-500">예상 납기일</label>
              <p class="font-medium">{{ purchaseOrder.expected_delivery_date ? formatDate(purchaseOrder.expected_delivery_date) : '-' }}</p>
            </div>
            <div>
              <label class="text-xs text-gray-500">상태</label>
              <span :class="['px-2 py-1 text-xs rounded-full', poStatusStyles[purchaseOrder.status]]">
                {{ poStatusLabels[purchaseOrder.status] }}
              </span>
            </div>
          </div>

          <!-- 입고 모드 선택 -->
          <div class="mb-6 p-4 bg-blue-50 rounded-lg">
            <div class="flex items-center gap-6">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  v-model="receiveMode"
                  type="radio"
                  value="partial"
                  class="text-blue-600 focus:ring-blue-500"
                />
                <span class="font-medium">순차 입고</span>
                <span class="text-sm text-gray-500">(일부 수량만 입고)</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  v-model="receiveMode"
                  type="radio"
                  value="final"
                  class="text-green-600 focus:ring-green-500"
                />
                <span class="font-medium">최종 입고</span>
                <span class="text-sm text-gray-500">(단가/총액 조정 가능)</span>
              </label>
            </div>
            <p v-if="receiveMode === 'final'" class="mt-2 text-sm text-green-700">
              최종 입고 시 누적 입고수량(기입고 + 이번입고)을 기준으로 단가와 총액을 최종 확정할 수 있습니다.
            </p>
          </div>

          <!-- 실제 입고일 -->
          <div class="mb-6">
            <label class="block text-sm font-medium text-gray-700 mb-1">
              실제 입고일 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="receiveData.actual_delivery_date"
              type="date"
              class="w-48 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
            />
          </div>

          <!-- 항목 테이블 -->
          <div class="mb-6">
            <h3 class="text-lg font-semibold mb-3">입고 항목</h3>
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">품번</th>
                    <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">부품명</th>
                    <th class="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">발주수량</th>
                    <th class="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">기입고</th>
                    <th class="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">미입고</th>
                    <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">이번입고</th>
                    <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">불량</th>
                    <th v-if="receiveMode === 'final'" class="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      최종단가
                    </th>
                    <th v-if="receiveMode === 'final'" class="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      최종총액
                    </th>
                    <th class="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase">실입고</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr v-for="(item, index) in receiveItems" :key="item.item_id" class="hover:bg-gray-50">
                    <td class="px-3 py-3 whitespace-nowrap text-sm font-mono text-blue-600">
                      {{ item.part_number }}
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-sm">
                      {{ item.part_name }}
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-sm text-right">
                      {{ formatNumber(item.ordered_quantity) }}
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-sm text-right text-green-600">
                      {{ formatNumber(item.already_received) }}
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-sm text-right text-orange-600">
                      {{ formatNumber(item.remaining) }}
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-center">
                      <div class="flex flex-col items-center">
                        <input
                          v-model.number="item.received_quantity"
                          type="number"
                          min="0"
                          step="0.001"
                          :class="[
                            'w-20 px-2 py-1 border rounded text-center text-sm focus:ring-2',
                            isOverReceiving(index)
                              ? 'border-orange-400 bg-orange-50 focus:ring-orange-500'
                              : 'border-gray-300 focus:ring-green-500'
                          ]"
                          @input="onQuantityChange(index)"
                        />
                        <span v-if="isOverReceiving(index)" class="text-xs text-orange-600 mt-1">
                          초과
                        </span>
                      </div>
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-center">
                      <input
                        v-model.number="item.defective_quantity"
                        type="number"
                        min="0"
                        step="0.001"
                        :max="item.received_quantity"
                        class="w-16 px-2 py-1 border border-gray-300 rounded text-center text-sm focus:ring-2 focus:ring-orange-500"
                        @input="validateDefective(index)"
                      />
                    </td>
                    <!-- 최종 입고 모드: 단가 -->
                    <td v-if="receiveMode === 'final'" class="px-3 py-3 whitespace-nowrap text-right">
                      <input
                        v-model.number="item.final_unit_price"
                        type="number"
                        min="0"
                        step="0.01"
                        class="w-24 px-2 py-1 border border-blue-300 rounded text-right text-sm focus:ring-2 focus:ring-blue-500 bg-blue-50"
                        placeholder="단가"
                        @input="onUnitPriceChange(index)"
                      />
                      <div class="text-xs text-gray-400 mt-0.5">
                        기존: {{ formatCurrency(item.original_unit_price) }}
                      </div>
                    </td>
                    <!-- 최종 입고 모드: 총액 -->
                    <td v-if="receiveMode === 'final'" class="px-3 py-3 whitespace-nowrap text-right">
                      <input
                        v-model.number="item.final_line_total"
                        type="number"
                        min="0"
                        step="1"
                        class="w-28 px-2 py-1 border border-purple-300 rounded text-right text-sm focus:ring-2 focus:ring-purple-500 bg-purple-50"
                        placeholder="총액"
                        @input="onLineTotalChange(index)"
                      />
                      <div class="text-xs text-gray-400 mt-0.5">
                        기존: {{ formatCurrency(item.original_line_total) }}
                      </div>
                    </td>
                    <td class="px-3 py-3 whitespace-nowrap text-sm text-right font-medium">
                      <span :class="getActualReceivedClass(index)">
                        {{ formatNumber(getActualReceived(index)) }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 전체 입고 버튼 -->
          <div class="mb-6 flex gap-2">
            <button
              @click="fillAllRemaining"
              class="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
            >
              잔량 전체 입고
            </button>
            <button
              v-if="receiveMode === 'final'"
              @click="resetPrices"
              class="px-4 py-2 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
            >
              가격 초기화
            </button>
          </div>

          <!-- 비고 -->
          <div class="mb-6">
            <label class="block text-sm font-medium text-gray-700 mb-1">비고</label>
            <textarea
              v-model="receiveData.remarks"
              rows="2"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
              placeholder="입고 관련 비고사항"
            ></textarea>
          </div>

          <!-- 요약 -->
          <div class="p-4 rounded-lg" :class="receiveMode === 'final' ? 'bg-green-50' : 'bg-gray-50'">
            <div :class="['grid gap-4 text-center', receiveMode === 'final' ? 'grid-cols-5' : 'grid-cols-3']">
              <div>
                <p class="text-sm text-gray-600">입고 예정 수량</p>
                <p class="text-2xl font-bold text-gray-800">{{ formatNumber(totalReceiving) }}</p>
              </div>
              <div>
                <p class="text-sm text-gray-600">불량 수량</p>
                <p class="text-2xl font-bold text-orange-600">{{ formatNumber(totalDefective) }}</p>
              </div>
              <div>
                <p class="text-sm text-gray-600">실 입고 수량</p>
                <p class="text-2xl font-bold text-green-600">{{ formatNumber(totalActual) }}</p>
              </div>
              <div v-if="receiveMode === 'final'">
                <p class="text-sm text-gray-600">누적 입고 수량</p>
                <p class="text-2xl font-bold text-blue-600">{{ formatNumber(totalCumulative) }}</p>
              </div>
              <div v-if="receiveMode === 'final'">
                <p class="text-sm text-gray-600">조정 후 총액</p>
                <p class="text-2xl font-bold text-purple-600">{{ formatCurrency(totalAdjustedAmount) }}</p>
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
          @click="handleReceive"
          :disabled="saving || !canReceive"
          :class="[
            'px-4 py-2 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed',
            receiveMode === 'final'
              ? 'bg-green-600 hover:bg-green-700'
              : 'bg-blue-600 hover:bg-blue-700'
          ]"
        >
          {{ saving ? '처리 중...' : (receiveMode === 'final' ? '최종 입고 완료' : '순차 입고') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import {
  purchaseOrderApi,
  type PurchaseOrder,
  type ReceiveRequest,
  type ReceiveItemRequest,
  poStatusLabels,
  poStatusStyles,
} from '@/api/purchaseOrder'

// Props
const props = defineProps<{
  purchaseOrderId: number
}>()

// Emits
const emit = defineEmits<{
  close: []
  received: []
}>()

// 상태
const loading = ref(false)
const saving = ref(false)
const purchaseOrder = ref<PurchaseOrder | null>(null)
const receiveMode = ref<'partial' | 'final'>('partial')

// 입고 항목 타입
interface ReceiveItem {
  item_id: number
  part_number: string
  part_name: string
  ordered_quantity: number
  already_received: number
  remaining: number
  received_quantity: number
  defective_quantity: number
  original_unit_price: number
  original_line_total: number
  final_unit_price: number | undefined
  final_line_total: number | undefined
}

const receiveItems = ref<ReceiveItem[]>([])

// 입고 데이터
const receiveData = ref({
  actual_delivery_date: new Date().toISOString().split('T')[0],
  remarks: '',
})

// 계산된 속성
const totalReceiving = computed(() => {
  return receiveItems.value.reduce((sum, item) => sum + (item.received_quantity || 0), 0)
})

const totalDefective = computed(() => {
  return receiveItems.value.reduce((sum, item) => sum + (item.defective_quantity || 0), 0)
})

const totalActual = computed(() => {
  return totalReceiving.value - totalDefective.value
})

// 누적 입고 수량 (기입고 + 이번 입고)
const totalCumulative = computed(() => {
  return receiveItems.value.reduce((sum, item) => {
    return sum + item.already_received + (item.received_quantity || 0) - (item.defective_quantity || 0)
  }, 0)
})

// 조정 후 총액
const totalAdjustedAmount = computed(() => {
  return receiveItems.value.reduce((sum, item) => {
    if (item.final_line_total !== undefined) {
      return sum + item.final_line_total
    }
    // 조정되지 않은 항목은 기존 총액 사용
    return sum + item.original_line_total
  }, 0)
})

const canReceive = computed(() => {
  return receiveData.value.actual_delivery_date && totalReceiving.value > 0
})

// 데이터 로드
async function loadData() {
  loading.value = true
  try {
    purchaseOrder.value = await purchaseOrderApi.getById(props.purchaseOrderId)

    // 입고 항목 초기화
    receiveItems.value = (purchaseOrder.value.items || []).map(item => ({
      item_id: item.id,
      part_number: item.part?.part_number_display || item.part?.part_number || item.custom_product_code || '-',
      part_name: item.part?.part_name || item.custom_product_name || item.custom_product_code || '-',
      ordered_quantity: item.ordered_quantity,
      already_received: item.received_quantity,
      remaining: item.ordered_quantity - item.received_quantity,
      received_quantity: 0,
      defective_quantity: 0,
      original_unit_price: item.unit_price,
      original_line_total: item.line_total || (item.ordered_quantity * item.unit_price),
      final_unit_price: undefined,
      final_line_total: undefined,
    }))
  } catch (error) {
    console.error('발주서 조회 실패:', error)
    alert('발주서 정보를 불러오는데 실패했습니다.')
    emit('close')
  } finally {
    loading.value = false
  }
}

// 모드 변경 시 가격 초기화
watch(receiveMode, (newMode) => {
  if (newMode === 'partial') {
    resetPrices()
  }
})

// 수량 검증 (초과 입고 허용, 경고만 표시)
function onQuantityChange(index: number) {
  const item = receiveItems.value[index]
  if (!item) return
  if (item.received_quantity < 0) {
    item.received_quantity = 0
  }
  // 불량수량이 입고수량을 초과하면 조정
  if (item.defective_quantity > item.received_quantity) {
    item.defective_quantity = item.received_quantity
  }

  // 최종 입고 모드에서 단가가 입력되어 있으면 총액 재계산
  if (receiveMode.value === 'final' && item.final_unit_price !== undefined) {
    const totalQty = item.already_received + item.received_quantity - item.defective_quantity
    item.final_line_total = Math.round(item.final_unit_price * totalQty)
  }
}

// 입고 수량이 미입고 수량 초과 여부 체크
function isOverReceiving(index: number): boolean {
  const item = receiveItems.value[index]
  if (!item) return false
  return item.received_quantity > item.remaining
}

function validateDefective(index: number) {
  const item = receiveItems.value[index]
  if (!item) return
  if (item.defective_quantity < 0) {
    item.defective_quantity = 0
  }
  if (item.defective_quantity > item.received_quantity) {
    item.defective_quantity = item.received_quantity
  }

  // 최종 입고 모드에서 단가가 입력되어 있으면 총액 재계산
  if (receiveMode.value === 'final' && item.final_unit_price !== undefined) {
    const totalQty = item.already_received + item.received_quantity - item.defective_quantity
    item.final_line_total = Math.round(item.final_unit_price * totalQty)
  }
}

// 단가 변경 시 총액 자동 계산
function onUnitPriceChange(index: number) {
  const item = receiveItems.value[index]
  if (!item) return
  if (item.final_unit_price !== undefined && item.final_unit_price >= 0) {
    // 누적 입고 수량 = 기입고 + 이번 입고 - 불량
    const totalQty = item.already_received + (item.received_quantity || 0) - (item.defective_quantity || 0)
    item.final_line_total = Math.round(item.final_unit_price * totalQty)
  }
}

// 총액 변경 시 단가 자동 역계산
function onLineTotalChange(index: number) {
  const item = receiveItems.value[index]
  if (!item) return
  if (item.final_line_total !== undefined && item.final_line_total >= 0) {
    // 누적 입고 수량 = 기입고 + 이번 입고 - 불량
    const totalQty = item.already_received + (item.received_quantity || 0) - (item.defective_quantity || 0)
    if (totalQty > 0) {
      item.final_unit_price = Math.round((item.final_line_total / totalQty) * 100) / 100
    }
  }
}

// 잔량 전체 입고
function fillAllRemaining() {
  receiveItems.value.forEach((item, index) => {
    item.received_quantity = Math.max(0, item.remaining)
    item.defective_quantity = 0
    onQuantityChange(index)
  })
}

// 가격 초기화
function resetPrices() {
  receiveItems.value.forEach(item => {
    item.final_unit_price = undefined
    item.final_line_total = undefined
  })
}

// 실 입고량 계산
function getActualReceived(index: number): number {
  const item = receiveItems.value[index]
  if (!item) return 0
  return (item.received_quantity || 0) - (item.defective_quantity || 0)
}

function getActualReceivedClass(index: number): string {
  const actual = getActualReceived(index)
  if (actual > 0) return 'text-green-600'
  return 'text-gray-400'
}

// 초과 입고 항목 수 체크
function getOverReceivingCount(): number {
  return receiveItems.value.filter((item, idx) => isOverReceiving(idx) && item.received_quantity > 0).length
}

// 입고 처리
async function handleReceive() {
  if (!canReceive.value) return

  // 입고 항목 필터링 (수량이 0보다 큰 것만)
  const items: ReceiveItemRequest[] = receiveItems.value
    .filter(item => item.received_quantity > 0)
    .map(item => {
      const reqItem: ReceiveItemRequest = {
        item_id: item.item_id,
        received_quantity: item.received_quantity,
        defective_quantity: item.defective_quantity || 0,
      }

      // 최종 입고 모드에서 가격 조정 정보 추가
      // 빈 정수 정규화 — Pydantic이 빈 문자열을 정수로 거부함
      if (receiveMode.value === 'final') {
        const _fup: any = item.final_unit_price
        if (typeof _fup === 'number' && !Number.isNaN(_fup)) {
          reqItem.final_unit_price = _fup
        }
        const _flt: any = item.final_line_total
        if (typeof _flt === 'number' && !Number.isNaN(_flt)) {
          reqItem.final_line_total = _flt
        }
      }

      return reqItem
    })

  if (items.length === 0) {
    alert('입고할 항목이 없습니다.')
    return
  }

  // 초과 입고 경고
  const overCount = getOverReceivingCount()
  if (overCount > 0) {
    const confirmed = confirm(
      `${overCount}개 항목이 미입고 수량을 초과합니다.\n` +
      `초과 입고를 진행하시겠습니까?\n\n` +
      `(불량 교체, 추가 생산 등의 경우 초과 입고가 필요할 수 있습니다)`
    )
    if (!confirmed) return
  }

  // 최종 입고 확인
  if (receiveMode.value === 'final') {
    const priceAdjustedCount = items.filter(i => i.final_unit_price !== undefined || i.final_line_total !== undefined).length
    if (priceAdjustedCount > 0) {
      const confirmed = confirm(
        `최종 입고로 처리합니다.\n\n` +
        `- 가격 조정 항목: ${priceAdjustedCount}개\n` +
        `- 조정 후 총액: ${formatCurrency(totalAdjustedAmount.value)}\n\n` +
        `진행하시겠습니까?`
      )
      if (!confirmed) return
    }
  }

  const request: ReceiveRequest = {
    items,
    actual_delivery_date: receiveData.value.actual_delivery_date,
    remarks: receiveData.value.remarks || undefined,
    is_final_receive: receiveMode.value === 'final',
  }

  saving.value = true
  try {
    await purchaseOrderApi.receive(props.purchaseOrderId, request)
    const message = receiveMode.value === 'final'
      ? '최종 입고 처리가 완료되었습니다. 가격이 확정되었습니다.'
      : '입고 처리가 완료되었습니다. 재고가 자동으로 증가되었습니다.'
    alert(message)
    emit('received')
  } catch (error: any) {
    console.error('입고 처리 실패:', error)
    alert(error.response?.data?.detail?.message || '입고 처리에 실패했습니다.')
  } finally {
    saving.value = false
  }
}

// 포맷 함수
function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('ko-KR')
}

function formatNumber(value: number | undefined | null): string {
  if (value === undefined || value === null) return '0'
  return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 3 }).format(value)
}

function formatCurrency(value: number | undefined | null): string {
  if (value === undefined || value === null) return '₩0'
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(value)
}

// 초기화
onMounted(() => {
  loadData()
})
</script>
