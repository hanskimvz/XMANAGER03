<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">공급업체 관리</h1>

    <!-- 검색 및 필터 섹션 -->
    <div class="bg-white shadow rounded-lg p-6 mb-6">
      <div class="grid grid-cols-3 gap-4">
        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">검색</label>
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="공급업체 코드 또는 업체명으로 검색"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            @keyup.enter="searchSuppliers"
            @input="debouncedSearch"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">상태 필터</label>
          <select
            v-model="filters.is_active"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
          >
            <option :value="undefined">전체</option>
            <option :value="true">활성</option>
            <option :value="false">비활성</option>
          </select>
        </div>
      </div>
      <div class="flex justify-end mt-4 space-x-2">
        <button
          @click="resetFilters"
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          필터 초기화
        </button>
        <button
          @click="searchSuppliers"
          class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          검색
        </button>
      </div>
    </div>

    <!-- 테이블 섹션 -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-semibold">공급업체 목록</h2>
        <button
          @click="openAddModal"
          class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded flex items-center"
        >
          <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          공급업체 추가
        </button>
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
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">코드</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">업체명</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">영문명</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">전화번호</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">담당자</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">등록일</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">작업</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="supplier in suppliers" :key="supplier.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                {{ supplier.supplier_code }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ supplier.supplier_name }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ supplier.supplier_name_en || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ supplier.tel || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ supplier.manager_name || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="[
                    'px-2 inline-flex text-xs leading-5 font-semibold rounded-full',
                    supplier.is_active
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-800',
                  ]"
                >
                  {{ supplier.is_active ? '활성' : '비활성' }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatDate(supplier.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button @click="viewDetail(supplier)" class="text-blue-600 hover:text-blue-900 mr-3">
                  상세
                </button>
                <button @click="openEditModal(supplier)" class="text-blue-600 hover:text-blue-900 mr-3">
                  수정
                </button>
                <button @click="deleteSupplier(supplier)" class="text-red-600 hover:text-red-900">
                  삭제
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="suppliers.length === 0" class="text-center py-8 text-gray-500">
          공급업체 데이터가 없습니다
        </div>
      </div>
    </div>

    <!-- 모달 -->
    <SupplierFormModal
      :show="showModal"
      :is-edit="isEditMode"
      :initial-data="selectedSupplier"
      @close="closeModal"
      @submit="handleSubmit"
    />

    <!-- 토스트 알림 -->
    <div
      v-if="toast.show"
      class="fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg transition-all"
      :class="toast.type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'"
    >
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import { ref, onMounted } from 'vue'
import {
  supplierApi,
  type SupplierListItem,
  type SupplierCreate,
  type SupplierSearchParams,
} from '@/api/supplier'
import SupplierFormModal from '@/views/production/components/SupplierFormModal.vue'
import { handleApiError } from '@/utils/errorHandler'

// 상태
const loading = ref(false)
const error = ref('')
const suppliers = ref<SupplierListItem[]>([])

// 검색 및 필터
const searchKeyword = ref('')
const filters = ref<SupplierSearchParams>({
  is_active: undefined,
})

// 모달 상태
const showModal = ref(false)
const isEditMode = ref(false)
const selectedSupplier = ref<SupplierCreate | null>(null)

// 토스트 알림
const toast = ref({
  show: false,
  message: '',
  type: 'success' as 'success' | 'error',
})

const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  toast.value = { show: true, message, type }
  setTimeout(() => {
    toast.value.show = false
  }, 3000)
}

// 공급업체 목록 로드
const loadSuppliers = async () => {
  try {
    loading.value = true
    error.value = ''
    const params: SupplierSearchParams = {
      ...filters.value,
      keyword: searchKeyword.value || undefined,
    }
    const response = await supplierApi.getAll(params)
    suppliers.value = response.data
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    error.value = errorMessage
    showToast(errorMessage, 'error')
  } finally {
    loading.value = false
  }
}

// 검색
const debouncedSearch = useDebouncedSearch(() => searchSuppliers())
const searchSuppliers = () => {
  loadSuppliers()
}

// 필터 초기화
const resetFilters = () => {
  searchKeyword.value = ''
  filters.value = {
    is_active: undefined,
  }
  loadSuppliers()
}

// 모달 열기 (추가)
const openAddModal = () => {
  isEditMode.value = false
  selectedSupplier.value = null
  showModal.value = true
}

// 모달 열기 (수정)
const openEditModal = async (supplier: SupplierListItem) => {
  try {
    const response = await supplierApi.getById(supplier.id)
    isEditMode.value = true
    selectedSupplier.value = response.data as any
    showModal.value = true
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  }
}

// 상세 보기 (미구현)
const viewDetail = (supplier: SupplierListItem) => {
  alert(`상세 보기 기능은 추후 구현됩니다.\n업체명: ${supplier.supplier_name}`)
}

// 모달 닫기
const closeModal = () => {
  showModal.value = false
  selectedSupplier.value = null
}

// 폼 제출 처리
const handleSubmit = async (data: SupplierCreate) => {
  // 클라이언트 측 유효성 검사
  if (!data.supplier_code || data.supplier_code.trim().length < 1) {
    showToast('공급업체 코드는 필수입니다', 'error')
    return
  }

  if (!data.supplier_name || data.supplier_name.trim().length < 2) {
    showToast('공급업체명은 2자 이상이어야 합니다', 'error')
    return
  }

  try {
    if (isEditMode.value && selectedSupplier.value) {
      await supplierApi.update((selectedSupplier.value as any).id, data)
      showToast('공급업체가 수정되었습니다')
    } else {
      await supplierApi.create(data)
      showToast('공급업체가 추가되었습니다')
    }
    closeModal()
    await loadSuppliers()
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  }
}

// 삭제
const deleteSupplier = async (supplier: SupplierListItem) => {
  if (!confirm(`"${supplier.supplier_name}" (${supplier.supplier_code})를 삭제하시겠습니까?`)) {
    return
  }

  try {
    await supplierApi.delete(supplier.id)
    showToast('공급업체가 삭제되었습니다')
    await loadSuppliers()
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  }
}

// 날짜 포맷
const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

// 마운트 시 데이터 로드
onMounted(() => {
  loadSuppliers()
})
</script>
