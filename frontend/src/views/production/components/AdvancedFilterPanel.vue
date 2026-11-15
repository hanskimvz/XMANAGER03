<template>
  <div class="bg-white border border-gray-200 rounded-lg shadow-sm">
    <!-- 헤더 -->
    <div
      class="flex items-center justify-between px-4 py-3 bg-orange-50 border-b border-orange-200 cursor-pointer"
      @click="togglePanel"
    >
      <div class="flex items-center space-x-2">
        <svg class="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
        </svg>
        <span class="font-medium text-orange-800">고급 필터 <span class="font-normal text-orange-600">(데이터 미입력 부품 찾기)</span></span>
        <span v-if="activeFiltersCount > 0" class="px-2 py-0.5 text-xs bg-orange-600 text-white rounded-full">
          {{ activeFiltersCount }}
        </span>
      </div>
      <svg
        class="w-5 h-5 text-orange-600 transition-transform"
        :class="{ 'rotate-180': isExpanded }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </div>

    <!-- 필터 내용 -->
    <div v-show="isExpanded" class="p-4">
      <div class="mb-4">
        <h4 class="text-sm font-medium text-gray-700 mb-2">미입력 데이터 검색</h4>
        <p class="text-xs text-gray-500 mb-3">
          선택한 항목이 비어있는 부품만 검색합니다. (데이터 정비용)
        </p>

        <!-- 체크박스 그리드 -->
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          <label
            v-for="field in missingFieldOptions"
            :key="field.value"
            class="flex items-center space-x-2 p-2 rounded border cursor-pointer transition-colors"
            :class="selectedMissingFields.includes(field.value)
              ? 'bg-orange-50 border-orange-300'
              : 'bg-white border-gray-200 hover:bg-gray-50'"
          >
            <input
              type="checkbox"
              :value="field.value"
              v-model="selectedMissingFields"
              class="rounded border-gray-300 text-orange-600 focus:ring-orange-500"
            />
            <div class="flex-1 min-w-0">
              <span class="text-sm text-gray-700 block truncate">{{ field.label }}</span>
              <span class="text-xs text-gray-400">{{ field.description }}</span>
            </div>
          </label>
        </div>
      </div>

      <!-- 버튼 -->
      <div class="flex justify-end space-x-2 pt-3 border-t">
        <button
          @click="clearFilters"
          class="px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50"
        >
          초기화
        </button>
        <button
          @click="applyFilters"
          class="px-4 py-1.5 text-sm text-white bg-orange-600 rounded hover:bg-orange-700"
        >
          검색
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

// 미입력 필드 옵션 정의
const missingFieldOptions = [
  { value: 'supplier_id', label: '공급업체', description: '미등록' },
  { value: 'part_name_en', label: '영문 부품명', description: '미등록' },
  { value: 'standard_price', label: '기준단가', description: '0 또는 미등록' },
  { value: 'specification', label: '규격', description: '미등록' },
  { value: 'unit_id', label: '단위', description: '미등록' },
  { value: 'material_id', label: '재질', description: '미등록' },
  { value: 'treatment_id', label: '후처리', description: '미등록' },
  { value: 'procurement_type_id', label: '조달구분', description: '미등록' },
  { value: 'development_type_id', label: '개발구분', description: '미등록' },
  { value: 'drawing_file', label: '도면', description: '미첨부' },
  { value: 'photo_file', label: '사진', description: '미첨부' },
  { value: 'description', label: '설명', description: '미등록' },
]

// Props
interface Props {
  modelValue?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => []
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: string[]]
  'search': [missingFields: string[]]
  'reset': []
}>()

// 상태
const isExpanded = ref(false)
const selectedMissingFields = ref<string[]>([...props.modelValue])

// 활성 필터 수
const activeFiltersCount = computed(() => selectedMissingFields.value.length)

// 패널 토글
const togglePanel = () => {
  isExpanded.value = !isExpanded.value
}

// 필터 적용
const applyFilters = () => {
  emit('update:modelValue', [...selectedMissingFields.value])
  emit('search', [...selectedMissingFields.value])
}

// 필터 초기화
const clearFilters = () => {
  selectedMissingFields.value = []
  emit('update:modelValue', [])
  emit('reset')
}

// props 변경 감지
watch(() => props.modelValue, (newValue) => {
  selectedMissingFields.value = [...newValue]
}, { deep: true })
</script>
