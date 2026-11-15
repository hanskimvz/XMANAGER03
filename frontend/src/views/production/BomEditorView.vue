<!--
  BOM 편집 전용 화면 (BOM 개편 2026-09, P1) — 별도 라우트 /bom/:partId/edit
  좌: 부품 팔레트(찾기/만들기) · 우: 트리 캔버스(두 구역 드롭)
  bomDrag를 여기서 provide → 팔레트↔트리가 같은 드래그 상태 공유
-->
<template>
  <div class="be">
    <!-- 툴바 -->
    <div class="be-bar">
      <button class="be-back" @click="goBack">◀ 완료</button>
      <div class="be-title" v-if="rootPart">
        <span v-if="rootPart.is_classified !== false" class="be-num">{{ rootPart.part_number_display || rootPart.part_number }}</span>
        <span v-else class="be-unc">미분류</span>
        <span class="be-name">{{ rootPart.part_name }}</span>
      </div>
      <div class="be-hint">좌측에서 부품을 끌어 우측 트리에 놓으세요 — 행 <b>위</b>=하위, 행 <b>사이</b>=같은 레벨</div>
    </div>

    <div v-if="loadingPart" class="be-loading">불러오는 중…</div>
    <div v-else-if="!rootPart" class="be-loading">부품을 찾을 수 없습니다. <button class="be-back" @click="goBack">돌아가기</button></div>

    <div v-else class="be-main">
      <!-- 좌: 팔레트 -->
      <div class="be-left">
        <BomPartPalette :placed-counts="placedCounts" @place-under-root="onPlaceUnderRoot" />
      </div>
      <!-- 우: 트리 -->
      <div class="be-right">
        <BomTreeEditor
          ref="treeRef"
          :root-part-id="rootPart.id"
          :root-label="rootLabel"
          @loaded="onTreeLoaded"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, provide, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { partApi, type Part, type PartListItem } from '@/api/parts'
import { type BOMTreeNode } from '@/api/bom'
import BomPartPalette from '@/views/production/bom/BomPartPalette.vue'
import BomTreeEditor from '@/views/production/bom/BomTreeEditor.vue'

const route = useRoute()
const router = useRouter()

// 팔레트↔트리 공유 드래그 상태
const drag = ref<any>(null)
provide('bomDrag', drag)

const rootPart = ref<Part | null>(null)
const loadingPart = ref(true)
const treeRef = ref<any>(null)

// 트리 헤더 라벨: 미분류(품번 없음)면 품번(고유ID) 대신 부품명 표시
const rootLabel = computed(() => {
  const p = rootPart.value
  if (!p) return ''
  return p.is_classified === false ? (p.part_name || '미분류 부품') : (p.part_number_display || p.part_number)
})

// 트리에서 올라온 노드로 부품별 배치 횟수 집계
const treeNodes = ref<BOMTreeNode[]>([])
const placedCounts = computed<Record<number, number>>(() => {
  const map: Record<number, number> = {}
  const walk = (nodes: BOMTreeNode[]) => {
    for (const n of nodes) {
      if (n.part_id) map[n.part_id] = (map[n.part_id] || 0) + 1
      if (n.children?.length) walk(n.children)
    }
  }
  walk(treeNodes.value)
  return map
})
function onTreeLoaded(nodes: BOMTreeNode[]) { treeNodes.value = nodes }

// 팔레트 카드 더블클릭 → 최상위 하위로 추가
function onPlaceUnderRoot(part: PartListItem) {
  if (!rootPart.value) return
  treeRef.value?.addExisting?.(rootPart.value.id, part.id, part.part_name)
}

function goBack() {
  router.push({ name: 'bom' })
}

onMounted(async () => {
  const id = Number(route.params.partId)
  try { rootPart.value = (await partApi.getById(id)).data }
  catch { rootPart.value = null }
  finally { loadingPart.value = false }
})
</script>

<style scoped>
.be { position: fixed; inset: 0; z-index: 40; background: #f3f4f6; display: flex; flex-direction: column; }
.be-bar { display: flex; align-items: center; gap: 16px; padding: 10px 16px; background: #fff; border-bottom: 1px solid #e5e7eb; }
.be-back { border: 1px solid #d1d5db; background: #fff; border-radius: 8px; padding: 6px 12px; font-size: 13px; cursor: pointer; font-weight: 600; }
.be-back:hover { background: #f9fafb; }
.be-title { display: flex; align-items: baseline; gap: 10px; }
.be-num { font-family: ui-monospace, Consolas, monospace; font-weight: 700; color: #111827; }
.be-unc { font-size: 11px; font-weight: 700; color: #b45309; background: #fdeede; border-radius: 5px; padding: 1px 7px; }
.be-name { color: #4b5563; font-size: 14px; }
.be-hint { margin-left: auto; font-size: 12px; color: #9ca3af; }
.be-loading { flex: 1; display: flex; align-items: center; justify-content: center; gap: 10px; color: #6b7280; }
.be-main { flex: 1; display: flex; gap: 12px; padding: 12px; min-height: 0; }
.be-left { width: 340px; flex-shrink: 0; }
.be-right { flex: 1; min-width: 0; background: #fff; border-radius: 12px; overflow: auto; }
</style>
