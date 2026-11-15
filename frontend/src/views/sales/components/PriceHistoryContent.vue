<template>
  <div class="p-4 sm:p-6">
    <h2 class="text-xl font-bold text-gray-900 mb-6">고객별 가격 이력</h2>

    <!-- 필터 -->
    <div class="bg-white rounded-lg shadow-sm border p-4 mb-4">
      <div class="flex flex-wrap gap-3 items-end">
        <div class="relative flex-shrink-0">
          <label class="block text-xs text-gray-500 mb-1">고객사</label>
          <input
            v-model="customerSearch"
            @focus="showDropdown = true; highlightedIndex = 0"
            @input="showDropdown = true; highlightedIndex = 0"
            @blur="hideDropdownDelayed"
            @keydown.down.prevent="moveHighlight(1)"
            @keydown.up.prevent="moveHighlight(-1)"
            @keydown.enter.prevent="handleEnter"
            @keydown.escape="showDropdown = false"
            class="border rounded-md px-3 py-2 text-sm w-56"
            placeholder="고객사명 검색..."
          />
          <div v-if="showDropdown && filteredCustomers.length > 0"
            class="absolute z-10 w-64 mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
            <div v-for="(c, idx) in filteredCustomers" :key="c.id"
              @mousedown.prevent="selectCustomer(c)"
              @mouseenter="highlightedIndex = idx"
              class="px-3 py-2 text-sm cursor-pointer"
              :class="highlightedIndex === idx ? 'bg-blue-100 font-medium' : (selectedCustomerId === c.id ? 'bg-blue-50 font-medium' : 'hover:bg-blue-50')">
              {{ c.partner_name }}
            </div>
          </div>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">제품 코드 (선택)</label>
          <input v-model="productFilter" @input="debouncedLoad" class="border rounded-md px-3 py-2 text-sm w-64" placeholder="HXB13-PSD-B-..." />
        </div>
      </div>
    </div>

    <!-- 결과 -->
    <div class="bg-white rounded-lg shadow-sm border overflow-hidden">
      <div v-if="!selectedCustomerId" class="p-8 text-center text-gray-400">
        고객사를 선택하세요.
      </div>
      <div v-else-if="loading" class="p-8 text-center text-gray-400">로딩 중...</div>
      <div v-else-if="groupedHistory.length === 0" class="p-8 text-center text-gray-400">
        이 고객에게 발송한 가격 이력이 없습니다.
      </div>
      <div v-else>
        <!-- 제품별 그룹 -->
        <div v-for="group in groupedHistory" :key="group.product_code" class="border-b last:border-b-0">
          <div class="bg-gray-50 px-4 py-2 flex justify-between items-center">
            <span class="text-sm font-bold text-gray-800">{{ group.product_code }}</span>
            <div class="flex gap-4 text-xs text-gray-500">
              <span>최근가: <span class="font-medium text-gray-700">{{ group.items[0]?.currency }} {{ group.items[0]?.unit_price.toLocaleString() }}</span></span>
              <span v-if="group.items.length > 1">
                변동:
                <span :class="group.trend > 0 ? 'text-red-600' : group.trend < 0 ? 'text-green-600' : 'text-gray-500'" class="font-medium">
                  {{ group.trend > 0 ? '↑' : group.trend < 0 ? '↓' : '→' }}
                  {{ Math.abs(group.trend).toFixed(1) }}%
                </span>
              </span>
              <span>{{ group.items.length }}건</span>
            </div>
          </div>
          <table class="min-w-full">
            <tbody>
              <tr v-for="(item, idx) in group.items" :key="idx" class="hover:bg-gray-50">
                <td class="px-4 py-2 text-sm text-blue-600 w-40 cursor-pointer hover:underline"
                  @click="openDoc(item)">{{ item.document_number }}</td>
                <td class="px-4 py-2 text-sm w-20">
                  <span :class="item.document_type === 'QUOTATION' ? 'text-gray-600' : item.document_type === 'PI' ? 'text-purple-600' : 'text-amber-600'" class="text-xs font-medium">
                    {{ item.document_type === 'QUOTATION' ? 'Q' : item.document_type }}
                  </span>
                </td>
                <td class="px-4 py-2 text-sm text-right w-32 font-medium">{{ item.currency }} {{ item.unit_price.toLocaleString() }}</td>
                <td class="px-4 py-2 text-sm text-center w-20 text-gray-500">× {{ item.quantity }}</td>
                <td class="px-4 py-2 text-sm text-gray-500 w-28">{{ item.document_date }}</td>
                <td class="px-4 py-2 text-sm text-center w-20">
                  <span :class="statusClass(item.status)" class="inline-block px-1.5 py-0.5 text-xs rounded whitespace-nowrap">
                    {{ statusLabel(item.status) }}
                  </span>
                </td>
                <!-- 이전 대비 변동 -->
                <td class="px-4 py-2 text-sm text-right w-24">
                  <span v-if="idx < group.items.length - 1 && group.items[idx + 1]" :class="item.unit_price > group.items[idx + 1]!.unit_price ? 'text-red-500' : item.unit_price < group.items[idx + 1]!.unit_price ? 'text-green-500' : 'text-gray-400'" class="text-xs">
                    {{ item.unit_price > group.items[idx + 1]!.unit_price ? '↑' : item.unit_price < group.items[idx + 1]!.unit_price ? '↓' : '→' }}
                    {{ Math.abs(((item.unit_price - group.items[idx + 1]!.unit_price) / group.items[idx + 1]!.unit_price) * 100).toFixed(1) }}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 문서 상세 모달 (인플레이스) -->
    <SalesDocumentFormModal
      v-if="showDocModal && viewingDoc"
      :document="viewingDoc"
      :document-type="viewingDoc.document_type"
      @close="showDocModal = false; viewingDoc = null"
      @saved="showDocModal = false; viewingDoc = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { salesDocumentApi, type SalesDocument, type PriceHistoryItem } from '@/api/salesDocument'
import { useToast } from '@/composables/useToast'
import SalesDocumentFormModal from './SalesDocumentFormModal.vue'
import apiClient from '@/api/client'

const { showToast } = useToast()

// 문서 상세 모달
const showDocModal = ref(false)
const viewingDoc = ref<SalesDocument | null>(null)

async function openDoc(item: any) {
  if (!item.document_id) return
  try {
    const res = await salesDocumentApi.getById(item.document_id)
    viewingDoc.value = res.data
    showDocModal.value = true
  } catch {
    showToast('문서를 불러오는데 실패했습니다', 'error')
  }
}

const loading = ref(false)
const customers = ref<{ id: number; partner_name: string }[]>([])
const selectedCustomerId = ref<number | undefined>(undefined)
const customerSearch = ref('')
const showDropdown = ref(false)
const highlightedIndex = ref(0)

function moveHighlight(delta: number) {
  const list = filteredCustomers.value
  if (list.length === 0) return
  highlightedIndex.value = (highlightedIndex.value + delta + list.length) % list.length
}

function handleEnter() {
  const list = filteredCustomers.value
  if (list.length === 1) { selectCustomer(list[0]!); return }
  if (list.length > 0 && highlightedIndex.value >= 0) {
    selectCustomer(list[highlightedIndex.value]!)
  }
}

function hideDropdownDelayed() { setTimeout(() => { showDropdown.value = false }, 200) }
const productFilter = ref('')
const history = ref<PriceHistoryItem[]>([])

const filteredCustomers = computed(() => {
  if (!customerSearch.value) return customers.value
  const q = customerSearch.value.toLowerCase()
  return customers.value.filter(c => c.partner_name.toLowerCase().includes(q))
})

// 제품별로 그룹화 + 가격 추이 계산
const groupedHistory = computed(() => {
  const map = new Map<string, PriceHistoryItem[]>()
  for (const item of history.value) {
    if (!map.has(item.product_code)) map.set(item.product_code, [])
    map.get(item.product_code)!.push(item)
  }

  return Array.from(map.entries()).map(([code, items]) => {
    // 추이: 최근가 vs 최초가
    let trend = 0
    if (items.length >= 2) {
      const latest = items[0]?.unit_price ?? 0
      const oldest = items[items.length - 1]?.unit_price ?? 0
      if (oldest > 0) trend = ((latest - oldest) / oldest) * 100
    }
    return { product_code: code, items, trend }
  })
})

function selectCustomer(c: { id: number; partner_name: string }) {
  selectedCustomerId.value = c.id
  customerSearch.value = c.partner_name
  showDropdown.value = false
  loadData()
}

async function loadData() {
  if (!selectedCustomerId.value) return
  loading.value = true
  try {
    const res = await salesDocumentApi.getCustomerPriceHistory(
      selectedCustomerId.value,
      productFilter.value || undefined,
    )
    history.value = res.data
  } catch {
    showToast('가격 이력을 불러오는데 실패했습니다', 'error')
  } finally {
    loading.value = false
  }
}

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedLoad() { clearTimeout(debounceTimer); debounceTimer = setTimeout(loadData, 300) }

async function loadCustomers() {
  try {
    const res = await apiClient.get('/partners', { params: { is_customer: true, limit: 500 } })
    customers.value = (res.data.items || res.data).map((c: any) => ({ id: c.id, partner_name: c.partner_name }))
  } catch { /* ignore */ }
}

function statusLabel(s: string) { return { DRAFT: '작성중', SENT: '발송', CONFIRMED: '확정', CANCELLED: '취소' }[s] || s }
function statusClass(s: string) { return { DRAFT: 'bg-gray-100 text-gray-600', SENT: 'bg-blue-100 text-blue-600', CONFIRMED: 'bg-green-100 text-green-600', CANCELLED: 'bg-red-100 text-red-600' }[s] || '' }

onMounted(loadCustomers)
defineExpose({ loadData })
</script>
