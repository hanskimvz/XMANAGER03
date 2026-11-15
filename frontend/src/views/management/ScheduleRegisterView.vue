<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import Pagination from '@/components/Pagination.vue'
import ScheduleFormModal from './ScheduleFormModal.vue'
import {
  scheduleApi,
  SCHEDULE_TYPES,
  scheduleTypeLabel,
  type ScheduleItem,
  type ScheduleType,
} from '@/api/schedule'

const { success, error } = useToast()

function pad(n: number) {
  return String(n).padStart(2, '0')
}
const now = new Date()
const today = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`

const items = ref<ScheduleItem[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const scheduleType = ref<ScheduleType | ''>('')
const month = ref(today.slice(0, 7)) // YYYY-MM, 비우면 전체 기간
const q = ref('')
const loading = ref(false)

const showForm = ref(false)
const editTarget = ref<ScheduleItem | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await scheduleApi.list({
      page: page.value,
      size: size.value,
      schedule_type: scheduleType.value || undefined,
      month: month.value || undefined,
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

function selectType(t: ScheduleType | '') {
  scheduleType.value = t
  onSearch()
}

function newSchedule() {
  editTarget.value = null
  showForm.value = true
}

function editSchedule(item: ScheduleItem) {
  editTarget.value = item
  showForm.value = true
}

async function onSaved(saved: ScheduleItem) {
  const wasEdit = !!editTarget.value
  showForm.value = false
  editTarget.value = null
  if (!wasEdit) {
    // 새 일정: 방금 등록한 일정이 보이도록 필터를 풀고 그 달로 이동
    scheduleType.value = ''
    q.value = ''
    month.value = saved.start_date.slice(0, 7)
    page.value = 1
  }
  await load()
}

async function removeSchedule(item: ScheduleItem) {
  if (!confirm(`일정 '${item.title}' 을(를) 삭제할까요?`)) return
  try {
    await scheduleApi.remove(item.id)
    success('일정이 삭제되었습니다')
    // 마지막 페이지의 마지막 항목을 지웠으면 앞 페이지로
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    await load()
  } catch (e: any) {
    error(e?.response?.data?.detail || '삭제 실패')
  }
}

function typeBadge(code: string) {
  return SCHEDULE_TYPES.find((t) => t.value === code)?.badge || 'bg-gray-100 text-gray-700'
}

function period(item: ScheduleItem) {
  return item.start_date === item.end_date ? item.start_date : `${item.start_date} ~ ${item.end_date}`
}

function targetLabel(item: ScheduleItem) {
  return item.target_name || (item.schedule_type === 'EVENT' ? '전사' : '-')
}

function sourceLabel(item: ScheduleItem) {
  return item.source === 'MANUAL' ? '직접 등록' : item.source
}

onMounted(load)
</script>

<template>
  <div class="max-w-screen-xl mx-auto px-4 py-6">
    <div class="flex items-start justify-between gap-3 mb-4">
      <div>
        <h1 class="text-xl font-bold text-gray-800">스케줄 등록</h1>
        <p class="text-xs text-gray-500 mt-0.5">
          행사 · 휴가 · 외근 · 출장을 등록하면 게시판 일정 캘린더에 표시됩니다. 휴가는 이후 휴가신청서와 연동할 수 있습니다.
        </p>
      </div>
      <button class="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700" @click="newSchedule">
        <span class="text-base leading-none">+</span> 일정 등록
      </button>
    </div>

    <!-- 필터 -->
    <div class="bg-white rounded-lg shadow border p-3 mb-4 flex flex-wrap items-center gap-2">
      <div class="flex flex-wrap items-center gap-1.5 mr-auto">
        <button type="button" class="pill" :class="{ 'pill-on': scheduleType === '' }" @click="selectType('')">전체</button>
        <button
          v-for="t in SCHEDULE_TYPES"
          :key="t.value"
          type="button"
          class="pill"
          :class="{ 'pill-on': scheduleType === t.value }"
          @click="selectType(t.value)"
        >
          <span class="w-2 h-2 rounded-full" :class="t.dot"></span>{{ t.label }}
        </button>
      </div>
      <input v-model="month" type="month" class="inp w-40" title="조회 월 (비우면 전체 기간)" @change="onSearch" />
      <input v-model="q" @keyup.enter="onSearch" placeholder="제목 · 대상자 · 장소 검색" class="inp w-full sm:w-56" />
      <button class="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700" @click="onSearch">검색</button>
    </div>

    <!-- 모바일 카드 목록 (lg 미만 전용) -->
    <div class="lg:hidden space-y-2">
      <div v-if="loading" class="bg-white rounded-lg shadow border p-6 text-center text-gray-400 text-sm">로딩 중...</div>
      <div v-else-if="!items.length" class="bg-white rounded-lg shadow border p-6 text-center text-gray-400 text-sm">등록된 일정이 없습니다.</div>
      <template v-else>
        <div v-for="a in items" :key="'m' + a.id" class="bg-white rounded-lg shadow border p-3">
          <div class="flex items-start gap-1.5">
            <span class="type-badge shrink-0" :class="typeBadge(a.schedule_type)">{{ scheduleTypeLabel(a.schedule_type) }}</span>
            <span class="flex-1 break-words text-gray-800">{{ a.title }}</span>
          </div>
          <div class="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500">
            <span>{{ targetLabel(a) }}</span>
            <span>{{ period(a) }}</span>
            <span v-if="a.location">{{ a.location }}</span>
          </div>
          <div v-if="a.can_edit" class="mt-2 flex justify-end gap-3 text-xs">
            <button class="text-blue-600 hover:underline" @click="editSchedule(a)">수정</button>
            <button class="text-red-600 hover:underline" @click="removeSchedule(a)">삭제</button>
          </div>
        </div>
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
            <th class="px-3 py-2 text-left w-20">유형</th>
            <th class="px-3 py-2 text-left">제목</th>
            <th class="px-3 py-2 text-left w-32">대상자</th>
            <th class="px-3 py-2 text-left w-52">기간</th>
            <th class="px-3 py-2 text-left w-44">장소</th>
            <th class="px-3 py-2 text-left w-24">출처</th>
            <th class="px-3 py-2 text-left w-24">관리</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in items" :key="a.id" class="border-t hover:bg-gray-50">
            <td class="px-3 py-2">
              <span class="type-badge" :class="typeBadge(a.schedule_type)">{{ scheduleTypeLabel(a.schedule_type) }}</span>
            </td>
            <td class="px-3 py-2 text-gray-800">
              {{ a.title }}
              <p v-if="a.memo" class="text-xs text-gray-400 truncate max-w-md" :title="a.memo">{{ a.memo }}</p>
            </td>
            <td class="px-3 py-2 text-gray-600 text-xs">{{ targetLabel(a) }}</td>
            <td class="px-3 py-2 text-gray-600 text-xs whitespace-nowrap">{{ period(a) }}</td>
            <td class="px-3 py-2 text-gray-600 text-xs">{{ a.location || '-' }}</td>
            <td class="px-3 py-2 text-gray-500 text-xs" :title="a.created_by_name ? `등록자: ${a.created_by_name}` : ''">{{ sourceLabel(a) }}</td>
            <td class="px-3 py-2 text-xs whitespace-nowrap">
              <template v-if="a.can_edit">
                <button class="text-blue-600 hover:underline mr-2" @click="editSchedule(a)">수정</button>
                <button class="text-red-600 hover:underline" @click="removeSchedule(a)">삭제</button>
              </template>
              <span v-else class="text-gray-300">-</span>
            </td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="7" class="px-3 py-10 text-center text-gray-400">등록된 일정이 없습니다.</td>
          </tr>
        </tbody>
      </table>
      <Pagination :total="total" :page-size="size" :current-page="page"
                  @update:current-page="(p) => { page = p; load() }"
                  @update:page-size="(s) => { size = s; page = 1; load() }" />
    </div>

    <!-- 등록/수정 -->
    <ScheduleFormModal
      v-if="showForm"
      :schedule="editTarget"
      :default-date="today"
      @close="showForm = false"
      @saved="onSaved"
    />
  </div>
</template>

<style scoped>
.inp { @apply px-2.5 py-1.5 border border-gray-300 rounded-md text-sm bg-white focus:outline-none focus:ring-1 focus:ring-blue-500; }

.pill { @apply inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-gray-200 bg-white text-xs font-medium text-gray-700 hover:bg-gray-50; }
.pill-on { @apply border-blue-500 bg-blue-50 text-blue-700; }

.type-badge { @apply inline-block px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap; }
</style>
