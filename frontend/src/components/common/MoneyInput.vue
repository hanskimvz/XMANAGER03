<template>
  <input
    type="text"
    inputmode="decimal"
    :value="display"
    :readonly="readonly"
    :placeholder="placeholder"
    @input="onInput"
    @blur="onBlur"
  />
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { currencyFractionDigits } from '@/api/price'

// 금액 입력 — 천단위 콤마 표시. 통화별 소수 자릿수 허용(KRW/JPY/CNY=0, USD/EUR=2).
// 내부적으로는 순수 숫자(number | null)를 v-model 로 주고받는다.
const props = withDefaults(defineProps<{
  modelValue: number | string | null | undefined
  readonly?: boolean
  placeholder?: string
  currency?: string        // 통화(소수 자릿수 판별). 미지정 시 KRW(정수)
  fractionDigits?: number  // 소수 자릿수 직접 지정(통화 규칙보다 우선) — 예: 원화 단가 0.5원 단위
}>(), {
  readonly: false,
  placeholder: '',
  currency: 'KRW',
  fractionDigits: undefined,
})

const emit = defineEmits<{ 'update:modelValue': [v: number | null] }>()

const maxFrac = computed(() => props.fractionDigits ?? currencyFractionDigits(props.currency || 'KRW'))

function group(intStr: string): string {
  return intStr.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

// 입력 문자열 → { 정규화 텍스트(콤마없음), 숫자값 } — 소수점/자릿수 제한 반영
function sanitize(s: string): { text: string; num: number | null } {
  let t = (s || '').replace(/[^0-9.]/g, '')
  const firstDot = t.indexOf('.')
  if (firstDot !== -1) {
    // 소수점 1개만 유지
    t = t.slice(0, firstDot + 1) + t.slice(firstDot + 1).replace(/\./g, '')
  }
  if (maxFrac.value === 0) {
    t = t.replace(/\./g, '')  // 정수 통화 → 소수점 제거
  } else if (t.includes('.')) {
    const [ip, fp = ''] = t.split('.')
    t = ip + '.' + fp.slice(0, maxFrac.value)  // 소수 자릿수 제한
  }
  const num = (t === '' || t === '.') ? null : Number(t)
  return { text: t, num }
}

// 정규화 텍스트 → 표시(정수부 콤마, 소수부/후행 점 보존해 입력 중 끊기지 않게)
function displayFromText(t: string): string {
  if (t === '') return ''
  if (t === '.') return '0.'
  const dot = t.indexOf('.')
  if (dot === -1) return group(t.replace(/^0+(?=\d)/, ''))
  const ip = t.slice(0, dot).replace(/^0+(?=\d)/, '')
  const fp = t.slice(dot + 1)
  return `${group(ip) || '0'}.${fp}`
}

// 외부(모델) 값 → 완성 포맷(통화 소수 자릿수 적용)
function format(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === '') return ''
  const n = Number(v)
  if (isNaN(n)) return ''
  return n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: maxFrac.value })
}

const display = ref(format(props.modelValue))

// 외부(모델) 변경 시 동기화 — 사용자가 방금 친 값과 같으면 재포맷 생략
watch(() => props.modelValue, (v) => {
  const cur = sanitize(display.value).num
  const nv = (v == null || v === '') ? null : Number(v)
  if (cur !== nv) display.value = format(v)
})

// 통화·자릿수 변경 시 재포맷(예: USD→KRW 전환 시 소수 제거)
watch(maxFrac, () => {
  display.value = format(props.modelValue)
})

function onInput(e: Event) {
  const el = e.target as HTMLInputElement
  const { text, num } = sanitize(el.value)
  display.value = displayFromText(text)
  emit('update:modelValue', num)
}

// 포커스 아웃 시 완성 포맷으로 정리(후행 점/부분 소수 정돈)
function onBlur() {
  display.value = format(sanitize(display.value).num)
}
</script>
