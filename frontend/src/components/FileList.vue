<template>
  <div class="file-list">
    <!-- 로딩 상태 -->
    <div v-if="isLoading" class="text-center py-4">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
      <p class="text-sm text-gray-500 mt-2">파일 목록 로딩 중...</p>
    </div>

    <!-- 파일 목록 -->
    <div v-else-if="files" class="space-y-4">
      <!-- 도면 파일 -->
      <div v-if="showDrawing" class="border rounded-lg p-4">
        <h4 class="font-medium text-gray-700 mb-3 flex items-center">
          <span class="text-xl mr-2">📐</span>
          도면 파일
        </h4>
        <div v-if="files.drawing" class="flex items-center justify-between bg-gray-50 p-3 rounded">
          <div class="flex items-center space-x-3">
            <span class="text-2xl">{{ getFileIcon(files.drawing.original_name) }}</span>
            <div>
              <p class="font-medium text-gray-800">{{ files.drawing.original_name }}</p>
              <p class="text-xs text-gray-500">
                {{ formatFileSize(files.drawing.file_size) }} · {{ formatDate(files.drawing.uploaded_at) }}
              </p>
            </div>
          </div>
          <div class="flex items-center space-x-2">
            <button
              v-if="fileApi.canPreview(files.drawing.original_name)"
              type="button"
              class="p-2 text-blue-500 hover:bg-blue-50 rounded"
              title="미리보기"
              @click="previewFile(files.drawing)"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </button>
            <button
              type="button"
              class="p-2 text-green-500 hover:bg-green-50 rounded"
              title="다운로드"
              @click="downloadFile(files.drawing)"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </button>
            <button
              v-if="editable"
              type="button"
              class="p-2 text-red-500 hover:bg-red-50 rounded"
              title="삭제"
              @click="deleteFile('drawing')"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
        <div v-else class="text-gray-400 text-sm py-2">첨부된 도면 파일이 없습니다</div>
      </div>

      <!-- 사진 파일 -->
      <div v-if="showPhoto" class="border rounded-lg p-4">
        <h4 class="font-medium text-gray-700 mb-3 flex items-center">
          <span class="text-xl mr-2">🖼️</span>
          사진 파일
        </h4>
        <div v-if="files.photo" class="bg-gray-50 p-3 rounded">
          <div class="flex items-start space-x-4">
            <!-- 이미지 미리보기 -->
            <img
              v-if="fileApi.isImageFile(files.photo.original_name) && photoThumbUrl"
              :src="photoThumbUrl"
              :alt="files.photo.original_name"
              class="w-32 h-32 object-cover rounded border"
              @error="handleImageError"
            />
            <div class="flex-1">
              <p class="font-medium text-gray-800">{{ files.photo.original_name }}</p>
              <p class="text-xs text-gray-500 mb-2">
                {{ formatFileSize(files.photo.file_size) }} · {{ formatDate(files.photo.uploaded_at) }}
              </p>
              <div class="flex items-center space-x-2">
                <button
                  type="button"
                  class="px-3 py-1 text-sm text-blue-500 hover:bg-blue-50 rounded border border-blue-200"
                  @click="previewFile(files.photo)"
                >
                  미리보기
                </button>
                <button
                  type="button"
                  class="px-3 py-1 text-sm text-green-500 hover:bg-green-50 rounded border border-green-200"
                  @click="downloadFile(files.photo)"
                >
                  다운로드
                </button>
                <button
                  v-if="editable"
                  type="button"
                  class="px-3 py-1 text-sm text-red-500 hover:bg-red-50 rounded border border-red-200"
                  @click="deleteFile('photo')"
                >
                  삭제
                </button>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="text-gray-400 text-sm py-2">첨부된 사진 파일이 없습니다</div>
      </div>

      <!-- 문서 파일들 -->
      <div v-if="showDocuments" class="border rounded-lg p-4">
        <h4 class="font-medium text-gray-700 mb-3 flex items-center">
          <span class="text-xl mr-2">📁</span>
          문서 파일
          <span class="ml-2 text-sm text-gray-400">({{ files.documents?.length || 0 }}개)</span>
        </h4>
        <div v-if="files.documents && files.documents.length > 0" class="space-y-2">
          <div
            v-for="(doc, index) in files.documents"
            :key="index"
            class="flex items-center justify-between bg-gray-50 p-3 rounded"
          >
            <div class="flex items-center space-x-3">
              <span class="text-2xl">{{ getFileIcon(doc.original_name) }}</span>
              <div>
                <p class="font-medium text-gray-800">{{ doc.original_name }}</p>
                <p class="text-xs text-gray-500">
                  {{ formatFileSize(doc.file_size) }} · {{ formatDate(doc.uploaded_at) }}
                </p>
              </div>
            </div>
            <div class="flex items-center space-x-2">
              <button
                v-if="fileApi.canPreview(doc.original_name)"
                type="button"
                class="p-2 text-blue-500 hover:bg-blue-50 rounded"
                title="미리보기"
                @click="previewFile(doc)"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </button>
              <button
                type="button"
                class="p-2 text-green-500 hover:bg-green-50 rounded"
                title="다운로드"
                @click="downloadFile(doc)"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
              </button>
              <button
                v-if="editable"
                type="button"
                class="p-2 text-red-500 hover:bg-red-50 rounded"
                title="삭제"
                @click="deleteFile('document', index)"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
        <div v-else class="text-gray-400 text-sm py-2">첨부된 문서 파일이 없습니다</div>
      </div>
    </div>

    <!-- 파일 없음 -->
    <div v-else class="text-center py-8 text-gray-400">
      <svg class="mx-auto h-12 w-12 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p>첨부된 파일이 없습니다</p>
    </div>

    <!-- 미리보기 모달 -->
    <div
      v-if="previewUrl"
      class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50"
      @click.self="closePreview"
    >
      <div class="relative max-w-4xl max-h-[90vh] bg-white rounded-lg overflow-hidden">
        <button
          type="button"
          class="absolute top-2 right-2 p-2 bg-white rounded-full shadow-lg text-gray-600 hover:text-gray-900 z-10"
          @click="closePreview"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <img
          v-if="isImagePreview"
          :src="previewUrl"
          class="max-w-full max-h-[90vh] object-contain"
        />
        <iframe
          v-else
          :src="previewUrl"
          class="w-[800px] h-[600px]"
        ></iframe>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue'
import { fileApi, type FileType, type PartFilesResponse, type FileInfo } from '@/api/files'
import { downloadAuthedUrl, fetchAuthedObjectUrl } from '@/utils/download'

interface Props {
  partId: number
  showDrawing?: boolean
  showPhoto?: boolean
  showDocuments?: boolean
  editable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showDrawing: true,
  showPhoto: true,
  showDocuments: true,
  editable: true,
})

const emit = defineEmits<{
  deleted: [fileType: FileType, index?: number]
  refresh: []
}>()

const isLoading = ref(false)
const files = ref<PartFilesResponse | null>(null)
const previewUrl = ref('')
const isImagePreview = ref(false)
const photoThumbUrl = ref('')  // v0.41.0: 인증 헤더로 받은 사진 썸네일 object URL

// 파일 목록 로드
const loadFiles = async () => {
  isLoading.value = true
  try {
    const response = await fileApi.getPartFiles(props.partId)
    files.value = response.data
    // 사진 썸네일을 인증 헤더와 함께 로드(RBAC enforce 시 <img src> 401 방지)
    if (photoThumbUrl.value) { window.URL.revokeObjectURL(photoThumbUrl.value); photoThumbUrl.value = '' }
    const photo = files.value?.photo
    if (photo && fileApi.isImageFile(photo.original_name)) {
      try {
        photoThumbUrl.value = await fetchAuthedObjectUrl(`/files/${photo.file_path}`, { preview: true })
      } catch { /* 썸네일 실패는 무시 */ }
    }
  } catch (error) {
    console.error('파일 목록 로드 실패:', error)
  } finally {
    isLoading.value = false
  }
}

// 파일 미리보기 (인증 헤더로 blob 받아 object URL 로 표시)
const previewFile = async (file: FileInfo) => {
  isImagePreview.value = fileApi.isImageFile(file.original_name)
  closePreview()
  try {
    previewUrl.value = await fetchAuthedObjectUrl(`/files/${file.file_path}`, { preview: true })
  } catch (e) {
    console.error('미리보기 실패', e)
  }
}

// 미리보기 닫기(object URL 해제)
const closePreview = () => {
  if (previewUrl.value) window.URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

// 파일 다운로드 (인증 헤더로 blob 다운로드)
const downloadFile = (file: FileInfo) => {
  downloadAuthedUrl(`/files/${file.file_path}`, file.original_name).catch((e) => console.error('다운로드 실패', e))
}

// 파일 삭제
const deleteFile = async (fileType: FileType, index?: number) => {
  if (!confirm('정말 삭제하시겠습니까?')) return

  try {
    await fileApi.delete(props.partId, fileType, index)
    emit('deleted', fileType, index)
    await loadFiles()
  } catch (error: any) {
    alert(error.response?.data?.detail || '삭제에 실패했습니다')
  }
}

// 파일 크기 포맷팅
const formatFileSize = (bytes: number): string => {
  return fileApi.formatFileSize(bytes)
}

// 날짜 포맷팅
const formatDate = (dateStr: string): string => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 파일 아이콘
const getFileIcon = (fileName: string): string => {
  if (!fileName) return '📎'
  const ext = fileApi.getFileExtension(fileName)
  const icons: Record<string, string> = {
    pdf: '📄',
    doc: '📝',
    docx: '📝',
    xls: '📊',
    xlsx: '📊',
    hwp: '📝',
    jpg: '🖼️',
    jpeg: '🖼️',
    png: '🖼️',
    gif: '🖼️',
    webp: '🖼️',
    dwg: '📐',
    dxf: '📐',
    step: '📐',
    stp: '📐',
    igs: '📐',
  }
  return icons[ext] || '📎'
}

// 이미지 로드 에러 처리
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

// 외부에서 새로고침 호출 가능
const refresh = () => {
  loadFiles()
}

defineExpose({ refresh })

// objectURL 누수 방지 (언마운트 시 해제)
onBeforeUnmount(() => {
  closePreview()
  if (photoThumbUrl.value) window.URL.revokeObjectURL(photoThumbUrl.value)
})

// partId 변경 감지
watch(
  () => props.partId,
  (newId) => {
    if (newId) {
      loadFiles()
    }
  },
  { immediate: true }
)
</script>
