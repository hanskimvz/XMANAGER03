<template>
  <div class="print-view">
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner">로딩 중...</div>
    </div>
    <div v-else-if="error" class="error-message">
      <p>{{ error }}</p>
      <button @click="loadData" class="retry-button">다시 시도</button>
    </div>
    <template v-else>
      <!-- 인쇄 컨트롤 (화면에서만 표시) -->
      <div class="print-controls no-print">
        <button @click="handlePrint" class="print-button">
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
          </svg>
          인쇄
        </button>
        <button @click="handleDownloadPDF" class="pdf-button">
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          PDF 다운로드
        </button>
        <button @click="handleClose" class="close-button">
          닫기
        </button>
      </div>

      <!-- 인쇄용 컴포넌트 -->
      <PurchaseOrderPrint :purchase-order="purchaseOrder" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { purchaseOrderApi, type PurchaseOrder } from '@/api/purchaseOrder'
import PurchaseOrderPrint from '@/views/production/components/PurchaseOrderPrint.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref<string | null>(null)
const purchaseOrder = ref<PurchaseOrder | null>(null)

// 데이터 로드
async function loadData() {
  const id = Number(route.params.id)
  if (!id || isNaN(id)) {
    error.value = '잘못된 발주서 ID입니다.'
    loading.value = false
    return
  }

  loading.value = true
  error.value = null

  try {
    purchaseOrder.value = await purchaseOrderApi.getById(id)
  } catch (err: any) {
    console.error('발주서 로드 실패:', err)
    error.value = err.response?.data?.detail?.message || '발주서를 불러오는데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

// 인쇄
function handlePrint() {
  window.print()
}

// PDF 다운로드
async function handleDownloadPDF() {
  if (!purchaseOrder.value) return

  try {
    await purchaseOrderApi.downloadPDF(purchaseOrder.value.id, purchaseOrder.value.po_number)
  } catch (err: any) {
    console.error('PDF 다운로드 실패:', err)
    alert('PDF 다운로드에 실패했습니다.')
  }
}

// 닫기
function handleClose() {
  window.close()
  // 새 창이 아닌 경우 뒤로가기
  setTimeout(() => {
    router.back()
  }, 100)
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.print-view {
  min-height: 100vh;
  background-color: #e0e0e0;
}

.loading-overlay {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}

.loading-spinner {
  font-size: 18px;
  color: #666;
}

.error-message {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  color: #ef4444;
}

.retry-button {
  margin-top: 16px;
  padding: 8px 16px;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.retry-button:hover {
  background-color: #2563eb;
}

/* 인쇄 컨트롤 */
.print-controls {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  gap: 16px;
  padding: 16px;
  background-color: #1f2937;
  z-index: 100;
}

.print-button,
.pdf-button,
.close-button {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.print-button {
  background-color: #3b82f6;
  color: white;
}

.print-button:hover {
  background-color: #2563eb;
}

.pdf-button {
  background-color: #10b981;
  color: white;
}

.pdf-button:hover {
  background-color: #059669;
}

.close-button {
  background-color: #6b7280;
  color: white;
}

.close-button:hover {
  background-color: #4b5563;
}

/* 인쇄 시 숨김 */
@media print {
  .no-print {
    display: none !important;
  }

  .print-view {
    background-color: white;
  }
}
</style>
