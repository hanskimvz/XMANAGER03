<template>
  <div
    v-if="show"
    ref="modalOverlay"
    class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-[60]"
    tabindex="-1"
    @keydown.escape="closeModal"
  >
    <div class="relative top-1/4 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white" @click.stop>
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold">{{ title }} 간편등록</h3>
        <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="bg-blue-50 border border-blue-200 rounded-md p-3 mb-4">
        <p class="text-sm text-blue-700">
          {{ description }}<br/>
          추가 정보는 코드 마스터 관리 페이지에서 입력할 수 있습니다.
        </p>
      </div>

      <form @submit.prevent="submitForm" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            코드 <span class="text-red-500">*</span>
          </label>
          <input
            v-model="formData.code"
            type="text"
            required
            :placeholder="codePlaceholder"
            :maxlength="codeMaxLength"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
          <p class="text-xs text-gray-500 mt-1">{{ codeHint }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            한글명 <span class="text-red-500">*</span>
          </label>
          <input
            v-model="formData.name_ko"
            type="text"
            required
            :placeholder="namePlaceholder"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">영문명</label>
          <input
            v-model="formData.name_en"
            type="text"
            placeholder="예: Battery Pack"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">설명</label>
          <textarea
            v-model="formData.description"
            rows="2"
            placeholder="간단한 설명 (선택사항)"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <!-- 에러 메시지 -->
        <div v-if="error" class="bg-red-50 border border-red-200 rounded-md p-3">
          <p class="text-sm text-red-700">{{ error }}</p>
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
            :disabled="isSubmitting"
            class="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
          >
            {{ isSubmitting ? '등록 중...' : '간편등록' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { productLineApi, partGroupApi, materialApi, treatmentApi, type CodeMasterCreate } from '@/api/codeMaster'

type CodeType = 'product_line' | 'part_group' | 'material' | 'treatment'

interface Props {
  show: boolean
  codeType: CodeType
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  added: [id: number]
}>()

const isSubmitting = ref(false)
const error = ref('')

// 코드 타입별 설정
const codeTypeConfig = computed(() => {
  switch (props.codeType) {
    case 'product_line':
      return {
        title: '제품라인(대분류)',
        description: '필수 정보만 입력하여 빠르게 제품라인을 등록합니다.',
        codePlaceholder: '예: HB01, BI03',
        codeHint: '4자리 영문+숫자 (예: HB01)',
        codeMaxLength: 4,
        namePlaceholder: '예: 수소자전거',
      }
    case 'part_group':
      return {
        title: '품목군(소분류)',
        description: '필수 정보만 입력하여 빠르게 품목군을 등록합니다.',
        codePlaceholder: '예: DCP, PLP',
        codeHint: '3자리 영문 대문자 (예: DCP)',
        codeMaxLength: 3,
        namePlaceholder: '예: 전기장치부품',
      }
    case 'material':
      return {
        title: '재질',
        description: '필수 정보만 입력하여 빠르게 재질을 등록합니다.',
        codePlaceholder: '예: A6, S4, NB',
        codeHint: '2자리 영문+숫자 (예: A6)',
        codeMaxLength: 2,
        namePlaceholder: '예: AL6061',
      }
    case 'treatment':
      return {
        title: '후처리',
        description: '필수 정보만 입력하여 빠르게 후처리를 등록합니다.',
        codePlaceholder: '예: WA, CD, NK',
        codeHint: '2자리 영문 대문자 (예: NK)',
        codeMaxLength: 2,
        namePlaceholder: '예: 니켈',
      }
    default:
      return {
        title: '코드',
        description: '코드를 등록합니다.',
        codePlaceholder: '코드 입력',
        codeHint: '',
        codeMaxLength: 10,
        namePlaceholder: '한글명 입력',
      }
  }
})

const title = computed(() => codeTypeConfig.value.title)
const description = computed(() => codeTypeConfig.value.description)
const codePlaceholder = computed(() => codeTypeConfig.value.codePlaceholder)
const codeHint = computed(() => codeTypeConfig.value.codeHint)
const codeMaxLength = computed(() => codeTypeConfig.value.codeMaxLength)
const namePlaceholder = computed(() => codeTypeConfig.value.namePlaceholder)

const formData = ref<CodeMasterCreate>({
  code: '',
  name_ko: '',
  name_en: '',
  description: '',
  is_active: true,
  sort_order: 0,
})

const resetForm = () => {
  formData.value = {
    code: '',
    name_ko: '',
    name_en: '',
    description: '',
    is_active: true,
    sort_order: 0,
  }
  error.value = ''
}

const closeModal = () => {
  resetForm()
  emit('close')
}

const submitForm = async () => {
  if (!formData.value.code || !formData.value.name_ko) {
    error.value = '코드와 한글명은 필수입니다.'
    return
  }

  try {
    isSubmitting.value = true
    error.value = ''

    let response
    switch (props.codeType) {
      case 'product_line':
        response = await productLineApi.create(formData.value)
        break
      case 'part_group':
        response = await partGroupApi.create(formData.value)
        break
      case 'material':
        response = await materialApi.create(formData.value)
        break
      case 'treatment':
        response = await treatmentApi.create(formData.value)
        break
      default:
        throw new Error('지원하지 않는 코드 유형입니다.')
    }

    emit('added', response.data.id)
    resetForm()
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = '코드 등록에 실패했습니다.'
    }
  } finally {
    isSubmitting.value = false
  }
}

// show 변경 시 폼 리셋
watch(() => props.show, (newVal) => {
  if (newVal) {
    resetForm()
  }
})
</script>
