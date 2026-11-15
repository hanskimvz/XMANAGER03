<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">재고 관리</h1>

    <!-- 검색 및 필터 섹션 -->
    <div class="bg-white shadow rounded-lg p-6 mb-6">
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">검색</label>
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="품번 또는 부품명으로 검색"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            @keyup.enter="searchInventory"
            @input="debouncedSearch"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">대분류</label>
          <select
            v-model="filters.product_line_id"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            @change="searchInventory"
          >
            <option :value="undefined">전체</option>
            <option v-for="item in productLines" :key="item.id" :value="item.id">
              {{ item.code }} - {{ item.name_ko }}
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">소분류</label>
          <select
            v-model="filters.part_group_id"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            @change="searchInventory"
          >
            <option :value="undefined">전체</option>
            <option v-for="item in partGroups" :key="item.id" :value="item.id">
              {{ item.code }} - {{ item.name_ko }}
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">레벨</label>
          <select
            v-model="filters.level_id"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            @change="searchInventory"
          >
            <option :value="undefined">전체</option>
            <option v-for="item in levels" :key="item.id" :value="item.id">
              {{ item.code }} - {{ item.name_ko }}
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">상태</label>
          <select
            v-model="filters.status"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            @change="searchInventory"
          >
            <option :value="undefined">전체</option>
            <option value="NORMAL">정상</option>
            <option value="LOW">부족</option>
            <option value="OUT_OF_STOCK">재고없음</option>
          </select>
        </div>
      </div>
      <div class="flex justify-between items-center mt-4">
        <label class="inline-flex items-center">
          <input
            v-model="filters.low_stock_only"
            type="checkbox"
            class="form-checkbox h-5 w-5 text-blue-600 rounded"
            @change="searchInventory"
          />
          <span class="ml-2 text-sm text-gray-700">부족 재고만 표시</span>
        </label>
        <div class="flex space-x-2">
          <button
            @click="resetFilters"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            필터 초기화
          </button>
          <button
            @click="searchInventory"
            class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            검색
          </button>
        </div>
      </div>
    </div>

    <!-- 테이블 섹션 -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-semibold">
          재고 목록
          <span class="text-sm text-gray-500 font-normal">(총 {{ totalItems }}건)</span>
        </h2>
        <div class="flex space-x-2">
          <button
            v-if="selectedIds.size > 0"
            @click="openBulkOrder"
            class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded flex items-center"
          >
            <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            선택 발주 ({{ selectedIds.size }})
          </button>
          <button
            @click="generateMissingLots"
            :disabled="isGeneratingLots"
            class="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
            title="재고가 있지만 로트가 없는 부품에 초기 로트를 생성합니다"
          >
            <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            {{ isGeneratingLots ? '생성 중...' : '누락 로트 생성' }}
          </button>
          <button
            @click="exportExcel"
            class="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded flex items-center"
          >
            <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            엑셀 다운로드
          </button>
        </div>
      </div>

      <!-- 로딩 중 -->
      <div v-if="loading" class="text-center py-8">
        <p class="text-gray-500">로딩 중...</p>
      </div>

      <!-- 에러 -->
      <div v-else-if="error" class="text-center py-8">
        <p class="text-red-500">{{ error }}</p>
      </div>

      <!-- 데이터 테이블 -->
      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-3 py-3 w-8 text-center">
                <input type="checkbox" :checked="allOnPageSelected" @change="toggleSelectAll"
                  class="w-4 h-4 rounded cursor-pointer accent-blue-600" title="현재 페이지 전체 선택" />
              </th>
              <th
                @click="sortBy('part_number')"
                class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
              >
                <div class="flex items-center space-x-1">
                  <span>품번</span>
                  <SortIcon :active="sortColumn === 'part_number'" :desc="sortDesc" />
                </div>
              </th>
              <th
                @click="sortBy('part_name')"
                class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
              >
                <div class="flex items-center space-x-1">
                  <span>부품명</span>
                  <SortIcon :active="sortColumn === 'part_name'" :desc="sortDesc" />
                </div>
              </th>
              <th
                @click="sortBy('quantity_on_hand')"
                class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
              >
                <div class="flex items-center justify-end space-x-1">
                  <span>현재고</span>
                  <SortIcon :active="sortColumn === 'quantity_on_hand'" :desc="sortDesc" />
                </div>
              </th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">재주문점</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">단가</th>
              <th
                @click="sortBy('status')"
                class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
              >
                <div class="flex items-center justify-center space-x-1">
                  <span>상태</span>
                  <SortIcon :active="sortColumn === 'status'" :desc="sortDesc" />
                </div>
              </th>
              <th
                @click="sortBy('updated_at')"
                class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
              >
                <div class="flex items-center justify-center space-x-1">
                  <span>수정일</span>
                  <SortIcon :active="sortColumn === 'updated_at'" :desc="sortDesc" />
                </div>
              </th>
              <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">작업</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr
              v-for="item in inventoryList"
              :key="item.id"
              class="hover:bg-gray-50"
              :class="{
                'bg-red-50': item.status === 'OUT_OF_STOCK',
                'bg-yellow-50': item.status === 'LOW',
                'bg-blue-50': selectedIds.has(item.id)
              }"
            >
              <td class="px-3 py-3 text-center" @click.stop>
                <input type="checkbox" :checked="selectedIds.has(item.id)" @change="toggleSelect(item)"
                  class="w-4 h-4 rounded cursor-pointer accent-blue-600" />
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm font-mono">
                <button
                  v-if="item.part?.id"
                  @click="openPartDetailModal(item.part.id)"
                  class="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                  :title="`부품 상세 보기: ${item.part?.part_name || ''}`"
                >
                  {{ item.part?.part_number_display || item.part?.part_number || '-' }}
                </button>
                <span v-else>{{ item.part?.part_number_display || item.part?.part_number || '-' }}</span>
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm">
                {{ item.part?.part_name || '-' }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-right font-semibold">
                {{ formatNumber(item.quantity_on_hand) }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-500">
                {{ item.reorder_point ? formatNumber(item.reorder_point) : '-' }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-right">
                {{ item.unit_cost ? formatCurrency(item.unit_cost) : '-' }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-center">
                <span
                  class="px-2 py-1 text-xs rounded-full"
                  :class="getStatusStyle(item.status)"
                >
                  {{ getStatusLabel(item.status) }}
                </span>
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-center text-gray-500">
                {{ formatDate(item.updated_at) }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-center">
                <div class="flex justify-center space-x-2">
                  <button
                    @click="openAdjustModal(item)"
                    class="text-blue-600 hover:text-blue-800 text-sm"
                    title="재고 조정"
                  >
                    조정
                  </button>
                  <button
                    @click="openHistoryModal(item)"
                    class="text-gray-600 hover:text-gray-800 text-sm"
                    title="거래 이력"
                  >
                    이력
                  </button>
                  <button
                    @click="openEditModal(item)"
                    class="text-green-600 hover:text-green-800 text-sm"
                    title="설정 수정"
                  >
                    설정
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="inventoryList.length === 0">
              <td colspan="9" class="px-4 py-8 text-center text-gray-500">
                재고 데이터가 없습니다.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 페이지네이션 -->
      <Pagination
        v-if="totalItems > 0"
        :current-page="currentPage"
        :page-size="pageSize"
        :total="totalItems"
        @update:current-page="handlePageChange"
        @update:page-size="handlePageSizeChange"
        class="mt-4"
      />
    </div>

    <!-- 재고 조정 모달 -->
    <InventoryAdjustModal
      :show="showAdjustModal"
      :inventory="selectedInventory"
      @close="closeAdjustModal"
      @submit="handleAdjust"
    />

    <!-- 거래 이력 모달 -->
    <InventoryHistoryModal
      :show="showHistoryModal"
      :inventory="selectedInventory"
      @close="closeHistoryModal"
    />

    <!-- 설정 수정 모달 -->
    <div v-if="showEditModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-full max-w-md">
        <h3 class="text-lg font-semibold mb-4">재고 설정 수정</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">부품</label>
            <p class="text-sm text-gray-600">
              {{ selectedInventory?.part?.part_number_display }} - {{ selectedInventory?.part?.part_name }}
            </p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">재주문점</label>
            <input
              v-model.number="editFormData.reorder_point"
              type="number"
              min="0"
              step="0.001"
              class="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="재주문 기준 수량"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">재주문량</label>
            <input
              v-model.number="editFormData.reorder_qty"
              type="number"
              min="0"
              step="0.001"
              class="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="재주문 시 수량"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">단가</label>
            <input
              v-model.number="editFormData.unit_cost"
              type="number"
              min="0"
              step="0.01"
              class="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="단가 (원)"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">비고</label>
            <textarea
              v-model="editFormData.remarks"
              rows="2"
              class="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="비고"
            ></textarea>
          </div>
        </div>
        <div class="flex justify-end space-x-2 mt-6">
          <button
            @click="closeEditModal"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            취소
          </button>
          <button
            @click="handleEditSubmit"
            class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            저장
          </button>
        </div>
      </div>
    </div>

    <!-- 부품 상세 모달 -->
    <PartDetailModal
      :show="showPartDetailModal"
      :part-id="selectedPartId"
      @close="closePartDetailModal"
    />

    <!-- 일괄 발주 모달 -->
    <BulkPurchaseOrderModal
      v-if="showBulkOrder"
      :items="bulkOrderItems"
      @close="showBulkOrder = false"
      @created="onBulkOrderCreated"
    />

    <!-- 토스트 알림 -->
    <div
      v-if="toast.show"
      class="fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 transition-opacity duration-300"
      :class="{
        'bg-green-500 text-white': toast.type === 'success',
        'bg-red-500 text-white': toast.type === 'error',
        'bg-yellow-500 text-white': toast.type === 'warning'
      }"
    >
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import {
  inventoryApi,
  inventoryStatusLabels,
  inventoryStatusStyles,
  type InventoryListItem,
  type InventoryStatus,
  type InventoryAdjust,
  type InventorySearchParams
} from '@/api/inventory'
import { inventoryLotApi } from '@/api/inventoryLot'
import { downloadAuthedUrl } from '@/utils/download'
import { productLineApi, partGroupApi, levelApi, type CodeMaster } from '@/api/codeMaster'
import SortIcon from '@/components/SortIcon.vue'
import Pagination from '@/components/Pagination.vue'
import InventoryAdjustModal from '@/views/production/components/InventoryAdjustModal.vue'
import InventoryHistoryModal from '@/views/production/components/InventoryHistoryModal.vue'
import PartDetailModal from '@/views/production/components/PartDetailModal.vue'
import BulkPurchaseOrderModal from '@/views/production/components/BulkPurchaseOrderModal.vue'
import { useRouter } from 'vue-router'
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'

const router = useRouter()

// 상태
const loading = ref(false)
const error = ref<string | null>(null)

// 다중 선택 → 일괄 발주
const selectedIds = ref<Set<number>>(new Set())
const selectedMap = ref<Map<number, InventoryListItem>>(new Map())  // 페이지 넘어가도 선택 데이터 유지
const showBulkOrder = ref(false)
const bulkOrderItems = ref<any[]>([])

const allOnPageSelected = computed(() =>
  inventoryList.value.length > 0 && inventoryList.value.every(it => selectedIds.value.has(it.id)))

function toggleSelect(item: InventoryListItem) {
  const next = new Set(selectedIds.value)
  if (next.has(item.id)) { next.delete(item.id); selectedMap.value.delete(item.id) }
  else { next.add(item.id); selectedMap.value.set(item.id, item) }
  selectedIds.value = next
}

function toggleSelectAll() {
  const next = new Set(selectedIds.value)
  if (allOnPageSelected.value) {
    inventoryList.value.forEach(it => { next.delete(it.id); selectedMap.value.delete(it.id) })
  } else {
    inventoryList.value.forEach(it => { next.add(it.id); selectedMap.value.set(it.id, it) })
  }
  selectedIds.value = next
}

function openBulkOrder() {
  bulkOrderItems.value = Array.from(selectedIds.value)
    .map(id => selectedMap.value.get(id))
    .filter(Boolean)
    .map((it: any) => ({
      part_id: it.part_id,
      part_number: it.part?.part_number_display || it.part?.part_number || '-',
      part_name: it.part?.part_name || '-',
      on_hand: it.quantity_on_hand,
      reorder_point: it.reorder_point,
      unit_cost: it.unit_cost,
    }))
  showBulkOrder.value = true
}

function onBulkOrderCreated(poId: number) {
  showBulkOrder.value = false
  selectedIds.value = new Set()
  selectedMap.value = new Map()
  router.push(`/purchase-orders?highlight=${poId}`)
}
const inventoryList = ref<InventoryListItem[]>([])
const totalItems = ref(0)
const isGeneratingLots = ref(false)

// 코드 마스터 데이터
const productLines = ref<CodeMaster[]>([])
const partGroups = ref<CodeMaster[]>([])
const levels = ref<CodeMaster[]>([])

// 페이지네이션
const currentPage = ref(1)
const pageSize = ref(20)

// 정렬
const sortColumn = ref('updated_at')
const sortDesc = ref(true)

// 검색/필터
const searchKeyword = ref('')
const filters = reactive<{
  status?: InventoryStatus
  low_stock_only: boolean
  product_line_id?: number
  part_group_id?: number
  level_id?: number
}>({
  status: undefined,
  low_stock_only: false,
  product_line_id: undefined,
  part_group_id: undefined,
  level_id: undefined
})

// 모달 상태
const showAdjustModal = ref(false)
const showHistoryModal = ref(false)
const showEditModal = ref(false)
const selectedInventory = ref<InventoryListItem | null>(null)

// 부품 상세 모달 상태
const showPartDetailModal = ref(false)
const selectedPartId = ref<number | null>(null)

// 설정 수정 폼
const editFormData = reactive({
  reorder_point: undefined as number | undefined,
  reorder_qty: undefined as number | undefined,
  unit_cost: undefined as number | undefined,
  remarks: ''
})

// 토스트
const toast = reactive({
  show: false,
  message: '',
  type: 'success' as 'success' | 'error' | 'warning'
})

// 코드 마스터 로드
const loadCodeMasters = async () => {
  try {
    const [productLineRes, partGroupRes, levelRes] = await Promise.all([
      productLineApi.getAll(),
      partGroupApi.getAll(),
      levelApi.getAll()
    ])
    productLines.value = productLineRes.data
    partGroups.value = partGroupRes.data
    levels.value = levelRes.data
  } catch (err) {
    console.error('코드 마스터 로드 실패:', err)
  }
}

// 데이터 로드
const loadInventory = async () => {
  loading.value = true
  error.value = null

  try {
    const params: InventorySearchParams = {
      keyword: searchKeyword.value || undefined,
      status: filters.status,
      low_stock_only: filters.low_stock_only,
      product_line_id: filters.product_line_id,
      part_group_id: filters.part_group_id,
      level_id: filters.level_id,
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      order_by: sortColumn.value,
      order_desc: sortDesc.value
    }

    const response = await inventoryApi.getAll(params)
    inventoryList.value = response.items
    totalItems.value = response.total
  } catch (err: any) {
    console.error('재고 목록 조회 실패:', err)
    error.value = err.response?.data?.detail || '재고 목록을 불러오는 데 실패했습니다.'
  } finally {
    loading.value = false
  }
}

// 검색
const debouncedSearch = useDebouncedSearch(() => searchInventory())
const searchInventory = () => {
  currentPage.value = 1
  loadInventory()
}

// 필터 초기화
const resetFilters = () => {
  searchKeyword.value = ''
  filters.status = undefined
  filters.low_stock_only = false
  filters.product_line_id = undefined
  filters.part_group_id = undefined
  filters.level_id = undefined
  currentPage.value = 1
  loadInventory()
}

// 정렬
const sortBy = (column: string) => {
  if (sortColumn.value === column) {
    sortDesc.value = !sortDesc.value
  } else {
    sortColumn.value = column
    sortDesc.value = true
  }
  loadInventory()
}

// 페이지 변경
const handlePageChange = (page: number) => {
  currentPage.value = page
  loadInventory()
}

const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  loadInventory()
}

// 엑셀 내보내기
const exportExcel = () => {
  // v0.41.0: 상대경로+params 로 인증 blob 다운로드.
  // (getExportExcelUrl 은 운영에서 baseURL('/api/v1')을 포함해 반환 → apiClient 가 다시 접두어를 붙여 이중경로가 되므로 사용하지 않음)
  const params: Record<string, unknown> = {
    keyword: searchKeyword.value || undefined,
    status: filters.status || undefined,
  }
  if (filters.low_stock_only) params.low_stock_only = true
  downloadAuthedUrl('/inventory/export/excel', 'inventory.xlsx', params).catch((e) => console.error('엑셀 내보내기 실패', e))
}

// 누락 로트 생성
const generateMissingLots = async () => {
  if (isGeneratingLots.value) return

  if (!confirm('재고가 있지만 로트가 없는 부품에 초기 로트를 생성하시겠습니까?\n\n생성된 로트는 "INIT-날짜-순번" 형식의 로트번호를 갖습니다.')) {
    return
  }

  isGeneratingLots.value = true

  try {
    const result = await inventoryLotApi.generateMissingLots()

    if (result.created_count > 0) {
      showToast(`${result.created_count}개의 로트가 생성되었습니다.`, 'success')
      // 생성된 로트 상세 정보를 콘솔에 출력 (디버깅용)
      console.log('생성된 로트:', result.details)
    } else {
      showToast('생성할 로트가 없습니다. (모든 재고에 이미 로트가 있습니다)', 'warning')
    }

    // 목록 새로고침
    loadInventory()
  } catch (err: any) {
    console.error('누락 로트 생성 실패:', err)
    showToast(err.response?.data?.detail?.message || '누락 로트 생성에 실패했습니다.', 'error')
  } finally {
    isGeneratingLots.value = false
  }
}

// 재고 조정 모달
const openAdjustModal = (item: InventoryListItem) => {
  selectedInventory.value = item
  showAdjustModal.value = true
}

const closeAdjustModal = () => {
  showAdjustModal.value = false
  selectedInventory.value = null
}

const handleAdjust = async (data: InventoryAdjust, files: File[] = []) => {
  if (!selectedInventory.value) return

  try {
    // 1. 먼저 재고 조정 실행
    const result = await inventoryApi.adjust(selectedInventory.value.id, data)

    // 2. 파일이 있으면 가장 최근 거래 이력에 첨부
    if (files.length > 0) {
      // 최근 거래 이력 조회
      const transactions = await inventoryApi.getTransactions(selectedInventory.value.id, { limit: 1 })
      const latestTransaction = transactions.items[0]
      if (latestTransaction) {
        // 파일 업로드 (순차적으로)
        for (const file of files) {
          try {
            await inventoryApi.uploadTransactionDocument(latestTransaction.id, file)
          } catch (uploadErr) {
            console.error('파일 업로드 실패:', uploadErr)
            // 개별 파일 업로드 실패는 경고만 표시
            showToast(`파일 "${file.name}" 업로드 실패`, 'warning')
          }
        }
      }
    }

    showToast('재고가 조정되었습니다.', 'success')
    closeAdjustModal()
    loadInventory()
  } catch (err: any) {
    console.error('재고 조정 실패:', err)
    showToast(err.response?.data?.detail?.message || '재고 조정에 실패했습니다.', 'error')
  }
}

// 거래 이력 모달
const openHistoryModal = (item: InventoryListItem) => {
  selectedInventory.value = item
  showHistoryModal.value = true
}

const closeHistoryModal = () => {
  showHistoryModal.value = false
  selectedInventory.value = null
}

// 부품 상세 모달
const openPartDetailModal = (partId: number) => {
  selectedPartId.value = partId
  showPartDetailModal.value = true
}

const closePartDetailModal = () => {
  showPartDetailModal.value = false
  selectedPartId.value = null
}

// 설정 수정 모달
const openEditModal = (item: InventoryListItem) => {
  selectedInventory.value = item
  editFormData.reorder_point = item.reorder_point
  editFormData.reorder_qty = undefined
  editFormData.unit_cost = item.unit_cost
  editFormData.remarks = ''
  showEditModal.value = true
}

const closeEditModal = () => {
  showEditModal.value = false
  selectedInventory.value = null
}

const handleEditSubmit = async () => {
  if (!selectedInventory.value) return

  try {
    await inventoryApi.update(selectedInventory.value.id, {
      reorder_point: editFormData.reorder_point,
      reorder_qty: editFormData.reorder_qty,
      unit_cost: editFormData.unit_cost,
      remarks: editFormData.remarks || undefined
    })
    showToast('설정이 저장되었습니다.', 'success')
    closeEditModal()
    loadInventory()
  } catch (err: any) {
    console.error('설정 수정 실패:', err)
    showToast(err.response?.data?.detail?.message || '설정 수정에 실패했습니다.', 'error')
  }
}

// 유틸리티 함수
const getStatusLabel = (status: InventoryStatus) => {
  return inventoryStatusLabels[status] || status
}

const getStatusStyle = (status: InventoryStatus) => {
  return inventoryStatusStyles[status] || 'bg-gray-100 text-gray-800'
}

const formatNumber = (value: number | undefined | null) => {
  if (value === undefined || value === null) return '-'
  return new Intl.NumberFormat('ko-KR').format(value)
}

const formatCurrency = (value: number | undefined | null) => {
  if (value === undefined || value === null) return '-'
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(value)
}

const formatDate = (dateString: string | undefined | null) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const showToast = (message: string, type: 'success' | 'error' | 'warning' = 'success') => {
  toast.message = message
  toast.type = type
  toast.show = true
  setTimeout(() => {
    toast.show = false
  }, 3000)
}

// 초기 로드
onMounted(() => {
  loadCodeMasters()
  loadInventory()
})
</script>
