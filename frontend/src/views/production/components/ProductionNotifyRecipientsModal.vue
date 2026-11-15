<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[60] bg-black/50 flex items-center justify-center p-4" @click.self="$emit('close')">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[85vh] flex flex-col overflow-hidden">
        <div class="flex items-center justify-between px-5 py-3 border-b">
          <div>
            <div class="text-sm font-semibold text-gray-800">🔔 생산 단계별 알림 수신자 지정</div>
            <div class="text-xs text-gray-400">각 단계마다 알림 받을 인원을 개별 지정합니다.</div>
          </div>
          <button class="text-gray-400 hover:text-gray-700 text-lg px-2" @click="$emit('close')">✕</button>
        </div>

        <!-- 단계 탭 -->
        <div class="flex border-b">
          <button v-for="s in STAGES" :key="s.key" @click="activeStage = s.key"
            class="flex-1 px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors"
            :class="activeStage === s.key ? 'border-blue-600 text-blue-700 bg-blue-50/50' : 'border-transparent text-gray-500 hover:text-gray-700'">
            {{ s.label }}
            <span class="ml-1 text-[11px] px-1.5 rounded-full"
              :class="activeStage === s.key ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'">{{ (recipients[s.key] || []).length }}</span>
          </button>
        </div>

        <div class="px-4 pt-2 text-[11px] text-gray-500">{{ activeStageDesc }}</div>

        <div class="p-4 pt-2 overflow-auto flex-1">
          <div v-if="loading" class="text-center py-8 text-gray-400 text-sm">불러오는 중…</div>
          <template v-else>
            <input v-model="q" type="text" placeholder="이름 검색"
              class="w-full border rounded px-3 py-1.5 text-sm mb-3" />
            <div class="space-y-1">
              <label v-for="u in filtered" :key="u.id"
                class="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-50 cursor-pointer">
                <input type="checkbox" :value="u.id" v-model="recipients[activeStage]" class="rounded border-gray-300" />
                <span class="text-sm text-gray-800">{{ u.name }}</span>
                <span class="text-xs text-gray-400">{{ deptLabel(u.department) }}{{ u.position ? ' · ' + u.position : '' }}</span>
              </label>
              <div v-if="filtered.length === 0" class="text-center py-6 text-gray-400 text-sm">검색 결과 없음</div>
            </div>
          </template>
        </div>

        <div class="flex items-center justify-between px-5 py-3 border-t bg-gray-50">
          <span class="text-xs text-gray-500">{{ activeStageLabel }} {{ (recipients[activeStage] || []).length }}명</span>
          <div class="flex items-center gap-2">
            <button class="px-3 py-1.5 text-sm text-gray-600 border rounded" @click="$emit('close')">취소</button>
            <button class="px-4 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              :disabled="saving" @click="save">{{ saving ? '저장 중…' : '저장' }}</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { productionRequestApi } from '@/api/productionRequest'
import { useToast } from '@/composables/useToast'

const emit = defineEmits<{ close: [] }>()
const toast = useToast()

type StageKey = 'requested' | 'in_progress' | 'shipped'
const STAGES: { key: StageKey; label: string; desc: string }[] = [
  { key: 'requested', label: '생산 요청', desc: '영업이 새 생산요청을 등록할 때 알림을 받습니다.' },
  { key: 'in_progress', label: '생산 진행', desc: '생산이 시작(진행중 진입)될 때 알림을 받습니다.' },
  { key: 'shipped', label: '생산 출고', desc: '생산 출고가 완료될 때 알림을 받습니다.' },
]

const loading = ref(true)
const saving = ref(false)
const q = ref('')
const activeStage = ref<StageKey>('requested')
const users = ref<Array<{ id: number; name: string; department?: string; position?: string }>>([])
const recipients = reactive<Record<StageKey, number[]>>({ requested: [], in_progress: [], shipped: [] })

const DEPT: Record<string, string> = { SALES: '영업', PRODUCTION: '생산', MANAGEMENT: '경영지원' }
const deptLabel = (d?: string) => (d ? (DEPT[d] || d) : '')
const activeStageLabel = computed(() => STAGES.find(s => s.key === activeStage.value)?.label || '')
const activeStageDesc = computed(() => STAGES.find(s => s.key === activeStage.value)?.desc || '')

const filtered = computed(() => {
  const k = q.value.trim().toLowerCase()
  const list = k ? users.value.filter(u => (u.name || '').toLowerCase().includes(k)) : users.value
  // 생산 부서를 위로
  return [...list].sort((a, b) => (a.department === 'PRODUCTION' ? -1 : 0) - (b.department === 'PRODUCTION' ? -1 : 0))
})

async function load() {
  loading.value = true
  try {
    const data = await productionRequestApi.getNotifyRecipients()
    users.value = data.users || []
    const r = data.recipients || { requested: data.user_ids || [], in_progress: [], shipped: [] }
    recipients.requested = r.requested || []
    recipients.in_progress = r.in_progress || []
    recipients.shipped = r.shipped || []
  } catch {
    toast.error('수신자 정보를 불러오지 못했습니다')
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await productionRequestApi.setNotifyRecipients({
      requested: recipients.requested,
      in_progress: recipients.in_progress,
      shipped: recipients.shipped,
    })
    toast.success('단계별 알림 수신자가 저장되었습니다')
    emit('close')
  } catch {
    toast.error('저장에 실패했습니다 (관리자만 지정 가능)')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
