<template>
  <div
    v-if="show"
    ref="modalOverlay"
    class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
    tabindex="-1"
    @keydown.escape="$emit('close')"
  >
    <div class="relative top-10 mx-auto p-5 border w-full max-w-5xl shadow-lg rounded-md bg-white" @click.stop>
      <!-- 헤더 -->
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold">부품 선택 {{ multiSelect ? '(다중 선택)' : '' }}</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 검색 필터 (v0.22.0: 소분류, 재질, 후처리 필터 추가) -->
      <div class="bg-gray-50 rounded-lg p-4 mb-4">
        <!-- 첫 번째 줄: 검색어, 대분류, 소분류, 레벨 -->
        <div class="grid grid-cols-5 gap-3 mb-3">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">검색</label>
            <input
              ref="searchInput"
              v-model="searchKeyword"
              type="text"
              placeholder="품번 또는 품명으로 검색..."
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              @keydown.enter="searchParts"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">대분류</label>
            <select
              v-model="filters.product_line_id"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              @change="searchParts"
            >
              <option :value="undefined">전체</option>
              <option v-for="pl in productLines" :key="pl.id" :value="pl.id">
                {{ pl.code }} - {{ pl.name_ko }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">소분류</label>
            <select
              v-model="filters.part_group_id"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              @change="searchParts"
            >
              <option :value="undefined">전체</option>
              <option v-for="pg in partGroups" :key="pg.id" :value="pg.id">
                {{ pg.code }} - {{ pg.name_ko }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">레벨</label>
            <select
              v-model="filters.level_id"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              @change="searchParts"
            >
              <option :value="undefined">전체</option>
              <option v-for="lv in levels" :key="lv.id" :value="lv.id">
                {{ lv.code }} - {{ lv.name_ko }}
              </option>
            </select>
          </div>
        </div>
        <!-- 두 번째 줄: 재질, 후처리, 초기화/검색 버튼 -->
        <div class="grid grid-cols-5 gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">재질</label>
            <select
              v-model="filters.material_id"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              @change="searchParts"
            >
              <option :value="undefined">전체</option>
              <option v-for="mt in materials" :key="mt.id" :value="mt.id">
                {{ mt.code }} - {{ mt.name_ko }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">후처리</label>
            <select
              v-model="filters.treatment_id"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              @change="searchParts"
            >
              <option :value="undefined">전체</option>
              <option v-for="tr in treatments" :key="tr.id" :value="tr.id">
                {{ tr.code }} - {{ tr.name_ko }}
              </option>
            </select>
          </div>
          <div></div>
          <div class="flex items-end">
            <button
              @click="resetFilters"
              class="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
            >
              초기화
            </button>
          </div>
          <div class="flex items-end">
            <button
              @click="searchParts"
              class="w-full px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
              검색
            </button>
          </div>
        </div>
      </div>

      <!-- 선택된 부품 목록 (다중 선택 모드) -->
      <div v-if="multiSelect && selectedParts.length > 0" class="mb-4">
        <div class="text-sm font-medium text-gray-700 mb-2">선택된 부품 ({{ selectedParts.length }}개)</div>
        <div class="flex flex-wrap gap-2">
          <div
            v-for="part in selectedParts"
            :key="part.id"
            class="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
          >
            <span class="font-mono">{{ part.part_number_display || part.part_number }}</span>
            <span class="mx-1">-</span>
            <span>{{ part.part_name }}</span>
            <button
              @click="togglePartSelection(part)"
              class="ml-2 text-blue-600 hover:text-blue-800"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- 부품 목록 테이블 -->
      <div class="border rounded-lg overflow-hidden">
        <div v-if="loading" class="text-center py-8 text-gray-500">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
          로딩 중...
        </div>
        <div v-else-if="parts.length === 0" class="text-center py-8 text-gray-500">
          검색 결과가 없습니다.
        </div>
        <div v-else class="max-h-96 overflow-y-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50 sticky top-0">
              <tr>
                <th v-if="multiSelect" class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase w-12">
                  <input
                    type="checkbox"
                    :checked="isAllSelected"
                    :indeterminate="isSomeSelected && !isAllSelected"
                    @change="toggleSelectAll"
                    class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                </th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">품번</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">품명</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">대분류</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">레벨</th>
                <th v-if="!multiSelect" class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase w-20">선택</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr
                v-for="part in parts"
                :key="part.id"
                :class="[
                  'hover:bg-blue-50 cursor-pointer',
                  isPartSelected(part) ? 'bg-blue-100' : '',
                  isPartExcluded(part) ? 'opacity-50 cursor-not-allowed' : ''
                ]"
                @click="!isPartExcluded(part) && (multiSelect ? togglePartSelection(part) : selectSinglePart(part))"
              >
                <td v-if="multiSelect" class="px-3 py-2 text-center" @click.stop>
                  <input
                    type="checkbox"
                    :checked="isPartSelected(part)"
                    :disabled="isPartExcluded(part)"
                    @change="togglePartSelection(part)"
                    class="rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                  />
                </td>
                <td class="px-3 py-2">
                  <span class="font-mono text-blue-600">{{ part.part_number_display || part.part_number }}</span>
                </td>
                <td class="px-3 py-2">
                  <div>{{ part.part_name }}</div>
                  <div v-if="part.specification" class="text-xs text-gray-400">{{ part.specification }}</div>
                </td>
                <td class="px-3 py-2 text-center">
                  <span v-if="part.product_line" class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-700">
                    {{ part.product_line.code }}
                  </span>
                </td>
                <td class="px-3 py-2 text-center">
                  <span v-if="part.level" :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', getLevelColorClass(part.level.code)]">
                    {{ part.level.code }}
                  </span>
                </td>
                <td v-if="!multiSelect" class="px-3 py-2 text-center">
                  <button
                    @click.stop="selectSinglePart(part)"
                    :disabled="isPartExcluded(part)"
                    class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    선택
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 페이지네이션 -->
      <div v-if="totalCount > 0" class="flex justify-between items-center mt-4 text-sm text-gray-500">
        <span>총 {{ totalCount }}건</span>
        <div class="flex gap-2 items-center">
          <button
            @click="currentPage > 1 && changePage(currentPage - 1)"
            :disabled="currentPage <= 1"
            class="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
          >
            이전
          </button>
          <span>{{ currentPage }} / {{ totalPages }}</span>
          <button
            @click="currentPage < totalPages && changePage(currentPage + 1)"
            :disabled="currentPage >= totalPages"
            class="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
          >
            다음
          </button>
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
          v-if="multiSelect"
          @click="confirmSelection"
          :disabled="selectedParts.length === 0"
          class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          {{ selectedParts.length }}개 선택 완료
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { partApi, type PartListItem } from '@/api/parts'
import {
  levelApi,
  productLineApi,
  partGroupApi,
  materialApi,
  treatmentApi,
  type CodeMaster
} from '@/api/codeMaster'

const props = defineProps<{
  show: boolean
  multiSelect?: boolean
  excludePartIds?: number[]  // 제외할 부품 ID (이미 추가된 부품 등)
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select', part: PartListItem): void
  (e: 'selectMultiple', parts: PartListItem[]): void
}>()

// 코드 마스터 (v0.22.0: 소분류, 재질, 후처리 추가)
const levels = ref<CodeMaster[]>([])
const productLines = ref<CodeMaster[]>([])
const partGroups = ref<CodeMaster[]>([])
const materials = ref<CodeMaster[]>([])
const treatments = ref<CodeMaster[]>([])

// 검색
const searchInput = ref<HTMLInputElement | null>(null)
const searchKeyword = ref('')
const filters = ref<{
  product_line_id?: number
  part_group_id?: number
  level_id?: number
  material_id?: number
  treatment_id?: number
}>({
  product_line_id: undefined,
  part_group_id: undefined,
  level_id: undefined,
  material_id: undefined,
  treatment_id: undefined,
})

// 부품 목록
const parts = ref<PartListItem[]>([])
const loading = ref(false)
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(15)
const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

// v0.21.0: 레벨별 색상 구분 함수
function getLevelColorClass(levelCode: string): string {
  const colorMap: Record<string, string> = {
    'M': 'bg-yellow-100 text-yellow-800',      // 내부공정
    'O': 'bg-orange-100 text-orange-800',      // 외주공정
    'R': 'bg-green-100 text-green-800',        // 원자재 (단품)
    'C': 'bg-blue-100 text-blue-800',          // 조합부품
    'S': 'bg-indigo-100 text-indigo-800',      // 서브어셈블리
    'P': 'bg-pink-100 text-pink-800',          // 패키지
    'K': 'bg-cyan-100 text-cyan-800',          // 키트
    'F': 'bg-red-100 text-red-800',            // 최종품 (완제품)
  }
  return colorMap[levelCode] || 'bg-purple-100 text-purple-700'
}

// 선택
const selectedParts = ref<PartListItem[]>([])

// 코드 마스터 로드 (v0.22.0: 소분류, 재질, 후처리 추가)
const loadCodeMasters = async () => {
  try {
    const [levelsRes, productLinesRes, partGroupsRes, materialsRes, treatmentsRes] = await Promise.all([
      levelApi.getAll(),
      productLineApi.getAll(),
      partGroupApi.getAll(),
      materialApi.getAll(),
      treatmentApi.getAll(),
    ])
    levels.value = levelsRes.data.filter((item: CodeMaster) => item.is_active)
    productLines.value = productLinesRes.data.filter((item: CodeMaster) => item.is_active)
    partGroups.value = partGroupsRes.data.filter((item: CodeMaster) => item.is_active)
    materials.value = materialsRes.data.filter((item: CodeMaster) => item.is_active)
    treatments.value = treatmentsRes.data.filter((item: CodeMaster) => item.is_active)
  } catch (error) {
    console.error('코드 마스터 로드 실패:', error)
  }
}

// v0.22.0: 필터 초기화
const resetFilters = () => {
  searchKeyword.value = ''
  filters.value = {
    product_line_id: undefined,
    part_group_id: undefined,
    level_id: undefined,
    material_id: undefined,
    treatment_id: undefined,
  }
  searchParts()
}

// 부품 검색 (v0.22.0: 소분류, 재질, 후처리 필터 추가)
const searchParts = async () => {
  loading.value = true
  currentPage.value = 1
  try {
    const response = await partApi.getAll({
      keyword: searchKeyword.value || undefined,
      product_line_id: filters.value.product_line_id,
      part_group_id: filters.value.part_group_id,
      level_id: filters.value.level_id,
      material_id: filters.value.material_id,
      treatment_id: filters.value.treatment_id,
      is_active: true,
      skip: 0,
      limit: pageSize.value,
      order_by: 'created_at',
      order_desc: true
    })
    parts.value = response.data.items
    totalCount.value = response.data.total
  } catch (error) {
    console.error('부품 검색 실패:', error)
    parts.value = []
    totalCount.value = 0
  } finally {
    loading.value = false
  }
}

// 페이지 변경 (v0.22.0: 소분류, 재질, 후처리 필터 추가)
const changePage = async (page: number) => {
  loading.value = true
  currentPage.value = page
  try {
    const response = await partApi.getAll({
      keyword: searchKeyword.value || undefined,
      product_line_id: filters.value.product_line_id,
      part_group_id: filters.value.part_group_id,
      level_id: filters.value.level_id,
      material_id: filters.value.material_id,
      treatment_id: filters.value.treatment_id,
      is_active: true,
      skip: (page - 1) * pageSize.value,
      limit: pageSize.value,
      order_by: 'created_at',
      order_desc: true
    })
    parts.value = response.data.items
    totalCount.value = response.data.total
  } catch (error) {
    console.error('부품 페이지 로드 실패:', error)
  } finally {
    loading.value = false
  }
}

// 부품 제외 여부
const isPartExcluded = (part: PartListItem): boolean => {
  return props.excludePartIds?.includes(part.id) ?? false
}

// 부품 선택 여부
const isPartSelected = (part: PartListItem): boolean => {
  return selectedParts.value.some(p => p.id === part.id)
}

// 전체 선택 여부
const isAllSelected = computed(() => {
  const selectableParts = parts.value.filter(p => !isPartExcluded(p))
  return selectableParts.length > 0 && selectableParts.every(p => isPartSelected(p))
})

const isSomeSelected = computed(() => {
  return parts.value.some(p => isPartSelected(p))
})

// 부품 선택 토글
const togglePartSelection = (part: PartListItem) => {
  if (isPartExcluded(part)) return

  const index = selectedParts.value.findIndex(p => p.id === part.id)
  if (index >= 0) {
    selectedParts.value.splice(index, 1)
  } else {
    selectedParts.value.push(part)
  }
}

// 전체 선택 토글
const toggleSelectAll = () => {
  const selectableParts = parts.value.filter(p => !isPartExcluded(p))

  if (isAllSelected.value) {
    // 현재 페이지 부품들 선택 해제
    selectableParts.forEach(part => {
      const index = selectedParts.value.findIndex(p => p.id === part.id)
      if (index >= 0) {
        selectedParts.value.splice(index, 1)
      }
    })
  } else {
    // 현재 페이지 부품들 선택
    selectableParts.forEach(part => {
      if (!isPartSelected(part)) {
        selectedParts.value.push(part)
      }
    })
  }
}

// 단일 선택 (다중 선택 모드가 아닐 때)
const selectSinglePart = (part: PartListItem) => {
  if (isPartExcluded(part)) return
  emit('select', part)
  emit('close')
}

// 선택 확정 (다중 선택 모드)
const confirmSelection = () => {
  emit('selectMultiple', [...selectedParts.value])
  emit('close')
}

// 모달 열릴 때 초기화 (v0.22.0: 소분류, 재질, 후처리 필터 추가)
watch(() => props.show, async (newVal) => {
  if (newVal) {
    searchKeyword.value = ''
    filters.value = {
      product_line_id: undefined,
      part_group_id: undefined,
      level_id: undefined,
      material_id: undefined,
      treatment_id: undefined,
    }
    selectedParts.value = []
    currentPage.value = 1

    if (levels.value.length === 0) {
      await loadCodeMasters()
    }
    await searchParts()

    nextTick(() => {
      searchInput.value?.focus()
    })
  }
})

onMounted(() => {
  loadCodeMasters()
})
</script>
