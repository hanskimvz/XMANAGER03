<template>
  <div class="role-permission-panel">
    <!-- 하위 탭: 역할/권한 매트릭스 · 사용자 역할 배정 (상위 페이지가 탭을 제어하면 숨김) -->
    <div v-if="!hideTabs" class="flex gap-2 mb-4 border-b border-gray-200">
      <button
        class="px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors"
        :class="subTab === 'roles' ? 'text-blue-600 border-blue-600' : 'text-gray-500 border-transparent hover:text-blue-600'"
        @click="subTab = 'roles'"
      >역할 · 권한 매트릭스</button>
      <button
        class="px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors"
        :class="subTab === 'assign' ? 'text-blue-600 border-blue-600' : 'text-gray-500 border-transparent hover:text-blue-600'"
        @click="subTab = 'assign'"
      >사용자 역할 배정</button>
    </div>

    <!-- ════════════ 역할 · 권한 매트릭스 ════════════ -->
    <div v-show="subTab === 'roles'" class="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-4">
      <!-- 좌측: 역할 목록 -->
      <div class="bg-white rounded-lg shadow">
        <div class="flex justify-between items-center px-4 py-3 border-b">
          <h3 class="text-sm font-bold text-gray-700">역할 <span class="font-normal text-gray-400">({{ roles.length }})</span></h3>
          <button
            class="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-md hover:bg-blue-700"
            @click="openCreateRole"
          >+ 역할 추가</button>
        </div>
        <div v-if="rolesLoading" class="py-10 text-center text-gray-500 text-sm">로딩 중...</div>
        <ul v-else class="divide-y divide-gray-100">
          <li
            v-for="(r, idx) in roles"
            :key="r.id"
            draggable="true"
            class="group relative pl-4 pr-3 py-3 cursor-pointer transition-colors border-l-2"
            :class="[
              selectedRoleId === r.id ? 'bg-blue-50 border-blue-500' : 'border-transparent hover:bg-gray-50',
              dragIndex === idx ? 'opacity-40' : '',
              dropIndex === idx && dragIndex !== null && dragIndex !== idx ? 'ring-2 ring-inset ring-blue-400' : '',
            ]"
            @click="selectRole(r.id)"
            @dragstart="onRoleDragStart(idx, $event)"
            @dragover.prevent="onRoleDragOver(idx)"
            @drop.prevent="onRoleDrop(idx)"
            @dragend="onRoleDragEnd"
          >
            <div class="flex items-start gap-2">
              <span
                class="text-gray-300 group-hover:text-gray-500 select-none cursor-grab pt-0.5 leading-none"
                title="드래그하여 순서 변경"
                @click.stop
              >⠿</span>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5">
                  <span class="text-sm font-semibold text-gray-800 truncate">{{ r.name }}</span>
                  <span v-if="r.is_admin" class="shrink-0 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-purple-100 text-purple-700">전체권한</span>
                  <span v-if="r.is_system" class="shrink-0 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-gray-100 text-gray-600">기본</span>
                </div>
                <div class="flex items-center gap-2 mt-1">
                  <span class="text-xs font-mono text-gray-400 truncate">{{ r.code }}</span>
                  <span
                    class="shrink-0 text-[10px] px-1.5 py-0.5 rounded-full"
                    :class="permCountFor(r) === -1 ? 'bg-purple-50 text-purple-600' : (permCountFor(r) === 0 ? 'bg-gray-100 text-gray-400' : 'bg-emerald-50 text-emerald-600')"
                  >{{ permCountFor(r) === -1 ? '모든 권한' : (permCountFor(r) === 0 ? '권한 없음' : `권한 ${permCountFor(r)}개`) }}</span>
                </div>
                <!-- 액션: 선택/호버 시에만 노출해 목록을 깔끔하게 -->
                <div
                  class="mt-2 flex gap-1 transition-opacity"
                  :class="selectedRoleId === r.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'"
                >
                  <button
                    class="px-2 py-0.5 text-[11px] rounded border border-gray-200 text-gray-600 hover:bg-gray-100"
                    @click.stop="openEditRole(r)"
                  >✎ 수정</button>
                  <button
                    class="px-2 py-0.5 text-[11px] rounded border border-gray-200 text-gray-600 hover:bg-gray-100"
                    title="이 역할의 권한을 복사해 새 역할 생성"
                    @click.stop="openCloneRole(r)"
                  >⎘ 복제</button>
                  <button
                    class="px-2 py-0.5 text-[11px] rounded border"
                    :class="r.is_system ? 'border-gray-100 text-gray-300 cursor-not-allowed' : 'border-red-200 text-red-600 hover:bg-red-50'"
                    :disabled="r.is_system"
                    :title="r.is_system ? '기본(시스템) 역할은 삭제할 수 없습니다' : '삭제'"
                    @click.stop="onDeleteRole(r)"
                  >🗑 삭제</button>
                </div>
              </div>
            </div>
          </li>
          <li v-if="!roles.length" class="px-4 py-10 text-center text-gray-400 text-sm">역할이 없습니다.</li>
        </ul>
      </div>

      <!-- 우측: 권한 매트릭스 -->
      <div class="bg-white rounded-lg shadow">
        <div v-if="!selectedRole" class="py-16 text-center text-gray-400 text-sm">
          ← 좌측에서 역할을 선택하세요.
        </div>

        <template v-else>
          <!-- 헤더: 역할 요약 + 저장 상태 -->
          <div class="px-4 py-3 border-b">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <h3 class="text-base font-bold text-gray-800">{{ selectedRole.name }}</h3>
                  <span class="text-xs font-mono text-gray-400">{{ selectedRole.code }}</span>
                  <span v-if="selectedRole.is_admin" class="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-purple-100 text-purple-700">전체권한</span>
                  <span v-if="selectedRole.is_system" class="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-gray-100 text-gray-600">기본역할</span>
                </div>
                <p v-if="selectedRole.description" class="text-xs text-gray-500 mt-1">{{ selectedRole.description }}</p>
              </div>
              <div v-if="!selectedRole.is_admin" class="flex items-center gap-2 shrink-0">
                <span v-if="isDirty" class="text-xs text-amber-600 font-medium whitespace-nowrap">● 저장 안 됨</span>
                <button
                  v-if="isDirty"
                  class="px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
                  @click="revertPerms"
                >되돌리기</button>
                <button
                  class="px-4 py-2 text-sm text-white rounded-md disabled:opacity-40 disabled:cursor-not-allowed"
                  :class="isDirty ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-300'"
                  :disabled="savingPerms || !isDirty"
                  @click="onSavePermissions"
                >{{ savingPerms ? '저장 중...' : '권한 저장' }}</button>
              </div>
            </div>
            <!-- 선택 권한 요약 (게이지) -->
            <div v-if="!selectedRole.is_admin" class="mt-2.5 flex items-center gap-2">
              <div class="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                <div class="h-full bg-emerald-400 transition-all" :style="{ width: totalPermCodes ? (checked.size / totalPermCodes * 100) + '%' : '0%' }"></div>
              </div>
              <span class="text-xs text-gray-500 whitespace-nowrap">선택 <b class="text-gray-800">{{ checked.size }}</b> / {{ totalPermCodes }}</span>
            </div>
          </div>

          <!-- is_admin: 와일드카드 안내 -->
          <div v-if="selectedRole.is_admin" class="m-4 p-4 rounded-md bg-purple-50 text-purple-800 text-sm flex items-start gap-2.5">
            <span class="text-lg leading-none">🛡️</span>
            <div>이 역할은 <b>모든 기능의 모든 권한</b>을 가집니다(와일드카드). 개별 권한을 설정할 필요가 없습니다.</div>
          </div>

          <!-- 매트릭스 -->
          <div v-else>
            <div v-if="permsLoading" class="py-10 text-center text-gray-500 text-sm">로딩 중...</div>
            <template v-else>
              <!-- 툴바: 검색 + 일괄 토글 -->
              <div class="flex flex-wrap items-center gap-2 px-4 py-2.5 border-b bg-gray-50">
                <div class="relative flex-1 min-w-[160px]">
                  <input
                    v-model="moduleSearch"
                    type="text"
                    placeholder="기능(모듈) 검색…"
                    class="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm pointer-events-none">🔍</span>
                </div>
                <button class="px-3 py-1.5 text-xs rounded-md border border-emerald-200 text-emerald-700 hover:bg-emerald-50" @click="setAllPerms(true)">모두 허용</button>
                <button class="px-3 py-1.5 text-xs rounded-md border border-gray-200 text-gray-600 hover:bg-gray-100" @click="setAllPerms(false)">모두 해제</button>
              </div>
              <!-- 표 -->
              <div class="overflow-x-auto">
                <table class="min-w-full text-sm border-collapse">
                  <thead>
                    <tr class="text-gray-500 border-b bg-white">
                      <th class="px-3 py-2 text-left font-medium sticky left-0 bg-white z-10 min-w-[120px]">기능</th>
                      <th
                        v-for="act in actionColumns"
                        :key="act"
                        class="px-3 py-2 text-center font-medium whitespace-nowrap"
                      >{{ actionLabel(act) }}</th>
                      <th class="px-3 py-2 text-center font-medium">전체</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="grp in filteredPermissions"
                      :key="grp.module"
                      class="border-b last:border-0 hover:bg-blue-50/40"
                    >
                      <td class="px-3 py-2 whitespace-nowrap sticky left-0 bg-white z-10">
                        <div class="font-medium text-gray-800">{{ grp.label }}</div>
                        <div
                          class="text-[10px] mt-0.5"
                          :class="enabledCountFor(grp) === 0 ? 'text-gray-300' : 'text-emerald-600'"
                        >{{ enabledCountFor(grp) }}/{{ grp.actions.length }} 허용</div>
                      </td>
                      <td
                        v-for="act in actionColumns"
                        :key="act"
                        class="px-3 py-2 text-center"
                      >
                        <input
                          v-if="codeFor(grp, act)"
                          type="checkbox"
                          class="h-4 w-4 cursor-pointer accent-blue-600 align-middle"
                          :checked="checked.has(codeFor(grp, act)!)"
                          @change="toggleCode(codeFor(grp, act)!)"
                        />
                        <span v-else class="text-gray-200 select-none">·</span>
                      </td>
                      <td class="px-3 py-2 text-center bg-gray-50/40">
                        <input
                          type="checkbox"
                          class="h-4 w-4 cursor-pointer accent-blue-600 align-middle"
                          :checked="isModuleAllChecked(grp)"
                          @change="toggleModule(grp, ($event.target as HTMLInputElement).checked)"
                        />
                      </td>
                    </tr>
                    <tr v-if="!filteredPermissions.length">
                      <td :colspan="actionColumns.length + 2" class="px-3 py-10 text-center text-gray-400">
                        {{ moduleSearch ? '검색 결과가 없습니다.' : '권한 정보가 없습니다.' }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </div>
        </template>
      </div>
    </div>

    <!-- ════════════ 사용자 역할 배정 ════════════ -->
    <div v-show="subTab === 'assign'" class="bg-white rounded-lg shadow overflow-hidden">
      <div class="flex justify-between items-center px-4 py-3 border-b">
        <h3 class="text-sm font-bold text-gray-700">사용자 역할 배정 <span class="font-normal text-gray-400">({{ users.length }}명)</span></h3>
        <button
          class="px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          :disabled="usersLoading"
          @click="loadUsersWithRoles"
        >새로고침</button>
      </div>
      <div v-if="usersLoading" class="py-10 text-center text-gray-500 text-sm">로딩 중...</div>
      <table v-else class="min-w-full text-sm">
        <thead>
          <tr class="bg-gray-50 text-left text-gray-600">
            <th class="px-3 py-2 font-medium">아이디</th>
            <th class="px-3 py-2 font-medium">이름</th>
            <th class="px-3 py-2 font-medium">현재 역할</th>
            <th class="px-3 py-2 font-medium text-right">작업</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="u in users" :key="u.id" class="hover:bg-gray-50">
            <td class="px-3 py-2 font-mono text-blue-600 whitespace-nowrap">{{ u.username }}</td>
            <td class="px-3 py-2 text-gray-800 whitespace-nowrap">{{ u.name }}</td>
            <td class="px-3 py-2">
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="r in (userRolesMap[u.id] || [])"
                  :key="r.id"
                  class="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700"
                >{{ r.name }}</span>
                <span v-if="!(userRolesMap[u.id] || []).length" class="text-gray-400 text-xs">역할 없음</span>
              </div>
            </td>
            <td class="px-3 py-2 text-right whitespace-nowrap">
              <button
                class="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700"
                @click="openAssign(u)"
              >역할 배정</button>
            </td>
          </tr>
          <tr v-if="!users.length">
            <td colspan="4" class="px-3 py-10 text-center text-gray-400">사용자가 없습니다.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 역할 생성/수정 모달 -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="roleFormOpen"
          class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
          @click.self="roleFormOpen = false"
        >
          <div class="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div class="flex justify-between items-center px-5 py-3 border-b">
              <h3 class="text-lg font-bold text-gray-800">{{ roleIsEdit ? '역할 수정' : (cloneSourceCodes ? '역할 복제' : '역할 추가') }}</h3>
              <button class="text-gray-400 hover:text-gray-700 text-2xl leading-none" @click="roleFormOpen = false">&times;</button>
            </div>
            <div class="p-5 space-y-3">
              <div>
                <label class="block text-xs text-gray-500 mb-1">코드 <span class="text-red-500">*</span></label>
                <input
                  v-model="roleForm.code"
                  type="text"
                  :disabled="roleIsEdit"
                  placeholder="예: SALES_MANAGER"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                />
                <p v-if="roleIsEdit" class="text-[11px] text-gray-400 mt-1">코드는 수정할 수 없습니다.</p>
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-1">이름 <span class="text-red-500">*</span></label>
                <input
                  v-model="roleForm.name"
                  type="text"
                  placeholder="예: 영업 관리자"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-1">설명</label>
                <textarea
                  v-model="roleForm.description"
                  rows="2"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                ></textarea>
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-1">정렬 순서</label>
                <input
                  v-model.number="roleForm.sort_order"
                  type="number"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div class="px-5 py-3 border-t flex justify-end gap-2">
              <button
                class="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
                @click="roleFormOpen = false"
              >취소</button>
              <button
                class="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                :disabled="roleSaving"
                @click="onSubmitRole"
              >{{ roleSaving ? '저장 중...' : '저장' }}</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 사용자 역할 배정 모달 -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="assignOpen"
          class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
          @click.self="assignOpen = false"
        >
          <div class="bg-white rounded-lg shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div class="flex justify-between items-center px-5 py-3 border-b sticky top-0 bg-white">
              <h3 class="text-lg font-bold text-gray-800">역할 배정</h3>
              <button class="text-gray-400 hover:text-gray-700 text-2xl leading-none" @click="assignOpen = false">&times;</button>
            </div>
            <div class="p-5 space-y-2">
              <p class="text-sm text-gray-600 mb-2">
                <span class="font-semibold">{{ assignUser?.name }}</span> ({{ assignUser?.username }}) 에게 배정할 역할을 선택하세요.
              </p>
              <label
                v-for="r in roles"
                :key="r.id"
                class="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-md cursor-pointer hover:bg-gray-50"
              >
                <input
                  type="checkbox"
                  class="h-4 w-4"
                  :checked="assignSelected.has(r.id)"
                  @change="toggleAssign(r.id)"
                />
                <span class="text-sm text-gray-800">{{ r.name }}</span>
                <span class="text-xs font-mono text-gray-400">{{ r.code }}</span>
                <span v-if="r.is_admin" class="ml-auto px-2 py-0.5 text-[10px] font-medium rounded-full bg-purple-100 text-purple-700">전체권한</span>
              </label>
              <p v-if="!roles.length" class="text-sm text-gray-400 text-center py-4">역할이 없습니다.</p>
            </div>
            <div class="px-5 py-3 border-t flex justify-end gap-2 sticky bottom-0 bg-white">
              <button
                class="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
                @click="assignOpen = false"
              >취소</button>
              <button
                class="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                :disabled="assignSaving"
                @click="onSubmitAssign"
              >{{ assignSaving ? '저장 중...' : '저장' }}</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useToast } from '@/composables/useToast'
import {
  rbacApi,
  type PermissionGroup,
  type Role,
  type RoleCreatePayload,
  type RoleUpdatePayload,
} from '@/api/rbac'
import { userApi, type ManagedUser } from '@/api/user'

const { success, error, warning } = useToast()

// 외부(상위 페이지)에서 서브탭을 제어하고 내부 탭바를 숨길 수 있게 함
const props = defineProps<{
  hideTabs?: boolean
  tab?: 'roles' | 'assign'
}>()

const subTab = ref<'roles' | 'assign'>(props.tab ?? 'roles')
watch(() => props.tab, (t) => { if (t) subTab.value = t })

// ─────────── 역할 / 권한 ───────────
const roles = ref<Role[]>([])
const rolesLoading = ref(false)
const permissions = ref<PermissionGroup[]>([])
const permsLoading = ref(false)
const selectedRoleId = ref<number | null>(null)
const checked = ref<Set<string>>(new Set())
const savingPerms = ref(false)

const selectedRole = computed<Role | null>(
  () => roles.value.find((r) => r.id === selectedRoleId.value) ?? null,
)

// 동작 열(액션) 순서 — 모든 모듈에서 등장하는 action 코드 집합을 안정적 순서로 정렬
const ACTION_ORDER = ['view', 'create', 'edit', 'delete', 'approve', 'export', 'manage', 'ci_delete']
const actionColumns = computed<string[]>(() => {
  const set = new Set<string>()
  for (const grp of permissions.value) {
    for (const a of grp.actions) set.add(a.action)
  }
  return Array.from(set).sort((a, b) => {
    const ia = ACTION_ORDER.indexOf(a)
    const ib = ACTION_ORDER.indexOf(b)
    if (ia === -1 && ib === -1) return a.localeCompare(b)
    if (ia === -1) return 1
    if (ib === -1) return -1
    return ia - ib
  })
})

const ACTION_LABELS: Record<string, string> = {
  view: '조회',
  create: '생성',
  edit: '수정',
  delete: '삭제',
  approve: '승인',
  export: '내보내기',
  manage: '관리',
  backup: '백업',
  ci_delete: 'CI 삭제',
}
// 열 머리글은 "동작"만 표시(조회/생성/수정/삭제…). 백엔드 label은 "코드관리 조회"처럼
// 모듈명이 붙은 전체 라벨이라 열 머리글로 쓰면 안 됨(모듈명이 뒤죽박죽 됨).
const actionLabel = (act: string): string => ACTION_LABELS[act] || act

// 모듈+동작 → 권한코드
const codeFor = (grp: PermissionGroup, act: string): string | null => {
  const found = grp.actions.find((a) => a.action === act)
  return found ? found.code : null
}

const toggleCode = (code: string) => {
  const next = new Set(checked.value)
  if (next.has(code)) next.delete(code)
  else next.add(code)
  checked.value = next
}

const isModuleAllChecked = (grp: PermissionGroup): boolean =>
  grp.actions.length > 0 && grp.actions.every((a) => checked.value.has(a.code))

const toggleModule = (grp: PermissionGroup, on: boolean) => {
  const next = new Set(checked.value)
  for (const a of grp.actions) {
    if (on) next.add(a.code)
    else next.delete(a.code)
  }
  checked.value = next
}

// ─────────── UX 헬퍼 (검색 / 카운트 / 변경감지 / 일괄토글) ───────────
const moduleSearch = ref('')
const filteredPermissions = computed<PermissionGroup[]>(() => {
  const q = moduleSearch.value.trim().toLowerCase()
  if (!q) return permissions.value
  return permissions.value.filter(
    (g) => g.label.toLowerCase().includes(q) || g.module.toLowerCase().includes(q),
  )
})

// 모듈에서 켜진 권한 수
const enabledCountFor = (grp: PermissionGroup): number =>
  grp.actions.filter((a) => checked.value.has(a.code)).length

// 전체 권한 코드 수(이 역할이 가질 수 있는 최대)
const totalPermCodes = computed<number>(() =>
  permissions.value.reduce((n, g) => n + g.actions.length, 0),
)

// 역할 목록 카드용: 역할이 보유한 권한 수 (admin은 -1 = 전체)
const permCountFor = (r: Role): number => (r.is_admin ? -1 : r.permission_codes?.length ?? 0)

// 저장되지 않은 변경 여부
const isDirty = computed<boolean>(() => {
  if (!selectedRole.value || selectedRole.value.is_admin) return false
  const saved = new Set(selectedRole.value.permission_codes ?? [])
  if (saved.size !== checked.value.size) return true
  for (const c of checked.value) if (!saved.has(c)) return true
  return false
})

// 전체 모듈 일괄 허용/해제
const setAllPerms = (on: boolean) => {
  if (!on) {
    checked.value = new Set()
    return
  }
  const next = new Set<string>()
  for (const g of permissions.value) for (const a of g.actions) next.add(a.code)
  checked.value = next
}

// 변경 되돌리기
const revertPerms = () => syncCheckedFromRole()

const loadRoles = async () => {
  rolesLoading.value = true
  try {
    roles.value = await rbacApi.roles()
    // 선택 유지 또는 첫 역할 자동 선택
    if (selectedRoleId.value == null && roles.value[0]) {
      selectRole(roles.value[0].id)
    } else if (selectedRoleId.value != null) {
      syncCheckedFromRole()
    }
  } catch {
    error('역할 목록을 불러오지 못했습니다')
  } finally {
    rolesLoading.value = false
  }
}

const loadPermissions = async () => {
  if (permissions.value.length) return
  permsLoading.value = true
  try {
    permissions.value = await rbacApi.permissions()
  } catch {
    error('권한 목록을 불러오지 못했습니다')
  } finally {
    permsLoading.value = false
  }
}

const syncCheckedFromRole = () => {
  checked.value = new Set(selectedRole.value?.permission_codes ?? [])
}

const selectRole = (id: number) => {
  selectedRoleId.value = id
  syncCheckedFromRole()
  if (!selectedRole.value?.is_admin) loadPermissions()
}

const onSavePermissions = async () => {
  if (!selectedRole.value) return
  savingPerms.value = true
  try {
    const updated = await rbacApi.setRolePermissions(
      selectedRole.value.id,
      Array.from(checked.value),
    )
    success('권한이 저장되었습니다')
    // 목록 갱신 후 선택 역할 권한 동기화
    const idx = roles.value.findIndex((r) => r.id === updated.id)
    if (idx > -1) roles.value[idx] = updated
    syncCheckedFromRole()
  } catch {
    error('권한 저장에 실패했습니다')
  } finally {
    savingPerms.value = false
  }
}

// ─────────── 역할 생성/수정 ───────────
interface RoleForm {
  code: string
  name: string
  description: string
  sort_order: number
}
const emptyRoleForm = (): RoleForm => ({ code: '', name: '', description: '', sort_order: 0 })
const roleFormOpen = ref(false)
const roleIsEdit = ref(false)
const editingRole = ref<Role | null>(null)
const roleForm = ref<RoleForm>(emptyRoleForm())
const roleSaving = ref(false)
// 복제 시 새 역할에 복사할 권한코드 (일반 생성이면 null)
const cloneSourceCodes = ref<string[] | null>(null)

const openCreateRole = () => {
  roleIsEdit.value = false
  editingRole.value = null
  cloneSourceCodes.value = null
  roleForm.value = emptyRoleForm()
  roleFormOpen.value = true
}

// 역할 복제: 권한까지 복사해 새 역할 생성(코드/이름만 바꿔 저장 → 매트릭스에서 수정)
const openCloneRole = (r: Role) => {
  roleIsEdit.value = false
  editingRole.value = null
  // 전체권한(is_admin) 역할 복제 시엔 모든 권한코드를 명시적으로 복사
  cloneSourceCodes.value = r.is_admin
    ? permissions.value.flatMap((g) => g.actions.map((a) => a.code))
    : [...(r.permission_codes ?? [])]
  roleForm.value = {
    code: `${r.code}_COPY`,
    name: `${r.name} 복사`,
    description: r.description || '',
    sort_order: (r.sort_order ?? 0) + 1,
  }
  roleFormOpen.value = true
}

const openEditRole = (r: Role) => {
  roleIsEdit.value = true
  editingRole.value = r
  roleForm.value = {
    code: r.code,
    name: r.name,
    description: r.description || '',
    sort_order: r.sort_order ?? 0,
  }
  roleFormOpen.value = true
}

const onSubmitRole = async () => {
  if (!roleIsEdit.value && !roleForm.value.code.trim()) {
    warning('코드를 입력하세요')
    return
  }
  if (!roleForm.value.name.trim()) {
    warning('이름을 입력하세요')
    return
  }
  roleSaving.value = true
  try {
    if (roleIsEdit.value && editingRole.value) {
      const payload: RoleUpdatePayload = {
        name: roleForm.value.name.trim(),
        description: roleForm.value.description.trim() || undefined,
        sort_order: roleForm.value.sort_order,
      }
      await rbacApi.updateRole(editingRole.value.id, payload)
      success('역할이 수정되었습니다')
    } else {
      const payload: RoleCreatePayload = {
        code: roleForm.value.code.trim(),
        name: roleForm.value.name.trim(),
        description: roleForm.value.description.trim() || undefined,
        sort_order: roleForm.value.sort_order,
      }
      const created = await rbacApi.createRole(payload)
      // 복제 모드면 원본 권한을 새 역할에 복사
      if (cloneSourceCodes.value && cloneSourceCodes.value.length) {
        try {
          await rbacApi.setRolePermissions(created.id, cloneSourceCodes.value)
        } catch {
          warning('역할은 생성됐으나 권한 복사에 실패했습니다. 매트릭스에서 다시 설정하세요.')
        }
      }
      success(cloneSourceCodes.value ? '역할이 복제되었습니다' : '역할이 생성되었습니다')
      cloneSourceCodes.value = null
      selectedRoleId.value = created.id
    }
    roleFormOpen.value = false
    await loadRoles()
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    if (!roleIsEdit.value && status === 400) {
      error('이미 존재하는 코드이거나 잘못된 요청입니다')
    } else {
      error(roleIsEdit.value ? '역할 수정에 실패했습니다' : '역할 생성에 실패했습니다')
    }
  } finally {
    roleSaving.value = false
  }
}

const onDeleteRole = async (r: Role) => {
  if (r.is_system) {
    warning('기본(시스템) 역할은 삭제할 수 없습니다')
    return
  }
  if (!confirm(`'${r.name}' (${r.code}) 역할을 삭제하시겠습니까?`)) return
  try {
    await rbacApi.deleteRole(r.id)
    success('역할이 삭제되었습니다')
    if (selectedRoleId.value === r.id) selectedRoleId.value = null
    await loadRoles()
  } catch {
    error('역할 삭제에 실패했습니다')
  }
}

// ─────────── 역할 순서 드래그 ───────────
const dragIndex = ref<number | null>(null)
const dropIndex = ref<number | null>(null)
const reordering = ref(false)

const onRoleDragStart = (idx: number, e: DragEvent) => {
  dragIndex.value = idx
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(idx)) // Firefox는 데이터가 있어야 드래그 시작
  }
}

const onRoleDragOver = (idx: number) => {
  if (dragIndex.value === null) return
  dropIndex.value = idx
}

const onRoleDragEnd = () => {
  dragIndex.value = null
  dropIndex.value = null
}

const onRoleDrop = async (idx: number) => {
  const from = dragIndex.value
  dragIndex.value = null
  dropIndex.value = null
  if (from === null || from === idx) return
  const arr = [...roles.value]
  const [moved] = arr.splice(from, 1)
  if (!moved) return
  arr.splice(idx, 0, moved)
  roles.value = arr // 낙관적 반영
  await persistRoleOrder()
}

// 새 순서를 10단위 sort_order로 재부여하고 변경분만 저장
const persistRoleOrder = async () => {
  reordering.value = true
  try {
    const updates = roles.value
      .map((r, i) => ({ r, want: i * 10 }))
      .filter(({ r, want }) => r.sort_order !== want)
    if (!updates.length) return
    await Promise.all(
      updates.map(({ r, want }) =>
        rbacApi.updateRole(r.id, { sort_order: want }).then((u) => {
          const j = roles.value.findIndex((x) => x.id === u.id)
          if (j > -1) roles.value[j] = u
        }),
      ),
    )
    success('역할 순서가 저장되었습니다')
  } catch {
    error('순서 저장에 실패했습니다')
    await loadRoles() // 실패 시 서버 기준으로 복구
  } finally {
    reordering.value = false
  }
}

// ─────────── 사용자 역할 배정 ───────────
const users = ref<ManagedUser[]>([])
const usersLoading = ref(false)
const userRolesMap = ref<Record<number, Role[]>>({})
const assignedLoaded = ref(false)

const loadUsersWithRoles = async () => {
  usersLoading.value = true
  try {
    if (!roles.value.length) await loadRoles()
    users.value = await userApi.list()
    const map: Record<number, Role[]> = {}
    await Promise.all(
      users.value.map(async (u) => {
        try {
          map[u.id] = await rbacApi.userRoles(u.id)
        } catch {
          map[u.id] = []
        }
      }),
    )
    userRolesMap.value = map
    assignedLoaded.value = true
  } catch {
    error('사용자 목록을 불러오지 못했습니다')
  } finally {
    usersLoading.value = false
  }
}

const assignOpen = ref(false)
const assignUser = ref<ManagedUser | null>(null)
const assignSelected = ref<Set<number>>(new Set())
const assignSaving = ref(false)

const openAssign = (u: ManagedUser) => {
  assignUser.value = u
  assignSelected.value = new Set((userRolesMap.value[u.id] || []).map((r) => r.id))
  assignOpen.value = true
}

const toggleAssign = (id: number) => {
  const next = new Set(assignSelected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  assignSelected.value = next
}

const onSubmitAssign = async () => {
  if (!assignUser.value) return
  assignSaving.value = true
  try {
    await rbacApi.setUserRoles(assignUser.value.id, Array.from(assignSelected.value))
    success('역할이 배정되었습니다')
    // 해당 사용자 역할 갱신
    userRolesMap.value[assignUser.value.id] = await rbacApi.userRoles(assignUser.value.id)
    assignOpen.value = false
  } catch {
    error('역할 배정에 실패했습니다')
  } finally {
    assignSaving.value = false
  }
}

// 사용자 탭 진입 시 지연 로드
watch(subTab, (t) => {
  if (t === 'assign' && !assignedLoaded.value) loadUsersWithRoles()
})

// 초기 로드
loadRoles()
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
