<template>
  <div class="p-4 sm:p-6 max-w-screen-2xl mx-auto">
    <!-- 인사말 -->
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-xl sm:text-2xl font-bold text-gray-800">
        안녕하세요, {{ userDisplay || userName }}님
        <span v-if="userDepartment" class="ml-1 text-sm font-normal text-gray-400">({{ userDepartment }})</span>
      </h1>
      <span class="text-sm text-gray-400">{{ today }}</span>
    </div>

    <!-- 요약 카드 -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
      <router-link to="/sales?tab=activity" class="bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow">
        <p class="text-2xl font-bold text-blue-600">{{ summary.active_activities }}</p>
        <p class="text-xs text-gray-500 mt-1">영업 진행중</p>
      </router-link>
      <router-link to="/production?tab=work-orders" class="bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow">
        <p class="text-2xl font-bold text-orange-600">{{ summary.pending_requests }}</p>
        <p class="text-xs text-gray-500 mt-1">생산요청 대기</p>
      </router-link>
      <router-link to="/production?tab=work-orders" class="bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow">
        <p class="text-2xl font-bold text-green-600">{{ summary.active_work_orders }}</p>
        <p class="text-xs text-gray-500 mt-1">작업 진행중</p>
      </router-link>
      <router-link to="/sales?tab=pi-ci" class="bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow">
        <p class="text-2xl font-bold text-purple-600">{{ summary.unpaid_pis }}</p>
        <p class="text-xs text-gray-500 mt-1">미입금 PI</p>
      </router-link>
      <router-link to="/sales?tab=activity&inactive=1" class="bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow"
        :class="summary.inactive_activities > 0 ? 'border-red-200 bg-red-50' : ''">
        <p class="text-2xl font-bold" :class="summary.inactive_activities > 0 ? 'text-red-600' : 'text-gray-400'">
          {{ summary.inactive_activities }}
        </p>
        <p class="text-xs mt-1" :class="summary.inactive_activities > 0 ? 'text-red-500' : 'text-gray-500'">비활성 (8주+)</p>
      </router-link>
    </div>

    <!-- 하단 2컬럼 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- 좌측: 최근 영업 활동 -->
      <div class="bg-white rounded-lg shadow-sm border">
        <div class="flex justify-between items-center px-4 py-3 border-b">
          <h2 class="text-sm font-bold text-gray-700">최근 영업 활동</h2>
          <router-link to="/sales?tab=activity" class="text-xs text-blue-600 hover:underline">전체 보기</router-link>
        </div>
        <div v-if="recentActivities.length === 0" class="p-6 text-center text-gray-400 text-sm">
          등록된 영업 활동이 없습니다
        </div>
        <div v-else class="divide-y divide-gray-100">
          <router-link v-for="item in recentActivities" :key="item.id"
            :to="`/sales?tab=activity`"
            class="flex items-start gap-3 px-4 py-3 hover:bg-gray-50">
            <div class="w-1.5 h-1.5 bg-blue-500 rounded-full mt-2 flex-shrink-0"></div>
            <div class="flex-1 min-w-0">
              <div class="flex items-baseline gap-2">
                <span class="text-xs text-gray-400">{{ formatDate(item.logged_at) }}</span>
                <span v-if="item.logged_by" class="text-xs font-medium text-gray-500">{{ item.logged_by }}</span>
              </div>
              <p class="text-sm text-gray-800 mt-0.5 truncate">
                <span class="font-medium">{{ item.customer_name || item.title }}</span>
                — {{ item.log_content }}
              </p>
            </div>
          </router-link>
        </div>
      </div>

      <!-- 우측: 대기 작업 + 미입금 PI -->
      <div class="space-y-4">
        <!-- 대기 중인 생산요청 -->
        <div class="bg-white rounded-lg shadow-sm border">
          <div class="flex justify-between items-center px-4 py-3 border-b">
            <h2 class="text-sm font-bold text-gray-700">대기 중인 생산요청</h2>
            <router-link to="/production?tab=work-orders" class="text-xs text-blue-600 hover:underline">전체 보기</router-link>
          </div>
          <div v-if="pendingItems.length === 0" class="p-4 text-center text-gray-400 text-sm">없음</div>
          <div v-else class="divide-y divide-gray-100">
            <div v-for="item in pendingItems" :key="item.id" class="px-4 py-2.5 flex justify-between items-center">
              <div>
                <span class="text-sm font-medium text-blue-600">{{ item.request_number }}</span>
                <span class="text-xs text-gray-400 ml-2">{{ item.customer_name || '' }}</span>
              </div>
              <span class="text-xs text-gray-400">{{ formatDate(item.created_at) }}</span>
            </div>
          </div>
        </div>

        <!-- 미입금 PI -->
        <div class="bg-white rounded-lg shadow-sm border">
          <div class="flex justify-between items-center px-4 py-3 border-b">
            <h2 class="text-sm font-bold text-gray-700">미입금 PI</h2>
            <router-link to="/sales?tab=pi-ci" class="text-xs text-blue-600 hover:underline">전체 보기</router-link>
          </div>
          <div v-if="unpaidItems.length === 0" class="p-4 text-center text-gray-400 text-sm">없음</div>
          <div v-else class="divide-y divide-gray-100">
            <div v-for="item in unpaidItems" :key="item.id" class="px-4 py-2.5 flex justify-between items-center">
              <div>
                <span class="text-sm font-medium text-purple-600">{{ item.document_number }}</span>
                <span class="text-xs text-gray-400 ml-2">{{ item.customer_name || '' }}</span>
              </div>
              <span class="text-sm font-medium text-gray-700">{{ item.currency }} {{ item.total_amount?.toLocaleString() }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuth } from '@/stores/auth'
import apiClient from '@/api/client'

const { userName, userDisplay, userDepartment } = useAuth()

const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

const summary = ref({
  active_activities: 0,
  pending_requests: 0,
  active_work_orders: 0,
  unpaid_pis: 0,
  inactive_activities: 0,
})
const recentActivities = ref<any[]>([])
const pendingItems = ref<any[]>([])
const unpaidItems = ref<any[]>([])

async function loadDashboard() {
  try {
    const res = await apiClient.get('/dashboard/summary')
    const data = res.data
    summary.value = data.cards
    recentActivities.value = data.recent_activities || []
    pendingItems.value = data.pending_items || []
    unpaidItems.value = data.unpaid_items || []
  } catch {
    // 대시보드 로드 실패 시 빈 상태 유지
  }
}

function formatDate(d?: string) {
  if (!d) return ''
  const date = new Date(d)
  return `${String(date.getMonth()+1).padStart(2,'0')}.${String(date.getDate()).padStart(2,'0')}`
}

onMounted(loadDashboard)
</script>
