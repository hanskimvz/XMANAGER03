<template>
  <div :style="{ paddingLeft: `${level * 16}px` }" class="py-0.5">
    <div class="flex items-center text-xs">
      <!-- 트리 라인 및 아이콘 -->
      <div class="flex items-center mr-1">
        <!-- 수직선 -->
        <span class="text-gray-300 mr-0.5">└</span>
        <!-- 폴더/파일 아이콘 -->
        <svg
          v-if="node.children && node.children.length > 0"
          class="w-3 h-3 text-amber-500"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path fill-rule="evenodd" d="M2 6a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1H8a3 3 0 00-3 3v1.5a1.5 1.5 0 01-3 0V6z" clip-rule="evenodd" />
          <path d="M6 12a2 2 0 012-2h8a2 2 0 012 2v2a2 2 0 01-2 2H2h2a2 2 0 002-2v-2z" />
        </svg>
        <svg v-else class="w-3 h-3 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
        </svg>
      </div>

      <!-- 부품 정보 -->
      <div class="flex-1 flex items-center min-w-0 flex-wrap">
        <span
          class="font-medium text-blue-600 hover:text-blue-800 hover:underline cursor-pointer break-all"
          @click="$emit('view-detail', node.part_id)"
          :title="(node.part_number_display || node.part_number) + ' - ' + node.part_name"
        >{{ node.part_number_display || node.part_number }}</span>
        <span class="text-gray-500 ml-1 break-words">{{ node.part_name }}</span>
      </div>

      <!-- 수량 및 가격 -->
      <div class="flex-shrink-0 ml-1 flex items-center gap-1">
        <span class="bg-blue-100 text-blue-800 font-medium px-1 py-0.5 rounded text-xs">
          x {{ node.quantity }}
        </span>
        <span v-if="priceInfo?.unit_price" class="text-green-600 font-medium whitespace-nowrap">
          {{ formatPrice(priceInfo.unit_price * node.quantity) }}
        </span>
      </div>
    </div>

    <!-- 자식 노드 재귀 렌더링 -->
    <template v-if="node.children && node.children.length > 0">
      <BOMTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :level="level + 1"
        :price-map="priceMap"
        @view-detail="(partId) => $emit('view-detail', partId)"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BOMTreeNode as BOMTreeNodeType } from '@/api/bom'

interface Props {
  node: BOMTreeNodeType
  level: number
  priceMap?: Record<number, { unit_price: number; currency: string }>
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'view-detail': [partId: number]
}>()

// 현재 노드의 가격 정보
const priceInfo = computed(() => {
  if (!props.priceMap || !props.node.part_id) return null
  return props.priceMap[props.node.part_id]
})

// 가격 포맷팅 (소수점 없이)
function formatPrice(amount: number | undefined): string {
  if (amount === undefined || amount === null || amount === 0) return ''
  return '₩' + Math.round(amount).toLocaleString('ko-KR')
}
</script>
