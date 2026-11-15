<template>
  <div v-if="availability" class="bg-gray-50 rounded-lg p-4 mb-4">
    <!-- 생산 가능 수량 요약 -->
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="font-medium text-gray-700">생산 가능 수량 분석</span>
      </div>
      <button
        @click="showDetails = !showDetails"
        class="text-sm text-blue-600 hover:text-blue-800"
      >
        {{ showDetails ? '접기' : '상세보기' }}
      </button>
    </div>

    <!-- 요약 정보 -->
    <div class="flex items-center gap-4">
      <div class="flex-1">
        <div class="text-sm text-gray-500">현재 재고로 생산 가능</div>
        <div class="text-2xl font-bold" :class="canProduceClass">
          {{ availability.can_produce }}개
        </div>
      </div>

      <div v-if="availability.limiting_parts && availability.limiting_parts.length > 0" class="flex-1 border-l pl-4">
        <div class="text-sm text-gray-500">제한 부품</div>
        <div class="text-sm font-medium text-orange-600">
          {{ availability.limiting_parts[0]?.part_name }}
          <span class="text-gray-400">(재고 {{ availability.limiting_parts[0]?.available_quantity }})</span>
        </div>
      </div>
    </div>

    <!-- 경고 메시지 -->
    <div
      v-if="requestedQuantity > availability.can_produce"
      class="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800"
    >
      요청 수량({{ requestedQuantity }})이 생산 가능 수량({{ availability.can_produce }})을 초과합니다.
      {{ requestedQuantity - availability.can_produce }}개 부족
    </div>

    <!-- 상세 BOM 항목별 재고 상태 -->
    <div v-if="showDetails && availability.items.length > 0" class="mt-4">
      <div class="text-sm font-medium text-gray-700 mb-2">BOM 항목별 재고 상태</div>
      <div class="border rounded-lg overflow-hidden max-h-48 overflow-y-auto">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-gray-100 sticky top-0">
            <tr>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">품번/품명</th>
              <th class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">단위소요</th>
              <th class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">필요량</th>
              <th class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">현재고</th>
              <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">상태</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="item in availability.items" :key="item.part_id">
              <td class="px-3 py-2">
                <div class="font-mono text-blue-600 text-xs">{{ item.part_number }}</div>
                <div class="text-gray-600">{{ item.part_name }}</div>
              </td>
              <td class="px-3 py-2 text-right">{{ item.required_per_unit }}</td>
              <td class="px-3 py-2 text-right">{{ item.required_quantity }}</td>
              <td class="px-3 py-2 text-right" :class="item.available_quantity < item.required_quantity ? 'text-red-600 font-bold' : ''">
                {{ item.available_quantity }}
              </td>
              <td class="px-3 py-2 text-center">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                  :class="getStatusClass(item.status)"
                >
                  {{ getStatusLabel(item.status) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- 로딩 상태 -->
  <div v-else-if="loading" class="bg-gray-50 rounded-lg p-4 mb-4">
    <div class="flex items-center gap-2 text-gray-500">
      <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
      <span>생산 가능 수량 확인 중...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { workOrderLotApi, type ProductionAvailabilityResponse } from '@/api/inventoryLot'

const props = defineProps<{
  productPartId: number
  requestedQuantity: number
}>()

const loading = ref(false)
const showDetails = ref(false)
const availability = ref<ProductionAvailabilityResponse | null>(null)

// 생산 가능 여부에 따른 스타일
const canProduceClass = computed(() => {
  if (!availability.value) return 'text-gray-600'

  if (availability.value.can_produce >= props.requestedQuantity) {
    return 'text-green-600'
  } else if (availability.value.can_produce > 0) {
    return 'text-orange-600'
  } else {
    return 'text-red-600'
  }
})

// 상태별 스타일
const getStatusClass = (status: string) => {
  switch (status) {
    case 'SUFFICIENT':
      return 'bg-green-100 text-green-800'
    case 'INSUFFICIENT':
      return 'bg-orange-100 text-orange-800'
    case 'OUT_OF_STOCK':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

// 상태 라벨
const getStatusLabel = (status: string) => {
  switch (status) {
    case 'SUFFICIENT':
      return '충분'
    case 'INSUFFICIENT':
      return '부족'
    case 'OUT_OF_STOCK':
      return '재고없음'
    default:
      return status
  }
}

// 가용수량 체크
const checkAvailability = async () => {
  if (!props.productPartId || props.requestedQuantity <= 0) {
    availability.value = null
    return
  }

  loading.value = true
  try {
    availability.value = await workOrderLotApi.checkAvailability(
      props.productPartId,
      props.requestedQuantity
    )
  } catch (error) {
    console.error('가용수량 체크 실패:', error)
    availability.value = null
  } finally {
    loading.value = false
  }
}

// 디바운스 타이머
let debounceTimer: number | null = null

// 완제품 또는 수량 변경 시 체크
watch(
  () => [props.productPartId, props.requestedQuantity],
  () => {
    // 디바운스 적용
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
    debounceTimer = setTimeout(() => {
      checkAvailability()
    }, 500) as unknown as number
  },
  { immediate: true }
)
</script>
