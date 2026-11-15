<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from '@/composables/useToast'
import RichTextViewer from '@/components/editor/RichTextViewer.vue'
import {
  freeBoardApi,
  freeBoardCategoryLabel,
  type FreeBoardComment,
  type FreeBoardDetail,
} from '@/api/freeBoard'

const props = defineProps<{ post: FreeBoardDetail }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'edit'): void
  (e: 'deleted'): void
  /** 댓글 등록/삭제로 글 상세가 갱신됨 */
  (e: 'updated', post: FreeBoardDetail): void
}>()
const { success, error, warning } = useToast()

const busy = ref(false)

// 댓글 입력 (replyTo: 답글 대상 최상위 댓글)
const commentText = ref('')
const commentAnonymous = ref(false)
const replyTo = ref<FreeBoardComment | null>(null)

// 최상위 댓글 + 그 아래 답글(1단계)
const threads = computed(() => {
  const roots = props.post.comments.filter((c) => !c.parent_id)
  return roots.map((root) => ({
    root,
    replies: props.post.comments.filter((c) => c.parent_id === root.id),
  }))
})

function authorLabel(c: { is_anonymous: boolean; author_name?: string | null }) {
  return c.is_anonymous ? '익명' : c.author_name || '-'
}

function fmtDateTime(s: string) {
  if (!s) return ''
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return s.slice(0, 16).replace('T', ' ')
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function submitComment() {
  if (busy.value) return
  const content = commentText.value.trim()
  if (!content) return warning('댓글 내용을 입력하세요')
  busy.value = true
  try {
    const updated = await freeBoardApi.addComment(props.post.id, {
      content,
      is_anonymous: commentAnonymous.value,
      parent_id: replyTo.value?.id ?? null,
    })
    commentText.value = ''
    replyTo.value = null
    emit('updated', updated)
  } catch (e: any) {
    error(e?.response?.data?.detail || '댓글 등록 실패')
  } finally {
    busy.value = false
  }
}

async function removeComment(c: FreeBoardComment) {
  if (busy.value) return
  if (!confirm('댓글을 삭제할까요?')) return
  busy.value = true
  try {
    const updated = await freeBoardApi.removeComment(props.post.id, c.id)
    if (replyTo.value?.id === c.id) replyTo.value = null
    emit('updated', updated)
  } catch (e: any) {
    error(e?.response?.data?.detail || '댓글 삭제 실패')
  } finally {
    busy.value = false
  }
}

async function removePost() {
  if (busy.value) return
  if (!confirm(`글 '${props.post.title}' 을(를) 삭제할까요?`)) return
  busy.value = true
  try {
    await freeBoardApi.remove(props.post.id)
    success('글이 삭제되었습니다')
    emit('deleted')
  } catch (e: any) {
    error(e?.response?.data?.detail || '삭제 실패')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <!-- 바깥 클릭으로 닫히지 않음(댓글 입력 보호) — 닫기[✕]로만 -->
  <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-40 p-4">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-2xl flex flex-col max-h-[92vh]">
      <div class="flex items-start justify-between gap-3 px-5 py-3 border-b">
        <div class="min-w-0">
          <h3 class="text-lg font-semibold text-gray-800 break-words">
            <span class="cat-badge align-middle mr-1.5" :class="`cat-${post.category}`">{{ freeBoardCategoryLabel(post.category) }}</span>
            <span class="align-middle">{{ post.title }}</span>
          </h3>
          <p class="text-xs text-gray-400 mt-1">
            {{ authorLabel(post) }}
            <span v-if="post.is_mine" class="text-blue-600">(내 글)</span>
            · {{ fmtDateTime(post.created_at) }} · 조회 {{ post.view_count }}
          </p>
        </div>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600 shrink-0" aria-label="닫기">✕</button>
      </div>

      <div class="px-5 py-4 overflow-y-auto">
        <RichTextViewer :html="post.body" />

        <!-- 댓글 -->
        <div class="mt-6 border-t pt-4">
          <div class="text-sm font-semibold text-gray-700 mb-2">댓글 {{ post.comment_count }}</div>

          <ul v-if="threads.length" class="space-y-3 mb-4">
            <li v-for="t in threads" :key="t.root.id">
              <div class="comment">
                <template v-if="t.root.is_deleted">
                  <p class="text-sm text-gray-400">삭제된 댓글입니다.</p>
                </template>
                <template v-else>
                  <div class="comment-meta">
                    <span class="font-medium text-gray-700">{{ authorLabel(t.root) }}</span>
                    <span v-if="t.root.is_post_author" class="author-badge">글쓴이</span>
                    <span>{{ fmtDateTime(t.root.created_at) }}</span>
                    <button type="button" class="hover:underline" @click="replyTo = t.root">답글</button>
                    <button v-if="t.root.can_delete" type="button" class="text-red-500 hover:underline" :disabled="busy" @click="removeComment(t.root)">삭제</button>
                  </div>
                  <p class="comment-text">{{ t.root.content }}</p>
                </template>
              </div>

              <ul v-if="t.replies.length" class="mt-2 ml-5 pl-3 border-l-2 border-gray-200 space-y-2">
                <li v-for="r in t.replies" :key="r.id" class="comment">
                  <div class="comment-meta">
                    <span class="font-medium text-gray-700">{{ authorLabel(r) }}</span>
                    <span v-if="r.is_post_author" class="author-badge">글쓴이</span>
                    <span>{{ fmtDateTime(r.created_at) }}</span>
                    <button v-if="r.can_delete" type="button" class="text-red-500 hover:underline" :disabled="busy" @click="removeComment(r)">삭제</button>
                  </div>
                  <p class="comment-text">{{ r.content }}</p>
                </li>
              </ul>
            </li>
          </ul>
          <p v-else class="text-sm text-gray-400 mb-4">첫 댓글을 남겨 보세요.</p>

          <!-- 댓글 입력 -->
          <div class="border rounded-lg p-3 bg-gray-50">
            <div v-if="replyTo" class="flex items-center justify-between mb-2 text-xs text-blue-700">
              <span>↳ {{ authorLabel(replyTo) }} 님의 댓글에 답글 작성 중</span>
              <button type="button" class="text-gray-500 hover:underline" @click="replyTo = null">취소</button>
            </div>
            <textarea
              v-model="commentText"
              rows="2"
              maxlength="2000"
              class="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              :placeholder="replyTo ? '답글을 입력하세요' : '댓글을 입력하세요'"
            ></textarea>
            <div class="mt-2 flex items-center justify-between">
              <label class="inline-flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" v-model="commentAnonymous" /> 익명으로 작성
              </label>
              <button :disabled="busy" @click="submitComment" class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50">
                {{ replyTo ? '답글 등록' : '댓글 등록' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="post.can_edit || post.can_delete" class="px-5 py-3 border-t flex justify-end gap-2">
        <button v-if="post.can_edit" class="px-3 py-1.5 text-sm text-gray-700 border rounded hover:bg-gray-50" @click="emit('edit')">수정</button>
        <button v-if="post.can_delete" :disabled="busy" class="px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded hover:bg-red-50 disabled:opacity-50" @click="removePost">삭제</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.comment-meta { @apply flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-gray-400; }
.comment-text { @apply mt-0.5 text-sm text-gray-800 whitespace-pre-wrap break-words; }
.author-badge { @apply px-1.5 py-px rounded bg-blue-50 text-blue-700 text-[10px] font-medium; }

.cat-badge { @apply inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700; }
.cat-SUGGESTION { @apply bg-blue-50 text-blue-700; }
.cat-COMPLAINT { @apply bg-red-50 text-red-700; }
.cat-HEART { @apply bg-purple-50 text-purple-700; }
</style>
