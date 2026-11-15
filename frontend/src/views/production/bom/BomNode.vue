<template>
  <div class="bn-wrap">
    <div class="bn-row" :class="{ 'bn-dragging': dragging, 'bn-active': isActive }" :style="rowStyle"
      draggable="true"
      @click="onRowClick"
      @dragstart.stop="onDragStart" @dragend="onDragEnd"
      @dragover.prevent="onDragOver" @dragleave="onDragLeave" @drop.stop.prevent="onDrop">
      <input v-if="sel?.mode?.value" type="checkbox" class="bn-chk" :checked="sel.has(node.id)" @change="sel.toggle(node.id)" @click.stop />
      <span class="bn-grip" title="드래그하여 이동">⋮⋮</span>
      <button class="bn-tog" @click.stop="open = !open" :style="{ visibility: hasChildren ? 'visible' : 'hidden' }">{{ open ? '▾' : '▸' }}</button>
      <span v-if="node.level_code" class="bn-lv" :style="{ background: lvColor.bg, color: lvColor.fg }" :title="'레벨 ' + node.level_code">{{ node.level_code }}</span>
      <span class="bn-num">{{ displayNum }}</span>
      <input v-if="editingName" ref="nameInput" v-model="nameVal" class="bn-nameedit"
        @keyup.enter="saveName" @keyup.escape="editingName = false" @blur="saveName" @click.stop @dblclick.stop />
      <span v-else class="bn-name" @dblclick.stop="startName" title="더블클릭하여 이름 변경">{{ node.part_name || node.description || '' }}</span>
      <span v-if="node.is_classified === false" class="bn-b bn-unc" title="미분류(코드·레벨 미부여)">미분류</span>
      <span v-if="(node.attachment_count || 0) > 0" class="bn-b bn-att" @click.stop="H.openAttach(node)">📎 {{ node.attachment_count }}</span>

      <span class="bn-qty" v-if="!editingQty" @click.stop="startQty" title="클릭하여 수량 수정">×{{ fmt(node.quantity) }}<small v-if="node.unit_name"> {{ node.unit_name }}</small></span>
      <span class="bn-qty-edit" v-else @click.stop>
        <input ref="qtyInput" v-model.number="qtyVal" type="number" min="1" step="1" class="bn-qi"
          @keyup.enter="saveQty" @blur="saveQty" />
      </span>

      <span class="bn-menu" @click.stop>
        <button class="bn-mbtn" @click="menu = !menu">⋯</button>
        <div v-if="menu" class="bn-drop-menu" @mouseleave="menu = false">
          <button @click="act(() => H.addChild(node))">+ 하위 추가</button>
          <button @click="act(startName)">✏ 이름 변경</button>
          <button @click="act(() => H.openAttach(node))">📎 첨부</button>
          <button v-if="node.is_classified === false" @click="act(() => H.classify(node))">🏷 분류/채번</button>
          <button @click="act(() => H.merge(node))">🔀 다른 부품과 병합</button>
          <button class="bn-del" @click="act(() => H.remove(node))">✕ 이 연결 삭제</button>
        </div>
      </span>
    </div>
    <div v-if="open && hasChildren">
      <BomNode v-for="c in node.children" :key="c.id" :node="c" :depth="depth + 1" :parent-part-id="node.part_id" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, nextTick } from 'vue'
import type { BOMTreeNode } from '@/api/bom'

// parentPartId: 이 노드가 매달린 상위 부품 id(형제로 드롭할 때의 대상 부모)
const props = defineProps<{ node: BOMTreeNode; depth: number; parentPartId: number }>()
const H = inject<any>('bomHandlers')
const drag = inject<any>('bomDrag')
const sel = inject<any>('bomSelect')
const active = inject<any>('bomActive', null)
const isActive = computed(() => active?.current?.value?.bomId === props.node.id)
function onRowClick() { active?.select(props.node) }
// 미분류(품번 미부여)는 고유ID 대신 공백 표시
const displayNum = computed(() => props.node.is_classified === false ? '' : (props.node.part_number_display || props.node.part_number))

// 레벨코드별 배경색(제품 편집 단계 시각 구분)
const LEVEL_COLORS: Record<string, [string, string]> = {
  M: ['#fef9c3', '#854d0e'], O: ['#ffedd5', '#9a3412'], R: ['#dcfce7', '#166534'],
  C: ['#dbeafe', '#1e40af'], S: ['#e0e7ff', '#3730a3'], P: ['#fce7f3', '#9d174d'],
  K: ['#cffafe', '#155e75'], F: ['#fee2e2', '#991b1b'], U: ['#f3e8ff', '#6b21a8'],
}
const lvColor = computed(() => {
  const c = LEVEL_COLORS[props.node.level_code || '']
  return c ? { bg: c[0], fg: c[1] } : { bg: '#eef2f7', fg: '#475569' }
})

// 이름 변경(인라인)
const editingName = ref(false)
const nameVal = ref('')
const nameInput = ref<HTMLInputElement | null>(null)
async function startName() {
  editingName.value = true
  nameVal.value = props.node.part_name || ''
  await nextTick(); nameInput.value?.focus(); nameInput.value?.select()
}
function saveName() {
  if (!editingName.value) return
  editingName.value = false
  const nm = nameVal.value.trim()
  if (nm && nm !== props.node.part_name) H.rename(props.node.part_id, nm)
}

const open = ref(true)
const menu = ref(false)
const editingQty = ref(false)
const qtyVal = ref<number>(props.node.quantity)
const qtyInput = ref<HTMLInputElement | null>(null)
const dropTarget = ref(false)
const dropPos = ref<'into' | 'sib-top' | 'sib-bottom'>('into')
const dropStatus = ref<'ok' | 'cycle' | 'merge' | 'self' | 'none'>('none')

const hasChildren = computed(() => (props.node.children || []).length > 0)
const dragging = computed(() => drag.value?.kind === 'tree-move' && drag.value?.bomId === props.node.id)

// 드롭 미리보기 색: ok=파랑, merge=주황, cycle=빨강
const dropColor = computed(() => dropStatus.value === 'cycle' ? '#dc2626' : dropStatus.value === 'merge' ? '#d97706' : '#2563eb')
const dropTint = computed(() => dropStatus.value === 'cycle' ? '#fee2e2' : dropStatus.value === 'merge' ? '#fef3c7' : '#e0edff')
const rowStyle = computed(() => {
  const base: Record<string, string> = { paddingLeft: (props.depth * 20 + 6) + 'px' }
  if (dropTarget.value && dropStatus.value !== 'self' && dropStatus.value !== 'none') {
    if (dropPos.value === 'into') { base.background = dropTint.value; base.outline = `2px dashed ${dropColor.value}`; base.outlineOffset = '-2px' }
    else if (dropPos.value === 'sib-top') base.boxShadow = `inset 0 3px 0 -1px ${dropColor.value}`
    else base.boxShadow = `inset 0 -3px 0 -1px ${dropColor.value}`
  }
  return base
})

function fmt(n: number) { return String(Math.round(Number(n || 0))) }  // 수량은 자연수 표시

function onDragStart(e: DragEvent) {
  drag.value = { kind: 'tree-move', bomId: props.node.id, partId: props.node.part_id, name: props.node.part_name }
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
}
function onDragEnd() { drag.value = null; dropTarget.value = false }

function onDragOver(e: DragEvent) {
  const d = drag.value
  if (!d) return
  const el = e.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  const ratio = (e.clientY - rect.top) / rect.height
  if (ratio < 0.28) dropPos.value = 'sib-top'
  else if (ratio > 0.72) dropPos.value = 'sib-bottom'
  else dropPos.value = 'into'
  const targetParent = dropPos.value === 'into' ? props.node.part_id : props.parentPartId
  dropStatus.value = H.validate(d, targetParent, props.node.id)
  dropTarget.value = dropStatus.value !== 'self'
}
function onDragLeave() { dropTarget.value = false }

function onDrop() {
  const d = drag.value
  const pos = dropPos.value
  const status = dropStatus.value
  dropTarget.value = false
  if (!d || status === 'self') { return }
  if (status === 'cycle') { alert('순환 구조가 되어 이 위치에는 추가할 수 없습니다.'); drag.value = null; return }

  const targetParent = pos === 'into' ? props.node.part_id : props.parentPartId
  const refBomId = pos === 'into' ? undefined : props.node.id
  const before = pos === 'sib-top'

  if (d.kind === 'palette-add-multi') {
    H.addMany(targetParent, d.items || [])
  } else if (d.kind === 'palette-add') {
    H.addExisting(targetParent, d.partId, d.name, refBomId, before)
  } else {
    if (d.bomId === props.node.id) { drag.value = null; return }
    H.reparent(d.bomId, targetParent, refBomId, before)
  }
  drag.value = null
}

async function startQty() { editingQty.value = true; qtyVal.value = props.node.quantity; await nextTick(); qtyInput.value?.focus() }
function saveQty() {
  if (!editingQty.value) return
  editingQty.value = false
  let v = Math.round(Number(qtyVal.value))  // 자연수로 강제(소수점 제거)
  if (isNaN(v) || v < 1) v = 1
  if (v !== props.node.quantity) H.updateQty(props.node.id, v)
}
function act(fn: () => void) { menu.value = false; fn() }
</script>

<style scoped>
.bn-row { display: flex; align-items: center; gap: 7px; padding: 5px 8px; border-radius: 7px; font-size: 13px; position: relative; }
.bn-row:hover { background: #f7f9fc; }
.bn-active { background: #ede9fe !important; box-shadow: inset 3px 0 0 0 #7c3aed; }
.bn-dragging { opacity: 0.45; }
.bn-chk { width: 15px; height: 15px; accent-color: #7c3aed; cursor: pointer; }
.bn-grip { cursor: grab; color: #cbd5e1; font-size: 11px; user-select: none; }
.bn-tog { border: none; background: none; cursor: pointer; color: #64748b; width: 16px; }
.bn-lv { font-size: 10px; font-weight: 800; border-radius: 5px; padding: 1px 6px; letter-spacing: .02em; }
.bn-num { font-family: ui-monospace, Consolas, monospace; font-size: 12px; color: #0f172a; font-weight: 600; }
.bn-name { color: #111827; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px; }
.bn-nameedit { border: 1px solid #7c3aed; border-radius: 5px; padding: 2px 6px; font-size: 13px; min-width: 180px; }
.bn-b { font-size: 10px; font-weight: 700; border-radius: 5px; padding: 1px 6px; cursor: default; }
.bn-unc { background: #fdeede; color: #b45309; }
.bn-att { background: #e0edff; color: #1d4ed8; cursor: pointer; }
.bn-qty { margin-left: auto; font-variant-numeric: tabular-nums; color: #1f2937; cursor: pointer; padding: 1px 6px; border-radius: 5px; }
.bn-qty:hover { background: #eef2f7; }
.bn-qty small { color: #9ca3af; }
.bn-qty-edit { margin-left: auto; }
.bn-qi { width: 70px; border: 1px solid #2563eb; border-radius: 5px; padding: 2px 5px; font-size: 12px; }
.bn-menu { position: relative; }
.bn-mbtn { border: none; background: none; cursor: pointer; color: #6b7280; font-size: 15px; padding: 0 4px; }
.bn-drop-menu { position: absolute; right: 0; top: 22px; z-index: 30; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 6px 20px rgba(0,0,0,.12); display: flex; flex-direction: column; min-width: 130px; padding: 4px; }
.bn-drop-menu button { text-align: left; border: none; background: none; padding: 6px 9px; font-size: 12.5px; border-radius: 5px; cursor: pointer; color: #374151; }
.bn-drop-menu button:hover { background: #f3f4f6; }
.bn-del { color: #dc2626 !important; }
</style>
