<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[70] bg-black/50 flex items-start justify-center overflow-y-auto py-6">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4">
        <div class="flex items-center justify-between px-5 py-3 border-b">
          <div>
            <h3 class="text-base font-bold">📦 분할선적 — CI 발행</h3>
            <p class="text-xs text-gray-500 mt-0.5">
              {{ preview?.customer || '' }} · 이번 배송에 실을 수량만 발행합니다. 잔여는 다음 CI로 나눠 발행.
            </p>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        <div class="px-5 py-4 max-h-[68vh] overflow-y-auto">
          <div v-if="loading" class="py-8 text-center text-gray-400 text-sm">불러오는 중…</div>
          <div v-else-if="!rows.length" class="py-8 text-center text-gray-400 text-sm">발행할 품목이 없습니다.</div>

          <table v-else class="min-w-full text-sm">
            <thead>
              <tr class="text-xs text-gray-500 border-b">
                <th class="px-2 py-2 text-left">품번</th>
                <th class="px-2 py-2 text-right w-16">전량</th>
                <th class="px-2 py-2 text-right w-16">기발행</th>
                <th class="px-2 py-2 text-right w-16">잔여</th>
                <th class="px-2 py-2 text-right w-24">단가</th>
                <th class="px-2 py-2 text-center w-24">이번 발행</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in rows" :key="r.pr_item_id" class="border-b" :class="r.remaining <= 0 ? 'opacity-50' : ''">
                <td class="px-2 py-1.5">
                  <div class="font-mono text-gray-800 truncate max-w-[220px]">{{ r.product_code }}
                    <span v-if="r.is_custom" class="ml-1 text-[10px] bg-slate-100 text-slate-600 rounded px-1">외주</span>
                  </div>
                  <div v-if="r.product_name" class="text-[11px] text-gray-400 truncate max-w-[220px]">{{ r.product_name }}</div>
                </td>
                <td class="px-2 py-1.5 text-right tabular-nums">{{ fmt(r.ordered) }}</td>
                <td class="px-2 py-1.5 text-right tabular-nums text-gray-500">{{ fmt(r.issued) }}</td>
                <td class="px-2 py-1.5 text-right tabular-nums font-medium">{{ fmt(r.remaining) }}</td>
                <td class="px-2 py-1.5">
                  <input v-if="r.is_custom || r.unit_price == null" v-model.number="r.price" type="number" min="0" step="0.01"
                    placeholder="수기" class="w-20 border rounded px-1.5 py-1 text-xs text-right" />
                  <span v-else class="block text-right text-xs text-gray-600 tabular-nums">{{ fmt(r.unit_price) }}</span>
                </td>
                <td class="px-2 py-1.5 text-center whitespace-nowrap">
                  <input v-model.number="r.qty" type="number" min="0" :max="r.remaining" step="1"
                    :disabled="r.remaining <= 0"
                    class="w-20 border rounded px-1.5 py-1 text-sm text-right disabled:bg-gray-100" />
                  <span class="ml-1 text-[10px] text-gray-400">{{ r.uom || '' }}</span>
                </td>
              </tr>
            </tbody>
          </table>

          <div class="mt-4 flex flex-wrap items-center gap-3">
            <label class="text-xs text-gray-600">문서일(출고일)
              <input v-model="docDate" type="date" class="ml-1 border rounded px-2 py-1 text-sm" />
            </label>
            <button class="text-xs text-blue-600 hover:text-blue-800" @click="fillAllRemaining">전량 채우기</button>
            <button class="text-xs text-gray-500 hover:text-gray-700" @click="clearAll">비우기</button>
            <span class="ml-auto text-sm text-gray-600">발행 합계: <b>{{ totalQty }}</b>개</span>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 px-5 py-3 border-t bg-gray-50">
          <button @click="$emit('close')" class="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-100">취소</button>
          <button @click="submit" :disabled="submitting || totalQty <= 0"
            class="px-4 py-2 text-sm bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50">
            {{ submitting ? '발행 중…' : '📄 CI 발행' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { productionRequestApi, type CiSplitLine } from '@/api/productionRequest'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ prIds: number[] }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'created', ciNumber: string): void }>()
const { showToast } = useToast()

type Row = CiSplitLine & { qty: number; price: number | null }
const loading = ref(true)
const submitting = ref(false)
const preview = ref<{ customer?: string | null; currency: string } | null>(null)
const rows = ref<Row[]>([])
const docDate = ref(todayStr())

function todayStr(): string {
  const d = new Date()
  const p = (x: number) => String(x).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}
function fmt(n: number | null | undefined): string {
  if (n == null) return '-'
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: 3 })
}

const totalQty = computed(() => rows.value.reduce((s, r) => s + (Number(r.qty) || 0), 0))

async function load() {
  loading.value = true
  try {
    const data = await productionRequestApi.ciSplitPreview(props.prIds)
    preview.value = { customer: data.customer, currency: data.currency }
    rows.value = data.lines.map((l) => ({ ...l, qty: Math.max(0, l.remaining), price: l.unit_price ?? null }))
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '미리보기를 불러오지 못했습니다', 'error')
  } finally {
    loading.value = false
  }
}
function fillAllRemaining() { rows.value.forEach((r) => (r.qty = Math.max(0, r.remaining))) }
function clearAll() { rows.value.forEach((r) => (r.qty = 0)) }

async function submit() {
  const lines = rows.value
    .filter((r) => (Number(r.qty) || 0) > 0)
    .map((r) => ({ pr_item_id: r.pr_item_id, quantity: Number(r.qty), unit_price: r.price }))
  if (!lines.length) { showToast('발행할 수량을 입력하세요', 'warning'); return }
  // 잔여 초과 검증(프론트)
  for (const r of rows.value) {
    if ((Number(r.qty) || 0) > r.remaining + 1e-6) { showToast(`${r.product_code}: 잔여 초과`, 'error'); return }
    if ((Number(r.qty) || 0) > 0 && (r.is_custom || r.unit_price == null) && !(r.price! > 0)) {
      showToast(`${r.product_code}: 단가를 입력하세요`, 'error'); return
    }
  }
  submitting.value = true
  try {
    const res = await productionRequestApi.createCiSplit({ pr_ids: props.prIds, lines, document_date: docDate.value })
    showToast(`분할 CI 발행: ${res.ci_number}`, 'success')
    emit('created', res.ci_number)
  } catch (e: any) {
    showToast(e?.response?.data?.detail || 'CI 발행에 실패했습니다', 'error')
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>
