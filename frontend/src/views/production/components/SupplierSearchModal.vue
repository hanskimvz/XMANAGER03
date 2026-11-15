<template>
  <div
    v-if="show"
    ref="modalOverlay"
    class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
    tabindex="-1"
    @keydown.escape="$emit('close')"
  >
    <div class="relative top-10 mx-auto p-5 border w-full max-w-3xl shadow-lg rounded-md bg-white" @click.stop>
      <!-- 헤더 -->
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold">{{ title }}</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 검색 필터 -->
      <div class="bg-gray-50 rounded-lg p-4 mb-4">
        <div class="flex gap-3">
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700 mb-1">검색</label>
            <input
              ref="searchInput"
              v-model="searchKeyword"
              type="text"
              placeholder="거래처 코드, 거래처명, 사업자번호로 검색..."
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              @keydown.enter="searchPartners"
            />
          </div>
          <div class="flex items-end">
            <button
              @click="searchPartners"
              class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
              검색
            </button>
          </div>
        </div>
      </div>

      <!-- 거래처 목록 테이블 -->
      <div class="border rounded-lg overflow-hidden">
        <div v-if="loading" class="text-center py-8 text-gray-500">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
          로딩 중...
        </div>
        <div v-else-if="partners.length === 0" class="text-center py-8 text-gray-500">
          검색 결과가 없습니다.
        </div>
        <div v-else class="max-h-96 overflow-y-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50 sticky top-0">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">코드</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">거래처명</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">사업자번호</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">담당자</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">연락처</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase w-20">선택</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr
                v-for="partner in partners"
                :key="partner.id"
                class="hover:bg-blue-50 cursor-pointer"
                @click="selectPartner(partner)"
              >
                <td class="px-3 py-2">
                  <span class="font-mono text-blue-600">{{ partner.partner_code }}</span>
                </td>
                <td class="px-3 py-2">
                  <div class="font-medium">{{ partner.partner_name }}</div>
                  <div v-if="partner.partner_name_en" class="text-xs text-gray-400">{{ partner.partner_name_en }}</div>
                </td>
                <td class="px-3 py-2 text-sm">{{ partner.business_number || '-' }}</td>
                <td class="px-3 py-2 text-sm">{{ partner.manager_name || '-' }}</td>
                <td class="px-3 py-2 text-sm">{{ partner.tel || '-' }}</td>
                <td class="px-3 py-2 text-center">
                  <button
                    @click.stop="selectPartner(partner)"
                    class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                  >
                    선택
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 페이지네이션 -->
      <div v-if="totalCount > 0" class="flex justify-between items-center mt-4 text-sm text-gray-500">
        <span>총 {{ totalCount }}건</span>
        <div class="flex gap-2 items-center">
          <button
            @click="currentPage > 1 && changePage(currentPage - 1)"
            :disabled="currentPage <= 1"
            class="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
          >
            이전
          </button>
          <span>{{ currentPage }} / {{ totalPages }}</span>
          <button
            @click="currentPage < totalPages && changePage(currentPage + 1)"
            :disabled="currentPage >= totalPages"
            class="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
          >
            다음
          </button>
        </div>
      </div>

      <!-- 하단 버튼 -->
      <div class="flex justify-end gap-2 mt-4 pt-4 border-t">
        <button
          @click="$emit('close')"
          class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          취소
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { partnerApi, type Partner } from '@/api/partner'

const props = defineProps<{
  show: boolean
  partnerType?: 'supplier' | 'customer' | 'all'  // 필터링 타입
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select', partner: Partner): void
}>()

// 검색
const searchInput = ref<HTMLInputElement | null>(null)
const searchKeyword = ref('')

// 거래처 목록
const partners = ref<Partner[]>([])
const loading = ref(false)
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(15)
const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

// 타이틀
const title = computed(() => {
  if (props.partnerType === 'supplier') return '공급업체 선택'
  if (props.partnerType === 'customer') return '고객사 선택'
  return '거래처 선택'
})

// 거래처 검색
const searchPartners = async () => {
  loading.value = true
  currentPage.value = 1
  try {
    const params: any = {
      keyword: searchKeyword.value || undefined,
      is_active: true,
      skip: 0,
      limit: pageSize.value,
    }

    // 타입별 필터
    if (props.partnerType === 'supplier') {
      params.is_supplier = true
    } else if (props.partnerType === 'customer') {
      params.is_customer = true
    }

    const response = await partnerApi.getAll(params)
    partners.value = response.data.items
    totalCount.value = response.data.total
  } catch (error) {
    console.error('거래처 검색 실패:', error)
    partners.value = []
    totalCount.value = 0
  } finally {
    loading.value = false
  }
}

// 페이지 변경
const changePage = async (page: number) => {
  loading.value = true
  currentPage.value = page
  try {
    const params: any = {
      keyword: searchKeyword.value || undefined,
      is_active: true,
      skip: (page - 1) * pageSize.value,
      limit: pageSize.value,
    }

    if (props.partnerType === 'supplier') {
      params.is_supplier = true
    } else if (props.partnerType === 'customer') {
      params.is_customer = true
    }

    const response = await partnerApi.getAll(params)
    partners.value = response.data.items
    totalCount.value = response.data.total
  } catch (error) {
    console.error('거래처 페이지 로드 실패:', error)
  } finally {
    loading.value = false
  }
}

// 거래처 선택
const selectPartner = (partner: Partner) => {
  emit('select', partner)
  emit('close')
}

// 모달 열릴 때 초기화
watch(() => props.show, async (newVal) => {
  if (newVal) {
    searchKeyword.value = ''
    currentPage.value = 1
    await searchPartners()

    nextTick(() => {
      searchInput.value?.focus()
    })
  }
})
</script>
