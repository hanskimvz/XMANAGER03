<template>
  <div class="container mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">코드 마스터 관리</h1>
      <RouterLink
        to="/code-simulator"
        class="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        품번 시뮬레이터
      </RouterLink>
    </div>

    <!-- 품번 자동생성 구조도 (드롭다운) -->
    <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200 mb-6">
      <button
        @click="showPartNumberGuide = !showPartNumberGuide"
        class="w-full px-4 py-3 flex justify-between items-center text-left"
      >
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="text-sm font-semibold text-blue-800">품번 자동생성 구조 (v0.20.0)</span>
          <span class="font-mono text-xs bg-white px-2 py-0.5 rounded text-blue-700">HB01-DCP-001-01-A6-NK-R</span>
        </div>
        <svg
          class="w-5 h-5 text-blue-600 transition-transform"
          :class="{ 'rotate-180': showPartNumberGuide }"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <div v-show="showPartNumberGuide" class="px-4 pb-4 border-t border-blue-200">
        <div class="mt-3 flex flex-wrap items-center gap-1 text-xs font-mono">
          <span
            class="px-2 py-1 rounded cursor-pointer transition-all"
            :class="activeTab === 'productLine' ? 'bg-blue-500 text-white' : 'bg-white text-blue-700 hover:bg-blue-100'"
            @click="changeTab('productLine')"
          >대분류(4)</span>
          <span class="text-gray-400">-</span>
          <span
            class="px-2 py-1 rounded cursor-pointer transition-all"
            :class="activeTab === 'partGroup' ? 'bg-blue-500 text-white' : 'bg-white text-blue-700 hover:bg-blue-100'"
            @click="changeTab('partGroup')"
          >소분류(3)</span>
          <span class="text-gray-400">-</span>
          <span class="px-2 py-1 bg-gray-200 text-gray-600 rounded">품목코드(5)</span>
          <span class="text-gray-400">-</span>
          <span
            class="px-2 py-1 rounded cursor-pointer transition-all"
            :class="activeTab === 'material' ? 'bg-blue-500 text-white' : 'bg-white text-blue-700 hover:bg-blue-100'"
            @click="changeTab('material')"
          >재질(2)</span>
          <span class="text-gray-400">-</span>
          <span
            class="px-2 py-1 rounded cursor-pointer transition-all"
            :class="activeTab === 'treatment' ? 'bg-blue-500 text-white' : 'bg-white text-blue-700 hover:bg-blue-100'"
            @click="changeTab('treatment')"
          >후처리(2)</span>
          <span class="text-gray-400">-</span>
          <span
            class="px-2 py-1 rounded cursor-pointer transition-all"
            :class="activeTab === 'level' ? 'bg-blue-500 text-white' : 'bg-white text-pink-700 hover:bg-pink-100'"
            @click="changeTab('level')"
          >레벨(1)</span>
        </div>
        <div class="mt-2 text-xs text-gray-600">
          <span class="font-medium">예시:</span>
          <span class="font-mono ml-2 bg-white px-2 py-0.5 rounded">HB01-DCP-001-01-A6-NK-R</span>
          <span class="ml-2 text-gray-500">→ HB01(대분류) - DCP(소분류) - 001-01(품목코드) - A6(재질) - NK(후처리) - R(레벨)</span>
        </div>
        <div class="mt-3 pt-2 border-t border-blue-100">
          <p class="text-xs font-medium text-gray-600 mb-1">분류 속성 (품번 미포함):</p>
          <div class="flex flex-wrap gap-4 text-xs text-gray-500">
            <span>
              <span
                class="cursor-pointer hover:text-blue-600"
                :class="activeTab === 'developmentType' ? 'text-blue-600 font-semibold' : ''"
                @click="changeTab('developmentType')"
              >개발구분(1)</span>: D(개발), S(규격), M(상용), R(원소재), C(주문품), P(공정)
            </span>
            <span>
              <span
                class="cursor-pointer hover:text-blue-600"
                :class="activeTab === 'partType' ? 'text-blue-600 font-semibold' : ''"
                @click="changeTab('partType')"
              >부품유형(1)</span>: P(가공), E(고무), O(광학) 등 <strong>(다중선택)</strong>
            </span>
            <span>
              <span
                class="cursor-pointer hover:text-blue-600"
                :class="activeTab === 'drawingType' ? 'text-blue-600 font-semibold' : ''"
                @click="changeTab('drawingType')"
              >도면여부(1)</span>: D(도면), S(표준), N(없음)
            </span>
          </div>
        </div>
        <div class="mt-2 text-xs text-orange-600 bg-orange-50 px-2 py-1 rounded">
          ※ 분류 속성(개발구분, 부품유형, 도면여부)은 품번에 포함되지 않고 별도 속성으로 관리됩니다.
        </div>
      </div>
    </div>

    <!-- 탭 네비게이션 - 그룹 분리 -->
    <div class="mb-6">
      <!-- 품번 구성요소 -->
      <div class="mb-2">
        <span class="text-xs font-semibold text-blue-600 uppercase tracking-wider">품번 구성요소</span>
      </div>
      <div class="border-b border-gray-200 mb-4">
        <nav class="-mb-px flex space-x-4 overflow-x-auto">
          <button
            v-for="tab in partNumberTabs"
            :key="tab.id"
            @click="changeTab(tab.id)"
            :class="[
              'py-3 px-2 border-b-2 font-medium text-sm whitespace-nowrap',
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            ]"
          >
            {{ tab.name }}<span class="text-gray-400 ml-1">({{ tab.count }})</span>
          </button>
        </nav>
      </div>

      <!-- 관리 데이터 -->
      <div class="mb-2">
        <span class="text-xs font-semibold text-purple-600 uppercase tracking-wider">관리 데이터 (품번 미포함)</span>
      </div>
      <div class="border-b border-gray-200">
        <nav class="-mb-px flex space-x-4 overflow-x-auto">
          <button
            v-for="tab in managementTabs"
            :key="tab.id"
            @click="changeTab(tab.id)"
            :class="[
              'py-3 px-2 border-b-2 font-medium text-sm whitespace-nowrap',
              activeTab === tab.id
                ? 'border-purple-500 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            ]"
          >
            {{ tab.name }}<span class="text-gray-400 ml-1">({{ tab.count }})</span>
          </button>
        </nav>
      </div>
    </div>

    <!-- 공통 테이블 컴포넌트 -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-semibold">{{ currentTabName }} 목록</h2>
        <button
          @click="openAddModal"
          class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded flex items-center"
        >
          <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          추가
        </button>
      </div>

      <!-- 로딩 중 -->
      <div v-if="loading" class="text-center py-8">
        <p class="text-gray-500">로딩 중...</p>
      </div>

      <!-- 에러 -->
      <div v-else-if="error" class="text-center py-8">
        <p class="text-red-500">{{ error }}</p>
      </div>

      <!-- 데이터 테이블 -->
      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase w-10">#</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">코드</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">한글명</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">영문명</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">설명</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-20">상태</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-24">작업</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr
              v-for="(item, index) in currentData"
              :key="item.id"
              class="hover:bg-gray-50 group"
              draggable="true"
              @dragstart="onDragStart($event, index)"
              @dragover.prevent="onDragOver($event, index)"
              @drop="onDrop($event, index)"
              @dragend="onDragEnd"
              :class="{ 'bg-blue-50': dragOverIndex === index }"
            >
              <!-- 순서 (드래그 핸들) -->
              <td class="px-2 py-3 text-sm text-gray-400 cursor-move">
                <span class="group-hover:hidden">{{ index + 1 }}</span>
                <svg class="w-4 h-4 hidden group-hover:block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16" />
                </svg>
              </td>
              <!-- 코드 (인라인 편집) -->
              <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                <div v-if="editingId === item.id && editingField === 'code'" class="flex items-center gap-1">
                  <input
                    v-model="editingValue"
                    type="text"
                    class="w-full px-2 py-1 text-sm border rounded focus:ring-blue-500 focus:border-blue-500 font-medium"
                    @keydown.enter="saveInlineEdit(item)"
                    @keydown.escape="cancelInlineEdit"
                    @blur="saveInlineEdit(item)"
                    ref="inlineInput"
                  />
                </div>
                <div
                  v-else
                  class="cursor-pointer hover:bg-blue-100 rounded px-1 py-0.5 inline-block"
                  @click="startInlineEdit(item, 'code', item.code)"
                  title="클릭하여 수정"
                >
                  {{ item.code }}
                </div>
              </td>
              <!-- 한글명 (인라인 편집) -->
              <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                <div v-if="editingId === item.id && editingField === 'name_ko'" class="flex items-center gap-1">
                  <input
                    v-model="editingValue"
                    type="text"
                    class="w-full px-2 py-1 text-sm border rounded focus:ring-blue-500 focus:border-blue-500"
                    @keydown.enter="saveInlineEdit(item)"
                    @keydown.escape="cancelInlineEdit"
                    @blur="saveInlineEdit(item)"
                    ref="inlineInput"
                  />
                </div>
                <div
                  v-else
                  class="cursor-pointer hover:bg-blue-100 rounded px-1 py-0.5 inline-block"
                  @click="startInlineEdit(item, 'name_ko', item.name_ko)"
                  title="클릭하여 수정"
                >
                  {{ item.name_ko }}
                </div>
              </td>
              <!-- 영문명 (인라인 편집) -->
              <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                <div v-if="editingId === item.id && editingField === 'name_en'" class="flex items-center gap-1">
                  <input
                    v-model="editingValue"
                    type="text"
                    class="w-full px-2 py-1 text-sm border rounded focus:ring-blue-500 focus:border-blue-500"
                    @keydown.enter="saveInlineEdit(item)"
                    @keydown.escape="cancelInlineEdit"
                    @blur="saveInlineEdit(item)"
                  />
                </div>
                <div
                  v-else
                  class="cursor-pointer hover:bg-blue-100 rounded px-1 py-0.5 inline-block"
                  @click="startInlineEdit(item, 'name_en', item.name_en || '')"
                  title="클릭하여 수정"
                >
                  {{ item.name_en || '-' }}
                </div>
              </td>
              <!-- 설명 -->
              <td class="px-4 py-3 text-sm text-gray-500">
                {{ item.description || '-' }}
              </td>
              <!-- 상태 -->
              <td class="px-4 py-3 whitespace-nowrap">
                <span
                  :class="[
                    'px-2 inline-flex text-xs leading-5 font-semibold rounded-full cursor-pointer',
                    item.is_active ? 'bg-green-100 text-green-800 hover:bg-green-200' : 'bg-red-100 text-red-800 hover:bg-red-200'
                  ]"
                  @click="toggleActive(item)"
                  title="클릭하여 상태 변경"
                >
                  {{ item.is_active ? '사용' : '미사용' }}
                </span>
              </td>
              <!-- 작업 -->
              <td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
                <button
                  @click="openEditModal(item)"
                  class="text-blue-600 hover:text-blue-900 mr-2"
                  title="전체 수정"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  @click="deleteItem(item)"
                  class="text-red-600 hover:text-red-900"
                  title="삭제"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="currentData.length === 0" class="text-center py-8 text-gray-500">
          데이터가 없습니다
        </div>
      </div>
    </div>

    <!-- 모달 -->
    <CodeMasterModal
      :show="showModal"
      :is-edit="isEditMode"
      :initial-data="selectedItem"
      @close="closeModal"
      @submit="handleSubmit"
    />

    <!-- 토스트 알림 -->
    <div
      v-if="toast.show"
      class="fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg transition-all"
      :class="toast.type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'"
    >
      {{ toast.message }}
    </div>

    <!-- 일괄 업데이트 확인 다이얼로그 -->
    <Teleport to="body">
      <div
        v-if="showBatchUpdateDialog"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black bg-opacity-50"
        @keydown.escape="cancelBatchUpdate"
      >
        <div class="bg-white rounded-lg shadow-xl w-full max-w-lg p-6" @click.stop>
          <!-- 헤더 -->
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 rounded-full bg-yellow-100 flex items-center justify-center">
              <svg class="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <h3 class="text-lg font-semibold">품번 일괄 변경 확인</h3>
              <p class="text-sm text-gray-500">코드 변경에 따른 품번 업데이트 여부를 선택하세요</p>
            </div>
          </div>

          <!-- 변경 내용 -->
          <div class="bg-gray-50 rounded-lg p-4 mb-4">
            <div class="flex items-center gap-4 mb-3">
              <div class="text-center">
                <div class="text-xs text-gray-500 mb-1">현재 코드</div>
                <div class="font-mono text-lg font-bold text-gray-700 bg-white px-3 py-1 rounded border">
                  {{ batchUpdatePending.item.code }}
                </div>
              </div>
              <svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
              <div class="text-center">
                <div class="text-xs text-gray-500 mb-1">변경 코드</div>
                <div class="font-mono text-lg font-bold text-blue-600 bg-white px-3 py-1 rounded border border-blue-200">
                  {{ batchUpdatePending.newCode }}
                </div>
              </div>
            </div>

            <!-- 영향받는 부품 정보 -->
            <div v-if="batchUpdatePending.isLoading" class="text-center py-4">
              <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
              <p class="text-sm text-gray-500 mt-2">영향받는 부품 조회 중...</p>
            </div>
            <div v-else-if="batchUpdatePending.affectedParts">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-sm font-medium text-gray-700">영향받는 부품:</span>
                <span class="px-2 py-0.5 bg-orange-100 text-orange-800 rounded-full text-sm font-semibold">
                  {{ batchUpdatePending.affectedParts.affected_count }}건
                </span>
              </div>

              <!-- 부품 목록 (최대 5개만 표시) -->
              <div v-if="batchUpdatePending.affectedParts.parts.length > 0" class="max-h-40 overflow-y-auto">
                <table class="w-full text-xs">
                  <thead class="bg-gray-100 sticky top-0">
                    <tr>
                      <th class="px-2 py-1 text-left">품번</th>
                      <th class="px-2 py-1 text-left">부품명</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-100">
                    <tr v-for="part in batchUpdatePending.affectedParts.parts.slice(0, 5)" :key="part.id">
                      <td class="px-2 py-1 font-mono">{{ part.part_number_display || part.part_number }}</td>
                      <td class="px-2 py-1">{{ part.part_name }}</td>
                    </tr>
                  </tbody>
                </table>
                <p v-if="batchUpdatePending.affectedParts.parts.length > 5" class="text-xs text-gray-500 mt-1 text-center">
                  ... 외 {{ batchUpdatePending.affectedParts.parts.length - 5 }}건 더 있음
                </p>
              </div>
            </div>
          </div>

          <!-- 안내 메시지 -->
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 text-sm">
            <p class="text-blue-800">
              <strong>일괄 적용:</strong> 코드 변경과 함께 모든 관련 품번도 새 코드로 업데이트합니다.<br>
              <strong>코드만 변경:</strong> 코드만 변경하고 기존 품번은 그대로 유지합니다.
            </p>
          </div>

          <!-- 버튼 -->
          <div class="flex justify-end gap-3">
            <button
              @click="cancelBatchUpdate"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              취소
            </button>
            <button
              @click="handleCodeOnlyUpdate"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200"
            >
              코드만 변경
            </button>
            <button
              @click="handleBatchUpdate"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              일괄 적용
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
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
  procurementTypeApi,
  supplierTypeApi,
  unitApi,
  codeUpdateApi,
  PART_NUMBER_AFFECTING_TYPES,
  type CodeMaster,
  type CodeMasterCreate,
  type AffectedPartsResponse,
} from '@/api/codeMaster'
import CodeMasterModal from '@/views/production/components/CodeMasterModal.vue'

// 품번 구조 가이드 표시 여부
const showPartNumberGuide = ref(false)

// 탭 설정 - 두 그룹으로 분리
// 1. 품번 구성요소: 품번에 직접 포함되는 코드 (v0.20.0: 레벨 추가)
const partNumberTabsConfig = [
  { id: 'productLine', name: '대분류(제품라인)', api: productLineApi },
  { id: 'partGroup', name: '소분류(품목군)', api: partGroupApi },
  { id: 'material', name: '재질', api: materialApi },
  { id: 'treatment', name: '후처리', api: treatmentApi },
  { id: 'level', name: '레벨', api: levelApi },
]

// 2. 관리 데이터: 품번에 포함되지 않는 분류/관리 속성
const managementTabsConfig = [
  { id: 'developmentType', name: '개발구분', api: developmentTypeApi },
  { id: 'partType', name: '부품유형', api: partTypeApi },
  { id: 'drawingType', name: '도면여부', api: drawingTypeApi },
  { id: 'procurement', name: '조달구분', api: procurementTypeApi },
  { id: 'supplierType', name: '공급업체 구분', api: supplierTypeApi },
  { id: 'unit', name: '단위', api: unitApi },
]

// 탭에 데이터 개수를 포함한 computed
const partNumberTabs = computed(() =>
  partNumberTabsConfig.map(tab => ({
    ...tab,
    count: dataStore.value[tab.id]?.length || 0
  }))
)

const managementTabs = computed(() =>
  managementTabsConfig.map(tab => ({
    ...tab,
    count: dataStore.value[tab.id]?.length || 0
  }))
)

// 전체 탭 (API 조회용)
const allTabsConfig = [...partNumberTabsConfig, ...managementTabsConfig]

const activeTab = ref('productLine')

// 데이터 상태 - 각 탭별로 저장
const dataStore = ref<Record<string, CodeMaster[]>>({
  productLine: [],
  partGroup: [],
  developmentType: [],
  partType: [],
  drawingType: [],
  material: [],
  treatment: [],
  level: [],
  procurement: [],
  supplierType: [],
  unit: [],
})

const loading = ref(false)
const error = ref('')

// 모달 상태
const showModal = ref(false)
const isEditMode = ref(false)
const selectedItem = ref<CodeMaster | null>(null)

// 인라인 편집 상태
const editingId = ref<number | null>(null)
const editingField = ref<string>('')
const editingValue = ref<string>('')
const inlineInput = ref<HTMLInputElement | null>(null)

// 드래그 앤 드롭 상태
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

// 토스트 알림
const toast = ref({
  show: false,
  message: '',
  type: 'success' as 'success' | 'error'
})

// 일괄 업데이트 다이얼로그 상태
const showBatchUpdateDialog = ref(false)
const batchUpdatePending = ref<{
  item: CodeMaster
  newCode: string
  affectedParts: AffectedPartsResponse | null
  isLoading: boolean
}>({
  item: {} as CodeMaster,
  newCode: '',
  affectedParts: null,
  isLoading: false
})

const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  toast.value = { show: true, message, type }
  setTimeout(() => {
    toast.value.show = false
  }, 3000)
}

// Computed
const currentTabName = computed(() => {
  return allTabsConfig.find(t => t.id === activeTab.value)?.name || ''
})

const currentData = computed(() => {
  return dataStore.value[activeTab.value] || []
})

const currentApi = computed(() => {
  return allTabsConfig.find(t => t.id === activeTab.value)?.api
})

// 데이터 로드
const loadData = async (tabId: string) => {
  const tab = allTabsConfig.find(t => t.id === tabId)
  if (!tab) return

  try {
    loading.value = true
    error.value = ''
    console.log(`Loading data for ${tabId}...`)
    const response = await tab.api.getAll()
    console.log(`Loaded ${tabId}:`, response.data)
    dataStore.value[tabId] = response.data
  } catch (err: any) {
    console.error(`Error loading ${tabId}:`, err)
    error.value = err.response?.data?.detail || err.message || '데이터를 불러오는데 실패했습니다'
    showToast('데이터 로드 실패', 'error')
  } finally {
    loading.value = false
  }
}

// 탭 변경
const changeTab = (tabId: string) => {
  activeTab.value = tabId
  // 탭 변경 시 항상 최신 데이터 로드
  loadData(tabId)
}

// 모달 열기 (추가)
const openAddModal = () => {
  isEditMode.value = false
  selectedItem.value = null
  showModal.value = true
}

// 모달 열기 (수정)
const openEditModal = (item: CodeMaster) => {
  isEditMode.value = true
  selectedItem.value = item
  showModal.value = true
}

// 모달 닫기
const closeModal = () => {
  showModal.value = false
  selectedItem.value = null
}

// 폼 제출 처리
const handleSubmit = async (data: CodeMasterCreate) => {
  try {
    const api = currentApi.value
    if (!api) return

    if (isEditMode.value && selectedItem.value) {
      // 코드가 변경되었고 품번에 영향을 주는 코드 타입인 경우
      if (
        data.code !== selectedItem.value.code &&
        PART_NUMBER_AFFECTING_TYPES.includes(activeTab.value)
      ) {
        // 영향받는 부품 확인
        const response = await codeUpdateApi.getAffectedParts(activeTab.value, selectedItem.value.id)

        if (response.data.affected_count > 0) {
          // 다이얼로그로 처리하기 위해 상태 저장
          batchUpdatePending.value = {
            item: selectedItem.value,
            newCode: data.code,
            affectedParts: response.data,
            isLoading: false
          }
          // 모달 닫고 일괄 업데이트 다이얼로그 표시
          closeModal()
          showBatchUpdateDialog.value = true
          return
        }
      }

      await api.update(selectedItem.value.id, data)
      showToast('수정되었습니다')
    } else {
      await api.create(data)
      showToast('추가되었습니다')
    }

    closeModal()
    await loadData(activeTab.value)
  } catch (err: any) {
    showToast(err.response?.data?.detail || '처리 실패', 'error')
  }
}

// 삭제
const deleteItem = async (item: CodeMaster) => {
  if (!confirm(`"${item.name_ko}"를 삭제하시겠습니까?`)) {
    return
  }

  try {
    const api = currentApi.value
    if (!api) return

    await api.delete(item.id)
    showToast('삭제되었습니다')
    await loadData(activeTab.value)
  } catch (err: any) {
    showToast(err.response?.data?.detail || '삭제 실패', 'error')
  }
}

// ==================== 인라인 편집 ====================

// 인라인 편집 시작
const startInlineEdit = (item: CodeMaster, field: string, value: string) => {
  editingId.value = item.id
  editingField.value = field
  editingValue.value = value
  nextTick(() => {
    inlineInput.value?.focus()
    inlineInput.value?.select()
  })
}

// 인라인 편집 저장
const saveInlineEdit = async (item: CodeMaster) => {
  if (editingId.value !== item.id) return

  const field = editingField.value
  const newValue = editingValue.value.trim()

  // 원본 값 가져오기
  let originalValue = ''
  if (field === 'code') {
    originalValue = item.code
  } else if (field === 'name_ko') {
    originalValue = item.name_ko
  } else if (field === 'name_en') {
    originalValue = item.name_en || ''
  }

  // 값이 변경되지 않았으면 취소
  if (newValue === originalValue) {
    cancelInlineEdit()
    return
  }

  // 필수값 검증
  if (field === 'code' && !newValue) {
    showToast('코드는 필수입니다', 'error')
    return
  }
  if (field === 'name_ko' && !newValue) {
    showToast('한글명은 필수입니다', 'error')
    return
  }

  // 코드 변경이고 품번에 영향을 주는 코드 타입인 경우
  if (field === 'code' && PART_NUMBER_AFFECTING_TYPES.includes(activeTab.value)) {
    await checkAffectedPartsAndShowDialog(item, newValue)
    return
  }

  // 일반적인 업데이트 처리
  await performInlineUpdate(item, field, newValue)
}

// 영향받는 부품 확인 및 다이얼로그 표시
const checkAffectedPartsAndShowDialog = async (item: CodeMaster, newCode: string) => {
  try {
    batchUpdatePending.value = {
      item,
      newCode,
      affectedParts: null,
      isLoading: true
    }

    // 영향받는 부품 조회
    const response = await codeUpdateApi.getAffectedParts(activeTab.value, item.id)
    batchUpdatePending.value.affectedParts = response.data
    batchUpdatePending.value.isLoading = false

    // 영향받는 부품이 있으면 다이얼로그 표시, 없으면 바로 업데이트
    if (response.data.affected_count > 0) {
      showBatchUpdateDialog.value = true
    } else {
      // 영향받는 부품이 없으면 바로 코드만 업데이트
      await performInlineUpdate(item, 'code', newCode)
    }
  } catch (err: any) {
    console.error('영향받는 부품 조회 실패:', err)
    // 조회 실패해도 코드 업데이트는 진행
    await performInlineUpdate(item, 'code', newCode)
  }
}

// 실제 인라인 업데이트 수행
const performInlineUpdate = async (item: CodeMaster, field: string, newValue: string) => {
  try {
    const api = currentApi.value
    if (!api) return

    const updateData: Partial<CodeMasterCreate> = {
      code: field === 'code' ? newValue : item.code,
      name_ko: field === 'name_ko' ? newValue : item.name_ko,
      name_en: field === 'name_en' ? newValue : item.name_en,
      description: item.description,
      is_active: item.is_active
    }

    await api.update(item.id, updateData as CodeMasterCreate)

    // 로컬 데이터 업데이트
    if (field === 'code') {
      item.code = newValue
    } else if (field === 'name_ko') {
      item.name_ko = newValue
    } else if (field === 'name_en') {
      item.name_en = newValue
    }

    showToast('수정되었습니다')
  } catch (err: any) {
    showToast(err.response?.data?.detail || '수정 실패', 'error')
  } finally {
    cancelInlineEdit()
  }
}

// 일괄 업데이트 다이얼로그 - 코드만 변경 (품번 유지)
const handleCodeOnlyUpdate = async () => {
  const { item, newCode } = batchUpdatePending.value

  try {
    const api = currentApi.value
    if (!api) return

    // 코드만 업데이트
    await api.update(item.id, {
      code: newCode,
      name_ko: item.name_ko,
      name_en: item.name_en,
      description: item.description,
      is_active: item.is_active
    } as CodeMasterCreate)

    showToast('코드가 수정되었습니다 (품번은 유지)')
    await loadData(activeTab.value)
  } catch (err: any) {
    showToast(err.response?.data?.detail || '수정 실패', 'error')
  } finally {
    showBatchUpdateDialog.value = false
    cancelInlineEdit()
  }
}

// 일괄 업데이트 다이얼로그 - 코드와 품번 모두 변경
const handleBatchUpdate = async () => {
  const { item, newCode } = batchUpdatePending.value

  try {
    const api = currentApi.value
    if (!api) return

    // 1. 먼저 코드 업데이트
    await api.update(item.id, {
      code: newCode,
      name_ko: item.name_ko,
      name_en: item.name_en,
      description: item.description,
      is_active: item.is_active
    } as CodeMasterCreate)

    // 2. 품번 일괄 업데이트
    const response = await codeUpdateApi.batchUpdatePartNumbers(activeTab.value, item.id, newCode)

    showToast(`코드 수정 및 ${response.data.updated_count}건의 품번이 일괄 변경되었습니다`)
    await loadData(activeTab.value)
  } catch (err: any) {
    showToast(err.response?.data?.detail || '일괄 업데이트 실패', 'error')
  } finally {
    showBatchUpdateDialog.value = false
    cancelInlineEdit()
  }
}

// 일괄 업데이트 다이얼로그 취소
const cancelBatchUpdate = () => {
  showBatchUpdateDialog.value = false
  cancelInlineEdit()
}

// 인라인 편집 취소
const cancelInlineEdit = () => {
  editingId.value = null
  editingField.value = ''
  editingValue.value = ''
}

// 상태 토글
const toggleActive = async (item: CodeMaster) => {
  try {
    const api = currentApi.value
    if (!api) return

    const updateData: CodeMasterCreate = {
      code: item.code,
      name_ko: item.name_ko,
      name_en: item.name_en,
      description: item.description,
      is_active: !item.is_active
    }

    await api.update(item.id, updateData)
    item.is_active = !item.is_active
    showToast(item.is_active ? '사용으로 변경되었습니다' : '미사용으로 변경되었습니다')
  } catch (err: any) {
    showToast(err.response?.data?.detail || '상태 변경 실패', 'error')
  }
}

// ==================== 드래그 앤 드롭 ====================

// 드래그 시작
const onDragStart = (event: DragEvent, index: number) => {
  dragIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

// 드래그 오버
const onDragOver = (event: DragEvent, index: number) => {
  dragOverIndex.value = index
}

// 드롭
const onDrop = async (event: DragEvent, dropIndex: number) => {
  const currentDragIndex = dragIndex.value
  if (currentDragIndex === null || currentDragIndex === dropIndex) {
    dragOverIndex.value = null
    return
  }

  const items = [...currentData.value]
  const draggedItem = items.splice(currentDragIndex, 1)[0]
  if (!draggedItem) {
    dragOverIndex.value = null
    return
  }
  items.splice(dropIndex, 0, draggedItem)

  // UI 업데이트
  dataStore.value[activeTab.value] = items
  dragOverIndex.value = null

  // 서버에 순서 업데이트 (sort_order 필드가 있는 경우)
  try {
    const api = currentApi.value
    if (!api) return

    // 각 아이템의 sort_order 업데이트
    for (let i = 0; i < items.length; i++) {
      const item = items[i]
      if (item) {
        await api.update(item.id, {
          code: item.code,
          name_ko: item.name_ko,
          name_en: item.name_en,
          description: item.description,
          is_active: item.is_active,
          sort_order: i
        } as CodeMasterCreate)
      }
    }
    showToast('순서가 변경되었습니다')
  } catch (err: any) {
    console.error('순서 업데이트 실패:', err)
    // 실패 시 원래 데이터 다시 로드
    await loadData(activeTab.value)
  }
}

// 드래그 종료
const onDragEnd = () => {
  dragIndex.value = null
  dragOverIndex.value = null
}

// 모든 탭 데이터 로드 (개수 표시용)
const loadAllTabsData = async () => {
  const promises = allTabsConfig.map(tab => loadDataSilent(tab.id))
  await Promise.all(promises)
}

// 데이터 로드 (에러 메시지 없이 - 백그라운드 로드용)
const loadDataSilent = async (tabId: string) => {
  const tab = allTabsConfig.find(t => t.id === tabId)
  if (!tab) return

  try {
    const response = await tab.api.getAll()
    dataStore.value[tabId] = response.data
  } catch (err: any) {
    console.error(`Error loading ${tabId}:`, err)
    dataStore.value[tabId] = []
  }
}

// 마운트 시 모든 탭 데이터 로드
onMounted(async () => {
  // 현재 활성 탭 먼저 로드 (로딩 표시)
  await loadData(activeTab.value)
  // 나머지 탭들은 백그라운드에서 로드 (개수 표시용)
  loadAllTabsData()
})
</script>
