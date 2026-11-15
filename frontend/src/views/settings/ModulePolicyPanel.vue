<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { rbacApi, type ModulePolicyRow } from '@/api/rbac'

const { success, error } = useToast()
const globalMode = ref('disabled')
const modules = ref<ModulePolicyRow[]>([])
const loading = ref(false)
const busy = ref('')

const MODE_LABEL: Record<string, string> = { disabled: '비활성(전체 개방)', observe: '관찰(로그인만)', enforce: '강제(권한 차단)' }

async function load() {
  loading.value = true
  try {
    const r = await rbacApi.modulePolicy()
    globalMode.value = r.global_mode
    modules.value = r.modules
  } catch {
    error('모듈 정책을 불러오지 못했습니다(관리자 전용)')
  } finally {
    loading.value = false
  }
}

async function toggle(m: ModulePolicyRow) {
  if (m.locked) return
  busy.value = m.module
  try {
    const r = await rbacApi.setModulePolicy(m.module, !m.enforced)
    globalMode.value = r.global_mode
    modules.value = r.modules
    success(`${m.label} 권한 강제 ${!m.enforced ? '켜짐' : '꺼짐'}`)
  } catch (e: any) {
    error(e?.response?.data?.detail || '변경 실패')
  } finally {
    busy.value = ''
  }
}

onMounted(load)
</script>

<template>
  <div class="p-4">
    <div class="mb-3">
      <h2 class="text-lg font-bold text-gray-800">권한 적용 (모듈별)</h2>
      <p class="text-xs text-gray-500 mt-1">
        전역 모드를 한 번에 켜지 않고 <b>모듈 단위로 권한 강제(enforce)를 켜고 끕니다.</b>
        켜진 모듈은 로그인 + 해당 권한이 있어야 접근 가능, 꺼진 모듈은 전역 모드를 따릅니다.
      </p>
      <p class="text-xs mt-1">
        전역 모드: <span class="px-2 py-0.5 rounded bg-gray-100 text-gray-700 font-medium">{{ MODE_LABEL[globalMode] || globalMode }}</span>
      </p>
      <p class="text-[11px] text-amber-600 mt-1">
        ⚠️ 모듈을 켜기 전, 그 모듈 권한을 역할에 먼저 배정하세요(권한 관리). 안 그러면 정당한 사용자도 차단됩니다.
      </p>
    </div>

    <div v-if="loading" class="text-sm text-gray-400">불러오는 중…</div>
    <table v-else class="w-full text-sm border rounded-lg overflow-hidden">
      <thead class="bg-gray-50 text-gray-500 text-xs">
        <tr>
          <th class="px-4 py-2 text-left">모듈</th>
          <th class="px-4 py-2 text-center">권한 강제</th>
          <th class="px-4 py-2 text-left">상태</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="m in modules" :key="m.module" class="border-t">
          <td class="px-4 py-2 font-medium text-gray-800">
            {{ m.label }}
            <span class="text-gray-400 text-xs ml-1">{{ m.module }}</span>
            <span v-if="m.locked" class="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-600">민감·항상보호</span>
          </td>
          <td class="px-4 py-2 text-center">
            <button
              :disabled="m.locked || busy === m.module"
              class="toggle"
              :class="m.enforced ? 'on' : 'off'"
              @click="toggle(m)"
            >
              <span class="knob" :class="{ 'knob-on': m.enforced }"></span>
            </button>
          </td>
          <td class="px-4 py-2">
            <span v-if="m.enforced" class="text-blue-600 text-xs font-medium">🔒 강제 (권한자만)</span>
            <span v-else class="text-gray-400 text-xs">개방 (전역 모드 따름)</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.toggle { @apply relative inline-flex items-center w-11 h-6 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed; }
.toggle.on { @apply bg-blue-600; }
.toggle.off { @apply bg-gray-300; }
.knob { @apply inline-block w-4 h-4 bg-white rounded-full transform translate-x-1 transition-transform; }
.knob-on { @apply translate-x-6; }
</style>
