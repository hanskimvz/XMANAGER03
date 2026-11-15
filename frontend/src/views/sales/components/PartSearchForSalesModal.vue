<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[60] flex items-start justify-center bg-black/50 overflow-y-auto py-8">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4">
        <!-- 헤더 -->
        <div class="flex items-center justify-between px-6 py-4 border-b">
          <h3 class="text-lg font-bold">완제품 검색</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- 검색 영역 -->
        <div class="px-6 py-4 border-b bg-gray-50">
          <div class="flex gap-2">
            <input
              ref="searchInput"
              v-model="keyword"
              @input="debouncedSearch"
              placeholder="품번, 품명, 설명 검색..."
              class="flex-1 border rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <button
              @click="openQuickAdd"
              class="px-3 py-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 whitespace-nowrap"
            >
              + 새 완제품 등록
            </button>
          </div>
          <p class="text-xs text-gray-500 mt-2">
            완제품(F) / 유닛(U) / 키트(K) 만 표시됩니다.
          </p>
        </div>

        <!-- 결과 목록 -->
        <div class="px-6 py-4 max-h-[60vh] overflow-y-auto">
          <div v-if="loading" class="text-center py-8 text-gray-400">검색 중...</div>
          <div v-else-if="items.length === 0 && keyword" class="text-center py-8 text-gray-400">
            <p>검색 결과가 없습니다.</p>
            <button @click="openQuickAdd" class="mt-3 px-4 py-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700">
              + 새 완제품으로 등록
            </button>
          </div>
          <div v-else-if="items.length === 0" class="text-center py-8 text-gray-400">
            검색어를 입력하세요.
          </div>
          <table v-else class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50 sticky top-0">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">품번</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">품명</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">레벨</th>
                <th class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">기준 단가</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">상태</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr
                v-for="part in items"
                :key="part.id"
                @click="selectPart(part)"
                class="hover:bg-blue-50 cursor-pointer"
              >
                <td class="px-3 py-2 text-sm font-mono text-blue-600">
                  {{ part.part_number_display || part.part_number }}
                  <span v-if="(part as any).is_protected" class="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-red-100 text-red-700 whitespace-nowrap"
                    :title="`전속: ${(part as any).protected_customer?.partner_name || '지정 고객'}`">🔒 전속</span>
                </td>
                <td class="px-3 py-2 text-sm">
                  <div>{{ part.part_name }}</div>
                  <div v-if="part.part_name_en" class="text-xs text-gray-400">{{ part.part_name_en }}</div>
                </td>
                <td class="px-3 py-2 text-sm text-gray-600">{{ part.level?.code || '-' }}</td>
                <td class="px-3 py-2 text-sm text-right">
                  <span v-if="part.standard_price">
                    {{ part.standard_price_currency || 'KRW' }} {{ Math.round(part.standard_price).toLocaleString() }}
                  </span>
                  <span v-else class="text-gray-400">-</span>
                </td>
                <td class="px-3 py-2 text-center">
                  <span
                    v-if="part.approval_status === 'DRAFT'"
                    class="px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full"
                  >승인대기</span>
                  <span v-else class="text-xs text-gray-400">-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Quick Add 모달 -->
    <PartQuickAddModal
      v-if="showQuickAdd"
      :initial-keyword="keyword"
      @close="showQuickAdd = false"
      @created="onQuickAddCreated"
    />
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { partApi, type PartListItem } from '@/api/parts'
import PartQuickAddModal from './PartQuickAddModal.vue'

const emit = defineEmits<{ (e: 'close'): void; (e: 'select', part: PartListItem): void }>()

const keyword = ref('')
const items = ref<PartListItem[]>([])
const loading = ref(false)
const searchInput = ref<HTMLInputElement | null>(null)
const showQuickAdd = ref(false)

// 완제품 레벨 IDs: F(1), U(2), K(3)
const FINISHED_LEVEL_IDS = '1,2,3'

async function search() {
  if (!keyword.value.trim()) {
    items.value = []
    return
  }
  loading.value = true
  try {
    const res = await partApi.getAll({
      keyword: keyword.value.trim(),
      level_ids: FINISHED_LEVEL_IDS,
      limit: 50,
    } as any)
    items.value = (res.data as any).items || []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedSearch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(search, 300)
}

function selectPart(part: PartListItem) {
  emit('select', part)
  emit('close')
}

function openQuickAdd() {
  showQuickAdd.value = true
}

function onQuickAddCreated(part: PartListItem) {
  showQuickAdd.value = false
  emit('select', part)
  emit('close')
}

onMounted(async () => {
  await nextTick()
  searchInput.value?.focus()
})
</script>
