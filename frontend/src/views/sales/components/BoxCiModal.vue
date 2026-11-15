<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[70] bg-black/50 flex items-start justify-center overflow-y-auto py-6">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4">
        <div class="flex items-center justify-between px-5 py-3 border-b">
          <div>
            <h3 class="text-base font-bold">📦 박스별 CI 발행 — {{ pr.request_number }}</h3>
            <p class="text-xs text-gray-500 mt-0.5">
              박스 1개당 CI 1건을 발행합니다. 내용물은 박스 품목·수량, 배송비는 박스당 운임(견적/PI)이 적용됩니다.
            </p>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        <div class="px-5 py-4 max-h-[70vh] overflow-y-auto">
          <div class="mb-3 flex flex-wrap items-center gap-3">
            <label class="text-xs text-gray-600">문서일(발행일)
              <input v-model="docDate" type="date" class="ml-1 border rounded px-2 py-1 text-sm" />
            </label>
            <span class="ml-auto text-sm text-gray-600">
              발행 <b>{{ issuedCount }}</b> / 전체 {{ boxes.length }} · 잔여 <b class="text-amber-600">{{ boxes.length - issuedCount }}</b>박스
            </span>
          </div>

          <div v-if="!boxes.length" class="py-8 text-center text-gray-400 text-sm">
            박스 분할계획이 없습니다. 먼저 "📦 박스계획"에서 작성하세요.
          </div>

          <div v-else class="space-y-2">
            <div v-for="box in boxes" :key="box.box_no"
              class="rounded-lg border p-3 flex items-start gap-3"
              :class="box.ci_number ? 'border-green-200 bg-green-50/40' : ''">
              <div class="text-sm font-bold text-gray-700 w-12 shrink-0">#{{ box.box_no }}</div>
              <div class="flex-1 min-w-0">
                <div v-for="(ln, li) in box.items" :key="li" class="text-sm whitespace-nowrap">
                  <span class="font-mono text-gray-800">{{ ln.product_code || codeOf(ln) }}</span>
                  <span class="mx-1 text-gray-400">×</span>
                  <span class="tabular-nums font-medium">{{ ln.quantity }}</span>
                </div>
                <div v-if="box.remarks" class="text-[11px] text-gray-400 mt-0.5">{{ box.remarks }}</div>
              </div>
              <div class="shrink-0">
                <span v-if="box.ci_number" class="inline-block text-[11px] rounded bg-green-100 text-green-700 px-2 py-1">✓ {{ box.ci_number }}</span>
                <button v-else @click="issue(box)" :disabled="busyBox === box.box_no"
                  class="px-3 py-1.5 text-xs bg-teal-600 text-white rounded hover:bg-teal-700 disabled:opacity-50 whitespace-nowrap">
                  {{ busyBox === box.box_no ? '발행 중…' : '📄 CI 발행' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 px-5 py-3 border-t bg-gray-50">
          <button @click="$emit('close')" class="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-100">닫기</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { productionRequestApi, type ProductionRequest, type BoxPlanBox, type BoxPlanLine } from '@/api/productionRequest'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ pr: ProductionRequest }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'issued'): void }>()
const { showToast } = useToast()

const boxes = ref<BoxPlanBox[]>((props.pr.box_plan || []).map((b) => ({ ...b, items: [...(b.items || [])] })))
const docDate = ref(todayStr())
const busyBox = ref<number | null>(null)

const issuedCount = computed(() => boxes.value.filter((b) => !!b.ci_number).length)

function todayStr(): string {
  const d = new Date()
  const p = (x: number) => String(x).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}
function codeOf(ln: BoxPlanLine): string {
  const it = (props.pr.items || []).find((x) => x.id === ln.pr_item_id)
  if (!it) return '(품목)'
  return (it.product_part?.part_number_display || it.product_part?.part_number || it.custom_product_code || '(품목)') as string
}

async function issue(box: BoxPlanBox) {
  if (!confirm(`박스 #${box.box_no} 를 CI로 발행할까요?`)) return
  busyBox.value = box.box_no
  try {
    const res = await productionRequestApi.createBoxCi(props.pr.id, box.box_no, docDate.value)
    box.ci_number = res.ci_number
    box.ci_document_id = res.ci_id
    showToast(`박스 #${box.box_no} → CI ${res.ci_number} 발행`, 'success')
    emit('issued')
  } catch (e: any) {
    showToast(e?.response?.data?.detail || 'CI 발행에 실패했습니다', 'error')
  } finally {
    busyBox.value = null
  }
}
</script>
