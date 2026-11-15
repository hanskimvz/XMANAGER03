<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from '@/composables/useToast'
import RichTextEditor from '@/components/editor/RichTextEditor.vue'
import {
  freeBoardApi,
  FREE_BOARD_CATEGORIES,
  type FreeBoardCategory,
  type FreeBoardDetail,
} from '@/api/freeBoard'

const props = defineProps<{ post?: FreeBoardDetail | null }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'saved', post: FreeBoardDetail): void }>()
const { success, error, warning } = useToast()

const isEdit = computed(() => !!props.post)
const busy = ref(false)

const category = ref<FreeBoardCategory | ''>(props.post?.category || '')
const title = ref(props.post?.title || '')
const body = ref(props.post?.body || '')
const isAnonymous = ref(props.post?.is_anonymous || false)

// 본문이 비었는지: 텍스트도 이미지도 없으면 빈 것으로 본다
function bodyIsEmpty(html: string) {
  if (html.includes('<img')) return false
  return !html.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim()
}

const isDirty = computed(() =>
  category.value !== (props.post?.category || '') ||
  title.value !== (props.post?.title || '') ||
  body.value !== (props.post?.body || '') ||
  isAnonymous.value !== (props.post?.is_anonymous || false)
)

// 작성 중인 내용이 있으면 확인 후 닫는다
function close() {
  if (busy.value) return
  if (isDirty.value && !confirm('작성 중인 내용이 사라집니다. 닫을까요?')) return
  emit('close')
}

async function submit() {
  if (busy.value) return // 중복 제출(더블클릭) 방지
  if (!category.value) return warning('분류를 선택하세요')
  if (!title.value.trim()) return warning('제목을 입력하세요')
  if (bodyIsEmpty(body.value)) return warning('내용을 입력하세요')
  busy.value = true
  try {
    const payload = {
      category: category.value,
      title: title.value.trim(),
      body: body.value,
      is_anonymous: isAnonymous.value,
    }
    const saved = isEdit.value && props.post
      ? await freeBoardApi.update(props.post.id, payload)
      : await freeBoardApi.create(payload)
    success(isEdit.value ? '글이 수정되었습니다' : '글이 등록되었습니다')
    emit('saved', saved)
  } catch (e: any) {
    error(e?.response?.data?.detail || '저장 실패')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <!-- 바깥 클릭으로는 닫히지 않는다(작성 중 내용 보호) -->
  <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-2xl flex flex-col max-h-[92vh]">
      <div class="flex items-start justify-between px-5 py-3 border-b">
        <div>
          <h3 class="text-base font-semibold text-gray-800">{{ isEdit ? '글 수정' : '글 작성' }}</h3>
          <p class="text-xs text-gray-500 mt-0.5">분류, 제목, 내용을 입력하고 실명 또는 익명을 선택하세요</p>
        </div>
        <button @click="close" class="text-gray-400 hover:text-gray-600" aria-label="닫기">✕</button>
      </div>

      <div class="px-5 py-4 space-y-4 overflow-y-auto">
        <div class="flex flex-col sm:flex-row gap-3">
          <div class="sm:w-44 shrink-0">
            <label class="block text-xs text-gray-500 mb-1">분류</label>
            <select v-model="category" class="inp w-full">
              <option value="" disabled>분류를 선택하세요</option>
              <option v-for="c in FREE_BOARD_CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <div class="flex-1 min-w-0">
            <label class="block text-xs text-gray-500 mb-1">제목</label>
            <input v-model="title" class="inp w-full" placeholder="제목을 입력하세요" maxlength="300" />
          </div>
        </div>

        <div>
          <label class="block text-xs text-gray-500 mb-1">내용</label>
          <RichTextEditor v-model="body" placeholder="내용을 입력하세요" />
        </div>

        <div>
          <label class="inline-flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" v-model="isAnonymous" /> 익명으로 작성
          </label>
          <p class="mt-2 px-3 py-2 rounded-lg bg-blue-50 text-xs text-blue-800">
            🕵️ 익명으로 작성하면 목록과 상세에서 작성자 이름이 표시되지 않습니다.
          </p>
        </div>
      </div>

      <div class="px-5 py-3 border-t flex justify-end gap-2">
        <button type="button" @click="close" class="px-3 py-2 text-sm text-gray-600 border rounded-md hover:bg-gray-50">취소</button>
        <button :disabled="busy" @click="submit" class="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50">
          {{ busy ? '저장 중...' : '저장' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.inp { @apply px-2.5 py-1.5 border border-gray-300 rounded-md text-sm bg-white focus:outline-none focus:ring-1 focus:ring-blue-500; }
</style>
