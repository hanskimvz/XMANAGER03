<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="show"
        ref="modalOverlay"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
        tabindex="-1"
        @keydown.escape="$emit('close')"
      >
        <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6" @click.stop>
          <!-- 헤더 -->
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-semibold">
              {{ isEdit ? '코드 수정' : '코드 추가' }}
            </h3>
            <button
              @click="$emit('close')"
              class="text-gray-400 hover:text-gray-600"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- 폼 -->
          <form @submit.prevent="handleSubmit">
            <div class="space-y-4">
              <!-- 코드 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  코드 *
                </label>
                <input
                  v-model="formData.code"
                  type="text"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="예: D, A6, NK"
                />
              </div>

              <!-- 한글명 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  한글명 *
                </label>
                <input
                  v-model="formData.name_ko"
                  type="text"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="예: 개발품, AL6061"
                />
              </div>

              <!-- 영문명 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  영문명
                </label>
                <input
                  v-model="formData.name_en"
                  type="text"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="예: Developed Part, Aluminum 6061"
                />
              </div>

              <!-- 설명 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  설명
                </label>
                <textarea
                  v-model="formData.description"
                  rows="3"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="설명을 입력하세요"
                ></textarea>
              </div>

              <!-- 정렬순서 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  정렬순서
                </label>
                <input
                  v-model.number="formData.sort_order"
                  type="number"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <!-- 사용여부 -->
              <div class="flex items-center">
                <input
                  v-model="formData.is_active"
                  type="checkbox"
                  id="is_active"
                  class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <label for="is_active" class="ml-2 text-sm text-gray-700">
                  사용
                </label>
              </div>
            </div>

            <!-- 버튼 -->
            <div class="mt-6 flex justify-end space-x-3">
              <button
                type="button"
                @click="$emit('close')"
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                취소
              </button>
              <button
                type="submit"
                :disabled="loading"
                class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
              >
                {{ loading ? '처리 중...' : (isEdit ? '수정' : '추가') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { CodeMaster, CodeMasterCreate } from '@/api/codeMaster'

interface Props {
  show: boolean
  isEdit?: boolean
  initialData?: CodeMaster | null
}

const props = withDefaults(defineProps<Props>(), {
  isEdit: false,
  initialData: null,
})

const emit = defineEmits<{
  close: []
  submit: [data: CodeMasterCreate]
}>()

const loading = ref(false)
const modalOverlay = ref<HTMLDivElement | null>(null)

// 모달이 열릴 때 포커스
watch(() => props.show, (newVal) => {
  if (newVal) {
    nextTick(() => {
      modalOverlay.value?.focus()
    })
  }
})

const formData = ref<CodeMasterCreate>({
  code: '',
  name_ko: '',
  name_en: '',
  description: '',
  sort_order: 0,
  is_active: true,
})

// props.initialData가 변경되면 폼 데이터 업데이트
watch(
  () => props.initialData,
  (newData) => {
    if (newData) {
      formData.value = {
        code: newData.code,
        name_ko: newData.name_ko,
        name_en: newData.name_en || '',
        description: newData.description || '',
        sort_order: newData.sort_order,
        is_active: newData.is_active,
      }
    } else {
      // 초기화
      formData.value = {
        code: '',
        name_ko: '',
        name_en: '',
        description: '',
        sort_order: 0,
        is_active: true,
      }
    }
  },
  { immediate: true }
)

const handleSubmit = () => {
  // 빈 정수 정규화 — Pydantic이 빈 문자열을 정수로 거부함
  const payload: any = { ...formData.value }
  const v = payload.sort_order
  if (v === '' || v === undefined || v === null || (typeof v === 'number' && Number.isNaN(v))) {
    payload.sort_order = 0
  }
  emit('submit', payload)
}
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
