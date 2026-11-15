<!--
  신규 제품 BOM 시작 위저드 (BOM 개편 2026-09)
  표준 흐름: 제품명 입력 → 최상위 부품 자동 생성(미분류) → 바로 트리 편집기 진입
  - 코드/레벨은 나중에 '분류/채번'으로 부여 (구조 먼저, 코드 나중)
  - 입력 중 유사 제품 실시간 감지로 중복 생성 방지
-->
<template>
  <div v-if="show" class="fixed inset-0 z-[80] flex items-start justify-center bg-gray-900/50 overflow-y-auto p-4">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-lg mt-16">
      <!-- 헤더 -->
      <div class="flex items-center justify-between px-5 py-4 border-b">
        <h3 class="text-lg font-bold flex items-center gap-2">✨ 신규 제품 BOM 시작</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <div class="px-5 py-4">
        <!-- 표준 흐름 안내 -->
        <div class="bg-violet-50 border border-violet-200 rounded-lg p-3 mb-4 text-[13px] text-violet-800">
          <div class="font-semibold mb-1">표준 등록 순서</div>
          <div class="flex items-center flex-wrap gap-x-1.5 gap-y-1 text-violet-700">
            <span class="font-medium">① 제품 이름</span><span class="text-violet-300">→</span>
            <span>② 트리에서 하위 부품(이름만)</span><span class="text-violet-300">→</span>
            <span>③ 도면 첨부</span><span class="text-violet-300">→</span>
            <span>④ 코드 부여(나중)</span>
          </div>
          <div class="mt-1.5 text-[12px] text-violet-500">
            지금은 <b>제품 이름만</b> 정하면 됩니다. 품번·레벨 등 코드는 구조를 다 짠 뒤 한꺼번에 부여해도 됩니다.
          </div>
        </div>

        <!-- 제품명 -->
        <label class="block text-sm font-medium text-gray-700 mb-1">제품(최상위) 이름 <span class="text-red-500">*</span></label>
        <input
          ref="nameInput"
          v-model="name"
          type="text"
          placeholder="예: HXB13-PSD 커넥터 키트"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-violet-400"
          @input="onNameInput"
          @keydown.enter="start()"
        />

        <!-- 유사 제품 감지(중복 방지) -->
        <div v-if="checking" class="mt-2 text-xs text-gray-400">유사 제품 확인 중…</div>
        <div v-else-if="similar.length > 0" class="mt-2 bg-amber-50 border border-amber-200 rounded-md p-2.5">
          <div class="text-[12.5px] text-amber-800 font-medium mb-1">
            ⚠️ 비슷한 이름의 제품이 이미 있어요 — 중복 등록이 아닌지 확인하세요.
          </div>
          <ul class="space-y-0.5 max-h-32 overflow-y-auto">
            <li v-for="p in similar" :key="p.id" class="flex items-center justify-between text-[12.5px] gap-2">
              <span class="truncate">
                <span v-if="p.is_classified !== false" class="font-mono text-blue-600">{{ p.part_number_display || p.part_number }}</span>
                <span v-else class="text-[10px] font-semibold text-amber-600">미분류</span>
                <span class="text-gray-600 ml-1.5">{{ p.part_name }}</span>
              </span>
              <button @click="$emit('use-existing', p)" class="flex-shrink-0 text-[11.5px] px-2 py-0.5 rounded bg-amber-500 text-white hover:bg-amber-600">
                이 제품 선택
              </button>
            </li>
          </ul>
        </div>

        <!-- 선택 입력: 영문명 -->
        <div class="mt-3">
          <button @click="showMore = !showMore" class="text-xs text-gray-500 hover:text-gray-700">
            {{ showMore ? '▾ 추가 정보 접기' : '▸ 영문명·설명 추가(선택)' }}
          </button>
          <div v-if="showMore" class="mt-2 space-y-2">
            <div>
              <label class="block text-xs text-gray-600 mb-1">영문 제품명</label>
              <input v-model="nameEn" type="text" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-violet-400 focus:border-violet-400"/>
            </div>
            <div>
              <label class="block text-xs text-gray-600 mb-1">설명</label>
              <textarea v-model="description" rows="2" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-violet-400 focus:border-violet-400"></textarea>
            </div>
          </div>
        </div>
      </div>

      <!-- 푸터 -->
      <div class="px-5 py-4 border-t flex items-center justify-between gap-2">
        <button @click="$emit('excel')" class="text-[12.5px] text-gray-500 hover:text-blue-600">
          📊 부품이 표로 정리돼 있나요? <span class="underline">엑셀로 일괄 등록</span>
        </button>
        <div class="flex gap-2">
          <button @click="$emit('close')" class="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200">취소</button>
          <button
            @click="start"
            :disabled="starting"
            class="px-4 py-2 text-sm bg-violet-600 text-white rounded-md hover:bg-violet-700 disabled:opacity-50 flex items-center gap-1.5"
          >
            {{ starting ? '생성 중…' : '시작 → 트리 편집' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { partApi, type Part, type PartListItem, type PartCreate } from '@/api/parts'
import { handleApiError } from '@/utils/errorHandler'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'excel'): void
  (e: 'started', part: PartListItem): void
  (e: 'use-existing', part: PartListItem): void
}>()

const toast = useToast()

const name = ref('')
const nameEn = ref('')
const description = ref('')
const showMore = ref(false)
const starting = ref(false)
const nameInput = ref<HTMLInputElement | null>(null)

const similar = ref<PartListItem[]>([])
const checking = ref(false)

let checkTimer: ReturnType<typeof setTimeout> | null = null
function onNameInput() {
  if (checkTimer) clearTimeout(checkTimer)
  const kw = name.value.trim()
  if (kw.length < 2) { similar.value = []; checking.value = false; return }
  checking.value = true
  checkTimer = setTimeout(async () => {
    try {
      const res = await partApi.getAll({ keyword: kw, limit: 5 })
      similar.value = res.data.items
    } catch { similar.value = [] }
    finally { checking.value = false }
  }, 300)
}

async function start() {
  const nm = name.value.trim()
  if (!nm) { toast.error('제품 이름을 입력하세요.'); return }
  if (starting.value) return
  starting.value = true
  try {
    const extra: Partial<PartCreate> = {}
    if (nameEn.value.trim()) extra.part_name_en = nameEn.value.trim()
    if (description.value.trim()) extra.description = description.value.trim()
    const created = (await partApi.createMinimal(name.value.trim(), extra)).data as Part
    const part: PartListItem = {
      id: created.id,
      part_number: created.part_number,
      part_number_display: created.part_number_display,
      part_name: created.part_name,
      specification: created.specification,
      is_active: true,
      created_at: new Date().toISOString(),
    } as PartListItem
    emit('started', part)
    reset()
  } catch (e: any) {
    toast.error(handleApiError(e))
  } finally {
    starting.value = false
  }
}

function reset() {
  name.value = ''; nameEn.value = ''; description.value = ''
  similar.value = []; showMore.value = false
}

watch(() => props.show, (v) => {
  if (v) { reset(); nextTick(() => nameInput.value?.focus()) }
})
</script>
