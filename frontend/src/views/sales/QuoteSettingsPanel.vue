<template>
  <div class="p-4 sm:p-6 max-w-3xl">
    <div class="mb-4">
      <h2 class="text-lg font-bold text-gray-800">견적 자동산출 설정</h2>
      <p class="text-xs text-gray-500 mt-1">
        견적서의 <b>「산출」</b> 버튼이 단가를 계산할 때 쓰는 기준값입니다. 수기 입력 견적에는 영향이 없습니다.
      </p>
    </div>

    <div v-if="loading" class="py-10 text-center text-gray-400 text-sm">불러오는 중…</div>

    <div v-else class="space-y-6">
      <!-- 채널 기준 마진 -->
      <section class="border rounded-lg p-4">
        <h3 class="text-sm font-semibold text-gray-700 mb-1">채널 기준 마진 (%)</h3>
        <p class="text-[11px] text-gray-400 mb-3">판매가 = 원가 ÷ (1 − 마진). 고객별 조정(±)은 거래처 설정에서 더해집니다.</p>
        <div class="grid grid-cols-3 gap-3 max-w-md">
          <div v-for="ch in CHANNELS" :key="ch">
            <label class="block text-xs text-gray-500 mb-0.5">{{ ch }}채널</label>
            <div class="relative">
              <input v-model.number="channelMargins[ch]" type="number" min="0" max="99" step="0.1"
                class="w-full border rounded px-2 py-1.5 text-sm text-right pr-6" />
              <span class="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">%</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 환율 · 국내 프리미엄 -->
      <section class="border rounded-lg p-4">
        <h3 class="text-sm font-semibold text-gray-700 mb-3">환율 · 국내 프리미엄</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-md">
          <div>
            <label class="block text-xs text-gray-500 mb-0.5">환율 (₩ / USD)</label>
            <input v-model.number="cfg.exchange_rate" type="number" min="1" step="1"
              class="w-full border rounded px-2 py-1.5 text-sm text-right" />
            <p class="text-[10px] text-gray-400 mt-0.5">USD 견적 산출에 사용 (기본 1,100)</p>
          </div>
          <div>
            <label class="block text-xs text-gray-500 mb-0.5">국내 프리미엄 (배수)</label>
            <input v-model.number="cfg.domestic_premium" type="number" min="1" step="0.01"
              class="w-full border rounded px-2 py-1.5 text-sm text-right" />
            <p class="text-[10px] text-gray-400 mt-0.5">원화 견적: 합계 × 프리미엄 (기본 1.3)</p>
          </div>
        </div>
      </section>

      <!-- 가격 인상률 -->
      <section class="border rounded-lg p-4">
        <h3 class="text-sm font-semibold text-gray-700 mb-1">가격 인상률 (%)</h3>
        <p class="text-[11px] text-gray-400 mb-3">노후 원가 보정 — 비율로만 적용(조정원가 = 기준원가 × (1+인상률/100)). 품목별이 전역보다 우선.</p>
        <div class="max-w-xs mb-4">
          <label class="block text-xs text-gray-500 mb-0.5">전역 기본 인상률</label>
          <div class="relative">
            <input v-model.number="cfg.price_increase_global" type="number" step="0.1"
              class="w-full border rounded px-2 py-1.5 text-sm text-right pr-6" />
            <span class="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">%</span>
          </div>
        </div>

        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-medium text-gray-600">품목별 인상률 (오더코드 기준)</span>
          <button @click="addItem" class="text-xs text-blue-600 hover:text-blue-800">＋ 품목 추가</button>
        </div>
        <div v-if="itemRates.length === 0" class="text-[11px] text-gray-400 border border-dashed rounded px-3 py-3 text-center">
          품목별 인상률이 없습니다. 전역 인상률이 적용됩니다.
        </div>
        <div v-else class="space-y-1.5">
          <div v-for="(row, i) in itemRates" :key="i" class="flex items-center gap-2">
            <input v-model="row.code" type="text" placeholder="오더코드 (예: HXB13AS-RJS-B-O2-S1-S20)"
              class="flex-1 border rounded px-2 py-1.5 text-sm font-mono" />
            <div class="relative w-24">
              <input v-model.number="row.pct" type="number" step="0.1"
                class="w-full border rounded px-2 py-1.5 text-sm text-right pr-6" />
              <span class="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">%</span>
            </div>
            <button @click="itemRates.splice(i, 1)" class="text-red-400 hover:text-red-600 px-1" title="삭제">✕</button>
          </div>
        </div>
      </section>

      <div class="flex items-center gap-3">
        <button @click="save" :disabled="saving"
          class="px-5 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50">
          {{ saving ? '저장 중…' : '설정 저장' }}
        </button>
        <button @click="load" :disabled="saving" class="px-4 py-2 border text-gray-600 text-sm rounded-lg hover:bg-gray-50">되돌리기</button>
        <span class="text-[11px] text-gray-400">기본값: 2ch 60 · 4ch 55 · 6ch 56 · 환율 1,100 · 프리미엄 1.3</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { salesDocumentApi, type QuoteConfig } from '@/api/salesDocument'
import { useToast } from '@/composables/useToast'

const { showToast } = useToast()

const CHANNELS = [2, 4, 6]
const loading = ref(true)
const saving = ref(false)

const cfg = reactive<QuoteConfig>({
  channel_margins: {},
  exchange_rate: 1100,
  domestic_premium: 1.3,
  price_increase_global: 0,
  price_increase_by_item: {},
})
const channelMargins = reactive<Record<number, number>>({ 2: 60, 4: 55, 6: 56 })
const itemRates = ref<{ code: string; pct: number }[]>([])

function addItem() { itemRates.value.push({ code: '', pct: 0 }) }

async function load() {
  loading.value = true
  try {
    const { data } = await salesDocumentApi.getQuoteConfig()
    cfg.exchange_rate = data.exchange_rate ?? 1100
    cfg.domestic_premium = data.domestic_premium ?? 1.3
    cfg.price_increase_global = data.price_increase_global ?? 0
    // 채널 마진 — 표준 2/4/6 채우기(기본값 폴백)
    const defaults: Record<number, number> = { 2: 60, 4: 55, 6: 56 }
    for (const ch of CHANNELS) {
      const v = data.channel_margins?.[String(ch)]
      channelMargins[ch] = (v === undefined || v === null) ? (defaults[ch] ?? 55) : Number(v)
    }
    // 품목별 인상률 dict → 배열
    itemRates.value = Object.entries(data.price_increase_by_item || {}).map(([code, pct]) => ({ code, pct: Number(pct) }))
  } catch {
    showToast('설정을 불러오지 못했습니다', 'error')
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const channel_margins: Record<string, number> = {}
    for (const ch of CHANNELS) channel_margins[String(ch)] = Number(channelMargins[ch]) || 0
    const price_increase_by_item: Record<string, number> = {}
    for (const r of itemRates.value) {
      const code = (r.code || '').trim().toUpperCase()
      if (code) price_increase_by_item[code] = Number(r.pct) || 0
    }
    const payload: QuoteConfig = {
      channel_margins,
      exchange_rate: Number(cfg.exchange_rate) || 1100,
      domestic_premium: Number(cfg.domestic_premium) || 1.3,
      price_increase_global: Number(cfg.price_increase_global) || 0,
      price_increase_by_item,
    }
    await salesDocumentApi.updateQuoteConfig(payload)
    showToast('견적 설정이 저장되었습니다', 'success')
    load()
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '저장에 실패했습니다 (관리자만 가능)', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
