<script setup lang="ts">
import { watch, onBeforeUnmount } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const editor = useEditor({
  content: props.modelValue || '',
  extensions: [StarterKit],
  editorProps: {
    attributes: { class: 'prose prose-sm max-w-none focus:outline-none min-h-[180px] px-3 py-2' },
  },
  onUpdate: ({ editor }) => emit('update:modelValue', editor.getHTML()),
})

// 외부 값 변경(수정 모달 열기 등) 반영 — 커서 무한루프 방지 위해 다를 때만
watch(() => props.modelValue, (v) => {
  if (editor.value && v !== editor.value.getHTML()) {
    editor.value.commands.setContent(v || '', { emitUpdate: false })
  }
})

onBeforeUnmount(() => editor.value?.destroy())

function btnClass(active: boolean) {
  return [
    'px-2 py-1 text-xs rounded border',
    active ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-100',
  ]
}
</script>

<template>
  <div class="border rounded-md">
    <div v-if="editor" class="flex flex-wrap gap-1 border-b bg-gray-50 p-1.5">
      <button type="button" :class="btnClass(editor.isActive('bold'))" @click="editor.chain().focus().toggleBold().run()"><b>B</b></button>
      <button type="button" :class="btnClass(editor.isActive('italic'))" @click="editor.chain().focus().toggleItalic().run()"><i>I</i></button>
      <button type="button" :class="btnClass(editor.isActive('strike'))" @click="editor.chain().focus().toggleStrike().run()"><s>S</s></button>
      <span class="w-px bg-gray-300 mx-1"></span>
      <button type="button" :class="btnClass(editor.isActive('heading', { level: 2 }))" @click="editor.chain().focus().toggleHeading({ level: 2 }).run()">제목</button>
      <button type="button" :class="btnClass(editor.isActive('bulletList'))" @click="editor.chain().focus().toggleBulletList().run()">• 목록</button>
      <button type="button" :class="btnClass(editor.isActive('orderedList'))" @click="editor.chain().focus().toggleOrderedList().run()">1. 목록</button>
      <button type="button" :class="btnClass(editor.isActive('blockquote'))" @click="editor.chain().focus().toggleBlockquote().run()">인용</button>
      <span class="w-px bg-gray-300 mx-1"></span>
      <button type="button" :class="btnClass(false)" @click="editor.chain().focus().undo().run()">↶</button>
      <button type="button" :class="btnClass(false)" @click="editor.chain().focus().redo().run()">↷</button>
    </div>
    <EditorContent :editor="editor" />
  </div>
</template>
