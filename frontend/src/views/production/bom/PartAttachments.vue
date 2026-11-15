<template>
  <div class="pa">
    <div class="pa-head">
      <span class="pa-title">📎 {{ partLabel }} 첨부</span>
      <div class="pa-actions">
        <select v-model="uploadKind" class="pa-kind">
          <option value="DRAWING">도면</option>
          <option value="SPEC">스펙시트</option>
          <option value="PHOTO">사진</option>
          <option value="OTHER">기타</option>
        </select>
        <button class="pa-btn pa-btn-p" :disabled="uploading" @click="fileInput?.click()">
          {{ uploading ? '업로드 중…' : '⬆ 업로드' }}
        </button>
        <input ref="fileInput" type="file" multiple class="hidden"
          accept=".png,.jpg,.jpeg,.gif,.webp,.bmp,.pdf,.xlsx,.xls,.csv,.doc,.docx,.hwp,.hwpx,.ppt,.pptx,.txt,.zip,.step,.stp,.dwg,.dxf,.igs,.iges"
          @change="onPick" />
      </div>
    </div>
    <div class="pa-drop" :class="{ over: dragOver }"
      @dragover.prevent="dragOver = true" @dragleave.prevent="dragOver = false" @drop.prevent="onDrop">
      <div v-if="loading" class="pa-empty">불러오는 중…</div>
      <div v-else-if="items.length === 0" class="pa-empty">첨부 없음 — 도면·스펙시트를 끌어다 놓거나 업로드하세요.</div>
      <ul v-else class="pa-list">
        <li v-for="a in items" :key="a.id" class="pa-item">
          <span class="pa-badge" :class="kindCls(a.kind)">{{ kindLabel(a.kind) }}</span>
          <button class="pa-name" :title="a.filename" @click="open(a)">{{ icon(a) }} {{ a.filename }}</button>
          <span class="pa-size">{{ sizeText(a.size) }}</span>
          <button class="pa-x" title="다운로드" @click="download(a)">⬇</button>
          <button class="pa-x pa-del" title="삭제" @click="remove(a)">✕</button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { partApi, type PartAttachment } from '@/api/parts'

const props = defineProps<{ partId: number; partLabel?: string }>()
const emit = defineEmits<{ (e: 'changed', count: number): void }>()

const items = ref<PartAttachment[]>([])
const loading = ref(false)
const uploading = ref(false)
const dragOver = ref(false)
const uploadKind = ref('DRAWING')
const fileInput = ref<HTMLInputElement | null>(null)

const IMG = /\.(png|jpe?g|gif|webp|bmp)$/i
function icon(a: PartAttachment) {
  const n = (a.filename || '').toLowerCase()
  if (IMG.test(n)) return '🖼'
  if (/\.pdf$/.test(n)) return '📕'
  if (/\.(xlsx?|csv)$/.test(n)) return '📊'
  if (/\.(step|stp|dwg|dxf|igs|iges)$/.test(n)) return '📐'
  return '📎'
}
function kindLabel(k: string) { return ({ DRAWING: '도면', SPEC: '스펙', PHOTO: '사진', OTHER: '기타' } as any)[k] || '기타' }
function kindCls(k: string) { return ({ DRAWING: 'k-d', SPEC: 'k-s', PHOTO: 'k-p', OTHER: 'k-o' } as any)[k] || 'k-o' }
function sizeText(b?: number | null) { if (!b && b !== 0) return ''; if (b! < 1024) return `${b}B`; if (b! < 1048576) return `${(b! / 1024).toFixed(0)}KB`; return `${(b! / 1048576).toFixed(1)}MB` }

async function load() {
  loading.value = true
  try { items.value = (await partApi.listAttachments(props.partId)).data } catch { items.value = [] }
  finally { loading.value = false; emit('changed', items.value.length) }
}
async function uploadFiles(files: File[]) {
  if (!files.length) return
  uploading.value = true
  try {
    for (const f of files) await partApi.uploadAttachment(props.partId, f, uploadKind.value)
    await load()
  } catch (e: any) { alert(e?.response?.data?.detail || '업로드 실패') }
  finally { uploading.value = false }
}
function onPick(e: Event) { const t = e.target as HTMLInputElement; const fs = Array.from(t.files || []); t.value = ''; uploadFiles(fs) }
function onDrop(e: DragEvent) { dragOver.value = false; uploadFiles(Array.from(e.dataTransfer?.files || [])) }
function open(a: PartAttachment) {
  const n = (a.filename || '').toLowerCase()
  if (IMG.test(n) || /\.pdf$/.test(n)) window.open(partApi.attachmentPreviewUrl(a.id), '_blank')
  else download(a)
}
async function download(a: PartAttachment) { try { await partApi.downloadAttachment(a.id, a.filename) } catch { alert('다운로드 실패') } }
async function remove(a: PartAttachment) {
  if (!confirm(`'${a.filename}' 삭제?`)) return
  try { await partApi.deleteAttachment(a.id); await load() } catch { alert('삭제 실패') }
}
watch(() => props.partId, load, { immediate: true })
</script>

<style scoped>
.pa { font-size: 13px; }
.pa-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.pa-title { font-weight: 700; color: #1f2937; }
.pa-actions { display: flex; gap: 6px; align-items: center; }
.pa-kind { border: 1px solid #d1d5db; border-radius: 6px; font-size: 12px; padding: 3px 6px; }
.pa-btn { border: 1px solid #d1d5db; border-radius: 6px; padding: 4px 10px; font-size: 12px; background: #fff; cursor: pointer; }
.pa-btn-p { border-color: #2563eb; color: #2563eb; }
.pa-drop { border: 1.5px dashed #d1d5db; border-radius: 10px; padding: 10px; }
.pa-drop.over { border-color: #2563eb; background: #eff6ff; }
.pa-empty { text-align: center; color: #9ca3af; font-size: 12.5px; padding: 12px 0; }
.pa-list { list-style: none; margin: 0; padding: 0; }
.pa-item { display: flex; align-items: center; gap: 8px; padding: 5px 4px; border-bottom: 1px solid #f3f4f6; }
.pa-badge { font-size: 10px; font-weight: 700; border-radius: 5px; padding: 1px 6px; }
.k-d { background: #e0edff; color: #1d4ed8; } .k-s { background: #e7f6ec; color: #15803d; } .k-p { background: #fdeede; color: #b45309; } .k-o { background: #eef1f5; color: #6b7280; }
.pa-name { flex: 1; min-width: 0; text-align: left; background: none; border: none; color: #374151; cursor: pointer; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pa-name:hover { color: #2563eb; }
.pa-size { font-size: 11px; color: #9ca3af; }
.pa-x { border: none; background: none; cursor: pointer; color: #6b7280; padding: 2px 5px; }
.pa-del:hover { color: #dc2626; }
.hidden { display: none; }
</style>
