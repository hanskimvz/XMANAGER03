<template>
  <div class="user-management-panel">
    <!-- 상단: 추가 버튼 / 새로고침 -->
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-sm font-bold text-gray-700">사용자 계정 목록 <span class="font-normal text-gray-400">({{ users.length }}명)</span></h3>
      <div class="flex gap-2">
        <button
          @click="loadUsers"
          :disabled="listLoading"
          class="px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
        >새로고침</button>
        <button
          @click="openCreate"
          class="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >+ 사용자 추가</button>
      </div>
    </div>

    <!-- 목록 표 -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <div v-if="listLoading" class="py-10 text-center text-gray-500 text-sm">로딩 중...</div>
      <table v-else class="min-w-full text-sm">
        <thead>
          <tr class="bg-gray-50 text-left text-gray-600">
            <th class="px-3 py-2 font-medium">아이디</th>
            <th class="px-3 py-2 font-medium">이름</th>
            <th class="px-3 py-2 font-medium">역할</th>
            <th class="px-3 py-2 font-medium">부서</th>
            <th class="px-3 py-2 font-medium">직급</th>
            <th class="px-3 py-2 font-medium">기본결재자</th>
            <th class="px-3 py-2 font-medium">활성</th>
            <th class="px-3 py-2 font-medium text-right">작업</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="u in users" :key="u.id" class="hover:bg-gray-50">
            <td class="px-3 py-2 font-mono text-blue-600 whitespace-nowrap">{{ u.username }}</td>
            <td class="px-3 py-2 text-gray-800 whitespace-nowrap">{{ u.name }}</td>
            <td class="px-3 py-2 whitespace-nowrap">
              <span
                class="px-2 py-0.5 text-xs font-medium rounded-full"
                :class="u.role === 'ADMIN' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'"
              >{{ u.role }}</span>
            </td>
            <td class="px-3 py-2 text-gray-700 whitespace-nowrap">{{ departmentLabel(u.department) }}</td>
            <td class="px-3 py-2 text-gray-700 whitespace-nowrap">{{ u.position || '-' }}</td>
            <td class="px-3 py-2 text-gray-700 whitespace-nowrap">
              {{ approverName(u.approver_id) }}<template v-if="u.approver2_id">, {{ approverName(u.approver2_id) }}</template>
            </td>
            <td class="px-3 py-2 whitespace-nowrap">
              <span
                class="px-2 py-0.5 text-xs font-medium rounded-full"
                :class="u.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
              >{{ u.is_active ? '활성' : '비활성' }}</span>
            </td>
            <td class="px-3 py-2 text-right whitespace-nowrap">
              <button
                @click="openEdit(u)"
                class="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 mr-1"
              >수정</button>
              <button
                @click="onToggleActive(u)"
                class="px-3 py-1 text-xs rounded text-white mr-1"
                :class="u.is_active ? 'bg-yellow-500 hover:bg-yellow-600' : 'bg-green-600 hover:bg-green-700'"
              >{{ u.is_active ? '비활성화' : '활성화' }}</button>
              <button
                @click="openResetPassword(u)"
                class="px-3 py-1 text-xs bg-indigo-500 text-white rounded hover:bg-indigo-600 mr-1"
              >비번 초기화</button>
              <button
                @click="onDelete(u)"
                class="px-3 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600"
              >삭제</button>
            </td>
          </tr>
          <tr v-if="!users.length">
            <td colspan="8" class="px-3 py-10 text-center text-gray-400">사용자가 없습니다.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 생성 / 수정 모달 -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="formOpen"
          class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
          @click.self="closeForm"
        >
          <div class="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div class="flex justify-between items-center px-5 py-3 border-b sticky top-0 bg-white z-10">
              <h3 class="text-lg font-bold text-gray-800">{{ isEdit ? '사용자 수정' : '사용자 추가' }}</h3>
              <button class="text-gray-400 hover:text-gray-700 text-2xl leading-none" @click="closeForm">&times;</button>
            </div>
            <div class="p-5 space-y-3">
              <!-- 아이디 (생성 시만) -->
              <div v-if="!isEdit">
                <label class="block text-xs text-gray-500 mb-1">아이디 <span class="text-red-500">*</span></label>
                <input
                  v-model="form.username"
                  type="text"
                  placeholder="로그인 아이디"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div v-else>
                <label class="block text-xs text-gray-500 mb-1">아이디</label>
                <input
                  :value="editingUser?.username"
                  type="text"
                  disabled
                  class="w-full px-3 py-2 border border-gray-200 rounded-md text-sm bg-gray-100 text-gray-500"
                />
              </div>

              <!-- 비밀번호 (생성 시만) -->
              <div v-if="!isEdit">
                <label class="block text-xs text-gray-500 mb-1">비밀번호 <span class="text-red-500">*</span></label>
                <input
                  v-model="form.password"
                  type="password"
                  placeholder="초기 비밀번호 (8자 이상, 영문+숫자)"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p class="text-[11px] text-gray-400 mt-1">비밀번호는 8자 이상, 영문과 숫자를 모두 포함해야 합니다.</p>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs text-gray-500 mb-1">이름 <span class="text-red-500">*</span></label>
                  <input
                    v-model="form.name"
                    type="text"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">영문 이름</label>
                  <input
                    v-model="form.name_en"
                    type="text"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label class="block text-xs text-gray-500 mb-1">이메일</label>
                <input
                  v-model="form.email"
                  type="email"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs text-gray-500 mb-1">역할 <span class="text-red-500">*</span></label>
                  <select
                    v-model="form.role"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="USER">USER</option>
                    <option value="ADMIN">ADMIN</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">부서</label>
                  <select
                    v-model="form.department"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">선택 안 함</option>
                    <option v-for="d in departments" :key="d.id" :value="d.code">{{ d.name }}</option>
                  </select>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs text-gray-500 mb-1">직급</label>
                  <input
                    v-model="form.position"
                    type="text"
                    list="position-suggestions"
                    placeholder="예: 과장"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <datalist id="position-suggestions">
                    <option v-for="p in POSITION_SUGGESTIONS" :key="p" :value="p" />
                  </datalist>
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">기본 결재자 1</label>
                  <select
                    v-model="form.approver_id"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option :value="null">없음</option>
                    <option v-for="a in approverOptions" :key="a.id" :value="a.id">
                      {{ a.name }} ({{ a.username }})
                    </option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">기본 결재자 2</label>
                  <select
                    v-model="form.approver2_id"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option :value="null">없음</option>
                    <option v-for="a in approver2Options" :key="a.id" :value="a.id">
                      {{ a.name }} ({{ a.username }})
                    </option>
                  </select>
                </div>
              </div>
              <p class="text-[11px] text-gray-400 -mt-1">기안 작성 시 결재선에 1차→2차 순서로 자동 추가됩니다.</p>

              <!-- 휴가 전용 결재선 / 참조자 (v0.51.0) -->
              <div class="border rounded-md p-3 bg-gray-50/60 space-y-3">
                <div class="text-xs font-semibold text-gray-600">휴가 결재선 / 참조자 <span class="font-normal text-gray-400">(휴가 신청서 전용)</span></div>

                <!-- 휴가 결재선 (순서 지정) -->
                <div>
                  <label class="block text-xs text-gray-500 mb-1">휴가 결재선 (순서대로)</label>
                  <div class="flex gap-2">
                    <select v-model.number="leaveApproverPick" class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                      <option :value="null">결재자 선택…</option>
                      <option v-for="a in approverOptions" :key="a.id" :value="a.id" :disabled="form.leave_approver_ids.includes(a.id)">
                        {{ a.name }} ({{ a.username }})
                      </option>
                    </select>
                    <button type="button" class="px-3 py-2 bg-gray-600 text-white text-sm rounded-md hover:bg-gray-700" @click="addLeaveApprover">추가</button>
                  </div>
                  <ul v-if="form.leave_approver_ids.length" class="mt-2 space-y-1">
                    <li v-for="(id, idx) in form.leave_approver_ids" :key="id" class="flex items-center gap-2 bg-white border rounded px-2 py-1 text-sm">
                      <span class="w-5 text-center text-xs text-gray-400">{{ idx + 1 }}</span>
                      <span class="flex-1 truncate">{{ leaveUserName(id) }}</span>
                      <button type="button" class="text-gray-400 hover:text-gray-700 disabled:opacity-30" :disabled="idx === 0" @click="moveLeaveApprover(idx, -1)">▲</button>
                      <button type="button" class="text-gray-400 hover:text-gray-700 disabled:opacity-30" :disabled="idx === form.leave_approver_ids.length - 1" @click="moveLeaveApprover(idx, 1)">▼</button>
                      <button type="button" class="text-red-400 hover:text-red-600" @click="removeLeaveApprover(id)">✕</button>
                    </li>
                  </ul>
                </div>

                <!-- 휴가 참조자 -->
                <div>
                  <label class="block text-xs text-gray-500 mb-1">휴가 참조자</label>
                  <div class="flex gap-2">
                    <select v-model.number="leaveRefPick" class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                      <option :value="null">참조자 선택…</option>
                      <option v-for="a in approverOptions" :key="a.id" :value="a.id" :disabled="form.leave_reference_ids.includes(a.id)">
                        {{ a.name }} ({{ a.username }})
                      </option>
                    </select>
                    <button type="button" class="px-3 py-2 bg-gray-600 text-white text-sm rounded-md hover:bg-gray-700" @click="addLeaveRef">추가</button>
                  </div>
                  <div v-if="form.leave_reference_ids.length" class="mt-2 flex flex-wrap gap-1.5">
                    <span v-for="id in form.leave_reference_ids" :key="id" class="inline-flex items-center gap-1 bg-white border rounded-full px-2 py-0.5 text-xs">
                      {{ leaveUserName(id) }}
                      <button type="button" class="text-red-400 hover:text-red-600" @click="removeLeaveRef(id)">✕</button>
                    </span>
                  </div>
                </div>

                <p class="text-[11px] text-gray-400">휴가 신청서 작성 시 이 결재선·참조자가 자동 적용됩니다. <b>미지정 시 위 기본 결재자</b>로 채워집니다.</p>
              </div>

              <!-- 입사일 / 퇴사일 (연차 발생 기준) -->
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs text-gray-500 mb-1">입사일 <span class="text-gray-400">(연차 발생 기준)</span></label>
                  <input
                    v-model="form.hire_date"
                    type="date"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">퇴사일 <span class="text-gray-400">(재직중=비움)</span></label>
                  <input
                    v-model="form.resign_date"
                    type="date"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <!-- 활성 토글 (수정 시만) -->
              <div v-if="isEdit" class="flex items-center gap-2 pt-1">
                <input id="form-active" v-model="form.is_active" type="checkbox" class="h-4 w-4" />
                <label for="form-active" class="text-sm text-gray-700">활성 계정</label>
              </div>
            </div>
            <div class="px-5 py-3 border-t flex justify-end gap-2">
              <button
                @click="closeForm"
                class="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
              >취소</button>
              <button
                @click="onSubmitForm"
                :disabled="saving"
                class="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >{{ saving ? '저장 중...' : '저장' }}</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 비밀번호 초기화 모달 -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="pwOpen"
          class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
          @click.self="pwOpen = false"
        >
          <div class="bg-white rounded-lg shadow-xl w-full max-w-sm">
            <div class="flex justify-between items-center px-5 py-3 border-b">
              <h3 class="text-lg font-bold text-gray-800">비밀번호 초기화</h3>
              <button class="text-gray-400 hover:text-gray-700 text-2xl leading-none" @click="pwOpen = false">&times;</button>
            </div>
            <div class="p-5 space-y-3">
              <p class="text-sm text-gray-600">
                <span class="font-semibold">{{ pwUser?.name }}</span> ({{ pwUser?.username }}) 의 새 비밀번호를 입력하세요.
              </p>
              <input
                v-model="newPassword"
                type="password"
                placeholder="새 비밀번호 (8자 이상, 영문+숫자)"
                class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                @keyup.enter="onResetPassword"
              />
              <p class="text-[11px] text-gray-400 mt-1">비밀번호는 8자 이상, 영문과 숫자를 모두 포함해야 합니다.</p>
            </div>
            <div class="px-5 py-3 border-t flex justify-end gap-2">
              <button
                @click="pwOpen = false"
                class="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
              >취소</button>
              <button
                @click="onResetPassword"
                :disabled="saving || !newPassword.trim()"
                class="px-4 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >{{ saving ? '처리 중...' : '초기화' }}</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from '@/composables/useToast'
import { useAuth } from '@/stores/auth'
import {
  userApi,
  POSITION_SUGGESTIONS,
  type ManagedUser,
  type UserRole,
  type UserCreatePayload,
  type UserUpdatePayload,
} from '@/api/user'
import { departments, departmentLabel, loadDepartments } from '@/api/department'

const { success, error, warning } = useToast()
const { user: currentUser } = useAuth()

// ─────────── 목록 ───────────
const users = ref<ManagedUser[]>([])
const listLoading = ref(false)
const saving = ref(false)

const userById = computed<Record<number, ManagedUser>>(() => {
  const map: Record<number, ManagedUser> = {}
  for (const u of users.value) map[u.id] = u
  return map
})

const approverName = (id?: number | null): string => {
  if (!id) return '-'
  return userById.value[id]?.name || '-'
}

const loadUsers = async () => {
  listLoading.value = true
  try {
    users.value = await userApi.list()
  } catch {
    error('사용자 목록을 불러오지 못했습니다')
  } finally {
    listLoading.value = false
  }
}

// ─────────── 생성 / 수정 폼 ───────────
interface UserForm {
  username: string
  password: string
  name: string
  name_en: string
  email: string
  role: UserRole
  department: string
  position: string
  approver_id: number | null
  approver2_id: number | null
  leave_approver_ids: number[]
  leave_reference_ids: number[]
  hire_date: string
  resign_date: string
  is_active: boolean
}

const emptyForm = (): UserForm => ({
  username: '',
  password: '',
  name: '',
  name_en: '',
  email: '',
  role: 'USER',
  department: '',
  position: '',
  approver_id: null,
  approver2_id: null,
  leave_approver_ids: [],
  leave_reference_ids: [],
  hire_date: '',
  resign_date: '',
  is_active: true,
})

const formOpen = ref(false)
const isEdit = ref(false)
const editingUser = ref<ManagedUser | null>(null)
const form = ref<UserForm>(emptyForm())

// 기본 결재자 옵션 (수정 중인 본인 제외)
const approverOptions = computed(() =>
  users.value.filter((u) => !editingUser.value || u.id !== editingUser.value.id),
)
// 2차 결재자 옵션: 본인 + 1차로 선택된 사람 제외(중복 방지)
const approver2Options = computed(() =>
  approverOptions.value.filter((u) => u.id !== form.value.approver_id),
)

// --- 휴가 전용 결재선/참조자 (관리자 지정, v0.51.0) ---
const leaveApproverPick = ref<number | null>(null)
const leaveRefPick = ref<number | null>(null)

function leaveUserName(id: number): string {
  const u = users.value.find((x) => x.id === id)
  return u ? `${u.name} (${u.username})` : `#${id}`
}
function addLeaveApprover() {
  const id = leaveApproverPick.value
  if (!id || form.value.leave_approver_ids.includes(id)) return
  form.value.leave_approver_ids.push(id)
  leaveApproverPick.value = null
}
function removeLeaveApprover(id: number) {
  form.value.leave_approver_ids = form.value.leave_approver_ids.filter((x) => x !== id)
}
function moveLeaveApprover(idx: number, dir: -1 | 1) {
  const arr = form.value.leave_approver_ids
  const j = idx + dir
  if (j < 0 || j >= arr.length) return
  const a = arr[idx]!
  arr[idx] = arr[j]!
  arr[j] = a
}
function addLeaveRef() {
  const id = leaveRefPick.value
  if (!id || form.value.leave_reference_ids.includes(id)) return
  form.value.leave_reference_ids.push(id)
  leaveRefPick.value = null
}
function removeLeaveRef(id: number) {
  form.value.leave_reference_ids = form.value.leave_reference_ids.filter((x) => x !== id)
}

const openCreate = () => {
  isEdit.value = false
  editingUser.value = null
  form.value = emptyForm()
  formOpen.value = true
}

const openEdit = (u: ManagedUser) => {
  isEdit.value = true
  editingUser.value = u
  form.value = {
    username: u.username,
    password: '',
    name: u.name,
    name_en: u.name_en || '',
    email: u.email || '',
    role: u.role,
    department: u.department || '',
    position: u.position || '',
    approver_id: u.approver_id ?? null,
    approver2_id: u.approver2_id ?? null,
    leave_approver_ids: [...(u.leave_approver_ids ?? [])],
    leave_reference_ids: [...(u.leave_reference_ids ?? [])],
    hire_date: u.hire_date || '',
    resign_date: u.resign_date || '',
    is_active: u.is_active,
  }
  formOpen.value = true
}

const closeForm = () => {
  formOpen.value = false
}

const onSubmitForm = async () => {
  if (!form.value.name.trim()) {
    warning('이름을 입력하세요')
    return
  }
  saving.value = true
  try {
    if (isEdit.value && editingUser.value) {
      const payload: UserUpdatePayload = {
        name: form.value.name.trim(),
        name_en: form.value.name_en.trim() || undefined,
        email: form.value.email.trim() || undefined,
        role: form.value.role,
        department: form.value.department || undefined,
        position: form.value.position.trim() || undefined,
        approver_id: form.value.approver_id,
        approver2_id: form.value.approver2_id,
        leave_approver_ids: form.value.leave_approver_ids,
        leave_reference_ids: form.value.leave_reference_ids,
        hire_date: form.value.hire_date || null,
        resign_date: form.value.resign_date || null,
        is_active: form.value.is_active,
      }
      await userApi.update(editingUser.value.id, payload)
      success('사용자가 수정되었습니다')
    } else {
      if (!form.value.username.trim()) {
        warning('아이디를 입력하세요')
        saving.value = false
        return
      }
      if (!form.value.password.trim()) {
        warning('비밀번호를 입력하세요')
        saving.value = false
        return
      }
      const pwErr = passwordPolicyError(form.value.password)
      if (pwErr) {
        warning(pwErr)
        saving.value = false
        return
      }
      if (form.value.username.trim().length < 2) {
        warning('아이디는 2자 이상이어야 합니다')
        saving.value = false
        return
      }
      const payload: UserCreatePayload = {
        username: form.value.username.trim(),
        password: form.value.password,
        name: form.value.name.trim(),
        name_en: form.value.name_en.trim() || undefined,
        email: form.value.email.trim() || undefined,
        role: form.value.role,
        department: form.value.department || undefined,
        position: form.value.position.trim() || undefined,
        approver_id: form.value.approver_id,
        approver2_id: form.value.approver2_id,
        leave_approver_ids: form.value.leave_approver_ids,
        leave_reference_ids: form.value.leave_reference_ids,
        hire_date: form.value.hire_date || undefined,
        resign_date: form.value.resign_date || undefined,
      }
      await userApi.create(payload)
      success('사용자가 생성되었습니다')
    }
    formOpen.value = false
    await loadUsers()
  } catch (e: unknown) {
    const resp = (e as { response?: { status?: number; data?: { detail?: unknown } } })?.response
    const status = resp?.status
    if (!isEdit.value && status === 400) {
      error('이미 존재하는 아이디입니다')
    } else if (status === 422) {
      // 서버 검증 실패(예: 비밀번호 4자 미만) — 구체 메시지 표시
      const d = resp?.data?.detail
      const msg = Array.isArray(d) && d[0] && typeof d[0] === 'object'
        ? ((d[0] as { msg?: string }).msg || '')
        : ''
      error(msg ? `입력값 오류: ${msg}` : '입력값을 확인하세요 (비밀번호 8자 이상·영문+숫자, 아이디 2자 이상)')
    } else {
      error(isEdit.value ? '사용자 수정에 실패했습니다' : '사용자 생성에 실패했습니다')
    }
  } finally {
    saving.value = false
  }
}

// ─────────── 활성 토글 ───────────
const onToggleActive = async (u: ManagedUser) => {
  if (u.id === currentUser.value?.id && u.is_active) {
    warning('본인 계정은 비활성화할 수 없습니다')
    return
  }
  try {
    await userApi.update(u.id, { is_active: !u.is_active })
    success(u.is_active ? '비활성화되었습니다' : '활성화되었습니다')
    await loadUsers()
  } catch {
    error('상태 변경에 실패했습니다')
  }
}

// ─────────── 비밀번호 초기화 ───────────
const pwOpen = ref(false)
const pwUser = ref<ManagedUser | null>(null)
const newPassword = ref('')

// 백엔드 정책(validate_password_strength)과 일치: 8자 이상 + 영문·숫자 혼합
function passwordPolicyError(pw: string): string | null {
  if (!pw || pw.length < 8) return '비밀번호는 8자 이상이어야 합니다'
  if (!/[A-Za-z]/.test(pw) || !/[0-9]/.test(pw)) return '비밀번호는 영문과 숫자를 모두 포함해야 합니다'
  return null
}

const openResetPassword = (u: ManagedUser) => {
  pwUser.value = u
  newPassword.value = ''
  pwOpen.value = true
}

const onResetPassword = async () => {
  if (!pwUser.value) return
  const pwErr = passwordPolicyError(newPassword.value)
  if (pwErr) {
    warning(pwErr)
    return
  }
  saving.value = true
  try {
    await userApi.resetPassword(pwUser.value.id, newPassword.value)
    success('비밀번호가 초기화되었습니다')
    pwOpen.value = false
  } catch (e: unknown) {
    const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
    const msg = Array.isArray(d) && d[0] && typeof d[0] === 'object'
      ? ((d[0] as { msg?: string }).msg || '')
      : (typeof d === 'string' ? d : '')
    error(msg ? `초기화 실패: ${msg}` : '비밀번호 초기화에 실패했습니다')
  } finally {
    saving.value = false
  }
}

// ─────────── 삭제 ───────────
const onDelete = async (u: ManagedUser) => {
  if (u.id === currentUser.value?.id) {
    warning('본인 계정은 삭제할 수 없습니다')
    return
  }
  if (u.role === 'ADMIN') {
    const adminCount = users.value.filter((x) => x.role === 'ADMIN').length
    if (adminCount <= 1) {
      warning('유일한 관리자 계정은 삭제할 수 없습니다')
      return
    }
  }
  if (!confirm(`'${u.name}' (${u.username}) 계정을 삭제하시겠습니까?`)) return
  try {
    await userApi.remove(u.id)
    success('사용자가 삭제되었습니다')
    await loadUsers()
  } catch {
    error('사용자 삭제에 실패했습니다')
  }
}

loadUsers()
loadDepartments() // 부서 드롭다운/라벨용 마스터 로드
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
