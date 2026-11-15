<template>
  <div class="p-4 sm:p-6">
    <!-- 연도 선택 -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <button @click="changeYear(-1)" class="p-1 hover:bg-gray-100 rounded">
          <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <span class="text-lg font-bold text-gray-800">{{ selectedYear }}년</span>
        <button @click="changeYear(1)" class="p-1 hover:bg-gray-100 rounded">
          <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
          </svg>
        </button>
      </div>
      <button @click="loadData" class="px-3 py-1.5 text-sm border rounded hover:bg-gray-50">새로고침</button>
    </div>

    <div v-if="loading" class="p-12 text-center text-gray-400">로딩 중...</div>

    <template v-else-if="data">
      <!-- 1. 핵심 지표 카드 -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <!-- 이달 매출 -->
        <div class="bg-white rounded-lg shadow-sm border p-4">
          <p class="text-xs text-gray-500 mb-1">이달 매출 (CI)</p>
          <p class="text-xl font-bold text-blue-600">${{ formatAmount(data.this_month.ci_amount) }}</p>
          <p class="text-[10px] text-gray-400 mt-1">{{ data.this_month.ci_count }}건</p>
        </div>
        <!-- 다음달 예상 -->
        <div class="bg-white rounded-lg shadow-sm border p-4">
          <p class="text-xs text-gray-500 mb-1">다음달 예상</p>
          <p class="text-xl font-bold text-indigo-600">${{ formatAmount(data.next_month.ci_amount) }}</p>
          <p class="text-[10px] text-gray-400 mt-1">
            확정 {{ data.next_month.ci_count }}건
            <span v-if="data.next_month.pipeline_amount > 0" class="ml-1">
              + 파이프라인 ${{ formatAmount(data.next_month.pipeline_amount) }}
            </span>
          </p>
        </div>
        <!-- 미입금 -->
        <div class="bg-white rounded-lg shadow-sm border p-4" :class="data.unpaid.total_amount > 0 ? 'border-red-200' : ''">
          <p class="text-xs text-gray-500 mb-1">미입금 잔액</p>
          <p class="text-xl font-bold" :class="data.unpaid.total_amount > 0 ? 'text-red-600' : 'text-gray-400'">
            ${{ formatAmount(data.unpaid.total_amount) }}
          </p>
          <p class="text-[10px] text-gray-400 mt-1">
            미입금 {{ data.unpaid.unpaid_count }}건
            <span v-if="data.unpaid.partial_count > 0">· 부분입금 {{ data.unpaid.partial_count }}건</span>
          </p>
        </div>
        <!-- 연간 누적 -->
        <div class="bg-white rounded-lg shadow-sm border p-4">
          <p class="text-xs text-gray-500 mb-1">{{ selectedYear }}년 누적 매출</p>
          <p class="text-xl font-bold text-green-600">${{ formatAmount(data.yearly_total.ci_amount) }}</p>
          <p class="text-[10px] text-gray-400 mt-1">CI {{ data.yearly_total.ci_count }}건</p>
        </div>
        <!-- 미실현 매출 -->
        <div v-if="data.unrealized" class="bg-white rounded-lg shadow-sm border p-4"
          :class="data.unrealized.unrealized_amount > 0 ? 'border-orange-200' : ''">
          <p class="text-xs text-gray-500 mb-1">미실현 매출</p>
          <p class="text-xl font-bold" :class="data.unrealized.unrealized_amount > 0 ? 'text-orange-600' : 'text-gray-400'">
            ${{ formatAmount(data.unrealized.unrealized_amount) }}
          </p>
          <p class="text-[10px] text-gray-400 mt-1">확정 PI 중 CI 미발행 {{ data.unrealized.unconverted_pi_count }}건</p>
        </div>
      </div>

      <!-- 2. 견적 전환율 + 담당자 실적 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <!-- 견적 전환율 -->
        <div class="bg-white rounded-lg shadow-sm border p-4">
          <h3 class="text-sm font-bold text-gray-700 mb-3">견적 전환율</h3>
          <div class="flex items-center gap-6">
            <div class="relative w-20 h-20">
              <svg class="w-20 h-20 transform -rotate-90" viewBox="0 0 36 36">
                <circle cx="18" cy="18" r="15" fill="none" stroke="#e5e7eb" stroke-width="3"/>
                <circle cx="18" cy="18" r="15" fill="none" stroke="#3b82f6" stroke-width="3"
                  :stroke-dasharray="`${data.conversion_rate.rate * 0.942} 94.2`" stroke-linecap="round"/>
              </svg>
              <span class="absolute inset-0 flex items-center justify-center text-sm font-bold text-blue-600">
                {{ data.conversion_rate.rate }}%
              </span>
            </div>
            <div class="text-sm text-gray-600">
              <p>총 견적: <span class="font-medium">{{ data.conversion_rate.total_quotations }}건</span></p>
              <p>PI 전환: <span class="font-medium text-blue-600">{{ data.conversion_rate.confirmed_quotations }}건</span></p>
            </div>
          </div>
        </div>

        <!-- 담당자별 실적 -->
        <div class="bg-white rounded-lg shadow-sm border p-4">
          <h3 class="text-sm font-bold text-gray-700 mb-3">담당자별 영업활동</h3>
          <div v-if="data.assignee_stats.length === 0" class="text-sm text-gray-400 text-center py-4">데이터 없음</div>
          <div v-else class="space-y-2">
            <div v-for="a in data.assignee_stats" :key="a.name" class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-800">{{ a.name }}</span>
              <div class="flex items-center gap-3 text-xs">
                <span class="text-blue-600">진행 {{ a.in_progress }}건</span>
                <span class="text-green-600">완료 {{ a.completed }}건</span>
                <span class="text-gray-400">총 {{ a.total }}건</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 3. 월별 매출 추이 (바 차트 - CSS only) -->
      <div class="bg-white rounded-lg shadow-sm border p-4 mb-6">
        <h3 class="text-sm font-bold text-gray-700 mb-4">월별 매출 추이 (CI 기준)</h3>
        <div v-if="data.monthly_trend.length === 0" class="text-sm text-gray-400 text-center py-8">데이터 없음</div>
        <div v-else class="overflow-x-auto">
          <div class="flex items-end gap-3 min-w-[600px] pl-2 pt-6" style="height: 220px;">
            <div v-for="m in data.monthly_trend" :key="m.month"
              class="flex flex-col items-center justify-end gap-1" style="width: 48px;">
              <!-- PI 바 -->
              <div class="w-8 bg-blue-500 rounded-t transition-all duration-300 min-h-[2px] relative group"
                :style="{ height: barHeight(m.ci_amount) + 'px' }">
                <div class="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100
                  bg-gray-800 text-white text-[10px] px-1.5 py-0.5 rounded whitespace-nowrap transition-opacity z-10 pointer-events-none">
                  ${{ formatAmount(m.ci_amount) }}
                </div>
              </div>
              <!-- 월 라벨 -->
              <span class="text-[10px] text-gray-500 mt-1">{{ m.month.split('-')[1] }}월</span>
            </div>
          </div>
          <!-- 범례 -->
          <div class="flex items-center gap-4 mt-3 text-[10px] text-gray-500 justify-end">
            <span class="flex items-center gap-1"><span class="w-3 h-3 bg-blue-500 rounded"></span>CI 매출</span>
          </div>
        </div>
      </div>

      <!-- 4. 거래처별 매출 랭킹 -->
      <div class="bg-white rounded-lg shadow-sm border p-4">
        <h3 class="text-sm font-bold text-gray-700 mb-3">거래처별 매출 TOP 10 (CI 기준)</h3>
        <div v-if="data.customer_ranking.length === 0" class="text-sm text-gray-400 text-center py-6">데이터 없음</div>
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="text-xs text-gray-500 border-b">
              <th class="text-left py-2 px-2">#</th>
              <th class="text-left py-2 px-2">거래처</th>
              <th class="text-left py-2 px-2">국가</th>
              <th class="text-right py-2 px-2">매출액</th>
              <th class="text-right py-2 px-2">건수</th>
              <th class="text-left py-2 px-2 w-1/3">비중</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(c, idx) in data.customer_ranking" :key="c.name" class="border-b last:border-b-0">
              <td class="py-2 px-2 text-gray-400">{{ idx + 1 }}</td>
              <td class="py-2 px-2 font-medium">{{ c.name }}</td>
              <td class="py-2 px-2 text-gray-500">{{ c.country || '-' }}</td>
              <td class="py-2 px-2 text-right font-medium">${{ formatAmount(c.amount) }}</td>
              <td class="py-2 px-2 text-right text-gray-500">{{ c.count }}건</td>
              <td class="py-2 px-2">
                <div class="flex items-center gap-2">
                  <div class="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div class="h-full bg-blue-500 rounded-full" :style="{ width: customerShare(c.amount) + '%' }"></div>
                  </div>
                  <span class="text-[10px] text-gray-400 w-8 text-right">{{ customerShare(c.amount) }}%</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import apiClient from '@/api/client'

interface AnalyticsData {
  year: number
  this_month: { month: string; ci_amount: number; ci_count: number }
  next_month: { month: string; ci_amount: number; ci_count: number; pipeline_amount: number }
  unpaid: { total_amount: number; unpaid_count: number; partial_count: number }
  yearly_total: { ci_amount: number; ci_count: number }
  unrealized?: { unrealized_amount: number; unconverted_pi_count: number }
  conversion_rate: { total_quotations: number; confirmed_quotations: number; rate: number }
  monthly_trend: { month: string; ci_amount: number; ci_count: number; quotation_amount: number; pi_amount: number }[]
  customer_ranking: { name: string; country?: string; amount: number; count: number }[]
  assignee_stats: { name: string; total: number; completed: number; in_progress: number }[]
}

const loading = ref(false)
const data = ref<AnalyticsData | null>(null)
const selectedYear = ref(new Date().getFullYear())

async function loadData() {
  loading.value = true
  try {
    const res = await apiClient.get('/sales-documents/analytics/summary', { params: { year: selectedYear.value } })
    data.value = res.data
  } catch { data.value = null }
  finally { loading.value = false }
}

function changeYear(delta: number) {
  selectedYear.value += delta
  loadData()
}

function formatAmount(n: number): string {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 })
}

const maxPiAmount = computed(() => {
  if (!data.value) return 1
  return Math.max(...data.value.monthly_trend.map(m => m.ci_amount), 1)
})

function barHeight(amount: number): number {
  return Math.max(2, (amount / maxPiAmount.value) * 170)
}

const totalCustomerAmount = computed(() => {
  if (!data.value) return 1
  return Math.max(data.value.customer_ranking.reduce((sum, c) => sum + c.amount, 0), 1)
})

function customerShare(amount: number): number {
  return Math.round(amount / totalCustomerAmount.value * 100)
}

onMounted(loadData)
defineExpose({ loadData })
</script>
