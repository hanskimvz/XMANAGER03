<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import Pagination from '@/components/Pagination.vue'
import FreeBoardFormModal from './FreeBoardFormModal.vue'
import FreeBoardDetailModal from './FreeBoardDetailModal.vue'
import {
  freeBoardApi,
  FREE_BOARD_CATEGORIES,
  freeBoardCategoryLabel,
  type FreeBoardCategory,
  type FreeBoardDetail,
  type FreeBoardListItem,
} from '@/api/freeBoard'

const { error } = useToast()

const items = ref<FreeBoardListItem[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const category = ref<FreeBoardCategory | ''>('')
const q = ref('')
const loading = ref(false)

const detail = ref<FreeBoardDetail | null>(null)
const showForm = ref(false)
const editTarget = ref<FreeBoardDetail | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await freeBoardApi.list({
      page: page.value,
      size: size.value,
      category: category.value || undefined,
      q: q.value.trim() || undefined,
    })
    items.value = res.items
    total.value = res.total
  } catch (e: any) {
    error(e?.response?.data?.detail || '목록 로드 실패')
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  load()
}

const openingId = ref<number | null>(null)
async function open(id: number) {
  if (openingId.value !== null) return // 연타/중복요청 방지
  openingId.value = id
  try {
    detail.value = await freeBoardApi.detail(id)
    syncRow(detail.value)
  } catch (e: any) {
    error(e?.response?.data?.detail || '글 로드 실패')
  } finally {
    openingId.value = null
  }
}

// 상세에서 바뀐 값(조회수/댓글수)을 목록 행에 반영 — 목록을 다시 부르지 않는다
function syncRow(d: FreeBoardDetail) {
  const row = items.value.find((i) => i.id === d.id)
  if (!row) return
  row.view_count = d.view_count
  row.comment_count = d.comment_count
}

function onDetailUpdated(d: FreeBoardDetail) {
  detail.value = d
  syncRow(d)
}

function newPost() {
  editTarget.value = null
  showForm.value = true
}

function editPost() {
  editTarget.value = detail.value
  showForm.value = true
}

async function onSaved(saved: FreeBoardDetail) {
  const wasEdit = !!editTarget.value
  showForm.value = false
  editTarget.value = null
  if (wasEdit) {
    detail.value = saved // 수정: 열려 있던 상세를 갱신
  } else {
    // 새 글: 필터를 풀고 첫 페이지로(방금 쓴 글이 보이도록)
    category.value = ''
    q.value = ''
    page.value = 1
  }
  await load()
}

async function onDeleted() {
  detail.value = null
  // 마지막 페이지의 마지막 글을 지웠으면 앞 페이지로
  if (items.value.length === 1 && page.value > 1) page.value -= 1
  await load()
}

function authorLabel(a: FreeBoardListItem) {
  return a.is_anonymous ? '익명' : a.author_name || '-'
}

function fmtDate(s: string) {
  if (!s) return ''
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return s.slice(0, 10)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

onMounted(load)
</script>

<template>
  <div class="max-w-screen-xl mx-auto px-4 py-6">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-xl font-bold text-gray-800">자유게시판</h1>
        <p class="text-xs text-gray-500 mt-0.5">잡담 · 건의 · 불만 · 속마음 · 실명 또는 익명 작성</p>
      </div>
      <button class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700" @click="newPost">
        <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M16.9 3.5a2.1 2.1 0 013 0l.6.6a2.1 2.1 0 010 3l-1.3 1.3-3.6-3.6 1.3-1.3zM14.2 6.2l3.6 3.6-9.6 9.6a2 2 0 01-.9.5l-3.5.9a.6.6 0 01-.7-.7l.9-3.5a2 2 0 01.5-.9l9.7-9.5z" />
        </svg>
        글쓰기
      </button>
    </div>

    <p class="mb-4 px-3 py-2.5 rounded-lg border border-blue-200 bg-blue-50 text-xs text-blue-800">
      🕵️ 익명 글은 작성자 정보가 표시되지 않습니다. 건설적인 의견 수집을 위해 존중과 배려를 지켜 주세요.
    </p>

    <!-- 필터 -->
    <div class="bg-white rounded-lg shadow border p-3 mb-4 flex flex-wrap items-center gap-2">
      <select v-model="category" class="inp w-28" @change="onSearch">
        <option value="">전체</option>
        <option v-for="c in FREE_BOARD_CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
      </select>
      <input v-model="q" @keyup.enter="onSearch" placeholder="제목 검색" class="inp flex-1 min-w-[12rem]" />
      <button class="px-4 py-1.5 bg-gray-700 text-white text-sm rounded-md hover:bg-gray-800" @click="onSearch">검색</button>
    </div>

    <!-- 모바일 카드 목록 (lg 미만 전용) -->
    <div class="lg:hidden space-y-2">
      <div v-if="loading" class="bg-white rounded-lg shadow border p-6 text-center text-gray-400 text-sm">로딩 중...</div>
      <div v-else-if="!items.length" class="bg-white rounded-lg shadow border p-6 text-center text-gray-400 text-sm">등록된 글이 없습니다.</div>
      <template v-else>
        <button
          v-for="a in items"
          :key="'m' + a.id"
          type="button"
          class="w-full text-left bg-white rounded-lg shadow border p-3 active:bg-blue-50 transition-opacity"
          :class="{ 'opacity-50 pointer-events-none': openingId === a.id }"
          @click="open(a.id)"
        >
          <div class="flex items-start gap-1.5">
            <span class="cat-badge shrink-0" :class="`cat-${a.category}`">{{ freeBoardCategoryLabel(a.category) }}</span>
            <span class="flex-1 break-words text-gray-800">{{ a.title }}</span>
          </div>
          <div class="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500">
            <span>{{ authorLabel(a) }}</span>
            <span>{{ fmtDate(a.created_at) }}</span>
            <span>조회 {{ a.view_count }}</span>
            <span>댓글 {{ a.comment_count }}</span>
          </div>
        </button>
      </template>
      <Pagination v-if="total > 0" class="bg-white rounded-lg shadow border" :total="total" :page-size="size" :current-page="page"
                  @update:current-page="(p) => { page = p; load() }"
                  @update:page-size="(s) => { size = s; page = 1; load() }" />
    </div>

    <!-- 목록 (데스크톱 테이블, lg 이상 전용) -->
    <div class="hidden lg:block bg-white rounded-lg shadow border overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400 text-sm">로딩 중...</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 text-gray-500 text-xs">
          <tr>
            <th class="px-3 py-2 text-left w-20">분류</th>
            <th class="px-3 py-2 text-left">제목</th>
            <th class="px-3 py-2 text-center w-28">작성자</th>
            <th class="px-3 py-2 text-center w-28">작성일</th>
            <th class="px-3 py-2 text-center w-16">조회</th>
            <th class="px-3 py-2 text-center w-16">댓글</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in items" :key="a.id"
              class="border-t hover:bg-blue-50 cursor-pointer"
              :class="{ 'opacity-50 pointer-events-none': openingId === a.id }"
              @click="open(a.id)">
            <td class="px-3 py-2">
              <span class="cat-badge" :class="`cat-${a.category}`">{{ freeBoardCategoryLabel(a.category) }}</span>
            </td>
            <td class="px-3 py-2 text-gray-800">
              {{ a.title }}
              <span v-if="a.is_mine" class="ml-1 text-[10px] text-blue-600">(내 글)</span>
            </td>
            <td class="px-3 py-2 text-center text-gray-500 text-xs">{{ authorLabel(a) }}</td>
            <td class="px-3 py-2 text-center text-gray-500 text-xs">{{ fmtDate(a.created_at) }}</td>
            <td class="px-3 py-2 text-center text-gray-500 text-xs">{{ a.view_count }}</td>
            <td class="px-3 py-2 text-center text-gray-500 text-xs">{{ a.comment_count }}</td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="6" class="px-3 py-10 text-center text-gray-400">등록된 글이 없습니다.</td>
          </tr>
        </tbody>
      </table>
      <Pagination :total="total" :page-size="size" :current-page="page"
                  @update:current-page="(p) => { page = p; load() }"
                  @update:page-size="(s) => { size = s; page = 1; load() }" />
    </div>

    <!-- 상세 + 댓글 -->
    <FreeBoardDetailModal
      v-if="detail"
      :post="detail"
      @close="detail = null"
      @edit="editPost"
      @deleted="onDeleted"
      @updated="onDetailUpdated"
    />

    <!-- 작성/수정 -->
    <FreeBoardFormModal v-if="showForm" :post="editTarget" @close="showForm = false" @saved="onSaved" />
  </div>
</template>

<style scoped>
.inp { @apply px-2.5 py-1.5 border border-gray-300 rounded-md text-sm bg-white focus:outline-none focus:ring-1 focus:ring-blue-500; }

.cat-badge { @apply inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700 whitespace-nowrap; }
.cat-SUGGESTION { @apply bg-blue-50 text-blue-700; }
.cat-COMPLAINT { @apply bg-red-50 text-red-700; }
.cat-HEART { @apply bg-purple-50 text-purple-700; }
</style>
