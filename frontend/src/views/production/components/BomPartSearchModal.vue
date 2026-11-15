<template>
  <div
    v-if="show"
    class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
    @keydown.escape="$emit('close')"
  >
    <div class="relative top-10 mx-auto p-5 border w-full max-w-6xl shadow-lg rounded-md bg-white" @click.stop>
      <!-- 헤더 -->
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold">제품 선택 (BOM 등록 부품)</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 검색 필터 (v0.22.0: 대분류, 소분류, 레벨, 재질, 후처리 필터 추가) -->
      <div class="bg-gray-50 rounded-lg p-4 mb-4">
        <!-- 첫 번째 줄: 검색어, 부품유형, 검색버튼 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
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
            <label class="block text-sm font-medium text-gray-700 mb-1">부품 유형</label>
            <select
              v-model="filters.part_type"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              @change="searchParts"
            >
              <option value="all">전체</option>
              <option value="parent">상위 부품 (완제품/반제품)</option>
              <option value="child">하위 부품 (원자재/부자재)</option>
            </select>
          </div>
          <div class="flex items-end gap-2">
            <button
              @click="resetFilters"
              class="px-3 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
              title="필터 초기화"
            >
              초기화
            </button>
            <button
              @click="searchParts"
              class="flex-1 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
              검색
            </button>
          </div>
        </div>
        <!-- 두 번째 줄: 대분류, 소분류, 레벨, 재질, 후처리 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">대분류</label>
            <select
              v-model="filters.product_line_id"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
              @change="searchParts"
            >
              <option :value="undefined">전체</option>
              <option v-for="item in productLines" :key="item.id" :value="item.id">
                {{ item.code }} - {{ item.name_ko }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">소분류</label>
            <select
              v-model="filters.part_group_id"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
              @change="searchParts"
            >
              <option :value="undefined">전체</option>
              <option v-for="item in partGroups" :key="item.id" :value="item.id">
                {{ item.code }} - {{ item.name_ko }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">레벨</label>
            <select
              v-model="filters.level_id"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
              @change="searchParts"
            >
              <option :value="undefined">전체</option>
              <option v-for="item in levels" :key="item.id" :value="item.id">
                {{ item.code }} - {{ item.name_ko }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">재질</label>
            <select
              v-model="filters.material_id"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
              @change="searchParts"
            >
              <option :value="undefined">전체</option>
              <option v-for="item in materials" :key="item.id" :value="item.id">
                {{ item.code }} - {{ item.name_ko }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">후처리</label>
            <select
              v-model="filters.treatment_id"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
              @change="searchParts"
            >
              <option :value="undefined">전체</option>
              <option v-for="item in treatments" :key="item.id" :value="item.id">
                {{ item.code }} - {{ item.name_ko }}
              </option>
            </select>
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
          <div class="mb-2">
            <svg class="w-12 h-12 mx-auto text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p>BOM에 등록된 부품이 없습니다.</p>
          <p class="text-sm mt-1">먼저 BOM 관리에서 부품을 등록해주세요.</p>
        </div>
        <div v-else class="max-h-96 overflow-y-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50 sticky top-0">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">품번</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">품명</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">대분류</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">소분류</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">레벨</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">재질</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">후처리</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase w-20">선택</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr
                v-for="part in parts"
                :key="part.id"
                class="hover:bg-blue-50 cursor-pointer"
                @click="selectPart(part)"
              >
                <td class="px-3 py-2">
                  <span class="font-mono text-blue-600">{{ part.part_number_display || part.part_number }}</span>
                  <span v-if="(part as any).is_protected" class="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-red-100 text-red-700 whitespace-nowrap"
                    :title="`전속: ${(part as any).protected_customer?.partner_name || '지정 고객'}`">🔒 전속</span>
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
                  <span v-if="part.part_group" class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-purple-100 text-purple-700">
                    {{ part.part_group.code }}
                  </span>
                </td>
                <td class="px-3 py-2 text-center">
                  <span v-if="part.level" :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', getLevelColorClass(part.level.code)]">
                    {{ part.level.code }}
                  </span>
                </td>
                <td class="px-3 py-2 text-center">
                  <span v-if="part.material" class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-100 text-green-700">
                    {{ part.material.code }}
                  </span>
                </td>
                <td class="px-3 py-2 text-center">
                  <span v-if="part.treatment" class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-orange-100 text-orange-700">
                    {{ part.treatment.code }}
                  </span>
                </td>
                <td class="px-3 py-2 text-center">
                  <button
                    @click.stop="selectPart(part)"
                    class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
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
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { bomApi, type BomPartItem } from '@/api/bom'
import {
  productLineApi,
  partGroupApi,
  levelApi,
  materialApi,
  treatmentApi,
  type CodeMaster,
  type LevelCodeMaster
} from '@/api/codeMaster'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select', part: BomPartItem): void
}>()

// 코드 마스터 데이터 (v0.22.0)
const productLines = ref<CodeMaster[]>([])
const partGroups = ref<CodeMaster[]>([])
const levels = ref<LevelCodeMaster[]>([])
const materials = ref<CodeMaster[]>([])
const treatments = ref<CodeMaster[]>([])

// 검색
const searchInput = ref<HTMLInputElement | null>(null)
const searchKeyword = ref('')
const filters = ref<{
  part_type: string
  product_line_id?: number
  part_group_id?: number
  level_id?: number
  material_id?: number
  treatment_id?: number
}>({
  part_type: 'all',
  product_line_id: undefined,
  part_group_id: undefined,
  level_id: undefined,
  material_id: undefined,
  treatment_id: undefined,
})

// 부품 목록
const parts = ref<BomPartItem[]>([])
const loading = ref(false)
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(15)
const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value) || 1)

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

// 코드 마스터 로드 (v0.22.0)
async function loadCodeMasters() {
  try {
    const [plRes, pgRes, lvRes, mtRes, trRes] = await Promise.all([
      productLineApi.getAll(),
      partGroupApi.getAll(),
      levelApi.getAll(),
      materialApi.getAll(),
      treatmentApi.getAll(),
    ])
    productLines.value = plRes.data.filter((item: CodeMaster) => item.is_active)
    partGroups.value = pgRes.data.filter((item: CodeMaster) => item.is_active)
    levels.value = lvRes.data.filter((item: LevelCodeMaster) => item.is_active)
    materials.value = mtRes.data.filter((item: CodeMaster) => item.is_active)
    treatments.value = trRes.data.filter((item: CodeMaster) => item.is_active)
  } catch (error) {
    console.error('코드 마스터 로드 실패:', error)
  }
}

// 필터 초기화 (v0.22.0)
function resetFilters() {
  searchKeyword.value = ''
  filters.value = {
    part_type: 'all',
    product_line_id: undefined,
    part_group_id: undefined,
    level_id: undefined,
    material_id: undefined,
    treatment_id: undefined,
  }
  searchParts()
}

// 부품 검색
const searchParts = async () => {
  loading.value = true
  currentPage.value = 1
  try {
    const response = await bomApi.getBomParts({
      keyword: searchKeyword.value || undefined,
      part_type: filters.value.part_type,
      product_line_id: filters.value.product_line_id,
      part_group_id: filters.value.part_group_id,
      level_id: filters.value.level_id,
      material_id: filters.value.material_id,
      treatment_id: filters.value.treatment_id,
      skip: 0,
      limit: pageSize.value
    })
    parts.value = response.data.items
    totalCount.value = response.data.total
  } catch (error) {
    console.error('BOM 부품 검색 실패:', error)
    parts.value = []
    totalCount.value = 0
  } finally {
    loading.value = false
  }
}

// 페이지 변경
const changePage = async (page: number) => {
  loading.value = true
  currentPage.value = page
  try {
    const response = await bomApi.getBomParts({
      keyword: searchKeyword.value || undefined,
      part_type: filters.value.part_type,
      product_line_id: filters.value.product_line_id,
      part_group_id: filters.value.part_group_id,
      level_id: filters.value.level_id,
      material_id: filters.value.material_id,
      treatment_id: filters.value.treatment_id,
      skip: (page - 1) * pageSize.value,
      limit: pageSize.value
    })
    parts.value = response.data.items
    totalCount.value = response.data.total
  } catch (error) {
    console.error('BOM 부품 페이지 로드 실패:', error)
  } finally {
    loading.value = false
  }
}

// 부품 선택
const selectPart = (part: BomPartItem) => {
  emit('select', part)
  emit('close')
}

// 코드 마스터 초기 로드
onMounted(() => {
  loadCodeMasters()
})

// 모달 열릴 때 초기화
watch(() => props.show, async (newVal) => {
  if (newVal) {
    searchKeyword.value = ''
    filters.value = {
      part_type: 'all',
      product_line_id: undefined,
      part_group_id: undefined,
      level_id: undefined,
      material_id: undefined,
      treatment_id: undefined,
    }
    currentPage.value = 1

    // 코드 마스터가 로드되지 않았다면 로드
    if (productLines.value.length === 0) {
      await loadCodeMasters()
    }

    await searchParts()

    nextTick(() => {
      searchInput.value?.focus()
    })
  }
})
</script>
