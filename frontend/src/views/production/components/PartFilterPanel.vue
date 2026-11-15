<template>
  <div class="filter-panel bg-white shadow rounded-lg p-4 mb-6">
    <!-- 필터 헤더 -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center space-x-2">
        <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
        </svg>
        <h3 class="text-sm font-semibold text-gray-700">상세 필터</h3>
        <span v-if="activeFilterCount > 0" class="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
          {{ activeFilterCount }}개 적용 중
        </span>
      </div>
      <div class="flex items-center space-x-2">
        <button
          @click="toggleExpand"
          class="text-sm text-gray-500 hover:text-gray-700 flex items-center"
        >
          {{ isExpanded ? '접기' : '펼치기' }}
          <svg
            class="w-4 h-4 ml-1 transition-transform"
            :class="{ 'rotate-180': isExpanded }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 기본 검색 (항상 표시) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-3">
      <!-- 키워드 검색 -->
      <div class="col-span-2">
        <label class="block text-xs font-medium text-gray-600 mb-1">품번/부품명 검색</label>
        <div class="relative">
          <input
            v-model="localFilters.keyword"
            type="text"
            placeholder="품번 또는 부품명으로 검색"
            class="w-full pl-8 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            @keyup.enter="emitSearch"
            @input="debouncedSearch"
          />
          <svg class="w-4 h-4 absolute left-2.5 top-2.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      <!-- 대분류 (드롭다운) -->
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">대분류</label>
        <select
          v-model="localFilters.product_line_id"
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          @change="emitSearch"
        >
          <option :value="undefined">전체</option>
          <option v-for="item in productLines" :key="item.id" :value="item.id">
            {{ item.code }} - {{ item.name_ko }}
          </option>
        </select>
      </div>

      <!-- 소분류 (드롭다운) -->
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">소분류</label>
        <select
          v-model="localFilters.part_group_id"
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          @change="emitSearch"
        >
          <option :value="undefined">전체</option>
          <option v-for="item in partGroups" :key="item.id" :value="item.id">
            {{ item.code }} - {{ item.name_ko }}
          </option>
        </select>
      </div>

      <!-- 상태 (드롭다운) -->
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">상태</label>
        <select
          v-model="localFilters.status"
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          @change="emitSearch"
        >
          <option :value="undefined">전체</option>
          <option value="ACTIVE">사용중</option>
          <option value="INACTIVE">미사용</option>
          <option value="OBSOLETE">단종</option>
        </select>
      </div>

      <!-- 분류상태 (미분류 부품 필터) -->
      <div>
        <label class="block text-xs font-medium text-gray-600 mb-1">분류상태</label>
        <select
          v-model="localFilters.classified"
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          @change="emitSearch"
        >
          <option :value="undefined">전체</option>
          <option :value="true">분류됨</option>
          <option :value="false">미분류</option>
        </select>
      </div>

      <!-- 레벨 (인라인 체크박스) - 전체 너비 사용 -->
      <div class="col-span-6">
        <div class="flex items-center gap-2 mb-1">
          <label class="text-xs font-medium text-gray-600">레벨</label>
          <div class="flex items-center gap-1">
            <button
              type="button"
              @click="selectAllLevels"
              class="px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
              title="모든 레벨 선택"
            >
              전체
            </button>
            <button
              type="button"
              @click="clearLevelSelection"
              class="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
              title="모든 레벨 해제"
            >
              해제
            </button>
            <button
              type="button"
              @click="selectDefaultLevels"
              class="px-1.5 py-0.5 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
              :title="mode === 'bom' ? '조립품 레벨만 선택' : '단품 레벨만 선택'"
            >
              기본
            </button>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 py-1">
          <label
            v-for="item in levels"
            :key="item.id"
            class="flex items-center cursor-pointer hover:bg-gray-100 px-2 py-1 rounded"
          >
            <input
              type="checkbox"
              :value="item.id"
              v-model="selectedLevelIds"
              class="mr-1.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 w-4 h-4"
              @change="onLevelChange"
            />
            <span class="text-sm font-medium" :class="item.is_assembly ? 'text-purple-700' : 'text-green-700'">{{ item.code }}</span>
            <span class="text-xs text-gray-500 ml-1">{{ item.name_ko }}</span>
          </label>
        </div>
      </div>
    </div>

    <!-- 확장 필터 영역 -->
    <div v-show="isExpanded" class="border-t pt-3 mt-3">
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <!-- 개발구분 (체크박스 다중선택) -->
        <div class="relative" ref="devTypeDropdownRef">
          <label class="block text-xs font-medium text-gray-600 mb-1">개발구분</label>
          <button
            type="button"
            @click="showDevTypeDropdown = !showDevTypeDropdown"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white text-left flex justify-between items-center hover:border-gray-400"
          >
            <span :class="selectedDevTypeIds.length === 0 ? 'text-gray-400' : 'text-gray-900'">
              {{ devTypeDisplayText }}
            </span>
            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <div
            v-if="showDevTypeDropdown"
            class="absolute z-30 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto"
          >
            <div class="p-2 border-b flex justify-between items-center bg-gray-50">
              <button type="button" @click="selectAllDevTypes" class="text-xs text-blue-600 hover:text-blue-800">전체</button>
              <button type="button" @click="clearDevTypeSelection" class="text-xs text-gray-500 hover:text-gray-700">해제</button>
            </div>
            <div class="p-2 space-y-1">
              <label
                v-for="item in developmentTypes"
                :key="item.id"
                class="flex items-center px-2 py-1.5 hover:bg-blue-50 rounded cursor-pointer"
              >
                <input
                  type="checkbox"
                  :value="item.id"
                  v-model="selectedDevTypeIds"
                  class="mr-2 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  @change="onDevTypeChange"
                />
                <span class="text-sm">{{ item.code }} - {{ item.name_ko }}</span>
              </label>
            </div>
          </div>
        </div>

        <!-- 재질 (드롭다운) -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">재질</label>
          <select
            v-model="localFilters.material_id"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            @change="emitSearch"
          >
            <option :value="undefined">전체</option>
            <option v-for="item in materials" :key="item.id" :value="item.id">
              {{ item.code }} - {{ item.name_ko }}
            </option>
          </select>
        </div>

        <!-- 후처리 (드롭다운) -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">후처리</label>
          <select
            v-model="localFilters.treatment_id"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            @change="emitSearch"
          >
            <option :value="undefined">전체</option>
            <option v-for="item in treatments" :key="item.id" :value="item.id">
              {{ item.code }} - {{ item.name_ko }}
            </option>
          </select>
        </div>

        <!-- 도면여부 (드롭다운) -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">도면여부</label>
          <select
            v-model="localFilters.drawing_type_id"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            @change="emitSearch"
          >
            <option :value="undefined">전체</option>
            <option v-for="item in drawingTypes" :key="item.id" :value="item.id">
              {{ item.code }} - {{ item.name_ko }}
            </option>
          </select>
        </div>

        <!-- 조달구분 (드롭다운) -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">조달구분</label>
          <select
            v-model="localFilters.procurement_type_id"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            @change="emitSearch"
          >
            <option :value="undefined">전체</option>
            <option v-for="item in procurementTypes" :key="item.id" :value="item.id">
              {{ item.code }} - {{ item.name_ko }}
            </option>
          </select>
        </div>

        <!-- 단위 (드롭다운) -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">단위</label>
          <select
            v-model="localFilters.unit_id"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            @change="emitSearch"
          >
            <option :value="undefined">전체</option>
            <option v-for="item in units" :key="item.id" :value="item.id">
              {{ item.code }} - {{ item.name_ko }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- 버튼 영역 -->
    <div class="flex justify-end mt-4 space-x-2 pt-3 border-t">
      <button
        @click="resetFilters"
        class="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 flex items-center"
      >
        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        초기화
      </button>
      <button
        @click="emitSearch"
        class="px-4 py-2 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 flex items-center"
      >
        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        검색
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import {
  levelApi,
  productLineApi,
  partGroupApi,
  developmentTypeApi,
  materialApi,
  treatmentApi,
  drawingTypeApi,
  procurementTypeApi,
  unitApi,
  type CodeMaster,
  type LevelCodeMaster
} from '@/api/codeMaster'

// Props
interface Props {
  mode: 'parts' | 'bom'  // 부품관리 or BOM관리
  modelValue?: FilterValues
}

// 필터 값 인터페이스
export interface FilterValues {
  keyword?: string
  level_ids?: number[]
  product_line_id?: number
  part_group_id?: number
  development_type_ids?: number[]
  material_id?: number
  treatment_id?: number
  drawing_type_id?: number
  procurement_type_id?: number
  unit_id?: number
  status?: string
  classified?: boolean  // 분류상태: undefined=전체, true=분류됨, false=미분류
}

const props = withDefaults(defineProps<Props>(), {
  mode: 'parts'
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: FilterValues): void
  (e: 'search', filters: FilterValues): void
  (e: 'reset'): void
}>()

// 상태
const isExpanded = ref(false)
const isLoading = ref(false)

// 코드 마스터 데이터
const levels = ref<LevelCodeMaster[]>([])
const productLines = ref<CodeMaster[]>([])
const partGroups = ref<CodeMaster[]>([])
const developmentTypes = ref<CodeMaster[]>([])
const materials = ref<CodeMaster[]>([])
const treatments = ref<CodeMaster[]>([])
const drawingTypes = ref<CodeMaster[]>([])
const procurementTypes = ref<CodeMaster[]>([])
const units = ref<CodeMaster[]>([])

// 로컬 필터 상태
const localFilters = ref<FilterValues>({
  keyword: '',
  product_line_id: undefined,
  part_group_id: undefined,
  material_id: undefined,
  treatment_id: undefined,
  drawing_type_id: undefined,
  procurement_type_id: undefined,
  unit_id: undefined,
  status: 'ACTIVE',  // 기본값: 사용중
})

// 다중 선택용 상태
const selectedLevelIds = ref<number[]>([])
const selectedDevTypeIds = ref<number[]>([])

// 드롭다운 상태
const showDevTypeDropdown = ref(false)

// 드롭다운 참조
const devTypeDropdownRef = ref<HTMLElement | null>(null)

// v0.22.0: 모드에 따른 기본 레벨 목록 (부품관리: 전체, BOM관리: F, U, P, K, S, C)
const assemblyLevelCodes = ['F', 'U', 'P', 'K', 'S', 'C']
const defaultLevels = computed(() => {
  if (props.mode === 'parts') {
    return levels.value  // 부품 관리: 전체 레벨
  } else {
    return levels.value.filter(l => assemblyLevelCodes.includes(l.code))
  }
})

// 개발구분 표시 텍스트
const devTypeDisplayText = computed(() => {
  if (selectedDevTypeIds.value.length === 0) return '전체'
  if (selectedDevTypeIds.value.length === developmentTypes.value.length) return '전체'
  const selectedCodes = developmentTypes.value
    .filter(d => selectedDevTypeIds.value.includes(d.id))
    .map(d => d.code)
  if (selectedCodes.length <= 3) return selectedCodes.join(', ')
  return `${selectedCodes.slice(0, 2).join(', ')} 외 ${selectedCodes.length - 2}개`
})

// 활성화된 필터 개수
const activeFilterCount = computed(() => {
  let count = 0
  if (localFilters.value.keyword) count++
  // 레벨 필터: 기본 선택된 레벨과 다르면 필터 활성화로 표시
  const defaultLevelIds = defaultLevels.value.map(l => l.id).sort().join(',')
  const currentLevelIds = [...selectedLevelIds.value].sort().join(',')
  if (currentLevelIds !== defaultLevelIds) count++
  if (localFilters.value.product_line_id) count++
  if (localFilters.value.part_group_id) count++
  if (selectedDevTypeIds.value.length > 0 && selectedDevTypeIds.value.length < developmentTypes.value.length) count++
  if (localFilters.value.material_id) count++
  if (localFilters.value.treatment_id) count++
  if (localFilters.value.drawing_type_id) count++
  if (localFilters.value.procurement_type_id) count++
  if (localFilters.value.unit_id) count++
  if (localFilters.value.status) count++
  if (localFilters.value.classified !== undefined) count++
  return count
})

// 코드 마스터 로드
const loadCodeMasters = async () => {
  try {
    isLoading.value = true
    const [
      levelsRes,
      productLinesRes,
      partGroupsRes,
      devTypesRes,
      materialsRes,
      treatmentsRes,
      drawingTypesRes,
      procTypesRes,
      unitsRes
    ] = await Promise.all([
      levelApi.getAll(),
      productLineApi.getAll(),
      partGroupApi.getAll(),
      developmentTypeApi.getAll(),
      materialApi.getAll(),
      treatmentApi.getAll(),
      drawingTypeApi.getAll(),
      procurementTypeApi.getAll(),
      unitApi.getAll()
    ])

    levels.value = levelsRes.data
    productLines.value = productLinesRes.data
    partGroups.value = partGroupsRes.data
    developmentTypes.value = devTypesRes.data
    materials.value = materialsRes.data
    treatments.value = treatmentsRes.data
    drawingTypes.value = drawingTypesRes.data
    procurementTypes.value = procTypesRes.data
    units.value = unitsRes.data

    // 기본 레벨 선택 (모드에 맞는 레벨 전체 선택)
    setDefaultLevels()
  } catch (error) {
    console.error('코드 마스터 로드 실패:', error)
  } finally {
    isLoading.value = false
  }
}

// 기본 레벨 설정 (모드에 맞는 레벨을 기본 선택)
const setDefaultLevels = () => {
  // v0.22.0: BOM 모드에서는 조립품 레벨(F, P, K, S, C)을 명시적으로 선택
  // 부품 모드: 모든 레벨 기본 선택 (전체 부품 표시)
  if (props.mode === 'bom') {
    selectedLevelIds.value = levels.value
      .filter(l => assemblyLevelCodes.includes(l.code))
      .map(l => l.id)
  } else {
    selectedLevelIds.value = levels.value.map(l => l.id)
  }
}

// 펼치기/접기 토글
const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

// 레벨 전체 선택 (모든 레벨)
const selectAllLevels = () => {
  selectedLevelIds.value = levels.value.map(l => l.id)
  onLevelChange()
}

// 레벨 선택 해제
const clearLevelSelection = () => {
  selectedLevelIds.value = []
  onLevelChange()
}

// 기본 레벨만 선택 (모드에 맞는 레벨)
const selectDefaultLevels = () => {
  selectedLevelIds.value = defaultLevels.value.map(l => l.id)
  onLevelChange()
}

// 개발구분 전체 선택
const selectAllDevTypes = () => {
  selectedDevTypeIds.value = developmentTypes.value.map(d => d.id)
  onDevTypeChange()
}

// 개발구분 선택 해제
const clearDevTypeSelection = () => {
  selectedDevTypeIds.value = []
  onDevTypeChange()
}

// 레벨 변경 핸들러
const onLevelChange = () => {
  localFilters.value.level_ids = selectedLevelIds.value.length > 0 ? [...selectedLevelIds.value] : undefined
}

// 개발구분 변경 핸들러
const onDevTypeChange = () => {
  localFilters.value.development_type_ids = selectedDevTypeIds.value.length > 0 ? [...selectedDevTypeIds.value] : undefined
}

// 검색 emit
const debouncedSearch = useDebouncedSearch(() => emitSearch())
const emitSearch = () => {
  const filters: FilterValues = {
    ...localFilters.value,
    level_ids: selectedLevelIds.value.length > 0 ? [...selectedLevelIds.value] : undefined,
    development_type_ids: selectedDevTypeIds.value.length > 0 ? [...selectedDevTypeIds.value] : undefined,
  }
  emit('update:modelValue', filters)
  emit('search', filters)
}

// 필터 초기화
const resetFilters = () => {
  localFilters.value = {
    keyword: '',
    product_line_id: undefined,
    part_group_id: undefined,
    material_id: undefined,
    treatment_id: undefined,
    drawing_type_id: undefined,
    procurement_type_id: undefined,
    unit_id: undefined,
    status: 'ACTIVE',  // 기본값: 사용중
    classified: undefined,  // 분류상태: 전체
  }
  setDefaultLevels()
  selectedDevTypeIds.value = []
  emit('reset')
  emitSearch()
}

// 외부 클릭 시 드롭다운 닫기
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (devTypeDropdownRef.value && !devTypeDropdownRef.value.contains(target)) {
    showDevTypeDropdown.value = false
  }
}

// props 변경 감시
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    localFilters.value = { ...newVal }
    if (newVal.level_ids) {
      selectedLevelIds.value = [...newVal.level_ids]
    }
    if (newVal.development_type_ids) {
      selectedDevTypeIds.value = [...newVal.development_type_ids]
    }
  }
}, { immediate: true })

onMounted(async () => {
  await loadCodeMasters()
  document.addEventListener('click', handleClickOutside)
  // 초기 필터 값으로 검색 트리거 (기본 레벨이 선택된 상태)
  emitSearch()
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

// 외부에서 사용할 수 있도록 expose
defineExpose({
  resetFilters,
  emitSearch
})
</script>

<style scoped>
.filter-panel {
  transition: all 0.3s ease;
}
</style>
