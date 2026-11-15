<template>
  <div class="markup-editor border rounded-md focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition-colors" :style="minHeight ? { '--me-min-h': minHeight } : undefined">
    <!-- 툴바 -->
    <div class="flex items-center gap-1 px-2 py-1 border-b bg-gray-50 rounded-t-md flex-wrap">
      <!-- 강조 3종 -->
      <button
        type="button"
        @click="toggleMark('critical')"
        :class="markActive('critical') ? 'bg-red-100 text-red-700' : 'hover:bg-gray-200 text-gray-700'"
        class="px-2 py-1 text-xs font-bold rounded transition-colors"
        title="핵심 강조 (빨간 굵게)"
      >
        <span class="text-red-600">A</span>
      </button>
      <button
        type="button"
        @click="toggleMark('warning')"
        :class="markActive('warning') ? 'bg-yellow-100 text-yellow-700' : 'hover:bg-gray-200 text-gray-700'"
        class="px-2 py-1 text-xs font-medium rounded transition-colors"
        title="보조 강조 (노란 하이라이트)"
      >
        <span class="bg-yellow-200 px-1 rounded">A</span>
      </button>
      <button
        type="button"
        @click="toggleMark('spec')"
        :class="markActive('spec') ? 'bg-red-100 text-red-700' : 'hover:bg-gray-200 text-gray-700'"
        class="px-2 py-1 text-xs font-medium rounded transition-colors"
        title="사양 강조 (빨간 밑줄)"
      >
        <span class="underline decoration-red-600 decoration-2">A</span>
      </button>

      <div class="w-px h-4 bg-gray-300 mx-0.5"></div>

      <!-- 단순 굵게 -->
      <button
        type="button"
        @click="toggleBold"
        :class="boldActive ? 'bg-gray-200 text-gray-900' : 'hover:bg-gray-200 text-gray-700'"
        class="px-2 py-1 text-xs font-bold rounded transition-colors"
        title="굵게"
      >
        B
      </button>

      <!-- 색상 픽커 -->
      <div class="relative" v-click-outside="closeColorMenu">
        <button
          type="button"
          @click="colorMenuOpen = !colorMenuOpen"
          :class="anyColorActive ? 'bg-blue-50' : 'hover:bg-gray-200'"
          class="px-2 py-1 text-xs rounded transition-colors flex items-center gap-0.5"
          title="글자색"
        >
          <span :style="{ color: activeColorHex || '#222' }">A</span>
          <svg class="w-2.5 h-2.5 text-gray-500" fill="currentColor" viewBox="0 0 12 12">
            <path d="M3 5l3 3 3-3z" />
          </svg>
        </button>
        <div v-if="colorMenuOpen"
          class="absolute top-full left-0 mt-1 z-10 bg-white border rounded-md shadow-lg p-1.5 grid grid-cols-4 gap-1">
          <button
            v-for="c in COLOR_LIST"
            :key="c.name"
            type="button"
            @click="applyColor(c.name); closeColorMenu()"
            :class="markActive(`color-${c.name}` as any) ? 'ring-2 ring-blue-500' : 'ring-1 ring-gray-200'"
            :style="{ color: c.hex }"
            :title="c.label"
            class="w-7 h-7 rounded text-sm font-bold hover:bg-gray-50 flex items-center justify-center"
          >
            A
          </button>
          <button
            type="button"
            @click="clearColor(); closeColorMenu()"
            class="w-7 h-7 rounded text-xs text-gray-500 hover:bg-gray-50 flex items-center justify-center ring-1 ring-gray-200 col-span-4"
            title="색 해제"
          >
            ✕ 해제
          </button>
        </div>
      </div>

      <div class="w-px h-4 bg-gray-300 mx-0.5"></div>

      <!-- 전체 해제 -->
      <button
        type="button"
        @click="clearMarks"
        class="px-2 py-1 text-xs text-gray-500 hover:bg-gray-200 rounded"
        title="모든 강조 해제"
      >
        ✕
      </button>
      <span class="ml-auto text-[10px] text-gray-400 hidden sm:inline">선택 후 클릭</span>
    </div>

    <!-- 에디터 -->
    <editor-content
      :editor="editor"
      class="px-3 py-2 text-sm focus:outline-none min-h-[2.5rem] cursor-text"
      :class="multiline ? 'whitespace-pre-line' : ''"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount, computed, type DirectiveBinding } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import { Mark, mergeAttributes } from '@tiptap/core'
import { markupToHtml, htmlToMarkup, COLOR_NAMES, type ColorName } from '@/utils/highlightMarkup'

interface Props {
  modelValue: string | null | undefined
  multiline?: boolean
  placeholder?: string
  minHeight?: string  // 편집 영역 최소 높이(예: '260px'). 미지정 시 기본(2.5rem)
  images?: boolean    // 이미지 붙여넣기/드롭 허용(본문 에디터용)
}

const props = withDefaults(defineProps<Props>(), {
  multiline: false,
  images: false,
})

// 붙여넣은 이미지 파일 → 다운스케일 data URL (긴 변 최대 1400px, JPEG 0.85)
function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(reader.error)
    reader.onload = () => {
      const src = reader.result as string
      const img = new window.Image()
      img.onerror = () => resolve(src) // 실패 시 원본 사용
      img.onload = () => {
        const MAX = 1400
        const scale = Math.min(1, MAX / Math.max(img.width, img.height))
        if (scale >= 1 && src.length < 600_000) {
          resolve(src) // 충분히 작으면 원본 유지
          return
        }
        const canvas = document.createElement('canvas')
        canvas.width = Math.round(img.width * scale)
        canvas.height = Math.round(img.height * scale)
        const ctx = canvas.getContext('2d')
        if (!ctx) { resolve(src); return }
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
        // 투명도 있는 PNG는 흰 배경 위에 얹혀도 무방(문서용)
        resolve(canvas.toDataURL('image/jpeg', 0.85))
      }
      img.src = src
    }
    reader.readAsDataURL(file)
  })
}

function insertImageFile(file: File) {
  fileToDataUrl(file).then((src) => {
    editor.value?.chain().focus().insertContent({ type: 'image', attrs: { src } }).run()
  }).catch(() => { /* 무시 */ })
}

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

// ─────────── 색상 팔레트 ───────────
const COLOR_LIST: { name: ColorName; hex: string; label: string }[] = [
  { name: 'red',    hex: '#c00000', label: '빨강' },
  { name: 'orange', hex: '#d97706', label: '주황' },
  { name: 'green',  hex: '#059669', label: '초록' },
  { name: 'blue',   hex: '#2563eb', label: '파랑' },
  { name: 'indigo', hex: '#4338ca', label: '남색' },
  { name: 'purple', hex: '#7c3aed', label: '보라' },
  { name: 'gray',   hex: '#6b7280', label: '회색' },
]
const COLOR_HEX_BY_NAME: Record<ColorName, string> = Object.fromEntries(
  COLOR_LIST.map((c) => [c.name, c.hex])
) as Record<ColorName, string>

// ─────────── 커스텀 강조 마크 3종 (highlight) ───────────
function makeHighlightMark(name: string, className: string) {
  return Mark.create({
    name,
    parseHTML() {
      return [{ tag: 'span', getAttrs: (el) => (el as HTMLElement).className.includes(className) ? {} : false }]
    },
    renderHTML({ HTMLAttributes }) {
      return ['span', mergeAttributes(HTMLAttributes, { class: className }), 0]
    },
  })
}

const HighlightCritical = makeHighlightMark('highlightCritical', 'highlight-critical')
const HighlightWarning = makeHighlightMark('highlightWarning', 'highlight-warning')
const HighlightSpec = makeHighlightMark('highlightSpec', 'highlight-spec')

// ─────────── 색상 마크 7종 (text-color-*) ───────────
function makeColorMark(colorName: ColorName) {
  const className = `text-color-${colorName}`
  return Mark.create({
    name: `color-${colorName}`,
    parseHTML() {
      return [{ tag: 'span', getAttrs: (el) => (el as HTMLElement).className.includes(className) ? {} : false }]
    },
    renderHTML({ HTMLAttributes }) {
      return ['span', mergeAttributes(HTMLAttributes, { class: className }), 0]
    },
  })
}
const colorMarks = COLOR_NAMES.map((c) => makeColorMark(c))

const MARK_BY_HIGHLIGHT: Record<'critical' | 'warning' | 'spec', string> = {
  critical: 'highlightCritical',
  warning: 'highlightWarning',
  spec: 'highlightSpec',
}

const isInternalUpdate = ref(false)

const editor = useEditor({
  content: markupToHtml(props.modelValue),
  extensions: [
    StarterKit.configure({
      heading: false,
      bulletList: false,
      orderedList: false,
      listItem: false,
      blockquote: false,
      codeBlock: false,
      code: false,
      // bold ON (Phase 4 확장)
      italic: false,
      strike: false,
      horizontalRule: false,
      hardBreak: props.multiline ? undefined : false,
    }),
    HighlightCritical,
    HighlightWarning,
    HighlightSpec,
    ...colorMarks,
    ...(props.images ? [Image.configure({ inline: false, allowBase64: true })] : []),
  ],
  onUpdate: ({ editor }) => {
    isInternalUpdate.value = true
    const html = editor.getHTML()
    const markup = htmlToMarkup(html)
    emit('update:modelValue', markup)
    queueMicrotask(() => { isInternalUpdate.value = false })
  },
  editorProps: {
    handleKeyDown: (_view, event) => {
      if (!props.multiline && event.key === 'Enter') {
        event.preventDefault()
        return true
      }
      return false
    },
    handlePaste: (_view, event) => {
      if (!props.images) return false
      const items = event.clipboardData?.items
      if (!items) return false
      for (const item of Array.from(items)) {
        if (item.kind === 'file' && item.type.startsWith('image/')) {
          const file = item.getAsFile()
          if (file) {
            event.preventDefault()
            insertImageFile(file)
            return true
          }
        }
      }
      return false
    },
    handleDrop: (_view, event) => {
      if (!props.images) return false
      const files = (event as DragEvent).dataTransfer?.files
      if (!files || files.length === 0) return false
      const imgFiles = Array.from(files).filter((f) => f.type.startsWith('image/'))
      if (imgFiles.length === 0) return false
      event.preventDefault()
      imgFiles.forEach(insertImageFile)
      return true
    },
  },
})

// 외부 modelValue 변경 시 에디터 동기화
watch(() => props.modelValue, (newValue) => {
  if (isInternalUpdate.value) return
  if (!editor.value) return
  const newHtml = markupToHtml(newValue)
  if (editor.value.getHTML() === newHtml) return
  editor.value.commands.setContent(newHtml, { emitUpdate: false })
})

// ─────────── 액션 ───────────
function toggleMark(kind: 'critical' | 'warning' | 'spec') {
  if (!editor.value) return
  editor.value.chain().focus().toggleMark(MARK_BY_HIGHLIGHT[kind]).run()
}

function markActive(kind: 'critical' | 'warning' | 'spec' | `color-${ColorName}`): boolean {
  if (!editor.value) return false
  if (kind === 'critical' || kind === 'warning' || kind === 'spec') {
    return editor.value.isActive(MARK_BY_HIGHLIGHT[kind])
  }
  return editor.value.isActive(kind)
}

function toggleBold() {
  if (!editor.value) return
  editor.value.chain().focus().toggleBold().run()
}
const boldActive = computed(() => editor.value?.isActive('bold') ?? false)

function applyColor(colorName: ColorName) {
  if (!editor.value) return
  const chain = editor.value.chain().focus()
  // 다른 색상 마크 먼저 제거 (동시 적용 방지)
  for (const c of COLOR_NAMES) {
    if (c !== colorName) chain.unsetMark(`color-${c}`)
  }
  chain.toggleMark(`color-${colorName}`).run()
}

function clearColor() {
  if (!editor.value) return
  const chain = editor.value.chain().focus()
  for (const c of COLOR_NAMES) chain.unsetMark(`color-${c}`)
  chain.run()
}

const anyColorActive = computed(() => {
  if (!editor.value) return false
  return COLOR_NAMES.some((c) => editor.value!.isActive(`color-${c}`))
})

const activeColorHex = computed<string | null>(() => {
  if (!editor.value) return null
  for (const c of COLOR_NAMES) {
    if (editor.value.isActive(`color-${c}`)) return COLOR_HEX_BY_NAME[c]
  }
  return null
})

function clearMarks() {
  if (!editor.value) return
  const chain = editor.value.chain().focus()
  chain
    .unsetMark('highlightCritical')
    .unsetMark('highlightWarning')
    .unsetMark('highlightSpec')
    .unsetMark('bold')
  for (const c of COLOR_NAMES) chain.unsetMark(`color-${c}`)
  chain.run()
}

// ─────────── 색상 메뉴 ───────────
const colorMenuOpen = ref(false)
function closeColorMenu() {
  colorMenuOpen.value = false
}

// click-outside 디렉티브 (인라인 정의)
const vClickOutside = {
  mounted(el: HTMLElement, binding: DirectiveBinding<() => void>) {
    (el as any).__clickOutsideHandler__ = (event: MouseEvent) => {
      if (!el.contains(event.target as Node)) {
        binding.value()
      }
    }
    document.addEventListener('click', (el as any).__clickOutsideHandler__)
  },
  unmounted(el: HTMLElement) {
    document.removeEventListener('click', (el as any).__clickOutsideHandler__)
  },
}

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>

<style>
.markup-editor .ProseMirror {
  outline: none;
  min-height: var(--me-min-h, 1.5rem);
}
.markup-editor .ProseMirror p {
  margin: 0;
}
.markup-editor .ProseMirror img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 4px 0;
}
.markup-editor .ProseMirror img.ProseMirror-selectednode {
  outline: 2px solid #2563eb;
}
.markup-editor .highlight-critical {
  color: #c00;
  font-weight: 700;
}
.markup-editor .highlight-warning {
  background-color: #fff3cd;
  padding: 0 2px;
  border-radius: 2px;
}
.markup-editor .highlight-spec {
  text-decoration: underline;
  text-decoration-color: #c00;
  text-decoration-thickness: 1.5px;
  text-underline-offset: 1px;
}
/* 색상 팔레트 (PDF common.css와 동일) */
.markup-editor .text-color-red    { color: #c00000; }
.markup-editor .text-color-orange { color: #d97706; }
.markup-editor .text-color-green  { color: #059669; }
.markup-editor .text-color-blue   { color: #2563eb; }
.markup-editor .text-color-indigo { color: #4338ca; }
.markup-editor .text-color-purple { color: #7c3aed; }
.markup-editor .text-color-gray   { color: #6b7280; }
</style>
