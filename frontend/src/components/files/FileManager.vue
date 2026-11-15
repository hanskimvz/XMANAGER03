<!--
  파일 관리자 — 첨부파일 추가(끌어다 놓기/선택)와 목록 표시를 담당하는 공용 컴포넌트.
  API 를 모른다: 목록은 items 로 받고, 추가/삭제/다운로드는 이벤트로 부모에 넘긴다.

  <FileManager :items="items" :busy="busy" @add="onAdd" @remove="onRemove" />
-->
<script setup lang="ts">
import { ref } from 'vue'

export interface FileManagerItem {
  key: string | number
  name: string
  size?: number | null
  /** 아직 서버에 올라가지 않은 파일(저장 시 업로드) */
  pending?: boolean
}

const props = withDefaults(
  defineProps<{
    items: FileManagerItem[]
    title?: string
    /** input accept 와 같은 형식 (예: ".pdf,.xlsx,image/*") */
    accept?: string
    multiple?: boolean
    /** 파일 1개당 최대 크기(byte). 미지정 시 제한 없음 */
    maxSize?: number
    /** 업로드 진행 중 등 — 추가/삭제 잠금 */
    busy?: boolean
    /** 목록만 표시(추가/삭제 불가) */
    readonly?: boolean
    /** 파일명 클릭 시 download 이벤트 발생 (pending 항목 제외) */
    downloadable?: boolean
    emptyText?: string
  }>(),
  {
    title: '파일 관리자',
    accept: '',
    multiple: true,
    busy: false,
    readonly: false,
    downloadable: false,
    emptyText: '첨부된 파일이 없습니다.',
  }
)

const emit = defineEmits<{
  add: [files: File[]]
  remove: [item: FileManagerItem]
  download: [item: FileManagerItem]
  /** 형식/크기 제한으로 걸러진 파일 안내 문구 */
  reject: [message: string]
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)

function openDialog() {
  if (props.busy) return
  fileInput.value?.click()
}

function matchesAccept(file: File): boolean {
  const tokens = props.accept.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean)
  if (!tokens.length) return true
  const name = file.name.toLowerCase()
  const type = (file.type || '').toLowerCase()
  return tokens.some((t) => {
    if (t.startsWith('.')) return name.endsWith(t)
    if (t.endsWith('/*')) return type.startsWith(t.slice(0, -1))
    return type === t
  })
}

function addFiles(list: FileList | null | undefined) {
  if (!list || !list.length || props.busy || props.readonly) return
  let files = Array.from(list)
  if (!props.multiple) files = files.slice(0, 1)

  const accepted: File[] = []
  const rejected: string[] = []
  for (const f of files) {
    if (!matchesAccept(f)) rejected.push(`${f.name}: 허용되지 않는 형식`)
    else if (props.maxSize && f.size > props.maxSize) rejected.push(`${f.name}: ${formatSize(props.maxSize)} 초과`)
    else accepted.push(f)
  }
  if (rejected.length) emit('reject', rejected.join('\n'))
  if (accepted.length) emit('add', accepted)
}

function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  addFiles(input.files)
  input.value = '' // 같은 파일을 다시 고를 수 있도록
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  addFiles(e.dataTransfer?.files)
}

function formatSize(n: number): string {
  if (n < 1024) return `${n}B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)}KB`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)}MB`
  return `${(n / 1024 / 1024 / 1024).toFixed(1)}GB`
}
</script>

<template>
  <div class="border border-gray-200 rounded-xl bg-gray-50 overflow-hidden">
    <div class="flex items-center gap-2 px-4 py-2.5 border-b border-gray-200 bg-white">
      <svg class="w-4 h-4 text-gray-700" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M3 6a2 2 0 012-2h4.2a2 2 0 011.4.6L12 6h6a2 2 0 012 2v1H7.3a2 2 0 00-1.9 1.4L3 18V6z" />
        <path d="M7.3 10.5H21a1 1 0 01.95 1.3l-2 6.5a1 1 0 01-.95.7H4.4l2-7.8a1 1 0 01.9-.7z" />
      </svg>
      <span class="text-sm font-semibold text-gray-800">{{ title }}</span>
      <span v-if="items.length" class="text-xs text-gray-400">{{ items.length }}개</span>
    </div>

    <div class="p-4 space-y-3">
      <!-- 추가 영역 -->
      <div
        v-if="!readonly"
        role="button"
        tabindex="0"
        class="flex flex-col items-center gap-1.5 px-4 py-5 border border-dashed rounded-lg bg-white text-center transition-colors"
        :class="[
          isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400',
          busy ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer',
        ]"
        @click="openDialog"
        @keydown.enter.prevent="openDialog"
        @keydown.space.prevent="openDialog"
        @dragover.prevent="!busy && (isDragging = true)"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
      >
        <input ref="fileInput" type="file" class="hidden" :accept="accept || undefined" :multiple="multiple" @change="onPick" />
        <svg class="w-7 h-7 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M7 18a4.5 4.5 0 01-.6-8.96A6 6 0 0118 10.2 3.9 3.9 0 0117.5 18" />
          <path d="M12 19v-7m0 0l-2.8 2.8M12 12l2.8 2.8" />
        </svg>
        <p class="text-sm text-gray-600">
          {{ busy ? '업로드 중...' : '파일을 끌어다 놓거나 클릭하여 추가하세요' }}
        </p>
        <span class="text-sm font-semibold text-blue-600">파일 선택</span>
        <slot name="hint" />
      </div>

      <!-- 목록 -->
      <ul v-if="items.length" class="space-y-1">
        <li
          v-for="item in items"
          :key="item.key"
          class="flex items-center gap-2 px-3 py-1.5 rounded-md border text-sm"
          :class="item.pending ? 'bg-amber-50 border-amber-200' : 'bg-white border-gray-200'"
        >
          <svg class="w-4 h-4 shrink-0 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z" />
            <path d="M14 3v5h5" />
          </svg>
          <button
            v-if="downloadable && !item.pending"
            type="button"
            class="min-w-0 truncate text-left text-blue-600 hover:underline"
            :title="item.name"
            @click="emit('download', item)"
          >
            {{ item.name }}
          </button>
          <span v-else class="min-w-0 truncate text-gray-800" :title="item.name">{{ item.name }}</span>
          <span class="shrink-0 text-xs text-gray-400">
            <template v-if="item.size != null">{{ formatSize(item.size) }}</template>
            <template v-if="item.pending">{{ item.size != null ? ' · ' : '' }}업로드 대기</template>
          </span>
          <button
            v-if="!readonly"
            type="button"
            class="ml-auto shrink-0 text-xs text-red-500 hover:underline disabled:opacity-50"
            :disabled="busy"
            @click="emit('remove', item)"
          >
            {{ item.pending ? '제거' : '삭제' }}
          </button>
        </li>
      </ul>
      <p v-else class="py-2 text-center text-sm text-gray-400">{{ emptyText }}</p>
    </div>
  </div>
</template>
