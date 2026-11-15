<script setup lang="ts">
/**
 * 비밀번호 변경 페이지 (로그인 사용자 본인)
 * 현재 비밀번호 확인 후 새 비밀번호로 변경 — POST /auth/change-password
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '@/api/client'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const toast = useToast()

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const errorMsg = ref('')

const canSubmit = computed(() =>
  currentPassword.value.length > 0 &&
  newPassword.value.length >= 4 &&
  newPassword.value === confirmPassword.value &&
  !submitting.value
)

async function submit() {
  errorMsg.value = ''
  if (newPassword.value.length < 8) {
    errorMsg.value = '새 비밀번호는 8자 이상이어야 합니다.'
    return
  }
  if (!/[A-Za-z]/.test(newPassword.value) || !/[0-9]/.test(newPassword.value)) {
    errorMsg.value = '새 비밀번호는 영문과 숫자를 모두 포함해야 합니다.'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    errorMsg.value = '새 비밀번호 확인이 일치하지 않습니다.'
    return
  }
  submitting.value = true
  try {
    await apiClient.post('/auth/change-password', {
      current_password: currentPassword.value,
      new_password: newPassword.value,
    })
    toast.success('비밀번호가 변경되었습니다.')
    router.push('/')
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || '비밀번호 변경에 실패했습니다.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="p-4 sm:p-6 max-w-lg mx-auto">
    <h1 class="text-xl font-bold text-gray-800 mb-1">비밀번호 변경</h1>
    <p class="text-sm text-gray-500 mb-6">현재 비밀번호를 확인한 뒤 새 비밀번호로 변경합니다.</p>

    <div class="bg-white rounded-lg shadow-sm border">
      <form @submit.prevent="submit" class="px-5 py-5 space-y-4">
        <div>
          <label class="block text-sm text-gray-600 mb-1">현재 비밀번호</label>
          <input v-model="currentPassword" type="password" autocomplete="current-password"
            class="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">새 비밀번호 <span class="text-xs text-gray-400">(8자 이상, 영문+숫자)</span></label>
          <input v-model="newPassword" type="password" autocomplete="new-password"
            class="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">새 비밀번호 확인</label>
          <input v-model="confirmPassword" type="password" autocomplete="new-password"
            class="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          <p v-if="confirmPassword && newPassword !== confirmPassword" class="mt-1 text-xs text-red-500">
            새 비밀번호 확인이 일치하지 않습니다.
          </p>
        </div>

        <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>

        <div class="flex justify-end gap-2 pt-1">
          <button type="button" @click="router.back()"
            class="px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded">취소</button>
          <button type="submit" :disabled="!canSubmit"
            class="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
            {{ submitting ? '변경 중...' : '변경' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
