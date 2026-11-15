<template>
  <div class="p-4 sm:p-6 max-w-3xl">
    <div class="mb-4">
      <h2 class="text-lg font-bold text-gray-800">회사 은행 계좌 (통화별)</h2>
      <p class="text-xs text-gray-500 mt-1">
        해외 문서(견적/PI/CI)에 표기되는 <b>당사 입금 계좌</b>입니다. 통장이 바뀌면 여기서 수정하면
        <b>신규 문서</b>에 자동 반영됩니다. (이미 발행된 문서는 발행 당시 값을 유지)
      </p>
    </div>

    <div v-if="loading" class="py-10 text-center text-gray-400 text-sm">불러오는 중…</div>

    <div v-else class="space-y-4">
      <div v-for="(a, i) in accounts" :key="i" class="border rounded-lg p-4 relative"
        :class="a.is_default ? 'border-blue-300 bg-blue-50/40' : ''">
        <div class="flex items-center justify-between mb-3">
          <label class="inline-flex items-center gap-2 text-sm cursor-pointer select-none">
            <input type="radio" :checked="a.is_default" @change="setDefault(i)" class="w-4 h-4" />
            <span :class="a.is_default ? 'text-blue-700 font-medium' : 'text-gray-500'">
              {{ a.is_default ? '기본 계좌' : '기본으로 지정' }}
            </span>
          </label>
          <button @click="remove(i)" class="text-xs text-red-500 hover:text-red-700">삭제</button>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div>
            <label class="block text-xs text-gray-500 mb-0.5">통화 <span class="text-red-500">*</span></label>
            <input v-model="a.currency" type="text" placeholder="USD" maxlength="10"
              class="w-full border rounded px-2 py-1.5 text-sm uppercase" />
          </div>
          <div class="col-span-2">
            <label class="block text-xs text-gray-500 mb-0.5">SWIFT</label>
            <input v-model="a.swift_code" type="text" placeholder="KOEXKRSE"
              class="w-full border rounded px-2 py-1.5 text-sm" />
          </div>
          <div class="col-span-2 sm:col-span-3">
            <label class="block text-xs text-gray-500 mb-0.5">은행명</label>
            <input v-model="a.bank_name" type="text" placeholder="KEB HANA BANK, HEAD OFFICE"
              class="w-full border rounded px-2 py-1.5 text-sm" />
          </div>
          <div class="col-span-2 sm:col-span-3">
            <label class="block text-xs text-gray-500 mb-0.5">은행 주소</label>
            <input v-model="a.bank_address" type="text" placeholder="35, EULJI-RO, JUNG-GU, SEOUL, KOREA"
              class="w-full border rounded px-2 py-1.5 text-sm" />
          </div>
          <div class="col-span-2">
            <label class="block text-xs text-gray-500 mb-0.5">예금주</label>
            <input v-model="a.account_name" type="text" placeholder="XBEAMTECH CO., LTD."
              class="w-full border rounded px-2 py-1.5 text-sm" />
          </div>
          <div>
            <label class="block text-xs text-gray-500 mb-0.5">계좌번호</label>
            <input v-model="a.account_number" type="text" placeholder="332-910005-81138"
              class="w-full border rounded px-2 py-1.5 text-sm" />
          </div>
        </div>
      </div>

      <button @click="addAccount"
        class="w-full py-2 text-sm border border-dashed border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50">
        + 통화 계좌 추가
      </button>

      <div class="flex items-center justify-end gap-2 pt-2">
        <span v-if="dirty" class="text-xs text-amber-600 mr-auto">저장하지 않은 변경이 있습니다</span>
        <button @click="reload" :disabled="saving" class="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-100 disabled:opacity-50">되돌리기</button>
        <button @click="save" :disabled="saving" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
          {{ saving ? '저장 중…' : '저장' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { settingsApi, type CompanyBankAccount } from '@/api/settings'
import { useToast } from '@/composables/useToast'

const { showToast } = useToast()
const loading = ref(true)
const saving = ref(false)
const accounts = ref<CompanyBankAccount[]>([])
const original = ref('')

const dirty = computed(() => JSON.stringify(accounts.value) !== original.value)

function snapshot() { original.value = JSON.stringify(accounts.value) }

async function load() {
  loading.value = true
  try {
    accounts.value = await settingsApi.getCompanyBankAccounts()
    snapshot()
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '계좌 설정을 불러오지 못했습니다', 'error')
  } finally {
    loading.value = false
  }
}
function reload() { load() }

function setDefault(i: number) {
  accounts.value.forEach((a, idx) => (a.is_default = idx === i))
}
function addAccount() {
  accounts.value.push({
    currency: '', bank_name: '', bank_address: '', swift_code: '',
    account_name: '', account_number: '', is_default: accounts.value.length === 0,
  })
}
function remove(i: number) {
  const wasDefault = accounts.value[i]?.is_default
  accounts.value.splice(i, 1)
  const first = accounts.value[0]
  if (wasDefault && first) first.is_default = true
}

async function save() {
  // 최소 검증: 통화 필수
  for (const a of accounts.value) {
    if (!a.currency || !a.currency.trim()) { showToast('통화 코드는 필수입니다', 'warning'); return }
    a.currency = a.currency.trim().toUpperCase()
  }
  saving.value = true
  try {
    accounts.value = await settingsApi.setCompanyBankAccounts(accounts.value)
    snapshot()
    showToast('회사 계좌가 저장되었습니다', 'success')
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '저장에 실패했습니다', 'error')
  } finally {
    saving.value = false
  }
}

load()
</script>
