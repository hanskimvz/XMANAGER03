<template>
  <div class="p-4 sm:p-6">
    <!-- 헤더 -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
      <h2 class="text-xl font-bold text-gray-900">영업 대응 현황</h2>
      <button @click="openCreateModal" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
        + 신규 등록
      </button>
    </div>

    <!-- 필터 -->
    <div class="bg-white rounded-lg shadow-sm border p-4 mb-4">
      <div class="flex flex-wrap gap-3">
        <!-- 상태 칩(다중선택, 합집합) -->
        <div class="flex flex-wrap gap-1.5 items-center">
          <span class="text-xs text-gray-500 mr-0.5">상태:</span>
          <button
            v-for="key in STATUS_ORDER" :key="key"
            type="button" @click="toggleStatus(key)"
            :class="isStatusOn(key)
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-white text-gray-400 border-gray-300 hover:bg-gray-50'"
            class="px-3 py-1 text-xs font-medium rounded-full border transition-colors"
          >{{ activityStatusLabels[key] }}</button>
        </div>
        <!-- 우선도 토글(별개 축) -->
        <div class="flex gap-1.5 items-center">
          <span class="text-xs text-gray-500 mr-0.5">우선도:</span>
          <button type="button" @click="toggleUrgent"
            :class="filters.urgent ? 'bg-rose-600 border-rose-600 text-white font-medium' : 'bg-white border-gray-300 text-gray-400'"
            class="border rounded-full px-3 py-1 text-xs whitespace-nowrap hover:bg-gray-50">🔴 긴급</button>
          <button type="button" @click="toggleImportant"
            :class="filters.important ? 'bg-amber-500 border-amber-500 text-white font-medium' : 'bg-white border-gray-300 text-gray-400'"
            class="border rounded-full px-3 py-1 text-xs whitespace-nowrap hover:bg-gray-50">🟠 중요</button>
        </div>
        <div class="flex items-center gap-2 text-xs ml-auto self-center whitespace-nowrap">
          <span class="px-2 py-1 rounded-full bg-rose-50 text-rose-600">🔴 긴급 {{ urgentCount }}</span>
          <span class="px-2 py-1 rounded-full bg-amber-50 text-amber-600">🟠 중요 {{ importantCount }}</span>
        </div>
        <!-- 담당자 다중 선택 -->
        <div class="relative" ref="assigneeDropdownRef">
          <button type="button" @click="showAssigneeDropdown = !showAssigneeDropdown"
            class="border rounded-md px-3 py-2 text-sm flex items-center gap-2 min-w-[160px] justify-between hover:border-gray-400">
            <span :class="filters.assigned_to.length === 0 ? 'text-gray-500' : 'text-gray-900'">
              {{ assigneeFilterLabel }}
            </span>
            <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <div v-if="showAssigneeDropdown"
            class="absolute z-20 mt-1 w-56 bg-white border rounded-md shadow-lg max-h-72 overflow-y-auto">
            <div class="flex items-center justify-between px-3 py-2 border-b bg-gray-50">
              <span class="text-xs text-gray-500">담당자 선택 (다중)</span>
              <button v-if="filters.assigned_to.length > 0" type="button"
                @click="clearAssignees" class="text-xs text-blue-600 hover:underline">전체 해제</button>
            </div>
            <label v-for="a in assignees" :key="a"
              class="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-blue-50">
              <input type="checkbox" :value="a" v-model="filters.assigned_to"
                @change="resetAndLoad" class="w-4 h-4 rounded accent-blue-600" />
              <span>{{ a }}</span>
            </label>
            <div v-if="assignees.length === 0" class="px-3 py-3 text-xs text-gray-400 text-center">
              담당자가 없습니다
            </div>
          </div>
        </div>
        <input v-model="filters.keyword" @input="debouncedLoad" placeholder="프로젝트명 / 거래처 검색..."
          class="border rounded-md px-3 py-2 text-sm flex-1 min-w-[200px]" />
      </div>
    </div>

    <!-- 비활성 필터 배너 -->
    <div v-if="showInactiveOnly" class="mb-3 flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
      <span class="text-sm text-red-700 font-medium">🔴 비활성 영업활동만 표시 중 (8주 이상 업데이트 없음)</span>
      <button @click="showInactiveOnly = false; router.replace({ query: { ...route.query, inactive: undefined } })"
        class="text-xs text-red-500 hover:text-red-700 underline">전체 보기</button>
    </div>

    <!-- 리스트 -->
    <div class="bg-white rounded-lg shadow-sm border overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400">로딩 중...</div>
      <div v-else-if="sortedItems.length === 0" class="p-8 text-center text-gray-400">
        {{ showInactiveOnly ? '비활성 영업활동이 없습니다.' : '등록된 영업활동이 없습니다.' }}
      </div>

      <!-- 데스크톱 테이블 -->
      <table v-else class="w-full table-fixed divide-y divide-gray-200 hidden sm:table">
        <colgroup>
          <col style="width: 9%" />
          <col style="width: 9%" />
          <col style="width: 15%" />
          <col style="width: 21%" />
          <col style="width: 10%" />
          <col style="width: 13%" />
          <col style="width: 14%" />
          <col style="width: 9%" />
        </colgroup>
        <thead class="bg-gray-50">
          <tr>
            <th @click="toggleSort('status')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">상태{{ sortIndicator('status') }}</th>
            <th @click="toggleSort('country')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">나라{{ sortIndicator('country') }}</th>
            <th @click="toggleSort('customer_name')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">거래처{{ sortIndicator('customer_name') }}</th>
            <th @click="toggleSort('title')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">프로젝트명{{ sortIndicator('title') }}</th>
            <th @click="toggleSort('inquiry_type')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">문의 유형{{ sortIndicator('inquiry_type') }}</th>
            <th @click="toggleSort('assigned_to')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">담당자{{ sortIndicator('assigned_to') }}</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">진행 단계</th>
            <th @click="toggleSort('updated_at')" class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">최근 업데이트{{ sortIndicator('updated_at') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          <tr v-for="item in sortedItems" :key="item.id" class="hover:bg-gray-50 cursor-pointer" @click="openDetail(item.id)">
            <td class="px-4 py-3 whitespace-nowrap">
              <div class="flex items-center gap-1">
                <span :class="activityStatusStyles[item.status]" class="inline-block px-2 py-0.5 text-xs font-medium rounded-full whitespace-nowrap">
                  {{ activityStatusLabels[item.status] || item.status }}
                </span>
                <span v-if="item.is_urgent" class="text-[11px]" title="긴급">🔴</span>
                <span v-if="item.is_important" class="text-[11px]" title="중요">🟠</span>
              </div>
            </td>
            <td class="px-4 py-3 text-sm text-gray-600 truncate" :title="item.country || '-'">{{ item.country || '-' }}</td>
            <td class="px-4 py-3 text-sm text-gray-900 truncate" :title="item.customer_name || item.customer?.partner_name || '-'">{{ item.customer_name || item.customer?.partner_name || '-' }}</td>
            <td class="px-4 py-3 text-sm font-medium text-blue-600 truncate" :title="item.title">{{ item.title }}</td>
            <td class="px-4 py-3 text-sm text-gray-500 truncate" :title="inquiryTypeLabel(item.inquiry_type)">{{ inquiryTypeLabel(item.inquiry_type) }}</td>
            <td class="px-4 py-3 text-sm text-gray-600 truncate" :title="item.assigned_to || '-'">{{ item.assigned_to || '-' }}</td>
            <td class="px-4 py-3 text-sm">
              <button v-if="item.stage_type" @click.stop="onStageClick(item)"
                :class="stageBadgeClass(item.stage_type)"
                class="px-2 py-0.5 text-xs font-medium rounded-full hover:opacity-80 whitespace-nowrap"
                title="클릭하여 문서 열기">
                {{ item.stage_label }} ↗
              </button>
              <span v-else class="text-gray-300 text-xs">-</span>
            </td>
            <td class="px-4 py-3 text-sm text-center text-gray-400">{{ formatDate(lastUpdatedAt(item)) }}</td>
          </tr>
        </tbody>
      </table>

      <!-- 모바일 카드 -->
      <div v-if="sortedItems.length > 0" class="sm:hidden divide-y divide-gray-200">
        <div v-for="item in sortedItems" :key="item.id" @click="openDetail(item.id)"
          class="p-4 hover:bg-gray-50 cursor-pointer">
          <div class="flex justify-between items-start mb-2">
            <span class="text-sm font-medium text-blue-600">{{ item.title }}</span>
            <span :class="activityStatusStyles[item.status]" class="px-2 py-0.5 text-xs font-medium rounded-full ml-2 whitespace-nowrap">
              {{ activityStatusLabels[item.status] }}
            </span>
          </div>
          <div class="text-xs text-gray-500">
            {{ item.country }} · {{ item.customer_name || item.customer?.partner_name }} · {{ item.assigned_to }}
          </div>
          <div class="flex items-center gap-2 mt-1">
            <button v-if="item.stage_type" @click.stop="onStageClick(item)" :class="stageBadgeClass(item.stage_type)" class="px-2 py-0.5 text-[11px] font-medium rounded-full">{{ item.stage_label }} ↗</button>
            <span v-if="item.is_urgent" class="text-[11px]">🔴</span>
            <span v-if="item.is_important" class="text-[11px]">🟠</span>
          </div>
        </div>
      </div>

      <!-- 페이지네이션 -->
      <Pagination
        v-if="totalCount > 0"
        :total="totalCount"
        :page-size="pageSize"
        :current-page="currentPage"
        @update:current-page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </div>

    <!-- 상세 모달 -->
    <SalesActivityDetailModal
      v-if="showDetailModal && detailId"
      :activity-id="detailId"
      @close="showDetailModal = false"
      @edit="openEditFromDetail"
      @updated="handleUpdated"
    />

    <!-- 생성/수정 모달 -->
    <SalesActivityFormModal
      v-if="showFormModal"
      :activity="editingItem"
      @close="showFormModal = false"
      @saved="handleSaved"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  salesActivityApi,
  activityStatusLabels,
  activityStatusStyles,
  type SalesActivity,
} from '@/api/salesActivity'
import { useToast } from '@/composables/useToast'
import SalesActivityDetailModal from '@/views/sales/activity/SalesActivityDetailModal.vue'
import SalesActivityFormModal from '@/views/sales/activity/SalesActivityFormModal.vue'
import Pagination from '@/components/Pagination.vue'

const route = useRoute()
const router = useRouter()
const { showToast } = useToast()
const emit = defineEmits<{ (e: 'navigate-doc', payload: { docId: number; docType: string }): void }>()

// 상태 칩(다중선택) — 기본 활성 3개 ON. 완료/무산은 기본 OFF.
const STATUS_ORDER = ['IN_PROGRESS', 'WAITING', 'ON_HOLD', 'COMPLETED', 'DROPPED']
const DEFAULT_STATUSES = ['IN_PROGRESS', 'WAITING', 'ON_HOLD']
const urgentCount = computed(() => items.value.filter(i => i.is_urgent && ['IN_PROGRESS', 'WAITING'].includes(i.status)).length)
const importantCount = computed(() => items.value.filter(i => i.is_important && ['IN_PROGRESS', 'WAITING'].includes(i.status)).length)

const INQUIRY_TYPE_LABELS: Record<string, string> = {
  GENERAL: '일반',
  TECHNICAL: '기술',
  QUOTATION: '견적',
  SAMPLE: '샘플',
  CLAIM: '클레임',
  OTHER: '기타',
}
function inquiryTypeLabel(type?: string) { return INQUIRY_TYPE_LABELS[type || ''] || type || '-' }
const loading = ref(false)
const items = ref<SalesActivity[]>([])
const assignees = ref<string[]>([])
const filters = ref<{ statuses: string[]; assigned_to: string[]; keyword: string; urgent: boolean; important: boolean }>({
  statuses: [...DEFAULT_STATUSES], assigned_to: [], keyword: '', urgent: false, important: false,
})
function isStatusOn(key: string) { return filters.value.statuses.includes(key) }
function toggleStatus(key: string) {
  const i = filters.value.statuses.indexOf(key)
  if (i >= 0) filters.value.statuses.splice(i, 1)
  else filters.value.statuses.push(key)
  resetAndLoad()
}
function toggleUrgent() { filters.value.urgent = !filters.value.urgent; resetAndLoad() }
function toggleImportant() { filters.value.important = !filters.value.important; resetAndLoad() }
const showInactiveOnly = ref(false)

// 담당자 다중 선택 드롭다운
const showAssigneeDropdown = ref(false)
const assigneeDropdownRef = ref<HTMLElement | null>(null)
const assigneeFilterLabel = computed(() => {
  const sel = filters.value.assigned_to
  if (sel.length === 0) return '전체 담당자'
  if (sel.length === 1) return sel[0] as string
  return `${sel[0]} 외 ${sel.length - 1}명`
})
function clearAssignees() {
  filters.value.assigned_to = []
  resetAndLoad()
}
function handleAssigneeClickOutside(e: MouseEvent) {
  if (assigneeDropdownRef.value && !assigneeDropdownRef.value.contains(e.target as Node)) {
    showAssigneeDropdown.value = false
  }
}

// 페이지네이션
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)

// 정렬 (빈 값 = 서버 기본 정렬: 상태 우선 → 최근순)
const sortKey = ref<string>('')
const sortDesc = ref(true)

function toggleSort(key: string) {
  if (sortKey.value === key) {
    sortDesc.value = !sortDesc.value
  } else {
    sortKey.value = key
    sortDesc.value = key === 'updated_at' || key === 'created_at'
  }
}

function sortIndicator(key: string) {
  if (sortKey.value !== key) return ''
  return sortDesc.value ? ' ↓' : ' ↑'
}

const INACTIVE_THRESHOLD = 8 * 7 * 24 * 60 * 60 * 1000 // 8주 in ms
const GRACE_PERIOD = 4 * 7 * 24 * 60 * 60 * 1000 // 4주 in ms (등록 유예)

const sortedItems = computed(() => {
  let arr = [...items.value]

  // 비활성 필터 (로그 8주 이상 전 OR 로그 없고 등록 4주 이상 전)
  if (showInactiveOnly.value) {
    const now = Date.now()
    arr = arr.filter(item => {
      if (!['IN_PROGRESS', 'WAITING'].includes(item.status)) return false
      if (item.last_log_date) {
        return now - new Date(item.last_log_date).getTime() > INACTIVE_THRESHOLD
      }
      // 로그 없음: 등록일 4주 이상 전이면 비활성
      const created = item.created_at ? new Date(item.created_at).getTime() : 0
      return now - created > GRACE_PERIOD
    })
  }
  const key = sortKey.value
  // 기본 정렬은 서버가 처리(긴급·중요 → 활성상태 → 최근순). 컬럼 클릭 시에만 클라이언트 정렬.
  if (!key) return arr
  const dir = sortDesc.value ? -1 : 1

  arr.sort((a: any, b: any) => {
    let va = a[key] ?? ''
    let vb = b[key] ?? ''

    // 특수 키 매핑
    if (key === 'customer_name') {
      va = a.customer_name || a.customer?.partner_name || ''
      vb = b.customer_name || b.customer?.partner_name || ''
    }
    if (key === 'updated_at') {
      va = lastUpdatedAt(a)
      vb = lastUpdatedAt(b)
    }

    if (typeof va === 'string') va = va.toLowerCase()
    if (typeof vb === 'string') vb = vb.toLowerCase()

    if (va < vb) return -1 * dir
    if (va > vb) return 1 * dir
    return 0
  })
  return arr
})

const showDetailModal = ref(false)
const detailId = ref<number | null>(null)
const showFormModal = ref(false)
const editingItem = ref<SalesActivity | null>(null)

async function loadData() {
  loading.value = true
  try {
    const params: any = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    }
    // 상태를 하나도 안 켜면 결과 없음(서버 호출 생략)
    if (filters.value.statuses.length === 0) { items.value = []; totalCount.value = 0; return }
    params.status = filters.value.statuses
    if (filters.value.assigned_to.length) params.assigned_to = filters.value.assigned_to.join(',')
    if (filters.value.keyword) params.keyword = filters.value.keyword
    if (filters.value.urgent) params.urgent = true
    if (filters.value.important) params.important = true
    const res = await salesActivityApi.getList(params)
    items.value = res.data.items
    totalCount.value = res.data.total
  } catch {
    showToast('데이터를 불러오는데 실패했습니다', 'error')
  } finally {
    loading.value = false
  }
}

function resetAndLoad() {
  currentPage.value = 1
  loadData()
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadData()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadData()
}

async function loadAssignees() {
  try {
    const res = await salesActivityApi.getAssignees()
    assignees.value = res.data
  } catch { /* ignore */ }
}

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedLoad() { clearTimeout(debounceTimer); debounceTimer = setTimeout(resetAndLoad, 300) }

function openCreateModal() { editingItem.value = null; showFormModal.value = true }
function openDetail(id: number) { detailId.value = id; showDetailModal.value = true }

function openEditFromDetail(id: number) {
  showDetailModal.value = false
  const item = items.value.find(i => i.id === id)
  if (item) { editingItem.value = item; showFormModal.value = true }
  else {
    salesActivityApi.getById(id).then(res => { editingItem.value = res.data; showFormModal.value = true })
  }
}

function handleSaved() { showFormModal.value = false; loadData(); loadAssignees() }
function handleUpdated() { loadData() }

// 진행 단계 배지 색 + 클릭 시 해당 문서 탭으로 이동
function stageBadgeClass(type?: string): string {
  switch (type) {
    case 'QUOTATION': return 'bg-blue-100 text-blue-700'
    case 'PI': return 'bg-purple-100 text-purple-700'
    case 'CI': return 'bg-amber-100 text-amber-700'
    case 'PRODUCTION': return 'bg-emerald-100 text-emerald-700'
    default: return 'bg-gray-100 text-gray-600'
  }
}
function onStageClick(item: SalesActivity) {
  if (!item.stage_type || !item.stage_doc_id) return
  if (item.stage_type === 'PRODUCTION') {
    router.push({ path: '/production' })  // 생산관리로 이동
  } else {
    emit('navigate-doc', { docId: item.stage_doc_id, docType: item.stage_type })
  }
}

function formatDate(d?: string) {
  if (!d) return '-'
  const date = new Date(d)
  return `${date.getFullYear()}.${String(date.getMonth()+1).padStart(2,'0')}.${String(date.getDate()).padStart(2,'0')}`
}

// 최근 업데이트 시각: 로그 생성일 / 필드 수정일(updated_at) / 생성일 중 가장 최신
// last_log_date만 보면 '다음 단계' 등 로그를 남기지 않는 필드 수정이 반영되지 않으므로 max로 계산
function lastUpdatedAt(item: { last_log_date?: string; updated_at?: string; created_at?: string }): string {
  const dates = [item.last_log_date, item.updated_at, item.created_at].filter(Boolean) as string[]
  if (dates.length === 0) return ''
  return dates.reduce((a, b) => (a > b ? a : b))
}

onMounted(() => {
  if (route.query.inactive === '1') showInactiveOnly.value = true
  loadData()
  loadAssignees()
  document.addEventListener('click', handleAssigneeClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleAssigneeClickOutside)
})

watch(() => route.query.inactive, (val) => {
  showInactiveOnly.value = val === '1'
})
</script>
