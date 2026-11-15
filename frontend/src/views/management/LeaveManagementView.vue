<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useToast } from '@/composables/useToast'
import { leaveApi, ENTRY_LABELS, type LeaveOverviewRow, type LeaveDetail, type Settlement } from '@/api/leave'
import { useAuth } from '@/stores/auth'
import { departmentLabel } from '@/api/department'
import { downloadAuthedUrl } from '@/utils/download'

const { success, error, warning } = useToast()
const { isAdmin } = useAuth()  // 퇴사 정산은 관리자만

const rows = ref<LeaveOverviewRow[]>([])
const loading = ref(false)
const selected = ref<LeaveDetail | null>(null)
const settlement = ref<Settlement | null>(null)
const busy = ref(false)
const empForm = ref({ hire_date: '', resign_date: '' })

// 탭: 재직자 / 퇴사자 / 부여 방식
const tab = ref<'active' | 'resigned' | 'grant'>('active')
const activeRows = computed(() => rows.value.filter((r) => !r.resign_date))
const resignedRows = computed(() => rows.value.filter((r) => !!r.resign_date))
const displayRows = computed(() => (tab.value === 'resigned' ? resignedRows.value : activeRows.value))
const selectedSafetyOfficer = computed(
  () => !!rows.value.find((r) => r.user_id === selected.value?.user_id)?.is_safety_officer,
)

async function changeSafetyOfficer(r: LeaveOverviewRow, on: boolean) {
  if (r.is_safety_officer === on) return
  if (on && !confirm(`${r.name} 님을 '산업기능요원'으로 지정합니다.\n연차가 회계연도가 아니라 입사일 기준(근로기준법)으로 재계산됩니다. 계속할까요?`)) return
  busy.value = true
  try {
    const detail = await leaveApi.setSafetyOfficer(r.user_id, on)
    r.is_safety_officer = on
    r.current_remaining = detail.current_remaining
    if (selected.value?.user_id === r.user_id) selected.value = detail
    success(on ? '산업기능요원(입사일 기준)으로 전환했습니다' : '회계연도 기준으로 되돌렸습니다')
  } catch {
    error('산업기능요원 설정 변경에 실패했습니다')
  } finally {
    busy.value = false
  }
}

const curYear = computed(() => rows.value[0]?.current_year ?? new Date().getFullYear())
// 최근 것이 위로(내림차순) — 연도별/원장
const yearsDesc = computed(() => (selected.value ? [...selected.value.years].reverse() : []))
const ledgerDesc = computed(() => (selected.value ? [...selected.value.ledger].reverse() : []))

// 거래 원장 정렬 — 기본값: 일자(event_date) 내림차순(최신 일자가 위)
type LedgerSortKey = 'fiscal_year' | 'entry_type' | 'amount' | 'event_date'
const ledgerSort = ref<{ key: LedgerSortKey | null; dir: 'asc' | 'desc' }>({ key: 'event_date', dir: 'desc' })
// 연도별 현황에서 클릭한 연도(원장 필터). null = 전체
const selectedLedgerYear = ref<number | null>(null)
function toggleLedgerSort(key: LedgerSortKey) {
  if (ledgerSort.value.key === key) {
    ledgerSort.value.dir = ledgerSort.value.dir === 'asc' ? 'desc' : 'asc'
  } else {
    ledgerSort.value = { key, dir: 'asc' }
  }
}
function ledgerArrow(key: LedgerSortKey) {
  if (ledgerSort.value.key !== key) return ''
  return ledgerSort.value.dir === 'asc' ? ' ▲' : ' ▼'
}
const ledgerSorted = computed(() => {
  const base = selectedLedgerYear.value == null
    ? ledgerDesc.value
    : ledgerDesc.value.filter((e) => e.fiscal_year === selectedLedgerYear.value)
  const { key, dir } = ledgerSort.value
  if (!key) return base
  const sign = dir === 'asc' ? 1 : -1
  return [...base].sort((a, b) => {
    const av = key === 'entry_type' ? (ENTRY_LABELS[a.entry_type] || a.entry_type) : a[key]
    const bv = key === 'entry_type' ? (ENTRY_LABELS[b.entry_type] || b.entry_type) : b[key]
    if (av == null && bv == null) return 0
    if (av == null) return 1 // 빈 값은 항상 뒤로
    if (bv == null) return -1
    if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * sign
    return String(av).localeCompare(String(bv), 'ko') * sign
  })
})

async function loadOverview() {
  loading.value = true
  try {
    rows.value = await leaveApi.overview()
  } catch (e: any) {
    error(e?.response?.status === 403 ? '연차 관리 권한이 없습니다(경영지원팀/관리자)' : '연차 현황을 불러오지 못했습니다')
  } finally {
    loading.value = false
  }
}

async function openDetail(userId: number) {
  settlement.value = null
  selectedLedgerYear.value = null  // 직원 전환 시 연도 필터 초기화
  try {
    selected.value = await leaveApi.detail(userId)
    empForm.value = { hire_date: selected.value.hire_date || '', resign_date: selected.value.resign_date || '' }
  } catch {
    error('상세를 불러오지 못했습니다')
  }
}

// 연도별 현황 행 클릭 → 해당 연도만 원장 표시(다시 클릭 시 해제)
function toggleLedgerYear(year: number) {
  selectedLedgerYear.value = selectedLedgerYear.value === year ? null : year
}

async function saveEmployment() {
  if (!selected.value) return
  if (!empForm.value.hire_date) return warning('입사일을 입력하세요')
  busy.value = true
  try {
    selected.value = await leaveApi.setEmployment(selected.value.user_id, empForm.value.hire_date || null, empForm.value.resign_date || null)
    empForm.value = { hire_date: selected.value.hire_date || '', resign_date: selected.value.resign_date || '' }
    await loadOverview()
    success('입사일/퇴사일 저장됨 — 연차 재계산')
  } catch (e: any) {
    error(e?.response?.data?.detail || '저장 실패')
  } finally {
    busy.value = false
  }
}

async function ensureAll() {
  busy.value = true
  try {
    const r = await leaveApi.ensureAll()
    success(`일괄 처리 완료 — 대상 ${r.users}명, 재계산 ${r.grants_recomputed}건`)
    await loadOverview()
    if (selected.value) await openDetail(selected.value.user_id)
  } catch {
    error('일괄 처리 실패')
  } finally {
    busy.value = false
  }
}

// 조정 입력
const adj = ref({ fiscal_year: curYear.value, amount: 0, memo: '' })
async function submitAdjust() {
  if (!selected.value) return
  if (!adj.value.memo.trim()) return warning('조정 사유를 입력하세요')
  if (!adj.value.amount) return warning('조정 일수를 입력하세요(+추가/−차감)')
  busy.value = true
  try {
    selected.value = await leaveApi.adjust(selected.value.user_id, adj.value.fiscal_year, adj.value.amount, adj.value.memo.trim())
    adj.value = { fiscal_year: curYear.value, amount: 0, memo: '' }
    await loadOverview()
    success('조정 반영됨')
  } catch (e: any) {
    error(e?.response?.data?.detail || '조정 실패')
  } finally {
    busy.value = false
  }
}

// 연말 수당 지급 입력
const allow = ref({ fiscal_year: curYear.value - 1, days: 0, memo: '' })
async function submitAllowance() {
  if (!selected.value) return
  if (!allow.value.days || allow.value.days <= 0) return warning('지급 일수를 입력하세요')
  busy.value = true
  try {
    selected.value = await leaveApi.payAllowance(selected.value.user_id, allow.value.fiscal_year, allow.value.days, allow.value.memo.trim() || undefined)
    allow.value = { fiscal_year: curYear.value - 1, days: 0, memo: '' }
    await loadOverview()
    success('연차수당 지급 반영됨 (다음 해 이월에서 차감)')
  } catch (e: any) {
    error(e?.response?.data?.detail || '수당 입력 실패')
  } finally {
    busy.value = false
  }
}

// 과거 휴가 소급 기입 (날짜 + 일수)
const usage = ref({ event_date: '', days: 1, memo: '' })
async function submitUsage() {
  if (!selected.value) return
  if (!usage.value.event_date) return warning('휴가 날짜를 선택하세요')
  if (!usage.value.days || usage.value.days <= 0) return warning('사용 일수를 입력하세요')
  busy.value = true
  try {
    selected.value = await leaveApi.addUsage(selected.value.user_id, usage.value.event_date, usage.value.days, usage.value.memo.trim() || undefined)
    usage.value = { event_date: '', days: 1, memo: '' }
    await loadOverview()
    success('과거 휴가 기입됨 (잔여·정산·엑셀에 반영)')
  } catch (e: any) {
    error(e?.response?.data?.detail || '휴가 기입 실패')
  } finally {
    busy.value = false
  }
}

// 회사 전체 휴가 시행 (일부 제외 가능)
const showCompany = ref(false)
const company = ref({ event_date: '', days: 1, memo: '' })
const excludeIds = ref<Set<number>>(new Set())
function toggleExclude(id: number) {
  const s = new Set(excludeIds.value)
  s.has(id) ? s.delete(id) : s.add(id)
  excludeIds.value = s
}
function openCompany() {
  company.value = { event_date: '', days: 1, memo: '' }
  excludeIds.value = new Set()
  showCompany.value = true
}
async function submitCompanyWide() {
  if (!company.value.event_date) return warning('휴가 날짜를 선택하세요')
  if (!company.value.days || company.value.days <= 0) return warning('차감 일수를 입력하세요')
  if (!company.value.memo.trim()) return warning('사유를 입력하세요')
  const applied = rows.value.length - excludeIds.value.size
  if (!confirm(`회사 전체 휴가 시행: ${company.value.event_date}, ${company.value.days}일 차감.\n대상 ${applied}명(제외 ${excludeIds.value.size}명). 진행할까요?`)) return
  busy.value = true
  try {
    const r = await leaveApi.companyWide(company.value.event_date, company.value.days, company.value.memo.trim(), Array.from(excludeIds.value))
    success(`회사 전체 휴가 반영 — 적용 ${r.applied}명, 제외 ${r.excluded}명`)
    showCompany.value = false
    await loadOverview()
    if (selected.value) await openDetail(selected.value.user_id)
  } catch (e: any) {
    error(e?.response?.data?.detail || '회사 전체 휴가 시행 실패')
  } finally {
    busy.value = false
  }
}

async function runSettlement() {
  if (!selected.value) return
  try {
    settlement.value = await leaveApi.settlement(selected.value.user_id, selected.value.resign_date || undefined)
  } catch (e: any) {
    error(e?.response?.data?.detail || '정산 계산 실패')
  }
}

async function downloadSettlementExcel() {
  if (!selected.value) return
  const u = selected.value
  const params = u.resign_date ? { asof: u.resign_date } : {}
  try {
    await downloadAuthedUrl(`/leave/${u.user_id}/settlement.xlsx`, `연차정산_${u.name}.xlsx`, params)
  } catch (e: any) {
    error(e?.response?.data?.detail || '엑셀 다운로드 실패')
  }
}

async function delEntry(id: number) {
  if (!selected.value) return
  if (!confirm('이 원장 항목을 삭제할까요? (수동 조정/수당만 가능)')) return
  try {
    await leaveApi.deleteEntry(id)
    selected.value = await leaveApi.detail(selected.value.user_id)
    await loadOverview()
    success('삭제됨')
  } catch (e: any) {
    error(e?.response?.data?.detail || '삭제 실패')
  }
}

onMounted(loadOverview)
</script>

<template>
  <div class="max-w-screen-xl mx-auto px-4 py-6">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-xl font-bold text-gray-800">연차 관리 <span class="text-sm font-normal text-gray-400">(경영지원팀)</span></h1>
        <p class="text-xs text-gray-500 mt-0.5">회계연도 기준 자동 발생 · 이월 · 연차수당 · 퇴사 정산. 입사일 미입력자는 사용자 관리에서 먼저 입력하세요.</p>
      </div>
      <div class="flex items-center gap-2">
        <button :disabled="busy" class="btn-indigo" @click="openCompany">회사 전체 휴가 시행</button>
        <button :disabled="busy" class="btn-primary" @click="ensureAll">전 직원 일괄 생성/동기화</button>
      </div>
    </div>

    <!-- 탭: 재직자 / 퇴사자 / 부여 방식 -->
    <div class="flex gap-1 mb-3 border-b">
      <button @click="tab = 'active'" class="px-4 py-2 text-sm font-medium -mb-px border-b-2"
        :class="tab === 'active' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'">
        재직자 <span class="text-xs text-gray-400">({{ activeRows.length }})</span>
      </button>
      <button @click="tab = 'resigned'" class="px-4 py-2 text-sm font-medium -mb-px border-b-2"
        :class="tab === 'resigned' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'">
        퇴사자 <span class="text-xs text-gray-400">({{ resignedRows.length }})</span>
      </button>
      <button @click="tab = 'grant'" class="px-4 py-2 text-sm font-medium -mb-px border-b-2"
        :class="tab === 'grant' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'">
        부여 방식
      </button>
    </div>

    <!-- 부여 방식 관리 탭 -->
    <div v-if="tab === 'grant'" class="bg-white rounded-lg shadow border">
      <div class="px-4 py-2 border-b text-sm font-semibold text-gray-700">부여 방식 관리 — 산업기능요원 지정</div>
      <p class="px-4 py-2 text-xs text-gray-500">
        기본은 <b>회계연도 기준</b> 자동 발생입니다.
        <b>산업기능요원</b>으로 체크하면 <b>입사일 기준(근로기준법)</b>으로 발생합니다 —
        1년 미만은 매월 개근 1일씩(도래한 달만), 입사 1년째부터 15일 일괄 + 근속가산(3년 16, 5년 17 …).
      </p>
      <div v-if="loading" class="p-4 text-sm text-gray-400">불러오는 중…</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 text-gray-500 text-xs">
          <tr><th class="px-3 py-2 text-left">이름</th><th class="px-2 py-2 text-left">부서</th><th class="px-2 py-2 text-center">입사일</th><th class="px-2 py-2 text-center">상태</th><th class="px-3 py-2 text-center">산업기능요원<br><span class="font-normal text-[10px] text-gray-400">(입사일 기준)</span></th></tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.user_id" class="border-t">
            <td class="px-3 py-2 font-medium text-gray-800">{{ r.name }} <span class="text-gray-400 text-xs">{{ r.position || '' }}</span></td>
            <td class="px-2 py-2 text-gray-600">{{ departmentLabel(r.department) }}</td>
            <td class="px-2 py-2 text-center text-xs" :class="r.has_hire_date ? 'text-gray-600' : 'text-red-500'">{{ r.hire_date || '미입력' }}</td>
            <td class="px-2 py-2 text-center text-xs" :class="r.resign_date ? 'text-gray-400' : 'text-green-600'">{{ r.resign_date ? '퇴사' : '재직' }}</td>
            <td class="px-3 py-2 text-center">
              <input type="checkbox" class="w-4 h-4 accent-blue-600 disabled:opacity-40"
                :checked="r.is_safety_officer" :disabled="busy"
                @change="changeSafetyOfficer(r, ($event.target as HTMLInputElement).checked)" />
            </td>
          </tr>
          <tr v-if="!rows.length"><td colspan="5" class="px-3 py-4 text-center text-gray-400">직원 없음</td></tr>
        </tbody>
      </table>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-5 gap-4">
      <!-- 좌: 직원 목록 -->
      <div class="lg:col-span-2 bg-white rounded-lg shadow border">
        <div class="px-4 py-2 border-b text-sm font-semibold text-gray-700">{{ tab === 'resigned' ? '퇴사자' : '재직자' }} ({{ curYear }}년 잔여)</div>
        <div v-if="loading" class="p-4 text-sm text-gray-400">불러오는 중…</div>
        <table v-else class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-500 text-xs">
            <tr><th class="px-3 py-2 text-left">이름</th><th class="px-2 py-2 text-left">부서</th><th class="px-2 py-2 text-center">입사일</th><th class="px-3 py-2 text-right">잔여</th></tr>
          </thead>
          <tbody>
            <tr v-if="!displayRows.length"><td colspan="4" class="px-3 py-4 text-center text-gray-400">{{ tab === 'resigned' ? '퇴사자' : '재직자' }} 없음</td></tr>
            <tr v-for="r in displayRows" :key="r.user_id"
                class="border-t cursor-pointer hover:bg-blue-50"
                :class="{ 'bg-blue-50': selected?.user_id === r.user_id }"
                @click="openDetail(r.user_id)">
              <td class="px-3 py-2 font-medium text-gray-800">{{ r.name }} <span class="text-gray-400 text-xs">{{ r.position || '' }}</span></td>
              <td class="px-2 py-2 text-gray-600">{{ departmentLabel(r.department) }}</td>
              <td class="px-2 py-2 text-center text-xs" :class="r.has_hire_date ? 'text-gray-600' : 'text-red-500'">
                {{ r.hire_date || '미입력' }}
              </td>
              <td class="px-3 py-2 text-right font-bold" :class="r.current_remaining < 0 ? 'text-red-600' : 'text-blue-600'">
                {{ r.has_hire_date ? r.current_remaining : '-' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 우: 상세 -->
      <div class="lg:col-span-3 space-y-4">
        <div v-if="!selected" class="bg-white rounded-lg shadow border p-8 text-center text-gray-400 text-sm">
          왼쪽에서 직원을 선택하세요.
        </div>
        <template v-else>
          <!-- 연도별 표 -->
          <div class="bg-white rounded-lg shadow border">
            <div class="px-4 py-2 border-b flex flex-wrap items-center justify-between gap-2">
              <span class="text-sm font-semibold text-gray-700">
                {{ selected.name }} — 연도별 현황
                <span v-if="selectedSafetyOfficer" class="ml-1 px-1.5 py-0.5 text-[11px] rounded bg-emerald-100 text-emerald-700" title="산업기능요원 — 입사일 기준(근로기준법) 발생">입사일 기준</span>
                <span v-else class="ml-1 px-1.5 py-0.5 text-[11px] rounded bg-blue-100 text-blue-700">회계연도 기준</span>
              </span>
              <div class="flex items-center gap-1.5 text-xs">
                <label class="text-gray-500">입사</label>
                <input v-model="empForm.hire_date" type="date" class="emp-date" />
                <label class="text-gray-500 ml-1">퇴사</label>
                <input v-model="empForm.resign_date" type="date" class="emp-date" />
                <button :disabled="busy" class="btn-gray !px-2 !py-1 !text-xs" @click="saveEmployment">저장</button>
              </div>
            </div>
            <div class="max-h-56 overflow-y-auto">
            <table class="w-full text-sm">
              <thead class="bg-gray-50 text-gray-500 text-xs sticky top-0 z-10">
                <tr><th class="px-3 py-2">연도</th><th class="px-2 py-2 text-right">이월</th><th class="px-2 py-2 text-right">발생</th><th class="px-2 py-2 text-right">사용</th><th class="px-2 py-2 text-right">수당</th><th class="px-2 py-2 text-right">조정</th><th class="px-3 py-2 text-right">잔여</th></tr>
              </thead>
              <tbody>
                <tr v-for="y in yearsDesc" :key="y.fiscal_year"
                    class="border-t cursor-pointer hover:bg-gray-50"
                    :class="{ 'bg-blue-50': selectedLedgerYear === y.fiscal_year }"
                    :title="`${y.fiscal_year}년 원장만 보기`"
                    @click="toggleLedgerYear(y.fiscal_year)">
                  <td class="px-3 py-2 text-center font-medium">{{ y.fiscal_year }}</td>
                  <td class="px-2 py-2 text-right text-gray-500">{{ y.carried_in }}</td>
                  <td class="px-2 py-2 text-right text-green-600">+{{ y.granted }}</td>
                  <td class="px-2 py-2 text-right text-red-500">−{{ y.used }}</td>
                  <td class="px-2 py-2 text-right text-orange-500">−{{ y.allowance_paid }}</td>
                  <td class="px-2 py-2 text-right text-gray-500">{{ y.adjust > 0 ? '+' : '' }}{{ y.adjust }}</td>
                  <td class="px-3 py-2 text-right font-bold" :class="y.remaining < 0 ? 'text-red-600' : 'text-blue-600'">{{ y.remaining }}</td>
                </tr>
              </tbody>
            </table>
            </div>
          </div>

          <!-- 액션: 수당 / 조정 / 정산 -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- 연말 수당 지급 -->
            <div class="bg-white rounded-lg shadow border p-4">
              <div class="text-sm font-semibold text-gray-700 mb-2">연말 연차수당 지급</div>
              <p class="text-[11px] text-gray-400 mb-2">지급분만큼 다음 해 이월에서 자동 차감됩니다.</p>
              <div class="flex items-end gap-2">
                <div><label class="block text-xs text-gray-500">연도</label><input v-model.number="allow.fiscal_year" type="number" class="inp w-20" /></div>
                <div><label class="block text-xs text-gray-500">지급 일수</label><input v-model.number="allow.days" type="number" step="0.5" class="inp w-24" /></div>
                <button :disabled="busy" class="btn-orange" @click="submitAllowance">지급</button>
              </div>
              <input v-model="allow.memo" placeholder="비고(선택)" class="inp w-full mt-2" />
            </div>

            <!-- 수동 조정 -->
            <div class="bg-white rounded-lg shadow border p-4">
              <div class="text-sm font-semibold text-gray-700 mb-2">수동 조정 / 도입 초기값</div>
              <p class="text-[11px] text-gray-400 mb-2">자동계산 위 강제 입력(+추가 / −차감). 사유 필수.</p>
              <div class="flex items-end gap-2">
                <div><label class="block text-xs text-gray-500">연도</label><input v-model.number="adj.fiscal_year" type="number" class="inp w-20" /></div>
                <div><label class="block text-xs text-gray-500">일수(±)</label><input v-model.number="adj.amount" type="number" step="0.5" class="inp w-24" /></div>
                <button :disabled="busy" class="btn-gray" @click="submitAdjust">반영</button>
              </div>
              <input v-model="adj.memo" placeholder="사유(필수)" class="inp w-full mt-2" />
            </div>

            <!-- 과거 휴가 소급 기입 (날짜) -->
            <div class="bg-white rounded-lg shadow border p-4 md:col-span-2">
              <div class="text-sm font-semibold text-gray-700 mb-2">과거 휴가 기입 (누락분 소급)</div>
              <p class="text-[11px] text-gray-400 mb-2">과거에 누락된 휴가 사용을 실제 날짜로 기입합니다. 사용으로 잡혀 잔여·정산·엑셀에 반영됩니다.</p>
              <div class="flex flex-wrap items-end gap-2">
                <div><label class="block text-xs text-gray-500">휴가 날짜</label><input v-model="usage.event_date" type="date" class="inp" /></div>
                <div><label class="block text-xs text-gray-500">사용 일수</label><input v-model.number="usage.days" type="number" step="0.5" min="0.5" class="inp w-24" /></div>
                <input v-model="usage.memo" placeholder="비고(선택)" class="inp flex-1 min-w-[8rem]" />
                <button :disabled="busy" class="btn-gray" @click="submitUsage">기입</button>
              </div>
            </div>
          </div>

          <!-- 퇴사 정산 (관리자 전용) -->
          <div v-if="isAdmin" class="bg-white rounded-lg shadow border p-4">
            <div class="flex items-center justify-between">
              <span class="text-sm font-semibold text-gray-700">퇴사 정산 (법정·노동부 규정)</span>
              <div class="flex gap-2">
                <button class="btn-gray" @click="runSettlement">정산 계산</button>
                <button class="btn-green" @click="downloadSettlementExcel">📄 엑셀 다운로드</button>
              </div>
            </div>
            <div v-if="settlement" class="mt-3 text-sm grid grid-cols-2 sm:grid-cols-5 gap-2">
              <div class="stat"><span>법정 발생</span><b>{{ settlement.legal_entitlement }}</b></div>
              <div class="stat"><span>수동 조정(±)</span><b :class="settlement.adjust < 0 ? 'text-red-600' : 'text-gray-700'">{{ settlement.adjust > 0 ? '+' : '' }}{{ settlement.adjust }}</b></div>
              <div class="stat"><span>총 사용</span><b>{{ settlement.used }}</b></div>
              <div class="stat"><span>기지급 수당</span><b>{{ settlement.allowance_paid }}</b></div>
              <div class="stat bg-blue-50"><span>미정산(퇴직금)</span><b class="text-blue-700">{{ settlement.unsettled_days }}일</b></div>
              <p class="col-span-full text-[11px] text-gray-500">미정산 = 법정 발생 + 수동조정 − 사용 − 기지급 수당</p>
              <p class="col-span-full text-[11px] text-amber-600">{{ settlement.note }}</p>
            </div>
          </div>

          <!-- 원장 -->
          <div class="bg-white rounded-lg shadow border">
            <div class="px-4 py-2 border-b flex items-center justify-between gap-2">
              <span class="text-sm font-semibold text-gray-700">
                거래 원장 (감사)
                <span v-if="selectedLedgerYear" class="ml-1 text-xs font-normal text-blue-600">· {{ selectedLedgerYear }}년만</span>
              </span>
              <button v-if="selectedLedgerYear" class="text-xs text-gray-500 hover:text-gray-700" @click="selectedLedgerYear = null">전체 보기</button>
              <span v-else class="text-[11px] text-gray-400">위 연도별 현황에서 연도를 클릭하면 해당 연도만 표시</span>
            </div>
            <div class="max-h-72 overflow-y-auto">
            <table class="w-full text-xs">
              <thead class="bg-gray-50 text-gray-500 sticky top-0 z-10"><tr><th class="px-2 py-1 cursor-pointer select-none hover:text-gray-700" @click="toggleLedgerSort('fiscal_year')">연도{{ ledgerArrow('fiscal_year') }}</th><th class="px-2 py-1 text-left">휴가구분</th><th class="px-2 py-1 text-left cursor-pointer select-none hover:text-gray-700" @click="toggleLedgerSort('event_date')">사용기간{{ ledgerArrow('event_date') }}</th><th class="px-2 py-1 text-right cursor-pointer select-none hover:text-gray-700" @click="toggleLedgerSort('amount')">휴가증감{{ ledgerArrow('amount') }}</th><th class="px-2 py-1 text-left">비고</th><th class="px-2 py-1"></th></tr></thead>
              <tbody>
                <tr v-for="e in ledgerSorted" :key="e.id" class="border-t" :class="e.voided ? 'line-through text-gray-400 opacity-70' : ''">
                  <td class="px-2 py-1 text-center">{{ e.fiscal_year }}</td>
                  <td class="px-2 py-1 text-left">{{ e.kind_label }}<span v-if="e.voided" class="ml-1 no-underline">🚫</span></td>
                  <td class="px-2 py-1 text-left text-gray-500">{{ e.date_display || e.event_date || '-' }}</td>
                  <td class="px-2 py-1 text-right" :class="e.voided ? '' : (e.source_type === 'LEAVE_APP' ? 'text-gray-400' : (e.amount >= 0 ? 'text-green-600' : 'text-red-500'))"><template v-if="e.source_type === 'LEAVE_APP'">-</template><template v-else>{{ e.amount >= 0 ? '+' : '' }}{{ e.amount }}</template></td>
                  <td class="px-2 py-1 text-left text-gray-600">{{ e.memo_label }}</td>
                  <td class="px-2 py-1 text-center">
                    <button v-if="e.source_type === 'MANUAL'" class="text-red-400 hover:text-red-600" @click="delEntry(e.id)">삭제</button>
                  </td>
                </tr>
                <tr v-if="!ledgerSorted.length"><td colspan="6" class="px-2 py-4 text-center text-gray-400">{{ selectedLedgerYear ? `${selectedLedgerYear}년 내역 없음` : '원장 없음' }}</td></tr>
              </tbody>
            </table>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 회사 전체 휴가 시행 모달 -->
    <div v-if="showCompany" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" @click.self="showCompany = false">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-lg flex flex-col max-h-[90vh]">
        <div class="flex items-center justify-between px-5 py-3 border-b">
          <h3 class="text-base font-semibold text-gray-800">회사 전체 휴가 시행</h3>
          <button @click="showCompany = false" class="text-gray-400 hover:text-gray-600" aria-label="닫기">✕</button>
        </div>
        <div class="px-5 py-4 space-y-3 overflow-y-auto">
          <p class="text-[12px] text-gray-500">전 재직자에게 지정한 날짜의 휴가를 일괄 차감합니다. 아래에서 <b>체크한 인원은 제외</b>됩니다.</p>
          <div class="flex flex-wrap items-end gap-2">
            <div><label class="block text-xs text-gray-500">휴가 날짜</label><input v-model="company.event_date" type="date" class="inp" /></div>
            <div><label class="block text-xs text-gray-500">차감 일수</label><input v-model.number="company.days" type="number" step="0.5" min="0.5" class="inp w-24" /></div>
            <input v-model="company.memo" placeholder="사유(필수, 예: 창립기념일 휴무)" class="inp flex-1 min-w-[10rem]" />
          </div>
          <div>
            <div class="flex items-center justify-between mb-1">
              <span class="text-xs font-semibold text-gray-600">제외할 인원 (체크)</span>
              <span class="text-[11px] text-gray-400">대상 {{ rows.length - excludeIds.size }}명 / 제외 {{ excludeIds.size }}명</span>
            </div>
            <div class="border rounded-md max-h-56 overflow-y-auto divide-y">
              <label v-for="r in rows" :key="r.user_id" class="flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-gray-50 cursor-pointer">
                <input type="checkbox" :checked="excludeIds.has(r.user_id)" @change="toggleExclude(r.user_id)" />
                <span class="font-medium text-gray-800">{{ r.name }}</span>
                <span class="text-xs text-gray-400">{{ r.position || '' }} · {{ departmentLabel(r.department) }}</span>
                <span v-if="excludeIds.has(r.user_id)" class="ml-auto text-[11px] text-red-500">제외</span>
              </label>
              <div v-if="!rows.length" class="px-3 py-4 text-center text-sm text-gray-400">재직자 없음</div>
            </div>
          </div>
        </div>
        <div class="px-5 py-3 border-t flex justify-end gap-2">
          <button type="button" @click="showCompany = false" class="px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded">취소</button>
          <button :disabled="busy" @click="submitCompanyWide" class="btn-indigo">{{ busy ? '처리 중...' : '전체 시행' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.btn-primary { @apply px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50; }
.btn-indigo { @apply px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-50; }
.btn-orange { @apply px-3 py-1.5 bg-orange-500 text-white text-sm rounded-md hover:bg-orange-600 disabled:opacity-50; }
.btn-gray { @apply px-3 py-1.5 bg-gray-600 text-white text-sm rounded-md hover:bg-gray-700 disabled:opacity-50; }
.btn-green { @apply px-3 py-1.5 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:opacity-50; }
.inp { @apply px-2 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500; }
.emp-date { @apply px-1.5 py-1 border border-gray-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500; }
.stat { @apply flex flex-col items-center justify-center p-2 rounded-md bg-gray-50; }
.stat span { @apply text-[11px] text-gray-500; }
.stat b { @apply text-base; }
</style>
