<template>
  <div
    ref="modalOverlay"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
    tabindex="-1"
    @keydown.escape="$emit('close')"
  >
    <div class="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] overflow-hidden" @click.stop>
      <!-- 헤더 -->
      <div class="flex justify-between items-center px-6 py-4 border-b bg-gray-50">
        <h2 class="text-xl font-semibold text-gray-800">
          {{ isEdit ? `발주서 상세 (${purchaseOrder?.po_number})` : '발주서 등록' }}
        </h2>
        <button @click="$emit('close')" class="text-gray-500 hover:text-gray-700">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="overflow-y-auto max-h-[calc(90vh-120px)]">
        <!-- 상태 진행 바 (수정 모드) -->
        <div v-if="isEdit" class="px-6 py-4 bg-gray-50 border-b">
          <div class="flex justify-between items-center">
            <div
              v-for="(label, status) in statusSteps"
              :key="status"
              class="flex-1 text-center"
            >
              <div
                :class="[
                  'w-8 h-8 mx-auto rounded-full flex items-center justify-center text-sm font-medium',
                  getStatusClass(status)
                ]"
              >
                {{ statusOrder.indexOf(status) + 1 }}
              </div>
              <div class="mt-1 text-xs text-gray-600">{{ label }}</div>
            </div>
          </div>
        </div>

        <!-- 폼 -->
        <form @submit.prevent="handleSubmit" class="p-6 space-y-6">
          <!-- 기본 정보 -->
          <div class="grid grid-cols-2 gap-4">
            <!-- 발주번호 (자동) -->
            <div v-if="isEdit">
              <label class="block text-sm font-medium text-gray-700 mb-1">발주번호</label>
              <input
                type="text"
                :value="purchaseOrder?.po_number"
                disabled
                class="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-100"
              />
            </div>

            <!-- 공급업체 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">공급업체 *</label>
              <div class="flex gap-2">
                <input
                  type="text"
                  :value="selectedSupplierName"
                  readonly
                  placeholder="공급업체를 선택하세요"
                  class="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 cursor-pointer"
                  :class="{ 'cursor-not-allowed opacity-50': !isEditable }"
                  @click="isEditable && (showSupplierSearch = true)"
                />
                <button
                  v-if="isEditable"
                  type="button"
                  @click="showSupplierSearch = true"
                  class="px-3 py-2 bg-gray-100 border border-gray-300 rounded-lg hover:bg-gray-200"
                >
                  <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- 발주일 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">발주일 *</label>
              <input
                v-model="form.order_date"
                type="date"
                :disabled="!isEditable"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                required
              />
            </div>

            <!-- 예상 납기일 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">예상 납기일</label>
              <input
                v-model="form.expected_delivery_date"
                type="date"
                :disabled="!isEditable"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              />
            </div>

            <!-- 결제 조건 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">결제 조건</label>
              <input
                v-model="form.payment_terms"
                type="text"
                :disabled="!isEditable"
                placeholder="예: 현금, 30일 후 결제"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              />
            </div>

            <!-- 납품 조건 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">납품 조건</label>
              <input
                v-model="form.delivery_terms"
                type="text"
                :disabled="!isEditable"
                placeholder="예: 현장 인도"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              />
            </div>
          </div>

          <!-- 비고 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">비고</label>
            <textarea
              v-model="form.remarks"
              rows="2"
              :disabled="!isEditable"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            />
          </div>

          <!-- 첨부파일 -->
          <div>
            <h3 class="text-sm font-medium text-gray-700 mb-2">첨부파일</h3>
            <div class="border rounded-lg p-4 bg-gray-50">
              <!-- 기존 파일 목록 -->
              <div v-if="purchaseOrder?.document_files?.length" class="mb-3">
                <div v-for="(file, idx) in purchaseOrder.document_files" :key="idx" class="flex items-center justify-between py-2 border-b last:border-b-0">
                  <span class="text-sm text-gray-700">{{ file.file_name }}</span>
                  <button
                    v-if="isEditable"
                    type="button"
                    @click="handleDeleteFile(idx)"
                    class="text-red-600 hover:text-red-800 text-sm"
                  >
                    삭제
                  </button>
                </div>
              </div>
              <div v-else-if="isEdit" class="text-sm text-gray-500 mb-3">첨부된 파일이 없습니다.</div>

              <!-- 파일 업로드 -->
              <div v-if="isEditable">
                <input
                  ref="fileInputRef"
                  type="file"
                  multiple
                  class="hidden"
                  @change="handleFileSelect"
                />
                <button
                  type="button"
                  @click="fileInputRef?.click()"
                  class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm"
                >
                  파일 선택
                </button>
                <!-- 신규 등록 시 선택한 파일 표시 -->
                <div v-if="!isEdit && selectedFiles.length" class="mt-2">
                  <div v-for="(file, idx) in selectedFiles" :key="idx" class="flex items-center justify-between py-1">
                    <span class="text-sm text-gray-600">{{ file.name }}</span>
                    <button type="button" @click="removeSelectedFile(idx)" class="text-red-500 text-sm">제거</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 발주 항목 -->
          <div>
            <div v-if="isApprovalDerived" class="mb-2 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
              🔒 이 발주서는 <b>구매 기안서에서 생성</b>되어 수량·단가·부품을 수정할 수 없습니다. 변경이 필요하면 <b>기안서를 다시 올려주세요.</b>
            </div>
            <div class="flex justify-between items-center mb-2">
              <h3 class="text-lg font-medium text-gray-800">발주 항목</h3>
              <div v-if="itemsEditable" class="flex gap-2">
                <button
                  type="button"
                  @click="showPartSearch = true"
                  class="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  부품 추가
                </button>
                <button
                  type="button"
                  @click="addCustomItem"
                  title="BOM에 없는 품목을 품명 직접 입력으로 발주(외주 등)"
                  class="px-3 py-1 text-sm border border-slate-300 text-slate-600 rounded hover:bg-slate-50"
                >
                  자유입력 품목
                </button>
              </div>
            </div>
            <div class="border rounded-lg overflow-hidden">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">품번</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">부품명</th>
                    <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">발주수량</th>
                    <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">단가</th>
                    <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">금액</th>
                    <th v-if="isEdit" class="px-4 py-2 text-right text-xs font-medium text-gray-500">입고수량</th>
                    <th v-if="itemsEditable" class="px-4 py-2 text-center text-xs font-medium text-gray-500">삭제</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200">
                  <tr v-if="items.length === 0">
                    <td :colspan="isEdit ? 7 : 6" class="px-4 py-4 text-center text-gray-500">
                      항목을 추가해주세요.
                    </td>
                  </tr>
                  <tr v-for="(item, idx) in items" :key="idx">
                    <td class="px-4 py-2 text-sm">
                      <template v-if="item.part">{{ item.part?.part_number_display || item.part?.part_number }}</template>
                      <input v-else-if="itemsEditable" v-model="item.custom_product_code" type="text" placeholder="품번(선택)"
                        class="w-28 px-2 py-1 border rounded text-sm" />
                      <span v-else>{{ item.custom_product_code || '-' }}</span>
                    </td>
                    <td class="px-4 py-2 text-sm">
                      <template v-if="item.part">{{ item.part?.part_name }}</template>
                      <template v-else>
                        <input v-if="itemsEditable" v-model="item.custom_product_name" type="text" placeholder="품명(자유입력)"
                          class="w-44 px-2 py-1 border rounded text-sm" />
                        <span v-else>{{ item.custom_product_name || '-' }}</span>
                        <span class="ml-1 text-[10px] bg-slate-100 text-slate-600 rounded px-1">외주</span>
                      </template>
                    </td>
                    <td class="px-4 py-2 text-right">
                      <input
                        v-if="itemsEditable"
                        v-model.number="item.ordered_quantity"
                        type="number"
                        min="1"
                        step="any"
                        class="w-24 px-2 py-1 border rounded text-right"
                        @input="calculateLineTotal(idx)"
                      />
                      <span v-else class="text-sm">{{ item.ordered_quantity }}</span>
                    </td>
                    <td class="px-4 py-2 text-right">
                      <div v-if="itemsEditable">
                        <input
                          v-model.number="item.unit_price"
                          type="number"
                          min="0"
                          step="any"
                          class="w-28 px-2 py-1 border rounded text-right"
                          @input="calculateLineTotal(idx)"
                        />
                        <div v-if="item.last_price" class="text-xs text-gray-400 mt-1">
                          이전: {{ formatNumber(item.last_price) }}
                        </div>
                      </div>
                      <span v-else class="text-sm">{{ formatNumber(item.unit_price) }}</span>
                    </td>
                    <td class="px-4 py-2 text-sm text-right">{{ formatNumber(item.line_total || 0) }}</td>
                    <td v-if="isEdit" class="px-4 py-2 text-sm text-right">
                      {{ item.received_quantity || 0 }} / {{ item.ordered_quantity }}
                    </td>
                    <td v-if="itemsEditable" class="px-4 py-2 text-center">
                      <button
                        type="button"
                        @click="removeItem(idx)"
                        class="text-red-600 hover:text-red-800"
                      >
                        삭제
                      </button>
                    </td>
                  </tr>
                </tbody>
                <tfoot class="bg-gray-50">
                  <tr>
                    <td :colspan="isEdit ? 4 : 3" class="px-4 py-2 text-right font-medium">합계</td>
                    <td class="px-4 py-2 text-right font-medium">{{ formatNumber(totalAmount) }}</td>
                    <td v-if="isEdit"></td>
                    <td v-if="isEditable"></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </form>
      </div>

      <!-- 푸터 -->
      <div class="flex justify-between items-center px-6 py-4 border-t bg-gray-50">
        <div>
          <!-- 상태 변경 버튼 -->
          <template v-if="isEdit">
            <button
              v-if="purchaseOrder?.status === 'DRAFT'"
              type="button"
              @click="handleOrder"
              class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 mr-2"
            >
              주문 확정
            </button>
            <button
              v-if="purchaseOrder?.status === 'ORDERED'"
              type="button"
              @click="handleConfirm"
              class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 mr-2"
            >
              납기 확정
            </button>
            <!-- 롤백 버튼 -->
            <button
              v-if="canRollback"
              type="button"
              @click="handleRollback"
              class="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 mr-2"
            >
              {{ rollbackLabels[purchaseOrder?.status || ''] }} 롤백
            </button>
            <button
              v-if="canCancel"
              type="button"
              @click="handleCancel"
              class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              취소
            </button>
          </template>
        </div>
        <div class="flex gap-2">
          <!-- 인쇄/PDF 버튼 (수정 모드에서만) -->
          <template v-if="isEdit">
            <button
              type="button"
              @click="handlePrint"
              class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 flex items-center"
            >
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
              </svg>
              인쇄
            </button>
            <button
              type="button"
              @click="handleDownloadPDF"
              class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center"
            >
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              PDF
            </button>
          </template>
          <button
            type="button"
            @click="$emit('close')"
            class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
          >
            닫기
          </button>
          <button
            v-if="isEditable"
            type="button"
            @click="handleSubmit"
            :disabled="saving"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {{ saving ? '저장 중...' : (isEdit ? '수정' : '등록') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 부품 검색 모달 -->
    <PartSearchModal
      :show="showPartSearch"
      @close="showPartSearch = false"
      @select="handlePartSelect"
    />

    <!-- 공급업체 검색 모달 -->
    <SupplierSearchModal
      :show="showSupplierSearch"
      partner-type="supplier"
      @close="showSupplierSearch = false"
      @select="handleSupplierSelect"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import {
  purchaseOrderApi,
  type PurchaseOrder,
  type PurchaseOrderCreate,
  type PurchaseOrderUpdate,
  type PurchaseOrderItem,
  type PurchaseOrderItemCreate,
  poStatusLabels,
} from '@/api/purchaseOrder'
import { type Partner } from '@/api/partner'
import PartSearchModal from '@/views/production/components/PartSearchModal.vue'
import SupplierSearchModal from '@/views/production/components/SupplierSearchModal.vue'

const props = defineProps<{
  purchaseOrderId: number | null
}>()

const emit = defineEmits(['close', 'saved'])

// 상태
const loading = ref(false)
const saving = ref(false)
const purchaseOrder = ref<PurchaseOrder | null>(null)
const showPartSearch = ref(false)
const showSupplierSearch = ref(false)
const selectedSupplier = ref<Partner | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFiles = ref<File[]>([])

// 폼 데이터
const form = reactive({
  supplier_id: '' as number | '',
  order_date: new Date().toISOString().split('T')[0] as string,
  expected_delivery_date: '',
  currency: 'KRW',
  payment_terms: '',
  delivery_terms: '',
  remarks: '',
})

// 항목 목록
const items = ref<(PurchaseOrderItem | (PurchaseOrderItemCreate & { part?: any; line_total?: number; last_price?: number | null; received_quantity?: number }))[]>([])

// 상태 단계 (COMPLETED는 기존 데이터 호환용)
const statusOrder = ['DRAFT', 'ORDERED', 'CONFIRMED', 'RECEIVED']
const statusSteps: Record<string, string> = {
  DRAFT: '작성중',
  ORDERED: '주문완료',
  CONFIRMED: '납기확정',
  RECEIVED: '입고완료',
  COMPLETED: '완료(구)', // 기존 데이터 호환용
}

// 롤백 가능 여부 (DRAFT, CANCELLED는 롤백 불가)
const rollbackLabels: Record<string, string> = {
  ORDERED: '작성중으로',
  CONFIRMED: '주문완료로',
  RECEIVED: '납기확정으로',
  COMPLETED: '입고완료로', // 기존 데이터 호환용
}

// 계산된 속성
const isEdit = computed(() => !!props.purchaseOrderId)
// 취소 상태가 아니면 모두 수정 가능
const isEditable = computed(() => !isEdit.value || purchaseOrder.value?.status !== 'CANCELLED')
// #6 기안서에서 파생된 발주서 → 수량·단가·부품 수정 잠금(수정하려면 기안서를 다시 올려야 함)
const isApprovalDerived = computed(() => !!purchaseOrder.value?.source_approval_id)
const itemsEditable = computed(() => isEditable.value && !isApprovalDerived.value)
const canCancel = computed(() => {
  const status = purchaseOrder.value?.status
  return status === 'DRAFT' || status === 'ORDERED' || status === 'CONFIRMED' || status === 'RECEIVED'
})
const canRollback = computed(() => {
  const status = purchaseOrder.value?.status
  return status === 'ORDERED' || status === 'CONFIRMED' || status === 'RECEIVED' || status === 'COMPLETED'
})
const totalAmount = computed(() => items.value.reduce((sum, item) => sum + (item.line_total || 0), 0))
const selectedSupplierName = computed(() => {
  if (selectedSupplier.value) {
    return `${selectedSupplier.value.partner_code} - ${selectedSupplier.value.partner_name}`
  }
  if (purchaseOrder.value?.supplier) {
    return `${purchaseOrder.value.supplier.partner_code} - ${purchaseOrder.value.supplier.partner_name}`
  }
  return ''
})

// 상태 클래스
function getStatusClass(status: string): string {
  const currentStatus = purchaseOrder.value?.status
  const currentIdx = statusOrder.indexOf(currentStatus || '')
  const statusIdx = statusOrder.indexOf(status)

  if (currentStatus === 'CANCELLED') {
    return 'bg-red-100 text-red-800'
  }
  if (statusIdx < currentIdx) {
    return 'bg-green-500 text-white'
  }
  if (statusIdx === currentIdx) {
    return 'bg-blue-500 text-white'
  }
  return 'bg-gray-200 text-gray-600'
}

// 데이터 로드
async function loadData() {
  if (!props.purchaseOrderId) return

  loading.value = true
  try {
    purchaseOrder.value = await purchaseOrderApi.getById(props.purchaseOrderId)

    // 폼 데이터 설정
    form.supplier_id = purchaseOrder.value.supplier_id
    form.order_date = purchaseOrder.value.order_date
    form.expected_delivery_date = purchaseOrder.value.expected_delivery_date || ''
    form.currency = purchaseOrder.value.currency
    form.payment_terms = purchaseOrder.value.payment_terms || ''
    form.delivery_terms = purchaseOrder.value.delivery_terms || ''
    form.remarks = purchaseOrder.value.remarks || ''

    // 항목 데이터 설정
    items.value = purchaseOrder.value.items || []
  } catch (error) {
    console.error('발주서 조회 실패:', error)
    alert('발주서를 불러오는데 실패했습니다.')
  } finally {
    loading.value = false
  }
}

// 항목 금액 계산 및 저장
let updateItemTimeout: ReturnType<typeof setTimeout> | null = null
function calculateLineTotal(idx: number) {
  const item = items.value[idx]
  if (!item) return
  item.line_total = (item.ordered_quantity || 0) * (item.unit_price || 0)

  // 수정 모드일 때 항목 변경 시 API 호출 (디바운스)
  if (isEdit.value && 'id' in item && item.id) {
    if (updateItemTimeout) clearTimeout(updateItemTimeout)
    updateItemTimeout = setTimeout(() => {
      updateItemOnServer(item as PurchaseOrderItem)
    }, 500)
  }
}

// 서버에 항목 수정 반영
async function updateItemOnServer(item: PurchaseOrderItem) {
  if (!props.purchaseOrderId || !item.id) return

  try {
    await purchaseOrderApi.updateItem(props.purchaseOrderId, item.id, {
      ordered_quantity: (typeof item.ordered_quantity === 'number' && !Number.isNaN(item.ordered_quantity)) ? item.ordered_quantity : 0,
      unit_price: (typeof item.unit_price === 'number' && !Number.isNaN(item.unit_price)) ? item.unit_price : 0,
    })
    // 성공 시 조용히 업데이트 완료
  } catch (error: any) {
    console.error('항목 수정 실패:', error)
    alert(error.response?.data?.detail?.message || '항목 수정에 실패했습니다.')
    // 실패 시 다시 로드
    await loadData()
  }
}

// 공급업체 선택
function handleSupplierSelect(supplier: Partner) {
  selectedSupplier.value = supplier
  form.supplier_id = supplier.id
  showSupplierSearch.value = false
}

// 부품 선택
async function handlePartSelect(part: any) {
  // 이전 구매 가격 조회
  let lastPrice = 0
  try {
    const history = await purchaseOrderApi.getPartPriceHistory(part.id)
    if (history && history.length > 0) {
      lastPrice = history[0]?.unit_price ?? 0
    }
  } catch (e) {
    // 이전 가격이 없으면 무시
  }

  // 부품에 등록된 단가가 있으면 기본값으로 사용
  const defaultPrice = part.unit_price || lastPrice || 0

  items.value.push({
    part_id: part.id,
    ordered_quantity: 1,
    unit_price: defaultPrice,
    line_total: defaultPrice,
    last_price: lastPrice || null,
    part: part,
  } as any)
  showPartSearch.value = false
}

// BOM 미등록(자유입력) 품목 추가 — 품명 직접 입력으로 발주(외주 등)
function addCustomItem() {
  items.value.push({
    part_id: null,
    custom_product_code: '',
    custom_product_name: '',
    ordered_quantity: 1,
    unit_price: 0,
    line_total: 0,
    last_price: null,
  } as any)
}

// 항목 삭제
function removeItem(idx: number) {
  items.value.splice(idx, 1)
}

// 저장
async function handleSubmit() {
  if (!form.supplier_id) {
    alert('공급업체를 선택해주세요.')
    return
  }
  if (items.value.length === 0) {
    alert('발주 항목을 추가해주세요.')
    return
  }

  saving.value = true
  try {
    if (isEdit.value) {
      // 수정
      await purchaseOrderApi.update(props.purchaseOrderId!, {
        supplier_id: form.supplier_id as number,
        order_date: form.order_date,
        expected_delivery_date: form.expected_delivery_date || undefined,
        currency: form.currency,
        payment_terms: form.payment_terms || undefined,
        delivery_terms: form.delivery_terms || undefined,
        remarks: form.remarks || undefined,
      })
      alert('발주서가 수정되었습니다.')
    } else {
      // 생성
      const createData: PurchaseOrderCreate = {
        supplier_id: form.supplier_id as number,
        order_date: form.order_date,
        expected_delivery_date: form.expected_delivery_date || undefined,
        currency: form.currency,
        payment_terms: form.payment_terms || undefined,
        delivery_terms: form.delivery_terms || undefined,
        remarks: form.remarks || undefined,
        items: items.value.map((item, idx) => ({
          part_id: item.part_id || (item as any).part?.id || null,
          custom_product_code: (item as any).custom_product_code || null,
          custom_product_name: (item as any).custom_product_name || null,
          ordered_quantity: (typeof item.ordered_quantity === 'number' && !Number.isNaN(item.ordered_quantity)) ? item.ordered_quantity : 0,
          unit_price: (typeof item.unit_price === 'number' && !Number.isNaN(item.unit_price)) ? item.unit_price : 0,
          sort_order: idx,
        })),
      }
      const newPurchaseOrder = await purchaseOrderApi.create(createData)

      // 선택된 파일 업로드
      if (selectedFiles.value.length > 0) {
        for (const file of selectedFiles.value) {
          try {
            await purchaseOrderApi.uploadDocument(newPurchaseOrder.id, file)
          } catch (error) {
            console.error('파일 업로드 실패:', error)
          }
        }
      }

      alert('발주서가 등록되었습니다.')
    }
    emit('saved')
  } catch (error: any) {
    console.error('저장 실패:', error)
    alert(error.response?.data?.detail?.message || '저장에 실패했습니다.')
  } finally {
    saving.value = false
  }
}

// 상태 변경 액션
async function handleOrder() {
  if (!confirm('주문을 확정하시겠습니까?')) return
  try {
    await purchaseOrderApi.order(props.purchaseOrderId!)
    alert('주문이 확정되었습니다.')
    emit('saved')
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '주문 확정에 실패했습니다.')
  }
}

async function handleConfirm() {
  const dateStr = prompt('납기 확정일을 입력하세요 (YYYY-MM-DD):', form.expected_delivery_date)
  if (!dateStr) return
  try {
    await purchaseOrderApi.confirm(props.purchaseOrderId!, {
      expected_delivery_date: dateStr,
    })
    alert('납기가 확정되었습니다.')
    emit('saved')
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '납기 확정에 실패했습니다.')
  }
}

async function handleRollback() {
  const status = purchaseOrder.value?.status
  const label = rollbackLabels[status || ''] || '이전 상태로'
  const message = status === 'RECEIVED'
    ? `${label} 롤백하시겠습니까?\n입고완료 상태에서 롤백 시 재고가 차감됩니다.`
    : `${label} 롤백하시겠습니까?`

  if (!confirm(message)) return

  try {
    await purchaseOrderApi.rollback(props.purchaseOrderId!)
    alert('롤백이 완료되었습니다.')
    emit('saved')
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '롤백에 실패했습니다.')
  }
}

async function handleCancel() {
  const reason = prompt('취소 사유를 입력하세요:')
  if (reason === null) return
  try {
    await purchaseOrderApi.cancel(props.purchaseOrderId!, reason)
    alert('발주가 취소되었습니다.')
    emit('saved')
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '취소에 실패했습니다.')
  }
}

// 파일 선택 처리
function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files) return

  const files = Array.from(input.files)

  if (isEdit.value && props.purchaseOrderId) {
    // 수정 모드: 바로 업로드
    files.forEach(async (file) => {
      try {
        await purchaseOrderApi.uploadDocument(props.purchaseOrderId!, file)
        await loadData() // 다시 로드
      } catch (error: any) {
        console.error('파일 업로드 실패:', error)
        alert(`파일 업로드 실패: ${file.name}`)
      }
    })
  } else {
    // 신규 등록: 선택된 파일 목록에 추가
    selectedFiles.value = [...selectedFiles.value, ...files]
  }

  // 파일 입력 초기화
  input.value = ''
}

// 기존 파일 삭제
async function handleDeleteFile(fileIndex: number) {
  if (!props.purchaseOrderId) return

  if (!confirm('첨부파일을 삭제하시겠습니까?')) return

  try {
    await purchaseOrderApi.deleteDocument(props.purchaseOrderId, fileIndex)
    await loadData()
    alert('파일이 삭제되었습니다.')
  } catch (error: any) {
    console.error('파일 삭제 실패:', error)
    alert(error.response?.data?.detail?.message || '파일 삭제에 실패했습니다.')
  }
}

// 선택된 파일 제거 (신규 등록 시)
function removeSelectedFile(index: number) {
  selectedFiles.value.splice(index, 1)
}

// 인쇄
function handlePrint() {
  if (!props.purchaseOrderId) return
  window.open(`/print/purchase-order/${props.purchaseOrderId}`, '_blank')
}

// PDF 다운로드
async function handleDownloadPDF() {
  if (!props.purchaseOrderId) return
  try {
    await purchaseOrderApi.downloadPDF(props.purchaseOrderId, purchaseOrder.value?.po_number)
  } catch (error: any) {
    console.error('PDF 다운로드 실패:', error)
    alert('PDF 다운로드에 실패했습니다.')
  }
}

// 포맷 (소수점 2자리까지)
function formatNumber(num: number): string {
  return new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(num || 0)
}

// 초기화
onMounted(() => {
  if (props.purchaseOrderId) {
    loadData()
  }
})

watch(() => props.purchaseOrderId, (newVal) => {
  if (newVal) {
    loadData()
  }
})
</script>
