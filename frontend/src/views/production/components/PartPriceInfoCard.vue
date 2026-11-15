<template>
  <div class="price-info-card">
    <div class="card-header">
      <h4 class="card-title">원가 정보</h4>
      <button @click="handleRefresh" class="refresh-btn" :disabled="loading" title="평균단가 갱신">
        <svg class="w-4 h-4" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>
    </div>

    <div v-if="loading && !priceInfo" class="loading">
      <span>로딩 중...</span>
    </div>

    <div v-else-if="error" class="error">
      <span>{{ error }}</span>
    </div>

    <div v-else-if="priceInfo" class="price-grid">
      <!-- 기준단가 -->
      <div class="price-item standard">
        <div class="price-label">
          <span class="label-text">기준단가</span>
          <button @click="showEditModal = true" class="edit-btn" title="수정">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </button>
        </div>
        <div class="price-value">{{ formatPrice(priceInfo.standard_price, priceInfo.standard_price_currency) }}</div>
        <div class="price-desc">사용자 입력 목표가</div>
      </div>

      <!-- 재고단가 -->
      <div class="price-item inventory">
        <div class="price-label">
          <span class="label-text">재고단가</span>
          <span class="badge badge-blue">이동평균</span>
        </div>
        <div class="price-value">{{ formatPrice(priceInfo.inventory_avg_price, priceInfo.inventory_avg_price_currency) }}</div>
        <div class="price-desc">입고 시 자동 계산</div>
      </div>

      <!-- 최근단가 -->
      <div class="price-item latest">
        <div class="price-label">
          <span class="label-text">최근단가</span>
        </div>
        <div class="price-value">{{ formatPrice(priceInfo.latest_price, priceInfo.latest_price_currency) }}</div>
        <div class="price-desc">
          <span v-if="priceInfo.latest_price_date">{{ formatDate(priceInfo.latest_price_date) }}</span>
          <span v-if="priceInfo.latest_price_supplier" class="supplier-name">{{ priceInfo.latest_price_supplier }}</span>
        </div>
      </div>

      <!-- 평균단가 -->
      <div class="price-item average">
        <div class="price-label">
          <span class="label-text">평균단가</span>
          <button @click="showHistoryModal = true" class="history-btn" title="이력 보기">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </button>
        </div>
        <div class="avg-price-grid">
          <div class="avg-item">
            <span class="avg-label">30일</span>
            <span class="avg-value">{{ formatPrice(priceInfo.avg_price_30d) }}</span>
          </div>
          <div class="avg-item">
            <span class="avg-label">90일</span>
            <span class="avg-value">{{ formatPrice(priceInfo.avg_price_90d) }}</span>
          </div>
          <div class="avg-item">
            <span class="avg-label">최근 5건</span>
            <span class="avg-value">{{ formatPrice(priceInfo.avg_price_last5) }}</span>
          </div>
          <div class="avg-item">
            <span class="avg-label">최근 10건</span>
            <span class="avg-value">{{ formatPrice(priceInfo.avg_price_last10) }}</span>
          </div>
        </div>
      </div>

      <!-- BOM 원가 계산 (v0.18.0) -->
      <div class="price-item bom-cost">
        <div class="price-label">
          <span class="label-text">BOM 원가</span>
          <span class="badge" :class="bomCostInfo?.has_bom ? 'badge-purple' : 'badge-gray'">
            {{ bomCostInfo?.has_bom ? 'BOM 합산' : '단품' }}
          </span>
          <button @click="handleCalculateBOMCost" class="calc-btn" :disabled="bomLoading" title="원가 계산">
            <svg class="w-3 h-3" :class="{ 'animate-spin': bomLoading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </button>
        </div>

        <div v-if="bomLoading && !bomCostInfo" class="bom-loading">
          <span>계산 중...</span>
        </div>

        <div v-else-if="bomCostInfo" class="bom-cost-content">
          <!-- 원가 요약 -->
          <div class="bom-cost-summary">
            <div class="cost-row">
              <span class="cost-label">재료비</span>
              <span class="cost-value">{{ formatPrice(bomCostInfo.material_cost) }}</span>
            </div>
            <div class="cost-row">
              <span class="cost-label">
                가공비
                <button @click="showLaborCostModal = true" class="inline-edit-btn" title="수정">
                  <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                </button>
              </span>
              <span class="cost-value">{{ formatPrice(bomCostInfo.labor_cost) }}</span>
            </div>
            <div class="cost-row">
              <span class="cost-label">
                경비
                <button @click="showOverheadCostModal = true" class="inline-edit-btn" title="수정">
                  <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                </button>
              </span>
              <span class="cost-value">{{ formatPrice(bomCostInfo.overhead_cost) }}</span>
            </div>
            <div class="cost-row total">
              <span class="cost-label">총원가</span>
              <span class="cost-value">{{ formatPrice(bomCostInfo.total_cost) }}</span>
            </div>
          </div>

          <!-- BOM 구성품 목록 (있는 경우만) -->
          <div v-if="bomCostInfo.has_bom && bomCostInfo.bom_items.length > 0" class="bom-items-section">
            <div class="bom-items-header" @click="showBOMItems = !showBOMItems">
              <span>구성품 상세 ({{ bomCostInfo.bom_items.length }}건)</span>
              <svg class="w-4 h-4 transition-transform" :class="{ 'rotate-180': showBOMItems }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
            <div v-show="showBOMItems" class="bom-items-list">
              <div v-for="item in bomCostInfo.bom_items" :key="item.bom_id" class="bom-item-row">
                <div class="bom-item-info">
                  <span class="bom-item-name">{{ item.child_part_name }}</span>
                  <span class="bom-item-number">{{ item.child_part_number }}</span>
                </div>
                <div class="bom-item-calc">
                  <span>{{ formatPrice(item.unit_cost) }} × {{ item.quantity }}</span>
                  <span class="bom-item-total">{{ formatPrice(item.line_cost) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 저장 버튼 -->
          <div class="bom-actions">
            <button @click="handleSaveBOMCost" :disabled="bomSaving" class="btn-save-cost">
              {{ bomSaving ? '저장 중...' : '원가 저장' }}
            </button>
            <span v-if="priceInfo.cost_calculated_at" class="last-calc-time">
              마지막 계산: {{ formatDateTime(priceInfo.cost_calculated_at) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 기준단가 수정 모달 -->
    <div v-if="showEditModal" class="modal-overlay" >
      <div class="modal-content">
        <div class="modal-header">
          <h5>기준단가 수정</h5>
          <button @click="showEditModal = false" class="close-btn">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>기준단가</label>
            <div class="input-group">
              <input type="number" v-model.number="editForm.standard_price" step="0.01" min="0" class="form-input" />
              <select v-model="editForm.standard_price_currency" class="currency-select">
                <option value="KRW">₩ KRW</option>
                <option value="USD">$ USD</option>
                <option value="EUR">€ EUR</option>
                <option value="JPY">¥ JPY</option>
                <option value="CNY">¥ CNY</option>
                <option value="GBP">£ GBP</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>변경 사유</label>
            <input type="text" v-model="editForm.remarks" class="form-input" placeholder="선택사항" />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showEditModal = false" class="btn-cancel">취소</button>
          <button @click="handleSaveStandardPrice" :disabled="saving" class="btn-save">
            {{ saving ? '저장 중...' : '저장' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 가격 이력 모달 -->
    <div v-if="showHistoryModal" class="modal-overlay" >
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h5>가격 이력</h5>
          <button @click="showHistoryModal = false" class="close-btn">&times;</button>
        </div>
        <div class="modal-body">
          <div class="history-filters">
            <select v-model="historyFilter.price_type" class="filter-select" @change="loadHistory">
              <option value="">전체 유형</option>
              <option value="PURCHASE">구매</option>
              <option value="STANDARD">기준단가</option>
              <option value="MANUAL">수동입력</option>
              <option value="QUOTE">견적</option>
            </select>
          </div>
          <div v-if="historyLoading" class="loading">로딩 중...</div>
          <table v-else class="history-table">
            <thead>
              <tr>
                <th>일자</th>
                <th>유형</th>
                <th>단가</th>
                <th>수량</th>
                <th>공급업체</th>
                <th>비고</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in historyItems" :key="item.id">
                <td>{{ formatDateTime(item.created_at) }}</td>
                <td>
                  <span class="type-badge" :class="'type-' + item.price_type.toLowerCase()">
                    {{ priceTypeLabels[item.price_type] || item.price_type }}
                  </span>
                </td>
                <td>{{ formatPrice(item.unit_price, item.currency) }}</td>
                <td>{{ item.quantity || '-' }}</td>
                <td>{{ item.supplier_name || '-' }}</td>
                <td class="remarks-cell">{{ item.remarks || '-' }}</td>
              </tr>
              <tr v-if="historyItems.length === 0">
                <td colspan="6" class="empty-row">가격 이력이 없습니다.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 가공비 수정 모달 -->
    <div v-if="showLaborCostModal" class="modal-overlay" >
      <div class="modal-content">
        <div class="modal-header">
          <h5>가공비 수정</h5>
          <button @click="showLaborCostModal = false" class="close-btn">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>가공비 (노무비)</label>
            <div class="input-group">
              <input type="number" v-model.number="laborCostForm.amount" step="1" min="0" class="form-input" />
              <select v-model="laborCostForm.currency" class="currency-select">
                <option value="KRW">₩ KRW</option>
                <option value="USD">$ USD</option>
                <option value="EUR">€ EUR</option>
                <option value="JPY">¥ JPY</option>
                <option value="CNY">¥ CNY</option>
                <option value="GBP">£ GBP</option>
              </select>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showLaborCostModal = false" class="btn-cancel">취소</button>
          <button @click="handleSaveLaborCost" :disabled="laborSaving" class="btn-save">
            {{ laborSaving ? '저장 중...' : '저장' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 경비 수정 모달 -->
    <div v-if="showOverheadCostModal" class="modal-overlay" >
      <div class="modal-content">
        <div class="modal-header">
          <h5>경비 수정</h5>
          <button @click="showOverheadCostModal = false" class="close-btn">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>경비 (간접비용)</label>
            <div class="input-group">
              <input type="number" v-model.number="overheadCostForm.amount" step="1" min="0" class="form-input" />
              <select v-model="overheadCostForm.currency" class="currency-select">
                <option value="KRW">₩ KRW</option>
                <option value="USD">$ USD</option>
                <option value="EUR">€ EUR</option>
                <option value="JPY">¥ JPY</option>
                <option value="CNY">¥ CNY</option>
                <option value="GBP">£ GBP</option>
              </select>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showOverheadCostModal = false" class="btn-cancel">취소</button>
          <button @click="handleSaveOverheadCost" :disabled="overheadSaving" class="btn-save">
            {{ overheadSaving ? '저장 중...' : '저장' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { priceApi, type PartPriceInfo, type PriceHistory, type BOMCostResult, priceTypeLabels, formatPrice } from '@/api/price'

const props = defineProps<{
  partId: number
}>()

const emit = defineEmits<{
  (e: 'updated'): void
}>()

const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const priceInfo = ref<PartPriceInfo | null>(null)

const showEditModal = ref(false)
const editForm = ref({
  standard_price: 0,
  standard_price_currency: 'KRW',
  remarks: '',
})

const showHistoryModal = ref(false)
const historyLoading = ref(false)
const historyItems = ref<PriceHistory[]>([])
const historyFilter = ref({
  price_type: '' as string,
})

// BOM 원가 관련
const bomLoading = ref(false)
const bomSaving = ref(false)
const bomCostInfo = ref<BOMCostResult | null>(null)
const showBOMItems = ref(false)

// 가공비/경비 모달
const showLaborCostModal = ref(false)
const showOverheadCostModal = ref(false)
const laborSaving = ref(false)
const overheadSaving = ref(false)
const laborCostForm = ref({ amount: 0, currency: 'KRW' })
const overheadCostForm = ref({ amount: 0, currency: 'KRW' })

// 가격 정보 로드
async function loadPriceInfo() {
  if (!props.partId) return

  loading.value = true
  error.value = null

  try {
    priceInfo.value = await priceApi.getPartPriceInfo(props.partId)
    // 수정 폼 초기화
    editForm.value.standard_price = priceInfo.value.standard_price
    editForm.value.standard_price_currency = priceInfo.value.standard_price_currency
  } catch (e: any) {
    error.value = e.response?.data?.detail?.message || '가격 정보를 불러오는데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

// 가격 이력 로드
async function loadHistory() {
  if (!props.partId) return

  historyLoading.value = true

  try {
    const params: any = { limit: 50 }
    if (historyFilter.value.price_type) {
      params.price_type = historyFilter.value.price_type
    }
    const response = await priceApi.getPriceHistory(props.partId, params)
    historyItems.value = response.items
  } catch (e: any) {
    console.error('가격 이력 로드 실패:', e)
  } finally {
    historyLoading.value = false
  }
}

// 평균단가 캐시 갱신
async function handleRefresh() {
  if (!props.partId) return

  loading.value = true

  try {
    priceInfo.value = await priceApi.refreshAvgPriceCache(props.partId)
    emit('updated')
  } catch (e: any) {
    console.error('평균단가 갱신 실패:', e)
  } finally {
    loading.value = false
  }
}

// 기준단가 저장
async function handleSaveStandardPrice() {
  if (!props.partId) return

  saving.value = true

  try {
    const _sp = editForm.value.standard_price
    const _stdPrice = (typeof _sp === 'number' && !Number.isNaN(_sp)) ? _sp : 0
    priceInfo.value = await priceApi.updateStandardPrice(props.partId, {
      standard_price: _stdPrice,
      standard_price_currency: editForm.value.standard_price_currency,
      remarks: editForm.value.remarks || undefined,
    })
    showEditModal.value = false
    editForm.value.remarks = ''
    emit('updated')
  } catch (e: any) {
    alert(e.response?.data?.detail?.message || '저장에 실패했습니다.')
  } finally {
    saving.value = false
  }
}

// 날짜 포맷
function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('ko-KR')
}

function formatDateTime(dateStr: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// BOM 원가 계산
async function handleCalculateBOMCost() {
  if (!props.partId) return

  bomLoading.value = true

  try {
    bomCostInfo.value = await priceApi.calculateBOMCost(props.partId)
    // 폼 초기화
    laborCostForm.value.amount = bomCostInfo.value.labor_cost
    overheadCostForm.value.amount = bomCostInfo.value.overhead_cost
  } catch (e: any) {
    console.error('BOM 원가 계산 실패:', e)
  } finally {
    bomLoading.value = false
  }
}

// BOM 원가 저장
async function handleSaveBOMCost() {
  if (!props.partId) return

  bomSaving.value = true

  try {
    priceInfo.value = await priceApi.saveCalculatedCost(props.partId)
    emit('updated')
    alert('원가가 저장되었습니다.')
  } catch (e: any) {
    alert(e.response?.data?.detail?.message || '저장에 실패했습니다.')
  } finally {
    bomSaving.value = false
  }
}

// 가공비 저장
async function handleSaveLaborCost() {
  if (!props.partId) return

  laborSaving.value = true

  try {
    const _la = laborCostForm.value.amount
    const _laborAmt = (typeof _la === 'number' && !Number.isNaN(_la)) ? _la : 0
    await priceApi.updateLaborCost(props.partId, _laborAmt, laborCostForm.value.currency)
    showLaborCostModal.value = false
    // 원가 재계산
    await handleCalculateBOMCost()
    emit('updated')
  } catch (e: any) {
    alert(e.response?.data?.detail?.message || '저장에 실패했습니다.')
  } finally {
    laborSaving.value = false
  }
}

// 경비 저장
async function handleSaveOverheadCost() {
  if (!props.partId) return

  overheadSaving.value = true

  try {
    const _oa = overheadCostForm.value.amount
    const _overAmt = (typeof _oa === 'number' && !Number.isNaN(_oa)) ? _oa : 0
    await priceApi.updateOverheadCost(props.partId, _overAmt, overheadCostForm.value.currency)
    showOverheadCostModal.value = false
    // 원가 재계산
    await handleCalculateBOMCost()
    emit('updated')
  } catch (e: any) {
    alert(e.response?.data?.detail?.message || '저장에 실패했습니다.')
  } finally {
    overheadSaving.value = false
  }
}

// 이력 모달 열릴 때 로드
watch(showHistoryModal, (newVal) => {
  if (newVal) {
    loadHistory()
  }
})

// 부품 ID 변경 시 로드
watch(() => props.partId, () => {
  loadPriceInfo()
  // BOM 원가도 초기 로드
  handleCalculateBOMCost()
})

onMounted(() => {
  loadPriceInfo()
  // BOM 원가 초기 로드
  handleCalculateBOMCost()
})
</script>

<style scoped>
.price-info-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.refresh-btn {
  padding: 4px;
  border: none;
  background: none;
  color: #6b7280;
  cursor: pointer;
  border-radius: 4px;
}

.refresh-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.loading, .error {
  text-align: center;
  padding: 20px;
  color: #6b7280;
}

.error {
  color: #ef4444;
}

.price-grid {
  display: grid;
  gap: 16px;
}

.price-item {
  padding: 12px;
  border-radius: 6px;
  background: #f9fafb;
}

.price-item.standard {
  background: #ecfdf5;
  border-left: 3px solid #10b981;
}

.price-item.inventory {
  background: #eff6ff;
  border-left: 3px solid #3b82f6;
}

.price-item.latest {
  background: #fef3c7;
  border-left: 3px solid #f59e0b;
}

.price-item.average {
  background: #f5f3ff;
  border-left: 3px solid #8b5cf6;
}

.price-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.label-text {
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
}

.badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
}

.badge-blue {
  background: #dbeafe;
  color: #1d4ed8;
}

.edit-btn, .history-btn {
  padding: 2px;
  border: none;
  background: none;
  color: #9ca3af;
  cursor: pointer;
  border-radius: 2px;
}

.edit-btn:hover, .history-btn:hover {
  color: #374151;
}

.price-value {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.price-desc {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 4px;
}

.supplier-name {
  margin-left: 8px;
  color: #6b7280;
}

.avg-price-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-top: 8px;
}

.avg-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.avg-label {
  color: #6b7280;
}

.avg-value {
  font-weight: 500;
  color: #374151;
}

/* 모달 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 400px;
  max-height: 90vh;
  overflow: auto;
}

.modal-content.modal-lg {
  width: 700px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h5 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.close-btn {
  border: none;
  background: none;
  font-size: 24px;
  color: #9ca3af;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: #374151;
}

.modal-body {
  padding: 16px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid #e5e7eb;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 4px;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.input-group {
  display: flex;
  gap: 8px;
}

.input-group .form-input {
  flex: 1;
}

.currency-select {
  width: 100px;
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.btn-cancel, .btn-save {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.btn-cancel {
  background: #f3f4f6;
  color: #374151;
}

.btn-cancel:hover {
  background: #e5e7eb;
}

.btn-save {
  background: #3b82f6;
  color: white;
}

.btn-save:hover {
  background: #2563eb;
}

.btn-save:disabled {
  background: #93c5fd;
  cursor: not-allowed;
}

/* 이력 */
.history-filters {
  margin-bottom: 12px;
}

.filter-select {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.history-table th,
.history-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.history-table th {
  background: #f9fafb;
  font-weight: 500;
  color: #6b7280;
}

.type-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.type-purchase {
  background: #dbeafe;
  color: #1d4ed8;
}

.type-standard {
  background: #dcfce7;
  color: #166534;
}

.type-manual {
  background: #fef3c7;
  color: #92400e;
}

.type-quote {
  background: #f3e8ff;
  color: #7c3aed;
}

.remarks-cell {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-row {
  text-align: center !important;
  color: #9ca3af;
  padding: 40px !important;
}

/* BOM 원가 스타일 */
.price-item.bom-cost {
  background: #fdf4ff;
  border-left: 3px solid #d946ef;
}

.badge-purple {
  background: #f3e8ff;
  color: #7c3aed;
}

.badge-gray {
  background: #f3f4f6;
  color: #6b7280;
}

.calc-btn {
  padding: 2px;
  border: none;
  background: none;
  color: #9ca3af;
  cursor: pointer;
  border-radius: 2px;
}

.calc-btn:hover {
  color: #d946ef;
}

.bom-loading {
  text-align: center;
  padding: 12px;
  color: #9ca3af;
  font-size: 12px;
}

.bom-cost-content {
  margin-top: 8px;
}

.bom-cost-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cost-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 2px 0;
}

.cost-row.total {
  border-top: 1px solid #e9d5ff;
  padding-top: 6px;
  margin-top: 4px;
  font-weight: 600;
}

.cost-label {
  color: #6b7280;
  display: flex;
  align-items: center;
  gap: 4px;
}

.cost-value {
  color: #374151;
  font-weight: 500;
}

.cost-row.total .cost-value {
  color: #7c3aed;
  font-size: 14px;
}

.inline-edit-btn {
  padding: 1px;
  border: none;
  background: none;
  color: #d1d5db;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}

.inline-edit-btn:hover {
  color: #9ca3af;
}

.bom-items-section {
  margin-top: 12px;
  border-top: 1px solid #e9d5ff;
  padding-top: 8px;
}

.bom-items-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #6b7280;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.bom-items-header:hover {
  background: #fae8ff;
}

.bom-items-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bom-item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  padding: 4px 8px;
  background: white;
  border-radius: 4px;
}

.bom-item-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.bom-item-name {
  color: #374151;
  font-weight: 500;
}

.bom-item-number {
  color: #9ca3af;
  font-size: 10px;
}

.bom-item-calc {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
  color: #6b7280;
}

.bom-item-total {
  font-weight: 500;
  color: #374151;
}

.bom-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid #e9d5ff;
}

.btn-save-cost {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  background: #d946ef;
  color: white;
  font-size: 12px;
  cursor: pointer;
}

.btn-save-cost:hover {
  background: #c026d3;
}

.btn-save-cost:disabled {
  background: #e9d5ff;
  cursor: not-allowed;
}

.last-calc-time {
  font-size: 10px;
  color: #9ca3af;
}
</style>
