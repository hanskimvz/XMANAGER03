<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[70] bg-black/50 flex items-start justify-center overflow-y-auto py-6">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4">
        <div class="flex items-center justify-between px-5 py-3 border-b">
          <div>
            <h3 class="text-base font-bold">📦 박스 분할계획 — {{ pr.request_number }}</h3>
            <p class="text-xs text-gray-500 mt-0.5">
              영업이 "N개씩 몇 박스"로 나눠 작성 → 생산팀이 보고 포장 → 박스별로 CI를 발행합니다.
            </p>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        <div class="px-5 py-4 max-h-[70vh] overflow-y-auto">
          <!-- 품목별 배정 요약 -->
          <div class="mb-4 rounded-lg border bg-gray-50 p-3">
            <div class="text-xs font-semibold text-gray-600 mb-2">품목별 배정 현황</div>
            <table class="min-w-full text-xs">
              <thead>
                <tr class="text-gray-400">
                  <th class="text-left py-1">품번</th>
                  <th class="text-right py-1 w-20">요청</th>
                  <th class="text-right py-1 w-20">배정</th>
                  <th class="text-right py-1 w-20">잔여</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="it in prItems" :key="it.id" class="border-t border-gray-200">
                  <td class="py-1 font-mono text-gray-700 truncate max-w-[240px]">{{ itemCode(it) }}</td>
                  <td class="py-1 text-right tabular-nums">{{ fmt(it.requested_quantity) }}</td>
                  <td class="py-1 text-right tabular-nums">{{ fmt(assigned(it.id)) }}</td>
                  <td class="py-1 text-right tabular-nums font-medium"
                    :class="remaining(it.id) < 0 ? 'text-red-600' : remaining(it.id) === 0 ? 'text-green-600' : 'text-amber-600'">
                    {{ fmt(remaining(it.id)) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 자동 분할 생성 -->
          <div class="mb-4 flex flex-wrap items-end gap-2 rounded-lg border border-blue-200 bg-blue-50/50 p-3">
            <div>
              <label class="block text-[11px] text-gray-500 mb-0.5">품목</label>
              <select v-model.number="autoItemId" class="border rounded px-2 py-1 text-sm bg-white">
                <option v-for="it in prItems" :key="it.id" :value="it.id">{{ itemCode(it) }}</option>
              </select>
            </div>
            <div>
              <label class="block text-[11px] text-gray-500 mb-0.5">박스당 수량</label>
              <input v-model.number="autoPerBox" type="number" min="1" step="1"
                class="w-24 border rounded px-2 py-1 text-sm" placeholder="예: 10" />
            </div>
            <button @click="autoSplit"
              class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">➕ 자동 분할</button>
            <span class="text-[11px] text-gray-500">잔여 {{ fmt(remaining(autoItemId)) }} 개를 박스당 {{ autoPerBox || '?' }}개로 나눕니다.</span>
          </div>

          <!-- 박스 목록 -->
          <div v-if="!boxes.length" class="py-8 text-center text-gray-400 text-sm">
            아직 박스가 없습니다. 위에서 자동 분할하거나 아래 버튼으로 박스를 추가하세요.
          </div>
          <div v-else class="space-y-3">
            <div v-for="(box, bi) in boxes" :key="bi" class="rounded-lg border p-3"
              :class="box.ci_number ? 'border-green-200 bg-green-50/40' : ''">
              <div class="flex items-center justify-between mb-2">
                <div class="text-sm font-semibold text-gray-700">
                  박스 {{ bi + 1 }}
                  <span v-if="box.ci_number" class="ml-2 text-[10px] rounded bg-green-100 text-green-700 px-1.5 py-0.5">✓ CI 발행됨 · {{ box.ci_number }}</span>
                </div>
                <button v-if="!box.ci_number" @click="removeBox(bi)" class="text-xs text-red-500 hover:text-red-700">박스 삭제</button>
                <span v-else class="text-[10px] text-gray-400">발행 후 수정 불가</span>
              </div>
              <table class="min-w-full text-sm mb-2">
                <tbody>
                  <tr v-for="(ln, li) in box.items" :key="li" class="border-b last:border-0">
                    <td class="py-1">
                      <select v-model.number="ln.pr_item_id" @change="onLineItemChange(ln)" :disabled="!!box.ci_number"
                        class="border rounded px-1.5 py-1 text-xs bg-white max-w-[240px] disabled:bg-gray-100">
                        <option v-for="it in prItems" :key="it.id" :value="it.id">{{ itemCode(it) }}</option>
                      </select>
                    </td>
                    <td class="py-1 text-right w-28">
                      <input v-model.number="ln.quantity" type="number" min="0" step="1" :disabled="!!box.ci_number"
                        class="w-24 border rounded px-1.5 py-1 text-sm text-right disabled:bg-gray-100" />
                    </td>
                    <td class="py-1 text-right w-10">
                      <button v-if="!box.ci_number" @click="box.items.splice(li, 1)" class="text-gray-400 hover:text-red-600 text-xs">✕</button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div class="flex items-center gap-2">
                <button v-if="!box.ci_number" @click="addLine(box)" class="text-xs text-blue-600 hover:text-blue-800">+ 품목 추가</button>
                <input v-model="box.remarks" placeholder="비고(포장 지시 등)" :disabled="!!box.ci_number"
                  class="flex-1 border rounded px-2 py-1 text-xs disabled:bg-gray-100" />
              </div>
            </div>
          </div>

          <button @click="addBox" class="mt-3 px-3 py-1.5 text-sm border border-dashed border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 w-full">
            + 빈 박스 추가
          </button>

          <p v-if="overAssigned" class="mt-3 text-xs text-red-600">⚠ 배정 수량이 요청 수량을 초과한 품목이 있습니다. 확인 후 저장하세요.</p>
        </div>

        <div class="flex items-center justify-between gap-2 px-5 py-3 border-t bg-gray-50">
          <button @click="clearPlan" :disabled="saving"
            class="px-3 py-2 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50">계획 해제</button>
          <div class="flex items-center gap-2">
            <button @click="$emit('close')" class="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-100">취소</button>
            <button @click="save" :disabled="saving"
              class="px-4 py-2 text-sm bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50">
              {{ saving ? '저장 중…' : '💾 저장' }} ({{ effectiveBoxes.length }}박스)
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { productionRequestApi, type ProductionRequest, type ProductionRequestItem, type BoxPlanBox } from '@/api/productionRequest'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ pr: ProductionRequest }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'saved', pr: ProductionRequest): void }>()
const { showToast } = useToast()

const prItems = computed<ProductionRequestItem[]>(() => props.pr.items || [])

type Line = { pr_item_id: number | null; product_code: string | null; quantity: number }
type Box = { box_no: number; items: Line[]; remarks: string; ci_document_id?: number | null; ci_number?: string | null }

// 기존 계획 로드(깊은 복제)
const boxes = ref<Box[]>(
  (props.pr.box_plan || []).map((b) => ({
    box_no: b.box_no,
    items: (b.items || []).map((l) => ({ pr_item_id: l.pr_item_id ?? null, product_code: l.product_code ?? null, quantity: Number(l.quantity) || 0 })),
    remarks: b.remarks || '',
    ci_document_id: b.ci_document_id ?? null,
    ci_number: b.ci_number ?? null,
  }))
)

const autoItemId = ref<number | null>(prItems.value[0]?.id ?? null)
const autoPerBox = ref<number | null>(null)
const saving = ref(false)

function fmt(n: number | null | undefined): string {
  if (n == null) return '-'
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: 3 })
}
function itemById(id: number | null | undefined): ProductionRequestItem | undefined {
  return prItems.value.find((it) => it.id === id)
}
function itemCode(it: ProductionRequestItem | undefined): string {
  if (!it) return '(품목)'
  return (it.product_part?.part_number_display || it.product_part?.part_number || it.custom_product_code || '(품목)') as string
}
function assigned(prItemId: number | null): number {
  if (prItemId == null) return 0
  let sum = 0
  for (const b of boxes.value) for (const l of b.items) if (l.pr_item_id === prItemId) sum += Number(l.quantity) || 0
  return sum
}
function remaining(prItemId: number | null): number {
  const it = itemById(prItemId)
  if (!it) return 0
  return (Number(it.requested_quantity) || 0) - assigned(prItemId)
}
const overAssigned = computed(() => prItems.value.some((it) => remaining(it.id) < -1e-9))

function autoSplit() {
  const it = itemById(autoItemId.value)
  if (!it) { showToast('품목을 선택하세요', 'warning'); return }
  const per = Number(autoPerBox.value) || 0
  if (per <= 0) { showToast('박스당 수량을 입력하세요', 'warning'); return }
  let rem = remaining(it.id)
  if (rem <= 0) { showToast('잔여 수량이 없습니다', 'warning'); return }
  while (rem > 1e-9) {
    const q = Math.min(per, rem)
    boxes.value.push({ box_no: boxes.value.length + 1, items: [{ pr_item_id: it.id, product_code: itemCode(it), quantity: q }], remarks: '' })
    rem -= q
  }
}
function addBox() {
  boxes.value.push({ box_no: boxes.value.length + 1, items: [], remarks: '' })
}
function removeBox(bi: number) {
  boxes.value.splice(bi, 1)
}
function addLine(box: Box) {
  // 아직 이 박스에 없는 첫 품목을 기본값으로
  const used = new Set(box.items.map((l) => l.pr_item_id))
  const cand = prItems.value.find((it) => !used.has(it.id)) || prItems.value[0]
  if (!cand) return
  box.items.push({ pr_item_id: cand.id, product_code: itemCode(cand), quantity: Math.max(0, remaining(cand.id)) })
}
function onLineItemChange(ln: Line) {
  ln.product_code = itemCode(itemById(ln.pr_item_id))
}

// 저장 대상: 라인이 있고 수량>0인 박스만, 번호 재정렬
const effectiveBoxes = computed<BoxPlanBox[]>(() =>
  boxes.value
    .map((b) => ({
      items: b.items.filter((l) => (Number(l.quantity) || 0) > 0).map((l) => ({ pr_item_id: l.pr_item_id, product_code: l.product_code, quantity: Number(l.quantity) })),
      remarks: b.remarks?.trim() || null,
      ci_document_id: b.ci_document_id ?? null,
      ci_number: b.ci_number ?? null,
    }))
    .filter((b) => b.items.length > 0)
    .map((b, i) => ({ box_no: i + 1, items: b.items, remarks: b.remarks, ci_document_id: b.ci_document_id, ci_number: b.ci_number }))
)

async function save() {
  if (overAssigned.value) {
    const ok = window.confirm('요청 수량을 초과한 품목이 있습니다. 그래도 저장할까요?')
    if (!ok) return
  }
  saving.value = true
  try {
    const updated = await productionRequestApi.updateBoxPlan(props.pr.id, effectiveBoxes.value.length ? effectiveBoxes.value : null)
    showToast('박스 분할계획을 저장했습니다', 'success')
    emit('saved', updated)
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '저장에 실패했습니다', 'error')
  } finally {
    saving.value = false
  }
}
async function clearPlan() {
  if (!window.confirm('박스 분할계획을 삭제할까요?')) return
  saving.value = true
  try {
    const updated = await productionRequestApi.updateBoxPlan(props.pr.id, null)
    showToast('박스 분할계획을 해제했습니다', 'success')
    emit('saved', updated)
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '삭제에 실패했습니다', 'error')
  } finally {
    saving.value = false
  }
}
</script>
