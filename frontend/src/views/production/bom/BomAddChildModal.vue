<!--
  트리 편집기 '하위 부품 추가' 모달 (BOM 개편 2026-09)
  - 이름 입력 중 유사 부품 실시간 감지 → 기존 부품 재사용 유도(중복 방지)
  - '새 부품으로 추가'는 미분류 최소등록(코드·레벨은 나중에)
  기존 prompt() 대체
-->
<template>
  <Teleport to="body">
  <div class="fixed inset-0 z-[95] flex items-start justify-center bg-gray-900/50 overflow-y-auto p-4" @click.self="$emit('close')">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-md mt-20">
      <div class="flex items-center justify-between px-5 py-3.5 border-b">
        <h3 class="text-base font-bold">＋ 하위 부품 추가</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <div class="px-5 py-4">
        <div class="text-[12.5px] text-gray-500 mb-2">
          <span class="font-medium text-gray-700">{{ parentLabel }}</span> 아래에 추가합니다.
        </div>

        <label class="block text-sm font-medium text-gray-700 mb-1">부품 이름 <span class="text-red-500">*</span></label>
        <div class="flex gap-2">
          <input
            ref="nameInput"
            v-model="name"
            type="text"
            placeholder="예: 하우징, 오링, 핀…"
            class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-violet-400"
            @input="onInput"
            @keydown.enter="addNew()"
          />
          <div class="w-20">
            <input v-model.number="qty" type="number" min="1" step="1" title="수량"
              class="w-full px-2 py-2 border border-gray-300 rounded-md text-center focus:outline-none focus:ring-violet-400 focus:border-violet-400"/>
          </div>
        </div>
        <div class="text-[11.5px] text-gray-400 mt-1">코드·레벨 없이 <b>미분류</b>로 등록됩니다. 나중에 분류/채번으로 부여하세요.</div>

        <!-- 유사 부품(중복 방지) -->
        <div v-if="checking" class="mt-3 text-xs text-gray-400">유사 부품 확인 중…</div>
        <div v-else-if="similar.length > 0" class="mt-3">
          <div class="text-[12px] text-amber-700 font-medium mb-1">이미 있는 비슷한 부품 — 재사용하면 중복을 막을 수 있어요:</div>
          <div class="space-y-1 max-h-40 overflow-y-auto">
            <button
              v-for="p in similar"
              :key="p.id"
              @click="addExisting(p)"
              class="w-full flex items-center justify-between gap-2 text-left px-2.5 py-1.5 rounded-md border border-gray-200 hover:border-violet-300 hover:bg-violet-50 text-[12.5px]"
            >
              <span class="truncate">
                <span v-if="p.is_classified !== false" class="font-mono text-blue-600">{{ p.part_number_display || p.part_number }}</span>
                <span v-else class="text-[10px] font-semibold text-amber-600">미분류</span>
                <span class="text-gray-600 ml-1.5">{{ p.part_name }}</span>
              </span>
              <span class="flex-shrink-0 text-[11px] text-violet-600 font-medium">이 부품 추가 →</span>
            </button>
          </div>
        </div>
      </div>

      <div class="px-5 py-3.5 border-t flex justify-end gap-2">
        <button @click="$emit('close')" class="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200">취소</button>
        <button @click="addNew" :disabled="busy"
          class="px-4 py-2 text-sm bg-violet-600 text-white rounded-md hover:bg-violet-700 disabled:opacity-50">
          {{ busy ? '추가 중…' : '새 부품으로 추가' }}
        </button>
      </div>
    </div>
  </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { partApi, type PartListItem } from '@/api/parts'
import { bomApi } from '@/api/bom'
import { handleApiError } from '@/utils/errorHandler'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ parentPartId: number; parentLabel: string }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'added'): void }>()

const toast = useToast()
const name = ref('')
const qty = ref(1)
const busy = ref(false)
const similar = ref<PartListItem[]>([])
const checking = ref(false)
const nameInput = ref<HTMLInputElement | null>(null)

let timer: ReturnType<typeof setTimeout> | null = null
function onInput() {
  if (timer) clearTimeout(timer)
  const kw = name.value.trim()
  if (kw.length < 2) { similar.value = []; checking.value = false; return }
  checking.value = true
  timer = setTimeout(async () => {
    try { similar.value = (await partApi.getAll({ keyword: kw, limit: 6 })).data.items }
    catch { similar.value = [] }
    finally { checking.value = false }
  }, 300)
}

async function attach(childPartId: number) {
  await bomApi.create({ parent_part_id: props.parentPartId, child_part_id: childPartId, quantity: qty.value || 1 } as any)
}

async function addNew() {
  const nm = name.value.trim()
  if (!nm) { toast.error('부품 이름을 입력하세요.'); return }
  if (!props.parentPartId) { toast.error('상위 부품이 지정되지 않았습니다.'); return }
  if (busy.value) return
  busy.value = true
  try {
    const p = (await partApi.createMinimal(nm)).data
    await attach(p.id)
    emit('added')
  } catch (e: any) { toast.error(handleApiError(e)) }
  finally { busy.value = false }
}

async function addExisting(p: PartListItem) {
  if (busy.value) return
  busy.value = true
  try {
    await attach(p.id)
    emit('added')
  } catch (e: any) { toast.error(handleApiError(e)) }
  finally { busy.value = false }
}

onMounted(() => nextTick(() => nameInput.value?.focus()))
</script>
