<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[70] flex items-start justify-center bg-black/50 overflow-y-auto py-6">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
        <!-- 헤더 -->
        <div class="flex items-center justify-between px-5 py-3 border-b">
          <div>
            <h3 class="text-base font-bold">견적 산출</h3>
            <p class="text-xs text-gray-500 mt-0.5 font-mono break-all">{{ orderCode || '(오더코드 없음)' }}</p>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="px-5 py-4 max-h-[74vh] overflow-y-auto">
          <!-- 파싱 결과 -->
          <div v-if="calc" class="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-gray-500 mb-3">
            <span>사이즈 <b class="text-gray-700">{{ calc.parsed.size || '-' }}</b></span>
            <span>형태 <b class="text-gray-700">{{ calc.parsed.form || '-' }}</b></span>
            <span>채널 <b class="text-gray-700">{{ calc.parsed.channel ?? '-' }}</b></span>
            <span>모드 <b class="text-gray-700">{{ calc.parsed.mode || '-' }}</b></span>
            <span v-if="calc.parsed.is_sa" class="text-indigo-600 font-medium">SA(양단동일)</span>
            <span>통화 <b class="text-gray-700">{{ currency }}</b></span>
          </div>

          <!-- 기본 입력 -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
            <div>
              <label class="block text-[11px] text-gray-500 mb-0.5">미터수(m)</label>
              <input v-model.number="lengthM" @input="onLengthChange" type="number" min="0" step="0.1"
                class="w-full border rounded px-2 py-1 text-sm text-right" />
            </div>
            <div>
              <label class="block text-[11px] text-gray-500 mb-0.5">수량</label>
              <input v-model.number="quantity" @input="scheduleRecompute" type="number" min="1" step="1"
                class="w-full border rounded px-2 py-1 text-sm text-right" />
            </div>
            <div>
              <label class="block text-[11px] text-gray-500 mb-0.5">
                마진(%) <span v-if="touched.margin_rate" class="text-amber-600">수정</span>
              </label>
              <input v-model.number="marginPct" @input="onInput('margin_rate', ['connector_a'])" type="number" min="0" max="99" step="0.1"
                class="w-full border rounded px-2 py-1 text-sm text-right"
                :class="touched.margin_rate ? 'border-amber-300 bg-amber-50' : ''" />
            </div>
            <div>
              <label class="block text-[11px] text-gray-500 mb-0.5">
                커넥터원가(₩) <span v-if="touched.base_cost_krw" class="text-amber-600">수정</span>
              </label>
              <input v-model.number="baseCost" @input="onInput('base_cost_krw', ['connector_a'])" type="number" min="0" step="1"
                class="w-full border rounded px-2 py-1 text-sm text-right"
                :class="touched.base_cost_krw ? 'border-amber-300 bg-amber-50' : ''" />
            </div>
          </div>

          <!-- 산출 내역(수정 가능) -->
          <div class="border rounded-md overflow-hidden">
            <div class="grid grid-cols-12 bg-gray-50 text-[11px] text-gray-500 px-3 py-1.5 font-medium">
              <div class="col-span-6">구성요소</div>
              <div class="col-span-6 text-right">금액 ({{ currency }})</div>
            </div>

            <CalcRow label="커넥터 A" :hint="marginHint" v-model="connA" :touched="touched.connector_a"
              @edit="onInput('connector_a')" />
            <CalcRow label="커넥터 B" :hint="calc?.parsed.is_sa ? 'SA=커넥터A' : `채널 × ${fmt(endfaceRate)}`" v-model="connB"
              :touched="touched.connector_b" @edit="onInput('connector_b')" />
            <!-- 케이블: 미터당 단가를 직접 입력(정확한 가격표 미확정) → 미터수 × 단가 = 총액 자동. 총액도 직접 수정 가능 -->
            <div class="grid grid-cols-12 items-center px-3 py-1.5 border-t text-sm gap-1">
              <div class="col-span-6 flex items-center gap-1.5 flex-wrap">
                <span>케이블</span>
                <span class="text-[11px] text-gray-400">{{ lengthM || 0 }}m ×</span>
                <input v-model.number="cableRate" @input="onInput('cable_rate', ['cable'])" type="number" min="0" step="0.01"
                  title="미터당 단가 직접 입력 — 입력하면 미터수 × 단가로 케이블비가 자동 계산됩니다."
                  class="w-24 border rounded px-1.5 py-0.5 text-xs text-right"
                  :class="touched.cable_rate ? 'border-amber-300 bg-amber-50' : ''" />
                <span class="text-[11px] text-gray-400">/m</span>
              </div>
              <div class="col-span-6">
                <input v-model.number="cable" @input="onInput('cable')" type="number" step="1"
                  class="w-full border rounded px-2 py-1 text-sm text-right"
                  :class="touched.cable ? 'border-amber-300 bg-amber-50' : ''" />
              </div>
            </div>
            <div class="grid grid-cols-12 items-center px-3 py-1.5 border-t text-sm">
              <div class="col-span-6 flex items-center gap-1.5">
                <span>조립비</span>
                <select v-model.number="stages" @change="onInput('assembly_stages', ['assembly'])"
                  class="border rounded px-1 py-0.5 text-[11px] text-gray-600">
                  <option :value="1">1단</option>
                  <option :value="2">2단</option>
                </select>
              </div>
              <div class="col-span-6">
                <input v-model.number="assembly" @input="onInput('assembly')" type="number" step="1"
                  class="w-full border rounded px-2 py-1 text-sm text-right"
                  :class="touched.assembly ? 'border-amber-300 bg-amber-50' : ''" />
              </div>
            </div>
            <CalcRow label="옵션 델타 (SUS 등)" hint="선택" v-model="optionDelta" :touched="touched.option_delta"
              @edit="onInput('option_delta')" />

            <!-- 기타 항목(특수케이블 등) -->
            <div v-for="(ex, i) in extras" :key="i" class="grid grid-cols-12 items-center px-3 py-1.5 border-t text-sm gap-1">
              <div class="col-span-6 flex items-center gap-1">
                <input v-model="ex.label" @input="scheduleRecompute" placeholder="항목명(특수케이블 등)"
                  class="w-full border rounded px-2 py-1 text-xs" />
              </div>
              <div class="col-span-5">
                <input v-model.number="ex.amount" @input="scheduleRecompute" type="number" step="1"
                  class="w-full border rounded px-2 py-1 text-sm text-right" />
              </div>
              <div class="col-span-1 flex justify-center">
                <button @click="removeExtra(i)" class="text-red-400 hover:text-red-600" title="삭제">✕</button>
              </div>
            </div>
            <div class="px-3 py-1.5 border-t">
              <button @click="addExtra" class="text-xs text-blue-600 hover:text-blue-800">＋ 항목 추가</button>
            </div>

            <!-- 소계/프리미엄/단가 -->
            <div class="border-t bg-gray-50 px-3 py-2 text-sm space-y-1">
              <div class="flex justify-between text-gray-600">
                <span>소계</span><span class="font-mono">{{ fmt(calc?.cost_breakdown.subtotal) }}</span>
              </div>
              <div v-if="currency !== 'USD'" class="flex justify-between text-gray-600">
                <span>× 국내프리미엄</span>
                <span>
                  <input v-model.number="premium" @input="onInput('domestic_premium')" type="number" step="0.01" min="1"
                    class="w-16 border rounded px-1 py-0.5 text-xs text-right"
                    :class="touched.domestic_premium ? 'border-amber-300 bg-amber-50' : ''" />
                </span>
              </div>
              <div class="flex justify-between items-baseline pt-1 border-t">
                <span class="font-semibold text-gray-800">단가 ({{ currency }})</span>
                <span class="text-lg font-bold text-blue-700 font-mono">{{ fmt(calc?.unit_price) }}</span>
              </div>
            </div>
          </div>

          <!-- 경고 -->
          <div v-if="calc?.warnings?.length" class="mt-3 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
            <div v-for="(w, i) in calc.warnings" :key="i">⚠ {{ w }}</div>
          </div>
          <div v-if="loading" class="mt-2 text-xs text-gray-400">계산 중…</div>
        </div>

        <!-- 하단 -->
        <div class="flex items-center justify-between px-5 py-3 border-t bg-gray-50">
          <button @click="reset" class="text-xs text-gray-500 hover:text-gray-700">자동값으로 초기화</button>
          <div class="flex gap-2">
            <button @click="$emit('close')" class="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded">취소</button>
            <button @click="apply" :disabled="calc?.unit_price == null"
              class="px-4 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-40">
              견적에 적용
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, h, defineComponent } from 'vue'
import { salesDocumentApi, type SuggestPriceResult } from '@/api/salesDocument'

const props = defineProps<{
  orderCode: string
  customerId: number | null
  currency: string
  length: number
  quantity: number
}>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'apply', payload: { unit_price: number; currency: string; result: SuggestPriceResult }): void
}>()

// 인라인 컴포넌트 행(라벨+힌트+수정가능 금액)
const CalcRow = defineComponent({
  props: { label: String, hint: String, modelValue: Number, touched: Boolean },
  emits: ['update:modelValue', 'edit'],
  setup(p, { emit }) {
    return () => h('div', { class: 'grid grid-cols-12 items-center px-3 py-1.5 border-t text-sm' }, [
      h('div', { class: 'col-span-6' }, [
        h('span', p.label),
        p.hint ? h('span', { class: 'ml-1 text-[10px] text-gray-400' }, p.hint) : null,
      ]),
      h('div', { class: 'col-span-6' }, [
        h('input', {
          type: 'number', step: '1', value: p.modelValue,
          class: 'w-full border rounded px-2 py-1 text-sm text-right ' + (p.touched ? 'border-amber-300 bg-amber-50' : ''),
          onInput: (e: any) => { emit('update:modelValue', e.target.value === '' ? null : Number(e.target.value)); emit('edit') },
        }),
      ]),
    ])
  },
})

const loading = ref(false)
const calc = ref<SuggestPriceResult | null>(null)

// 편집 상태
const lengthM = ref(Number(props.length) || 0)
const quantity = ref(Number(props.quantity) || 1)
const marginPct = ref<number | null>(null)
const baseCost = ref<number | null>(null)
const connA = ref<number | undefined>(undefined)
const connB = ref<number | undefined>(undefined)
const cable = ref<number | undefined>(undefined)
const cableRate = ref<number | null>(null)  // 미터당 단가(사용자 입력, 표 미확정)
const stages = ref(1)
const assembly = ref<number | null>(null)
const optionDelta = ref<number | undefined>(0)
const premium = ref<number | null>(null)
const extras = reactive<{ label: string; amount: number | null }[]>([])

// 사용자가 손댄(오버라이드) 필드
const touched = reactive<Record<string, boolean>>({})

const endfaceRate = computed(() => {
  const b = calc.value?.cost_breakdown
  const ch = calc.value?.parsed.channel
  if (!b || !ch || calc.value?.parsed.is_sa) return null
  return (b.connector_b ?? 0) / ch
})
const marginHint = computed(() => {
  const m = calc.value?.applied.margin_rate
  return m != null ? `원가 ÷ (1−${Math.round(m * 1000) / 10}%)` : ''
})

function fmt(n: number | null | undefined) {
  if (n == null) return '-'
  const dp = (props.currency === 'USD' || props.currency === 'EUR') ? 2 : 0
  return Number(n).toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp })
}

let timer: any = null
function scheduleRecompute() {
  clearTimeout(timer)
  timer = setTimeout(recompute, 250)
}
// 입력 필드 편집: 해당 override를 touched로, 파생 컴포넌트는 touched 해제(재계산)
function onInput(field: string, clearDerived: string[] = []) {
  touched[field] = true
  clearDerived.forEach((d) => { touched[d] = false })
  scheduleRecompute()
}
// 미터수 변경: 케이블 총액 override는 해제(미터수×단가로 재계산), 단가 override는 유지
function onLengthChange() {
  touched.cable = false
  scheduleRecompute()
}

function buildOverrides(): Record<string, any> {
  const o: Record<string, any> = {}
  const map: Record<string, any> = {
    margin_rate: marginPct.value, base_cost_krw: baseCost.value,
    connector_a: connA.value, connector_b: connB.value, cable: cable.value, cable_rate: cableRate.value,
    assembly: assembly.value, option_delta: optionDelta.value,
    assembly_stages: stages.value, domestic_premium: premium.value,
  }
  for (const k in map) {
    if (touched[k] && map[k] !== null && map[k] !== undefined && map[k] !== '') o[k] = map[k]
  }
  const items = extras.filter((e) => e.label || e.amount).map((e) => ({ label: e.label || '기타', amount: Number(e.amount) || 0 }))
  if (items.length) o.extra_items = items
  return o
}

async function recompute() {
  loading.value = true
  try {
    const overrides = buildOverrides()
    const { data } = await salesDocumentApi.suggestPrice({
      order_code: props.orderCode,
      length_m: lengthM.value || 0,
      quantity: quantity.value || 1,
      customer_id: props.customerId,
      currency: props.currency,
      overrides: Object.keys(overrides).length ? overrides : null,
    })
    calc.value = data
    // 손대지 않은 필드는 서버값으로 갱신
    const b = data.cost_breakdown, a = data.applied
    if (!touched.margin_rate && a.margin_rate != null) marginPct.value = Math.round(a.margin_rate * 10000) / 100
    if (!touched.base_cost_krw && b.base_cost_krw != null) baseCost.value = b.base_cost_krw
    if (!touched.connector_a && b.connector_a != null) connA.value = b.connector_a
    if (!touched.connector_b && b.connector_b != null) connB.value = b.connector_b
    if (!touched.cable && b.cable != null) cable.value = b.cable
    if (!touched.cable_rate && b.cable_rate != null) cableRate.value = b.cable_rate
    if (!touched.assembly && b.assembly != null) assembly.value = b.assembly
    if (!touched.assembly_stages && a.assembly_stages != null) stages.value = a.assembly_stages
    if (!touched.option_delta && b.option_delta != null) optionDelta.value = b.option_delta
    if (!touched.domestic_premium && a.domestic_premium != null) premium.value = a.domestic_premium
  } catch (e) {
    console.error('suggest-price 실패', e)
  } finally {
    loading.value = false
  }
}

function addExtra() { extras.push({ label: '', amount: null }) }
function removeExtra(i: number) { extras.splice(i, 1); scheduleRecompute() }

function reset() {
  for (const k in touched) touched[k] = false
  extras.splice(0, extras.length)
  lengthM.value = Number(props.length) || 0
  quantity.value = Number(props.quantity) || 1
  recompute()
}

function apply() {
  if (!calc.value || calc.value.unit_price == null) return
  emit('apply', { unit_price: calc.value.unit_price, currency: props.currency, result: calc.value })
}

watch(() => props.orderCode, () => reset())
onMounted(recompute)
</script>
