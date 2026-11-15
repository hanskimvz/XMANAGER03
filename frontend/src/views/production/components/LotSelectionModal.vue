<template>
  <div
    v-if="show"
    ref="modalOverlay"
    class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
    tabindex="-1"
    @keydown.escape="$emit('close')"
  >
    <div class="relative top-10 mx-auto p-5 border w-full max-w-3xl shadow-lg rounded-md bg-white" @click.stop>
      <!-- 헤더 -->
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold">로트 선택 출고</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 부품 정보 -->
      <div class="bg-gray-50 rounded-lg p-4 mb-4">
        <div class="flex justify-between items-center">
          <div>
            <span class="font-mono text-blue-600">{{ partNumber }}</span>
            <span class="mx-2">-</span>
            <span class="font-medium">{{ partName }}</span>
          </div>
          <div class="text-sm text-gray-600">
            필요수량: <span class="font-bold text-lg">{{ requiredQuantity }}</span>
          </div>
        </div>
      </div>

      <!-- 출고 수량 입력 -->
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">출고 수량</label>
        <input
          v-model.number="issueQuantity"
          type="number"
          :max="requiredQuantity"
          min="0"
          step="0.001"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        />
        <p v-if="issueQuantity > totalAvailable" class="mt-1 text-sm text-red-500">
          가용 재고({{ totalAvailable }})를 초과합니다.
        </p>
      </div>

      <!-- FIFO 자동 / 수동 선택 토글 -->
      <div class="mb-4">
        <label class="flex items-center cursor-pointer">
          <input
            v-model="useFifo"
            type="checkbox"
            class="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mr-2"
          />
          <span class="text-sm font-medium text-gray-700">선입선출(FIFO) 자동 적용</span>
        </label>
      </div>

      <!-- FIFO 자동 선택 표시 -->
      <div v-if="useFifo && fifoSuggestion" class="mb-4">
        <div class="text-sm font-medium text-gray-700 mb-2">FIFO 자동 선택 결과</div>
        <div class="border rounded-lg overflow-hidden">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">로트번호</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">입고일</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">제조사</th>
                <th class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">잔량</th>
                <th class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">출고량</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="lot in fifoSuggestion.lots" :key="lot.lot_id">
                <td class="px-3 py-2 font-mono text-blue-600">{{ lot.lot_number }}</td>
                <td class="px-3 py-2 text-sm">{{ formatDate(lot.received_date) }}</td>
                <td class="px-3 py-2 text-sm text-gray-600">{{ lot.supplier_name || '-' }}</td>
                <td class="px-3 py-2 text-right">{{ lot.available_quantity }}</td>
                <td class="px-3 py-2 text-right font-bold text-green-600">{{ lot.suggested_quantity }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!fifoSuggestion.is_sufficient" class="mt-2 text-sm text-red-500">
          재고 부족: {{ fifoSuggestion.shortage }} 개 부족
        </div>
      </div>

      <!-- 수동 로트 선택 -->
      <div v-else class="mb-4">
        <div class="text-sm font-medium text-gray-700 mb-2">로트 직접 선택</div>
        <div v-if="loading" class="text-center py-4 text-gray-500">
          <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto mb-2"></div>
          로딩 중...
        </div>
        <div v-else-if="availableLots.length === 0" class="text-center py-6 text-gray-500">
          <div class="mb-2">출고 가능한 로트가 없습니다.</div>
          <div class="text-xs text-gray-400">
            재고가 있더라도 로트가 생성되지 않은 경우 표시되지 않습니다.<br/>
            발주 입고를 통해 입고하거나, 재고 페이지에서 로트를 직접 생성해주세요.
          </div>
        </div>
        <div v-else class="border rounded-lg overflow-hidden max-h-64 overflow-y-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50 sticky top-0">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">로트번호</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">입고일</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">제조사</th>
                <th class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">잔량</th>
                <th class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase w-32">출고량</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="lot in availableLots" :key="lot.id">
                <td class="px-3 py-2 font-mono text-blue-600">{{ lot.lot_number }}</td>
                <td class="px-3 py-2 text-sm">{{ formatDate(lot.received_date) }}</td>
                <td class="px-3 py-2 text-sm text-gray-600">{{ lot.supplier?.partner_name || '-' }}</td>
                <td class="px-3 py-2 text-right">{{ lot.quantity_on_hand }}</td>
                <td class="px-3 py-2 text-right">
                  <input
                    v-model.number="lotQuantities[lot.id]"
                    type="number"
                    min="0"
                    :max="lot.quantity_on_hand"
                    step="0.001"
                    class="w-24 px-2 py-1 border border-gray-300 rounded text-right focus:ring-blue-500 focus:border-blue-500"
                    @input="validateLotQuantity(lot.id, lot.quantity_on_hand)"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="mt-2 flex justify-between text-sm">
          <span class="text-gray-600">선택된 수량 합계: <span class="font-bold">{{ selectedTotal }}</span></span>
          <span :class="selectedTotal === issueQuantity ? 'text-green-600' : 'text-red-500'">
            {{ selectedTotal === issueQuantity ? '수량 일치' : `차이: ${Math.abs(selectedTotal - issueQuantity)}` }}
          </span>
        </div>
      </div>

      <!-- 하단 버튼 -->
      <div class="flex justify-end gap-2 mt-4 pt-4 border-t">
        <button
          @click="$emit('close')"
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          취소
        </button>
        <button
          @click="handleSubmit"
          :disabled="!canSubmit"
          class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          출고 확정
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  inventoryLotApi,
  type InventoryLot,
  type FIFOSuggestionResponse,
  type LotIssueItem
} from '@/api/inventoryLot'

const props = defineProps<{
  show: boolean
  partId: number
  partNumber: string
  partName: string
  requiredQuantity: number
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'confirm', data: { use_fifo: boolean; issue_quantity: number; lot_selections?: LotIssueItem[] }): void
}>()

// 상태
const loading = ref(false)
const useFifo = ref(true)
const issueQuantity = ref(0)
const availableLots = ref<InventoryLot[]>([])
const lotQuantities = ref<Record<number, number>>({})
const fifoSuggestion = ref<FIFOSuggestionResponse | null>(null)

// 전체 가용 수량
const totalAvailable = computed(() => {
  return availableLots.value.reduce((sum, lot) => sum + lot.quantity_on_hand, 0)
})

// 수동 선택 합계
const selectedTotal = computed(() => {
  return Object.values(lotQuantities.value).reduce((sum, qty) => sum + (qty || 0), 0)
})

// 제출 가능 여부
const canSubmit = computed(() => {
  if (issueQuantity.value <= 0) return false
  if (issueQuantity.value > totalAvailable.value) return false

  if (useFifo.value) {
    return fifoSuggestion.value?.is_sufficient ?? false
  } else {
    return selectedTotal.value === issueQuantity.value
  }
})

// 날짜 포맷
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

// 로트 수량 검증
const validateLotQuantity = (lotId: number, maxQty: number) => {
  const currentQty = lotQuantities.value[lotId] ?? 0
  if (currentQty > maxQty) {
    lotQuantities.value[lotId] = maxQty
  }
  if (currentQty < 0) {
    lotQuantities.value[lotId] = 0
  }
}

// 로트 목록 로드
const loadLots = async () => {
  if (!props.partId) return

  loading.value = true
  try {
    availableLots.value = await inventoryLotApi.getByPart(props.partId, false)

    // 수량 초기화
    lotQuantities.value = {}
    for (const lot of availableLots.value) {
      lotQuantities.value[lot.id] = 0
    }
  } catch (error) {
    console.error('로트 목록 로드 실패:', error)
  } finally {
    loading.value = false
  }
}

// FIFO 제안 로드
const loadFifoSuggestion = async () => {
  if (!props.partId || issueQuantity.value <= 0) {
    fifoSuggestion.value = null
    return
  }

  try {
    fifoSuggestion.value = await inventoryLotApi.getFIFOSuggestion(props.partId, issueQuantity.value)
  } catch (error) {
    console.error('FIFO 제안 로드 실패:', error)
    fifoSuggestion.value = null
  }
}

// 제출 처리
const handleSubmit = () => {
  if (!canSubmit.value) return

  if (useFifo.value) {
    emit('confirm', {
      use_fifo: true,
      issue_quantity: issueQuantity.value
    })
  } else {
    const lotSelections: LotIssueItem[] = Object.entries(lotQuantities.value)
      .filter(([_, qty]) => qty > 0)
      .map(([lotId, qty]) => ({
        lot_id: parseInt(lotId),
        quantity: qty
      }))

    emit('confirm', {
      use_fifo: false,
      issue_quantity: issueQuantity.value,
      lot_selections: lotSelections
    })
  }
}

// 모달 열릴 때 초기화
watch(() => props.show, async (newVal) => {
  if (newVal) {
    issueQuantity.value = props.requiredQuantity
    useFifo.value = true
    await loadLots()
    await loadFifoSuggestion()
  }
})

// 출고 수량 변경 시 FIFO 재계산
watch(issueQuantity, () => {
  if (useFifo.value) {
    loadFifoSuggestion()
  }
})

// FIFO 토글 시
watch(useFifo, (newVal) => {
  if (newVal) {
    loadFifoSuggestion()
  }
})
</script>
