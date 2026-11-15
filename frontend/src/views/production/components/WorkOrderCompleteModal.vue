<template>
  <div
    ref="modalOverlay"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    tabindex="-1"
    @keydown.escape="$emit('close')"
  >
    <div class="bg-white rounded-lg shadow-xl w-full max-w-lg overflow-hidden" @click.stop>
      <!-- 헤더 -->
      <div class="flex justify-between items-center px-6 py-4 border-b bg-orange-50">
        <div>
          <h2 class="text-xl font-bold text-gray-800">작업 완료</h2>
          <p class="text-sm text-gray-600">{{ workOrder?.wo_number }}</p>
        </div>
        <button @click="$emit('close')" class="text-gray-500 hover:text-gray-700">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 본문 -->
      <div class="p-6">
        <!-- 로딩 -->
        <div v-if="loading" class="text-center py-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p class="mt-2 text-gray-500">로딩 중...</p>
        </div>

        <div v-else-if="workOrder">
          <!-- 기본 정보 -->
          <div class="grid grid-cols-2 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
            <div>
              <label class="text-xs text-gray-500">완제품</label>
              <p class="font-medium">{{ workOrder.product_part?.part_name || '-' }}</p>
            </div>
            <div>
              <label class="text-xs text-gray-500">지시수량</label>
              <p class="font-medium">{{ workOrder.order_quantity }}</p>
            </div>
          </div>

          <!-- 완료 수량 입력 -->
          <div class="mb-6">
            <label class="block text-sm font-medium text-gray-700 mb-1">
              완료 수량 <span class="text-red-500">*</span>
            </label>
            <input
              v-model.number="completeData.completed_quantity"
              type="number"
              min="0"
              :max="workOrder.order_quantity"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
              placeholder="완료된 수량을 입력하세요"
            />
            <p class="text-xs text-gray-500 mt-1">
              지시수량: {{ workOrder.order_quantity }} / 기 완료: {{ workOrder.completed_quantity }}
            </p>
          </div>

          <!-- 불량 수량 입력 -->
          <div class="mb-6">
            <label class="block text-sm font-medium text-gray-700 mb-1">불량 수량</label>
            <input
              v-model.number="completeData.defective_quantity"
              type="number"
              min="0"
              :max="completeData.completed_quantity"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
              placeholder="불량 수량 (선택)"
            />
          </div>

          <!-- 비고 -->
          <div class="mb-6">
            <label class="block text-sm font-medium text-gray-700 mb-1">비고</label>
            <textarea
              v-model="completeData.remarks"
              rows="3"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
              placeholder="작업 완료 관련 비고사항"
            ></textarea>
          </div>

          <!-- 요약 -->
          <div class="p-4 bg-orange-50 rounded-lg">
            <div class="grid grid-cols-3 gap-4 text-center">
              <div>
                <p class="text-sm text-gray-600">완료 수량</p>
                <p class="text-xl font-bold text-gray-800">{{ completeData.completed_quantity || 0 }}</p>
              </div>
              <div>
                <p class="text-sm text-gray-600">불량 수량</p>
                <p class="text-xl font-bold text-red-600">{{ completeData.defective_quantity || 0 }}</p>
              </div>
              <div>
                <p class="text-sm text-gray-600">양품 수량</p>
                <p class="text-xl font-bold text-green-600">{{ goodQuantity }}</p>
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
          @click="handleComplete"
          :disabled="saving || !canComplete"
          class="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ saving ? '처리 중...' : '작업 완료' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import {
  workOrderApi,
  type WorkOrder,
  type ProductionCompleteRequest,
} from '@/api/workOrder'

// Props
const props = defineProps<{
  workOrderId: number
}>()

// Emits
const emit = defineEmits<{
  close: []
  completed: []
}>()

// 상태
const loading = ref(false)
const saving = ref(false)
const workOrder = ref<WorkOrder | null>(null)

// 완료 데이터
const completeData = reactive<ProductionCompleteRequest>({
  completed_quantity: 0,
  defective_quantity: 0,
  remarks: '',
})

// 계산된 속성
const goodQuantity = computed(() => {
  return (completeData.completed_quantity || 0) - (completeData.defective_quantity || 0)
})

const canComplete = computed(() => {
  return completeData.completed_quantity > 0 &&
         (completeData.defective_quantity || 0) <= completeData.completed_quantity
})

// 데이터 로드
async function loadData() {
  loading.value = true
  try {
    workOrder.value = await workOrderApi.getById(props.workOrderId)
    // 기본값: 지시수량 - 기 완료수량
    completeData.completed_quantity = (workOrder.value.order_quantity ?? 0) - (workOrder.value.completed_quantity ?? 0)
  } catch (error) {
    console.error('작업지시서 조회 실패:', error)
    alert('작업지시서 정보를 불러오는데 실패했습니다.')
    emit('close')
  } finally {
    loading.value = false
  }
}

// 완료 처리
async function handleComplete() {
  if (!canComplete.value) return

  saving.value = true
  try {
    await workOrderApi.completeProduction(props.workOrderId, {
      completed_quantity: completeData.completed_quantity,
      defective_quantity: completeData.defective_quantity || 0,
      remarks: completeData.remarks || undefined,
    })
    alert('작업이 완료되었습니다.')
    emit('completed')
  } catch (error: any) {
    console.error('작업 완료 실패:', error)
    alert(error.response?.data?.detail?.message || '작업 완료 처리에 실패했습니다.')
  } finally {
    saving.value = false
  }
}

// 초기화
onMounted(() => {
  loadData()
})
</script>
