<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[80] flex items-center justify-center bg-black/70" @click.self="close">
      <div class="bg-white rounded-lg shadow-2xl w-full max-w-5xl mx-4 flex flex-col" style="height: 90vh">
        <!-- 헤더 -->
        <div class="flex items-center justify-between px-6 py-3 border-b">
          <div>
            <h3 class="text-lg font-bold">{{ docNumber }} 미리보기</h3>
            <p class="text-xs text-gray-500 mt-0.5">{{ lang === 'ko' ? '한글' : '영문' }} · {{ docTypeLabel }}</p>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="handleDownload"
              :disabled="downloading"
              class="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50"
            >
              {{ downloading ? '다운로드 중...' : '다운로드' }}
            </button>
            <button @click="close" class="p-2 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- PDF iframe -->
        <div class="flex-1 bg-gray-100 relative">
          <div v-if="loading" class="absolute inset-0 flex items-center justify-center text-gray-500">
            <div class="text-center">
              <svg class="w-8 h-8 animate-spin mx-auto mb-2 text-blue-600" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
                <path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="4" class="opacity-75" />
              </svg>
              <p class="text-sm">PDF 생성 중...</p>
            </div>
          </div>
          <div v-else-if="error" class="absolute inset-0 flex items-center justify-center">
            <div class="text-center text-red-600">
              <p class="font-medium">미리보기 실패</p>
              <p class="text-sm mt-1">{{ error }}</p>
            </div>
          </div>
          <iframe
            v-else-if="pdfUrl"
            :src="pdfUrl"
            class="w-full h-full"
            frameborder="0"
            title="PDF 미리보기"
          ></iframe>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { salesDocumentApi } from '@/api/salesDocument'
import { useToast } from '@/composables/useToast'

interface Props {
  docId: number
  docNumber: string
  docType: 'QUOTATION' | 'PI' | 'CI' | 'INVOICE'
  lang: 'ko' | 'en'
  version?: number
}

const props = defineProps<Props>()
const emit = defineEmits<{ close: [] }>()
const { showToast } = useToast()

const pdfUrl = ref<string | null>(null)
const loading = ref(true)
const downloading = ref(false)
const error = ref<string | null>(null)

const docTypeLabel = computed(() => {
  switch (props.docType) {
    case 'QUOTATION': return '견적서'
    case 'CI': return 'Commercial Invoice'
    case 'INVOICE': return 'Invoice'
    default: return 'Proforma Invoice'
  }
})

async function loadPreview() {
  loading.value = true
  error.value = null
  try {
    pdfUrl.value = await salesDocumentApi.getPdfPreviewBlobUrl(props.docId, props.lang)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'PDF를 불러오지 못했습니다'
  } finally {
    loading.value = false
  }
}

async function handleDownload() {
  downloading.value = true
  try {
    const filename = props.version && props.version > 1
      ? `${props.docNumber}_v${props.version}.pdf`
      : `${props.docNumber}.pdf`
    await salesDocumentApi.downloadPdf(props.docId, props.lang, filename)
    showToast('PDF를 다운로드했습니다', 'success')
  } catch {
    showToast('다운로드 실패', 'error')
  } finally {
    downloading.value = false
  }
}

function close() {
  emit('close')
}

onMounted(() => loadPreview())

onBeforeUnmount(() => {
  // Blob URL 메모리 해제
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = null
  }
})
</script>
