<template>
  <div class="p-4 sm:p-6 max-w-screen-2xl mx-auto">
    <!-- 헤더 -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
      <h1 class="text-2xl font-bold text-gray-800">영업 대응 현황</h1>
      <div class="flex gap-2">
        <button @click="openCreateModal" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
          + 신규 등록
        </button>
      </div>
    </div>

    <!-- 필터 -->
    <div class="bg-white rounded-lg shadow-sm border p-4 mb-4 space-y-3">
      <!-- 상태(다중선택) + 우선도(긴급/중요) 칩 -->
      <div class="flex flex-wrap gap-2 items-center">
        <span class="text-xs text-gray-500 mr-1">상태:</span>
        <button
          v-for="key in STATUS_ORDER" :key="key"
          @click="toggleStatus(key)"
          :class="isStatusOn(key)
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-gray-400 border-gray-300 hover:bg-gray-50'"
          class="px-3 py-1 text-xs font-medium rounded-full border transition-colors"
        >{{ activityStatusLabels[key] }}</button>

        <span class="w-px h-5 bg-gray-200 mx-1.5"></span>
        <span class="text-xs text-gray-500 mr-1">우선도:</span>
        <button
          @click="toggleUrgent"
          :class="filters.urgent
            ? 'bg-red-600 text-white border-red-600'
            : 'bg-white text-gray-400 border-gray-300 hover:bg-gray-50'"
          class="px-3 py-1 text-xs font-medium rounded-full border transition-colors"
        >긴급</button>
        <button
          @click="toggleImportant"
          :class="filters.important
            ? 'bg-amber-500 text-white border-amber-500'
            : 'bg-white text-gray-400 border-gray-300 hover:bg-gray-50'"
          class="px-3 py-1 text-xs font-medium rounded-full border transition-colors"
        >중요</button>

        <div class="flex-1"></div>
        <button @click="resetFilters" type="button"
          class="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 whitespace-nowrap">
          🔄 초기화
        </button>
      </div>

      <!-- 담당자 + 검색 -->
      <div class="flex flex-wrap gap-3 items-center">
        <select v-model="filters.assigned_to" @change="loadData" class="border rounded-md px-3 py-2 text-sm">
          <option value="">전체 담당자</option>
          <option v-for="a in assignees" :key="a" :value="a">{{ a }}</option>
        </select>
        <input v-model="filters.keyword" @input="debouncedLoad" placeholder="프로젝트명 / 거래처 검색..."
          class="border rounded-md px-3 py-2 text-sm flex-1 min-w-[200px]" />
      </div>

      <!-- 문의 유형 필터 (탭 형태) -->
      <div class="flex flex-wrap gap-2 items-center">
        <span class="text-xs text-gray-500 mr-1">문의 유형:</span>
        <button
          @click="selectInquiryType('')"
          :class="filters.inquiry_type === ''
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'"
          class="px-3 py-1 text-xs font-medium rounded-full border transition-colors"
        >전체</button>
        <button
          v-for="(label, key) in inquiryTypeLabels"
          :key="key"
          @click="selectInquiryType(key)"
          :class="filters.inquiry_type === key
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'"
          class="px-3 py-1 text-xs font-medium rounded-full border transition-colors"
        >{{ label }}</button>
      </div>
    </div>

    <!-- 리스트 -->
    <div class="bg-white rounded-lg shadow-sm border overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400">로딩 중...</div>
      <div v-else-if="displayItems.length === 0" class="p-8 text-center text-gray-400">
        <p v-if="filters.statuses.length === 0">상태 칩을 하나 이상 선택하세요.</p>
        <p v-else>필터 조건에 맞는 영업활동이 없습니다.</p>
      </div>

      <!-- 데스크톱 테이블 -->
      <table v-else class="min-w-full divide-y divide-gray-200 hidden sm:table">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">유형</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">나라</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">거래처</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">프로젝트명</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">담당자</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">다음 단계</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">최근 업데이트</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          <tr v-for="item in displayItems" :key="item.id" class="hover:bg-gray-50 cursor-pointer" @click="openDetail(item.id)">
            <td class="px-4 py-3">
              <span :class="activityStatusStyles[item.status]" class="px-2 py-0.5 text-xs font-medium rounded-full">
                {{ activityStatusLabels[item.status] || item.status }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span :class="inquiryTypeStyles[item.inquiry_type || 'GENERAL']" class="px-2 py-0.5 text-xs font-medium rounded-full">
                {{ inquiryTypeLabels[item.inquiry_type || 'GENERAL'] }}
              </span>
            </td>
            <td class="px-4 py-3 text-sm text-gray-600">{{ item.country || '-' }}</td>
            <td class="px-4 py-3 text-sm text-gray-900">{{ item.customer_name || item.customer?.partner_name || '-' }}</td>
            <td class="px-4 py-3 text-sm font-medium text-blue-600">{{ item.title }}</td>
            <td class="px-4 py-3 text-sm text-gray-600">{{ item.assigned_to || '-' }}</td>
            <td class="px-4 py-3 text-sm max-w-[200px] relative">
              <div
                @click.stop="openNextStepPopover(item, $event)"
                class="truncate cursor-pointer hover:bg-blue-50 hover:text-blue-700 rounded px-1 py-0.5 -mx-1 group"
                :title="item.next_step || '클릭하여 입력'"
              >
                <span :class="item.next_step ? 'text-gray-700' : 'text-gray-400 italic'">
                  {{ item.next_step || '+ 다음 단계 입력' }}
                </span>
                <svg class="w-3 h-3 inline ml-1 text-gray-400 opacity-0 group-hover:opacity-100" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </div>
            </td>
            <td class="px-4 py-3 text-sm text-center text-gray-400">{{ formatDate(item.last_log_date || item.updated_at || item.created_at) }}</td>
          </tr>
        </tbody>
      </table>

      <!-- 모바일 카드 -->
      <div v-if="displayItems.length > 0" class="sm:hidden divide-y divide-gray-200">
        <div v-for="item in displayItems" :key="item.id" @click="openDetail(item.id)"
          class="p-4 hover:bg-gray-50 cursor-pointer">
          <div class="flex justify-between items-start mb-2">
            <span class="text-sm font-medium text-blue-600">{{ item.title }}</span>
            <span :class="activityStatusStyles[item.status]" class="px-2 py-0.5 text-xs font-medium rounded-full ml-2">
              {{ activityStatusLabels[item.status] }}
            </span>
          </div>
          <div class="flex items-center gap-1 mb-1">
            <span :class="inquiryTypeStyles[item.inquiry_type || 'GENERAL']" class="px-2 py-0.5 text-[10px] font-medium rounded-full">
              {{ inquiryTypeLabels[item.inquiry_type || 'GENERAL'] }}
            </span>
          </div>
          <div class="text-xs text-gray-500">
            {{ item.country }} · {{ item.customer_name || item.customer?.partner_name }} · {{ item.assigned_to }}
          </div>
          <div v-if="item.next_step" class="text-xs text-gray-400 mt-1 truncate">다음: {{ item.next_step }}</div>
        </div>
      </div>
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

    <!-- 다음 단계 팝오버 -->
    <Teleport to="body">
      <div v-if="nextStepPopover.show"
        class="fixed inset-0 z-40"
        @click="closeNextStepPopover"
      ></div>
      <div v-if="nextStepPopover.show"
        class="fixed z-50 bg-white rounded-lg shadow-xl border p-3 w-80"
        :style="{ top: nextStepPopover.y + 'px', left: nextStepPopover.x + 'px' }"
      >
        <div class="flex items-center gap-2 mb-2">
          <span class="text-sm font-medium text-gray-700">📝 다음 단계 업데이트</span>
        </div>
        <textarea
          ref="nextStepInput"
          v-model="nextStepPopover.value"
          rows="3"
          class="w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          placeholder="다음 진행 단계를 입력하세요..."
          @keydown.ctrl.enter="saveNextStep"
          @keydown.meta.enter="saveNextStep"
          @keydown.escape="closeNextStepPopover"
        ></textarea>
        <div class="flex justify-between items-center mt-2">
          <span class="text-[10px] text-gray-400">Ctrl+Enter로 저장</span>
          <div class="flex gap-1">
            <button @click="closeNextStepPopover" class="px-3 py-1 text-xs text-gray-600 hover:text-gray-800">취소</button>
            <button @click="saveNextStep" :disabled="savingNextStep"
              class="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {{ savingNextStep ? '저장 중...' : '저장' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  salesActivityApi,
  activityStatusLabels,
  activityStatusStyles,
  inquiryTypeLabels,
  inquiryTypeStyles,
  type SalesActivity,
} from '@/api/salesActivity'
import { useToast } from '@/composables/useToast'
import SalesActivityDetailModal from '@/views/sales/activity/SalesActivityDetailModal.vue'
import SalesActivityFormModal from '@/views/sales/activity/SalesActivityFormModal.vue'

const { showToast } = useToast()
const loading = ref(false)
const items = ref<SalesActivity[]>([])
const assignees = ref<string[]>([])
// 상태 칩 순서 + 기본 켜짐(활성 3개). 완료/무산은 기본 OFF.
const STATUS_ORDER = ['IN_PROGRESS', 'WAITING', 'ON_HOLD', 'COMPLETED', 'DROPPED']
const DEFAULT_STATUSES = ['IN_PROGRESS', 'WAITING', 'ON_HOLD']
const filters = ref({
  statuses: [...DEFAULT_STATUSES] as string[],
  assigned_to: '',
  inquiry_type: '',
  keyword: '',
  urgent: false,
  important: false,
})

// 서버가 상태·우선도로 이미 필터링 → 화면은 받은 목록 그대로
const displayItems = computed(() => items.value)

function isStatusOn(key: string) {
  return filters.value.statuses.includes(key)
}
function toggleStatus(key: string) {
  const i = filters.value.statuses.indexOf(key)
  if (i >= 0) filters.value.statuses.splice(i, 1)
  else filters.value.statuses.push(key)
  loadData()
}
function toggleUrgent() { filters.value.urgent = !filters.value.urgent; loadData() }
function toggleImportant() { filters.value.important = !filters.value.important; loadData() }

function selectInquiryType(key: string) {
  filters.value.inquiry_type = key
  loadData()
}

function resetFilters() {
  filters.value = {
    statuses: [...DEFAULT_STATUSES], assigned_to: '', inquiry_type: '', keyword: '',
    urgent: false, important: false,
  }
  loadData()
}

const showDetailModal = ref(false)
const detailId = ref<number | null>(null)
const showFormModal = ref(false)
const editingItem = ref<SalesActivity | null>(null)

async function loadData() {
  loading.value = true
  try {
    // 상태를 하나도 안 켜면 결과 없음(서버 호출 생략)
    if (filters.value.statuses.length === 0) {
      items.value = []
      return
    }
    const params: any = { status: filters.value.statuses }
    if (filters.value.assigned_to) params.assigned_to = filters.value.assigned_to
    if (filters.value.inquiry_type) params.inquiry_type = filters.value.inquiry_type
    if (filters.value.keyword) params.keyword = filters.value.keyword
    if (filters.value.urgent) params.urgent = true
    if (filters.value.important) params.important = true
    const res = await salesActivityApi.getList(params)
    items.value = res.data.items
  } catch {
    showToast('데이터를 불러오는데 실패했습니다', 'error')
  } finally {
    loading.value = false
  }
}

async function loadAssignees() {
  try {
    const res = await salesActivityApi.getAssignees()
    assignees.value = res.data
  } catch { /* ignore */ }
}

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedLoad() { clearTimeout(debounceTimer); debounceTimer = setTimeout(loadData, 300) }

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

// 다음 단계 팝오버
const nextStepInput = ref<HTMLTextAreaElement | null>(null)
const savingNextStep = ref(false)
const nextStepPopover = ref({
  show: false,
  x: 0,
  y: 0,
  value: '',
  activityId: null as number | null,
})

function openNextStepPopover(item: SalesActivity, event: MouseEvent) {
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  // 팝오버를 셀 아래에 표시, 화면 밖으로 나가지 않도록 조정
  let x = rect.left
  let y = rect.bottom + 4
  if (x + 320 > window.innerWidth) x = window.innerWidth - 330
  if (y + 200 > window.innerHeight) y = rect.top - 200

  nextStepPopover.value = {
    show: true,
    x,
    y,
    value: item.next_step || '',
    activityId: item.id,
  }
  // 포커스
  setTimeout(() => nextStepInput.value?.focus(), 50)
}

function closeNextStepPopover() {
  nextStepPopover.value.show = false
  nextStepPopover.value.activityId = null
}

async function saveNextStep() {
  if (!nextStepPopover.value.activityId) return
  savingNextStep.value = true
  try {
    // 다음 단계를 로그로 기록 (타임라인에 남김)
    await salesActivityApi.addLog(nextStepPopover.value.activityId, {
      content: nextStepPopover.value.value,
      log_type: 'NEXT_STEP',
    })
    showToast('다음 단계가 업데이트되었습니다', 'success')
    closeNextStepPopover()
    loadData()
  } catch {
    showToast('저장에 실패했습니다', 'error')
  } finally {
    savingNextStep.value = false
  }
}

function formatDate(d?: string) {
  if (!d) return '-'
  const date = new Date(d)
  return `${date.getFullYear()}.${String(date.getMonth()+1).padStart(2,'0')}.${String(date.getDate()).padStart(2,'0')}`
}

onMounted(() => { loadData(); loadAssignees() })
</script>

