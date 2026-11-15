<template>
  <div class="relative" ref="containerRef">
    <!-- 입력 필드 -->
    <div class="relative">
      <input
        ref="inputRef"
        type="text"
        v-model="searchQuery"
        :placeholder="selectedOption ? '' : placeholder"
        :disabled="disabled"
        :class="[
          'w-full px-3 py-2 pr-8 border rounded-md focus:outline-none focus:ring-2',
          disabled
            ? 'bg-gray-100 border-gray-300 cursor-not-allowed'
            : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500',
          inputClass
        ]"
        @focus="handleFocus"
        @input="handleInput"
        @keydown.down.prevent="navigateDown"
        @keydown.up.prevent="navigateUp"
        @keydown.enter.prevent="selectHighlighted"
        @keydown.escape="closeDropdown"
        @keydown.tab="closeDropdown"
      />
      <!-- 선택된 값 표시 (검색 중이 아닐 때) -->
      <div
        v-if="selectedOption && !isOpen && !searchQuery"
        class="absolute inset-0 flex items-center px-3 pointer-events-none"
      >
        <span class="truncate text-gray-900">{{ selectedOption.code }} - {{ selectedOption.name_ko }}</span>
      </div>
      <!-- 드롭다운 화살표 -->
      <button
        type="button"
        :disabled="disabled"
        class="absolute inset-y-0 right-0 flex items-center px-2 text-gray-400 hover:text-gray-600"
        @click.stop="toggleDropdown"
      >
        <svg
          class="w-5 h-5 transition-transform"
          :class="{ 'rotate-180': isOpen }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    </div>

    <!-- 드롭다운 목록 -->
    <div
      v-if="isOpen"
      class="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto"
    >
      <!-- 결과 없음 -->
      <div v-if="filteredOptions.length === 0" class="px-3 py-2 text-gray-500 text-sm">
        검색 결과가 없습니다
      </div>
      <!-- 옵션 목록 -->
      <div
        v-for="(option, index) in filteredOptions"
        :key="option.id"
        :class="[
          'px-3 py-2 cursor-pointer text-sm',
          highlightedIndex === index ? 'bg-blue-100 text-blue-900' : 'hover:bg-gray-100',
          modelValue === option.id ? 'bg-blue-50 font-medium' : ''
        ]"
        @click="selectOption(option)"
        @mouseenter="highlightedIndex = index"
      >
        <span class="font-mono text-blue-600">{{ option.code }}</span>
        <span class="text-gray-400 mx-1">-</span>
        <span>{{ option.name_ko }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'

interface Option {
  id: number
  code: string
  name_ko: string
  name_en?: string
}

interface Props {
  modelValue?: number
  options: Option[]
  placeholder?: string
  disabled?: boolean
  inputClass?: string
  preserveOrder?: boolean  // true면 code 정렬 없이 전달된 options 순서 유지(예: 최신순)
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '검색 또는 선택',
  disabled: false,
  inputClass: '',
  preserveOrder: false
})

const emit = defineEmits<{
  'update:modelValue': [value: number | undefined]
}>()

// Refs
const containerRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

// 상태
const isOpen = ref(false)
const searchQuery = ref('')
const highlightedIndex = ref(0)

// 선택된 옵션
const selectedOption = computed(() => {
  if (!props.modelValue) return null
  return props.options.find(opt => opt.id === props.modelValue) || null
})

// 정렬된 옵션 (기본: code 알파벳순 / preserveOrder면 전달 순서 유지)
const sortedOptions = computed(() => {
  if (props.preserveOrder) return [...props.options]
  return [...props.options].sort((a, b) => a.code.localeCompare(b.code))
})

// 필터링된 옵션
const filteredOptions = computed(() => {
  if (!searchQuery.value) {
    return sortedOptions.value
  }
  const query = searchQuery.value.toLowerCase()
  return sortedOptions.value.filter(option =>
    option.code.toLowerCase().includes(query) ||
    option.name_ko.toLowerCase().includes(query) ||
    (option.name_en && option.name_en.toLowerCase().includes(query))
  )
})

// 드롭다운 열기
const openDropdown = () => {
  if (props.disabled) return
  isOpen.value = true
  highlightedIndex.value = 0
  nextTick(() => {
    inputRef.value?.focus()
  })
}

// 드롭다운 닫기
const closeDropdown = () => {
  isOpen.value = false
  searchQuery.value = ''
  highlightedIndex.value = 0
}

// 드롭다운 토글
const toggleDropdown = () => {
  if (isOpen.value) {
    closeDropdown()
  } else {
    openDropdown()
  }
}

// 포커스 처리
const handleFocus = () => {
  openDropdown()
}

// 입력 처리
const handleInput = () => {
  if (!isOpen.value) {
    isOpen.value = true
  }
  highlightedIndex.value = 0
}

// 키보드 내비게이션
const navigateDown = () => {
  if (!isOpen.value) {
    openDropdown()
    return
  }
  if (highlightedIndex.value < filteredOptions.value.length - 1) {
    highlightedIndex.value++
  }
}

const navigateUp = () => {
  if (highlightedIndex.value > 0) {
    highlightedIndex.value--
  }
}

// 하이라이트된 항목 선택
const selectHighlighted = () => {
  if (filteredOptions.value.length > 0 && highlightedIndex.value >= 0) {
    const option = filteredOptions.value[highlightedIndex.value]
    if (option) selectOption(option)
  }
}

// 옵션 선택
const selectOption = (option: Option) => {
  emit('update:modelValue', option.id)
  closeDropdown()
}

// 외부 클릭 감지
const handleClickOutside = (event: MouseEvent) => {
  if (containerRef.value && !containerRef.value.contains(event.target as Node)) {
    closeDropdown()
  }
}

// 선택값 변경 시 검색어 초기화
watch(() => props.modelValue, () => {
  searchQuery.value = ''
})

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
