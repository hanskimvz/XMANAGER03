<template>
  <div
    v-if="show"
    ref="modalOverlay"
    class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
    tabindex="-1"
    @keydown.escape="closeModal"
  >
    <div class="relative top-20 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white" @click.stop>
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold">{{ isEdit ? '공급업체 수정' : '공급업체 등록' }}</h3>
        <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <form @submit.prevent="submitForm" class="space-y-4">
        <!-- 기본 정보 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">기본 정보</h4>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >공급업체 코드 <span class="text-red-500">*</span></label
              >
              <input
                v-model="formData.supplier_code"
                type="text"
                required
                :disabled="isEdit"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >공급업체명 <span class="text-red-500">*</span></label
              >
              <input
                v-model="formData.supplier_name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">영문 공급업체명</label>
              <input
                v-model="formData.supplier_name_en"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">사업자등록번호</label>
              <input
                v-model="formData.business_number"
                type="text"
                placeholder="123-45-67890"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        <!-- 사업자 정보 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">사업자 정보</h4>
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">대표자명</label>
              <input
                v-model="formData.representative"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">업태</label>
              <input
                v-model="formData.business_type"
                type="text"
                placeholder="제조업"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">종목</label>
              <input
                v-model="formData.business_item"
                type="text"
                placeholder="기계부품"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <div class="mt-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">주소</label>
            <input
              v-model="formData.address"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        <!-- 연락처 정보 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">연락처 정보</h4>
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">전화번호</label>
              <input
                v-model="formData.tel"
                type="tel"
                placeholder="02-1234-5678"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">팩스번호</label>
              <input
                v-model="formData.fax"
                type="tel"
                placeholder="02-1234-5679"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">이메일</label>
              <input
                v-model="formData.email"
                type="email"
                placeholder="company@example.com"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        <!-- 담당자 정보 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">담당자 정보</h4>
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">담당자명</label>
              <input
                v-model="formData.manager_name"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">담당자 전화</label>
              <input
                v-model="formData.manager_tel"
                type="tel"
                placeholder="010-1234-5678"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">담당자 이메일</label>
              <input
                v-model="formData.manager_email"
                type="email"
                placeholder="manager@example.com"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        <!-- 거래 조건 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">거래 조건</h4>
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">결제 조건</label>
              <input
                v-model="formData.payment_terms"
                type="text"
                placeholder="월말 익월 30일"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">납품 조건</label>
              <input
                v-model="formData.delivery_terms"
                type="text"
                placeholder="주문 후 7일"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">신용등급</label>
              <select
                v-model="formData.credit_rating"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">선택</option>
                <option value="AAA">AAA</option>
                <option value="AA">AA</option>
                <option value="A">A</option>
                <option value="BBB">BBB</option>
                <option value="BB">BB</option>
                <option value="B">B</option>
              </select>
            </div>
          </div>
        </div>

        <!-- 추가 정보 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">추가 정보</h4>
          <div class="grid grid-cols-2 gap-4">
            <div class="flex items-center">
              <input
                v-model="formData.is_active"
                type="checkbox"
                id="is_active"
                class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label for="is_active" class="ml-2 text-sm font-medium text-gray-700">활성 상태</label>
            </div>
          </div>
          <div class="mt-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">비고</label>
            <textarea
              v-model="formData.remark"
              rows="3"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        <!-- 버튼 -->
        <div class="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            @click="closeModal"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            취소
          </button>
          <button
            type="submit"
            class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            {{ isEdit ? '수정' : '등록' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { type SupplierCreate } from '@/api/supplier'

interface Props {
  show: boolean
  isEdit: boolean
  initialData?: Partial<SupplierCreate> | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  submit: [data: SupplierCreate]
}>()

// 폼 데이터
const formData = ref<SupplierCreate>({
  supplier_code: '',
  supplier_name: '',
  supplier_name_en: '',
  business_number: '',
  representative: '',
  business_type: '',
  business_item: '',
  address: '',
  tel: '',
  fax: '',
  email: '',
  manager_name: '',
  manager_tel: '',
  manager_email: '',
  payment_terms: '',
  delivery_terms: '',
  credit_rating: '',
  is_active: true,
  remark: '',
})

// 폼 리셋
const resetForm = () => {
  formData.value = {
    supplier_code: '',
    supplier_name: '',
    supplier_name_en: '',
    business_number: '',
    representative: '',
    business_type: '',
    business_item: '',
    address: '',
    tel: '',
    fax: '',
    email: '',
    manager_name: '',
    manager_tel: '',
    manager_email: '',
    payment_terms: '',
    delivery_terms: '',
    credit_rating: '',
    is_active: true,
    remark: '',
  }
}

// 모달 닫기
const closeModal = () => {
  emit('close')
}

// 폼 제출
const submitForm = () => {
  emit('submit', formData.value)
}

// props 변경 감지
watch(
  () => props.initialData,
  (newData) => {
    if (newData) {
      formData.value = { ...formData.value, ...newData }
    } else {
      resetForm()
    }
  },
  { immediate: true }
)
</script>
