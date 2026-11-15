<template>
  <div class="rich-text-editor">
    <div v-if="editor" class="editor-toolbar">
      <div class="toolbar-group">
        <div class="color-picker-wrap">
          <button
            type="button"
            class="toolbar-btn color-btn"
            :class="{ active: !!editor.getAttributes('textStyle').color }"
            title="글자색"
            @mousedown.prevent
            @click="textColorInput?.click()"
          >
            <span class="color-icon" :style="{ color: currentTextColor }">A</span>
          </button>
          <input
            ref="textColorInput"
            type="color"
            class="hidden-input"
            tabindex="-1"
            :value="currentTextColor"
            @input="setTextColor(($event.target as HTMLInputElement).value)"
          />
        </div>

        <div class="color-picker-wrap">
          <button
            type="button"
            class="toolbar-btn highlight-btn"
            :class="{ active: editor.isActive('highlight') }"
            title="형광펜"
            @mousedown.prevent
            @click="highlightColorInput?.click()"
          >
            <span class="highlight-icon" :style="{ backgroundColor: currentHighlightColor }">A</span>
          </button>
          <input
            ref="highlightColorInput"
            type="color"
            class="hidden-input"
            tabindex="-1"
            :value="currentHighlightColor"
            @input="setHighlightColor(($event.target as HTMLInputElement).value)"
          />
        </div>

        <button
          type="button"
          class="toolbar-btn"
          :class="{ active: editor.isActive('underline') }"
          title="밑줄"
          @mousedown.prevent
          @click="editor.chain().focus().toggleUnderline().run()"
        >
          <span class="underline-icon">A</span>
        </button>
      </div>

      <span class="toolbar-divider" aria-hidden="true"></span>

      <div class="toolbar-group">
        <button
          type="button"
          class="toolbar-btn"
          :class="{ active: editor.isActive('bold') }"
          title="굵게"
          @mousedown.prevent
          @click="editor.chain().focus().toggleBold().run()"
        >
          <strong>B</strong>
        </button>

        <select
          class="font-size-select"
          :value="currentFontSize"
          title="글자 크기"
          @mousedown.stop
          @change="setFontSize(($event.target as HTMLSelectElement).value)"
        >
          <option value="">크기</option>
          <option v-for="size in FONT_SIZE_OPTIONS" :key="size.value" :value="size.value">
            {{ size.label }}px
          </option>
        </select>
      </div>

      <span class="toolbar-divider" aria-hidden="true"></span>

      <div class="toolbar-group">
        <button
          type="button"
          class="toolbar-btn"
          title="서식 지우기"
          @mousedown.prevent
          @click="clearFormatting"
        >
          <svg class="toolbar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>

        <button
          type="button"
          class="toolbar-btn"
          title="이미지 첨부"
          @mousedown.prevent
          @click="imageInput?.click()"
        >
          <svg class="toolbar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <rect x="3" y="4" width="18" height="16" rx="2" />
            <circle cx="8.5" cy="9.5" r="1.5" />
            <path d="M21 16l-5-5L5 20" />
          </svg>
        </button>
        <input
          ref="imageInput"
          type="file"
          accept="image/*"
          class="hidden-input"
          tabindex="-1"
          @change="handleImageSelect"
        />
      </div>

      <span class="toolbar-hint">선택 후 클릭</span>
    </div>

    <EditorContent :editor="editor" class="editor-content" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import {
  createEditorExtensions,
  FONT_SIZE_OPTIONS,
  isEmptyEditorHtml,
  MAX_EDITOR_IMAGE_SIZE,
  readImageAsDataUrl,
} from './editorConfig'

const props = withDefaults(
  defineProps<{
    modelValue?: string | null
    placeholder?: string
    minHeight?: string
    /** 이전 에디터로 작성된 제목/목록/인용/링크를 편집 시 보존 (editorConfig 참고) */
    preserveLegacyBlocks?: boolean
  }>(),
  {
    modelValue: '',
    placeholder: '내용을 입력하세요',
    minHeight: '16rem',
    preserveLegacyBlocks: false,
  }
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const textColorInput = ref<HTMLInputElement | null>(null)
const highlightColorInput = ref<HTMLInputElement | null>(null)
const imageInput = ref<HTMLInputElement | null>(null)
const isInternalUpdate = ref(false)

const editor = useEditor({
  content: props.modelValue || '',
  editable: true,
  autofocus: false,
  editorProps: {
    attributes: {
      class: 'tiptap',
    },
  },
  extensions: createEditorExtensions({
    placeholder: props.placeholder,
    preserveLegacyBlocks: props.preserveLegacyBlocks,
  }),
  onUpdate: ({ editor: currentEditor }) => {
    const html = currentEditor.getHTML()
    isInternalUpdate.value = true
    emit('update:modelValue', isEmptyEditorHtml(html) ? '' : html)
    nextTick(() => {
      isInternalUpdate.value = false
    })
  },
})

// 외부 값 변경(수정 모달 열기 등) 반영
watch(
  () => props.modelValue,
  (value) => {
    if (isInternalUpdate.value || !editor.value) return

    const nextValue = value || ''
    const currentHtml = editor.value.getHTML()

    if (nextValue === currentHtml) return
    if (!nextValue && isEmptyEditorHtml(currentHtml)) return

    editor.value.commands.setContent(nextValue, { emitUpdate: false })
  }
)

const currentTextColor = computed<string>(() => {
  return editor.value?.getAttributes('textStyle').color || '#111827'
})

const currentHighlightColor = computed<string>(() => {
  return editor.value?.getAttributes('highlight').color || '#fef08a'
})

const currentFontSize = computed<string>(() => editor.value?.getAttributes('textStyle').fontSize || '')

const setTextColor = (color: string) => {
  editor.value?.chain().focus().setColor(color).run()
}

// 색을 고르는 동작이므로 toggle이 아닌 set — 같은 색을 다시 골라도 꺼지지 않는다
const setHighlightColor = (color: string) => {
  editor.value?.chain().focus().setHighlight({ color }).run()
}

const setFontSize = (fontSize: string) => {
  if (!editor.value) return
  if (!fontSize) {
    editor.value.chain().focus().unsetFontSize().run()
    return
  }
  editor.value.chain().focus().setFontSize(fontSize).run()
}

const clearFormatting = () => {
  editor.value?.chain().focus().unsetAllMarks().clearNodes().run()
}

const handleImageSelect = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !editor.value) return

  if (!file.type.startsWith('image/')) {
    window.alert('이미지 파일만 첨부할 수 있습니다.')
    return
  }
  if (file.size > MAX_EDITOR_IMAGE_SIZE) {
    window.alert('이미지는 2MB 이하만 첨부할 수 있습니다.')
    return
  }

  try {
    const dataUrl = await readImageAsDataUrl(file)
    editor.value.chain().focus().setImage({ src: dataUrl, alt: file.name }).run()
  } catch (error) {
    window.alert((error as Error).message || '이미지 첨부에 실패했습니다.')
  }
}
</script>

<style scoped>
.rich-text-editor {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.45rem 0.65rem;
  border-bottom: 1px solid #e5e7eb;
  background: #fafafa;
  flex-wrap: wrap;
}

.toolbar-group {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
}

.toolbar-divider {
  width: 1px;
  height: 1.25rem;
  background: #d1d5db;
  margin: 0 0.15rem;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #374151;
  cursor: pointer;
  font-size: 0.95rem;
}

.toolbar-btn:hover,
.toolbar-btn.active {
  background: #eef2ff;
  color: #1d4ed8;
}

.toolbar-icon {
  width: 1rem;
  height: 1rem;
}

.color-picker-wrap {
  position: relative;
}

.color-icon {
  font-weight: 700;
  line-height: 1;
}

.highlight-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.15rem;
  height: 1.15rem;
  border-radius: 3px;
  font-weight: 700;
  color: #111827;
  line-height: 1;
}

.underline-icon {
  text-decoration: underline;
  text-decoration-color: #dc2626;
  text-underline-offset: 2px;
  font-weight: 600;
}

.font-size-select {
  min-width: 3.6rem;
  height: 2rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  font-size: 0.85rem;
  padding: 0 0.25rem;
  cursor: pointer;
}

.toolbar-hint {
  margin-left: auto;
  font-size: 0.78rem;
  color: #9ca3af;
  white-space: nowrap;
}

/* display:none 이면 일부 브라우저에서 색상 픽커가 버튼 위치에 뜨지 않아 시각적으로만 숨긴다 */
.hidden-input {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 0;
  height: 0;
  padding: 0;
  border: 0;
  opacity: 0;
  pointer-events: none;
}

.editor-content {
  min-height: v-bind(minHeight);
  cursor: text;
}

.editor-content :deep(.tiptap) {
  min-height: v-bind(minHeight);
  padding: 0.85rem 0.9rem;
  outline: none;
  font-size: 0.95rem;
  line-height: 1.65;
  color: #111827;
  cursor: text;
}

.editor-content :deep(.tiptap p) {
  margin: 0 0 0.75rem;
}

.editor-content :deep(.tiptap p:last-child) {
  margin-bottom: 0;
}

/* 이전 에디터로 작성된 블록(preserveLegacyBlocks) — Tailwind preflight 리셋 복원 */
.editor-content :deep(.tiptap h1),
.editor-content :deep(.tiptap h2),
.editor-content :deep(.tiptap h3) {
  margin: 0 0 0.75rem;
  font-size: 1.15em;
  font-weight: 700;
}

.editor-content :deep(.tiptap ul) {
  list-style: disc;
  padding-left: 1.4em;
  margin: 0 0 0.75rem;
}

.editor-content :deep(.tiptap ol) {
  list-style: decimal;
  padding-left: 1.4em;
  margin: 0 0 0.75rem;
}

.editor-content :deep(.tiptap li p) {
  margin: 0;
}

.editor-content :deep(.tiptap blockquote) {
  margin: 0 0 0.75rem;
  padding-left: 0.75rem;
  border-left: 3px solid #d1d5db;
  color: #4b5563;
}

.editor-content :deep(.tiptap a) {
  color: #2563eb;
  text-decoration: underline;
}

.editor-content :deep(.tiptap mark) {
  padding: 0 2px;
  border-radius: 2px;
  color: inherit;
}

.editor-content :deep(.tiptap img) {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  margin: 0.5rem 0;
}

.editor-content :deep(.tiptap img.ProseMirror-selectednode) {
  outline: 2px solid #2563eb;
}

.editor-content :deep(.tiptap p.is-editor-empty:first-child::before) {
  color: #9ca3af;
  content: attr(data-placeholder);
  float: left;
  height: 0;
  pointer-events: none;
}
</style>
