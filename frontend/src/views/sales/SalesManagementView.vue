<template>
  <div class="min-h-screen bg-gray-50">
    <!-- 탭 네비게이션 -->
    <div class="bg-white border-b">
      <div class="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
        <nav class="flex space-x-1 overflow-x-auto flex-1" aria-label="Tabs">
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
            <span
              v-if="tab.badge && tab.badge > 0"
              class="absolute -top-1 -right-1 flex items-center justify-center min-w-[20px] h-5 px-1 text-xs font-bold text-white bg-blue-500 rounded-full"
            >
              {{ tab.badge }}
            </span>
          </button>
        </nav>
        <!-- 일괄 업로드 (데스크톱 전용 — 엑셀 업로드성 작업) -->
        <div class="hidden lg:flex items-center gap-2 flex-shrink-0">
          <button type="button" @click="downloadBulkTemplate" class="px-3 py-1.5 text-xs border rounded hover:bg-gray-50 text-gray-600">템플릿 다운</button>
          <label class="px-3 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700 cursor-pointer">
            일괄 업로드
            <input type="file" accept=".xlsx,.xls" class="hidden" @change="handleBulkUpload" />
          </label>
          <label class="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 cursor-pointer">
            영업현황 가져오기
            <input type="file" accept=".xlsx,.xls" class="hidden" @change="handleSalesTrackingImport" />
          </label>
        </div>
      </div>
    </div>

    <!-- 탭 내용 -->
    <div class="max-w-screen-2xl mx-auto">
      <div v-show="activeTab === 'activity'">
        <SalesActivityContent ref="activityRef" @navigate-doc="handleNavigateDoc" />
      </div>

      <div v-show="activeTab === 'quotations'">
        <QuotationContent
          ref="quotationRef"
          :initial-customer-id="initialCustomerId"
          @data-changed="handleDataChanged"
          @navigate-doc="handleNavigateDoc"
        />
      </div>

      <div v-show="activeTab === 'pi'">
        <PiCiContent
          ref="piRef"
          fixed-type="PI"
          @data-changed="handleDataChanged"
          @navigate-doc="handleNavigateDoc"
        />
      </div>

      <div v-show="activeTab === 'ci'">
        <PiCiContent
          ref="ciRef"
          fixed-type="CI"
          @data-changed="handleDataChanged"
          @navigate-doc="handleNavigateDoc"
        />
      </div>

      <div v-show="activeTab === 'invoice'">
        <PiCiContent
          ref="invoiceRef"
          fixed-type="INVOICE"
          @data-changed="handleDataChanged"
          @navigate-doc="handleNavigateDoc"
        />
      </div>

      <div v-show="activeTab === 'price-history'">
        <PriceHistoryContent
          ref="priceHistoryRef"
        />
      </div>

      <div v-show="activeTab === 'production-status'">
        <ProductionStatusContent ref="productionStatusRef" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import apiClient from '@/api/client'
import { downloadAuthedUrl } from '@/utils/download'
import { useToast } from '@/composables/useToast'
import SalesActivityContent from '@/views/sales/activity/SalesActivityContent.vue'
import QuotationContent from '@/views/sales/components/QuotationContent.vue'
import PiCiContent from '@/views/sales/components/PiCiContent.vue'
import PriceHistoryContent from '@/views/sales/components/PriceHistoryContent.vue'
import ProductionStatusContent from '@/views/sales/components/ProductionStatusContent.vue'

const route = useRoute()
const router = useRouter()
const { showToast } = useToast()

// 일괄 업로드 템플릿 — v0.41.0: 인증 헤더를 실어 blob 다운로드(RBAC enforce 시 401 방지)
const downloadBulkTemplate = () =>
  downloadAuthedUrl('/sales-documents/bulk/template', 'sales_template.xlsx').catch((e) => console.error('템플릿 다운로드 실패', e))

async function handleBulkUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  try {
    const res = await apiClient.post('/sales-documents/bulk/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const s = res.data.summary
    showToast(`문서 ${s.documents_created}건 생성, ${s.items_created}건 품목 등록 (스킵 ${s.documents_skipped}건)`, 'success')
    quotationRef.value?.loadData?.()
    piRef.value?.loadData?.()
  } catch (err: any) {
    showToast(err.response?.data?.detail || '업로드에 실패했습니다', 'error')
  } finally {
    input.value = ''
  }
}

async function handleSalesTrackingImport(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!confirm('해외영업 주문/수금/출고 현황 파일에서 PI/CI를 자동 생성합니다.\n이미 등록된 문서번호는 스킵됩니다.\n\n계속하시겠습니까?')) {
    input.value = ''; return
  }
  const formData = new FormData()
  formData.append('file', file)
  try {
    const res = await apiClient.post('/sales-documents/bulk/import-sales-tracking', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const s = res.data.summary
    showToast(`PI ${s.pi_created}건, CI ${s.ci_created}건 생성 (스킵 ${s.skipped}건)`, 'success')
    quotationRef.value?.loadData?.()
    piRef.value?.loadData?.()
  } catch (err: any) {
    showToast(err.response?.data?.detail || '가져오기에 실패했습니다', 'error')
  } finally {
    input.value = ''
  }
}

const activityRef = ref<InstanceType<typeof SalesActivityContent> | null>(null)
const quotationRef = ref<InstanceType<typeof QuotationContent> | null>(null)
const piRef = ref<InstanceType<typeof PiCiContent> | null>(null)
const ciRef = ref<InstanceType<typeof PiCiContent> | null>(null)
const invoiceRef = ref<InstanceType<typeof PiCiContent> | null>(null)
const priceHistoryRef = ref<InstanceType<typeof PriceHistoryContent> | null>(null)

// URL에서 customer_id 파라미터 (거래처 페이지에서 이동 시)
const initialCustomerId = computed(() => {
  const id = route.query.customer_id
  return id ? Number(id) : undefined
})

const tabs = ref([
  { id: 'activity', name: '영업 대응 현황', badge: 0 },
  { id: 'quotations', name: '견적서 (Q)', badge: 0 },
  { id: 'pi', name: 'PI', badge: 0 },
  { id: 'ci', name: 'CI', badge: 0 },
  { id: 'invoice', name: 'Invoice', badge: 0 },
  { id: 'production-status', name: '생산 요청 현황', badge: 0 },
  { id: 'price-history', name: '가격 이력', badge: 0 },
])

const activeTab = ref(route.query.tab as string || 'activity')

function handleDataChanged() {
  if (quotationRef.value && typeof (quotationRef.value as any).loadData === 'function') {
    (quotationRef.value as any).loadData()
  }
  if (piRef.value && typeof (piRef.value as any).loadData === 'function') {
    (piRef.value as any).loadData()
  }
}

// 양방향 링크: 다른 탭의 문서로 이동 + 모달 자동 오픈
async function handleNavigateDoc(payload: { docId: number; docType: string }) {
  const targetTab = payload.docType === 'QUOTATION' ? 'quotations' : payload.docType === 'CI' ? 'ci' : payload.docType === 'INVOICE' ? 'invoice' : 'pi'
  activeTab.value = targetTab

  await new Promise(resolve => setTimeout(resolve, 100))

  const refMap: Record<string, any> = { quotations: quotationRef, pi: piRef, ci: ciRef, invoice: invoiceRef }
  const ref = refMap[targetTab]
  if (ref?.value && typeof ref.value.openDocumentById === 'function') {
    ref.value.openDocumentById(payload.docId)
  }
}

watch(activeTab, (newTab) => {
  const query: Record<string, string> = { tab: newTab }
  if (route.query.customer_id) {
    query.customer_id = route.query.customer_id as string
  }
  router.replace({ query })
})

watch(() => route.query.tab, (newTab) => {
  if (newTab && typeof newTab === 'string') {
    activeTab.value = newTab
  }
})

onMounted(() => {
  if (!route.query.tab) {
    router.replace({ query: { ...route.query, tab: 'activity' } })
  }
})
</script>
