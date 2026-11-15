<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100">
    <div class="bg-white rounded-2xl shadow-lg w-full max-w-sm mx-4 px-8 py-10 text-center">
      <!-- 로고 + 타이틀 -->
      <div class="mb-8">
        <img src="/xbeamtech-logo.png" alt="XbeamTech" class="h-12 mx-auto mb-4" />
        <h1 class="text-2xl font-bold text-gray-800 tracking-wide">X-Manager</h1>
        <p class="text-sm text-gray-400 mt-1">부품 관리 및 BOM 통합 시스템</p>
        <p class="text-xs text-gray-300 mt-1">v0.28.0</p>
      </div>

      <!-- 로그인 폼 -->
      <form @submit.prevent="handleLogin" class="space-y-4 text-left">
        <div>
          <label class="block text-sm font-medium text-gray-600 mb-1">아이디</label>
          <input
            v-model="username"
            type="text"
            required
            autofocus
            class="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            placeholder="아이디를 입력하세요"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-600 mb-1">비밀번호</label>
          <input
            v-model="password"
            type="password"
            required
            class="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            placeholder="비밀번호를 입력하세요"
            @keyup.enter="handleLogin"
          />
        </div>

        <div v-if="errorMsg" class="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 text-center">
          {{ errorMsg }}
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors text-sm mt-2"
        >
          {{ loading ? '로그인 중...' : '로그인' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/stores/auth'

const router = useRouter()
const { login } = useAuth()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function handleLogin() {
  if (!username.value || !password.value) return
  loading.value = true
  errorMsg.value = ''
  try {
    await login(username.value, password.value)
    router.push('/')
  } catch (err: any) {
    errorMsg.value = err.response?.data?.detail || '로그인에 실패했습니다'
  } finally {
    loading.value = false
  }
}
</script>
