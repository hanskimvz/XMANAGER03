<template>
  <div class="container mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">품번 생성 시뮬레이터</h1>
      <RouterLink
        to="/code-master"
        class="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        코드 관리
      </RouterLink>
    </div>

    <!-- 설명 -->
    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
      <h2 class="text-sm font-semibold text-blue-800 mb-2">품번 구조 설명 (v1.1)</h2>
      <p class="text-sm text-blue-700 mb-2">
        품번은 아래 코드들의 조합으로 자동 생성됩니다. 각 분류를 선택하면 미리보기에서 결과를 확인할 수 있습니다.
      </p>
      <div class="font-mono text-xs bg-white px-3 py-2 rounded border">
        <span class="text-red-600">[대분류(4)]</span>
        <span class="text-gray-400">-</span>
        <span class="text-orange-600">[소분류(3)]</span>
        <span class="text-gray-400">-</span>
        <span class="text-yellow-600">[품목코드(5)]</span>
        <span class="text-gray-400">-</span>
        <span class="text-green-600">[재질(2)]</span>
        <span class="text-gray-400">-</span>
        <span class="text-blue-600">[후처리(2)]</span>
        <span class="text-gray-500 ml-2">= 총 20자리 (하이픈 포함)</span>
      </div>
      <div class="mt-2 text-xs text-gray-600">
        <span class="font-medium">예시:</span>
        <span class="font-mono ml-2 bg-white px-2 py-0.5 rounded">HB01-DCP-00001-A6-NK</span>
      </div>
      <div class="mt-2 text-xs text-orange-600 bg-orange-50 px-2 py-1 rounded">
        ※ 재질/후처리가 다르면 별개의 부품입니다 (재고 별도 관리)
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- 왼쪽: 코드 선택 영역 -->
      <div class="lg:col-span-2 space-y-4">
        <!-- 대분류 (제품라인) - 4자리 -->
        <div class="bg-white rounded-lg shadow p-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            <span class="text-red-600">대분류 - 제품라인 (4자리)</span> <span class="text-red-500">*</span>
          </label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="item in productLines"
              :key="item.id"
              @click="selected.productLine = item"
              :class="[
                'px-3 py-2 rounded border text-sm font-mono transition-all',
                selected.productLine?.id === item.id
                  ? 'bg-red-500 text-white border-red-500'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-red-300 hover:bg-red-50'
              ]"
            >
              {{ item.code }} - {{ item.name_ko }}
            </button>
          </div>
          <p v-if="productLines.length === 0" class="text-gray-400 text-sm mt-2">
            코드 마스터에서 대분류를 등록해주세요
          </p>
        </div>

        <!-- 소분류 (품목군) - 3자리 -->
        <div class="bg-white rounded-lg shadow p-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            <span class="text-orange-600">소분류 - 품목군 (3자리)</span> <span class="text-red-500">*</span>
          </label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="item in partGroups"
              :key="item.id"
              @click="selected.partGroup = item"
              :class="[
                'px-3 py-2 rounded border text-sm font-mono transition-all',
                selected.partGroup?.id === item.id
                  ? 'bg-orange-500 text-white border-orange-500'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-orange-300 hover:bg-orange-50'
              ]"
            >
              {{ item.code }} - {{ item.name_ko }}
            </button>
          </div>
          <p v-if="partGroups.length === 0" class="text-gray-400 text-sm mt-2">
            코드 마스터에서 소분류를 등록해주세요
          </p>
        </div>

        <!-- 재질 - 2자리 -->
        <div class="bg-white rounded-lg shadow p-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            <span class="text-green-600">재질 (2자리)</span>
          </label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="item in materials"
              :key="item.id"
              @click="selected.material = item"
              :class="[
                'px-3 py-2 rounded border text-sm font-mono transition-all',
                selected.material?.id === item.id
                  ? 'bg-green-500 text-white border-green-500'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-green-300 hover:bg-green-50'
              ]"
            >
              {{ item.code }} - {{ item.name_ko }}
            </button>
          </div>
        </div>

        <!-- 후처리 - 2자리 -->
        <div class="bg-white rounded-lg shadow p-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            <span class="text-blue-600">후처리 (2자리)</span>
          </label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="item in treatments"
              :key="item.id"
              @click="selected.treatment = item"
              :class="[
                'px-3 py-2 rounded border text-sm font-mono transition-all',
                selected.treatment?.id === item.id
                  ? 'bg-blue-500 text-white border-blue-500'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-blue-300 hover:bg-blue-50'
              ]"
            >
              {{ item.code }} - {{ item.name_ko }}
            </button>
          </div>
        </div>

        <!-- 분류 속성 (품번에 미포함) -->
        <div class="bg-gray-50 rounded-lg shadow p-4">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">분류 속성 (품번에 미포함, 검색/필터용)</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- 분류1 - 개발구분 -->
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">분류1 - 개발구분 (단일선택)</label>
              <div class="flex flex-wrap gap-1">
                <button
                  v-for="item in developmentTypes"
                  :key="item.id"
                  @click="selected.developmentType = item"
                  :class="[
                    'px-2 py-1 rounded border text-xs font-mono transition-all',
                    selected.developmentType?.id === item.id
                      ? 'bg-indigo-500 text-white border-indigo-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:border-indigo-300'
                  ]"
                  :title="item.name_ko"
                >
                  {{ item.code }}
                </button>
              </div>
            </div>

            <!-- 분류2 - 부품유형 (다중선택) -->
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">
                분류2 - 부품유형 <span class="text-orange-500 font-bold">(다중선택)</span>
              </label>
              <div class="flex flex-wrap gap-1">
                <button
                  v-for="item in partTypes"
                  :key="item.id"
                  @click="togglePartType(item)"
                  :class="[
                    'px-2 py-1 rounded border text-xs font-mono transition-all',
                    selectedPartTypes.includes(item.id)
                      ? 'bg-purple-500 text-white border-purple-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:border-purple-300'
                  ]"
                  :title="item.name_ko"
                >
                  {{ item.code }}
                </button>
              </div>
            </div>

            <!-- 분류3 - 도면여부 -->
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">분류3 - 도면여부 (단일선택)</label>
              <div class="flex flex-wrap gap-1">
                <button
                  v-for="item in drawingTypes"
                  :key="item.id"
                  @click="selected.drawingType = item"
                  :class="[
                    'px-2 py-1 rounded border text-xs font-mono transition-all',
                    selected.drawingType?.id === item.id
                      ? 'bg-teal-500 text-white border-teal-500'
                      : 'bg-white text-gray-700 border-gray-300 hover:border-teal-300'
                  ]"
                  :title="item.name_ko"
                >
                  {{ item.code }}
                </button>
              </div>
            </div>
          </div>

          <!-- 레벨 (BOM) -->
          <div class="mt-4">
            <label class="block text-xs font-medium text-gray-500 mb-1">레벨 - BOM 구조 (단일선택)</label>
            <div class="flex flex-wrap gap-1">
              <button
                v-for="item in levels"
                :key="item.id"
                @click="selected.level = item"
                :class="[
                  'px-2 py-1 rounded border text-xs font-mono transition-all',
                  selected.level?.id === item.id
                    ? 'bg-cyan-500 text-white border-cyan-500'
                    : 'bg-white text-gray-700 border-gray-300 hover:border-cyan-300'
                ]"
                :title="item.name_ko"
              >
                {{ item.code }} - {{ item.name_ko }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 오른쪽: 미리보기 -->
      <div class="lg:col-span-1">
        <div class="bg-white rounded-lg shadow p-4 sticky top-4">
          <h3 class="text-lg font-semibold mb-4">품번 미리보기</h3>

          <!-- 생성된 품번 -->
          <div class="bg-gray-100 rounded-lg p-4 mb-4">
            <div class="text-xs text-gray-500 mb-1">생성된 품번</div>
            <div class="text-2xl font-mono font-bold text-gray-800">
              {{ generatedPartNumber || '코드를 선택하세요' }}
            </div>
            <div class="text-xs text-gray-400 mt-1">
              총 {{ generatedPartNumber ? generatedPartNumber.length : 0 }}자리
            </div>
          </div>

          <!-- 선택된 코드 상세 -->
          <div class="space-y-3">
            <div class="flex justify-between items-center py-2 border-b">
              <span class="text-sm text-gray-500">대분류 (4자리)</span>
              <span class="font-mono text-red-600">{{ selected.productLine?.code || '____' }}</span>
            </div>
            <div class="flex justify-between items-center py-2 border-b">
              <span class="text-sm text-gray-500">소분류 (3자리)</span>
              <span class="font-mono text-orange-600">{{ selected.partGroup?.code || '___' }}</span>
            </div>
            <div class="flex justify-between items-center py-2 border-b">
              <span class="text-sm text-gray-500">품목코드 (5자리)</span>
              <span class="font-mono text-yellow-600">00001</span>
            </div>
            <div class="flex justify-between items-center py-2 border-b">
              <span class="text-sm text-gray-500">재질 (2자리)</span>
              <span class="font-mono text-green-600">{{ selected.material?.code || 'XX' }}</span>
            </div>
            <div class="flex justify-between items-center py-2 border-b">
              <span class="text-sm text-gray-500">후처리 (2자리)</span>
              <span class="font-mono text-blue-600">{{ selected.treatment?.code || 'NN' }}</span>
            </div>
          </div>

          <!-- 분류 속성 표시 -->
          <div class="mt-4 pt-4 border-t">
            <h4 class="text-xs font-semibold text-gray-500 mb-2">분류 속성 (품번 미포함)</h4>
            <div class="space-y-1 text-xs">
              <div class="flex justify-between">
                <span class="text-gray-400">분류1 (개발구분)</span>
                <span class="font-mono">{{ selected.developmentType ? `${selected.developmentType.code} - ${selected.developmentType.name_ko}` : '-' }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-400">분류2 (부품유형)</span>
                <span class="font-mono">{{ selectedPartTypeDisplay || '-' }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-400">분류3 (도면여부)</span>
                <span class="font-mono">{{ selected.drawingType ? `${selected.drawingType.code} - ${selected.drawingType.name_ko}` : '-' }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-400">레벨 (BOM)</span>
                <span class="font-mono">{{ selected.level ? `${selected.level.code} - ${selected.level.name_ko}` : '-' }}</span>
              </div>
            </div>
          </div>

          <!-- 버튼 -->
          <div class="mt-6 space-y-2">
            <button
              @click="resetSelection"
              class="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            >
              초기화
            </button>
            <button
              @click="copyToClipboard"
              :disabled="!generatedPartNumber"
              class="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              품번 복사
            </button>
          </div>

          <!-- 안내 -->
          <div class="mt-4 text-xs text-gray-500 space-y-1">
            <p>* 실제 부품 등록 시 품목코드(5자리)는 자동으로 부여됩니다.</p>
            <p>* 재질/후처리 미선택 시 기본값(XX, NN)이 사용됩니다.</p>
            <p>* 동일 부품이라도 후처리 전/후는 별개 품번으로 관리됩니다.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import {
  productLineApi,
  partGroupApi,
  developmentTypeApi,
  partTypeApi,
  drawingTypeApi,
  materialApi,
  treatmentApi,
  levelApi,
  type CodeMaster
} from '@/api/codeMaster'

// 코드 데이터
const productLines = ref<CodeMaster[]>([])
const partGroups = ref<CodeMaster[]>([])
const developmentTypes = ref<CodeMaster[]>([])
const partTypes = ref<CodeMaster[]>([])
const drawingTypes = ref<CodeMaster[]>([])
const materials = ref<CodeMaster[]>([])
const treatments = ref<CodeMaster[]>([])
const levels = ref<CodeMaster[]>([])

// 선택된 코드
const selected = ref<{
  productLine: CodeMaster | null
  partGroup: CodeMaster | null
  developmentType: CodeMaster | null
  drawingType: CodeMaster | null
  material: CodeMaster | null
  treatment: CodeMaster | null
  level: CodeMaster | null
}>({
  productLine: null,
  partGroup: null,
  developmentType: null,
  drawingType: null,
  material: null,
  treatment: null,
  level: null
})

// 부품유형 다중선택
const selectedPartTypes = ref<number[]>([])

// 부품유형 토글
const togglePartType = (item: CodeMaster) => {
  const index = selectedPartTypes.value.indexOf(item.id)
  if (index === -1) {
    selectedPartTypes.value.push(item.id)
  } else {
    selectedPartTypes.value.splice(index, 1)
  }
}

// 선택된 부품유형 표시
const selectedPartTypeDisplay = computed(() => {
  if (selectedPartTypes.value.length === 0) return ''
  return partTypes.value
    .filter(pt => selectedPartTypes.value.includes(pt.id))
    .map(pt => pt.code)
    .join(', ')
})

// 생성된 품번 (예: HB01-DCP-00001-A6-NK)
const generatedPartNumber = computed(() => {
  if (!selected.value.productLine || !selected.value.partGroup) {
    return ''
  }

  const productLine = selected.value.productLine.code
  const partGroup = selected.value.partGroup.code
  const itemCode = '00001'
  const material = selected.value.material?.code || 'XX'
  const treatment = selected.value.treatment?.code || 'NN'

  return `${productLine}-${partGroup}-${itemCode}-${material}-${treatment}`
})

// 초기화
const resetSelection = () => {
  selected.value = {
    productLine: null,
    partGroup: null,
    developmentType: null,
    drawingType: null,
    material: null,
    treatment: null,
    level: null
  }
  selectedPartTypes.value = []
}

// 클립보드 복사
const copyToClipboard = async () => {
  if (!generatedPartNumber.value) return

  try {
    await navigator.clipboard.writeText(generatedPartNumber.value)
    alert('품번이 복사되었습니다: ' + generatedPartNumber.value)
  } catch (err) {
    console.error('복사 실패:', err)
  }
}

// 데이터 로드
const loadData = async () => {
  try {
    const results = await Promise.allSettled([
      productLineApi.getAll(),
      partGroupApi.getAll(),
      developmentTypeApi.getAll(),
      partTypeApi.getAll(),
      drawingTypeApi.getAll(),
      materialApi.getAll(),
      treatmentApi.getAll(),
      levelApi.getAll()
    ])

    if (results[0].status === 'fulfilled') {
      productLines.value = results[0].value.data.filter(item => item.is_active)
    }
    if (results[1].status === 'fulfilled') {
      partGroups.value = results[1].value.data.filter(item => item.is_active)
    }
    if (results[2].status === 'fulfilled') {
      developmentTypes.value = results[2].value.data.filter(item => item.is_active)
    }
    if (results[3].status === 'fulfilled') {
      partTypes.value = results[3].value.data.filter(item => item.is_active)
    }
    if (results[4].status === 'fulfilled') {
      drawingTypes.value = results[4].value.data.filter(item => item.is_active)
    }
    if (results[5].status === 'fulfilled') {
      materials.value = results[5].value.data.filter(item => item.is_active)
    }
    if (results[6].status === 'fulfilled') {
      treatments.value = results[6].value.data.filter(item => item.is_active)
    }
    if (results[7].status === 'fulfilled') {
      levels.value = results[7].value.data.filter(item => item.is_active)
    }
  } catch (err) {
    console.error('데이터 로드 실패:', err)
  }
}

onMounted(() => {
  loadData()
})
</script>
