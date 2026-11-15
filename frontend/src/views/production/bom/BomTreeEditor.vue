<template>
  <div class="bte">
    <div class="bte-head">
      <div class="bte-title">
        🧩 <b class="bte-root" :class="{ 'bte-root-sel': activeNode && !activeNode.bomId }" @click="selectRoot"
          title="클릭하여 최상위 선택 → '+ 하위 추가'로 최상위 아래에 부품 추가">{{ rootLabel }}</b>
        <span class="bte-sub">트리 편집 — 드래그로 이동, 수량 클릭 수정, ⋯로 추가/첨부/분류</span>
      </div>
      <div class="bte-actions">
        <button class="bte-btn bte-ic" @click="undoLast" :disabled="undoStack.length === 0" :title="undoStack.length ? '실행취소: ' + (undoStack[undoStack.length-1]?.label || '') : '실행취소'">⟲</button>
        <button class="bte-btn bte-ic" @click="redoLast" :disabled="redoStack.length === 0" title="다시 실행">⟳</button>
        <button class="bte-btn" @click="reloadClearExt" :disabled="loading">↻ 새로고침</button>
        <button class="bte-btn bte-btn-p" :disabled="!activeNode" @click="addSelectedChild"
          :title="activeNode ? `'${activeNode.label}' 아래에 하위 부품 추가` : '트리에서 부품(또는 최상위)을 클릭하면 그 하위로 추가할 수 있습니다'">
          + 하위 추가
        </button>
        <button class="bte-btn" :class="{ 'bte-btn-sel': selectMode }" @click="toggleSelectMode">
          {{ selectMode ? `묶기 선택(${selected.size})` : '☑ 묶기 선택' }}
        </button>
      </div>
    </div>

    <!-- 외부 변경 감지 배너 -->
    <div v-if="externalChanged" class="bte-ext">
      <span>⚠️ 다른 곳에서 이 BOM이 변경되었습니다. 최신 상태로 보려면 새로고침하세요.</span>
      <button class="bte-btn" @click="reloadClearExt">↻ 새로고침</button>
    </div>

    <div v-if="selectMode" class="bte-selbar">
      <span>{{ selected.size }}개 선택됨 — 새 상위 부품 밑으로 묶습니다.</span>
      <div>
        <button class="bte-btn" @click="clearSelection">해제</button>
        <button class="bte-btn bte-btn-p" :disabled="selected.size === 0" @click="doGroupUnder">⬆ 상위로 묶기</button>
      </div>
    </div>

    <div class="bte-body">
      <div v-if="loading" class="bte-empty">불러오는 중…</div>
      <div v-else-if="nodes.length === 0" class="bte-empty">
        하위 부품이 없습니다. <b>“+ 하위 추가”</b>로 시작하세요.
      </div>
      <div v-else class="bte-tree" @dragover.prevent @drop.prevent="onRootDrop">
        <BomNode v-for="n in nodes" :key="n.id" :node="n" :depth="0" :parent-part-id="rootPartId" />
      </div>
      <p class="bte-hint">
        <template v-if="activeNode">✅ 선택됨: <b>{{ activeNode.label }}</b> — <b>‘+ 하위 추가’</b>(단축키 <b>Insert</b>) · 삭제 <b>Delete</b> · 이름은 <b>더블클릭</b>으로 변경</template>
        <template v-else>💡 편집할 <b>부품을 클릭</b>하면 ‘+ 하위 추가’가 활성화됩니다. (최상위 아래에 넣으려면 위의 제품명 클릭 · 단축키 Insert/Delete)</template>
      </p>
    </div>

    <!-- 첨부 모달 -->
    <Teleport to="body">
      <div v-if="attachOpen" class="bte-modal" @click.self="attachOpen = false">
        <div class="bte-modal-box">
          <div class="bte-modal-head"><span>{{ attachLabel }}</span><button @click="attachOpen = false">✕</button></div>
          <PartAttachments v-if="attachPartId" :part-id="attachPartId" :part-label="attachLabel" @changed="reload" />
        </div>
      </div>
    </Teleport>

    <!-- 분류/채번 모달 -->
    <BomClassifyModal v-if="classifyPartId" :part-id="classifyPartId" :part-label="classifyLabel"
      @close="classifyPartId = null" @classified="onClassified" />

    <!-- 병합 모달 -->
    <BomMergeModal v-if="mergeSource" :source-part-id="mergeSource.id" :source-label="mergeSource.label"
      @close="mergeSource = null" @merged="onMerged" />

    <!-- 하위 추가 모달 (중복 감지) -->
    <BomAddChildModal v-if="addChild.open" :parent-part-id="addChild.parentPartId" :parent-label="addChild.parentLabel"
      @close="addChild.open = false" @added="onChildAdded" />

    <!-- 실행취소 스낵바 -->
    <Teleport to="body">
      <div v-if="undoItem" class="bte-undo">
        <span>{{ undoItem.label }}</span>
        <button @click="undoLast">↩ 실행취소</button>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, provide, inject, watch, onMounted, onUnmounted } from 'vue'
import { bomApi, type BOMTreeNode } from '@/api/bom'
import { partApi } from '@/api/parts'
import BomNode from './BomNode.vue'
import PartAttachments from './PartAttachments.vue'
import BomClassifyModal from './BomClassifyModal.vue'
import BomMergeModal from './BomMergeModal.vue'
import BomAddChildModal from './BomAddChildModal.vue'

const props = defineProps<{ rootPartId: number; rootLabel: string }>()
const emit = defineEmits<{ (e: 'loaded', nodes: BOMTreeNode[]): void }>()

const nodes = ref<BOMTreeNode[]>([])
const loading = ref(false)
// 편집 화면(팔레트) 등 상위에서 bomDrag를 제공하면 그것을 공유(팔레트↔트리 드래그), 없으면 자체 생성
const injectedDrag = inject<any>('bomDrag', null)
const drag = injectedDrag || ref<any>(null)
if (!injectedDrag) provide('bomDrag', drag)

// ==================== P4: 실행취소/다시실행 스택 ====================
type Op = { label: string; undo: () => Promise<void>; redo: () => Promise<void> }
const undoStack = ref<Op[]>([])
const redoStack = ref<Op[]>([])
const MAX_HISTORY = 50

const undoItem = ref<{ label: string } | null>(null)
let undoTimer: ReturnType<typeof setTimeout> | null = null
function flashUndo(label: string) {
  undoItem.value = { label }
  if (undoTimer) clearTimeout(undoTimer)
  undoTimer = setTimeout(() => { undoItem.value = null }, 6000)
}

async function runOp(op: Op, doFn: () => Promise<void>) {
  try {
    await doFn()
    undoStack.value.push(op)
    if (undoStack.value.length > MAX_HISTORY) undoStack.value.shift()
    redoStack.value = []
    flashUndo(op.label)
    await reload()
  } catch (e: any) {
    alert(e?.response?.data?.detail || '작업 실패(순환/중복 등)')
    await reload()
  }
}
async function undoLast() {
  const op = undoStack.value.pop()
  if (!op) return
  undoItem.value = null
  try { await op.undo(); redoStack.value.push(op) } catch { alert('실행취소에 실패했습니다.') }
  await reload()
}
async function redoLast() {
  const op = redoStack.value.pop()
  if (!op) return
  try { await op.redo(); undoStack.value.push(op) } catch { alert('다시 실행에 실패했습니다.') }
  await reload()
}

// ==================== 저수준 변경 프리미티브(재실행에 안전하도록 부모+자식 기준) ====================
async function _create(parentPartId: number, childPartId: number, qty: number) {
  return (await bomApi.create({ parent_part_id: parentPartId, child_part_id: childPartId, quantity: qty } as any)).data
}
async function _deleteByParts(parentPartId: number, childPartId: number) {
  const kids = (await bomApi.getChildren(parentPartId)).data || []
  const found = kids.find((c: any) => c.child_part_id === childPartId)
  if (found) await bomApi.delete(found.id)
}
async function _setQtyByParts(parentPartId: number, childPartId: number, qty: number) {
  const kids = (await bomApi.getChildren(parentPartId)).data || []
  const found = kids.find((c: any) => c.child_part_id === childPartId)
  if (found) await bomApi.update(found.id, { quantity: qty } as any)
}
// 이동 후 특정 참조 노드 옆으로 정렬(P3)
async function _reorderAdjacent(parentPartId: number, movedBomId: number, refBomId: number, before: boolean) {
  const kids = (await bomApi.getChildren(parentPartId)).data || []
  let ids = kids.map((c: any) => c.id).filter((id: number) => id !== movedBomId)
  const refIdx = ids.indexOf(refBomId)
  if (refIdx < 0) ids.push(movedBomId)
  else ids.splice(before ? refIdx : refIdx + 1, 0, movedBomId)
  await bomApi.updateSortOrders(parentPartId, ids.map((id: number, i: number) => ({ id, sort_order: i })))
}

// ==================== 트리 탐색 헬퍼(검증·부모조회) ====================
function findNodeById(list: BOMTreeNode[], id: number): BOMTreeNode | null {
  for (const n of list) {
    if (n.id === id) return n
    const f = findNodeById(n.children || [], id)
    if (f) return f
  }
  return null
}
function findParentPartId(bomId: number): number {
  function walk(list: BOMTreeNode[], parentPartId: number): number | null {
    for (const n of list) {
      if (n.id === bomId) return parentPartId
      const f = walk(n.children || [], n.part_id)
      if (f !== null) return f
    }
    return null
  }
  return walk(nodes.value, props.rootPartId) ?? props.rootPartId
}
function childrenNodesOfParent(parentPartId: number): BOMTreeNode[] {
  if (parentPartId === props.rootPartId) return nodes.value
  function find(list: BOMTreeNode[]): BOMTreeNode | null {
    for (const n of list) {
      if (n.part_id === parentPartId) return n
      const f = find(n.children || [])
      if (f) return f
    }
    return null
  }
  return find(nodes.value)?.children || []
}
function collectDescendantPartIds(bomId: number): Set<number> {
  const set = new Set<number>()
  const start = findNodeById(nodes.value, bomId)
  if (!start) return set
  const walk = (n: BOMTreeNode) => { set.add(n.part_id); for (const c of n.children || []) walk(c) }
  walk(start)
  return set
}
function childHasPart(parentPartId: number, partId: number, excludeBomId?: number): boolean {
  return childrenNodesOfParent(parentPartId).some(k => k.part_id === partId && k.id !== excludeBomId)
}

// P2: 드롭 전 검증 → 'ok' | 'cycle' | 'merge' | 'self'
function validate(d: any, targetParentPartId: number, targetNodeId: number): string {
  if (!d) return 'none'
  if (d.kind === 'tree-move') {
    if (d.bomId === targetNodeId) return 'self'
    if (collectDescendantPartIds(d.bomId).has(targetParentPartId)) return 'cycle'
    if (childHasPart(targetParentPartId, d.partId, d.bomId)) return 'merge'
    return 'ok'
  }
  if (d.kind === 'palette-add') {
    if (d.partId === targetParentPartId) return 'cycle'
    if (childHasPart(targetParentPartId, d.partId)) return 'merge'
    return 'ok'
  }
  return 'ok' // palette-add-multi 등은 개별 처리
}

// ==================== 고수준 편집 동작 ====================
// 팔레트 기존 부품 추가(같은 부모 중복이면 수량 합산). refBomId 지정 시 그 옆으로 정렬(P3)
async function addExisting(parentPartId: number, childPartId: number, name?: string, refBomId?: number, before?: boolean) {
  const kids = (await bomApi.getChildren(parentPartId)).data || []
  const existing = kids.find((c: any) => c.child_part_id === childPartId)
  if (existing) {
    const oldQty = Number(existing.quantity)
    const newQty = oldQty + 1
    await runOp(
      { label: `'${name || '부품'}' 수량 합침 (${oldQty}→${newQty})`,
        undo: () => _setQtyByParts(parentPartId, childPartId, oldQty),
        redo: () => _setQtyByParts(parentPartId, childPartId, newQty) },
      () => _setQtyByParts(parentPartId, childPartId, newQty)
    )
  } else {
    await runOp(
      { label: `'${name || '부품'}' 추가`,
        undo: () => _deleteByParts(parentPartId, childPartId),
        redo: () => _create(parentPartId, childPartId, 1).then(() => undefined) },
      async () => {
        const created = await _create(parentPartId, childPartId, 1)
        if (refBomId) await _reorderAdjacent(parentPartId, created.id, refBomId, !!before)
      }
    )
  }
}
// 여러 부품 일괄 추가(P3 다중선택 드롭)
async function addMany(parentPartId: number, items: Array<{ partId: number; name?: string }>) {
  for (const it of items) await addExisting(parentPartId, it.partId, it.name)
}

async function reparent(bomId: number, newParentPartId: number, refBomId?: number, before?: boolean) {
  const oldParentPartId = findParentPartId(bomId)
  await runOp(
    { label: '이동',
      undo: () => bomApi.move(bomId, oldParentPartId).then(() => undefined),
      redo: () => bomApi.move(bomId, newParentPartId).then(() => undefined) },
    async () => {
      await bomApi.move(bomId, newParentPartId)
      if (refBomId && refBomId !== bomId) await _reorderAdjacent(newParentPartId, bomId, refBomId, !!before)
    }
  )
}

// 부품 이름 변경(트리에서 인라인) — 부품 자체 속성이라 partApi.update
async function renamePart(partId: number, name: string) {
  try { await partApi.update(partId, { part_name: name } as any); await reload() }
  catch (e: any) { alert(e?.response?.data?.detail || '이름 변경 실패') }
}

async function updateQty(bomId: number, qty: number) {
  const cur = findNodeById(nodes.value, bomId)
  const oldQty = cur ? Number(cur.quantity) : qty
  await runOp(
    { label: `수량 변경 (${oldQty}→${qty})`,
      undo: () => bomApi.update(bomId, { quantity: oldQty } as any).then(() => undefined),
      redo: () => bomApi.update(bomId, { quantity: qty } as any).then(() => undefined) },
    () => bomApi.update(bomId, { quantity: qty } as any).then(() => undefined)
  )
}

async function remove(node: BOMTreeNode) {
  if (!confirm(`'${node.part_name || node.part_number}' 연결을 삭제하시겠습니까? (부품 자체는 유지)`)) return
  const parentPartId = findParentPartId(node.id)
  const childPartId = node.part_id
  const qty = Number(node.quantity)
  await runOp(
    { label: `'${node.part_name || node.part_number}' 삭제`,
      undo: () => _create(parentPartId, childPartId, qty).then(() => undefined),
      redo: () => _deleteByParts(parentPartId, childPartId) },
    () => bomApi.delete(node.id).then(() => undefined)
  )
}

// 하위 추가 모달 상태(중복 감지 지원) — 새 부품 생성 경로라 실행취소 스택 미포함
const addChild = ref<{ open: boolean; parentPartId: number; parentLabel: string }>({ open: false, parentPartId: 0, parentLabel: '' })
function addUnder(parentPartId: number, parentLabel: string) {
  addChild.value = { open: true, parentPartId, parentLabel }
}
function onChildAdded() { addChild.value.open = false; reload() }

// 우측 상단 '+ 하위 추가'용 활성 선택: 트리에서 부품(또는 최상위)을 클릭하면 활성화되고, 그 하위로 추가
const activeNode = ref<{ bomId?: number; partId: number; label: string } | null>(null)
function selectActive(node: BOMTreeNode) {
  if (activeNode.value?.bomId === node.id) { activeNode.value = null; return } // 다시 클릭 = 해제
  activeNode.value = { bomId: node.id, partId: node.part_id, label: node.is_classified === false ? (node.part_name || '미분류 부품') : (node.part_number_display || node.part_number) }
}
function selectRoot() {
  if (activeNode.value && !activeNode.value.bomId) { activeNode.value = null; return }
  activeNode.value = { partId: props.rootPartId, label: props.rootLabel }
}
provide('bomActive', { current: activeNode, select: selectActive })
function addSelectedChild() {
  if (!activeNode.value) return
  addUnder(activeNode.value.partId, activeNode.value.label)
}

// 묶기 다중선택
const selectMode = ref(false)
const selected = ref<Set<number>>(new Set())
function toggleSel(bomId: number) {
  const s = new Set(selected.value)
  s.has(bomId) ? s.delete(bomId) : s.add(bomId)
  selected.value = s
}
provide('bomSelect', { mode: selectMode, has: (id: number) => selected.value.has(id), toggle: toggleSel })
function toggleSelectMode() { selectMode.value = !selectMode.value; if (!selectMode.value) selected.value = new Set() }
function clearSelection() { selected.value = new Set() }

const mergeSource = ref<{ id: number; label: string } | null>(null)
const attachOpen = ref(false)
const attachPartId = ref<number | null>(null)
const attachLabel = ref('')
const classifyPartId = ref<number | null>(null)
const classifyLabel = ref('')

function openAttach(node: BOMTreeNode) { attachPartId.value = node.part_id; attachLabel.value = node.part_number_display || node.part_number; attachOpen.value = true }
function classify(node: BOMTreeNode) { classifyPartId.value = node.part_id; classifyLabel.value = node.part_name || node.part_number }
function onClassified() { classifyPartId.value = null; reload() }
function merge(node: BOMTreeNode) { mergeSource.value = { id: node.part_id, label: node.part_number_display || node.part_number } }
function onMerged() { mergeSource.value = null; reload() }

async function doGroupUnder() {
  if (selected.value.size === 0) return
  const name = prompt('새 상위(어셈블리) 부품명을 입력하세요 (미분류로 생성, 선택 항목이 그 밑으로 이동):')
  if (!name || !name.trim()) return
  try {
    const p = (await partApi.createMinimal(name.trim())).data
    await bomApi.groupUnder(Array.from(selected.value), p.id)
    selected.value = new Set(); selectMode.value = false
    await reload()
  } catch (e: any) { alert(e?.response?.data?.detail || '묶기 실패') }
}

provide('bomHandlers', {
  reparent, updateQty,
  addChild: (n: BOMTreeNode) => addUnder(n.part_id, n.part_number_display || n.part_number),
  remove, openAttach, classify, merge, addExisting, addMany, validate, rename: renamePart,
})

// 단축키: 선택된 노드 기준 Insert=하위추가, Delete=연결삭제 (입력 중일 땐 무시)
function onKeydown(e: KeyboardEvent) {
  const t = e.target as HTMLElement
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
  if (!activeNode.value) return
  if (e.key === 'Insert') { e.preventDefault(); addSelectedChild() }
  else if (e.key === 'Delete') {
    if (activeNode.value.bomId) {
      const n = findNodeById(nodes.value, activeNode.value.bomId)
      if (n) { e.preventDefault(); remove(n) }
    }
  }
}

function onRootDrop() {
  const d = drag.value
  if (!d) return
  if (d.kind === 'palette-add') { addExisting(props.rootPartId, d.partId, d.name); drag.value = null; return }
  if (d.kind === 'palette-add-multi') { addMany(props.rootPartId, d.items || []); drag.value = null; return }
  reparent(d.bomId, props.rootPartId); drag.value = null
}

// ==================== 외부 변경 감지(경량 폴링) ====================
const externalChanged = ref(false)
const expectedHash = ref('')
function treeHash(list: BOMTreeNode[]): string {
  return (list || []).map(n => `${n.id}:${n.quantity}:[${treeHash(n.children || [])}]`).join(',')
}
let pollTimer: ReturnType<typeof setInterval> | null = null
async function checkExternal() {
  if (loading.value || document.hidden) return
  try {
    const remote = (await bomApi.getTree(props.rootPartId)).data || []
    if (treeHash(remote) !== expectedHash.value) externalChanged.value = true
  } catch { /* 무시 */ }
}
function reloadClearExt() { externalChanged.value = false; reload() }

async function reload() {
  loading.value = true
  try { nodes.value = (await bomApi.getTree(props.rootPartId)).data || [] }
  catch { nodes.value = [] }
  finally {
    loading.value = false
    expectedHash.value = treeHash(nodes.value)
    externalChanged.value = false
    emit('loaded', nodes.value)
  }
}

// 편집 화면(더블클릭 배치 등)에서 직접 호출할 수 있도록 노출
defineExpose({ addExisting, addMany, reload })

onMounted(() => { pollTimer = setInterval(checkExternal, 20000); document.addEventListener('keydown', onKeydown) })
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer); if (undoTimer) clearTimeout(undoTimer); document.removeEventListener('keydown', onKeydown) })
watch(() => props.rootPartId, reload, { immediate: true })
</script>

<style scoped>
.bte { border: 1px solid #e5e7eb; border-radius: 12px; background: #fff; }
.bte-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 12px 14px; border-bottom: 1px solid #eef1f5; position: sticky; top: 0; z-index: 6; background: #fff; border-radius: 12px 12px 0 0; }
.bte-title { font-size: 14px; color: #111827; font-weight: 500; }
.bte-root { cursor: pointer; padding: 1px 6px; border-radius: 6px; border: 1px solid transparent; }
.bte-root:hover { background: #f5f3ff; }
.bte-root-sel { background: #ede9fe; border-color: #7c3aed; color: #6d28d9; }
.bte-sub { font-size: 11.5px; color: #6b7280; font-weight: 400; margin-left: 6px; }
.bte-actions { display: flex; gap: 6px; }
.bte-btn { border: 1px solid #d1d5db; border-radius: 7px; padding: 5px 11px; font-size: 12.5px; background: #fff; cursor: pointer; }
.bte-btn:disabled { opacity: 0.4; cursor: default; }
.bte-ic { padding: 5px 9px; font-size: 14px; line-height: 1; }
.bte-btn-p { border-color: #2563eb; color: #2563eb; }
.bte-btn-sel { border-color: #7c3aed; background: #7c3aed; color: #fff; }
.bte-ext { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 8px 14px; background: #fff7ed; border-bottom: 1px solid #fed7aa; font-size: 12.5px; color: #b45309; }
.bte-selbar { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 8px 14px; background: #f5f3ff; border-bottom: 1px solid #e9e5fb; font-size: 12.5px; color: #6d28d9; }
.bte-selbar > div { display: flex; gap: 6px; }
.bte-body { padding: 10px 8px 4px; }
.bte-empty { text-align: center; color: #9ca3af; padding: 26px 0; font-size: 13px; }
.bte-tree { min-height: 40px; }
.bte-hint { font-size: 12px; color: #5b6675; padding: 8px 10px 10px; margin: 0; }
.bte-modal { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 70; display: flex; align-items: center; justify-content: center; padding: 20px; }
.bte-modal-box { background: #fff; border-radius: 12px; width: 100%; max-width: 560px; max-height: 82vh; overflow: auto; padding: 16px; }
.bte-modal-head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; margin-bottom: 12px; }
.bte-modal-head button { border: none; background: none; cursor: pointer; font-size: 16px; color: #6b7280; }
.bte-undo { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); z-index: 90; background: #1f2937; color: #fff; border-radius: 10px; padding: 10px 14px; display: flex; align-items: center; gap: 14px; font-size: 13px; box-shadow: 0 8px 24px rgba(0,0,0,.25); }
.bte-undo button { background: none; border: none; color: #a5b4fc; font-weight: 700; cursor: pointer; font-size: 13px; }
.bte-undo button:hover { color: #c7d2fe; }
</style>
