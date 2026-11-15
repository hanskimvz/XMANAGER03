<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { approvalApi, type ApproverCandidate } from '@/api/approval'
import {
  departmentApi,
  loadDepartments,
  ORG_TYPES,
  orgTypeBadge,
  orgTypeLabel,
  type Department,
  type OrgType,
} from '@/api/department'
import OrgChartNode, { type OrgTreeNode } from './OrgChartNode.vue'

const { success, error, warning } = useToast()

const rows = ref<Department[]>([])
const users = ref<ApproverCandidate[]>([]) // 책임자 후보(활성 사용자)
const loading = ref(false)
const selectedId = ref<number | null>(null)

async function load() {
  loading.value = true
  try {
    rows.value = await departmentApi.listAll()
    if (selectedId.value !== null && !rows.value.some((d) => d.id === selectedId.value)) selectedId.value = null
  } catch {
    error('조직 목록을 불러오지 못했습니다')
  } finally {
    loading.value = false
  }
}

// 저장/삭제 후: 목록 + 전역 부서 캐시(드롭다운/라벨) 갱신
async function reload() {
  await load()
  await loadDepartments(true)
}

// ── 트리 구성 ── (상위 조직이 없거나 찾을 수 없으면 최상위로 둔다. API 가 정렬순으로 내려준다)
const byId = computed(() => new Map(rows.value.map((d) => [d.id, d])))

const tree = computed<OrgTreeNode[]>(() => {
  const nodes = new Map<number, OrgTreeNode>(rows.value.map((d) => [d.id, { dept: d, children: [] }]))
  const roots: OrgTreeNode[] = []
  for (const d of rows.value) {
    const node = nodes.get(d.id)!
    const parent = d.parent_id != null ? nodes.get(d.parent_id) : undefined
    if (parent) parent.children.push(node)
    else roots.push(node)
  }
  return roots
})

// 목록용: 트리 순서대로 펼친 행(+들여쓰기 깊이)
const flat = computed(() => {
  const out: { dept: Department; depth: number }[] = []
  const walk = (nodes: OrgTreeNode[], depth: number) => {
    for (const n of nodes) {
      out.push({ dept: n.dept, depth })
      walk(n.children, depth + 1)
    }
  }
  walk(tree.value, 0)
  return out
})

const selected = computed(() => (selectedId.value !== null ? byId.value.get(selectedId.value) || null : null))

function parentName(d: Department) {
  return d.parent_id != null ? byId.value.get(d.parent_id)?.name || '-' : '-'
}

// 자신과 모든 하위 조직 id — 편집 시 상위 조직 후보에서 제외(순환 방지)
function subtreeIds(id: number): Set<number> {
  const ids = new Set<number>([id])
  let grew = true
  while (grew) {
    grew = false
    for (const d of rows.value) {
      if (d.parent_id != null && ids.has(d.parent_id) && !ids.has(d.id)) {
        ids.add(d.id)
        grew = true
      }
    }
  }
  return ids
}

// ── 추가/편집 ──
interface OrgForm {
  code: string
  name: string
  name_en: string
  org_type: OrgType
  parent_id: number | null
  manager_user_id: number | null
  description: string
  sort_order: number
  is_active: boolean
}

const formOpen = ref(false)
const editingId = ref<number | null>(null)
const isEdit = computed(() => editingId.value !== null)
const saving = ref(false)
const form = ref<OrgForm>(emptyForm())

function emptyForm(): OrgForm {
  return {
    code: '', name: '', name_en: '', org_type: 'TEAM', parent_id: null,
    manager_user_id: null, description: '', sort_order: 0, is_active: true,
  }
}

const parentOptions = computed(() => {
  const excluded = editingId.value !== null ? subtreeIds(editingId.value) : new Set<number>()
  return flat.value.filter((r) => !excluded.has(r.dept.id))
})

function openCreate(parentId: number | null = null) {
  editingId.value = null
  const maxOrder = rows.value.reduce((m, d) => Math.max(m, d.sort_order), 0)
  form.value = { ...emptyForm(), parent_id: parentId, sort_order: maxOrder + 1 }
  formOpen.value = true
}

function openEdit(d: Department) {
  editingId.value = d.id
  form.value = {
    code: d.code,
    name: d.name,
    name_en: d.name_en || '',
    org_type: d.org_type,
    parent_id: d.parent_id ?? null,
    manager_user_id: d.manager_user_id ?? null,
    description: d.description || '',
    sort_order: d.sort_order,
    is_active: d.is_active,
  }
  formOpen.value = true
}

function userLabel(u: ApproverCandidate) {
  const extra = [u.department, u.position].filter(Boolean).join(' ')
  return extra ? `${u.name} (${extra})` : u.name
}

async function onSubmit() {
  if (saving.value) return
  const f = form.value
  if (!f.name.trim()) return warning('조직명을 입력하세요')
  if (!isEdit.value && !f.code.trim()) return warning('코드를 입력하세요')
  saving.value = true
  try {
    const common = {
      name: f.name.trim(),
      name_en: f.name_en.trim() || null,
      org_type: f.org_type,
      parent_id: f.parent_id,
      manager_user_id: f.manager_user_id,
      description: f.description.trim() || null,
      sort_order: Number(f.sort_order) || 0,
    }
    if (editingId.value !== null) {
      await departmentApi.update(editingId.value, { ...common, is_active: f.is_active })
      success('조직이 수정되었습니다')
    } else {
      const created = await departmentApi.create({ ...common, code: f.code.trim() })
      selectedId.value = created.id
      success('조직이 추가되었습니다')
    }
    formOpen.value = false
    await reload()
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    error(typeof detail === 'string' ? detail : isEdit.value ? '조직 수정에 실패했습니다' : '조직 추가에 실패했습니다')
  } finally {
    saving.value = false
  }
}

async function onDelete(d: Department) {
  if (d.member_count > 0) {
    return warning(`소속 사용자가 ${d.member_count}명 있어 삭제할 수 없습니다. 비활성화하거나 사용자 부서를 먼저 변경하세요.`)
  }
  if (rows.value.some((x) => x.parent_id === d.id)) {
    return warning('하위 조직이 있어 삭제할 수 없습니다. 하위 조직을 먼저 옮기거나 삭제하세요.')
  }
  if (!confirm(`'${d.name}' (${d.code}) 조직을 삭제하시겠습니까?`)) return
  try {
    await departmentApi.remove(d.id)
    success('조직이 삭제되었습니다')
    await reload()
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    error(typeof detail === 'string' ? detail : '조직 삭제에 실패했습니다')
  }
}

onMounted(async () => {
  await load()
  try {
    users.value = (await approvalApi.getApprovers()).data || []
  } catch {
    error('책임자 후보 목록을 불러오지 못했습니다')
  }
})
</script>

<template>
  <div class="max-w-screen-xl mx-auto px-4 py-6">
    <div class="flex items-start justify-between gap-3 mb-4">
      <div>
        <h1 class="text-xl font-bold text-gray-800">조직관리</h1>
        <p class="text-xs text-gray-500 mt-0.5">회사 조직도와 부서/팀 구조를 관리합니다.</p>
      </div>
      <button class="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700" @click="openCreate()">
        <span class="text-base leading-none">+</span> 조직 추가
      </button>
    </div>

    <!-- 조직도 -->
    <div class="bg-white rounded-lg shadow border p-4 mb-4">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-sm font-semibold text-gray-800">조직도</h2>
        <span class="text-xs text-gray-500">총 {{ rows.length }}개 조직</span>
      </div>
      <div v-if="loading && !rows.length" class="py-10 text-center text-gray-400 text-sm">로딩 중...</div>
      <div v-else-if="!rows.length" class="py-10 text-center text-gray-400 text-sm">등록된 조직이 없습니다.</div>
      <div v-else class="overflow-x-auto pb-2">
        <div class="org-tree w-max min-w-full">
          <ul>
            <OrgChartNode
              v-for="node in tree"
              :key="node.dept.id"
              :node="node"
              :selected-id="selectedId"
              @select="(id) => (selectedId = id)"
            />
          </ul>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
      <!-- 조직 목록 -->
      <div class="lg:col-span-2 bg-white rounded-lg shadow border p-4 overflow-x-auto">
        <h2 class="text-sm font-semibold text-gray-800 mb-3">조직 목록</h2>
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-gray-500 text-xs">
            <tr>
              <th class="px-3 py-2 text-left">조직명</th>
              <th class="px-3 py-2 text-left w-20">유형</th>
              <th class="px-3 py-2 text-left w-24">책임자</th>
              <th class="px-3 py-2 text-left w-14">인원</th>
              <th class="px-3 py-2 text-left w-44">관리</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in flat"
              :key="r.dept.id"
              class="border-t cursor-pointer"
              :class="r.dept.id === selectedId ? 'bg-blue-50' : 'hover:bg-gray-50'"
              @click="selectedId = r.dept.id"
            >
              <td class="px-3 py-2.5 text-gray-800 whitespace-nowrap" :style="{ paddingLeft: `${12 + r.depth * 18}px` }">
                {{ r.dept.name }}
                <span v-if="!r.dept.is_active" class="ml-1 px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 text-[10px]">비활성</span>
              </td>
              <td class="px-3 py-2.5">
                <span class="type-badge" :class="orgTypeBadge(r.dept.org_type)">{{ orgTypeLabel(r.dept.org_type) }}</span>
              </td>
              <td class="px-3 py-2.5 text-gray-600 whitespace-nowrap">{{ r.dept.manager_name || '-' }}</td>
              <td class="px-3 py-2.5 text-gray-600">{{ r.dept.member_count }}</td>
              <td class="px-3 py-2.5 text-xs whitespace-nowrap" @click.stop>
                <button class="text-blue-600 hover:underline mr-3" @click="openCreate(r.dept.id)">하위 추가</button>
                <button class="text-blue-600 hover:underline mr-3" @click="openEdit(r.dept)">편집</button>
                <button class="text-red-600 hover:underline" @click="onDelete(r.dept)">삭제</button>
              </td>
            </tr>
            <tr v-if="!flat.length">
              <td colspan="5" class="px-3 py-10 text-center text-gray-400">{{ loading ? '로딩 중...' : '등록된 조직이 없습니다.' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 조직 상세 -->
      <div class="bg-white rounded-lg shadow border p-4">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-sm font-semibold text-gray-800">조직 상세</h2>
          <button v-if="selected" class="text-xs text-blue-600 hover:underline" @click="openEdit(selected)">편집</button>
        </div>
        <p v-if="!selected" class="py-8 text-center text-gray-400 text-sm">조직도나 목록에서 조직을 선택하세요.</p>
        <dl v-else class="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
          <div>
            <dt class="detail-label">조직명</dt>
            <dd class="text-gray-800">{{ selected.name }}</dd>
          </div>
          <div>
            <dt class="detail-label">영문명</dt>
            <dd class="text-gray-800">{{ selected.name_en || '-' }}</dd>
          </div>
          <div>
            <dt class="detail-label">유형</dt>
            <dd class="text-gray-800">{{ orgTypeLabel(selected.org_type) }}</dd>
          </div>
          <div>
            <dt class="detail-label">상위 조직</dt>
            <dd class="text-gray-800">{{ parentName(selected) }}</dd>
          </div>
          <div>
            <dt class="detail-label">책임자</dt>
            <dd class="text-gray-800">{{ selected.manager_name || '-' }}</dd>
          </div>
          <div>
            <dt class="detail-label">인원</dt>
            <dd class="text-gray-800">{{ selected.member_count }}명</dd>
          </div>
          <div>
            <dt class="detail-label">코드</dt>
            <dd class="font-mono text-gray-800">{{ selected.code }}</dd>
          </div>
          <div>
            <dt class="detail-label">상태</dt>
            <dd class="text-gray-800">{{ selected.is_active ? '활성' : '비활성' }}</dd>
          </div>
          <div class="col-span-2">
            <dt class="detail-label">설명</dt>
            <dd class="text-gray-800 whitespace-pre-wrap break-words">{{ selected.description || '-' }}</dd>
          </div>
        </dl>
      </div>
    </div>

    <!-- 추가/편집 모달 -->
    <div v-if="formOpen" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-xl flex flex-col max-h-[92vh]">
        <div class="flex items-center justify-between px-5 py-3 border-b">
          <h3 class="text-base font-semibold text-gray-800">{{ isEdit ? '조직 편집' : '조직 추가' }}</h3>
          <button class="text-gray-400 hover:text-gray-600" aria-label="닫기" @click="formOpen = false">✕</button>
        </div>

        <div class="px-5 py-4 space-y-4 overflow-y-auto">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="lbl">조직명 <span class="text-red-500">*</span></label>
              <input v-model="form.name" class="inp w-full" placeholder="예: 기술연구소" maxlength="50" />
            </div>
            <div>
              <label class="lbl">영문명</label>
              <input v-model="form.name_en" class="inp w-full" placeholder="예: R&D Center" maxlength="100" />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="lbl">유형 <span class="text-red-500">*</span></label>
              <select v-model="form.org_type" class="inp w-full">
                <option v-for="t in ORG_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
            </div>
            <div>
              <label class="lbl">상위 조직</label>
              <select v-model="form.parent_id" class="inp w-full">
                <option :value="null">없음 (최상위)</option>
                <option v-for="p in parentOptions" :key="p.dept.id" :value="p.dept.id">
                  {{ '  '.repeat(p.depth) + p.dept.name }}
                </option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="lbl">책임자</label>
              <select v-model="form.manager_user_id" class="inp w-full">
                <option :value="null">미지정</option>
                <option v-for="u in users" :key="u.id" :value="u.id">{{ userLabel(u) }}</option>
              </select>
            </div>
            <div>
              <label class="lbl">정렬 순서</label>
              <input v-model.number="form.sort_order" type="number" class="inp w-full" />
            </div>
          </div>

          <div>
            <label class="lbl">코드 <span class="text-red-500">*</span></label>
            <input v-model="form.code" class="inp w-full disabled:bg-gray-100 disabled:text-gray-500" :disabled="isEdit" placeholder="예: RND" maxlength="30" />
            <p class="text-[11px] text-gray-400 mt-1">
              사용자 소속 부서에 저장되는 값입니다.{{ isEdit ? ' 코드는 수정할 수 없습니다.' : ' 등록 후에는 바꿀 수 없습니다.' }}
            </p>
          </div>

          <div>
            <label class="lbl">설명</label>
            <textarea v-model="form.description" rows="3" class="inp w-full" placeholder="조직의 역할·업무를 입력하세요" maxlength="2000"></textarea>
          </div>

          <label v-if="isEdit" class="inline-flex items-center gap-2 text-sm text-gray-700">
            <input v-model="form.is_active" type="checkbox" /> 활성
            <span class="text-xs text-gray-400">(끄면 사용자 부서 선택 목록에서 빠집니다)</span>
          </label>
        </div>

        <div class="px-5 py-3 border-t flex justify-end gap-2">
          <button type="button" class="px-3 py-2 text-sm text-gray-600 border rounded-md hover:bg-gray-50" @click="formOpen = false">취소</button>
          <button :disabled="saving" class="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50" @click="onSubmit">
            {{ saving ? '저장 중...' : '저장' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.inp { @apply px-2.5 py-1.5 border border-gray-300 rounded-md text-sm bg-white focus:outline-none focus:ring-1 focus:ring-blue-500; }
.lbl { @apply block text-xs text-gray-500 mb-1; }
.type-badge { @apply inline-block px-2 py-0.5 rounded-full text-[11px] font-bold whitespace-nowrap; }
.detail-label { @apply text-xs text-gray-500 mb-0.5; }
</style>
