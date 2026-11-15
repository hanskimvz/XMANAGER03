<template>
  <div
    v-if="show"
    ref="modalOverlay"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    tabindex="-1"
    @keydown.escape="$emit('close')"
  >
    <div class="bg-white rounded-lg p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto" @click.stop>
      <h3 class="text-lg font-semibold mb-4">재고 조정</h3>

      <!-- 부품 정보 -->
      <div class="bg-gray-50 rounded-lg p-4 mb-4">
        <div class="text-sm text-gray-500 mb-1">부품</div>
        <div class="font-medium">
          {{ inventory?.part?.part_number_display || inventory?.part?.part_number }}
        </div>
        <div class="text-sm text-gray-600">{{ inventory?.part?.part_name }}</div>
        <div class="mt-2 flex justify-between">
          <span class="text-sm text-gray-500">현재고</span>
          <span class="font-semibold text-lg">{{ formatNumber(inventory?.quantity_on_hand) }}</span>
        </div>
      </div>

      <!-- 입력 폼 -->
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">거래 유형 *</label>
          <div class="grid grid-cols-3 gap-2">
            <button
              v-for="type in transactionTypes"
              :key="type.value"
              @click="formData.transaction_type = type.value"
              class="px-3 py-2 border rounded-md text-sm transition-colors"
              :class="{
                'border-blue-500 bg-blue-50 text-blue-700': formData.transaction_type === type.value,
                'border-gray-300 hover:border-gray-400': formData.transaction_type !== type.value
              }"
            >
              {{ type.label }}
            </button>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">수량 *</label>
          <input
            v-model.number="formData.quantity"
            type="number"
            min="0"
            step="0.001"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            :placeholder="quantityPlaceholder"
          />
          <p v-if="formData.transaction_type && formData.quantity" class="text-sm text-gray-500 mt-1">
            예상 재고: <span class="font-semibold">{{ formatNumber(expectedQuantity) }}</span>
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">사유</label>
          <input
            v-model="formData.reason"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="조정 사유 입력"
          />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">참조 유형</label>
            <select
              v-model="formData.reference_type"
              class="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">선택안함</option>
              <option value="PO">구매주문(PO)</option>
              <option value="MO">생산지시(MO)</option>
              <option value="SO">판매주문(SO)</option>
              <option value="MANUAL">수동조정</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">참조 번호</label>
            <input
              v-model="formData.reference_id"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="문서 번호"
            />
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">비고</label>
          <textarea
            v-model="formData.remarks"
            rows="2"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="추가 메모"
          ></textarea>
        </div>

        <!-- 로트 생성 옵션 (입고 시에만 표시) -->
        <div v-if="formData.transaction_type === 'IN'" class="bg-blue-50 rounded-lg p-4">
          <label class="flex items-center cursor-pointer">
            <input
              v-model="formData.create_lot"
              type="checkbox"
              class="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mr-2"
            />
            <span class="text-sm font-medium text-gray-700">로트도 함께 생성</span>
          </label>
          <p class="text-xs text-gray-500 mt-1 ml-6">
            체크하면 FIFO 출고를 위한 로트 정보가 함께 생성됩니다.
          </p>

          <!-- 로트 정보 입력 -->
          <div v-if="formData.create_lot" class="mt-3 space-y-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">로트번호</label>
              <input
                v-model="formData.lot_number"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="자동생성 (비워두면 날짜 기반 생성)"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">입고 단가</label>
              <input
                v-model.number="formData.unit_cost"
                type="number"
                min="0"
                step="1"
                class="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="단가 (선택)"
              />
            </div>
          </div>
        </div>

        <!-- 파일 첨부 섹션 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">증빙서류 첨부</label>
          <div
            class="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-blue-400 transition-colors"
            @click="triggerFileInput"
            @dragover.prevent="onDragOver"
            @dragleave="onDragLeave"
            @drop.prevent="onDrop"
            :class="{ 'border-blue-400 bg-blue-50': isDragging }"
          >
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png"
              class="hidden"
              @change="onFileChange"
            />
            <svg class="mx-auto h-8 w-8 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
              <path d="M28 8H12a4 4 0 00-4 4v24a4 4 0 004 4h24a4 4 0 004-4V20L28 8z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M28 8v12h12M32 32H16M32 24H16" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <p class="mt-1 text-sm text-gray-500">
              클릭하거나 파일을 드래그하여 업로드
            </p>
            <p class="text-xs text-gray-400">
              PDF, DOC, XLS, JPG, PNG (최대 10MB)
            </p>
          </div>

          <!-- 첨부된 파일 목록 -->
          <div v-if="selectedFiles.length > 0" class="mt-3 space-y-2">
            <div
              v-for="(file, index) in selectedFiles"
              :key="index"
              class="flex items-center justify-between p-2 bg-gray-50 rounded"
            >
              <div class="flex items-center gap-2 min-w-0">
                <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span class="text-sm text-gray-700 truncate">{{ file.name }}</span>
                <span class="text-xs text-gray-400">({{ formatFileSize(file.size) }})</span>
              </div>
              <button
                @click.stop="removeFile(index)"
                class="text-red-500 hover:text-red-700 flex-shrink-0"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 버튼 -->
      <div class="flex justify-end space-x-2 mt-6">
        <button
          @click="handleClose"
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          취소
        </button>
        <button
          @click="handleSubmit"
          :disabled="!isValid"
          class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          저장
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import type { InventoryListItem, InventoryAdjust, TransactionType } from '@/api/inventory'

interface Props {
  show: boolean
  inventory: InventoryListItem | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', data: InventoryAdjust, files: File[]): void
}>()

// 파일 관련 상태
const fileInput = ref<HTMLInputElement | null>(null)
const selectedFiles = ref<File[]>([])
const isDragging = ref(false)

// 거래 유형 옵션
const transactionTypes = [
  { value: 'IN' as TransactionType, label: '입고' },
  { value: 'OUT' as TransactionType, label: '출고' },
  { value: 'ADJUST' as TransactionType, label: '조정' },
]

// 폼 데이터
const formData = reactive<{
  transaction_type: TransactionType
  quantity: number | undefined
  reason: string
  reference_type: string
  reference_id: string
  remarks: string
  create_lot: boolean
  lot_number: string
  unit_cost: number | undefined
}>({
  transaction_type: 'IN',
  quantity: undefined,
  reason: '',
  reference_type: '',
  reference_id: '',
  remarks: '',
  create_lot: true,  // 기본값: 로트 생성
  lot_number: '',
  unit_cost: undefined
})

// 폼 초기화
const resetForm = () => {
  formData.transaction_type = 'IN'
  formData.quantity = undefined
  formData.reason = ''
  formData.reference_type = ''
  formData.reference_id = ''
  formData.remarks = ''
  formData.create_lot = true
  formData.lot_number = ''
  formData.unit_cost = undefined
  selectedFiles.value = []
  isDragging.value = false
}

// 모달 표시 시 폼 초기화
watch(() => props.show, (newValue) => {
  if (newValue) {
    resetForm()
  }
})

// 수량 플레이스홀더
const quantityPlaceholder = computed(() => {
  switch (formData.transaction_type) {
    case 'IN':
      return '입고할 수량'
    case 'OUT':
      return '출고할 수량'
    case 'ADJUST':
      return '조정 후 수량'
    default:
      return '수량'
  }
})

// 예상 재고 계산
const expectedQuantity = computed(() => {
  if (!props.inventory || formData.quantity === undefined) return 0

  const currentQty = props.inventory.quantity_on_hand || 0
  const qty = formData.quantity || 0

  switch (formData.transaction_type) {
    case 'IN':
      return currentQty + qty
    case 'OUT':
      return Math.max(0, currentQty - qty)
    case 'ADJUST':
      return qty
    default:
      return currentQty
  }
})

// 유효성 검사
const isValid = computed(() => {
  if (!formData.transaction_type) return false
  if (formData.quantity === undefined || formData.quantity < 0) return false

  // 출고 시 현재고 초과 체크
  if (formData.transaction_type === 'OUT') {
    const currentQty = props.inventory?.quantity_on_hand || 0
    if (formData.quantity > currentQty) return false
  }

  return true
})

// 숫자 포맷
const formatNumber = (value: number | undefined | null) => {
  if (value === undefined || value === null) return '0'
  return new Intl.NumberFormat('ko-KR').format(value)
}

// 닫기
const handleClose = () => {
  emit('close')
}

// 제출
const handleSubmit = () => {
  if (!isValid.value) return

  const data: InventoryAdjust = {
    transaction_type: formData.transaction_type,
    quantity: formData.quantity!,
    reason: formData.reason || undefined,
    reference_type: formData.reference_type || undefined,
    reference_id: formData.reference_id || undefined,
    remarks: formData.remarks || undefined,
    // 로트 생성 정보 (입고 시에만)
    create_lot: formData.transaction_type === 'IN' ? formData.create_lot : undefined,
    lot_number: formData.create_lot && formData.lot_number ? formData.lot_number : undefined,
    unit_cost: formData.create_lot && formData.unit_cost ? formData.unit_cost : undefined
  }

  emit('submit', data, selectedFiles.value)
}

// 파일 관련 함수들
const triggerFileInput = () => {
  fileInput.value?.click()
}

const onFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files) {
    addFiles(Array.from(input.files))
  }
  // 같은 파일 재선택 가능하도록 초기화
  input.value = ''
}

const onDragOver = () => {
  isDragging.value = true
}

const onDragLeave = () => {
  isDragging.value = false
}

const onDrop = (event: DragEvent) => {
  isDragging.value = false
  if (event.dataTransfer?.files) {
    addFiles(Array.from(event.dataTransfer.files))
  }
}

const addFiles = (files: File[]) => {
  const maxSize = 10 * 1024 * 1024 // 10MB
  const allowedTypes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'image/jpeg',
    'image/png'
  ]

  for (const file of files) {
    // 파일 크기 체크
    if (file.size > maxSize) {
      alert(`파일 "${file.name}"의 크기가 10MB를 초과합니다.`)
      continue
    }

    // 파일 타입 체크
    if (!allowedTypes.includes(file.type)) {
      alert(`파일 "${file.name}"은(는) 지원하지 않는 형식입니다.`)
      continue
    }

    // 중복 체크
    if (selectedFiles.value.some(f => f.name === file.name && f.size === file.size)) {
      continue
    }

    selectedFiles.value.push(file)
  }
}

const removeFile = (index: number) => {
  selectedFiles.value.splice(index, 1)
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>
