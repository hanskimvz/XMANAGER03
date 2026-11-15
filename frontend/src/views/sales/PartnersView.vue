<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl sm:text-3xl font-bold mb-6">거래처 관리</h1>

    <!-- 검색 및 필터 섹션 -->
    <div class="bg-white shadow rounded-lg p-4 sm:p-6 mb-6">
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">검색</label>
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="거래처 코드 또는 거래처명으로 검색"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            @keyup.enter="searchPartners"
            @input="debouncedSearch"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">거래처 유형</label>
          <select
            v-model="filters.partnerType"
            class="w-full px-3 py-2 border border-gray-300 rounded-md"
            @change="applyPartnerTypeFilter"
          >
            <option value="all">전체</option>
            <option value="supplier">공급업체</option>
            <option value="customer">고객사</option>
            <option value="both">공급업체+고객사</option>
          </select>
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
          @click="searchPartners"
          class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          검색
        </button>
      </div>
    </div>

    <!-- 테이블 섹션 -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-semibold">거래처 목록 <span class="text-sm text-gray-500 font-normal">(총 {{ totalPartners }}건)</span></h2>
        <div class="flex space-x-2">
          <button
            @click="exportExcel"
            class="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded flex items-center"
          >
            <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            엑셀 다운로드
          </button>
          <button
            @click="openExcelUploadModal"
            class="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded flex items-center"
          >
            <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            엑셀 업로드
          </button>
          <button
            @click="openAddModal"
            class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded flex items-center"
          >
            <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            거래처 추가
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

      <!-- 데이터 (모바일 카드 / 데스크톱 테이블) -->
      <div v-else class="overflow-x-auto">
        <!-- 모바일 카드 목록 (lg 미만 전용) -->
        <div class="lg:hidden divide-y divide-gray-100">
          <div v-for="partner in partners" :key="'m' + partner.id" class="py-3">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="text-sm font-medium text-gray-900 truncate">{{ partner.partner_name }}</div>
                <div class="text-xs text-blue-600">{{ partner.partner_code }}</div>
              </div>
              <span :class="['px-2 py-0.5 text-[11px] rounded-full whitespace-nowrap', partner.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600']">{{ partner.is_active ? '활성' : '비활성' }}</span>
            </div>
            <div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-500">
              <span v-if="partner.is_supplier" class="px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">공급</span>
              <span v-if="partner.is_customer" class="px-1.5 py-0.5 rounded bg-purple-100 text-purple-800">고객</span>
              <span v-if="partner.tel">☎ {{ partner.tel }}</span>
              <span v-if="partner.manager_name">담당 {{ partner.manager_name }}</span>
            </div>
            <div class="mt-2 flex gap-4 text-sm">
              <button @click="viewDetail(partner)" class="text-blue-600">상세</button>
              <button @click="openEditModal(partner)" class="text-blue-600">수정</button>
              <button @click="deletePartner(partner)" class="text-red-600">삭제</button>
            </div>
          </div>
        </div>

        <!-- 데스크톱 테이블 (lg 이상 전용 — 기존 UI 보존) -->
        <table class="min-w-full divide-y divide-gray-200 hidden lg:table">
          <thead class="bg-gray-50">
            <tr>
              <th
                @click="sortBy('partner_code')"
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
              >
                <div class="flex items-center space-x-1">
                  <span>코드</span>
                  <SortIcon :active="sortColumn === 'partner_code'" :desc="sortDesc" />
                </div>
              </th>
              <th
                @click="sortBy('partner_name')"
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
              >
                <div class="flex items-center space-x-1">
                  <span>거래처명</span>
                  <SortIcon :active="sortColumn === 'partner_name'" :desc="sortDesc" />
                </div>
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">유형</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">전화번호</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">담당자</th>
              <th
                @click="sortBy('is_active')"
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
              >
                <div class="flex items-center space-x-1">
                  <span>상태</span>
                  <SortIcon :active="sortColumn === 'is_active'" :desc="sortDesc" />
                </div>
              </th>
              <th
                @click="sortBy('created_at')"
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
              >
                <div class="flex items-center space-x-1">
                  <span>등록일</span>
                  <SortIcon :active="sortColumn === 'created_at'" :desc="sortDesc" />
                </div>
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">작업</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="partner in partners" :key="partner.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                {{ partner.partner_code }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ partner.partner_name }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex gap-1">
                  <span
                    v-if="partner.is_supplier"
                    class="px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-800"
                  >
                    공급
                  </span>
                  <span
                    v-if="partner.is_customer"
                    class="px-2 py-0.5 text-xs font-medium rounded bg-purple-100 text-purple-800"
                  >
                    고객
                  </span>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ partner.tel || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ partner.manager_name || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="[
                    'px-2 inline-flex text-xs leading-5 font-semibold rounded-full',
                    partner.is_active
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-800',
                  ]"
                >
                  {{ partner.is_active ? '활성' : '비활성' }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatDate(partner.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button @click="viewDetail(partner)" class="text-blue-600 hover:text-blue-900 mr-3">
                  상세
                </button>
                <button @click="openEditModal(partner)" class="text-blue-600 hover:text-blue-900 mr-3">
                  수정
                </button>
                <button @click="deletePartner(partner)" class="text-red-600 hover:text-red-900">
                  삭제
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="partners.length === 0" class="text-center py-8 text-gray-500">
          거래처 데이터가 없습니다
        </div>

        <!-- 페이지네이션 -->
        <Pagination
          v-if="totalCount > 0"
          :total="totalCount"
          :page-size="pageSize"
          :current-page="currentPage"
          @update:current-page="handlePageChange"
          @update:page-size="handlePageSizeChange"
        />
      </div>
    </div>

    <!-- 모달 -->
    <PartnerFormModal
      :show="showModal"
      :is-edit="isEditMode"
      :initial-data="selectedPartner"
      @close="closeModal"
      @submit="handleSubmit"
    />

    <!-- 상세 모달 -->
    <PartnerDetailModal
      :show="showDetailModal"
      :partner="detailPartner"
      @close="closeDetailModal"
      @edit="openEditFromDetail"
      @updated="handleDetailUpdated"
    />

    <!-- 토스트 알림 -->
    <div
      v-if="toast.show"
      class="fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg transition-all"
      :class="toast.type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'"
    >
      {{ toast.message }}
    </div>

    <!-- 엑셀 업로드 모달 -->
    <div v-if="showExcelUploadModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div class="flex justify-between items-center p-4 border-b">
          <h3 class="text-lg font-semibold">거래처 엑셀 업로드</h3>
          <button @click="closeExcelUploadModal" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="p-6">
          <div class="mb-4">
            <p class="text-sm text-gray-600 mb-2">엑셀 파일을 업로드하여 거래처를 일괄 등록/수정합니다.</p>
            <div class="bg-blue-50 p-3 rounded text-sm text-blue-700">
              <p class="font-medium mb-1">엑셀 양식 (9개 컬럼)</p>
              <p>기업코드 | 거래처 | 국가코드 | 국가명 | 대륙 | 응용분야 | 고객유형 | 거래시작년도 | 결제조건</p>
              <p class="mt-2 text-xs">
                - 기업코드가 이미 존재하면: 해당 거래처 정보 업데이트<br>
                - 기업코드가 없으면: 신규 거래처 등록 (고객사로 설정)
              </p>
            </div>
          </div>
          <div
            class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition-colors"
            @click="triggerFileInput"
            @dragover.prevent
            @drop.prevent="handleFileDrop"
          >
            <input
              ref="fileInput"
              type="file"
              accept=".xlsx,.xls"
              class="hidden"
              @change="handleFileSelect"
            />
            <svg class="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p v-if="!selectedFile" class="text-gray-600">
              클릭하거나 파일을 드래그하여 업로드<br>
              <span class="text-sm text-gray-400">(.xlsx, .xls 파일만 지원)</span>
            </p>
            <p v-else class="text-blue-600 font-medium">{{ selectedFile.name }}</p>
          </div>
        </div>
        <div class="flex justify-end space-x-2 p-4 border-t">
          <button
            @click="closeExcelUploadModal"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            취소
          </button>
          <button
            @click="uploadExcel"
            :disabled="!selectedFile || uploading"
            class="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {{ uploading ? '업로드 중...' : '업로드' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 엑셀 업로드 결과 모달 -->
    <div v-if="showUploadResultModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[80vh] flex flex-col">
        <div class="flex justify-between items-center p-4 border-b">
          <h3 class="text-lg font-semibold">업로드 결과</h3>
          <button @click="closeUploadResultModal" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="p-6 overflow-auto flex-1">
          <!-- 요약 -->
          <div v-if="uploadResult" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-gray-100 p-4 rounded text-center">
              <p class="text-2xl font-bold text-gray-700">{{ uploadResult.summary.total }}</p>
              <p class="text-sm text-gray-500">전체</p>
            </div>
            <div class="bg-green-100 p-4 rounded text-center">
              <p class="text-2xl font-bold text-green-700">{{ uploadResult.summary.success_count }}</p>
              <p class="text-sm text-green-600">신규 등록</p>
            </div>
            <div class="bg-blue-100 p-4 rounded text-center">
              <p class="text-2xl font-bold text-blue-700">{{ uploadResult.summary.updated_count }}</p>
              <p class="text-sm text-blue-600">정보 수정</p>
            </div>
            <div class="bg-red-100 p-4 rounded text-center">
              <p class="text-2xl font-bold text-red-700">{{ uploadResult.summary.failed_count }}</p>
              <p class="text-sm text-red-600">실패</p>
            </div>
          </div>

          <!-- 결과 테이블 -->
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">행</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">기업코드</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">메시지</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr v-for="item in uploadResult?.results || []" :key="item.row">
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">{{ item.row }}</td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{{ item.partner_code }}</td>
                  <td class="px-4 py-3 whitespace-nowrap">
                    <span
                      :class="[
                        'px-2 py-1 text-xs font-medium rounded',
                        item.status === 'success' ? 'bg-green-100 text-green-800' :
                        item.status === 'updated' ? 'bg-blue-100 text-blue-800' :
                        'bg-red-100 text-red-800'
                      ]"
                    >
                      {{ item.status === 'success' ? '신규등록' : item.status === 'updated' ? '정보수정' : '실패' }}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-sm text-gray-500">{{ item.message }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="flex justify-end p-4 border-t">
          <button
            @click="closeUploadResultModal"
            class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            확인
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import { ref, onMounted } from 'vue'
import {
  partnerApi,
  type BusinessPartnerListItem,
  type BusinessPartnerCreate,
  type BusinessPartnerSearchParams,
  type BusinessPartner,
  type ExcelUploadResponse,
} from '@/api/partner'
import { downloadAuthedUrl } from '@/utils/download'
import PartnerFormModal from '@/views/sales/PartnerFormModal.vue'
import PartnerDetailModal from '@/views/sales/PartnerDetailModal.vue'
import Pagination from '@/components/Pagination.vue'
import SortIcon from '@/components/SortIcon.vue'
import { handleApiError } from '@/utils/errorHandler'

// 상태
const loading = ref(false)
const error = ref('')
const partners = ref<BusinessPartnerListItem[]>([])
const totalCount = ref(0)

// 페이지네이션
const currentPage = ref(1)
const pageSize = ref(20)

// 정렬
const sortColumn = ref('created_at')
const sortDesc = ref(true)

// 검색 및 필터
const searchKeyword = ref('')
const filters = ref<BusinessPartnerSearchParams & { partnerType?: string }>({
  is_active: undefined,
  is_supplier: undefined,
  is_customer: undefined,
  partnerType: 'all',
})

// 모달 상태
const showModal = ref(false)
const isEditMode = ref(false)
const selectedPartner = ref<BusinessPartnerCreate | null>(null)

// 상세 모달 상태
const showDetailModal = ref(false)
const detailPartner = ref<BusinessPartner | null>(null)

// 엑셀 업로드 상태
const showExcelUploadModal = ref(false)
const showUploadResultModal = ref(false)
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const uploadResult = ref<ExcelUploadResponse | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

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

// 거래처 유형 필터 적용
const applyPartnerTypeFilter = () => {
  switch (filters.value.partnerType) {
    case 'supplier':
      filters.value.is_supplier = true
      filters.value.is_customer = undefined
      break
    case 'customer':
      filters.value.is_supplier = undefined
      filters.value.is_customer = true
      break
    case 'both':
      filters.value.is_supplier = true
      filters.value.is_customer = true
      break
    default:
      filters.value.is_supplier = undefined
      filters.value.is_customer = undefined
  }
}

// 거래처 목록 로드
const loadPartners = async () => {
  try {
    loading.value = true
    error.value = ''
    const params: BusinessPartnerSearchParams = {
      is_active: filters.value.is_active,
      is_supplier: filters.value.is_supplier,
      is_customer: filters.value.is_customer,
      keyword: searchKeyword.value || undefined,
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      order_by: sortColumn.value,
      order_desc: sortDesc.value,
    }
    const response = await partnerApi.getAll(params)
    partners.value = response.data.items
    totalCount.value = response.data.total
    totalPartners.value = response.data.total
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    error.value = errorMessage
    showToast(errorMessage, 'error')
  } finally {
    loading.value = false
  }
}

// 정렬
const sortBy = (column: string) => {
  if (sortColumn.value === column) {
    sortDesc.value = !sortDesc.value
  } else {
    sortColumn.value = column
    sortDesc.value = true
  }
  loadPartners()
}

// 페이지 변경
const handlePageChange = (page: number) => {
  currentPage.value = page
  loadPartners()
}

// 페이지 크기 변경
const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  loadPartners()
}

// 검색
const debouncedSearch = useDebouncedSearch(() => searchPartners())
const searchPartners = () => {
  currentPage.value = 1
  loadPartners()
}

// 총 건수 (템플릿용)
const totalPartners = ref(0)

// 엑셀 내보내기
const exportExcel = () => {
  const params: BusinessPartnerSearchParams = {
    is_active: filters.value.is_active,
    is_supplier: filters.value.is_supplier,
    is_customer: filters.value.is_customer,
    keyword: searchKeyword.value || undefined,
    order_by: sortColumn.value,
    order_desc: sortDesc.value,
  }
  const url = partnerApi.getExportExcelUrl(params)
  // v0.41.0: 인증 헤더를 실어 blob 다운로드(RBAC enforce 시 401 방지)
  downloadAuthedUrl(url, 'partners.xlsx').catch((e) => console.error('엑셀 내보내기 실패', e))
}

// 필터 초기화
const resetFilters = () => {
  searchKeyword.value = ''
  filters.value = {
    is_active: undefined,
    is_supplier: undefined,
    is_customer: undefined,
    partnerType: 'all',
  }
  currentPage.value = 1
  loadPartners()
}

// 모달 열기 (추가)
const openAddModal = () => {
  isEditMode.value = false
  selectedPartner.value = null
  showModal.value = true
}

// 모달 열기 (수정)
const openEditModal = async (partner: BusinessPartnerListItem) => {
  try {
    const response = await partnerApi.getById(partner.id)
    isEditMode.value = true
    selectedPartner.value = response.data as any
    showModal.value = true
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  }
}

// 상세 보기
const viewDetail = async (partner: BusinessPartnerListItem) => {
  try {
    const response = await partnerApi.getById(partner.id)
    detailPartner.value = response.data
    showDetailModal.value = true
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  }
}

// 상세 모달에서 수정 열기
const openEditFromDetail = () => {
  if (detailPartner.value) {
    isEditMode.value = true
    selectedPartner.value = detailPartner.value as any
    showDetailModal.value = false
    showModal.value = true
  }
}

// 상세 모달 닫기
const closeDetailModal = () => {
  showDetailModal.value = false
  detailPartner.value = null
}

// 상세 모달에서 파일 업로드/삭제 후 데이터 갱신
const handleDetailUpdated = async () => {
  if (detailPartner.value) {
    try {
      const response = await partnerApi.getById(detailPartner.value.id)
      detailPartner.value = response.data
    } catch (err: any) {
      console.error('데이터 갱신 실패:', err)
    }
  }
}

// 모달 닫기
const closeModal = () => {
  showModal.value = false
  selectedPartner.value = null
}

// 폼 제출 처리
const handleSubmit = async (data: BusinessPartnerCreate) => {
  // 클라이언트 측 유효성 검사
  if (!data.partner_code || data.partner_code.trim().length < 1) {
    showToast('거래처 코드는 필수입니다', 'error')
    return
  }

  if (!data.partner_name || data.partner_name.trim().length < 2) {
    showToast('거래처명은 2자 이상이어야 합니다', 'error')
    return
  }

  if (!data.is_supplier && !data.is_customer) {
    showToast('공급업체 또는 고객사 중 하나 이상을 선택해야 합니다', 'error')
    return
  }

  try {
    if (isEditMode.value && selectedPartner.value) {
      await partnerApi.update((selectedPartner.value as any).id, data)
      showToast('거래처가 수정되었습니다')
    } else {
      await partnerApi.create(data)
      showToast('거래처가 추가되었습니다')
    }
    closeModal()
    await loadPartners()
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  }
}

// 삭제
const deletePartner = async (partner: BusinessPartnerListItem) => {
  if (!confirm(`"${partner.partner_name}" (${partner.partner_code})를 삭제하시겠습니까?`)) {
    return
  }

  try {
    await partnerApi.delete(partner.id)
    showToast('거래처가 삭제되었습니다')
    await loadPartners()
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

// 엑셀 업로드 모달 열기
const openExcelUploadModal = () => {
  selectedFile.value = null
  showExcelUploadModal.value = true
}

// 엑셀 업로드 모달 닫기
const closeExcelUploadModal = () => {
  showExcelUploadModal.value = false
  selectedFile.value = null
}

// 파일 입력 트리거
const triggerFileInput = () => {
  fileInput.value?.click()
}

// 파일 선택 처리
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const file = target.files[0]
    if (file) selectedFile.value = file
  }
}

// 파일 드롭 처리
const handleFileDrop = (event: DragEvent) => {
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    const file = event.dataTransfer.files[0]
    if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
      selectedFile.value = file
    } else if (file) {
      showToast('엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.', 'error')
    }
  }
}

// 엑셀 업로드
const uploadExcel = async () => {
  if (!selectedFile.value) return

  uploading.value = true
  try {
    const response = await partnerApi.uploadExcel(selectedFile.value)
    uploadResult.value = response.data
    showExcelUploadModal.value = false
    showUploadResultModal.value = true

    // 목록 새로고침
    await loadPartners()
  } catch (err: any) {
    const errorMessage = handleApiError(err)
    showToast(errorMessage, 'error')
  } finally {
    uploading.value = false
  }
}

// 업로드 결과 모달 닫기
const closeUploadResultModal = () => {
  showUploadResultModal.value = false
  uploadResult.value = null
}

// 마운트 시 데이터 로드
onMounted(() => {
  loadPartners()
})
</script>
