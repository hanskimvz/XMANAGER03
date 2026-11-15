<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[70] flex items-start justify-center bg-black/60 overflow-y-auto py-8">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        <!-- 헤더 -->
        <div class="flex items-center justify-between px-6 py-4 border-b">
          <h3 class="text-lg font-bold">완제품 간편 등록</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- 안내 -->
        <div class="px-6 py-3 bg-yellow-50 border-b border-yellow-200">
          <p class="text-xs text-yellow-800">
            <strong>⚠ 승인 대기 상태</strong>로 등록됩니다. 추후 기술팀이 정식 품번/분류를 보완합니다.
          </p>
        </div>

        <!-- 폼 -->
        <div class="px-6 py-4 space-y-4">
          <!-- 품번 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              품번 (오더코드) <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.part_number"
              class="w-full border rounded-md px-3 py-2 text-sm font-mono"
              placeholder="예: HXB13-PSD-B-O4-S1-D55"
            />
            <p class="text-xs text-gray-400 mt-1">고객사에 보낼 오더코드 그대로 입력하세요.</p>
          </div>

          <!-- 품명 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              품명 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.part_name"
              class="w-full border rounded-md px-3 py-2 text-sm"
              placeholder="예: HXB13 4채널 관통 커넥터"
            />
          </div>

          <!-- 영문 품명 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">영문 품명</label>
            <input
              v-model="form.part_name_en"
              class="w-full border rounded-md px-3 py-2 text-sm"
              placeholder="예: HXB13 4CH Feedthrough Connector"
            />
          </div>

          <!-- 레벨 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">레벨</label>
            <select v-model.number="form.level_id" class="w-full border rounded-md px-3 py-2 text-sm">
              <option :value="1">F - 완제품</option>
              <option :value="2">U - 유닛</option>
              <option :value="3">K - 키트</option>
            </select>
          </div>

          <!-- 기준 단가 -->
          <div class="grid grid-cols-3 gap-3">
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">기준 단가</label>
              <input
                v-model.number="form.standard_price"
                type="number"
                min="0"
                class="w-full border rounded-md px-3 py-2 text-sm"
                placeholder="0"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">통화</label>
              <select v-model="form.standard_price_currency" class="w-full border rounded-md px-3 py-2 text-sm">
                <option value="KRW">KRW (₩)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="JPY">JPY (¥)</option>
                <option value="CNY">CNY (¥)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>
          </div>

          <!-- 설명 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">설명 (선택)</label>
            <textarea
              v-model="form.description"
              rows="3"
              class="w-full border rounded-md px-3 py-2 text-sm"
              placeholder="부품 설명 또는 특이사항"
            />
          </div>
        </div>

        <!-- 하단 버튼 -->
        <div class="flex justify-end gap-2 px-6 py-4 border-t bg-gray-50">
          <button @click="$emit('close')" class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
            취소
          </button>
          <button
            @click="save"
            :disabled="saving || !form.part_number || !form.part_name"
            class="px-6 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {{ saving ? '등록 중...' : '등록' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { partApi, type PartListItem } from '@/api/parts'
import { useToast } from '@/composables/useToast'

interface Props {
  initialKeyword?: string
}
const props = withDefaults(defineProps<Props>(), { initialKeyword: '' })
const emit = defineEmits<{ (e: 'close'): void; (e: 'created', part: PartListItem): void }>()
const { showToast } = useToast()

const saving = ref(false)
const form = ref({
  part_number: props.initialKeyword || '',
  part_name: '',
  part_name_en: '',
  level_id: 1, // F - 완제품
  standard_price: 0,
  standard_price_currency: 'KRW',
  description: '',
  approval_status: 'DRAFT',
  status: 'ACTIVE',
  is_active: true,
})

async function save() {
  if (!form.value.part_number.trim() || !form.value.part_name.trim()) {
    showToast('품번과 품명은 필수입니다', 'error')
    return
  }

  saving.value = true
  try {
    const payload: any = {
      part_number: form.value.part_number.trim(),
      part_number_display: form.value.part_number.trim(),
      part_name: form.value.part_name.trim(),
      level_id: form.value.level_id,
      approval_status: 'DRAFT',
      status: 'ACTIVE',
      is_active: true,
    }
    if (form.value.part_name_en) payload.part_name_en = form.value.part_name_en.trim()
    if (form.value.description) payload.description = form.value.description.trim()
    if (form.value.standard_price && form.value.standard_price > 0) {
      payload.standard_price = form.value.standard_price
      payload.standard_price_currency = form.value.standard_price_currency
    }

    const res = await partApi.create(payload)
    showToast('완제품이 등록되었습니다 (승인 대기)', 'success')
    emit('created', res.data as PartListItem)
  } catch (err: any) {
    const detail = err?.response?.data?.detail || '등록에 실패했습니다'
    showToast(typeof detail === 'string' ? detail : '등록에 실패했습니다', 'error')
  } finally {
    saving.value = false
  }
}
</script>
