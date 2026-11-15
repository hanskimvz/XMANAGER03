<template>
  <div class="max-w-3xl mx-auto px-4 py-6">
    <div class="mb-4">
      <h1 class="text-xl font-bold text-gray-800">내 연차</h1>
      <p class="text-xs text-gray-500 mt-0.5">본인 연차 발생·사용 내역입니다. 신청은 전자결재의 「휴가 신청서」에서 하세요.</p>
    </div>

    <div v-if="loading" class="p-6 text-sm text-gray-400">불러오는 중…</div>

    <template v-else-if="detail">
      <!-- 올해 잔여 -->
      <div class="bg-white rounded-lg shadow border p-5 mb-4 flex items-center justify-between">
        <div>
          <div class="text-xs text-gray-500">{{ detail.current_year }}년 잔여 연차</div>
          <div class="text-3xl font-bold mt-1" :class="detail.current_remaining < 0 ? 'text-red-600' : 'text-blue-600'">
            {{ detail.current_remaining }}<span class="text-base font-medium text-gray-400 ml-1">일</span>
          </div>
        </div>
        <RouterLink to="/approvals/write?form=LEAVE"
          class="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700">휴가 신청</RouterLink>
      </div>

      <!-- 연도별 요약 -->
      <div class="bg-white rounded-lg shadow border mb-4">
        <div class="px-4 py-2 border-b text-sm font-semibold text-gray-700">연도별 현황</div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-gray-500 text-xs">
              <tr>
                <th class="px-3 py-2">연도</th><th class="px-2 py-2 text-right">이월</th>
                <th class="px-2 py-2 text-right">발생</th><th class="px-2 py-2 text-right">사용</th>
                <th class="px-3 py-2 text-right">잔여</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="y in yearsDesc" :key="y.fiscal_year"
                  class="border-t cursor-pointer hover:bg-blue-50"
                  :class="{ 'bg-blue-50': selectedYear === y.fiscal_year }"
                  @click="selectedYear = selectedYear === y.fiscal_year ? null : y.fiscal_year">
                <td class="px-3 py-2 text-center font-medium">{{ y.fiscal_year }}</td>
                <td class="px-2 py-2 text-right text-gray-500">{{ y.carried_in }}</td>
                <td class="px-2 py-2 text-right text-green-600">+{{ y.granted }}</td>
                <td class="px-2 py-2 text-right text-red-500">−{{ y.used }}</td>
                <td class="px-3 py-2 text-right font-bold" :class="y.remaining < 0 ? 'text-red-600' : 'text-blue-600'">{{ y.remaining }}</td>
              </tr>
              <tr v-if="!yearsDesc.length"><td colspan="5" class="px-3 py-4 text-center text-gray-400">내역 없음</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 발생·사용 내역 (거래원장과 동일 형식) -->
      <div class="bg-white rounded-lg shadow border">
        <div class="px-4 py-2 border-b flex items-center justify-between">
          <span class="text-sm font-semibold text-gray-700">발생·사용 내역
            <span v-if="selectedYear" class="text-xs font-normal text-blue-600">· {{ selectedYear }}년만</span>
          </span>
          <button v-if="selectedYear" class="text-xs text-gray-500 hover:text-gray-700" @click="selectedYear = null">전체 보기</button>
        </div>
        <p class="px-4 pt-2 text-[11px] text-gray-400">위 연도별 현황에서 연도를 클릭하면 해당 연도만 표시됩니다.</p>
        <div class="max-h-96 overflow-y-auto">
          <table class="w-full text-xs">
            <thead class="bg-gray-50 text-gray-500 sticky top-0">
              <tr>
                <th class="px-2 py-1.5 text-center">연도</th>
                <th class="px-2 py-1.5 text-left">휴가구분</th>
                <th class="px-2 py-1.5 text-left cursor-pointer select-none hover:text-gray-700" @click="toggleDateSort">사용기간{{ dateSort === 'desc' ? ' ▼' : ' ▲' }}</th>
                <th class="px-2 py-1.5 text-right">휴가증감</th>
                <th class="px-2 py-1.5 text-left">비고</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="e in filteredLedger" :key="e.id" class="border-t" :class="e.voided ? 'line-through text-gray-400 opacity-70' : ''">
                <td class="px-2 py-1 text-center">{{ e.fiscal_year }}</td>
                <td class="px-2 py-1 text-left">{{ e.kind_label }}<span v-if="e.voided" class="ml-1 no-underline">🚫</span></td>
                <td class="px-2 py-1 text-left text-gray-500">{{ e.date_display || e.event_date || '-' }}</td>
                <td class="px-2 py-1 text-right" :class="e.source_type === 'LEAVE_APP' ? 'text-gray-400' : (e.amount >= 0 ? 'text-green-600' : 'text-red-500')">
                  <template v-if="e.source_type === 'LEAVE_APP'">-</template>
                  <template v-else>{{ e.amount >= 0 ? '+' : '' }}{{ e.amount }}</template>
                </td>
                <td class="px-2 py-1 text-left text-gray-600">{{ e.memo_label }}</td>
              </tr>
              <tr v-if="!filteredLedger.length"><td colspan="5" class="px-2 py-4 text-center text-gray-400">내역 없음</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-else class="p-6 text-sm text-gray-400">연차 정보를 불러오지 못했습니다.</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { leaveApi, type LeaveDetail } from '@/api/leave'
import { useToast } from '@/composables/useToast'

const { error } = useToast()
const loading = ref(false)
const detail = ref<LeaveDetail | null>(null)
const selectedYear = ref<number | null>(null)  // 연도별 현황에서 클릭한 연도(필터)
const dateSort = ref<'asc' | 'desc'>('desc')    // 사용 일자 정렬(기본: 최근이 위)

const yearsDesc = computed(() => (detail.value ? [...detail.value.years].reverse() : []))

// 정렬 기준 날짜: event_date 우선, 없으면 사용기간의 시작일
const sortDate = (e: { event_date?: string | null; date_display?: string }) =>
  e.event_date || (e.date_display || '').slice(0, 10) || ''

const filteredLedger = computed(() => {
  let all = detail.value ? [...detail.value.ledger] : []
  if (selectedYear.value) all = all.filter((e) => e.fiscal_year === selectedYear.value)
  const dir = dateSort.value === 'asc' ? 1 : -1
  return all.sort((a, b) => {
    const av = sortDate(a), bv = sortDate(b)
    if (av === bv) return 0
    if (!av) return 1        // 날짜 없는 행은 항상 아래
    if (!bv) return -1
    return av < bv ? -dir : dir
  })
})
function toggleDateSort() {
  dateSort.value = dateSort.value === 'desc' ? 'asc' : 'desc'
}

onMounted(async () => {
  loading.value = true
  try {
    detail.value = await leaveApi.me()
  } catch {
    error('연차 정보를 불러오지 못했습니다')
  } finally {
    loading.value = false
  }
})
</script>
