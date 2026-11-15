<template>
  <div class="p-4 sm:p-6 max-w-screen-2xl mx-auto">
    <!-- 인사말 -->
    <div class="mb-6">
      <h1 class="text-xl sm:text-2xl font-bold text-gray-800">
        안녕하세요, {{ userName }}님
      </h1>
      <p class="text-sm text-gray-400 mt-1">사용할 모듈을 선택하세요.</p>
    </div>

    <!-- 모듈 타일 그리드 -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
      <button
        v-for="m in modules"
        :key="m.key"
        type="button"
        @click="openModule(m)"
        :class="[
          'relative flex flex-col items-center justify-center text-center bg-white rounded-xl shadow-sm border p-5 min-h-[8rem] transition-shadow',
          m.mobileReady ? 'hover:shadow-md cursor-pointer' : 'opacity-60 cursor-pointer',
        ]"
      >
        <!-- 결재 대기 배지 -->
        <span
          v-if="m.badge === 'approvalPending' && pendingCount > 0"
          class="absolute top-2 right-2 min-w-[20px] h-5 px-1.5 flex items-center justify-center text-[11px] font-bold rounded-full bg-red-500 text-white"
        >{{ pendingCount }}</span>

        <span class="text-4xl mb-2" aria-hidden="true">{{ m.icon }}</span>
        <span class="text-sm font-bold text-gray-800">{{ m.title }}</span>
        <span v-if="m.description" class="text-xs text-gray-500 mt-1">{{ m.description }}</span>

        <!-- PC 권장 라벨 -->
        <span
          v-if="!m.mobileReady"
          class="mt-2 px-2 py-0.5 text-[10px] font-medium rounded-full bg-gray-100 text-gray-500"
        >PC 권장</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth, hasPermStrict } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { approvalApi } from '@/api/approval'
import { visibleModules, type AppModule } from '@/modules/registry'

const router = useRouter()
const { isAdmin, userName } = useAuth()
const { info } = useToast()

// 권한 없는 모듈은 런처에서 숨김(전자결재 전용 계정은 전자결재만 노출)
const modules = visibleModules({ isAdmin: isAdmin.value, has: hasPermStrict })
const pendingCount = ref(0)

function openModule(m: AppModule) {
  if (m.mobileReady) {
    router.push(m.to)
  } else {
    info('PC에서 이용하거나 곧 모바일 지원 예정입니다')
  }
}

onMounted(async () => {
  // 결재 대기 배지
  if (modules.some((m) => m.badge === 'approvalPending')) {
    try {
      const res = await approvalApi.pendingCount()
      pendingCount.value = res.data.count
    } catch { /* ignore */ }
  }
})
</script>
