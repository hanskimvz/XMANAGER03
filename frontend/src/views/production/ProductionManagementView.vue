<template>
  <div class="min-h-screen bg-gray-50">
    <!-- 탭 네비게이션 -->
    <div class="bg-white border-b">
      <div class="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav class="flex space-x-1" aria-label="Tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'relative px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600 bg-blue-50'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            ]"
          >
            {{ tab.name }}
            <!-- 처리 대기 요청 알림 배지 (작업 지시 관리 탭) -->
            <span
              v-if="tab.id === 'work-orders' && pendingCount > 0"
              :class="[
                'absolute -top-1 -right-1 flex items-center justify-center min-w-[20px] h-5 px-1 text-xs font-bold text-white rounded-full',
                pendingPulse ? 'bg-red-500 animate-pulse' : 'bg-red-500'
              ]"
            >
              <svg v-if="pendingPulse" class="w-3 h-3 mr-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              {{ pendingCount }}
            </span>
          </button>
        </nav>
      </div>
    </div>

    <!-- 탭 내용 -->
    <div class="max-w-screen-2xl mx-auto">
      <!-- 간편 처리 (생산팀 일상 업무) -->
      <div v-show="activeTab === 'simple'">
        <ProductionSimpleView
          ref="simpleViewRef"
          @data-changed="handleDataChanged"
        />
      </div>

      <!-- 작업 지시 관리 (생산팀) - v0.22.0: 요청 현황 기능 통합 -->
      <div v-show="activeTab === 'work-orders'">
        <WorkOrderContent
          ref="workOrderContentRef"
          @data-changed="handleDataChanged"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { hasPermStrict } from '@/stores/auth'
import WorkOrderContent from '@/views/production/components/WorkOrderContent.vue'
import ProductionSimpleView from '@/views/production/components/ProductionSimpleView.vue'
import { productionRequestApi } from '@/api/productionRequest'

const route = useRoute()
const router = useRouter()

// 자식 컴포넌트 ref
const workOrderContentRef = ref<InstanceType<typeof WorkOrderContent> | null>(null)
const simpleViewRef = ref<InstanceType<typeof ProductionSimpleView> | null>(null)

// 탭 정의
// 탭별 권한: 생산요청(간편·요청서)=production, 작업지시=workorder.
// 영업팀은 production만 있어 작업지시 탭이 숨겨짐(생산팀만 노출).
const allTabs = [
  { id: 'simple', name: '📋 생산 요청 관리', perm: 'production_simple:view' },
  { id: 'work-orders', name: '작업 지시 관리', perm: 'workorder:view' },
]
const tabs = computed(() => allTabs.filter(t => hasPermStrict(t.perm)))

// 활성 탭 (URL 쿼리에서 읽거나 기본값 사용)
const activeTab = ref(route.query.tab as string || 'simple')

// 권한 없는 탭이 URL/기본값으로 선택돼 내용이 노출되지 않도록, 허용된 첫 탭으로 정규화
watch(tabs, (list) => {
  const ids = list.map(t => t.id)
  if (!ids.includes(activeTab.value)) {
    activeTab.value = ids[0] || ''
  }
}, { immediate: true })

// 처리 대기 요청 카운트
const pendingCount = ref(0)
const pendingPulse = ref(false)

// 대기 요청 카운트 로드
async function loadPendingCount() {
  try {
    const response = await productionRequestApi.getAll({ status: 'REQUESTED', limit: 1 })
    pendingCount.value = response.total
  } catch (error) {
    console.error('대기 요청 카운트 로드 실패:', error)
  }
}

// 데이터 변경 시 모든 탭 새로고침 (통합 핸들러)
function handleDataChanged() {
  // 대기 요청 카운트 새로고침
  loadPendingCount()

  // 알림 펄스 효과 트리거
  pendingPulse.value = true
  setTimeout(() => {
    pendingPulse.value = false
  }, 3000)

  // 작업지시 탭 새로고침 (v0.22.0: 요청 현황 기능 포함)
  if (workOrderContentRef.value) {
    if (typeof (workOrderContentRef.value as any).loadPendingRequests === 'function') {
      (workOrderContentRef.value as any).loadPendingRequests()
    }
    if (typeof (workOrderContentRef.value as any).loadStatusCounts === 'function') {
      (workOrderContentRef.value as any).loadStatusCounts()
    }
    if (typeof (workOrderContentRef.value as any).loadData === 'function') {
      (workOrderContentRef.value as any).loadData()
    }
  }
}

// 탭 변경 시 URL 업데이트
watch(activeTab, (newTab) => {
  router.replace({ query: { tab: newTab } })
})

// URL 쿼리 변경 감지
watch(() => route.query.tab, (newTab) => {
  if (newTab && typeof newTab === 'string') {
    activeTab.value = newTab
  }
})

onMounted(() => {
  // 권한 없는 탭이 선택돼 있으면 접근 가능한 첫 탭으로 보정(작업지시 전용 탭 등)
  const valid = tabs.value.map(t => t.id)
  const desired = (route.query.tab as string) || 'simple'
  const target = valid.includes(desired) ? desired : (valid[0] || 'simple')
  if (route.query.tab !== target) router.replace({ query: { tab: target } })
  activeTab.value = target

  // 대기 요청 카운트 초기 로드
  loadPendingCount()
})
</script>
