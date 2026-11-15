<template>
  <div
    v-if="show"
    ref="modalOverlay"
    class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
    tabindex="-1"
    @keydown.escape="closeModal"
  >
    <div class="relative top-10 mx-auto p-5 border w-full max-w-5xl shadow-lg rounded-md bg-white mb-10" @click.stop>
      <!-- 헤더 -->
      <div class="flex justify-between items-center mb-4 border-b pb-4">
        <div>
          <h3 class="text-xl font-bold text-gray-800">부품 상세 정보</h3>
          <p class="text-sm text-gray-500 mt-1">{{ part?.part_number_display || part?.part_number }}</p>
        </div>
        <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 로딩 상태 -->
      <div v-if="isLoading" class="text-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
        <p class="text-gray-500 mt-4">로딩 중...</p>
      </div>

      <div v-else-if="part" class="space-y-6">
        <!-- 탭 네비게이션 -->
        <div class="border-b">
          <nav class="flex space-x-4">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              type="button"
              class="py-2 px-4 border-b-2 font-medium text-sm transition-colors"
              :class="{
                'border-blue-500 text-blue-600': activeTab === tab.id,
                'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300': activeTab !== tab.id,
              }"
              @click="activeTab = tab.id"
            >
              {{ tab.label }}
            </button>
          </nav>
        </div>

        <!-- 탭 내용 -->
        <div class="min-h-[400px]">
          <!-- 기본 정보 탭 -->
          <div v-show="activeTab === 'info'" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- 기본 정보 -->
              <div class="space-y-3">
                <h4 class="font-semibold text-gray-700 border-b pb-2">기본 정보</h4>
                <div class="grid grid-cols-2 gap-2 text-sm">
                  <!-- Part UID (v0.12.0) -->
                  <span class="text-gray-500">고유ID:</span>
                  <span v-if="part.part_uid" class="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded inline-block" title="바코드/QR용 고유 ID (변경불가)">{{ part.part_uid }}</span>
                  <span v-else class="text-gray-400">-</span>
                  <span class="text-gray-500">품번:</span>
                  <span class="font-medium">{{ part.part_number_display || part.part_number }}</span>
                  <span class="text-gray-500">부품명:</span>
                  <span class="font-medium">{{ part.part_name }}</span>
                  <span class="text-gray-500">영문명:</span>
                  <span>{{ part.part_name_en || '-' }}</span>
                  <span class="text-gray-500">규격:</span>
                  <span>{{ part.specification || '-' }}</span>
                  <span class="text-gray-500">버전:</span>
                  <span>{{ part.version }}</span>
                  <span class="text-gray-500">상태:</span>
                  <div class="flex items-center gap-2">
                    <span
                      class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                      :class="{
                        'bg-green-100 text-green-800': part.status === 'ACTIVE',
                        'bg-gray-100 text-gray-800': part.status === 'INACTIVE',
                        'bg-red-100 text-red-800': part.status === 'OBSOLETE',
                      }"
                    >
                      {{ statusLabel }}
                    </span>
                    <div class="relative" ref="statusDropdownRef">
                      <button
                        type="button"
                        @click="toggleStatusDropdown"
                        class="text-xs text-blue-600 hover:text-blue-800 underline"
                        :disabled="isChangingStatus"
                      >
                        {{ isChangingStatus ? '변경중...' : '변경' }}
                      </button>
                      <!-- 상태 변경 드롭다운 -->
                      <div
                        v-if="showStatusDropdown"
                        class="absolute left-0 top-6 z-10 bg-white border border-gray-200 rounded-md shadow-lg py-1 min-w-[120px]"
                      >
                        <button
                          v-for="status in statusOptions"
                          :key="status.value"
                          type="button"
                          @click="changeStatus(status.value)"
                          class="w-full text-left px-3 py-1.5 text-sm hover:bg-gray-100 flex items-center gap-2"
                          :class="{ 'bg-gray-50 font-medium': part.status === status.value }"
                        >
                          <span
                            class="w-2 h-2 rounded-full"
                            :class="{
                              'bg-green-500': status.value === 'ACTIVE',
                              'bg-yellow-500': status.value === 'INACTIVE',
                              'bg-red-500': status.value === 'OBSOLETE',
                            }"
                          ></span>
                          {{ status.label }}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 품번 구성 정보 -->
              <div class="space-y-3">
                <h4 class="font-semibold text-gray-700 border-b pb-2">품번 구성 (v1.1)</h4>
                <div class="grid grid-cols-2 gap-2 text-sm">
                  <span class="text-gray-500">대분류 (4자리):</span>
                  <span>{{ part.product_line ? `${part.product_line.code} - ${part.product_line.name_ko}` : '-' }}</span>
                  <span class="text-gray-500">소분류 (3자리):</span>
                  <span>{{ part.part_group ? `${part.part_group.code} - ${part.part_group.name_ko}` : '-' }}</span>
                  <span class="text-gray-500">품목코드 (5자리):</span>
                  <span class="font-mono">{{ part.item_code || '-' }}</span>
                  <span class="text-gray-500">재질 (2자리):</span>
                  <span>{{ part.material ? `${part.material.code} - ${part.material.name_ko}` : '-' }}</span>
                  <span class="text-gray-500">후처리 (2자리):</span>
                  <span>{{ part.treatment ? `${part.treatment.code} - ${part.treatment.name_ko}` : '-' }}</span>
                </div>

                <h4 class="font-semibold text-gray-700 border-b pb-2 mt-4">분류 속성 (품번 미포함)</h4>
                <div class="grid grid-cols-2 gap-2 text-sm">
                  <span class="text-gray-500">분류1-개발구분:</span>
                  <span>{{ part.development_type ? `${part.development_type.code} - ${part.development_type.name_ko}` : '-' }}</span>
                  <span class="text-gray-500">분류2-부품유형:</span>
                  <span>{{ part.part_types?.map(t => `${t.code}(${t.name_ko})`).join(', ') || '-' }}</span>
                  <span class="text-gray-500">분류3-도면여부:</span>
                  <span>{{ part.drawing_type ? `${part.drawing_type.code} - ${part.drawing_type.name_ko}` : '-' }}</span>
                  <span class="text-gray-500">레벨:</span>
                  <span>{{ part.level ? `${part.level.code} - ${part.level.name_ko}` : '-' }}</span>
                </div>
              </div>
            </div>

            <!-- 설명 -->
            <div v-if="part.description" class="space-y-2">
              <h4 class="font-semibold text-gray-700 border-b pb-2">설명</h4>
              <p class="text-sm text-gray-600 whitespace-pre-wrap">{{ part.description }}</p>
            </div>

            <!-- 비고 -->
            <div v-if="part.remark" class="space-y-2">
              <h4 class="font-semibold text-gray-700 border-b pb-2">비고</h4>
              <p class="text-sm text-gray-600 whitespace-pre-wrap">{{ part.remark }}</p>
            </div>
          </div>

          <!-- 원가 정보 탭 -->
          <div v-show="activeTab === 'price'" class="space-y-4">
            <PartPriceInfoCard v-if="part" :part-id="part.id" @updated="loadPart" />
          </div>

          <!-- 재고 정보 탭 -->
          <div v-show="activeTab === 'inventory'" class="space-y-4">
            <!-- 로딩 상태 -->
            <div v-if="isLoadingInventory" class="text-center py-8">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p class="text-gray-500 mt-2">재고 정보 로딩 중...</p>
            </div>

            <!-- 재고 정보가 없을 때 -->
            <div v-else-if="!inventory" class="text-center py-12 text-gray-400">
              <svg class="mx-auto h-12 w-12 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
              <p>등록된 재고 정보가 없습니다.</p>
              <p class="text-sm mt-1">재고 관리 페이지에서 재고를 등록해주세요.</p>
            </div>

            <!-- 재고 정보 표시 -->
            <div v-else class="space-y-6">
              <!-- 현재 재고 현황 -->
              <div class="bg-gray-50 rounded-lg p-4">
                <h4 class="font-semibold text-gray-700 mb-3">현재 재고 현황</h4>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div class="bg-white p-3 rounded border">
                    <p class="text-xs text-gray-500 mb-1">현재고</p>
                    <p class="text-xl font-bold text-blue-600">{{ formatNumber(inventory.quantity_on_hand) }}</p>
                  </div>
                  <div class="bg-white p-3 rounded border">
                    <p class="text-xs text-gray-500 mb-1">예약수량</p>
                    <p class="text-xl font-bold text-orange-500">{{ formatNumber(inventory.quantity_reserved || 0) }}</p>
                  </div>
                  <div class="bg-white p-3 rounded border">
                    <p class="text-xs text-gray-500 mb-1">가용수량</p>
                    <p class="text-xl font-bold text-green-600">{{ formatNumber(inventory.quantity_available || inventory.quantity_on_hand) }}</p>
                  </div>
                  <div class="bg-white p-3 rounded border">
                    <p class="text-xs text-gray-500 mb-1">상태</p>
                    <span
                      class="px-2 py-1 text-sm rounded-full"
                      :class="inventoryStatusStyles[inventory.status]"
                    >
                      {{ inventoryStatusLabels[inventory.status] }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- 재고 설정 수정 -->
              <div class="border rounded-lg p-4">
                <div class="flex justify-between items-center mb-4">
                  <h4 class="font-semibold text-gray-700">재고 설정</h4>
                  <button
                    v-if="!isEditingInventory"
                    @click="startEditInventory"
                    class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                  >
                    수정
                  </button>
                  <div v-else class="flex gap-2">
                    <button
                      @click="cancelEditInventory"
                      class="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                      :disabled="isSavingInventory"
                    >
                      취소
                    </button>
                    <button
                      @click="saveInventory"
                      class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                      :disabled="isSavingInventory"
                    >
                      {{ isSavingInventory ? '저장 중...' : '저장' }}
                    </button>
                  </div>
                </div>

                <!-- 보기 모드 -->
                <div v-if="!isEditingInventory" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <p class="text-sm text-gray-500">재주문점</p>
                    <p class="font-medium">{{ inventory.reorder_point != null ? formatNumber(inventory.reorder_point) : '-' }}</p>
                  </div>
                  <div>
                    <p class="text-sm text-gray-500">재주문량</p>
                    <p class="font-medium">{{ inventory.reorder_qty != null ? formatNumber(inventory.reorder_qty) : '-' }}</p>
                  </div>
                  <div>
                    <p class="text-sm text-gray-500">단가</p>
                    <p class="font-medium">{{ inventory.unit_cost != null ? formatCurrency(inventory.unit_cost) : '-' }}</p>
                  </div>
                  <div>
                    <p class="text-sm text-gray-500">최종 실사일</p>
                    <p class="font-medium">{{ inventory.last_count_date ? formatDate(inventory.last_count_date) : '-' }}</p>
                  </div>
                  <div class="col-span-2">
                    <p class="text-sm text-gray-500">비고</p>
                    <p class="font-medium">{{ inventory.remarks || '-' }}</p>
                  </div>
                </div>

                <!-- 수정 모드 -->
                <div v-else class="space-y-4">
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">재주문점</label>
                      <input
                        v-model.number="inventoryFormData.reorder_point"
                        type="number"
                        min="0"
                        step="0.001"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        placeholder="재주문 기준 수량"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">재주문량</label>
                      <input
                        v-model.number="inventoryFormData.reorder_qty"
                        type="number"
                        min="0"
                        step="0.001"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        placeholder="재주문 시 수량"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">단가 (원)</label>
                      <input
                        v-model.number="inventoryFormData.unit_cost"
                        type="number"
                        min="0"
                        step="0.01"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        placeholder="단가"
                      />
                    </div>
                    <div></div>
                    <div class="col-span-2">
                      <label class="block text-sm font-medium text-gray-700 mb-1">비고</label>
                      <textarea
                        v-model="inventoryFormData.remarks"
                        rows="2"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        placeholder="비고"
                      ></textarea>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 최종 수정일 -->
              <div class="text-right text-xs text-gray-400">
                최종 수정: {{ inventory.updated_at ? formatDateTime(inventory.updated_at) : '-' }}
              </div>
            </div>
          </div>

          <!-- 첨부파일 탭 -->
          <div v-show="activeTab === 'files'" class="space-y-6">
            <!-- 파일 업로드 섹션 -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <!-- 도면 업로드 -->
              <div class="border rounded-lg p-4">
                <h4 class="font-medium text-gray-700 mb-3">도면 업로드</h4>
                <FileUpload
                  :part-id="part.id"
                  file-type="drawing"
                  @uploaded="handleFileUploaded"
                  @error="handleUploadError"
                />
              </div>

              <!-- 사진 업로드 -->
              <div class="border rounded-lg p-4">
                <h4 class="font-medium text-gray-700 mb-3">사진 업로드</h4>
                <FileUpload
                  :part-id="part.id"
                  file-type="photo"
                  @uploaded="handleFileUploaded"
                  @error="handleUploadError"
                />
              </div>

              <!-- 문서 업로드 -->
              <div class="border rounded-lg p-4">
                <h4 class="font-medium text-gray-700 mb-3">문서 업로드</h4>
                <FileUpload
                  :part-id="part.id"
                  file-type="document"
                  @uploaded="handleFileUploaded"
                  @error="handleUploadError"
                />
              </div>
            </div>

            <!-- 첨부된 파일 목록 -->
            <div>
              <h4 class="font-semibold text-gray-700 mb-4">첨부된 파일</h4>
              <FileList
                ref="fileListRef"
                :part-id="part.id"
                @deleted="handleFileDeleted"
              />
            </div>
          </div>

          <!-- 이력 탭 (향후 구현) -->
          <div v-show="activeTab === 'history'" class="text-center py-12 text-gray-400">
            <svg class="mx-auto h-12 w-12 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>이력 관리 기능은 향후 구현 예정입니다</p>
          </div>
        </div>

        <!-- 하단 버튼 -->
        <div class="flex justify-end space-x-3 pt-4 border-t">
          <button
            type="button"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            @click="closeModal"
          >
            닫기
          </button>
          <button
            type="button"
            class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            @click="$emit('edit', part)"
          >
            수정
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed, onMounted, onUnmounted } from 'vue'
import { partApi, type Part } from '@/api/parts'
import {
  inventoryApi,
  inventoryStatusLabels,
  inventoryStatusStyles,
  type Inventory,
  type InventoryUpdate
} from '@/api/inventory'
import FileUpload from '@/components/FileUpload.vue'
import FileList from '@/components/FileList.vue'
import PartPriceInfoCard from './PartPriceInfoCard.vue'

interface Props {
  show: boolean
  partId: number | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  edit: [part: Part]
  updated: []  // 상태 변경 후 목록 갱신용
}>()

const isLoading = ref(false)
const part = ref<Part | null>(null)
const activeTab = ref('info')
const fileListRef = ref<InstanceType<typeof FileList> | null>(null)

// 재고 관련 상태
const inventory = ref<Inventory | null>(null)
const isLoadingInventory = ref(false)
const isEditingInventory = ref(false)
const isSavingInventory = ref(false)
const inventoryFormData = reactive<InventoryUpdate>({
  reorder_point: undefined,
  reorder_qty: undefined,
  unit_cost: undefined,
  remarks: ''
})

// 상태 변경 관련
const showStatusDropdown = ref(false)
const isChangingStatus = ref(false)
const statusDropdownRef = ref<HTMLElement | null>(null)

const statusOptions = [
  { value: 'ACTIVE', label: '사용중' },
  { value: 'INACTIVE', label: '미사용' },
  { value: 'OBSOLETE', label: '단종' },
]

const statusLabel = computed(() => {
  const status = statusOptions.find(s => s.value === part.value?.status)
  return status?.label || part.value?.status || '-'
})

// 상태 드롭다운 토글
const toggleStatusDropdown = () => {
  showStatusDropdown.value = !showStatusDropdown.value
}

// 상태 변경
const changeStatus = async (newStatus: string) => {
  if (!part.value || part.value.status === newStatus) {
    showStatusDropdown.value = false
    return
  }

  isChangingStatus.value = true
  try {
    await partApi.updateStatus(part.value.id, newStatus)
    part.value.status = newStatus
    showStatusDropdown.value = false
    emit('updated')  // 목록 갱신 이벤트
  } catch (error) {
    console.error('상태 변경 실패:', error)
    alert('상태 변경에 실패했습니다.')
  } finally {
    isChangingStatus.value = false
  }
}

// 외부 클릭 시 드롭다운 닫기
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (statusDropdownRef.value && !statusDropdownRef.value.contains(target)) {
    showStatusDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

const tabs = [
  { id: 'info', label: '기본 정보' },
  { id: 'price', label: '원가 정보' },
  { id: 'inventory', label: '재고 정보' },
  { id: 'files', label: '첨부파일' },
  { id: 'history', label: '변경 이력' },
]

// 부품 정보 로드
const loadPart = async () => {
  if (!props.partId) return

  isLoading.value = true
  try {
    const response = await partApi.getById(props.partId)
    part.value = response.data
  } catch (error) {
    console.error('부품 정보 로드 실패:', error)
  } finally {
    isLoading.value = false
  }
}

// 재고 정보 로드
const loadInventory = async () => {
  if (!props.partId) return

  isLoadingInventory.value = true
  try {
    const response = await inventoryApi.getByPartId(props.partId)
    inventory.value = response
  } catch (error: any) {
    // 404는 재고 정보가 없는 경우 (정상)
    if (error.response?.status === 404) {
      inventory.value = null
    } else {
      console.error('재고 정보 로드 실패:', error)
    }
  } finally {
    isLoadingInventory.value = false
  }
}

// 재고 수정 시작
const startEditInventory = () => {
  if (!inventory.value) return
  inventoryFormData.reorder_point = inventory.value.reorder_point
  inventoryFormData.reorder_qty = inventory.value.reorder_qty
  inventoryFormData.unit_cost = inventory.value.unit_cost
  inventoryFormData.remarks = inventory.value.remarks || ''
  isEditingInventory.value = true
}

// 재고 수정 취소
const cancelEditInventory = () => {
  isEditingInventory.value = false
}

// 재고 저장
const saveInventory = async () => {
  if (!inventory.value) return

  isSavingInventory.value = true
  try {
    // 빈 정수 정규화 — Pydantic이 빈 문자열을 정수로 거부함
    const _norm = (v: any) =>
      (v === '' || v === undefined || v === null || (typeof v === 'number' && Number.isNaN(v))) ? null : v
    const updatedInventory = await inventoryApi.update(inventory.value.id, {
      reorder_point: _norm(inventoryFormData.reorder_point),
      reorder_qty: _norm(inventoryFormData.reorder_qty),
      unit_cost: _norm(inventoryFormData.unit_cost),
      remarks: inventoryFormData.remarks || undefined
    })
    inventory.value = updatedInventory
    isEditingInventory.value = false
    emit('updated')
  } catch (error) {
    console.error('재고 설정 수정 실패:', error)
    alert('재고 설정 수정에 실패했습니다.')
  } finally {
    isSavingInventory.value = false
  }
}

// 숫자 포맷
const formatNumber = (value: number | undefined | null) => {
  if (value === undefined || value === null) return '0'
  return new Intl.NumberFormat('ko-KR').format(value)
}

// 통화 포맷 (소수점 2자리까지)
const formatCurrency = (value: number | undefined | null) => {
  if (value === undefined || value === null) return '-'
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(value)
}

// 날짜 포맷
const formatDate = (dateString: string | undefined | null) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('ko-KR')
}

// 날짜시간 포맷
const formatDateTime = (dateString: string | undefined | null) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('ko-KR')
}

// 파일 업로드 완료
const handleFileUploaded = () => {
  fileListRef.value?.refresh()
}

// 업로드 에러
const handleUploadError = (error: string) => {
  alert(error)
}

// 파일 삭제 완료
const handleFileDeleted = () => {
  // 필요시 추가 처리
}

// 모달 닫기
const closeModal = () => {
  emit('close')
  activeTab.value = 'info'
}

// props 변경 감지
watch(
  () => props.partId,
  (newId) => {
    if (newId) {
      loadPart()
      // 재고 정보 초기화
      inventory.value = null
      isEditingInventory.value = false
    } else {
      part.value = null
      inventory.value = null
    }
  },
  { immediate: true }
)

// 탭 변경 감지 - 재고 탭 선택 시 로드
watch(
  () => activeTab.value,
  (newTab) => {
    if (newTab === 'inventory' && props.partId && !inventory.value && !isLoadingInventory.value) {
      loadInventory()
    }
  }
)
</script>
