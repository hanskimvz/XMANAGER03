<template>
  <div class="file-upload">
    <!-- 업로드 영역 -->
    <div
      class="border-2 border-dashed rounded-lg p-6 text-center transition-colors"
      :class="{
        'border-blue-400 bg-blue-50': isDragging,
        'border-gray-300 hover:border-gray-400': !isDragging,
      }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <input
        ref="fileInput"
        type="file"
        :accept="acceptString"
        class="hidden"
        @change="handleFileSelect"
      />

      <div v-if="!isUploading" class="space-y-2">
        <svg
          class="mx-auto h-12 w-12 text-gray-400"
          stroke="currentColor"
          fill="none"
          viewBox="0 0 48 48"
        >
          <path
            d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <div class="text-gray-600">
          <button
            type="button"
            class="text-blue-500 hover:text-blue-600 font-medium"
            @click="openFileDialog"
          >
            파일 선택
          </button>
          <span class="text-gray-500"> 또는 여기에 파일을 드래그하세요</span>
        </div>
        <p class="text-xs text-gray-500">{{ fileTypeDescription }}</p>
        <p class="text-xs text-gray-400">최대 200MB</p>
      </div>

      <!-- 업로드 진행률 -->
      <div v-else class="space-y-3">
        <div class="flex items-center justify-center">
          <svg
            class="animate-spin h-8 w-8 text-blue-500"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            ></circle>
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        </div>
        <p class="text-sm text-gray-600">업로드 중... {{ uploadProgress }}%</p>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div
            class="bg-blue-500 h-2 rounded-full transition-all duration-300"
            :style="{ width: `${uploadProgress}%` }"
          ></div>
        </div>
      </div>
    </div>

    <!-- 선택된 파일 정보 -->
    <div v-if="selectedFile && !isUploading" class="mt-4">
      <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <div class="flex items-center space-x-3">
          <span class="text-2xl">{{ getFileIcon(selectedFile.name) }}</span>
          <div>
            <p class="text-sm font-medium text-gray-800">{{ selectedFile.name }}</p>
            <p class="text-xs text-gray-500">{{ formatFileSize(selectedFile.size) }}</p>
          </div>
        </div>
        <div class="flex items-center space-x-2">
          <button
            type="button"
            class="px-3 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
            @click="uploadFile"
          >
            업로드
          </button>
          <button
            type="button"
            class="p-1.5 text-gray-400 hover:text-red-500"
            @click="clearSelectedFile"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 유효성 검사 오류 -->
      <p v-if="validationError" class="mt-2 text-sm text-red-500">{{ validationError }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { fileApi, type FileType, type FileUploadResponse, MAX_FILE_SIZE, ALLOWED_EXTENSIONS } from '@/api/files'

interface Props {
  partId: number
  fileType: FileType
}

const props = defineProps<Props>()

const emit = defineEmits<{
  uploaded: [response: FileUploadResponse]
  error: [error: string]
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const isUploading = ref(false)
const uploadProgress = ref(0)
const selectedFile = ref<File | null>(null)
const validationError = ref('')

// 파일 타입별 설명
const fileTypeDescription = computed(() => fileApi.getFileTypeDescription(props.fileType))

// accept 속성용 문자열
const acceptString = computed(() => fileApi.getAcceptString(props.fileType))

// 파일 선택 다이얼로그 열기
const openFileDialog = () => {
  fileInput.value?.click()
}

// 파일 선택 처리
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    setSelectedFile(file)
  }
}

// 드래그 앤 드롭 처리
const handleDrop = (event: DragEvent) => {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) {
    setSelectedFile(file)
  }
}

// 파일 설정 및 유효성 검사
const setSelectedFile = (file: File) => {
  validationError.value = ''

  // 파일 확장자 검사
  if (!fileApi.isValidExtension(file.name, props.fileType)) {
    const allowed = ALLOWED_EXTENSIONS[props.fileType].join(', ')
    validationError.value = `허용되지 않는 파일 형식입니다. 허용: ${allowed}`
    selectedFile.value = null
    return
  }

  // 파일 크기 검사
  if (!fileApi.isValidFileSize(file.size)) {
    const maxMb = MAX_FILE_SIZE / (1024 * 1024)
    validationError.value = `파일 크기가 너무 큽니다. 최대 ${maxMb}MB까지 허용됩니다.`
    selectedFile.value = null
    return
  }

  selectedFile.value = file
}

// 선택 파일 초기화
const clearSelectedFile = () => {
  selectedFile.value = null
  validationError.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// 파일 업로드
const uploadFile = async () => {
  if (!selectedFile.value) return

  isUploading.value = true
  uploadProgress.value = 0

  try {
    const response = await fileApi.upload(
      props.partId,
      props.fileType,
      selectedFile.value,
      (progress) => {
        uploadProgress.value = progress
      }
    )

    if (response.success) {
      emit('uploaded', response)
      clearSelectedFile()
    } else {
      emit('error', response.message)
    }
  } catch (error: any) {
    const message = error.response?.data?.detail || '파일 업로드에 실패했습니다'
    emit('error', message)
  } finally {
    isUploading.value = false
    uploadProgress.value = 0
  }
}

// 파일 크기 포맷팅
const formatFileSize = (bytes: number): string => {
  return fileApi.formatFileSize(bytes)
}

// 파일 아이콘
const getFileIcon = (fileName: string): string => {
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
</script>
