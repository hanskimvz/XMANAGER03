<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[80] flex items-center justify-center bg-black/70" @click.self="close">
      <div class="bg-white rounded-lg shadow-2xl w-full max-w-5xl mx-4 flex flex-col" style="height: 90vh">
        <!-- 헤더 -->
        <div class="flex items-center justify-between px-6 py-3 border-b">
          <div>
            <h3 class="text-lg font-bold">{{ docNumber }} 운송장</h3>
            <p class="text-xs text-gray-500 mt-0.5">
              {{ files.length > 0 ? `${files.length}개 파일` : '아직 업로드된 운송장이 없습니다' }}
            </p>
          </div>
          <div class="flex items-center gap-2">
            <button
              v-if="files.length > 0"
              @click="handleDownload"
              :disabled="downloading || activeIndex === -1"
              class="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50"
            >
              {{ downloading ? '다운로드 중...' : '다운로드' }}
            </button>
            <label
              class="px-3 py-1.5 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded cursor-pointer"
              :class="uploading ? 'opacity-50 cursor-not-allowed' : ''"
            >
              {{ uploading ? '업로드 중...' : '파일 추가' }}
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                multiple
                class="hidden"
                :disabled="uploading"
                @change="handleUpload"
              />
            </label>
            <button @click="close" class="p-2 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 파일 탭 (여러 개일 때) -->
        <div v-if="files.length > 1" class="flex items-center gap-1 px-4 pt-2 border-b bg-gray-50 overflow-x-auto">
          <button
            v-for="(f, idx) in files"
            :key="idx"
            @click="selectFile(idx)"
            :class="activeIndex === idx
              ? 'bg-white border-t border-l border-r text-blue-700 font-medium'
              : 'text-gray-500 hover:text-gray-800'"
            class="px-3 py-1.5 text-xs rounded-t whitespace-nowrap"
            :title="f.filename"
          >
            {{ truncate(f.filename, 28) }}
          </button>
        </div>

        <!-- 미리보기 영역 -->
        <div
          class="flex-1 bg-gray-100 relative overflow-auto"
          @dragenter.prevent="onDragEnter"
          @dragover.prevent="onDragOver"
          @dragleave.prevent="onDragLeave"
          @drop.prevent="onDrop"
        >
          <!-- 드래그 오버레이 -->
          <div
            v-if="isDragging"
            class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-blue-50/95 border-4 border-dashed border-blue-400 pointer-events-none"
          >
            <svg class="w-16 h-16 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p class="text-base font-medium text-blue-700">파일을 여기에 놓아 업로드</p>
            <p class="text-xs text-blue-500">PDF, PNG, JPG (최대 200MB)</p>
          </div>

          <!-- 빈 상태 -->
          <div v-if="files.length === 0" class="absolute inset-0 flex flex-col items-center justify-center gap-3 text-gray-500">
            <svg class="w-16 h-16 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="text-sm">운송장 PDF 또는 이미지를 업로드하세요</p>
            <p class="text-xs text-gray-400">PDF, PNG, JPG · 드래그 또는 "파일 추가" 버튼 · 최대 200MB</p>
          </div>

          <!-- 로딩 -->
          <div v-else-if="loading" class="absolute inset-0 flex items-center justify-center text-gray-500">
            <div class="text-center">
              <svg class="w-8 h-8 animate-spin mx-auto mb-2 text-blue-600" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
                <path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="4" class="opacity-75" />
              </svg>
              <p class="text-sm">불러오는 중...</p>
            </div>
          </div>

          <!-- 에러 -->
          <div v-else-if="error" class="absolute inset-0 flex items-center justify-center">
            <div class="text-center text-red-600">
              <p class="font-medium">미리보기 실패</p>
              <p class="text-sm mt-1">{{ error }}</p>
            </div>
          </div>

          <!-- PDF -->
          <iframe
            v-else-if="previewUrl && isPdf"
            :src="previewUrl"
            class="w-full h-full"
            frameborder="0"
            title="운송장 미리보기"
          />

          <!-- 이미지 -->
          <div v-else-if="previewUrl && isImage" class="flex items-center justify-center min-h-full p-4">
            <img :src="previewUrl" :alt="activeFile?.filename" class="max-w-full max-h-full object-contain shadow-md" />
          </div>
        </div>

        <!-- 푸터: 활성 파일 정보 + 삭제 -->
        <div v-if="files.length > 0 && activeFile" class="flex items-center justify-between px-6 py-2 border-t bg-gray-50">
          <div class="text-xs text-gray-600 truncate flex-1 mr-3">
            <span class="font-medium">{{ activeFile.filename }}</span>
            <span class="text-gray-400 ml-2">{{ formatSize(activeFile.size) }}</span>
            <span v-if="activeFile.uploaded_at" class="text-gray-400 ml-2">{{ formatDate(activeFile.uploaded_at) }}</span>
          </div>
          <button
            @click="handleDelete"
            :disabled="deleting"
            class="px-3 py-1 text-xs text-red-600 hover:text-white hover:bg-red-600 border border-red-300 rounded disabled:opacity-50"
          >
            {{ deleting ? '삭제 중...' : '삭제' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { salesDocumentApi, type ShippingInvoiceFile } from '@/api/salesDocument'
import { useToast } from '@/composables/useToast'

interface Props {
  docId: number
  docNumber: string
  initialFiles?: ShippingInvoiceFile[]
}

const props = withDefaults(defineProps<Props>(), { initialFiles: () => [] })
const emit = defineEmits<{
  close: []
  updated: [files: ShippingInvoiceFile[]]
}>()
const { showToast } = useToast()

const files = ref<ShippingInvoiceFile[]>([...props.initialFiles])
const activeIndex = ref<number>(files.value.length > 0 ? 0 : -1)
const previewUrl = ref<string | null>(null)
const previewMime = ref<string>('')
const loading = ref(false)
const error = ref<string | null>(null)
const uploading = ref(false)
const downloading = ref(false)
const deleting = ref(false)
const isDragging = ref(false)
let dragCounter = 0

const ACCEPTED_EXT = ['.pdf', '.png', '.jpg', '.jpeg']
const ACCEPTED_MIME_PREFIX = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg']

function isAcceptedFile(file: File): boolean {
  const name = (file.name || '').toLowerCase()
  if (ACCEPTED_EXT.some(ext => name.endsWith(ext))) return true
  return ACCEPTED_MIME_PREFIX.some(m => (file.type || '').startsWith(m))
}

const activeFile = computed(() => activeIndex.value >= 0 ? files.value[activeIndex.value] : null)
const isPdf = computed(() => previewMime.value.includes('pdf'))
const isImage = computed(() => previewMime.value.startsWith('image/'))

function revokePreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
}

async function loadPreview(idx: number) {
  if (idx < 0 || idx >= files.value.length) {
    revokePreview()
    return
  }
  loading.value = true
  error.value = null
  revokePreview()
  try {
    const { url, mimetype } = await salesDocumentApi.getShippingInvoicePreviewBlobUrl(props.docId, idx)
    previewUrl.value = url
    previewMime.value = mimetype
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '미리보기를 불러오지 못했습니다'
  } finally {
    loading.value = false
  }
}

function selectFile(idx: number) {
  activeIndex.value = idx
  loadPreview(idx)
}

async function uploadFiles(fileList: File[]) {
  if (fileList.length === 0) return
  uploading.value = true
  let lastFile: ShippingInvoiceFile | null = null
  let successCount = 0
  try {
    for (const f of fileList) {
      if (!isAcceptedFile(f)) {
        showToast(`지원하지 않는 형식: ${f.name}`, 'error')
        continue
      }
      try {
        const res = await salesDocumentApi.uploadShippingInvoice(props.docId, f)
        const newFile: ShippingInvoiceFile = res.data?.file
        if (newFile) {
          files.value.push(newFile)
          lastFile = newFile
          successCount += 1
        }
      } catch (e: any) {
        showToast(e?.response?.data?.detail || `${f.name} 업로드 실패`, 'error')
      }
    }
    if (lastFile) {
      activeIndex.value = files.value.length - 1
      await loadPreview(activeIndex.value)
    }
    if (successCount > 0) {
      showToast(`${successCount}개 운송장이 업로드되었습니다`, 'success')
      emit('updated', files.value)
    }
  } finally {
    uploading.value = false
  }
}

async function handleUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const list = input.files ? Array.from(input.files) : []
  await uploadFiles(list)
  input.value = ''
}

function onDragEnter(e: DragEvent) {
  if (!e.dataTransfer?.types?.includes('Files')) return
  dragCounter += 1
  isDragging.value = true
}

function onDragOver(e: DragEvent) {
  if (!e.dataTransfer?.types?.includes('Files')) return
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
}

function onDragLeave() {
  dragCounter = Math.max(0, dragCounter - 1)
  if (dragCounter === 0) isDragging.value = false
}

async function onDrop(e: DragEvent) {
  dragCounter = 0
  isDragging.value = false
  const dropped = e.dataTransfer?.files ? Array.from(e.dataTransfer.files) : []
  if (dropped.length === 0) return
  await uploadFiles(dropped)
}

async function handleDelete() {
  if (activeIndex.value < 0) return
  if (!confirm('이 운송장을 삭제하시겠습니까?')) return
  deleting.value = true
  try {
    await salesDocumentApi.deleteShippingInvoice(props.docId, activeIndex.value)
    files.value.splice(activeIndex.value, 1)
    revokePreview()
    if (files.value.length === 0) {
      activeIndex.value = -1
    } else {
      activeIndex.value = Math.min(activeIndex.value, files.value.length - 1)
      await loadPreview(activeIndex.value)
    }
    showToast('삭제되었습니다', 'success')
    emit('updated', files.value)
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '삭제 실패', 'error')
  } finally {
    deleting.value = false
  }
}

async function handleDownload() {
  if (activeIndex.value < 0) return
  downloading.value = true
  try {
    const url = salesDocumentApi.getShippingInvoiceDownloadUrl(props.docId, activeIndex.value)
    const a = document.createElement('a')
    a.href = url
    a.download = activeFile.value?.filename || `shipping_${props.docId}_${activeIndex.value}`
    document.body.appendChild(a)
    a.click()
    a.remove()
  } catch {
    showToast('다운로드 실패', 'error')
  } finally {
    downloading.value = false
  }
}

function close() {
  emit('close')
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}

function formatSize(bytes?: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('ko-KR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

watch(() => props.initialFiles, (newFiles) => {
  files.value = [...(newFiles || [])]
  if (files.value.length > 0 && activeIndex.value < 0) {
    activeIndex.value = 0
    loadPreview(0)
  } else if (files.value.length === 0) {
    activeIndex.value = -1
    revokePreview()
  }
})

onMounted(() => {
  if (activeIndex.value >= 0) loadPreview(activeIndex.value)
})

onBeforeUnmount(() => {
  revokePreview()
})
</script>
