<template>
  <div
    v-if="show"
    ref="modalOverlay"
    class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
    tabindex="-1"
    @keydown.escape="closeModal"
  >
    <div class="relative top-20 mx-auto p-5 border w-full max-w-lg shadow-lg rounded-md bg-white" @click.stop>
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold">
          {{ mode === 'add' ? '하위 부품 추가' : 'BOM 수정' }}
        </h3>
        <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 상위 부품 정보 -->
      <div v-if="parentPart" class="bg-gray-50 rounded-md p-3 mb-4">
        <div class="text-sm text-gray-500">상위 부품</div>
        <div class="font-medium">{{ parentPart.part_number }}</div>
        <div class="text-sm text-gray-600">{{ parentPart.part_name }}</div>
      </div>

      <form @submit.prevent="submitForm" class="space-y-4">
        <!-- 하위 부품 선택 (추가 모드에서만) -->
        <div v-if="mode === 'add'">
          <label class="block text-sm font-medium text-gray-700 mb-1">
            하위 부품 <span class="text-red-500">*</span>
          </label>
          <div class="relative">
            <input
              v-model="childPartSearch"
              type="text"
              placeholder="품번 또는 품명으로 검색..."
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              @input="searchChildParts"
              @focus="showChildDropdown = true"
            />
            <!-- 선택된 부품 표시 -->
            <div v-if="selectedChildPart" class="mt-2 bg-blue-50 border border-blue-200 rounded-md p-2">
              <div class="flex justify-between items-center">
                <div>
                  <span class="font-medium text-blue-700">{{ selectedChildPart.part_number }}</span>
                  <span class="text-blue-600 ml-2">{{ selectedChildPart.part_name }}</span>
                </div>
                <button @click="clearChildPart" type="button" class="text-red-500 hover:text-red-700">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <!-- 검색 결과 드롭다운 -->
            <div
              v-if="showChildDropdown && searchedChildParts.length > 0"
              class="absolute z-10 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-48 overflow-y-auto mt-1"
            >
              <div
                v-for="part in searchedChildParts"
                :key="part.id"
                class="px-3 py-2 hover:bg-gray-100 cursor-pointer"
                @click="selectChildPart(part)"
              >
                <span class="font-medium">{{ part.part_number }}</span>
                <span class="text-gray-500 ml-2">{{ part.part_name }}</span>
                <span v-if="part.specification" class="text-gray-400 text-sm ml-2">{{ part.specification }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 수정 모드: 하위 부품 정보 표시 -->
        <div v-else-if="bomData?.child_part" class="bg-gray-50 rounded-md p-3">
          <div class="text-sm text-gray-500">하위 부품</div>
          <div class="font-medium">{{ bomData.child_part.part_number }}</div>
          <div class="text-sm text-gray-600">{{ bomData.child_part.part_name }}</div>
        </div>

        <!-- 수량 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            수량 <span class="text-red-500">*</span>
          </label>
          <div class="flex gap-2">
            <input
              v-model.number="formData.quantity"
              type="number"
              step="0.001"
              min="0.001"
              required
              class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <select
              v-model="formData.unit_id"
              class="w-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option :value="undefined">단위 선택</option>
              <option v-for="unit in units" :key="unit.id" :value="unit.id">{{ unit.name_ko }}</option>
            </select>
          </div>
        </div>

        <!-- 정렬순서 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">정렬순서</label>
          <input
            v-model.number="formData.sort_order"
            type="number"
            min="0"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <!-- 비고 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">비고</label>
          <textarea
            v-model="formData.remark"
            rows="2"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          ></textarea>
        </div>

        <!-- 에러 메시지 -->
        <div v-if="error" class="bg-red-50 border border-red-200 rounded-md p-3">
          <p class="text-sm text-red-700">{{ error }}</p>
        </div>

        <!-- 버튼 -->
        <div class="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            @click="closeModal"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            취소
          </button>
          <button
            type="submit"
            :disabled="isSubmitting"
            class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {{ isSubmitting ? '저장 중...' : (mode === 'add' ? '추가' : '저장') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { partApi, type Part, type PartListItem } from '@/api/parts'
import { bomApi, type BOMDetailResponse, type BOMCreate, type BOMUpdate } from '@/api/bom'
import { unitApi, type CodeMaster } from '@/api/codeMaster'

interface Props {
  show: boolean
  mode: 'add' | 'edit'
  parentPart: PartListItem | null
  bomData: BOMDetailResponse | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  saved: []
}>()

// 폼 데이터
const formData = ref<{
  quantity: number
  unit_id?: number
  sort_order: number
  remark?: string
}>({
  quantity: 1,
  unit_id: undefined,
  sort_order: 0,
  remark: ''
})

// 하위 부품 검색
const childPartSearch = ref('')
const searchedChildParts = ref<PartListItem[]>([])
const selectedChildPart = ref<PartListItem | null>(null)
const showChildDropdown = ref(false)

// 단위 목록
const units = ref<CodeMaster[]>([])

// 상태
const isSubmitting = ref(false)
const error = ref('')

// 단위 목록 로드
const loadUnits = async () => {
  try {
    const response = await unitApi.getAll()
    units.value = response.data
  } catch (e) {
    console.error('단위 목록 로드 실패:', e)
  }
}

// 하위 부품 검색
let searchTimeout: ReturnType<typeof setTimeout> | null = null
const searchChildParts = () => {
  if (searchTimeout) clearTimeout(searchTimeout)

  searchTimeout = setTimeout(async () => {
    if (!childPartSearch.value.trim()) {
      searchedChildParts.value = []
      return
    }

    try {
      const response = await partApi.getAll({
        keyword: childPartSearch.value,
        is_active: true,
        limit: 20
      })
      // 상위 부품과 같은 부품은 제외
      searchedChildParts.value = response.data.items.filter(
        p => p.id !== props.parentPart?.id
      )
      showChildDropdown.value = true
    } catch (e) {
      console.error('부품 검색 실패:', e)
    }
  }, 300)
}

// 하위 부품 선택
const selectChildPart = (part: PartListItem) => {
  selectedChildPart.value = part
  childPartSearch.value = ''
  searchedChildParts.value = []
  showChildDropdown.value = false
}

// 하위 부품 선택 해제
const clearChildPart = () => {
  selectedChildPart.value = null
  childPartSearch.value = ''
}

// 폼 초기화
const resetForm = () => {
  formData.value = {
    quantity: 1,
    unit_id: undefined,
    sort_order: 0,
    remark: ''
  }
  selectedChildPart.value = null
  childPartSearch.value = ''
  searchedChildParts.value = []
  showChildDropdown.value = false
  error.value = ''
}

// 모달 닫기
const closeModal = () => {
  resetForm()
  emit('close')
}

// 폼 제출
const submitForm = async () => {
  // 추가 모드에서 하위 부품 필수 검증
  if (props.mode === 'add' && !selectedChildPart.value) {
    error.value = '하위 부품을 선택해주세요.'
    return
  }

  if (formData.value.quantity <= 0) {
    error.value = '수량은 0보다 커야 합니다.'
    return
  }

  try {
    isSubmitting.value = true
    error.value = ''

    // 빈 정수 정규화 — Pydantic이 빈 문자열을 정수로 거부함
    const _quantity = (typeof formData.value.quantity === 'number' && !Number.isNaN(formData.value.quantity))
      ? formData.value.quantity
      : 0
    const _sortOrder = (typeof formData.value.sort_order === 'number' && !Number.isNaN(formData.value.sort_order))
      ? formData.value.sort_order
      : undefined

    if (props.mode === 'add') {
      const createData: BOMCreate = {
        parent_part_id: props.parentPart!.id,
        child_part_id: selectedChildPart.value!.id,
        quantity: _quantity,
        unit_id: formData.value.unit_id,
        sort_order: _sortOrder,
        remark: formData.value.remark
      }
      await bomApi.create(createData)
    } else {
      const updateData: BOMUpdate = {
        quantity: _quantity,
        unit_id: formData.value.unit_id,
        sort_order: _sortOrder,
        remark: formData.value.remark
      }
      await bomApi.update(props.bomData!.id, updateData)
    }

    emit('saved')
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'BOM 저장에 실패했습니다.'
  } finally {
    isSubmitting.value = false
  }
}

// show 변경 감지
watch(() => props.show, (newVal) => {
  if (newVal) {
    resetForm()
    loadUnits()

    // 수정 모드인 경우 기존 데이터 로드
    if (props.mode === 'edit' && props.bomData) {
      formData.value = {
        quantity: props.bomData.quantity,
        unit_id: props.bomData.unit_id,
        sort_order: props.bomData.sort_order,
        remark: props.bomData.remark || ''
      }
    }
  }
})

// 드롭다운 외부 클릭 시 닫기
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (!target.closest('.relative')) {
    showChildDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

import { onUnmounted } from 'vue'
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
