<template>
  <div
    v-if="show"
    ref="modalOverlay"
    class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
    tabindex="-1"
    @keydown.escape="closeModal"
  >
    <div class="relative top-10 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white mb-10" @click.stop>
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold">{{ isEdit ? '거래처 수정' : '거래처 등록' }}</h3>
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
        <!-- 1. 거래 구분 (최상단) -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">거래 구분</h4>
          <!-- 거래 유형 (국내/해외) -->
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              거래 유형 <span class="text-red-500">*</span>
            </label>
            <div class="flex space-x-4">
              <label :class="[
                'flex-1 flex items-center justify-center gap-2 px-4 py-3 border-2 rounded-lg cursor-pointer transition-colors',
                formData.trade_type === 'EXPORT'
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 hover:border-gray-300'
              ]">
                <input v-model="formData.trade_type" type="radio" value="EXPORT" class="hidden" @change="onTradeTypeChange" />
                <span class="text-lg">🌍</span>
                <span class="font-medium">해외 (수출)</span>
              </label>
              <label :class="[
                'flex-1 flex items-center justify-center gap-2 px-4 py-3 border-2 rounded-lg cursor-pointer transition-colors',
                formData.trade_type === 'DOMESTIC'
                  ? 'border-green-500 bg-green-50 text-green-700'
                  : 'border-gray-200 hover:border-gray-300'
              ]">
                <input v-model="formData.trade_type" type="radio" value="DOMESTIC" class="hidden" @change="onTradeTypeChange" />
                <span class="text-lg">🇰🇷</span>
                <span class="font-medium">국내</span>
              </label>
            </div>
          </div>
          <!-- 거래처 유형 (고객사/공급업체) -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              거래처 유형 <span class="text-red-500">*</span>
            </label>
            <div class="flex space-x-6">
              <label class="inline-flex items-center">
                <input v-model="formData.is_customer" type="checkbox" @change="onPartnerTypeChange"
                  class="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500" />
                <span class="ml-2 text-sm text-gray-700">고객사</span>
              </label>
              <label class="inline-flex items-center">
                <input v-model="formData.is_supplier" type="checkbox" @change="onPartnerTypeChange"
                  class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" />
                <span class="ml-2 text-sm text-gray-700">공급업체</span>
              </label>
            </div>
            <p class="mt-1 text-xs text-gray-500">최소 하나 이상 선택해야 합니다</p>
          </div>
        </div>

        <!-- 2. 기본 정보 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">기본 정보</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <!-- 거래처 코드: 국내=자동, 해외=수동 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                거래처 코드 <span class="text-red-500">*</span>
              </label>
              <div v-if="isDomestic">
                <input
                  v-model="formData.partner_code"
                  type="text"
                  disabled
                  class="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-600"
                />
                <p class="text-xs text-green-600 mt-1">🇰🇷 국내 업체: 자동 채번 ({{ formData.is_customer ? 'CUS' : 'SUP' }}+순번)</p>
              </div>
              <div v-else>
                <input
                  v-model="formData.partner_code"
                  @blur="checkDuplicateCode"
                  type="text"
                  required
                  maxlength="10"
                  placeholder="예: OP, HEX"
                  :class="[
                    'w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                    duplicateError ? 'border-red-500 bg-red-50' : 'border-gray-300'
                  ]"
                />
                <p v-if="duplicateError" class="text-xs text-red-500 mt-1 font-medium">⚠ {{ duplicateError }}</p>
                <p v-else class="text-xs text-gray-400 mt-1">🌍 해외 업체: 영문 약어 수동 입력 — 문서번호 채번에 사용</p>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                거래처명 <span class="text-red-500">*</span>
              </label>
              <input
                v-model="formData.partner_name"
                type="text"
                required
                :placeholder="isDomestic ? '예: 153오디오랩 주식회사' : '예: Hexa Fos'"
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
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">거래시작년도</label>
              <input
                v-model.number="formData.business_start_year"
                type="number"
                min="1900"
                max="2100"
                placeholder="2025"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        <!-- 국가 및 주소 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">국가 및 주소</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">대표자명</label>
              <input
                v-model="formData.representative"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">국가명 <span class="text-xs text-gray-400">(한글)</span></label>
              <template v-if="!countryManual">
                <SearchableSelect
                  v-model="countryId"
                  :options="countryOptions"
                  :preserve-order="true"
                  placeholder="국가명·코드·영문명 검색"
                />
                <p class="text-[11px] text-gray-400 mt-1">
                  폴더 규칙이 한글 국가명 기준이라 목록에서 선택합니다(국가코드 자동).
                  <button type="button" class="text-blue-600 hover:underline" @click="startCountryManual">목록에 없나요? 직접 입력</button>
                </p>
              </template>
              <template v-else>
                <input
                  v-model="formData.country_name"
                  type="text"
                  maxlength="100"
                  placeholder="한글 국가명 (예: 몬테네그로)"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  @input="countryError = ''"
                />
                <p v-if="countryError" class="text-[11px] text-red-600 mt-1">{{ countryError }}</p>
                <p class="text-[11px] text-gray-400 mt-1">
                  폴더명에 쓰이므로 한글로 입력하세요. 국가코드는 알면 입력(선택).
                  <button type="button" class="text-blue-600 hover:underline" @click="stopCountryManual">목록에서 선택</button>
                </p>
              </template>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">국가코드 <span class="text-xs text-gray-400">{{ countryManual ? '(직접 입력)' : '(자동)' }}</span></label>
              <input
                v-model="formData.country_code"
                type="text"
                placeholder="KR"
                maxlength="3"
                :class="['w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500', countryManual ? 'bg-white' : 'bg-gray-50']"
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
          <h4 class="font-semibold mb-3">회사 연락처</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
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
              <label class="block text-sm font-medium text-gray-700 mb-1">이메일</label>
              <input
                v-model="formData.email"
                type="email"
                placeholder="company@example.com"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">웹사이트</label>
              <input
                v-model="formData.website"
                type="text"
                placeholder="www.example.com"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        <!-- 담당자 안내 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-2 text-gray-700">담당자 정보</h4>
          <p class="text-sm text-gray-500 bg-gray-50 rounded-lg p-3">
            담당자는 <strong>거래처 등록 후 상세보기</strong>에서 추가할 수 있습니다.
            여러 명의 담당자를 등록하고 역할(구매/기술/영업)을 지정할 수 있습니다.
          </p>
        </div>

        <!-- 거래 조건 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">거래 조건</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">결제 조건</label>
              <input
                v-model="formData.payment_terms"
                type="text"
                placeholder="30 days net"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">납품 조건</label>
              <input
                v-model="formData.delivery_terms"
                type="text"
                placeholder="EXW Seoul"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div v-if="formData.is_customer">
              <label class="block text-sm font-medium text-gray-700 mb-1">기본 마진율 (%)</label>
              <input
                v-model.number="formData.default_margin_rate"
                type="number"
                min="0"
                max="100"
                step="0.1"
                placeholder="30"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <p class="text-xs text-gray-400 mt-1">견적 가격 산정 시 사용</p>
            </div>
          </div>
          <!-- CI 원산지 신고문 기본값 (수출 고객 전용) -->
          <div v-if="formData.is_customer && !isDomestic" class="mt-4">
            <label class="inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer select-none">
              <input type="checkbox" v-model="formData.show_statement_of_origin" class="w-4 h-4 rounded" />
              CI에 원산지 신고문(Statement of Origin) 기본 표기
            </label>
            <p class="text-xs text-gray-400 mt-1">이 거래처로 CI 작성 시 원산지 신고문+서명란을 기본 포함합니다(문서별 조정 가능).</p>
          </div>
          <!-- v0.78.0: 생산요청 자동 채움 기본값 (고객 전용) -->
          <div v-if="formData.is_customer" class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">기본 SHIPPING MARK</label>
              <textarea
                v-model="formData.default_shipping_mark"
                rows="3"
                placeholder="생산요청 등록 시 자동으로 채워집니다"
                class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 resize-y"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">기본 CONSIGNEE (수하인)</label>
              <textarea
                v-model="formData.default_consignee"
                rows="3"
                placeholder="생산요청 등록 시 자동으로 채워집니다"
                class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 resize-y"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">기본 DESTINATION (도착지)</label>
              <input
                v-model="formData.default_destination"
                type="text"
                placeholder="예: Shenzhen, China (생산요청 등록 시 자동으로 채워집니다)"
                class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        <!-- 추가 정보 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">추가 정보</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
import { ref, computed, watch } from 'vue'
import apiClient from '@/api/client'
import { type BusinessPartnerCreate } from '@/api/partner'
import { COUNTRIES } from '@/constants/countries'
import SearchableSelect from '@/components/SearchableSelect.vue'

interface Props {
  show: boolean
  isEdit: boolean
  initialData?: Partial<BusinessPartnerCreate> | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  submit: [data: BusinessPartnerCreate]
}>()

// 중복 코드 에러 메시지
const duplicateError = ref<string>('')

// 국내/해외 판별
const isDomestic = computed(() => formData.value.trade_type === 'DOMESTIC')

// 거래 유형 변경 시 국내 코드 자동 채번
async function onTradeTypeChange() {
  if (isDomestic.value && !props.isEdit) {
    await generateDomesticCode()
  } else {
    // 해외로 변경하면 코드 초기화 (수동 입력)
    if (formData.value.partner_code?.startsWith('CUS') || formData.value.partner_code?.startsWith('SUP')) {
      formData.value.partner_code = ''
    }
  }
  duplicateError.value = ''
}

// 거래처 유형(고객/공급) 변경 시 국내면 코드 재채번
async function onPartnerTypeChange() {
  if (isDomestic.value && !props.isEdit) {
    await generateDomesticCode()
  }
}

// 국내 업체 코드 자동 생성
async function generateDomesticCode() {
  const partnerType = formData.value.is_customer ? 'customer' : (formData.value.is_supplier ? 'supplier' : 'customer')
  try {
    const res = await apiClient.get(`/partners/generate-domestic-code/${partnerType}`)
    formData.value.partner_code = res.data.code
    duplicateError.value = ''
  } catch {
    formData.value.partner_code = ''
  }
}

// 거래처 코드 중복 체크 (blur 이벤트)
async function checkDuplicateCode() {
  const code = formData.value.partner_code?.trim()
  if (!code) {
    duplicateError.value = ''
    return
  }

  // 수정 모드에서 자기 자신과 같으면 통과
  if (props.isEdit && props.initialData?.partner_code === code) {
    duplicateError.value = ''
    return
  }

  try {
    const res = await apiClient.get(`/partners/code/${encodeURIComponent(code)}`)
    if (res.data && res.data.id) {
      duplicateError.value = `이미 사용 중인 거래처 코드입니다: ${res.data.partner_name}`
    }
  } catch (err: any) {
    // 404 = 존재하지 않음 = 사용 가능
    if (err?.response?.status === 404) {
      duplicateError.value = ''
    }
  }
}

// 기본 폼 데이터
const getDefaultFormData = (): BusinessPartnerCreate => ({
  partner_code: '',
  partner_name: '',
  business_number: '',
  representative: '',
  is_supplier: false,
  is_customer: false,
  trade_type: 'EXPORT',
  country_code: '',
  country_name: '',
  business_start_year: undefined,
  address: '',
  tel: '',
  email: '',
  website: '',
  payment_terms: '',
  delivery_terms: '',
  show_statement_of_origin: false,
  default_margin_rate: undefined,
  default_shipping_mark: '',
  default_consignee: '',
  default_destination: '',
  remark: '',
  is_active: true,
})

// 폼 데이터
const formData = ref<BusinessPartnerCreate>(getDefaultFormData())

// 국가 검색 드롭다운(한글). 가나다순 + 기존 값이 목록에 없으면(레거시·직접 입력 표기) 맨 위에 그대로 노출.
// SearchableSelect 는 숫자 id 로 선택값을 다루므로 목록 순번을 id 로 쓴다.
const SORTED_COUNTRIES = [...COUNTRIES].sort((a, b) => a.ko.localeCompare(b.ko, 'ko'))
const countryOptions = computed(() => {
  const list = SORTED_COUNTRIES.map((c, i) => ({ id: i + 1, code: c.code, name_ko: c.ko, name_en: c.en }))
  const cur = (formData.value.country_name || '').trim()
  if (cur && !SORTED_COUNTRIES.some((c) => c.ko === cur)) {
    list.unshift({ id: list.length + 1, code: formData.value.country_code || '-', name_ko: cur, name_en: '' })
  }
  return list
})
// 선택 id ↔ 국가명·국가코드 (선택 시 국가코드 자동 채움)
const countryId = computed<number | undefined>({
  get: () => {
    const cur = (formData.value.country_name || '').trim()
    return cur ? countryOptions.value.find((o) => o.name_ko === cur)?.id : undefined
  },
  set: (id) => {
    const o = countryOptions.value.find((x) => x.id === id)
    if (!o) return
    formData.value.country_name = o.name_ko
    if (o.code !== '-') formData.value.country_code = o.code
  },
})

// 목록에 없는 국가 직접 입력 (폴더 규칙상 한글 국가명만 허용)
const countryManual = ref(false)
const countryError = ref('')
function startCountryManual() {
  countryManual.value = true
  countryError.value = ''
  formData.value.country_name = ''
  formData.value.country_code = ''
}
function stopCountryManual() {
  countryManual.value = false
  countryError.value = ''
  // 직접 입력한 값이 목록에 있으면 그대로 선택, 아니면 비움
  const c = COUNTRIES.find((x) => x.ko === (formData.value.country_name || '').trim())
  formData.value.country_name = c ? c.ko : ''
  formData.value.country_code = c ? c.code : ''
}

// 폼 리셋
const resetForm = () => {
  formData.value = getDefaultFormData()
  duplicateError.value = ''
  countryManual.value = false
  countryError.value = ''
}

// 모달 닫기
const closeModal = () => {
  emit('close')
}

// 폼 제출
const submitForm = async () => {
  // 제출 직전 한 번 더 중복 체크
  await checkDuplicateCode()
  if (duplicateError.value) {
    return
  }
  // 직접 입력한 국가명: 한글만(폴더명 기준). 목록에 있는 이름이면 국가코드 자동 보완.
  if (countryManual.value) {
    const name = (formData.value.country_name || '').trim()
    if (name && (!/[가-힣]/.test(name) || /[A-Za-z]/.test(name))) {
      countryError.value = '국가명은 한글로 입력하세요 (예: Montenegro → 몬테네그로)'
      return
    }
    formData.value.country_name = name
    const c = COUNTRIES.find((x) => x.ko === name)
    if (c && !formData.value.country_code) formData.value.country_code = c.code
  }
  formData.value.country_code = (formData.value.country_code || '').trim().toUpperCase()
  // 정수/Decimal 필드: 빈 문자열·NaN → null (Pydantic이 빈 문자열을 정수로 거부)
  const payload: any = { ...formData.value }
  const numericFields = [
    'business_start_year', 'lead_time_days',
    'credit_limit', 'discount_rate', 'default_margin_rate',
  ]
  for (const f of numericFields) {
    const v = payload[f]
    if (v === '' || v === undefined || (typeof v === 'number' && Number.isNaN(v))) {
      payload[f] = null
    }
  }
  emit('submit', payload)
}

// props 변경 감지
watch(
  () => props.initialData,
  (newData) => {
    if (newData) {
      formData.value = { ...getDefaultFormData(), ...newData }
      duplicateError.value = ''
      countryManual.value = false
      countryError.value = ''
    } else {
      resetForm()
    }
  },
  { immediate: true }
)
</script>
