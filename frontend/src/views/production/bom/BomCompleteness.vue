<!--
  BOM 완결성 체크 패널 (BOM 개편 2026-09)
  트리 데이터로부터 마무리 품질을 요약: 미분류 / 도면(첨부) 없음 / 원가 미산정 / 수량 미입력.
  각 항목을 펼쳐 해당 부품으로 바로 이동(상세)할 수 있습니다.
  - 트리(getTree) 응답의 is_classified·attachment_count·quantity, priceMap을 그대로 활용(추가 API 없음)
-->
<template>
  <div class="rounded-lg border bg-white p-3" v-if="total > 0">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2 text-sm">
        <span class="font-semibold text-gray-700">완결성 체크</span>
        <span v-if="allClear" class="inline-flex items-center gap-1 text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5 text-xs font-medium">
          ✓ 모두 완료 · 부품 {{ total }}개
        </span>
        <span v-else class="text-xs text-gray-400">부품 {{ total }}개</span>
      </div>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="c in categories"
          :key="c.key"
          @click="toggle(c.key)"
          :class="[
            'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium border transition',
            c.items.length === 0
              ? 'bg-gray-50 text-gray-400 border-gray-200 cursor-default'
              : (open === c.key ? c.activeClass : c.class)
          ]"
          :disabled="c.items.length === 0"
        >
          <span>{{ c.icon }} {{ c.label }}</span>
          <span :class="c.items.length === 0 ? '' : 'font-bold'">{{ c.items.length }}</span>
        </button>
      </div>
    </div>

    <!-- 펼침: 해당 항목 부품 목록 -->
    <div v-if="openCategory && openCategory.items.length > 0" class="mt-3 border-t pt-2">
      <div class="text-xs text-gray-500 mb-1.5">{{ openCategory.hint }}</div>
      <div class="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
        <button
          v-for="n in openCategory.items"
          :key="n.part_id + '-' + n.id"
          @click="$emit('view-detail', n.part_id)"
          class="inline-flex items-center gap-1.5 rounded-md border border-gray-200 bg-gray-50 hover:bg-blue-50 hover:border-blue-300 px-2 py-1 text-xs"
          title="클릭하여 부품 상세 보기"
        >
          <span v-if="n.is_classified !== false" class="font-mono text-blue-600">{{ n.part_number_display || n.part_number }}</span>
          <span v-else class="text-[10px] font-semibold text-amber-600">미분류</span>
          <span class="text-gray-600 truncate max-w-[160px]">{{ n.part_name }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { BOMTreeNode } from '@/api/bom'

const props = defineProps<{
  tree: BOMTreeNode[]
  priceMap: Record<number, { unit_price: number; currency: string }>
}>()
defineEmits<{ (e: 'view-detail', partId: number): void }>()

const open = ref<string | null>(null)
function toggle(key: string) { open.value = open.value === key ? null : key }

// 트리 평탄화(모든 노드)
const flat = computed<BOMTreeNode[]>(() => {
  const out: BOMTreeNode[] = []
  const walk = (nodes: BOMTreeNode[]) => {
    for (const n of nodes) {
      out.push(n)
      if (n.children && n.children.length) walk(n.children)
    }
  }
  walk(props.tree || [])
  return out
})

const total = computed(() => flat.value.length)

const unclassified = computed(() => flat.value.filter(n => n.is_classified === false))
// 도면/첨부 없음: 말단(하위가 없는) 부품만 대상 — 어셈블리는 구조로 정의됨
const noDrawing = computed(() => flat.value.filter(n => (!n.children || n.children.length === 0) && (n.attachment_count || 0) === 0))
const noCost = computed(() => flat.value.filter(n => !(props.priceMap[n.part_id]?.unit_price)))
const zeroQty = computed(() => flat.value.filter(n => !n.quantity || n.quantity <= 0))

const categories = computed(() => [
  { key: 'unclassified', icon: '🏷️', label: '미분류', items: unclassified.value,
    class: 'bg-amber-50 text-amber-700 border-amber-200', activeClass: 'bg-amber-500 text-white border-amber-500',
    hint: '품번·레벨이 아직 부여되지 않은 부품입니다. 트리에서 ⋯ → 분류/채번으로 정식 품번을 부여하세요.' },
  { key: 'noDrawing', icon: '📎', label: '도면없음', items: noDrawing.value,
    class: 'bg-sky-50 text-sky-700 border-sky-200', activeClass: 'bg-sky-500 text-white border-sky-500',
    hint: '도면/스펙 첨부가 없는 말단 부품입니다. 트리에서 ⋯ → 첨부로 도면을 올리세요.' },
  { key: 'noCost', icon: '₩', label: '원가미산정', items: noCost.value,
    class: 'bg-rose-50 text-rose-700 border-rose-200', activeClass: 'bg-rose-500 text-white border-rose-500',
    hint: '단가/원가가 없는 부품입니다. 부품 상세에서 기준단가를 입력하거나 "원가 재계산"을 실행하세요.' },
  { key: 'zeroQty', icon: '#', label: '수량미입력', items: zeroQty.value,
    class: 'bg-orange-50 text-orange-700 border-orange-200', activeClass: 'bg-orange-500 text-white border-orange-500',
    hint: '수량이 0인 부품입니다. 트리에서 수량을 클릭해 수정하세요.' },
])

const openCategory = computed(() => categories.value.find(c => c.key === open.value) || null)
const allClear = computed(() => categories.value.every(c => c.items.length === 0))
</script>
