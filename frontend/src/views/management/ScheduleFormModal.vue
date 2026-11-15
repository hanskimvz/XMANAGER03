<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { useAuth } from '@/stores/auth'
import { approvalApi, type ApproverCandidate } from '@/api/approval'
import { scheduleApi, SCHEDULE_TYPES, type ScheduleItem, type ScheduleType } from '@/api/schedule'

const props = defineProps<{ schedule?: ScheduleItem | null; defaultDate?: string }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'saved', item: ScheduleItem): void }>()
const { success, error, warning } = useToast()
const { user } = useAuth()

const isEdit = computed(() => !!props.schedule)
const busy = ref(false)

const scheduleType = ref<ScheduleType>(props.schedule?.schedule_type || 'EVENT')
const title = ref(props.schedule?.title || '')
const targetUserId = ref<number | null>(props.schedule?.target_user_id ?? null)
const startDate = ref(props.schedule?.start_date || props.defaultDate || '')
// 하루짜리 일정은 종료일 칸을 비워 둔다(등록 화면과 같은 모양)
const endDate = ref(
  props.schedule && props.schedule.end_date !== props.schedule.start_date ? props.schedule.end_date : '',
)
const location = ref(props.schedule?.location || '')
const memo = ref(props.schedule?.memo || '')

// 행사는 전사 일정이라 대상자가 없다
const needsTarget = computed(() => scheduleType.value !== 'EVENT')

const titlePlaceholder = computed(() => ({
  EVENT: '예: 전사 워크숍',
  LEAVE: '예: 연차',
  FIELDWORK: '예: 고객사 방문',
  TRIP: '예: 부산 출장',
}[scheduleType.value]))

// 대상자 후보(활성 사용자) — 전자결재의 결재자 후보 API 재사용
const users = ref<ApproverCandidate[]>([])
onMounted(async () => {
  try {
    users.value = (await approvalApi.getApprovers()).data || []
  } catch (e: any) {
    error(e?.response?.data?.detail || '대상자 목록 로드 실패')
  }
})

function userLabel(u: ApproverCandidate) {
  const extra = [u.department, u.position].filter(Boolean).join(' ')
  return extra ? `${u.name} (${extra})` : u.name
}

// 휴가/외근/출장으로 바꾸면 대상자를 본인으로 기본 선택
function onTypeChange() {
  if (needsTarget.value && targetUserId.value === null) targetUserId.value = user.value?.id ?? null
}

async function submit() {
  if (busy.value) return // 중복 제출(더블클릭) 방지
  if (!title.value.trim()) return warning('제목을 입력하세요')
  if (!startDate.value) return warning('시작일을 선택하세요')
  if (endDate.value && endDate.value < startDate.value) return warning('종료일은 시작일보다 빠를 수 없습니다')
  if (needsTarget.value && targetUserId.value === null) return warning('대상자를 선택하세요')
  busy.value = true
  try {
    const payload = {
      schedule_type: scheduleType.value,
      title: title.value.trim(),
      target_user_id: needsTarget.value ? targetUserId.value : null,
      start_date: startDate.value,
      end_date: endDate.value || null,
      location: location.value.trim() || null,
      memo: memo.value.trim() || null,
    }
    const saved = isEdit.value && props.schedule
      ? await scheduleApi.update(props.schedule.id, payload)
      : await scheduleApi.create(payload)
    success(isEdit.value ? '일정이 수정되었습니다' : '일정이 등록되었습니다')
    emit('saved', saved)
  } catch (e: any) {
    error(e?.response?.data?.detail || '저장 실패')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-xl flex flex-col max-h-[92vh]">
      <div class="flex items-center justify-between px-5 py-3 border-b">
        <h3 class="text-base font-semibold text-gray-800">{{ isEdit ? '일정 수정' : '일정 등록' }}</h3>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600" aria-label="닫기">✕</button>
      </div>

      <div class="px-5 py-4 space-y-4 overflow-y-auto">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="lbl">유형 <span class="text-red-500">*</span></label>
            <select v-model="scheduleType" class="inp w-full" @change="onTypeChange">
              <option v-for="t in SCHEDULE_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <div v-if="needsTarget">
            <label class="lbl">대상자 <span class="text-red-500">*</span></label>
            <select v-model="targetUserId" class="inp w-full">
              <option :value="null" disabled>대상자를 선택하세요</option>
              <option v-for="u in users" :key="u.id" :value="u.id">{{ userLabel(u) }}</option>
            </select>
          </div>
        </div>

        <div>
          <label class="lbl">제목 <span class="text-red-500">*</span></label>
          <input v-model="title" class="inp w-full" :placeholder="titlePlaceholder" maxlength="200" />
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="lbl">시작일 <span class="text-red-500">*</span></label>
            <input v-model="startDate" type="date" class="inp w-full" />
          </div>
          <div>
            <label class="lbl">종료일</label>
            <input v-model="endDate" type="date" class="inp w-full" :min="startDate || undefined" />
          </div>
        </div>

        <div>
          <label class="lbl">장소</label>
          <input v-model="location" class="inp w-full" placeholder="행사 장소 / 방문지" maxlength="200" />
        </div>

        <div>
          <label class="lbl">메모</label>
          <textarea v-model="memo" rows="3" class="inp w-full" placeholder="세부 내용을 입력하세요" maxlength="2000"></textarea>
        </div>
      </div>

      <div class="px-5 py-3 border-t flex justify-end gap-2">
        <button type="button" @click="emit('close')" class="px-3 py-2 text-sm text-gray-600 border rounded-md hover:bg-gray-50">취소</button>
        <button :disabled="busy" @click="submit" class="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50">
          {{ busy ? '저장 중...' : '저장' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.inp { @apply px-2.5 py-1.5 border border-gray-300 rounded-md text-sm bg-white focus:outline-none focus:ring-1 focus:ring-blue-500; }
.lbl { @apply block text-xs text-gray-500 mb-1; }
</style>
