<template>
  <div>
    <div v-if="!enabled" class="text-xs text-gray-400 bg-gray-50 rounded px-3 py-3 text-center">
      납품 파일 연동이 비활성화되어 있습니다. (서버 NEXTCLOUD_DELIVERY_PATH 미설정)
    </div>

    <template v-else>
      <!-- 상단: 개수 + 업로드 -->
      <div class="flex items-center justify-between gap-2 mb-2">
        <div class="text-xs text-gray-500">
          <template v-if="loading">불러오는 중…</template>
          <template v-else>📊 측정자료 <b class="text-gray-700">{{ files.length }}</b>개</template>
          <span v-if="folder" class="text-gray-300 ml-1 font-mono truncate hidden sm:inline" :title="folder">· {{ folderTail }}</span>
        </div>
        <div v-if="!readonly" class="flex items-center gap-1.5 shrink-0">
          <span v-if="uploading" class="text-xs text-blue-600">{{ uploadLabel }}</span>
          <button class="mf-btn mf-btn-primary" :disabled="uploading" @click="fileInput?.click()">⬆ 파일 업로드</button>
          <input ref="fileInput" type="file" accept=".xlsx,.xls,.xlsm,.xlsb,.csv,.pdf,.doc,.docx,.hwp,.hwpx,.ppt,.pptx,.txt,.zip,image/*" multiple class="hidden" @change="onPick" />
        </div>
      </div>

      <!-- 드롭존 + 파일 목록 -->
      <div class="border rounded-lg p-2"
        :class="dragOver ? 'border-blue-400 bg-blue-50/60' : 'border-gray-200'"
        @dragover.prevent="!readonly && (dragOver = true)"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop">

        <div v-if="loading" class="py-6 text-center text-gray-400 text-sm">불러오는 중…</div>
        <div v-else-if="files.length === 0" class="py-6 text-center text-gray-400 text-sm">
          업로드된 측정자료가 없습니다.
          <div v-if="!readonly" class="text-xs text-gray-300 mt-1">엑셀·PDF 등을 끌어다 놓거나 "파일 업로드"를 누르세요.</div>
        </div>

        <ul v-else class="divide-y divide-gray-100">
          <li v-for="f in files" :key="f.name" class="flex items-center gap-2 py-1.5 px-1">
            <span class="text-base shrink-0">{{ iconFor(f.name) }}</span>
            <button class="flex-1 min-w-0 text-left text-sm text-gray-700 hover:text-blue-600 truncate"
              :title="`${f.name} — 다운로드`" @click="download(f)">{{ f.name }}</button>
            <span class="text-[11px] text-gray-400 shrink-0 tabular-nums">{{ sizeText(f.size) }}</span>
            <button class="mf-btn shrink-0" @click="download(f)">⬇</button>
            <button v-if="!readonly" class="mf-btn mf-btn-danger shrink-0" title="삭제" @click="remove(f)">✕</button>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { productionRequestApi } from '@/api/productionRequest'

const props = defineProps<{ requestId: number; readonly?: boolean }>()

const DOC_RE = /\.(xlsx?|xlsm|xlsb|csv|pdf|docx?|hwpx?|pptx?|txt|zip|png|jpe?g|gif|webp|bmp|heic|heif|tiff?)$/i
function isAllowed(f: File): boolean {
  return DOC_RE.test(f.name)
}

type FileItem = { name: string; size: number; mtime: number }
const enabled = ref(true)
const loading = ref(false)
const uploading = ref(false)
const uploadTotal = ref(0)
const uploadDone = ref(0)
const uploadLabel = computed(() => (uploadTotal.value ? `업로드 ${uploadDone.value}/${uploadTotal.value}…` : '업로드 중…'))
const dragOver = ref(false)
const files = ref<FileItem[]>([])
const folder = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const folderTail = computed(() => (folder.value || '').split('/').pop() || '')

function iconFor(name: string): string {
  const n = name.toLowerCase()
  if (/\.(xlsx?|xlsm|xlsb|csv)$/.test(n)) return '📊'
  if (/\.pdf$/.test(n)) return '📕'
  if (/\.(docx?|hwpx?|txt)$/.test(n)) return '📄'
  if (/\.(pptx?)$/.test(n)) return '📑'
  if (/\.(png|jpe?g|gif|webp|bmp|heic|heif|tiff?)$/.test(n)) return '🖼'
  if (/\.zip$/.test(n)) return '🗜'
  return '📎'
}
function sizeText(bytes: number): string {
  if (!bytes && bytes !== 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function load() {
  loading.value = true
  try {
    const data = await productionRequestApi.listMeasurementFiles(props.requestId)
    enabled.value = data.enabled
    folder.value = data.folder
    files.value = data.files || []
  } catch {
    enabled.value = true
    files.value = []
  } finally {
    loading.value = false
  }
}

async function uploadFiles(picked: File[]) {
  const ok = picked.filter(isAllowed)
  if (!ok.length) {
    if (picked.length) alert('허용되지 않는 파일 형식입니다. (엑셀·CSV·PDF·문서·이미지·zip만 가능)')
    return
  }
  uploading.value = true
  uploadTotal.value = ok.length
  uploadDone.value = 0
  try {
    for (const f of ok) {
      await productionRequestApi.uploadMeasurementFile(props.requestId, f)
      uploadDone.value++
    }
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || '업로드에 실패했습니다.')
  } finally {
    uploading.value = false
    uploadTotal.value = 0
    uploadDone.value = 0
  }
}
function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  const picked = Array.from(input.files || [])
  input.value = ''
  uploadFiles(picked)
}
function onDrop(e: DragEvent) {
  dragOver.value = false
  if (props.readonly) return
  const dt = e.dataTransfer
  if (!dt) return
  uploadFiles(Array.from(dt.files || []))
}

async function download(f: FileItem) {
  try {
    await productionRequestApi.downloadMeasurementFile(props.requestId, f.name)
  } catch (e: any) {
    alert(e?.response?.data?.detail || '다운로드에 실패했습니다.')
  }
}

async function remove(f: FileItem) {
  if (!confirm(`'${f.name}' 파일을 삭제하시겠습니까? (Nextcloud 원본도 삭제됩니다)`)) return
  try {
    await productionRequestApi.deleteMeasurementFile(props.requestId, f.name)
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || '삭제에 실패했습니다.')
  }
}

watch(() => props.requestId, load, { immediate: true })
</script>

<style scoped>
.mf-btn { @apply px-2 py-1 text-xs rounded border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors; }
.mf-btn-primary { @apply border-blue-500 text-blue-600 hover:bg-blue-50; }
.mf-btn-danger { @apply hover:bg-red-50 hover:text-red-600 hover:border-red-300; }
</style>
