<template>
  <div
    v-if="show"
    class="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50"
    
  >
    <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[85vh] overflow-hidden">
      <!-- 헤더 -->
      <div class="flex justify-between items-center px-6 py-4 border-b">
        <div>
          <h2 class="text-xl font-bold text-gray-800">BOM 엑셀 업로드</h2>
          <p class="text-sm text-blue-500">
            엑셀의 L1 행에서 상위 부품을 자동 인식합니다
          </p>
        </div>
        <button @click="handleClose" class="text-gray-500 hover:text-gray-700">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 본문 -->
      <div class="p-6 overflow-y-auto max-h-[calc(85vh-140px)]">

        <!-- Step 1: 파일 선택 -->
        <div v-if="step === 'select'">
          <!-- 양식 안내 + 템플릿 다운로드 (BOM 개편 2026-09) -->
          <div class="mb-4 rounded-lg border border-blue-200 bg-blue-50/60 p-3">
            <div class="flex items-center justify-between gap-3 flex-wrap">
              <div class="text-[13px] text-blue-800">
                <div class="font-semibold mb-0.5">엑셀 양식: <span class="font-mono">레벨 · 품번 · 품명 · 규격 · 수량 · 단위 · 비고</span></div>
                <div class="text-blue-600 text-[12px]">
                  여기서 <b>레벨(L1/L2/L3)</b>은 <b>트리 위치(상위-하위)</b>를 뜻합니다 — 부품 자체의 레벨코드([S]/[C]/[R])와는 다릅니다.
                  <b>L1</b>이 최상위 제품, 그 아래가 <b>L2</b>, 다시 그 아래가 <b>L3</b>입니다.
                </div>
              </div>
              <button
                @click="downloadTemplate"
                :disabled="isDownloadingTemplate"
                class="flex-shrink-0 px-3 py-1.5 text-sm bg-white border border-blue-300 text-blue-700 rounded hover:bg-blue-100 disabled:opacity-50 flex items-center gap-1.5"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                {{ isDownloadingTemplate ? '준비 중…' : '빈 양식 내려받기' }}
              </button>
            </div>
          </div>

          <!-- 드래그 앤 드롭 영역 -->
          <div
            class="border-2 border-dashed rounded-lg p-8 text-center transition-colors"
            :class="isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
          >
            <svg class="mx-auto h-12 w-12 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            <p class="text-gray-600 mb-2">엑셀 파일을 여기에 드래그하거나</p>
            <label class="cursor-pointer">
              <span class="px-4 py-2 bg-blue-500 text-white text-sm rounded hover:bg-blue-600">
                파일 선택
              </span>
              <input
                type="file"
                accept=".xlsx,.xls"
                class="hidden"
                @change="handleFileSelect"
              />
            </label>
            <p class="text-xs text-gray-400 mt-2">.xlsx, .xls 파일만 가능</p>
          </div>

          <!-- 선택된 파일 표시 -->
          <div v-if="selectedFile" class="mt-4 p-3 bg-gray-50 rounded-lg flex items-center justify-between">
            <div class="flex items-center gap-2">
              <svg class="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M4 18h12a2 2 0 002-2V6l-4-4H4a2 2 0 00-2 2v12a2 2 0 002 2z"/>
              </svg>
              <span class="text-sm text-gray-700">{{ selectedFile.name }}</span>
              <span class="text-xs text-gray-400">({{ formatFileSize(selectedFile.size) }})</span>
            </div>
            <button @click="selectedFile = null" class="text-red-500 hover:text-red-700 text-sm">
              삭제
            </button>
          </div>

          <!-- 모드 선택 -->
          <div class="mt-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">업로드 모드</label>
            <div class="flex gap-4">
              <label class="flex items-start gap-2 cursor-pointer p-3 border rounded-lg"
                     :class="mode === 'replace' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'">
                <input type="radio" v-model="mode" value="replace" class="mt-0.5" />
                <div>
                  <span class="text-sm font-medium">교체</span>
                  <p class="text-xs text-gray-500">기존 BOM을 삭제하고 엑셀 데이터로 교체</p>
                </div>
              </label>
              <label class="flex items-start gap-2 cursor-pointer p-3 border rounded-lg"
                     :class="mode === 'append' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'">
                <input type="radio" v-model="mode" value="append" class="mt-0.5" />
                <div>
                  <span class="text-sm font-medium">추가</span>
                  <p class="text-xs text-gray-500">기존 BOM을 유지하고 새 항목만 추가</p>
                </div>
              </label>
            </div>
          </div>

          <!-- 검증 버튼 -->
          <div class="mt-6 flex justify-end">
            <button
              @click="handleValidate"
              :disabled="!selectedFile || isValidating"
              class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <svg v-if="isValidating" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              {{ isValidating ? '검증 중...' : '검증' }}
            </button>
          </div>
        </div>

        <!-- Step 2: 검증 결과 -->
        <div v-else-if="step === 'validated' && validationResult">
          <!-- 요약 바 -->
          <div class="flex gap-3 mb-4 flex-wrap">
            <div class="flex-1 min-w-[70px] p-3 bg-gray-50 rounded-lg text-center">
              <div class="text-2xl font-bold text-gray-700">{{ validationResult.total_rows }}</div>
              <div class="text-xs text-gray-500">전체</div>
            </div>
            <div class="flex-1 min-w-[70px] p-3 bg-green-50 rounded-lg text-center">
              <div class="text-2xl font-bold text-green-600">{{ validationResult.valid_count }}</div>
              <div class="text-xs text-green-600">정상</div>
            </div>
            <div v-if="validationResult.overwrite_count > 0" class="flex-1 min-w-[70px] p-3 bg-orange-50 rounded-lg text-center">
              <div class="text-2xl font-bold text-orange-600">{{ validationResult.overwrite_count }}</div>
              <div class="text-xs text-orange-600">덮어쓰기</div>
            </div>
            <div v-if="validationResult.new_part_count > 0" class="flex-1 min-w-[70px] p-3 bg-blue-50 rounded-lg text-center">
              <div class="text-2xl font-bold text-blue-600">{{ validationResult.new_part_count }}</div>
              <div class="text-xs text-blue-600">신규 품번</div>
            </div>
            <div v-if="validationResult.error_count > 0" class="flex-1 min-w-[70px] p-3 bg-red-50 rounded-lg text-center">
              <div class="text-2xl font-bold text-red-600">{{ validationResult.error_count }}</div>
              <div class="text-xs text-red-600">오류(스킵)</div>
            </div>
          </div>

          <!-- 감지된 상위 부품 목록 -->
          <div v-if="validationResult.parent_parts.length > 0" class="mb-4 p-3 bg-blue-50 rounded-lg">
            <span class="text-sm text-blue-700 font-medium">감지된 상위 부품 ({{ validationResult.parent_parts.length }}개):</span>
            <div class="mt-1 flex flex-wrap gap-2">
              <span
                v-for="pp in validationResult.parent_parts"
                :key="pp.part_id"
                class="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded"
              >
                {{ pp.part_number }} ({{ pp.part_name }})
              </span>
            </div>
          </div>

          <!-- 덮어쓰기 경고 -->
          <div v-if="validationResult.overwrite_count > 0" class="mb-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
            <div class="flex items-center gap-2 text-orange-700">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              <span class="text-sm font-medium">{{ validationResult.overwrite_count }}건의 기존 BOM이 덮어씌워집니다</span>
            </div>
          </div>

          <!-- 미등록 품번 안내 -->
          <div v-if="validationResult.new_part_count > 0" class="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div class="flex items-center gap-2 text-blue-700">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
              </svg>
              <span class="text-sm font-medium">{{ validationResult.new_part_count }}건의 미등록 품번이 자동 생성됩니다</span>
            </div>
          </div>

          <!-- 오류 안내 -->
          <div v-if="validationResult.error_count > 0" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div class="flex items-center gap-2 text-red-700">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
              <span class="text-sm font-medium">{{ validationResult.error_count }}건의 오류는 스킵됩니다 (나머지는 정상 처리)</span>
            </div>
          </div>

          <!-- 검증 결과 테이블 -->
          <div class="border rounded-lg overflow-hidden">
            <table class="w-full text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">행</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">레벨</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">품번</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">품명</th>
                  <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">수량</th>
                  <th class="px-3 py-2 text-center text-xs font-medium text-gray-500">상태</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">메시지</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr
                  v-for="item in validationResult.items"
                  :key="item.row_number"
                  :class="{
                    'bg-green-50': item.status === 'valid',
                    'bg-yellow-50': item.status === 'warning',
                    'bg-red-50': item.status === 'error',
                  }"
                >
                  <td class="px-3 py-2 text-gray-500">{{ item.row_number }}</td>
                  <td class="px-3 py-2">
                    <span
                      :style="{ paddingLeft: (item.level - 1) * 12 + 'px' }"
                      :class="{ 'font-bold text-blue-700': item.level === 1 }"
                    >
                      L{{ item.level }}
                    </span>
                  </td>
                  <td class="px-3 py-2 font-mono text-xs">
                    {{ item.part_number_display }}
                    <span v-if="item.is_new_part" class="ml-1 text-blue-500 text-[10px]">[NEW]</span>
                  </td>
                  <td class="px-3 py-2">{{ item.resolved_part_name || item.part_name || '-' }}</td>
                  <td class="px-3 py-2 text-right">{{ item.level === 1 ? '-' : item.quantity }}</td>
                  <td class="px-3 py-2 text-center">
                    <span v-if="item.status === 'valid'" class="text-green-600">
                      <svg class="w-4 h-4 inline" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                      </svg>
                    </span>
                    <span v-else-if="item.status === 'warning'" class="text-yellow-600">
                      <svg class="w-4 h-4 inline" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                      </svg>
                    </span>
                    <span v-else class="text-red-600">
                      <svg class="w-4 h-4 inline" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                      </svg>
                    </span>
                  </td>
                  <td class="px-3 py-2 text-xs text-gray-600">
                    {{ item.messages.join(', ') }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 버튼 -->
          <div class="mt-6 flex justify-between">
            <button
              @click="resetToSelect"
              class="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
            >
              다시 선택
            </button>
            <button
              @click="handleUpload"
              :disabled="!canUpload || isUploading"
              class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <svg v-if="isUploading" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              {{ isUploading ? '업로드 중...' : '업로드' }}
            </button>
          </div>
        </div>

        <!-- Step 3: 업로드 완료 -->
        <div v-else-if="step === 'done' && uploadResult">
          <div class="text-center py-8">
            <div v-if="uploadResult.success" class="mb-4">
              <svg class="mx-auto h-16 w-16 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div v-else class="mb-4">
              <svg class="mx-auto h-16 w-16 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>

            <h3 class="text-lg font-bold mb-2" :class="uploadResult.success ? 'text-green-700' : 'text-red-700'">
              {{ uploadResult.success ? '업로드 완료' : '업로드 실패' }}
            </h3>
            <p class="text-gray-600 mb-4">{{ uploadResult.message }}</p>

            <div class="flex gap-3 justify-center mb-6 flex-wrap">
              <div class="p-3 bg-green-50 rounded-lg text-center min-w-[80px]">
                <div class="text-xl font-bold text-green-600">{{ uploadResult.created_count }}</div>
                <div class="text-xs text-green-600">등록</div>
              </div>
              <div v-if="uploadResult.new_part_count > 0" class="p-3 bg-blue-50 rounded-lg text-center min-w-[80px]">
                <div class="text-xl font-bold text-blue-600">{{ uploadResult.new_part_count }}</div>
                <div class="text-xs text-blue-600">신규 품번</div>
              </div>
              <div v-if="uploadResult.overwrite_count > 0" class="p-3 bg-orange-50 rounded-lg text-center min-w-[80px]">
                <div class="text-xl font-bold text-orange-600">{{ uploadResult.overwrite_count }}</div>
                <div class="text-xs text-orange-600">덮어쓰기</div>
              </div>
              <div v-if="uploadResult.skipped_count > 0" class="p-3 bg-yellow-50 rounded-lg text-center min-w-[80px]">
                <div class="text-xl font-bold text-yellow-600">{{ uploadResult.skipped_count }}</div>
                <div class="text-xs text-yellow-600">건너뜀</div>
              </div>
              <div v-if="uploadResult.error_count > 0" class="p-3 bg-red-50 rounded-lg text-center min-w-[80px]">
                <div class="text-xl font-bold text-red-600">{{ uploadResult.error_count }}</div>
                <div class="text-xs text-red-600">스킵</div>
              </div>
            </div>

            <!-- 에러 목록 -->
            <div v-if="uploadResult.errors.length > 0" class="text-left mb-4">
              <h4 class="text-sm font-medium text-red-700 mb-2">오류 상세:</h4>
              <div class="border rounded-lg overflow-hidden">
                <table class="w-full text-sm">
                  <thead class="bg-red-50">
                    <tr>
                      <th class="px-3 py-2 text-left text-xs text-red-600">행</th>
                      <th class="px-3 py-2 text-left text-xs text-red-600">품번</th>
                      <th class="px-3 py-2 text-left text-xs text-red-600">오류</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="err in uploadResult.errors" :key="err.row" class="border-t">
                      <td class="px-3 py-2">{{ err.row }}</td>
                      <td class="px-3 py-2 font-mono text-xs">{{ err.part_no }}</td>
                      <td class="px-3 py-2 text-red-600">{{ err.error }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <button
              @click="handleDone"
              class="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              닫기
            </button>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { bomApi, type BOMUploadValidateResponse, type BOMUploadResult } from '@/api/bom'

interface Props {
  show: boolean
  parentPartId?: number
  parentPartNumber?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  uploaded: [parentPartId?: number]
}>()

// 상태
const step = ref<'select' | 'validated' | 'done'>('select')
const selectedFile = ref<File | null>(null)
const mode = ref<'replace' | 'append'>('replace')
const isDragging = ref(false)
const isValidating = ref(false)
const isUploading = ref(false)
const isDownloadingTemplate = ref(false)
const validationResult = ref<BOMUploadValidateResponse | null>(null)
const uploadResult = ref<BOMUploadResult | null>(null)

// 업로드 가능 여부: 정상 또는 warning 항목이 1개 이상이면 업로드 가능
const canUpload = computed(() => {
  if (!validationResult.value) return false
  return (validationResult.value.valid_count + validationResult.value.warning_count) > 0
})

// 파일 선택
function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    selectedFile.value = input.files[0]
  }
}

// 드래그 앤 드롭
function handleDrop(event: DragEvent) {
  isDragging.value = false
  const files = event.dataTransfer?.files
  if (files && files[0]) {
    const file = files[0]
    if (file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls')) {
      selectedFile.value = file
    } else {
      alert('엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.')
    }
  }
}

// 빈 양식 다운로드
async function downloadTemplate() {
  isDownloadingTemplate.value = true
  try {
    await bomApi.downloadUploadTemplate()
  } catch (error: any) {
    alert(error.response?.data?.detail || '양식 다운로드 중 오류가 발생했습니다.')
  } finally {
    isDownloadingTemplate.value = false
  }
}

// 검증
async function handleValidate() {
  if (!selectedFile.value) return
  isValidating.value = true
  try {
    const result = await bomApi.uploadValidate(selectedFile.value, mode.value)
    validationResult.value = result
    step.value = 'validated'
  } catch (error: any) {
    alert(error.response?.data?.detail || '검증 중 오류가 발생했습니다.')
  } finally {
    isValidating.value = false
  }
}

// 업로드
async function handleUpload() {
  if (!selectedFile.value) return
  isUploading.value = true
  try {
    const result = await bomApi.uploadExcel(selectedFile.value, mode.value)
    uploadResult.value = result
    step.value = 'done'
  } catch (error: any) {
    alert(error.response?.data?.detail || '업로드 중 오류가 발생했습니다.')
  } finally {
    isUploading.value = false
  }
}

// 다시 선택
function resetToSelect() {
  step.value = 'select'
  validationResult.value = null
}

// 완료 후 닫기
function handleDone() {
  if (uploadResult.value?.success) {
    // 첫 번째 상위 부품 ID를 전달 (자동 선택용)
    const firstParentId = uploadResult.value.parent_part_ids?.[0]
    emit('uploaded', firstParentId)
  }
  handleClose()
}

// 닫기
function handleClose() {
  step.value = 'select'
  selectedFile.value = null
  mode.value = 'replace'
  validationResult.value = null
  uploadResult.value = null
  emit('close')
}

// 유틸리티
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>
