<template>
  <div class="bg-white rounded-lg shadow p-5 max-w-2xl">
    <h3 class="text-sm font-bold text-gray-700 mb-1">지출결의서 집행 담당 지정</h3>
    <p class="text-xs text-gray-500 mb-4">
      지정한 사람이 지출결의서 작성 시 <b>결재선에 자동으로</b> 들어갑니다(아래 순서대로). 여러 명이면 순서대로 결재합니다.
      마지막 결재자의 <b>승인 = 집행 완료</b>입니다.
    </p>

    <div v-if="loading" class="py-6 text-center text-gray-500 text-sm">로딩 중...</div>
    <template v-else>
      <!-- 현재 지정 목록 -->
      <ol class="space-y-2 mb-4">
        <li v-for="(a, i) in selected" :key="a.id" class="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded px-3 py-2">
          <span class="w-5 text-center text-xs font-bold text-gray-400">{{ i + 1 }}</span>
          <span class="text-sm text-gray-800">{{ a.name }}</span>
          <span class="text-xs text-gray-400">{{ a.position || '' }} {{ deptLabel(a.department) }}</span>
          <span class="text-xs font-mono text-gray-300">{{ a.username }}</span>
          <div class="ml-auto flex items-center gap-1">
            <button class="px-1.5 text-gray-400 hover:text-gray-700 disabled:opacity-30" :disabled="i === 0" title="위로" @click="move(i, -1)">▲</button>
            <button class="px-1.5 text-gray-400 hover:text-gray-700 disabled:opacity-30" :disabled="i === selected.length - 1" title="아래로" @click="move(i, 1)">▼</button>
            <button class="px-2 py-0.5 text-xs bg-red-500 text-white rounded hover:bg-red-600" @click="remove(i)">제거</button>
          </div>
        </li>
        <li v-if="!selected.length" class="text-sm text-gray-400 py-2">지정된 집행 담당이 없습니다. 아래에서 추가하세요. (미지정 시 작성자의 기본 결재자로 채워집니다.)</li>
      </ol>

      <!-- 추가 -->
      <div class="flex items-center gap-2 mb-4">
        <select v-model="addId" class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option :value="null">+ 집행 담당 추가…</option>
          <option v-for="u in addable" :key="u.id" :value="u.id">{{ u.name }} ({{ u.username }}){{ u.position ? ' · ' + u.position : '' }}</option>
        </select>
        <button class="px-3 py-2 text-sm bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-40" :disabled="addId == null" @click="add">추가</button>
      </div>

      <div class="flex justify-end gap-2">
        <button class="px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50" @click="load">되돌리기</button>
        <button class="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50" :disabled="saving" @click="save">{{ saving ? '저장 중...' : '저장' }}</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { settingsApi, type DisbApprover } from '@/api/settings'
import { userApi, type ManagedUser } from '@/api/user'
import { departmentLabel } from '@/api/department'

const { success, error } = useToast()

const loading = ref(false)
const saving = ref(false)
const selected = ref<DisbApprover[]>([])
const users = ref<ManagedUser[]>([])
const addId = ref<number | null>(null)

const deptLabel = (c?: string | null) => (c ? departmentLabel(c) : '')

const addable = computed(() =>
  users.value.filter((u) => u.is_active && !selected.value.some((s) => s.id === u.id)),
)

const load = async () => {
  loading.value = true
  try {
    const [aps, us] = await Promise.all([
      settingsApi.getDisbursementApprovers(),
      userApi.list().catch(() => [] as ManagedUser[]),
    ])
    selected.value = aps
    users.value = us
  } catch {
    error('집행 담당 설정을 불러오지 못했습니다')
  } finally {
    loading.value = false
  }
}

const add = () => {
  const u = users.value.find((x) => x.id === addId.value)
  if (u) selected.value.push({ id: u.id, name: u.name, username: u.username, position: u.position, department: u.department })
  addId.value = null
}
const remove = (i: number) => selected.value.splice(i, 1)
const move = (i: number, d: number) => {
  const j = i + d
  const arr = selected.value
  if (j < 0 || j >= arr.length) return
  const [item] = arr.splice(i, 1)
  if (item) arr.splice(j, 0, item)
}

const save = async () => {
  saving.value = true
  try {
    selected.value = await settingsApi.setDisbursementApprovers(selected.value.map((a) => a.id))
    success('집행 담당이 저장되었습니다')
  } catch {
    error('저장에 실패했습니다')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
