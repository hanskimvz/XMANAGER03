<template>
  <Teleport to="body">
    <Transition name="modal">
      <div class="fixed inset-0 z-50 flex items-start justify-center bg-black/50 overflow-y-auto py-8" >
        <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
          <div class="flex items-center justify-between px-6 py-4 border-b">
            <h3 class="text-lg font-bold">{{ isEdit ? '영업활동 수정' : '영업활동 등록' }}</h3>
            <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="px-6 py-4 space-y-4">
            <!-- 거래처 선택 -->
            <div class="grid grid-cols-2 gap-4">
              <div class="relative">
                <label class="block text-sm font-medium text-gray-700 mb-1">거래처</label>
                <input v-model="customerSearch"
                  @focus="showDropdown = true; highlightedIndex = 0"
                  @input="showDropdown = true; highlightedIndex = 0"
                  @blur="hideDropdownDelayed"
                  @keydown.down.prevent="moveHighlight(1)"
                  @keydown.up.prevent="moveHighlight(-1)"
                  @keydown.enter.prevent="handleEnter"
                  @keydown.escape="showDropdown = false"
                  class="w-full border rounded-md px-3 py-2 text-sm" placeholder="거래처 검색 또는 직접 입력" />
                <div v-if="showDropdown && filteredCustomers.length > 0"
                  class="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-40 overflow-y-auto">
                  <div v-for="(c, idx) in filteredCustomers" :key="c.id"
                    :ref="el => setItemRef(el, idx)"
                    @mousedown.prevent="selectCustomer(c)"
                    @mouseenter="highlightedIndex = idx"
                    :class="highlightedIndex === idx ? 'bg-blue-100' : 'hover:bg-blue-50'"
                    class="px-3 py-2 text-sm cursor-pointer">
                    {{ c.partner_name }} <span v-if="c.country_name" class="text-xs text-gray-400">{{ c.country_name }}</span>
                  </div>
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">나라</label>
                <input v-model="form.country" class="w-full border rounded-md px-3 py-2 text-sm" placeholder="체코, 한국 등" />
              </div>
            </div>

            <!-- 프로젝트명 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">프로젝트명 <span class="text-red-500">*</span></label>
              <input v-model="form.title" class="w-full border rounded-md px-3 py-2 text-sm" placeholder="HXB13 4CH 방산 납품" />
            </div>

            <!-- 담당자 + 상태 -->
            <div class="grid grid-cols-2 gap-4">
              <div class="relative" ref="assigneeBoxRef">
                <label class="block text-sm font-medium text-gray-700 mb-1">담당자</label>
                <div @click="showAssigneeMenu = !showAssigneeMenu"
                  class="w-full border rounded-md px-2 py-1.5 text-sm min-h-[38px] flex flex-wrap items-center gap-1 cursor-pointer">
                  <span v-for="name in assigneeNames" :key="name"
                    class="inline-flex items-center gap-1 bg-blue-100 text-blue-700 rounded px-1.5 py-0.5 text-xs">
                    {{ name }}
                    <button type="button" @click.stop="removeAssignee(name)" class="hover:text-blue-900">×</button>
                  </span>
                  <span v-if="assigneeNames.length === 0" class="text-gray-400 px-1">담당자 선택</span>
                </div>
                <div v-if="showAssigneeMenu"
                  class="absolute z-20 mt-1 w-full bg-white border rounded-md shadow-lg max-h-56 overflow-y-auto">
                  <label v-for="a in knownAssignees" :key="a"
                    class="flex items-center gap-2 px-3 py-1.5 text-sm cursor-pointer hover:bg-blue-50">
                    <input type="checkbox" :checked="assigneeNames.includes(a)"
                      @change="toggleAssignee(a)" class="w-4 h-4 rounded accent-blue-600" />
                    <span>{{ a }}</span>
                  </label>
                  <div v-if="knownAssignees.length === 0" class="px-3 py-2 text-xs text-gray-400">
                    등록된 담당자가 없습니다
                  </div>
                  <div class="flex gap-1 border-t px-2 py-2 bg-gray-50">
                    <input v-model="customAssignee" @keydown.enter.prevent="addCustomAssignee"
                      placeholder="직접 입력 후 Enter"
                      class="flex-1 border rounded px-2 py-1 text-xs" />
                    <button type="button" @click="addCustomAssignee"
                      class="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700">추가</button>
                  </div>
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">상태</label>
                <select v-model="form.status" class="w-full border rounded-md px-3 py-2 text-sm">
                  <option value="IN_PROGRESS">진행중</option>
                  <option value="WAITING">대기</option>
                  <option value="COMPLETED">완료</option>
                  <option value="ON_HOLD">보류</option>
                  <option value="DROPPED">무산</option>
                </select>
              </div>
            </div>

            <!-- 문의 유형 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">문의 유형</label>
              <select v-model="form.inquiry_type" class="w-full border rounded-md px-3 py-2 text-sm">
                <option value="GENERAL">일반 문의</option>
                <option value="TECHNICAL">기술 문의</option>
                <option value="QUOTATION">견적 문의</option>
                <option value="SAMPLE">샘플 요청</option>
                <option value="CLAIM">클레임</option>
                <option value="OTHER">기타</option>
              </select>
              <p class="text-xs text-gray-400 mt-1">기술 문의는 기술팀에서 확인할 수 있도록 별도 분류됩니다.</p>
            </div>

            <!-- 우선순위 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">우선순위</label>
              <div class="flex items-center gap-4">
                <label class="inline-flex items-center gap-1.5 text-sm cursor-pointer">
                  <input type="checkbox" v-model="form.is_urgent" class="w-4 h-4 rounded" />
                  <span :class="form.is_urgent ? 'text-rose-600 font-medium' : 'text-gray-600'">🔴 긴급</span>
                </label>
                <label class="inline-flex items-center gap-1.5 text-sm cursor-pointer">
                  <input type="checkbox" v-model="form.is_important" class="w-4 h-4 rounded" />
                  <span :class="form.is_important ? 'text-amber-600 font-medium' : 'text-gray-600'">🟠 중요</span>
                </label>
              </div>
            </div>

            <!-- 지연 사유 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">지연 사유</label>
              <textarea v-model="form.pending_reason" rows="2" class="w-full border rounded-md px-3 py-2 text-sm" placeholder="고객사 내부 예산 승인 대기 중" />
            </div>

            <!-- 예상 금액 -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">예상 금액</label>
                <input v-model.number="form.expected_amount" type="number" min="0" class="w-full border rounded-md px-3 py-2 text-sm" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">통화</label>
                <select v-model="form.expected_currency" class="w-full border rounded-md px-3 py-2 text-sm">
                  <option value="KRW">KRW (₩)</option>
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="CNY">CNY (¥)</option>
                  <option value="JPY">JPY (¥)</option>
                  <option value="GBP">GBP (£)</option>
                </select>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2 px-6 py-4 border-t bg-gray-50">
            <button @click="$emit('close')" class="px-4 py-2 text-sm text-gray-600">취소</button>
            <button @click="save" :disabled="saving" class="px-6 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
              {{ saving ? '저장 중...' : '저장' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { salesActivityApi, type SalesActivity, type SalesActivityCreate } from '@/api/salesActivity'
import { useToast } from '@/composables/useToast'
import apiClient from '@/api/client'

interface Props { activity?: SalesActivity | null }
const props = withDefaults(defineProps<Props>(), { activity: null })
const emit = defineEmits<{ (e: 'close'): void; (e: 'saved'): void }>()
const { showToast } = useToast()

const isEdit = computed(() => !!props.activity?.id)
const saving = ref(false)
const customers = ref<any[]>([])
const customerSearch = ref('')
const showDropdown = ref(false)
const highlightedIndex = ref(0)
const itemRefs = ref<(HTMLElement | null)[]>([])

function setItemRef(el: any, idx: number) {
  itemRefs.value[idx] = el as HTMLElement | null
}

function hideDropdownDelayed() { setTimeout(() => { showDropdown.value = false }, 200) }

function moveHighlight(delta: number) {
  if (!showDropdown.value) showDropdown.value = true
  const list = filteredCustomers.value
  if (list.length === 0) return
  const next = (highlightedIndex.value + delta + list.length) % list.length
  highlightedIndex.value = next
  nextTick(() => {
    itemRefs.value[next]?.scrollIntoView({ block: 'nearest' })
  })
}

function handleEnter() {
  const list = filteredCustomers.value
  // 1건만 남았거나, 드롭다운이 열려 있고 선택된 항목이 있으면 해당 항목 선택
  if (list.length === 1) {
    selectCustomer(list[0])
    return
  }
  if (showDropdown.value && list.length > 0) {
    const target = list[highlightedIndex.value]
    if (target) selectCustomer(target)
  }
}

const loggedInUserName = JSON.parse(localStorage.getItem('user') || '{}')?.name || ''

// 담당자 다중 선택
const assigneeNames = ref<string[]>(loggedInUserName ? [loggedInUserName] : [])
const knownAssignees = ref<string[]>([])
const showAssigneeMenu = ref(false)
const customAssignee = ref('')
const assigneeBoxRef = ref<HTMLElement | null>(null)

function toggleAssignee(name: string) {
  const i = assigneeNames.value.indexOf(name)
  if (i >= 0) assigneeNames.value.splice(i, 1)
  else assigneeNames.value.push(name)
}
function removeAssignee(name: string) {
  const i = assigneeNames.value.indexOf(name)
  if (i >= 0) assigneeNames.value.splice(i, 1)
}
function addCustomAssignee() {
  const v = customAssignee.value.trim()
  if (!v) return
  if (!assigneeNames.value.includes(v)) assigneeNames.value.push(v)
  if (!knownAssignees.value.includes(v)) knownAssignees.value.push(v)
  customAssignee.value = ''
}
function handleAssigneeClickOutside(e: MouseEvent) {
  if (assigneeBoxRef.value && !assigneeBoxRef.value.contains(e.target as Node)) {
    showAssigneeMenu.value = false
  }
}

const form = ref<SalesActivityCreate>({
  customer_id: undefined,
  customer_name: '',
  country: '',
  title: '',
  assigned_to: loggedInUserName,
  status: 'IN_PROGRESS',
  inquiry_type: 'QUOTATION',
  is_urgent: false,
  is_important: false,
  pending_reason: '',
  expected_amount: undefined,
  expected_currency: 'KRW',
})

if (props.activity) {
  form.value = {
    customer_id: props.activity.customer_id,
    customer_name: props.activity.customer_name || '',
    country: props.activity.country || '',
    title: props.activity.title,
    assigned_to: props.activity.assigned_to || '',
    status: props.activity.status,
    inquiry_type: props.activity.inquiry_type || 'GENERAL',
    is_urgent: !!props.activity.is_urgent,
    is_important: !!props.activity.is_important,
    pending_reason: props.activity.pending_reason || '',
    expected_amount: props.activity.expected_amount,
    expected_currency: props.activity.expected_currency || 'KRW',
  }
  customerSearch.value = props.activity.customer_name || props.activity.customer?.partner_name || ''
  assigneeNames.value = (props.activity.assigned_to || '')
    .split(',').map((s) => s.trim()).filter(Boolean)
}

const filteredCustomers = computed(() => {
  if (!customerSearch.value) return customers.value
  const q = customerSearch.value.toLowerCase()
  return customers.value.filter((c: any) => c.partner_name.toLowerCase().includes(q) || c.partner_name_en?.toLowerCase().includes(q))
})

function selectCustomer(c: any) {
  form.value.customer_id = c.id
  form.value.customer_name = c.partner_name
  form.value.country = c.country_name || ''
  customerSearch.value = c.partner_name
  showDropdown.value = false
}

async function save() {
  if (!form.value.title) { showToast('프로젝트명을 입력하세요', 'error'); return }
  // 거래처 직접 입력 (드롭다운 선택 안 한 경우)
  if (!form.value.customer_id && customerSearch.value) {
    form.value.customer_name = customerSearch.value
  }

  // 빈 숫자 필드 정리 (Pydantic 빈 문자열 거부 방지)
  const payload: any = { ...form.value }
  for (const f of ['expected_amount']) {
    const v = payload[f]
    if (v === '' || v === undefined || (typeof v === 'number' && Number.isNaN(v))) payload[f] = null
  }
  // 담당자: 다중 선택 → 콤마 구분 문자열로 저장
  payload.assigned_to = assigneeNames.value.join(', ')

  saving.value = true
  try {
    if (isEdit.value) {
      await salesActivityApi.update(props.activity!.id, payload)
      showToast('수정되었습니다', 'success')
    } else {
      await salesActivityApi.create(payload)
      showToast('등록되었습니다', 'success')
    }
    emit('saved')
  } catch (err: any) {
    showToast(err.response?.data?.detail || '저장에 실패했습니다', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const res = await apiClient.get('/partners', { params: { is_customer: true, limit: 500 } })
    customers.value = (res.data.items || res.data).map((c: any) => ({
      id: c.id, partner_name: c.partner_name, partner_name_en: c.partner_name_en, country_name: c.country_name,
    }))
  } catch { /* ignore */ }

  // 등록된 담당자 목록 로드 (현재 선택값도 후보에 포함)
  try {
    const res = await salesActivityApi.getAssignees()
    const merged = new Set<string>([...(res.data || []), ...assigneeNames.value])
    knownAssignees.value = Array.from(merged).sort()
  } catch {
    knownAssignees.value = [...assigneeNames.value]
  }

  document.addEventListener('click', handleAssigneeClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleAssigneeClickOutside)
})
</script>
