<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">부품 마스터 관리</h1>

    <!-- 품번 구조 가이드 (드롭다운) -->
    <div class="bg-blue-50 border border-blue-200 rounded-lg mb-6">
      <button
        @click="showPartNumberGuide = !showPartNumberGuide"
        class="w-full px-4 py-3 flex items-center justify-between text-left"
      >
        <div class="flex items-center space-x-2">
          <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="font-medium text-blue-700">품번 자동생성 구조 안내</span>
        </div>
        <svg
          class="w-5 h-5 text-blue-500 transition-transform"
          :class="{ 'rotate-180': showPartNumberGuide }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div v-show="showPartNumberGuide" class="px-4 pb-4">
        <div class="bg-white rounded-lg p-4 border border-blue-100">
          <div class="text-center mb-3">
            <code class="text-lg font-mono bg-gray-100 px-3 py-1 rounded">
              <span class="text-blue-600">HB01</span>-<span class="text-green-600">DCP</span>-<span class="text-purple-600">00001</span>-<span class="text-orange-600">A6</span>-<span class="text-red-600">NK</span>
            </code>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 text-sm">
            <div class="text-center">
              <div class="font-semibold text-blue-600">대분류(4)</div>
              <div class="text-gray-500">제품라인</div>
            </div>
            <div class="text-center">
              <div class="font-semibold text-green-600">소분류(3)</div>
              <div class="text-gray-500">품목군</div>
            </div>
            <div class="text-center">
              <div class="font-semibold text-purple-600">품목코드(5)</div>
              <div class="text-gray-500">자동채번</div>
            </div>
            <div class="text-center">
              <div class="font-semibold text-orange-600">재질(2)</div>
              <div class="text-gray-500">선택</div>
            </div>
            <div class="text-center">
              <div class="font-semibold text-red-600">후처리(2)</div>
              <div class="text-gray-500">선택</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 상세 필터 패널 (v0.12.0) -->
    <PartFilterPanel
      ref="filterPanelRef"
      mode="parts"
      v-model="filterValues"
      @search="handleFilterSearch"
      @reset="handleFilterReset"
    />

    <!-- 고급 필터 패널 (미입력 데이터 검색) -->
    <div class="mb-6">
      <AdvancedFilterPanel
        v-model="advancedFilterValues"
        @search="handleAdvancedFilterSearch"
        @reset="handleAdvancedFilterReset"
      />
    </div>

    <!-- 테이블 섹션 -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-semibold">부품 목록 <span class="text-sm text-gray-500 font-normal">(총 {{ totalParts }}건)</span></h2>
        <div class="flex space-x-2">
          <button
            @click="generateMissingUids"
            :disabled="isGeneratingUids"
            class="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
            title="UID가 없는 기존 부품에 UID를 일괄 생성합니다"
          >
            <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
            </svg>
            {{ isGeneratingUids ? 'UID 생성 중...' : 'UID 일괄생성' }}
          </button>
          <button
            @click="exportExcel"
            class="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded flex items-center"
          >
            <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            엑셀 다운로드
          </button>
          <button
            @click="openExcelUploadModal"
            class="bg-teal-500 hover:bg-teal-600 text-white px-4 py-2 rounded flex items-center"
          >
            <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            엑셀 업로드
          </button>
          <button
            @click="openAddModal"
            class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded flex items-center"
          >
            <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            부품 추가
          </button>
        </div>
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
        <table class="min-w-full divide-y divide-gray-200 table-fixed" style="table-layout: fixed;">
          <thead class="bg-gray-50">
            <tr>
              <!-- 품번 열 -->
              <th
                @click="sortBy('part_number')"
                class="text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 relative select-none"
                :style="{ width: columnWidths.part_number + 'px', minWidth: '50px' }"
              >
                <div class="px-4 py-3 flex items-center space-x-1">
                  <span>품번</span>
                  <SortIcon :active="sortColumn === 'part_number'" :desc="sortDesc" />
                </div>
                <div
                  class="absolute right-0 top-0 h-full w-2 cursor-col-resize hover:bg-blue-400 bg-gray-200"
                  @mousedown.stop="startResize($event, 'part_number')"
                ></div>
              </th>
              <!-- 부품명 열 -->
              <th
                @click="sortBy('part_name')"
                class="text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 relative select-none"
                :style="{ width: columnWidths.part_name + 'px', minWidth: '50px' }"
              >
                <div class="px-4 py-3 flex items-center space-x-1">
                  <span>부품명</span>
                  <SortIcon :active="sortColumn === 'part_name'" :desc="sortDesc" />
                </div>
                <div
                  class="absolute right-0 top-0 h-full w-2 cursor-col-resize hover:bg-blue-400 bg-gray-200"
                  @mousedown.stop="startResize($event, 'part_name')"
                ></div>
              </th>
              <!-- 레벨 열 -->
              <th
                class="text-left text-xs font-medium text-gray-500 uppercase relative select-none"
                :style="{ width: columnWidths.level + 'px', minWidth: '50px' }"
              >
                <div class="px-4 py-3">레벨</div>
                <div
                  class="absolute right-0 top-0 h-full w-2 cursor-col-resize hover:bg-blue-400 bg-gray-200"
                  @mousedown="startResize($event, 'level')"
                ></div>
              </th>
              <!-- 설명 열 -->
              <th
                class="text-left text-xs font-medium text-gray-500 uppercase relative select-none"
                :style="{ width: columnWidths.description + 'px', minWidth: '50px' }"
              >
                <div class="px-4 py-3">설명</div>
                <div
                  class="absolute right-0 top-0 h-full w-2 cursor-col-resize hover:bg-blue-400 bg-gray-200"
                  @mousedown="startResize($event, 'description')"
                ></div>
              </th>
              <!-- 상태 열 -->
              <th
                @click="sortBy('status')"
                class="text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 relative select-none"
                :style="{ width: columnWidths.status + 'px', minWidth: '50px' }"
              >
                <div class="px-4 py-3 flex items-center space-x-1">
                  <span>상태</span>
                  <SortIcon :active="sortColumn === 'status'" :desc="sortDesc" />
                </div>
                <div
                  class="absolute right-0 top-0 h-full w-2 cursor-col-resize hover:bg-blue-400 bg-gray-200"
                  @mousedown.stop="startResize($event, 'status')"
                ></div>
              </th>
              <!-- 등록일 열 -->
              <th
                @click="sortBy('created_at')"
                class="text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 relative select-none"
                :style="{ width: columnWidths.created_at + 'px', minWidth: '50px' }"
              >
                <div class="px-4 py-3 flex items-center space-x-1">
                  <span>등록일</span>
                  <SortIcon :active="sortColumn === 'created_at'" :desc="sortDesc" />
                </div>
                <div
                  class="absolute right-0 top-0 h-full w-2 cursor-col-resize hover:bg-blue-400 bg-gray-200"
                  @mousedown.stop="startResize($event, 'created_at')"
                ></div>
              </th>
              <!-- 작업 열 -->
              <th
                class="text-left text-xs font-medium text-gray-500 uppercase select-none"
                :style="{ width: columnWidths.actions + 'px', minWidth: '50px' }"
              >
                <div class="px-4 py-3">작업</div>
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="part in parts" :key="part.id" class="hover:bg-gray-50">
              <td class="px-4 py-4 text-sm font-medium break-all" :style="{ width: columnWidths.part_number + 'px', minWidth: columnWidths.part_number + 'px' }" :title="getDisplayPartNumber(part)">
                <button
                  @click="viewDetail(part)"
                  class="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                >
                  {{ getDisplayPartNumber(part) }}
                </button>
                <span v-if="(part as any).is_protected"
                  class="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-red-100 text-red-700 whitespace-nowrap align-middle"
                  :title="`전속: ${(part as any).protected_customer?.partner_name || '지정 고객'}`">🔒 전속</span>
              </td>
              <td class="px-4 py-4 text-sm text-gray-900 break-words" :style="{ width: columnWidths.part_name + 'px', minWidth: columnWidths.part_name + 'px' }" :title="part.part_name">
                {{ part.part_name }}
              </td>
              <td class="px-4 py-4 whitespace-nowrap text-sm text-center" :style="{ width: columnWidths.level + 'px' }">
                <span v-if="part.level" :class="['px-2 py-0.5 rounded text-xs font-medium', getLevelColorClass(part.level.code)]">
                  {{ part.level.code }}
                </span>
                <span v-else class="text-gray-400">-</span>
              </td>
              <td class="px-4 py-4 text-sm text-gray-500 break-words" :style="{ width: columnWidths.description + 'px', minWidth: columnWidths.description + 'px' }" :title="part.description || ''">
                {{ part.description || '-' }}
              </td>
              <td class="px-4 py-4 whitespace-nowrap" :style="{ width: columnWidths.status + 'px' }">
                <span
                  :class="[
                    'px-2 inline-flex text-xs leading-5 font-semibold rounded-full',
                    part.status === 'ACTIVE'
                      ? 'bg-green-100 text-green-800'
                      : part.status === 'INACTIVE'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800',
                  ]"
                >
                  {{
                    part.status === 'ACTIVE'
                      ? '사용중'
                      : part.status === 'INACTIVE'
                        ? '미사용'
                        : '단종'
                  }}
                </span>
              </td>
              <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500" :style="{ width: columnWidths.created_at + 'px' }">
                {{ formatDate(part.created_at) }}
              </td>
              <td class="px-4 py-4 whitespace-nowrap text-sm font-medium" :style="{ width: columnWidths.actions + 'px' }">
                <button @click="viewDetail(part)" class="text-blue-600 hover:text-blue-900 mr-2">
                  상세
                </button>
                <button @click="openEditModal(part)" class="text-blue-600 hover:text-blue-900 mr-2">
                  수정
                </button>
                <button @click="duplicatePart(part)" class="text-purple-600 hover:text-purple-900 mr-2" title="부품 복제">
                  복제
                </button>
                <button @click="deletePart(part)" class="text-red-600 hover:text-red-900">
                  삭제
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="parts.length === 0" class="text-center py-8 text-gray-500">
          부품 데이터가 없습니다
        </div>

        <!-- 페이지네이션 -->
        <Pagination
          v-if="totalCount > 0"
          :total="totalCount"
          :page-size="pageSize"
          :current-page="currentPage"
          @update:current-page="handlePageChange"
          @update:page-size="handlePageSizeChange"
        />
      </div>
    </div>

    <!-- 부품 등록/수정 모달 -->
    <PartFormModal
      :show="showModal"
      :is-edit="isEditMode"
      :initial-data="selectedPart"
      @close="closeModal"
      @submit="handleSubmit"
    />

    <!-- 부품 상세 모달 -->
    <PartDetailModal
      :show="showDetailModal"
      :part-id="detailPartId"
      @close="closeDetailModal"
      @edit="handleEditFromDetail"
      @updated="loadParts"
    />

    <!-- 엑셀 업로드 모달 -->
    <div v-if="showExcelUploadModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
        <div class="px-6 py-4 border-b flex justify-between items-center">
          <h3 class="text-lg font-semibold">엑셀 파일 업로드</h3>
          <button @click="closeExcelUploadModal" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="p-6">
          <!-- 파일 선택 영역 -->
          <div
            class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-teal-500 transition-colors"
            :class="{ 'border-teal-500 bg-teal-50': excelFile }"
            @dragover.prevent
            @drop.prevent="handleFileDrop"
          >
            <input
              type="file"
              ref="fileInputRef"
              accept=".xlsx,.xls"
              class="hidden"
              @change="handleFileSelect"
            />
            <div v-if="!excelFile">
              <svg class="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p class="text-gray-600 mb-2">파일을 드래그하거나 클릭하여 선택하세요</p>
              <p class="text-sm text-gray-400">지원 형식: .xlsx, .xls</p>
              <button
                @click="fileInputRef?.click()"
                class="mt-4 px-4 py-2 bg-teal-500 text-white rounded hover:bg-teal-600"
              >
                파일 선택
              </button>
            </div>
            <div v-else>
              <svg class="w-12 h-12 mx-auto text-teal-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p class="text-teal-700 font-medium">{{ excelFile.name }}</p>
              <p class="text-sm text-gray-500 mt-1">{{ formatFileSize(excelFile.size) }}</p>
              <button
                @click="excelFile = null"
                class="mt-4 px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
              >
                다른 파일 선택
              </button>
            </div>
          </div>

          <!-- 엑셀 형식 안내 (v0.22.0) -->
          <div class="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 class="font-medium text-blue-700 mb-2">엑셀 파일 형식</h4>
            <p class="text-sm text-blue-600 mb-2">다음 컬럼 순서로 작성해주세요:</p>
            <div class="text-xs text-blue-600 font-mono bg-white p-2 rounded overflow-x-auto">
              No | 전체품번 | 품명 | 설명 | 코드1(대분류) | 코드2(소분류) | 코드3 | 코드4 | 코드5(재질) | 코드6(후처리) | 레벨
            </div>
            <div class="mt-2 text-xs text-blue-500 space-y-1">
              <p>* 코드3+코드4 = 품목코드 (예: FSO + 01 = FSO01)</p>
              <p>* 코드1~코드6 중 하나라도 비어있으면 <span class="font-semibold">직접입력</span> 형태로 저장됩니다 (레벨만 매핑)</p>
            </div>
          </div>

          <!-- 업로드 결과 -->
          <div v-if="excelUploadResult" class="mt-4">
            <div class="flex items-center gap-4 mb-2">
              <span class="text-sm">총 {{ excelUploadResult.total }}건</span>
              <span class="text-sm text-green-600">성공 {{ excelUploadResult.success_count }}건</span>
              <span v-if="excelUploadResult.price_updated_count" class="text-sm text-blue-600">가격수정 {{ excelUploadResult.price_updated_count }}건</span>
              <span class="text-sm text-red-600">실패 {{ excelUploadResult.failed_count }}건</span>
            </div>
            <div class="max-h-48 overflow-y-auto border rounded">
              <table class="w-full text-sm">
                <thead class="bg-gray-50 sticky top-0">
                  <tr>
                    <th class="px-2 py-1 text-left">행</th>
                    <th class="px-2 py-1 text-left">품번</th>
                    <th class="px-2 py-1 text-left">상태</th>
                    <th class="px-2 py-1 text-left">메시지</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="result in excelUploadResult.results" :key="result.row" class="border-t">
                    <td class="px-2 py-1">{{ result.row }}</td>
                    <td class="px-2 py-1 font-mono text-xs">{{ result.part_number }}</td>
                    <td class="px-2 py-1">
                      <span
                        class="px-2 py-0.5 rounded text-xs"
                        :class="{
                          'bg-green-100 text-green-700': result.status === 'success',
                          'bg-blue-100 text-blue-700': result.status === 'price_updated',
                          'bg-red-100 text-red-700': result.status === 'failed',
                          'bg-yellow-100 text-yellow-700': result.status === 'skipped'
                        }"
                      >
                        {{ result.status === 'success' ? '성공' : result.status === 'price_updated' ? '가격수정' : result.status === 'skipped' ? '건너뜀' : '실패' }}
                      </span>
                    </td>
                    <td class="px-2 py-1 text-gray-600">{{ result.message }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="px-6 py-4 border-t bg-gray-50 flex justify-end gap-2">
          <button
            @click="closeExcelUploadModal"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            닫기
          </button>
          <button
            @click="uploadExcel"
            :disabled="!excelFile || isUploadingExcel"
            class="px-4 py-2 bg-teal-500 text-white rounded hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ isUploadingExcel ? '업로드 중...' : '업로드' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 토스트 알림 -->
    <div
      v-if="toast.show"
      class="fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg transition-all"
      :class="toast.type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'"
    >
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { partApi, type PartListItem, type PartCreate, type PartSearchParams, type Part } from '@/api/parts'
import { downloadAuthedUrl } from '@/utils/download'
import PartFormModal from '@/views/production/components/PartFormModal.vue'
import PartDetailModal from '@/views/production/components/PartDetailModal.vue'
import PartFilterPanel, { type FilterValues } from '@/views/production/components/PartFilterPanel.vue'
import AdvancedFilterPanel from '@/views/production/components/AdvancedFilterPanel.vue'
import Pagination from '@/components/Pagination.vue'
import SortIcon from '@/components/SortIcon.vue'
import { handleApiError } from '@/utils/errorHandler'

// 상태
const loading = ref(false)
const error = ref('')
const parts = ref<PartListItem[]>([])
const totalCount = ref(0)
const totalParts = ref(0)
const isGeneratingUids = ref(false)

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

// 엑셀 업로드 상태
const showExcelUploadModal = ref(false)
const excelFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const isUploadingExcel = ref(false)
const excelUploadResult = ref<{
  total: number
  success_count: number
  price_updated_count?: number
  failed_count: number
  results: Array<{
    row: number
    part_number: string
    part_id?: number
    status: 'success' | 'failed' | 'skipped' | 'price_updated'
    message: string
    parsed_errors?: string[]
  }>
} | null>(null)

// 컬럼 너비 (리사이즈 가능)
const columnWidths = ref({
  part_number: 200,
  part_name: 180,
  level: 80,
  description: 200,
  status: 80,
  created_at: 100,
  actions: 180,
})

// 컬럼 리사이즈 상태
let resizingColumn = ''
let startX = 0
let startWidth = 0

const startResize = (event: MouseEvent, column: string) => {
  resizingColumn = column
  startX = event.clientX
  startWidth = columnWidths.value[column as keyof typeof columnWidths.value]
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  event.preventDefault()
}

const onResize = (event: MouseEvent) => {
  if (!resizingColumn) return
  const diff = event.clientX - startX
  const newWidth = Math.max(50, startWidth + diff)
  columnWidths.value[resizingColumn as keyof typeof columnWidths.value] = newWidth
}

const stopResize = () => {
  resizingColumn = ''
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}

// 품번 구조 가이드 표시 여부
const showPartNumberGuide = ref(false)

// 페이지네이션
const currentPage = ref(1)
const pageSize = ref(20)

// 정렬
const sortColumn = ref('created_at')
const sortDesc = ref(true)

// v0.12.0: 필터 패널 참조 및 필터 값
const filterPanelRef = ref<InstanceType<typeof PartFilterPanel> | null>(null)
const filterValues = ref<FilterValues>({})

// 현재 적용 중인 검색 필터
const currentFilters = ref<FilterValues>({})

// 고급 필터 (미입력 데이터 검색)
const advancedFilterValues = ref<string[]>([])

// 등록/수정 모달 상태
const showModal = ref(false)
const isEditMode = ref(false)
const selectedPart = ref<PartCreate | null>(null)

// 상세 모달 상태
const showDetailModal = ref(false)
const detailPartId = ref<number | null>(null)

// 토스트 알림
const toast = ref({
  show: false,
  message: '',
  type: 'success' as 'success' | 'error',
})

const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  toast.value = { show: true, message, type }
  setTimeout(() => {
    toast.value.show = false
  }, 3000)
}

// 품번 표시 (part_number_display가 없으면 part_number에서 하이픈 추가)
const getDisplayPartNumber = (part: PartListItem) => {
  if (part.part_number_display) {
    return part.part_number_display
  }
  // part_number에서 하이픈 추가: HB01DCP00001A6NK -> HB01-DCP-00001-A6-NK
  const pn = part.part_number
  if (pn && pn.length >= 16) {
    return `${pn.slice(0, 4)}-${pn.slice(4, 7)}-${pn.slice(7, 12)}-${pn.slice(12, 14)}-${pn.slice(14)}`
  }
  return part.part_number
}

// v0.12.0: 필터 검색 핸들러
const handleFilterSearch = (filters: FilterValues) => {
  currentFilters.value = { ...filters }
  currentPage.value = 1
  loadParts()
}

// v0.12.0: 필터 초기화 핸들러
const handleFilterReset = () => {
  currentFilters.value = {}
  filterValues.value = {}
  currentPage.value = 1
  loadParts()
}

// 고급 필터 검색 핸들러
const handleAdvancedFilterSearch = (missingFields: string[]) => {
  advancedFilterValues.value = [...missingFields]
  currentPage.value = 1
  loadParts()
}

// 고급 필터 초기화 핸들러
const handleAdvancedFilterReset = () => {
  advancedFilterValues.value = []
  currentPage.value = 1
  loadParts()
}

// 부품 목록 로드
const loadParts = async () => {
  try {
    loading.value = true
    error.value = ''

    // level_ids 배열을 콤마 구분 문자열로 변환
    const levelIdsParam = currentFilters.value.level_ids && currentFilters.value.level_ids.length > 0
      ? currentFilters.value.level_ids.join(',')
      : undefined

    // development_type_ids 배열을 콤마 구분 문자열로 변환
    const devTypeIdsParam = currentFilters.value.development_type_ids && currentFilters.value.development_type_ids.length > 0
      ? currentFilters.value.development_type_ids.join(',')
      : undefined

    // 고급 필터: missing_fields 배열을 콤마 구분 문자열로 변환
    const missingFieldsParam = advancedFilterValues.value.length > 0
      ? advancedFilterValues.value.join(',')
      : undefined

    const params: PartSearchParams = {
      keyword: currentFilters.value.keyword || undefined,
      level_ids: levelIdsParam,
      product_line_id: currentFilters.value.product_line_id,
      part_group_id: currentFilters.value.part_group_id,
      development_type_ids: devTypeIdsParam,
      material_id: currentFilters.value.material_id,
      treatment_id: currentFilters.value.treatment_id,
      drawing_type_id: currentFilters.value.drawing_type_id,
      procurement_type_id: currentFilters.value.procurement_type_id,
      unit_id: currentFilters.value.unit_id,
      status: currentFilters.value.status,
      classified: currentFilters.value.classified,
      missing_fields: missingFieldsParam,
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      order_by: sortColumn.value,
      order_desc: sortDesc.value,
    }

    const response = await partApi.getAll(params)
    parts.value = response.data.items
    totalCount.value = response.data.total
    totalParts.value = response.data.total
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    error.value = errorMessage
    showToast(errorMessage, 'error')
  } finally {
    loading.value = false
  }
}

// 정렬
const sortBy = (column: string) => {
  if (sortColumn.value === column) {
    sortDesc.value = !sortDesc.value
  } else {
    sortColumn.value = column
    sortDesc.value = true
  }
  loadParts()
}

// 페이지 변경
const handlePageChange = (page: number) => {
  currentPage.value = page
  loadParts()
}

// 페이지 크기 변경
const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  loadParts()
}

// UID 일괄 생성
const generateMissingUids = async () => {
  if (!confirm('UID가 없는 모든 부품에 대해 UID를 일괄 생성합니다.\n계속하시겠습니까?')) {
    return
  }

  try {
    isGeneratingUids.value = true
    const response = await partApi.generateMissingUids()
    const result = response.data

    if (result.total_without_uid === 0) {
      showToast('UID가 없는 부품이 없습니다.', 'success')
    } else if (result.failed_count > 0) {
      showToast(
        `총 ${result.total_without_uid}건 중 ${result.generated_count}건 생성 완료, ${result.failed_count}건 실패`,
        'error'
      )
    } else {
      showToast(`${result.generated_count}건의 부품에 UID가 생성되었습니다.`, 'success')
    }

    // 목록 새로고침
    await loadParts()
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  } finally {
    isGeneratingUids.value = false
  }
}

// 엑셀 내보내기
const exportExcel = () => {
  // level_ids, development_type_ids 배열을 문자열로 변환
  const levelIdsParam = currentFilters.value.level_ids && currentFilters.value.level_ids.length > 0
    ? currentFilters.value.level_ids.join(',')
    : undefined
  const devTypeIdsParam = currentFilters.value.development_type_ids && currentFilters.value.development_type_ids.length > 0
    ? currentFilters.value.development_type_ids.join(',')
    : undefined

  const params: PartSearchParams = {
    keyword: currentFilters.value.keyword || undefined,
    level_ids: levelIdsParam,
    product_line_id: currentFilters.value.product_line_id,
    part_group_id: currentFilters.value.part_group_id,
    development_type_ids: devTypeIdsParam,
    material_id: currentFilters.value.material_id,
    treatment_id: currentFilters.value.treatment_id,
    drawing_type_id: currentFilters.value.drawing_type_id,
    procurement_type_id: currentFilters.value.procurement_type_id,
    unit_id: currentFilters.value.unit_id,
    status: currentFilters.value.status,
    order_by: sortColumn.value,
    order_desc: sortDesc.value,
  }
  const url = partApi.getExportExcelUrl(params)
  // v0.41.0: 인증 헤더를 실어 blob 다운로드(RBAC enforce 시 401 방지)
  downloadAuthedUrl(url, 'parts.xlsx').catch((e) => console.error('엑셀 내보내기 실패', e))
}

// 모달 열기 (추가)
const openAddModal = () => {
  isEditMode.value = false
  selectedPart.value = null
  showModal.value = true
}

// 모달 열기 (수정)
const openEditModal = async (part: PartListItem) => {
  try {
    const response = await partApi.getById(part.id)
    isEditMode.value = true
    selectedPart.value = response.data as any
    showModal.value = true
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  }
}

// 부품 복제 (기존 데이터를 새 등록 폼에 pre-fill)
const duplicatePart = async (part: PartListItem) => {
  try {
    const response = await partApi.getById(part.id)
    const partData = response.data

    // 복제 데이터 생성 (id, part_uid, created_at, updated_at 등 고유값 제외)
    const duplicateData: any = {
      part_number: partData.part_number,  // 품번도 그대로 복사 (사용자가 수정해야 함)
      part_number_display: partData.part_number_display,
      part_name: partData.part_name,
      part_name_en: partData.part_name_en,
      specification: partData.specification,
      description: partData.description,
      product_line_id: partData.product_line_id,
      part_group_id: partData.part_group_id,
      material_id: partData.material_id,
      treatment_id: partData.treatment_id,
      unit_id: partData.unit_id,
      level_id: partData.level_id,
      drawing_type_id: partData.drawing_type_id,
      procurement_type_id: partData.procurement_type_id,
      development_type_id: partData.development_type_id,
      supplier_id: partData.supplier_id,
      standard_price: partData.standard_price,
      status: 'ACTIVE',  // 새 부품은 기본적으로 활성 상태
      // 파일은 복제하지 않음 (필요시 다시 업로드)
    }

    isEditMode.value = false  // 신규 등록 모드
    selectedPart.value = duplicateData
    showModal.value = true

    showToast('부품 데이터가 복제되었습니다. 품번을 수정하거나 자동생성 옵션을 사용하세요.', 'success')
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  }
}

// 상세 보기
const viewDetail = (part: PartListItem) => {
  detailPartId.value = part.id
  showDetailModal.value = true
}

// 상세 모달 닫기
const closeDetailModal = () => {
  showDetailModal.value = false
  detailPartId.value = null
}

// 상세 모달에서 수정 버튼 클릭
const handleEditFromDetail = async (part: Part) => {
  closeDetailModal()
  isEditMode.value = true
  selectedPart.value = part as any
  showModal.value = true
}

// 모달 닫기
const closeModal = () => {
  showModal.value = false
  selectedPart.value = null
}

// 폼 제출 처리
const handleSubmit = async (data: PartCreate) => {
  if (!data.part_name || data.part_name.trim().length < 2) {
    showToast('부품명은 2자 이상이어야 합니다', 'error')
    return
  }

  // 직접 입력 모드가 아닐 때만 대분류/소분류 필수 체크
  // 직접 입력 모드: part_number가 있고 product_line_id가 없는 경우
  const isDirectInputMode = data.part_number && !data.product_line_id
  if (!isDirectInputMode && (!data.product_line_id || !data.part_group_id)) {
    showToast('대분류와 소분류는 필수입니다', 'error')
    return
  }

  try {
    if (isEditMode.value && selectedPart.value) {
      await partApi.update((selectedPart.value as any).id, data)
      showToast('부품이 수정되었습니다')
    } else {
      await partApi.create(data)
      showToast('부품이 추가되었습니다')
    }
    closeModal()
    await loadParts()
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  }
}

// 삭제 (2단계: 1차 단종, 2차 완전삭제)
const deletePart = async (part: PartListItem) => {
  const displayNumber = getDisplayPartNumber(part)

  // 상태에 따라 다른 확인 메시지
  let confirmMessage: string
  if (part.status === 'OBSOLETE') {
    confirmMessage = `"${part.part_name}" (${displayNumber})를 완전히 삭제하시겠습니까?\n\n⚠️ 이 작업은 되돌릴 수 없습니다.`
  } else {
    confirmMessage = `"${part.part_name}" (${displayNumber})를 삭제하시겠습니까?\n\n※ 부품이 단종 처리됩니다. 완전 삭제는 한번 더 삭제를 눌러주세요.`
  }

  if (!confirm(confirmMessage)) {
    return
  }

  try {
    const response = await partApi.delete(part.id)
    const result = response.data

    // 결과에 따른 토스트 메시지
    if (result.action === 'obsoleted') {
      showToast(result.message || '부품이 단종 처리되었습니다. 완전 삭제를 원하시면 한번 더 삭제를 눌러주세요.')
    } else {
      showToast(result.message || '부품이 완전히 삭제되었습니다.')
    }
    await loadParts()
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  }
}

// 날짜 포맷
const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

// ==================== 엑셀 업로드 ====================

// 엑셀 업로드 모달 열기
const openExcelUploadModal = () => {
  showExcelUploadModal.value = true
  excelFile.value = null
  excelUploadResult.value = null
}

// 엑셀 업로드 모달 닫기
const closeExcelUploadModal = () => {
  showExcelUploadModal.value = false
  excelFile.value = null
  excelUploadResult.value = null
}

// 파일 선택 핸들러
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const file = target.files[0]
    if (file) {
      excelFile.value = file
      excelUploadResult.value = null
    }
  }
}

// 파일 드롭 핸들러
const handleFileDrop = (event: DragEvent) => {
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    const file = files[0]
    if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
      excelFile.value = file
      excelUploadResult.value = null
    } else if (file) {
      showToast('엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.', 'error')
    }
  }
}

// 파일 크기 포맷
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// 엑셀 업로드 실행
const uploadExcel = async () => {
  if (!excelFile.value) return

  isUploadingExcel.value = true
  try {
    const response = await partApi.uploadExcel(excelFile.value)
    excelUploadResult.value = response.data

    if (response.data.success_count > 0) {
      showToast(`${response.data.success_count}건의 부품이 등록되었습니다.`)
      await loadParts()
    } else if (response.data.failed_count > 0) {
      showToast(`업로드 실패: ${response.data.failed_count}건`, 'error')
    }
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  } finally {
    isUploadingExcel.value = false
  }
}

// 마운트 시 데이터 로드
onMounted(() => {
  // v0.12.0: PartFilterPanel 컴포넌트가 초기 레벨 필터를 설정한 후 검색을 트리거함
  // 초기 로드는 PartFilterPanel의 onMounted에서 처리됨
  loadParts()
})
</script>
