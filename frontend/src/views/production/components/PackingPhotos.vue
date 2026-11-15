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
          <template v-else>📷 포장사진 <b class="text-gray-700">{{ photos.length }}</b>장</template>
          <span v-if="folder" class="text-gray-300 ml-1 font-mono truncate hidden sm:inline" :title="folder">· {{ folderTail }}</span>
        </div>
        <div v-if="!readonly" class="flex items-center gap-1.5 shrink-0">
          <span v-if="uploading" class="text-xs text-blue-600">{{ uploadLabel }}</span>
          <button class="pp-btn" :disabled="uploading" @click="dirInput?.click()" title="폴더 안의 이미지를 전부 업로드">📁 폴더</button>
          <input ref="dirInput" type="file" multiple class="hidden" @change="onPickDir" />
          <button class="pp-btn pp-btn-primary" :disabled="uploading" @click="fileInput?.click()">⬆ 사진 업로드</button>
          <input ref="fileInput" type="file" accept="image/*" multiple class="hidden" @change="onPick" />
        </div>
      </div>

      <!-- 드롭존 -->
      <div class="border rounded-lg p-2"
        :class="dragOver ? 'border-blue-400 bg-blue-50/60' : 'border-gray-200'"
        @dragover.prevent="!readonly && (dragOver = true)"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop">

        <div v-if="loading" class="py-6 text-center text-gray-400 text-sm">불러오는 중…</div>
        <div v-else-if="photos.length === 0" class="py-6 text-center text-gray-400 text-sm">
          업로드된 포장사진이 없습니다.
          <div v-if="!readonly" class="text-xs text-gray-300 mt-1">사진을 끌어다 놓거나 "사진 업로드"를 누르세요.</div>
        </div>

        <!-- 적을 때(≤ threshold): 썸네일 그리드 -->
        <div v-else-if="photos.length <= THRESHOLD" class="grid grid-cols-3 sm:grid-cols-4 gap-2">
          <div v-for="(p, i) in photos" :key="p.name" class="relative group aspect-square">
            <button class="w-full h-full rounded overflow-hidden border border-gray-200 bg-gray-50" @click="openViewer(i)">
              <img v-if="thumbs[p.name]" :src="thumbs[p.name]" class="w-full h-full object-cover" />
              <span v-else class="w-full h-full flex items-center justify-center text-[10px] text-gray-400">불러오는 중…</span>
            </button>
            <button v-if="!readonly" @click.stop="remove(p)" title="삭제"
              class="absolute top-0.5 right-0.5 w-5 h-5 rounded-full bg-black/50 text-white text-xs opacity-0 group-hover:opacity-100 transition-opacity">✕</button>
          </div>
        </div>

        <!-- 많을 때(> threshold): 요약 + 폴더 열기 -->
        <div v-else class="flex items-center justify-between px-2 py-3">
          <div class="flex items-center gap-2 text-sm text-gray-700">
            <span class="text-2xl">🗂</span>
            <div>
              <div class="font-medium">포장사진 {{ photos.length }}장</div>
              <div class="text-xs text-gray-400">사진이 많아 목록으로 표시됩니다.</div>
            </div>
          </div>
          <button class="pp-btn pp-btn-primary" @click="openFolder">📂 폴더 열기</button>
        </div>
      </div>
    </template>

    <!-- 폴더 뷰어(전체 그리드) / 라이트박스 -->
    <Teleport to="body">
      <div v-if="folderOpen" class="fixed inset-0 z-[75] bg-black/60 flex items-center justify-center p-4" @click.self="folderOpen = false">
        <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[88vh] flex flex-col overflow-hidden">
          <div class="flex items-center justify-between px-5 py-3 border-b">
            <div class="text-sm font-semibold text-gray-800">📂 포장사진 ({{ photos.length }}장)</div>
            <button class="pp-btn" @click="folderOpen = false">닫기 ✕</button>
          </div>
          <div class="flex-1 overflow-auto p-4">
            <div class="grid grid-cols-3 sm:grid-cols-5 gap-2">
              <div v-for="(p, i) in photos" :key="p.name" class="relative group aspect-square">
                <button class="w-full h-full rounded overflow-hidden border border-gray-200 bg-gray-50" @click="openViewer(i)">
                  <img v-if="thumbs[p.name]" :src="thumbs[p.name]" class="w-full h-full object-cover" loading="lazy" />
                  <span v-else class="w-full h-full flex items-center justify-center text-[10px] text-gray-400">…</span>
                </button>
                <button v-if="!readonly" @click.stop="remove(p)" title="삭제"
                  class="absolute top-0.5 right-0.5 w-5 h-5 rounded-full bg-black/50 text-white text-xs opacity-0 group-hover:opacity-100">✕</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 큰 미리보기 -->
      <div v-if="viewer" class="fixed inset-0 z-[80] bg-black/80 flex items-center justify-center p-4" @click.self="closeViewer">
        <div class="max-w-5xl w-full max-h-[92vh] flex flex-col items-center">
          <div class="flex items-center justify-between w-full mb-2 text-white text-sm">
            <span class="truncate">{{ viewer.name }} ({{ viewer.index + 1 }}/{{ photos.length }})</span>
            <div class="flex gap-2">
              <button class="pp-btn-dark" @click="viewerStep(-1)">‹ 이전</button>
              <button class="pp-btn-dark" @click="viewerStep(1)">다음 ›</button>
              <button class="pp-btn-dark" @click="closeViewer">닫기 ✕</button>
            </div>
          </div>
          <img v-if="viewer.url" :src="viewer.url" class="max-w-full max-h-[82vh] object-contain rounded" />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { productionRequestApi } from '@/api/productionRequest'

const props = defineProps<{ requestId: number; readonly?: boolean }>()

const THRESHOLD = 6  // 이 개수 이하면 썸네일, 초과면 리스트/폴더열기
const IMG_RE = /\.(png|jpe?g|gif|webp|bmp|heic|heif|tiff?)$/i
function isImageFile(f: File): boolean {
  return (f.type || '').startsWith('image/') || IMG_RE.test(f.name)
}

type Photo = { name: string; size: number; mtime: number }
const enabled = ref(true)
const loading = ref(false)
const uploading = ref(false)
const uploadTotal = ref(0)
const uploadDone = ref(0)
const uploadLabel = computed(() => (uploadTotal.value ? `업로드 ${uploadDone.value}/${uploadTotal.value}…` : '업로드 중…'))
const dragOver = ref(false)
const photos = ref<Photo[]>([])
const folder = ref<string | null>(null)
const thumbs = reactive<Record<string, string>>({})
const fileInput = ref<HTMLInputElement | null>(null)
const dirInput = ref<HTMLInputElement | null>(null)
const folderOpen = ref(false)

const folderTail = computed(() => (folder.value || '').split('/').pop() || '')

async function load() {
  loading.value = true
  try {
    const data = await productionRequestApi.listPackingPhotos(props.requestId)
    enabled.value = data.enabled
    folder.value = data.folder
    photos.value = data.photos || []
    loadThumbs()
  } catch {
    enabled.value = true
    photos.value = []
  } finally {
    loading.value = false
  }
}

async function loadThumbs() {
  for (const p of photos.value) {
    if (thumbs[p.name]) continue
    try {
      thumbs[p.name] = await productionRequestApi.packingPhotoBlobUrl(props.requestId, p.name)
    } catch { /* 개별 실패 무시 */ }
  }
}

async function uploadFiles(files: File[]) {
  const imgs = files.filter(isImageFile)
  if (!imgs.length) {
    if (files.length) alert('이미지 파일이 없습니다.')
    return
  }
  uploading.value = true
  uploadTotal.value = imgs.length
  uploadDone.value = 0
  try {
    for (const f of imgs) {
      await productionRequestApi.uploadPackingPhoto(props.requestId, f)
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
  const files = Array.from(input.files || [])
  input.value = ''
  uploadFiles(files)
}
// 폴더 선택(webkitdirectory) — 안의 이미지 전부(하위폴더 포함)
function onPickDir(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  uploadFiles(files)
}
// 드롭 — 파일/폴더 모두. 폴더는 재귀 탐색(webkitGetAsEntry)
function onDrop(e: DragEvent) {
  dragOver.value = false
  if (props.readonly) return
  const dt = e.dataTransfer
  if (!dt) return
  const entries: any[] = []
  const items = dt.items
  if (items && items.length && (items[0] as any).webkitGetAsEntry) {
    for (const it of Array.from(items)) {
      const entry = (it as any).webkitGetAsEntry?.()
      if (entry) entries.push(entry)
    }
  }
  if (entries.length) {
    collectFromEntries(entries).then(uploadFiles)
  } else {
    uploadFiles(Array.from(dt.files || []))
  }
}
async function collectFromEntries(entries: any[]): Promise<File[]> {
  const out: File[] = []
  for (const e of entries) await traverseEntry(e, out)
  return out
}
function traverseEntry(entry: any, out: File[]): Promise<void> {
  return new Promise((resolve) => {
    if (!entry) return resolve()
    if (entry.isFile) {
      entry.file((f: File) => { out.push(f); resolve() }, () => resolve())
    } else if (entry.isDirectory) {
      const reader = entry.createReader()
      const readBatch = () => reader.readEntries(async (batch: any[]) => {
        if (!batch.length) return resolve()  // 더 없음
        for (const e of batch) await traverseEntry(e, out)
        readBatch()  // readEntries는 배치로 반환 → 빈 배치까지 반복
      }, () => resolve())
      readBatch()
    } else resolve()
  })
}

async function remove(p: Photo) {
  if (!confirm(`'${p.name}' 사진을 삭제하시겠습니까? (Nextcloud 원본도 삭제됩니다)`)) return
  try {
    await productionRequestApi.deletePackingPhoto(props.requestId, p.name)
    const u = thumbs[p.name]
    if (u) { URL.revokeObjectURL(u); delete thumbs[p.name] }
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || '삭제에 실패했습니다.')
  }
}

function openFolder() { folderOpen.value = true }

// 라이트박스
type Viewer = { index: number; name: string; url: string }
const viewer = ref<Viewer | null>(null)
function openViewer(i: number) {
  const p = photos.value[i]
  if (!p) return
  viewer.value = { index: i, name: p.name, url: thumbs[p.name] || '' }
}
function viewerStep(d: number) {
  if (!viewer.value) return
  const n = (viewer.value.index + d + photos.value.length) % photos.value.length
  openViewer(n)
}
function closeViewer() { viewer.value = null }

watch(() => props.requestId, load, { immediate: true })
onMounted(() => {
  // 폴더 선택 지원 속성(표준 타입에 없어 런타임 설정)
  const el = dirInput.value
  if (el) {
    el.setAttribute('webkitdirectory', '')
    el.setAttribute('directory', '')
    el.setAttribute('mozdirectory', '')
  }
})
onBeforeUnmount(() => { for (const k in thumbs) { const u = thumbs[k]; if (u) URL.revokeObjectURL(u) } })
</script>

<style scoped>
.pp-btn { @apply px-2.5 py-1 text-xs rounded border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors; }
.pp-btn-primary { @apply border-blue-500 text-blue-600 hover:bg-blue-50; }
.pp-btn-dark { @apply px-2.5 py-1 text-xs rounded bg-white/10 text-white hover:bg-white/20 border border-white/20; }
</style>
