<template>
  <div class="p-4 sm:p-6">
    <!-- 헤더 -->
    <div class="flex flex-wrap gap-2 justify-between items-center mb-6">
      <h1 class="text-xl sm:text-2xl font-bold text-gray-800">전자결재</h1>
      <div class="flex items-center gap-2">
        <!-- 휴가 빠른 작성: 클릭 한 번에 휴가 양식 선택된 작성 화면 -->
        <RouterLink
          to="/approvals/write?form=LEAVE"
          title="휴가 신청서 바로 작성"
          class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          휴가
        </RouterLink>
        <RouterLink
          to="/approvals/write"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          기안 작성
        </RouterLink>
      </div>
    </div>

    <!-- 탭 -->
    <div class="border-b border-gray-200 mb-4">
      <nav class="-mb-px flex flex-wrap gap-x-6">
        <button
          v-for="tab in tabs"
          :key="tab.box"
          @click="changeTab(tab.box)"
          :class="[
            'py-3 px-1 border-b-2 text-sm font-medium transition-colors flex items-center gap-2',
            currentBox === tab.box
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >
          {{ tab.label }}
          <span
            v-if="tab.box === 'pending' && pendingCount > 0"
            class="px-2 py-0.5 text-xs rounded-full bg-red-500 text-white"
          >{{ pendingCount }}</span>
        </button>
      </nav>
    </div>

    <!-- 검색 / 필터 -->
    <div class="flex flex-wrap gap-2 mb-4">
      <input
        v-model="keyword"
        type="text"
        placeholder="문서번호, 제목, 기안자 검색"
        class="flex-1 min-w-[12rem] max-w-md px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        @keyup.enter="reload"
        @input="debouncedSearch"
      />
      <select
        v-model="formCode"
        class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        @change="reload"
      >
        <option value="">전체 종류</option>
        <option v-for="f in forms" :key="f.id" :value="f.code">{{ f.name }}</option>
      </select>
      <select
        v-model="projectId"
        class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        @change="reload"
      >
        <option :value="null">전체 프로젝트</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <select
        v-model="category"
        class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        @change="reload"
      >
        <option value="">전체 구매구분</option>
        <option value="일반">일반</option>
        <option value="과제">과제</option>
        <option value="개발">개발</option>
      </select>
      <select
        v-if="currentBox === 'execution'"
        v-model="executionStatus"
        class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        @change="reload"
      >
        <option value="">시행 전/후 전체</option>
        <option value="PENDING">시행전(대기)</option>
        <option value="DONE">시행후(완료)</option>
      </select>
      <button @click="reload" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">검색</button>
    </div>

    <!-- 모바일 카드 목록 (lg 미만 전용) -->
    <div class="lg:hidden space-y-2">
      <div v-if="loading" class="bg-white rounded-lg shadow p-6 text-center text-gray-500">로딩 중...</div>
      <div v-else-if="items.length === 0" class="bg-white rounded-lg shadow p-6 text-center text-gray-500">문서가 없습니다.</div>
      <button
        v-for="doc in items"
        :key="'m' + doc.id"
        type="button"
        class="w-full text-left bg-white rounded-lg shadow p-3 active:bg-gray-50"
        @click="openDetail(doc)"
      >
        <div class="flex items-center justify-between gap-2">
          <span class="text-xs font-mono text-blue-600 truncate">{{ doc.doc_number }}</span>
          <span class="flex items-center gap-1 whitespace-nowrap">
            <span v-if="doc.is_my_turn" class="px-2 py-0.5 text-[11px] font-bold rounded-full bg-red-100 text-red-700">내 차례</span>
            <span class="px-2 py-0.5 text-[11px] font-medium rounded-full" :class="APPROVAL_STATUS_BADGE[doc.status]">
              {{ APPROVAL_STATUS_LABELS[doc.status] }}
            </span>
          </span>
        </div>
        <div class="mt-1 text-sm font-medium text-gray-900 break-words">{{ doc.title }}</div>
        <div class="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500">
          <span v-if="doc.form_name">{{ doc.form_name }}</span>
          <span>기안 {{ doc.drafter_name || '-' }}</span>
          <span v-if="doc.current_approver_name">현재 {{ doc.current_approver_name }}</span>
          <span>{{ formatDate(doc.drafted_at) }}</span>
        </div>
      </button>
      <Pagination
        v-if="total > 0"
        class="bg-white rounded-lg shadow"
        :total="total"
        :page-size="pageSize"
        :current-page="currentPage"
        @update:current-page="onPageChange"
        @update:page-size="onPageSizeChange"
      />
    </div>

    <!-- 데스크톱 테이블 (lg 이상 전용 — 기존 UI 보존) -->
    <div class="hidden lg:block bg-white rounded-lg shadow overflow-hidden">
      <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">문서번호</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">제목</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">종류</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">프로젝트</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">기안자</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">현재결재자</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">상태</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">상신일</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-if="loading">
            <td colspan="8" class="px-4 py-6 text-center text-gray-500">로딩 중...</td>
          </tr>
          <tr v-else-if="items.length === 0">
            <td colspan="8" class="px-4 py-6 text-center text-gray-500">문서가 없습니다.</td>
          </tr>
          <tr
            v-for="doc in items"
            :key="doc.id"
            class="hover:bg-gray-50 cursor-pointer"
            @click="openDetail(doc)"
          >
            <td class="px-4 py-3 text-sm font-mono text-blue-600 whitespace-nowrap">{{ doc.doc_number }}</td>
            <td class="px-4 py-3 text-sm text-gray-900">{{ doc.title }}</td>
            <td class="px-4 py-3 text-sm text-gray-700 whitespace-nowrap">{{ doc.form_name || '-' }}</td>
            <td class="px-4 py-3 text-sm text-gray-700 whitespace-nowrap">{{ doc.project_name || '-' }}</td>
            <td class="px-4 py-3 text-sm text-gray-700 whitespace-nowrap">{{ doc.drafter_name || '-' }}</td>
            <td class="px-4 py-3 text-sm text-gray-700 whitespace-nowrap">{{ doc.current_approver_name || '-' }}</td>
            <td class="px-4 py-3 text-center whitespace-nowrap">
              <span v-if="doc.is_my_turn" class="mr-1 px-2 py-0.5 text-xs font-bold rounded-full bg-red-100 text-red-700">내 차례</span>
              <span class="px-2 py-0.5 text-xs font-medium rounded-full" :class="APPROVAL_STATUS_BADGE[doc.status]">
                {{ APPROVAL_STATUS_LABELS[doc.status] }}
              </span>
              <span v-if="doc.execution_status" class="ml-1 px-2 py-0.5 text-xs font-medium rounded-full"
                :class="doc.execution_status === 'DONE' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'">
                {{ doc.execution_status === 'DONE' ? '시행후' : '시행전' }}
              </span>
            </td>
            <td class="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{{ formatDate(doc.drafted_at) }}</td>
          </tr>
        </tbody>
      </table>
      </div>

      <Pagination
        v-if="total > 0"
        :total="total"
        :page-size="pageSize"
        :current-page="currentPage"
        @update:current-page="onPageChange"
        @update:page-size="onPageSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import { ref, onMounted, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import Pagination from '@/components/Pagination.vue'
import { useToast } from '@/composables/useToast'
import {
  approvalApi,
  APPROVAL_STATUS_BADGE,
  APPROVAL_STATUS_LABELS,
  type ApprovalListItem,
  type ApprovalForm,
  type ApprovalProject,
  type BoxType,
} from '@/api/approval'

const route = useRoute()
const router = useRouter()
const { error } = useToast()

const tabs: { box: BoxType; label: string }[] = [
  { box: 'drafted', label: '기안함' },
  { box: 'pending', label: '결재대기' },
  { box: 'done', label: '완료함' },
  { box: 'reference', label: '참조함' },
  { box: 'execution', label: '시행함' },
]
const category = ref('')            // 구매 구분 필터(일반/과제/개발)
const executionStatus = ref('')     // 시행함 세부: PENDING(시행전)/DONE(시행후)

const currentBox = ref<BoxType>((route.query.box as BoxType) || 'drafted')
const keyword = ref('')
const formCode = ref('')
const projectId = ref<number | null>(null)
const forms = ref<ApprovalForm[]>([])
const projects = ref<ApprovalProject[]>([])
const items = ref<ApprovalListItem[]>([])
const total = ref(0)
const pageSize = ref(20)
const currentPage = ref(1)
const loading = ref(false)
const pendingCount = ref(0)

const formatDate = (v?: string | null) => (v ? new Date(v).toLocaleDateString('ko-KR') : '-')

const loadData = async () => {
  loading.value = true
  try {
    const res = await approvalApi.getBox({
      box: currentBox.value,
      keyword: keyword.value || undefined,
      form_code: formCode.value || undefined,
      project_id: projectId.value ?? undefined,
      category: category.value || undefined,
      execution_status: currentBox.value === 'execution' ? (executionStatus.value || undefined) : undefined,
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    })
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    error('목록을 불러오지 못했습니다')
  } finally {
    loading.value = false
  }
}

const loadPendingCount = async () => {
  try {
    const res = await approvalApi.pendingCount()
    pendingCount.value = res.data.count
  } catch { /* ignore */ }
}

const loadForms = async () => {
  try {
    const res = await approvalApi.getForms()
    forms.value = [...res.data].sort((a, b) => a.sort_order - b.sort_order)
  } catch { /* ignore */ }
}

const loadProjects = async () => {
  try {
    const res = await approvalApi.getProjects()
    projects.value = res.data
  } catch { /* ignore */ }
}

const debouncedSearch = useDebouncedSearch(() => reload())
const reload = () => {
  currentPage.value = 1
  loadData()
}

const changeTab = (box: BoxType) => {
  if (currentBox.value === box) return
  currentBox.value = box
  keyword.value = ''
  formCode.value = ''
  projectId.value = null
  category.value = ''
  executionStatus.value = ''
  currentPage.value = 1
  router.replace({ query: { box } })
  loadData()
}

const onPageChange = (p: number) => {
  currentPage.value = p
  loadData()
}
const onPageSizeChange = (s: number) => {
  pageSize.value = s
  currentPage.value = 1
  loadData()
}

const openDetail = (doc: ApprovalListItem) => {
  router.push(`/approvals/${doc.id}`)
}

// 다른 화면에서 ?box= 로 진입 시 반영
watch(() => route.query.box, (v) => {
  if (v && v !== currentBox.value) {
    currentBox.value = v as BoxType
    currentPage.value = 1
    loadData()
  }
})

onMounted(() => {
  loadData()
  loadPendingCount()
  loadForms()
  loadProjects()
})
</script>
