<template>
  <div class="cfb">
    <!-- 비활성(경로 미설정) 안내 -->
    <div v-if="notEnabled" class="text-center py-8 text-gray-400 text-sm bg-gray-50 rounded">
      파일 연동이 비활성화되어 있습니다. (서버 NEXTCLOUD_BASE_PATH 미설정)
    </div>

    <template v-else>
      <!-- 상단 바: 브레드크럼 + 액션 -->
      <div class="flex items-center justify-between gap-2 mb-3 flex-wrap">
        <nav class="flex items-center gap-1 text-sm text-gray-600 flex-wrap min-w-0">
          <template v-for="(c, i) in crumbs" :key="c.path">
            <button
              class="hover:text-blue-600 hover:underline truncate max-w-[180px]"
              :class="i === crumbs.length - 1 ? 'font-semibold text-gray-800' : ''"
              :title="c.label"
              @click="navigateTo(c.path)"
            >{{ i === 0 ? '🗂 ' + c.label : c.label }}</button>
            <span v-if="i < crumbs.length - 1" class="text-gray-300">/</span>
          </template>
        </nav>
        <div class="flex items-center gap-1.5 shrink-0">
          <button class="cfb-btn" :disabled="loading" @click="openPicker" title="사람이 만든 기존(레거시) 폴더를 이 거래처/주문에 연결">🔗 기존 폴더 연결</button>
          <button class="cfb-btn" :disabled="loading" @click="refresh" title="새로고침">↻</button>
          <button class="cfb-btn" :disabled="loading || uploading" @click="promptMkdir">＋ 폴더</button>
          <button class="cfb-btn cfb-btn-primary" :disabled="loading || uploading" @click="fileInput?.click()">
            {{ uploading ? '업로드 중…' : '⬆ 업로드' }}
          </button>
          <input ref="fileInput" type="file" multiple class="hidden" @change="onPickFiles" />
        </div>
      </div>

      <!-- 수동 링크(레거시) 상태 배지 -->
      <div v-if="rootPath && managed === false" class="flex items-center gap-2 mb-3 text-xs bg-amber-50 border border-amber-200 text-amber-700 rounded px-3 py-1.5">
        🔗 기존(레거시) 폴더에 연결됨: <span class="font-mono truncate">{{ rootPath }}</span>
        <button class="ml-auto cfb-btn" :disabled="loading" @click="unlinkFolder">연결 해제</button>
      </div>

      <!-- 드롭존 + 목록 -->
      <div
        class="cfb-drop border rounded-lg"
        :class="dragOver ? 'border-blue-400 bg-blue-50/60' : 'border-gray-200'"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
      >
        <div v-if="loading" class="text-center py-8 text-gray-400 text-sm">불러오는 중…</div>
        <div v-else-if="error" class="text-center py-8 text-red-400 text-sm">{{ error }}</div>
        <div v-else-if="items.length === 0" class="text-center py-10 text-gray-400 text-sm">
          이 폴더는 비어 있습니다.
          <div class="text-xs text-gray-300 mt-1">파일을 이 영역에 끌어다 놓거나 붙여넣기(Ctrl+V) 하세요.</div>
        </div>
        <ul v-else class="divide-y divide-gray-100">
          <li
            v-for="it in items"
            :key="it.name"
            class="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 group"
          >
            <!-- 아이콘/이름 -->
            <button
              v-if="it.is_dir"
              class="flex items-center gap-2 min-w-0 flex-1 text-left"
              @click="openFolder(it)"
            >
              <span class="text-lg leading-none">📁</span>
              <span class="truncate text-sm text-gray-800">{{ it.name }}</span>
            </button>
            <button
              v-else
              class="flex items-center gap-2 min-w-0 flex-1 text-left"
              @click="canPreview(it.name) ? preview(it) : download(it)"
              :title="canPreview(it.name) ? '미리보기' : '다운로드'"
            >
              <span class="text-lg leading-none">{{ fileIcon(it.name) }}</span>
              <span class="truncate text-sm text-gray-700">{{ it.name }}</span>
            </button>

            <!-- 메타 -->
            <span v-if="!it.is_dir" class="text-xs text-gray-400 shrink-0 w-20 text-right tabular-nums">{{ humanSize(it.size) }}</span>
            <span class="text-xs text-gray-400 shrink-0 w-28 text-right hidden sm:inline">{{ fmtDate(it.mtime) }}</span>

            <!-- 파일 액션 -->
            <span v-if="!it.is_dir" class="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
              <button v-if="canPreview(it.name)" class="cfb-icon" title="미리보기" @click.stop="preview(it)">👁</button>
              <button class="cfb-icon" title="다운로드" @click.stop="download(it)">⬇</button>
              <button class="cfb-icon cfb-icon-del" title="삭제" @click.stop="remove(it)">✕</button>
            </span>
            <span v-else class="w-[64px] shrink-0"></span>
          </li>
        </ul>
      </div>
      <p class="text-xs text-gray-400 mt-2">
        Nextcloud 동기화 폴더를 직접 탐색합니다. 업로드/삭제는 즉시 동기화되며, 원본은 Nextcloud에 저장됩니다.
      </p>
    </template>

    <!-- 기존(레거시) 폴더 선택기 -->
    <Teleport to="body">
      <div v-if="pickerOpen" class="fixed inset-0 z-[70] bg-black/50 flex items-center justify-center p-4" @click.self="pickerOpen = false">
        <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden">
          <div class="px-5 py-3 border-b">
            <div class="text-sm font-semibold text-gray-800">기존 폴더 연결</div>
            <div class="text-xs text-gray-400 mt-0.5">사람이 만든 기존 폴더(예: 수출/·국내판매/)로 들어가 <b>연결할 폴더에서</b> "이 폴더 선택"을 누르세요.</div>
          </div>
          <!-- 브레드크럼 -->
          <div class="px-5 py-2 border-b flex items-center gap-1 text-sm text-gray-600 flex-wrap">
            <button class="hover:text-blue-600 hover:underline" @click="pickerNavigate('')">🗂 루트</button>
            <template v-for="(seg, i) in pickerSegs" :key="i">
              <span class="text-gray-300">/</span>
              <button class="hover:text-blue-600 hover:underline truncate max-w-[160px]"
                :class="i === pickerSegs.length - 1 ? 'font-semibold text-gray-800' : ''"
                @click="pickerNavigate(pickerSegs.slice(0, i + 1).join('/'))">{{ seg }}</button>
            </template>
          </div>
          <!-- 폴더 목록 -->
          <div class="flex-1 overflow-auto min-h-[240px]">
            <div v-if="pickerLoading" class="text-center py-10 text-gray-400 text-sm">불러오는 중…</div>
            <div v-else-if="pickerFolders.length === 0" class="text-center py-10 text-gray-400 text-sm">하위 폴더가 없습니다.</div>
            <ul v-else class="divide-y divide-gray-100">
              <li v-for="d in pickerFolders" :key="d.name">
                <button class="w-full flex items-center gap-2 px-5 py-2 hover:bg-gray-50 text-left"
                  @click="pickerOpenFolder(d.name)">
                  <span class="text-lg leading-none">📁</span>
                  <span class="truncate text-sm text-gray-800">{{ d.name }}</span>
                  <span class="ml-auto text-xs text-gray-300">열기 ›</span>
                </button>
              </li>
            </ul>
          </div>
          <div class="px-5 py-3 border-t bg-gray-50 flex items-center justify-between gap-2">
            <div class="text-xs text-gray-500 truncate">
              현재: <span class="font-mono">{{ pickerPath || '(루트)' }}</span>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <button class="cfb-btn" @click="pickerOpen = false">취소</button>
              <button class="cfb-btn cfb-btn-primary" :disabled="!pickerPath || linking" @click="confirmLink">
                {{ linking ? '연결 중…' : '이 폴더 선택' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 미리보기 오버레이 -->
    <Teleport to="body">
      <div
        v-if="previewState"
        class="fixed inset-0 z-[70] bg-black/70 flex items-center justify-center p-4"
        @click.self="closePreview"
      >
        <div class="bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden">
          <div class="flex items-center justify-between px-4 py-2 border-b">
            <span class="text-sm font-medium text-gray-700 truncate">{{ previewState.name }}</span>
            <div class="flex items-center gap-2">
              <button class="cfb-btn" @click="download(previewState.item)">⬇ 다운로드</button>
              <button class="cfb-btn" @click="closePreview">닫기 ✕</button>
            </div>
          </div>
          <div class="flex-1 overflow-auto bg-gray-100 flex items-center justify-center">
            <img v-if="previewState.kind === 'image'" :src="previewState.url" class="max-w-full max-h-[82vh] object-contain" />
            <iframe v-else :src="previewState.url" class="w-full h-[82vh] bg-white" />
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { cloudFilesApi, type CloudItem } from '@/api/cloudFiles'

interface Props {
  scope: 'customer' | 'order'
  customerId?: number | null
  documentId?: number | null
  active: boolean
}
const props = defineProps<Props>()

const rootPath = ref('')
const currentPath = ref('')
const items = ref<CloudItem[]>([])
const managed = ref<boolean | undefined>(undefined) // false=수동 링크(레거시)
const loading = ref(false)
const uploading = ref(false)
const error = ref<string | null>(null)
const notEnabled = ref(false)
const dragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const loadedKey = ref<string>('') // 중복 로드 방지 (scope+id)

// ── 브레드크럼 ──
const relSegs = computed(() => {
  const r = rootPath.value
  const c = currentPath.value
  if (!r || c === r) return [] as string[]
  const rest = c.startsWith(r + '/') ? c.slice(r.length + 1) : ''
  return rest ? rest.split('/') : []
})
const crumbs = computed(() => {
  const rootLabel = rootPath.value.split('/').pop() || '파일 루트'
  const list = [{ label: rootLabel, path: rootPath.value }]
  relSegs.value.forEach((seg, i) => {
    list.push({ label: seg, path: rootPath.value + '/' + relSegs.value.slice(0, i + 1).join('/') })
  })
  return list
})

// ── 로드 ──
const entryKey = () =>
  props.scope === 'customer' ? `c:${props.customerId ?? ''}` : `o:${props.documentId ?? ''}`

async function loadEntry() {
  const key = entryKey()
  if ((props.scope === 'customer' && !props.customerId) || (props.scope === 'order' && !props.documentId)) return
  loading.value = true
  error.value = null
  notEnabled.value = false
  try {
    const res =
      props.scope === 'customer'
        ? await cloudFilesApi.entryCustomer(props.customerId as number)
        : await cloudFilesApi.entryOrder(props.documentId as number)
    rootPath.value = res.data.path
    currentPath.value = res.data.path
    items.value = res.data.items || []
    managed.value = res.data.managed
    loadedKey.value = key
  } catch (e: any) {
    if (e?.response?.status === 503) {
      notEnabled.value = true
    } else {
      error.value = e?.response?.data?.detail || '폴더를 불러오지 못했습니다.'
    }
  } finally {
    loading.value = false
  }
}

async function listPath(path: string) {
  loading.value = true
  error.value = null
  try {
    const res = await cloudFilesApi.list(path)
    currentPath.value = res.data.path
    items.value = res.data.items || []
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '폴더를 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

const refresh = () => (currentPath.value === rootPath.value ? loadEntry() : listPath(currentPath.value))
const openFolder = (it: CloudItem) => listPath(currentPath.value + '/' + it.name)
const navigateTo = (path: string) => (path === currentPath.value ? undefined : listPath(path))

// ── 업로드 ──
async function uploadFiles(files: File[]) {
  if (!files.length || !currentPath.value) return
  uploading.value = true
  try {
    for (const f of files) {
      await cloudFilesApi.upload(currentPath.value, f)
    }
    await listPath(currentPath.value)
  } catch (e: any) {
    alert(e?.response?.data?.detail || '업로드에 실패했습니다.')
  } finally {
    uploading.value = false
  }
}
function onPickFiles(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  uploadFiles(files)
}
function onDrop(e: DragEvent) {
  dragOver.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length) uploadFiles(files)
}
function onPaste(e: ClipboardEvent) {
  if (!props.active) return
  const files: File[] = []
  const items2 = e.clipboardData?.items
  if (items2) {
    for (const it of Array.from(items2)) {
      if (it.kind === 'file') {
        const f = it.getAsFile()
        if (f) files.push(f)
      }
    }
  }
  if (files.length) {
    e.preventDefault()
    uploadFiles(files)
  }
}

// ── 폴더 생성 ──
async function promptMkdir() {
  const name = prompt('새 폴더 이름을 입력하세요.')?.trim()
  if (!name) return
  try {
    await cloudFilesApi.mkdir(currentPath.value, name)
    await listPath(currentPath.value)
  } catch (e: any) {
    alert(e?.response?.data?.detail || '폴더 생성에 실패했습니다.')
  }
}

// ── 다운로드/삭제 ──
async function download(it: CloudItem) {
  try {
    await cloudFilesApi.download(currentPath.value + '/' + it.name, it.name)
  } catch {
    alert('다운로드에 실패했습니다.')
  }
}
async function remove(it: CloudItem) {
  if (!confirm(`'${it.name}' 파일을 삭제하시겠습니까? (Nextcloud 원본도 삭제됩니다)`)) return
  try {
    await cloudFilesApi.remove(currentPath.value + '/' + it.name)
    await listPath(currentPath.value)
  } catch (e: any) {
    alert(e?.response?.data?.detail || '삭제에 실패했습니다.')
  }
}

// ── 기존(레거시) 폴더 연결 (Phase 2a) ──
const entityId = computed(() => (props.scope === 'customer' ? props.customerId : props.documentId) ?? null)
const pickerOpen = ref(false)
const pickerPath = ref('')
const pickerItems = ref<CloudItem[]>([])
const pickerLoading = ref(false)
const linking = ref(false)
const pickerFolders = computed(() => pickerItems.value.filter((i) => i.is_dir))
const pickerSegs = computed(() => (pickerPath.value ? pickerPath.value.split('/') : []))

async function loadPicker() {
  pickerLoading.value = true
  try {
    const res = await cloudFilesApi.list(pickerPath.value)
    pickerPath.value = res.data.path
    pickerItems.value = res.data.items || []
  } catch (e: any) {
    alert(e?.response?.data?.detail || '폴더를 불러오지 못했습니다.')
  } finally {
    pickerLoading.value = false
  }
}
function openPicker() {
  pickerPath.value = ''
  pickerItems.value = []
  pickerOpen.value = true
  loadPicker()
}
function pickerOpenFolder(name: string) {
  pickerPath.value = pickerPath.value ? `${pickerPath.value}/${name}` : name
  loadPicker()
}
function pickerNavigate(path: string) {
  pickerPath.value = path
  loadPicker()
}
async function confirmLink() {
  if (!pickerPath.value || entityId.value == null) return
  if (!confirm(`이 거래처/주문의 파일함을 아래 폴더로 연결할까요?\n\n${pickerPath.value}\n\n(이후 파일함이 이 폴더를 가리킵니다)`)) return
  linking.value = true
  try {
    const res = await cloudFilesApi.link(props.scope, entityId.value, pickerPath.value)
    rootPath.value = res.data.path
    currentPath.value = res.data.path
    items.value = res.data.items || []
    managed.value = res.data.managed
    pickerOpen.value = false
  } catch (e: any) {
    alert(e?.response?.data?.detail || '연결에 실패했습니다.')
  } finally {
    linking.value = false
  }
}
async function unlinkFolder() {
  if (entityId.value == null) return
  if (!confirm('기존 폴더 연결을 해제할까요?\n다음 진입 시 X-Manager 전용 폴더(자동)로 돌아갑니다. (레거시 폴더/파일은 삭제되지 않습니다)')) return
  loading.value = true
  try {
    await cloudFilesApi.unlink(props.scope, entityId.value)
    await loadEntry()
  } catch (e: any) {
    alert(e?.response?.data?.detail || '연결 해제에 실패했습니다.')
  } finally {
    loading.value = false
  }
}

// ── 미리보기 ──
type PreviewState = { name: string; url: string; kind: 'image' | 'pdf'; item: CloudItem }
const previewState = ref<PreviewState | null>(null)
async function preview(it: CloudItem) {
  try {
    const { url } = await cloudFilesApi.previewBlobUrl(currentPath.value + '/' + it.name)
    previewState.value = { name: it.name, url, kind: isImage(it.name) ? 'image' : 'pdf', item: it }
  } catch {
    alert('미리보기를 불러오지 못했습니다.')
  }
}
function closePreview() {
  if (previewState.value) URL.revokeObjectURL(previewState.value.url)
  previewState.value = null
}

// ── 유틸 ──
const isImage = (n: string) => /\.(png|jpe?g|gif|webp|bmp|svg|heic)$/i.test(n)
const isPdf = (n: string) => /\.pdf$/i.test(n)
const canPreview = (n: string) => isImage(n) || isPdf(n)
function fileIcon(n: string): string {
  if (isImage(n)) return '🖼'
  if (isPdf(n)) return '📕'
  if (/\.(xlsx?|csv)$/i.test(n)) return '📊'
  if (/\.(docx?)$/i.test(n)) return '📝'
  if (/\.(pptx?)$/i.test(n)) return '📑'
  if (/\.(zip|7z|rar|tar|gz)$/i.test(n)) return '🗜'
  if (/\.(dwg|dxf|step|stp|igs|iges)$/i.test(n)) return '📐'
  return '📄'
}
function humanSize(bytes: number): string {
  if (!bytes) return '0 B'
  const u = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${u[i]}`
}
function fmtDate(epochSec: number): string {
  if (!epochSec) return ''
  const d = new Date(epochSec * 1000)
  const p = (x: number) => String(x).padStart(2, '0')
  return `${String(d.getFullYear()).slice(2)}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

// ── 활성화/엔티티 변경 시 로드 ──
watch(
  () => [props.active, props.customerId, props.documentId] as const,
  () => {
    if (!props.active) return
    if (loadedKey.value !== entryKey()) {
      rootPath.value = ''
      currentPath.value = ''
      items.value = []
      loadEntry()
    }
  },
  { immediate: true },
)

// 붙여넣기 업로드 (활성 탭에서만 동작 — 파일이 있을 때만 처리)
document.addEventListener('paste', onPaste)
onBeforeUnmount(() => {
  document.removeEventListener('paste', onPaste)
  if (previewState.value) URL.revokeObjectURL(previewState.value.url)
})
</script>

<style scoped>
.cfb-btn {
  @apply px-2.5 py-1 text-xs rounded border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors;
}
.cfb-btn-primary {
  @apply border-blue-500 text-blue-600 hover:bg-blue-50;
}
.cfb-icon {
  @apply px-1.5 py-0.5 text-sm rounded hover:bg-gray-200 text-gray-500;
}
.cfb-icon-del {
  @apply hover:bg-red-100 hover:text-red-500;
}
.cfb-drop {
  min-height: 160px;
}
</style>
