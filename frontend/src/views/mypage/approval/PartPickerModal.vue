<template>
  <div class="fixed inset-0 z-[70] flex items-center justify-center bg-black/50" @click.self="$emit('close')">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 flex flex-col max-h-[85vh]">
      <div class="flex items-center justify-between px-5 py-3 border-b">
        <h3 class="text-base font-semibold text-gray-800">BOM(부품)에서 선택</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
      </div>
      <div class="px-5 py-3 border-b">
        <input
          v-model="keyword"
          @input="onSearch"
          type="text"
          placeholder="품번 · 품명 · 코드로 검색 (예: PT-, 브라켓, 품번 앞자리)"
          class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p class="text-[11px] text-gray-400 mt-1">부품 마스터(BOM 등록 품목)에서 검색됩니다. 품번 코드 앞자리로도 분류 검색 가능. 여러 개 선택 후 추가하세요.</p>
      </div>
      <div class="flex-1 overflow-y-auto">
        <div v-if="loading" class="p-4 text-sm text-gray-400">검색 중…</div>
        <table v-else class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-500 text-xs sticky top-0">
            <tr>
              <th class="w-8 px-2 py-2"></th>
              <th class="px-2 py-2 text-left">품번</th>
              <th class="px-2 py-2 text-left">품명</th>
              <th class="px-2 py-2 text-right">표준단가</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="p in results"
              :key="p.id"
              class="border-t hover:bg-blue-50 cursor-pointer"
              @click="toggle(p)"
            >
              <td class="px-2 py-2 text-center">
                <input type="checkbox" :checked="selected.has(p.id)" @click.stop="toggle(p)" />
              </td>
              <td class="px-2 py-2 font-mono text-xs text-gray-700">{{ p.part_number_display || p.part_number }}</td>
              <td class="px-2 py-2 text-gray-800">{{ p.part_name }}</td>
              <td class="px-2 py-2 text-right text-gray-500">{{ p.standard_price != null ? p.standard_price.toLocaleString() : '-' }}</td>
            </tr>
            <tr v-if="!results.length">
              <td colspan="4" class="px-2 py-6 text-center text-gray-400">검색 결과가 없습니다</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="px-5 py-3 border-t flex items-center justify-between">
        <span class="text-xs text-gray-500">{{ selected.size }}개 선택</span>
        <div class="flex gap-2">
          <button @click="$emit('close')" class="px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded">취소</button>
          <button
            @click="confirm"
            :disabled="!selected.size"
            class="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >추가 ({{ selected.size }})</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { partApi, type PartListItem } from '@/api/parts'

export interface PickedItem { part_id: number; name: string; unit_price: number | null }
const emit = defineEmits<{ (e: 'close'): void; (e: 'select', items: PickedItem[]): void }>()

const keyword = ref('')
const results = ref<PartListItem[]>([])
const loading = ref(false)
const selected = ref<Map<number, PartListItem>>(new Map())
let timer: ReturnType<typeof setTimeout> | null = null

async function search() {
  loading.value = true
  try {
    const res = await partApi.getAll({ keyword: keyword.value.trim() || undefined, is_active: true, limit: 50 })
    results.value = res.data.items || []
  } catch {
    results.value = []
  } finally {
    loading.value = false
  }
}
function onSearch() {
  if (timer) clearTimeout(timer)
  timer = setTimeout(search, 300)
}
function toggle(p: PartListItem) {
  if (selected.value.has(p.id)) selected.value.delete(p.id)
  else selected.value.set(p.id, p)
  selected.value = new Map(selected.value) // 반응성 트리거
}
function confirm() {
  const items: PickedItem[] = [...selected.value.values()].map((p) => ({
    part_id: p.id,
    name: `${p.part_number_display || p.part_number} ${p.part_name}`.trim(),
    unit_price: p.standard_price ?? null,
  }))
  emit('select', items)
}
onMounted(search)
</script>
