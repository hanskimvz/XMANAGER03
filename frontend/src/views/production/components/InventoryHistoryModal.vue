<template>
  <div
    v-if="show"
    ref="modalOverlay"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    tabindex="-1"
    @keydown.escape="handleClose"
  >
    <div class="bg-white rounded-lg p-6 w-full max-w-3xl max-h-[80vh] flex flex-col" @click.stop>
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">거래 이력</h3>
        <div class="flex items-center gap-2">
          <button
            @click="exportHistoryExcel"
            :disabled="!inventory || transactions.length === 0"
            class="px-3 py-1.5 text-sm rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed"
            title="사유 포함 거래 이력 엑셀 다운로드"
          >
            📊 엑셀 다운로드
          </button>
          <button @click="handleClose" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 부품 정보 -->
      <div class="bg-gray-50 rounded-lg p-4 mb-4">
        <div class="flex justify-between">
          <div>
            <div class="font-medium">
              {{ inventory?.part?.part_number_display || inventory?.part?.part_number }}
            </div>
            <div class="text-sm text-gray-600">{{ inventory?.part?.part_name }}</div>
          </div>
          <div class="text-right">
            <div class="text-sm text-gray-500">현재고</div>
            <div class="font-semibold text-lg">{{ formatNumber(inventory?.quantity_on_hand) }}</div>
          </div>
        </div>
      </div>

      <!-- 이력 테이블 -->
      <div class="flex-1 overflow-auto">
        <div v-if="loading" class="text-center py-8">
          <p class="text-gray-500">로딩 중...</p>
        </div>

        <div v-else-if="error" class="text-center py-8">
          <p class="text-red-500">{{ error }}</p>
        </div>

        <table v-else class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50 sticky top-0">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">일시</th>
              <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">유형</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">변동</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">변동 전</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">변동 후</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">사유</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">참조</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="tx in transactions" :key="tx.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                {{ formatDateTime(tx.transaction_date) }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-center">
                <span
                  class="px-2 py-1 text-xs rounded-full"
                  :class="getTypeStyle(tx.transaction_type)"
                >
                  {{ getTypeLabel(tx.transaction_type) }}
                </span>
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-right font-semibold"
                  :class="{
                    'text-green-600': tx.transaction_type === 'IN' || tx.transaction_type === 'RETURN',
                    'text-red-600': tx.transaction_type === 'OUT',
                    'text-blue-600': tx.transaction_type === 'ADJUST' || tx.transaction_type === 'COUNT'
                  }">
                <span v-if="tx.transaction_type === 'IN' || tx.transaction_type === 'RETURN'">+</span>
                <span v-else-if="tx.transaction_type === 'OUT'">-</span>
                {{ formatNumber(tx.quantity) }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-500">
                {{ tx.quantity_before !== null ? formatNumber(tx.quantity_before) : '-' }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-right font-medium">
                {{ tx.quantity_after !== null ? formatNumber(tx.quantity_after) : '-' }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-600 break-words max-w-sm" :title="tx.reason || ''">
                {{ tx.reason || '-' }}
              </td>
              <td class="px-4 py-3 text-sm text-gray-500">
                <span v-if="tx.reference_type || tx.reference_id">
                  {{ tx.reference_type }}{{ tx.reference_id ? `: ${tx.reference_id}` : '' }}
                </span>
                <span v-else>-</span>
              </td>
            </tr>
            <tr v-if="transactions.length === 0">
              <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                거래 이력이 없습니다.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 페이지네이션 -->
      <div v-if="totalItems > pageSize" class="mt-4 flex justify-center">
        <nav class="inline-flex rounded-md shadow-sm">
          <button
            @click="loadPage(currentPage - 1)"
            :disabled="currentPage === 1"
            class="px-3 py-2 border border-gray-300 rounded-l-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            이전
          </button>
          <span class="px-4 py-2 border-t border-b border-gray-300 text-sm bg-white">
            {{ currentPage }} / {{ totalPages }}
          </span>
          <button
            @click="loadPage(currentPage + 1)"
            :disabled="currentPage >= totalPages"
            class="px-3 py-2 border border-gray-300 rounded-r-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            다음
          </button>
        </nav>
      </div>

      <!-- 닫기 버튼 -->
      <div class="flex justify-end mt-4">
        <button
          @click="handleClose"
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          닫기
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import {
  inventoryApi,
  transactionTypeLabels,
  type InventoryListItem,
  type InventoryTransaction,
  type TransactionType
} from '@/api/inventory'
import { downloadAuthedUrl } from '@/utils/download'

interface Props {
  show: boolean
  inventory: InventoryListItem | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

// 상태
const loading = ref(false)
const error = ref<string | null>(null)
const transactions = ref<InventoryTransaction[]>([])
const totalItems = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

// 총 페이지 수
const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value))

// 거래 이력 엑셀 다운로드 (사유 포함, 전체 이력)
const exportHistoryExcel = () => {
  if (!props.inventory) return
  const pn = props.inventory.part?.part_number_display || props.inventory.part?.part_number || `inv${props.inventory.id}`
  const filename = `inventory_history_${pn}.xlsx`.replace(/[/\\]/g, '_')
  downloadAuthedUrl(`/inventory/${props.inventory.id}/transactions/export/excel`, filename)
    .catch((e) => { console.error('이력 엑셀 다운로드 실패', e); error.value = '엑셀 다운로드에 실패했습니다.' })
}

// 이력 로드
const loadTransactions = async () => {
  if (!props.inventory) return

  loading.value = true
  error.value = null

  try {
    const response = await inventoryApi.getTransactions(props.inventory.id, {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    })
    transactions.value = response.items
    totalItems.value = response.total
  } catch (err: any) {
    console.error('거래 이력 조회 실패:', err)
    error.value = err.response?.data?.detail || '거래 이력을 불러오는 데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

// 페이지 변경
const loadPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadTransactions()
}

// 모달 표시 시 데이터 로드
watch(() => props.show, (newValue) => {
  if (newValue && props.inventory) {
    currentPage.value = 1
    loadTransactions()
  }
})

// 유틸리티 함수
const getTypeLabel = (type: TransactionType) => {
  return transactionTypeLabels[type] || type
}

const getTypeStyle = (type: TransactionType) => {
  switch (type) {
    case 'IN':
      return 'bg-green-100 text-green-800'
    case 'OUT':
      return 'bg-red-100 text-red-800'
    case 'ADJUST':
      return 'bg-blue-100 text-blue-800'
    case 'RETURN':
      return 'bg-purple-100 text-purple-800'
    case 'COUNT':
      return 'bg-yellow-100 text-yellow-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const formatNumber = (value: number | undefined | null) => {
  if (value === undefined || value === null) return '0'
  return new Intl.NumberFormat('ko-KR').format(value)
}

const formatDateTime = (dateString: string | undefined | null) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 닫기
const handleClose = () => {
  emit('close')
}
</script>
