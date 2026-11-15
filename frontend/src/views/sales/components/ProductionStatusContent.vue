<template>
  <div class="p-4 sm:p-6">
    <!-- 단계별 요약 (클릭 시 해당 상태 필터) -->
    <div class="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-4">
      <button
        v-for="t in summaryTiles" :key="t.status"
        @click="toggleStatusFilter(t.status)"
        class="rounded-lg border px-3 py-2 text-left transition-colors"
        :class="statusFilter === t.status ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-200' : 'border-gray-200 hover:bg-gray-50'"
      >
        <div class="flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full" :class="t.dot"></span>
          <span class="text-[11px] text-gray-500 truncate">{{ t.label }}</span>
        </div>
        <div class="text-xl font-bold text-gray-800 mt-0.5 tabular-nums">{{ counts[t.status] ?? 0 }}</div>
      </button>
    </div>

    <!-- 필터 -->
    <div class="flex flex-wrap items-end gap-2 mb-4">
      <div>
        <label class="block text-xs font-medium text-gray-500 mb-1">검색</label>
        <input v-model="keyword" type="text" placeholder="요청번호·PI·PO"
          class="w-48 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          @keyup.enter="applySearch" @input="debouncedSearch" />
      </div>
      <div class="relative" ref="customerBoxRef">
        <label class="block text-xs font-medium text-gray-500 mb-1">고객사</label>
        <div class="relative">
          <input v-model="customerSearchText" type="text" placeholder="검색/선택"
            class="w-44 px-3 py-2 pr-8 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            @focus="showCustomerDropdown = true" @input="showCustomerDropdown = true" />
          <button type="button" class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400" @click="showCustomerDropdown = !showCustomerDropdown">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
          </button>
          <div v-if="showCustomerDropdown" class="absolute z-50 w-56 mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-56 overflow-y-auto">
            <div class="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm" @click="selectCustomer(null, '')">전체</div>
            <div v-for="c in filteredCustomers" :key="c.id" class="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm truncate" @click="selectCustomer(c.id, c.name)">{{ c.name }}</div>
            <div v-if="filteredCustomers.length === 0" class="px-3 py-2 text-sm text-gray-400">결과 없음</div>
          </div>
        </div>
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-500 mb-1">요청일</label>
        <div class="flex items-center gap-1">
          <input v-model="fromDate" type="date" @change="applySearch" class="px-2 py-2 border border-gray-300 rounded-lg text-sm" />
          <span class="text-gray-400 text-xs">~</span>
          <input v-model="toDate" type="date" @change="applySearch" class="px-2 py-2 border border-gray-300 rounded-lg text-sm" />
        </div>
      </div>
      <button class="px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50" @click="resetFilters">초기화</button>
      <button class="px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50" @click="reload">새로고침</button>
      <!-- 리스트/캘린더 뷰 전환 -->
      <div class="ml-auto inline-flex rounded-lg border overflow-hidden">
        <button @click="viewMode='list'" class="px-3 py-2 text-sm"
          :class="viewMode==='list' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'">리스트</button>
        <button @click="viewMode='calendar'" class="px-3 py-2 text-sm border-l"
          :class="viewMode==='calendar' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'">📅 캘린더</button>
      </div>
    </div>

    <!-- 캘린더 뷰 (납기일/요청일) -->
    <div v-if="viewMode==='calendar'" class="bg-white rounded-lg border p-3">
      <ProductionRequestCalendar :customer-id="customerId ?? undefined" @open-detail="openDetail" />
    </div>

    <!-- 진행바 리스트 -->
    <div v-else class="bg-white rounded-lg border overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400">로딩 중...</div>
      <div v-else-if="items.length === 0" class="p-8 text-center text-gray-400">생산요청이 없습니다.</div>
      <ul v-else class="divide-y divide-gray-100">
        <li v-for="pr in items" :key="pr.id"
          class="px-4 py-2.5 hover:bg-gray-50 cursor-pointer" @click="openDetail(pr.id)">
          <div class="flex items-start gap-4">
            <!-- 좌: 요청 식별 -->
            <div class="w-56 shrink-0">
              <div class="flex items-center gap-1.5 flex-wrap">
                <span class="text-sm font-semibold text-blue-600">{{ pr.request_number }}</span>
                <span v-if="pr.is_draft"
                  class="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-gray-200 text-gray-600">초안 · 미전송</span>
                <span v-else-if="!isBranch(pr.status)"
                  class="px-1.5 py-0.5 text-[10px] font-medium rounded-full"
                  :class="isConfirmed(pr.status) ? 'bg-blue-100 text-blue-700' : 'bg-yellow-100 text-yellow-700'">
                  {{ isConfirmed(pr.status) ? '✓ 확인' : '미확인' }}
                </span>
              </div>
              <div class="text-sm text-gray-800 truncate">{{ pr.customer?.partner_name || '-' }}</div>
              <div class="text-[11px] text-gray-400 truncate">
                <span v-if="pr.pi_number">PI {{ pr.pi_number }}</span>
                <span v-if="pr.prepared_by_name"> · 영업 {{ pr.prepared_by_name }}</span>
              </div>
              <div class="text-[11px] text-gray-400 whitespace-nowrap">
                요청 {{ fmtDate(pr.requested_at) }} · 납기
                <span :class="isOverdue(pr.due_date) && !isDone(pr.status) ? 'text-red-600 font-medium' : ''">{{ fmtDate(pr.due_date) }}</span>
              </div>
            </div>

            <!-- 중: 품목별 수량 + 특이사항 (핵심 정보) -->
            <div class="flex-1 min-w-0 space-y-0.5">
              <div v-for="(it, i) in (pr.items || [])" :key="i" class="flex items-baseline gap-2 text-xs leading-snug">
                <span class="font-mono text-gray-700 truncate shrink-0 max-w-[48%]">{{ itemLabel(it) }}</span>
                <span class="text-gray-900 font-semibold whitespace-nowrap">{{ qi(it.requested_quantity) }} {{ it.uom || 'EA' }}</span>
                <span v-if="it.customer_requirements" class="text-amber-700 truncate" :title="it.customer_requirements">· {{ it.customer_requirements }}</span>
              </div>
              <div v-if="!(pr.items?.length)" class="text-xs text-gray-400">품목 정보 없음</div>
            </div>

            <!-- 우: 진행 상태 클러스터 -->
            <div class="shrink-0 flex flex-col items-end gap-1">
              <div class="flex items-center gap-1.5">
                <div v-if="!isBranch(pr.status)" class="flex gap-[2px]">
                  <div v-for="(st, i) in STAGES" :key="st.key" class="h-1.5 w-3 rounded-full"
                    :class="i <= stageIdx(pr.status) ? stageFill(pr.status) : 'bg-gray-200'"></div>
                </div>
                <span class="px-2 py-0.5 text-[11px] font-medium rounded-full whitespace-nowrap" :class="prStatusStyles[pr.status]">
                  <template v-if="isBranch(pr.status)">{{ branchIcon(pr.status) }} </template>{{ compactStageLabel(pr.status) }}
                </span>
              </div>
              <div class="flex items-center gap-1.5">
                <span v-if="attachCount(pr) > 0" class="px-1.5 py-0.5 text-[10px] rounded-full bg-sky-100 text-sky-700 whitespace-nowrap">📷 도면 {{ attachCount(pr) }}</span>
                <span class="px-1.5 py-0.5 text-[10px] rounded-full whitespace-nowrap"
                  :class="pr.insert_not_applicable ? 'bg-gray-100 text-gray-400' : (pr.insert_shipped ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-400')">
                  <template v-if="pr.insert_not_applicable">— 인서트 없음</template>
                  <template v-else>{{ pr.insert_shipped ? '✓' : '○' }} 인서트<template v-if="pr.insert_shipped && pr.insert_shipped_at"> {{ fmtMd(pr.insert_shipped_at) }}</template></template>
                </span>
                <span v-if="pr.needs_review" class="px-1.5 py-0.5 text-[10px] rounded-full bg-amber-100 text-amber-700 cursor-help"
                  :title="pr.review_note || '검토 필요'">⚠ 검토<template v-if="pr.review_note">: {{ pr.review_note }}</template></span>
                <span v-if="packBoxes(pr) > 0" class="px-1.5 py-0.5 text-[10px] rounded-full bg-indigo-100 text-indigo-700 whitespace-nowrap">📦 {{ packBoxes(pr) }}box</span>
              </div>

              <!-- 초안(미전송): 특이사항 입력 후 '생산팀에 요청'해야 생산팀에 노출·알림 -->
              <div v-if="pr.is_draft" class="flex items-center gap-1 mt-0.5" @click.stop>
                <button @click="openEdit(pr.id)"
                  class="px-2 py-0.5 text-[10px] rounded bg-blue-600 text-white hover:bg-blue-700 whitespace-nowrap">✏ 특이사항</button>
                <button @click="handleSubmitDraft(pr)" :disabled="submittingId === pr.id"
                  title="특이사항 입력을 마쳤으면 생산팀에 요청합니다(이때 생산팀에 알림)"
                  class="px-2 py-0.5 text-[10px] rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 whitespace-nowrap">
                  {{ submittingId === pr.id ? '전송 중…' : '📤 생산팀에 요청' }}</button>
                <button @click="handleWithdrawDraft(pr)" :disabled="withdrawingId === pr.id"
                  title="아직 생산팀에 전송하지 않은 임시 건을 회수(삭제)합니다"
                  class="px-2 py-0.5 text-[10px] rounded border border-gray-300 text-gray-500 hover:bg-gray-50 disabled:opacity-50 whitespace-nowrap">
                  {{ withdrawingId === pr.id ? '회수 중…' : '🗑 회수' }}</button>
                <button @click="openBoxPlan(pr)" :class="boxPlanBtnClass(pr)"
                  :title="pr.has_box_plan ? '분할선적 박스계획 보기/수정' : '분할선적 박스계획 작성(생산팀에 포장 지시)'"
                  class="px-2 py-0.5 text-[10px] rounded border whitespace-nowrap">📦 박스계획</button>
              </div>
              <!-- 출고 이후 영업 처리: CI 생성(→CI 발송 시 발송완료 자동) · 수동 발송(예외) -->
              <div v-else-if="pr.status === 'SHIPPED'" class="flex items-center gap-1 mt-0.5" @click.stop>
                <label class="inline-flex items-center gap-0.5 text-[10px] text-gray-500 cursor-pointer mr-0.5"
                  title="여러 출고건을 체크해 하나의 CI로 합배송 발행(같은 고객)">
                  <input type="checkbox" :value="pr.id" v-model="mergeSel" class="w-3.5 h-3.5 rounded border-gray-300" />
                  합배송
                </label>
                <button @click="handleCreateCi(pr)" :disabled="ciBusy === pr.id"
                  title="연결된 PI로 CI 초안을 만듭니다. CI를 '발송' 처리하면 이 건이 자동으로 발송 완료됩니다."
                  class="px-2 py-0.5 text-[10px] rounded bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-50 whitespace-nowrap">
                  {{ ciBusy === pr.id ? '생성 중…' : '📄 CI 생성' }}
                </button>
                <button @click="openSplit(pr)"
                  title="이번 배송에 실을 수량만 나눠 CI 발행(분할선적). 잔여는 다음 CI로."
                  class="px-2 py-0.5 text-[10px] rounded border border-teal-300 text-teal-700 hover:bg-teal-50 whitespace-nowrap">✂ 분할 발행</button>
                <button v-if="pr.has_box_plan" @click="openBoxCi(pr)"
                  title="박스 분할계획대로 박스 1개당 CI 1건 발행(잔여박스 추적)"
                  class="px-2 py-0.5 text-[10px] rounded border border-indigo-300 text-indigo-700 bg-indigo-50 hover:bg-indigo-100 whitespace-nowrap">📦 박스별 CI</button>
                <button @click="handleDeliver(pr)"
                  title="CI 없이 발송하는 예외 케이스용 수동 처리"
                  class="px-2 py-0.5 text-[10px] rounded border border-purple-300 text-purple-600 hover:bg-purple-50 whitespace-nowrap">🚚 발송(수동)</button>
                <button @click="openBoxPlan(pr)" :class="boxPlanBtnClass(pr)"
                  :title="pr.has_box_plan ? '분할선적 박스계획 보기/수정' : '분할선적 박스계획 작성'"
                  class="px-2 py-0.5 text-[10px] rounded border whitespace-nowrap">📦 박스계획</button>
              </div>
              <div v-else-if="pr.status === 'DELIVERED'" class="text-[10px] text-purple-600 mt-0.5 whitespace-nowrap">✓ 발송 {{ fmtMd(pr.delivered_at) }}</div>

              <!-- 출고 완료 이전: 영업이 수정 가능(진행중·완료 포함). 요청/반려 건은 회수·재요청도 -->
              <div v-else-if="canSalesEdit(pr.status)" class="flex items-center gap-1 mt-0.5" @click.stop>
                <button @click="openEdit(pr.id)"
                  class="px-2 py-0.5 text-[10px] rounded bg-blue-600 text-white hover:bg-blue-700 whitespace-nowrap">✏ 수정</button>
                <button v-if="pr.status === 'REQUESTED'" @click="handleWithdraw(pr)"
                  title="확인 전 요청을 회수(삭제)합니다"
                  class="px-2 py-0.5 text-[10px] rounded border border-gray-300 text-gray-500 hover:bg-gray-50 whitespace-nowrap">↩ 회수</button>
                <button v-if="pr.status === 'REJECTED'" @click="handleResubmit(pr)"
                  title="수정 후 다시 생산팀에 요청합니다"
                  class="px-2 py-0.5 text-[10px] rounded border border-orange-300 text-orange-600 hover:bg-orange-50 whitespace-nowrap">↻ 재요청</button>
                <button @click="openBoxPlan(pr)" :class="boxPlanBtnClass(pr)"
                  :title="pr.has_box_plan ? '분할선적 박스계획 보기/수정' : '분할선적 박스계획 작성(생산팀에 포장 지시)'"
                  class="px-2 py-0.5 text-[10px] rounded border whitespace-nowrap">📦 박스계획</button>
              </div>
            </div>
          </div>
        </li>
      </ul>
    </div>

    <!-- 페이지네이션 (리스트 뷰 전용) -->
    <div v-if="viewMode==='list' && total > 0" class="mt-4 flex justify-between items-center text-sm">
      <div class="text-gray-500">총 {{ total }}건 중 {{ items.length ? skip + 1 : 0 }} - {{ skip + items.length }}건</div>
      <div class="flex gap-2 items-center">
        <button class="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-50" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">이전</button>
        <span class="px-3 py-1">{{ currentPage }} / {{ totalPages }}</span>
        <button class="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-50" :disabled="!hasMore" @click="goToPage(currentPage + 1)">다음</button>
      </div>
    </div>

    <!-- 합배송 CI 발행 바(출고건 2건 이상 체크 시) -->
    <div v-if="mergeSel.length >= 2"
      class="fixed bottom-5 left-1/2 -translate-x-1/2 z-40 bg-white border border-gray-200 shadow-lg rounded-full pl-4 pr-2 py-2 flex items-center gap-3">
      <span class="text-sm text-gray-700">합배송 선택 <b>{{ mergeSel.length }}</b>건</span>
      <button class="text-xs text-gray-400 hover:text-gray-600" @click="mergeSel = []">해제</button>
      <button @click="handleCreateCiMerged" :disabled="mergeBusy"
        class="px-4 py-1.5 text-sm bg-teal-600 text-white rounded-full hover:bg-teal-700 disabled:opacity-50">
        {{ mergeBusy ? '생성 중…' : '📄 합배송 CI 생성' }}
      </button>
    </div>

    <!-- 분할선적 CI 발행 모달 -->
    <CiSplitModal
      v-if="showSplit && splitPrIds.length"
      :pr-ids="splitPrIds"
      @close="showSplit = false"
      @created="onSplitCreated"
    />

    <!-- 박스 분할계획 모달 -->
    <BoxPlanModal
      v-if="boxPlanPr"
      :pr="boxPlanPr"
      @close="boxPlanPr = null"
      @saved="onBoxPlanSaved"
    />

    <!-- 박스별 CI 발행 모달 -->
    <BoxCiModal
      v-if="boxCiPr"
      :pr="boxCiPr"
      @close="boxCiPr = null"
      @issued="onBoxCiIssued"
    />

    <!-- 상세 (읽기전용) -->
    <ProductionRequestDetailModal
      v-if="showDetail && selectedId !== null"
      :request-id="selectedId"
      readonly
      @close="showDetail = false"
    />

    <!-- 수정 폼 (미확인·반려 건 영업 수정) -->
    <ProductionRequestFormModal
      v-if="showFormModal"
      :request-id="editingId"
      :customers="customers"
      @close="showFormModal = false; editingId = null"
      @saved="onFormSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import {
  productionRequestApi,
  prStatusLabels,
  prStatusStyles,
  type ProductionRequestListItem,
  type ProductionRequest,
} from '@/api/productionRequest'
import { partnerApi } from '@/api/partner'
import { useToast } from '@/composables/useToast'
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import ProductionRequestDetailModal from '@/views/production/components/ProductionRequestDetailModal.vue'
import ProductionRequestCalendar from '@/views/production/components/ProductionRequestCalendar.vue'
import CiSplitModal from '@/views/sales/components/CiSplitModal.vue'
import BoxPlanModal from '@/views/sales/components/BoxPlanModal.vue'
import BoxCiModal from '@/views/sales/components/BoxCiModal.vue'
import ProductionRequestFormModal from '@/views/production/components/ProductionRequestFormModal.vue'

const router = useRouter()
const { showToast } = useToast()
const ciBusy = ref<number | null>(null)

// 미확인·반려 건 영업 수정(회수) — 수정 폼
const showFormModal = ref(false)
const editingId = ref<number | null>(null)
function openEdit(id: number) {
  editingId.value = id
  showFormModal.value = true
}
function onFormSaved() {
  showFormModal.value = false
  editingId.value = null
  loadData(); loadCounts()
}

// 초안 → 생산팀에 요청(전송): is_draft 해제 + 생산팀 알림
const submittingId = ref<number | null>(null)
async function handleSubmitDraft(pr: ProductionRequestListItem) {
  if (!confirm(`${pr.request_number}\n특이사항 입력을 마쳤나요?\n생산팀에 요청하면 생산팀 목록에 표시되고 알림이 발송됩니다.`)) return
  submittingId.value = pr.id
  try {
    await productionRequestApi.submitDraft(pr.id)
    showToast('생산팀에 요청되었습니다', 'success')
    loadData(); loadCounts()
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '요청 전송에 실패했습니다', 'error')
  } finally {
    submittingId.value = null
  }
}
// 초안(임시) 회수(삭제) — 아직 전송 전 건만
const withdrawingId = ref<number | null>(null)
async function handleWithdrawDraft(pr: ProductionRequestListItem) {
  if (!confirm(`${pr.request_number}\n아직 생산팀에 전송하지 않은 임시 생산요청입니다.\n회수(삭제)하시겠습니까? 되돌릴 수 없습니다.`)) return
  withdrawingId.value = pr.id
  try {
    await productionRequestApi.withdrawDraft(pr.id)
    showToast('임시 생산요청을 회수했습니다', 'success')
    loadData(); loadCounts()
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '회수에 실패했습니다', 'error')
  } finally {
    withdrawingId.value = null
  }
}
// 회수(삭제) — 확인 전 요청 철회
async function handleWithdraw(pr: ProductionRequestListItem) {
  if (!confirm(`${pr.request_number}\n생산 요청을 회수(삭제)하시겠습니까? 되돌릴 수 없습니다.`)) return
  try {
    await productionRequestApi.delete(pr.id)
    showToast('요청이 회수되었습니다', 'success')
    loadData(); loadCounts()
  } catch (e: any) {
    showToast(e?.response?.data?.detail?.message || e?.response?.data?.detail || '회수에 실패했습니다', 'error')
  }
}
// 반려 → 재요청(수정 후 다시 생산팀으로)
async function handleResubmit(pr: ProductionRequestListItem) {
  if (!confirm(`${pr.request_number}\n다시 생산팀에 요청하시겠습니까?`)) return
  try {
    await productionRequestApi.changeStatus(pr.id, 'REQUESTED')
    showToast('재요청되었습니다', 'success')
    loadData(); loadCounts()
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '재요청에 실패했습니다', 'error')
  }
}

// 출고건 → CI 생성 (연결된 PI를 CI로 전환) 후 CI 탭으로 이동해 마무리
async function handleCreateCi(pr: ProductionRequestListItem) {
  ciBusy.value = pr.id
  try {
    const res = await productionRequestApi.createCi(pr.id)
    showToast(res.already_exists ? `이미 생성된 CI: ${res.ci_number}` : `CI 생성 완료: ${res.ci_number}`, 'success')
    router.push({ query: { tab: 'ci' } })  // CI 탭에서 출고/포장 정보 입력 후 발행
  } catch (e: any) {
    showToast(e?.response?.data?.detail || 'CI 생성에 실패했습니다', 'error')
  } finally {
    ciBusy.value = null
  }
}

// 분할선적: 한 출고건을 배치로 나눠 여러 CI
const showSplit = ref(false)
const splitPrIds = ref<number[]>([])
function openSplit(pr: ProductionRequestListItem) {
  splitPrIds.value = [pr.id]
  showSplit.value = true
}
function onSplitCreated() {
  showSplit.value = false
  splitPrIds.value = []
  loadData(); loadCounts()
  router.push({ query: { tab: 'ci' } })
}

// 박스 분할계획(영업 작성 → 생산 포장 → 박스별 CI)
const boxPlanPr = ref<ProductionRequest | null>(null)
function boxPlanBtnClass(pr: ProductionRequestListItem) {
  return pr.has_box_plan
    ? 'border-indigo-300 text-indigo-700 bg-indigo-50 hover:bg-indigo-100'
    : 'border-gray-300 text-gray-500 hover:bg-gray-50'
}
async function openBoxPlan(pr: ProductionRequestListItem) {
  try {
    // 전체 품목이 필요하므로 상세를 조회해서 모달에 전달
    boxPlanPr.value = await productionRequestApi.getById(pr.id)
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '생산요청을 불러오지 못했습니다', 'error')
  }
}
function onBoxPlanSaved(updated: ProductionRequest) {
  // 목록 배지 즉시 반영
  const row = items.value.find((r) => r.id === updated.id)
  if (row) row.has_box_plan = !!(updated.box_plan && updated.box_plan.length)
  boxPlanPr.value = null
}

// 박스별 CI 발행(SHIPPED)
const boxCiPr = ref<ProductionRequest | null>(null)
async function openBoxCi(pr: ProductionRequestListItem) {
  try {
    boxCiPr.value = await productionRequestApi.getById(pr.id)
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '생산요청을 불러오지 못했습니다', 'error')
  }
}
function onBoxCiIssued() {
  loadData(); loadCounts()
}

// 합배송: 출고건 여러 개 → 하나의 CI(같은 고객)
const mergeSel = ref<number[]>([])
const mergeBusy = ref(false)
async function handleCreateCiMerged() {
  const sel = items.value.filter((p) => mergeSel.value.includes(p.id))
  const custs = new Set(sel.map((p) => (p as any).customer_id ?? p.customer?.id))
  if (custs.size > 1) { showToast('같은 고객의 출고건만 합배송할 수 있습니다', 'error'); return }
  if (!confirm(`선택한 ${mergeSel.value.length}건을 하나의 CI로 합배송 발행할까요?`)) return
  mergeBusy.value = true
  try {
    const res = await productionRequestApi.createCiMerged(mergeSel.value)
    showToast(`합배송 CI 생성: ${res.ci_number} (${res.merged_count}건)`, 'success')
    mergeSel.value = []
    router.push({ query: { tab: 'ci' } })
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '합배송 CI 생성에 실패했습니다', 'error')
  } finally {
    mergeBusy.value = false
  }
}

// 발송 완료(영업 처리) → 생산팀은 발송여부만 파악
async function handleDeliver(pr: ProductionRequestListItem) {
  if (!confirm(`${pr.request_number}\n발송 완료로 처리하시겠습니까? (생산팀 현황에 발송여부가 표시됩니다)`)) return
  try {
    await productionRequestApi.changeStatus(pr.id, 'DELIVERED')
    showToast('발송 완료 처리되었습니다', 'success')
    reload()
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '처리에 실패했습니다', 'error')
  }
}

// 파이프라인 4단계 (생산요청+생산부확인 통합, 확인 유무는 별도 배지로 표기)
const STAGES = [
  { key: 'REQUESTED', label: '생산요청' },
  { key: 'IN_PROGRESS', label: '생산진행' },
  { key: 'SHIPPED', label: '출고' },
  { key: 'DELIVERED', label: '발송완료' },
]
const STAGE_IDX: Record<string, number> = { REQUESTED: 0, APPROVED: 0, IN_PROGRESS: 1, COMPLETED: 1, SHIPPED: 2, DELIVERED: 3 }
// 확인 유무: REQUESTED는 미확인, APPROVED 이상(분기 제외)은 확인됨
const isConfirmed = (s: string) => ['APPROVED', 'IN_PROGRESS', 'COMPLETED', 'SHIPPED', 'DELIVERED'].includes(s)
const STAGE_FILL: Record<string, string> = { REQUESTED: 'bg-yellow-400', APPROVED: 'bg-blue-500', IN_PROGRESS: 'bg-indigo-500', COMPLETED: 'bg-indigo-500', SHIPPED: 'bg-teal-500', DELIVERED: 'bg-purple-500' }
const BRANCH = ['HOLD', 'REJECTED', 'CANCELLED']

const stageIdx = (s: string) => STAGE_IDX[s] ?? 0
const stageFill = (s: string) => STAGE_FILL[s] || 'bg-gray-400'
const isBranch = (s: string) => BRANCH.includes(s)
// 현재 단계 콤팩트 라벨(요청+확인 통합)
function compactStageLabel(s: string): string {
  if (s === 'REQUESTED' || s === 'APPROVED') return '생산요청'
  const m: Record<string, string> = { IN_PROGRESS: '생산진행', COMPLETED: '생산진행', SHIPPED: '출고', DELIVERED: '발송완료', HOLD: '보류', REJECTED: '반려', CANCELLED: '취소' }
  return m[s] || s
}
const isDone = (s: string) => ['DELIVERED', 'CANCELLED', 'REJECTED'].includes(s)
// 영업 수정 가능: 출고(SHIPPED) 이전 모든 상태(요청·보류·승인·진행중·완료·반려). 출고/발송/취소는 불가
const canSalesEdit = (s: string) => !['SHIPPED', 'DELIVERED', 'CANCELLED'].includes(s)
const branchIcon = (s: string) => ({ HOLD: '⏸', REJECTED: '✕', CANCELLED: '⊘' } as Record<string, string>)[s] || ''

// 요약 타일 (생산요청+생산부확인 통합 → 콤마 다중 상태로 조회)
const DRAFT_KEY = '__DRAFT__'  // 초안(미전송) 필터 키
const summaryTiles = [
  { status: DRAFT_KEY, label: '초안(미전송)', dot: 'bg-gray-400' },
  { status: 'REQUESTED,APPROVED', label: '생산 요청', dot: 'bg-yellow-400' },
  { status: 'IN_PROGRESS', label: '생산 진행중', dot: 'bg-indigo-500' },
  { status: 'SHIPPED', label: '생산 출고', dot: 'bg-teal-500' },
  { status: 'DELIVERED', label: '발송 완료', dot: 'bg-purple-500' },
  { status: 'HOLD', label: '보류', dot: 'bg-orange-400' },
  { status: 'REJECTED', label: '반려', dot: 'bg-red-400' },
]

const loading = ref(false)
const items = ref<ProductionRequestListItem[]>([])
const counts = ref<Record<string, number>>({})
const statusFilter = ref<string>('')

// 필터
const keyword = ref('')
const customerId = ref<number | null>(null)
const customerSearchText = ref('')
const showCustomerDropdown = ref(false)
const customerBoxRef = ref<HTMLElement | null>(null)
const customers = ref<{ id: number; name: string }[]>([])
const fromDate = ref('')
const toDate = ref('')

// 페이지네이션
const PAGE_SIZE = 30
const skip = ref(0)
const total = ref(0)
const hasMore = ref(false)
const currentPage = computed(() => Math.floor(skip.value / PAGE_SIZE) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

// 상세
const viewMode = ref<'list' | 'calendar'>('list')
const showDetail = ref(false)
const selectedId = ref<number | null>(null)

const filteredCustomers = computed(() => {
  const q = customerSearchText.value.trim().toLowerCase()
  if (!q) return customers.value
  return customers.value.filter(c => c.name.toLowerCase().includes(q))
})

function partLabel(pr: ProductionRequestListItem): string {
  const it = pr.items?.[0]
  const p = it?.product_part
  return p?.part_number_display || p?.part_number || p?.part_name || it?.custom_product_code || it?.custom_product_name || '-'
}
function itemLabel(it: any): string {
  const p = it?.product_part
  return p?.part_number_display || p?.part_number || p?.part_name || it?.custom_product_code || it?.custom_product_name || '-'
}
function qi(v: any): number { return Math.round(Number(v) || 0) }  // 수량 자연수
function fmtDate(d?: string) { return d ? (d.split('T')[0] ?? d).replace(/-/g, '.') : '-' }
// 첨부(도면/사진) 개수
function attachCount(pr: ProductionRequestListItem): number {
  return (pr.attachment_files || []).length
}
// 출고 packing list 총 박스 수
function packBoxes(pr: ProductionRequestListItem): number {
  return (pr.packing_list || []).reduce((s: number, b: any) => s + (Number(b.quantity) || 0), 0)
}
function fmtMd(d?: string | null): string {
  if (!d) return ''
  const p = (d.split('T')[0] ?? d).split('-')
  return p.length === 3 ? `${p[1]}/${p[2]}` : ''
}
function isOverdue(d?: string) { return d ? new Date(d) < new Date() : false }

function baseParams() {
  const p: any = { limit: PAGE_SIZE }
  if (keyword.value.trim()) p.keyword = keyword.value.trim()
  if (customerId.value) p.customer_id = customerId.value
  if (fromDate.value) p.from_date = fromDate.value
  if (toDate.value) p.to_date = toDate.value
  return p
}

async function loadData() {
  loading.value = true
  try {
    const params: any = { ...baseParams(), skip: skip.value }
    // 초안 타일이면 초안만, 그 외에는 초안 제외(정식만) (v0.87.0)
    if (statusFilter.value === DRAFT_KEY) {
      params.is_draft = true
    } else {
      params.is_draft = false
      if (statusFilter.value) params.status = statusFilter.value
    }
    const res = await productionRequestApi.getAll(params)
    items.value = res.items || []
    total.value = res.total || 0
    hasMore.value = !!res.has_more
  } catch { items.value = []; total.value = 0; hasMore.value = false }
  finally { loading.value = false }
}

async function loadCounts() {
  for (const t of summaryTiles) {
    try {
      const p: any = { ...baseParams(), limit: 1 }
      if (t.status === DRAFT_KEY) p.is_draft = true
      else { p.is_draft = false; p.status = t.status }
      const res = await productionRequestApi.getAll(p)
      counts.value = { ...counts.value, [t.status]: res.total || 0 }
    } catch { counts.value = { ...counts.value, [t.status]: 0 } }
  }
}

function applySearch() { skip.value = 0; loadData(); loadCounts() }
const debouncedSearch = useDebouncedSearch(() => applySearch())
function reload() { loadData(); loadCounts() }
function resetFilters() {
  keyword.value = ''; customerId.value = null; customerSearchText.value = ''
  fromDate.value = ''; toDate.value = ''; statusFilter.value = ''
  skip.value = 0; loadData(); loadCounts()
}
function toggleStatusFilter(s: string) {
  statusFilter.value = statusFilter.value === s ? '' : s
  skip.value = 0; loadData()
}
function goToPage(p: number) {
  const page = Math.min(Math.max(1, p), totalPages.value)
  skip.value = (page - 1) * PAGE_SIZE
  loadData()
}
function selectCustomer(id: number | null, name: string) {
  customerId.value = id; customerSearchText.value = name; showCustomerDropdown.value = false; applySearch()
}
function onCustomerClickOutside(e: MouseEvent) {
  if (customerBoxRef.value && !customerBoxRef.value.contains(e.target as Node)) showCustomerDropdown.value = false
}
function openDetail(id: number) { selectedId.value = id; showDetail.value = true }

async function loadCustomers() {
  try {
    const res = await partnerApi.getAll({ is_customer: true, limit: 300 })
    customers.value = (res.data.items || []).map((p: any) => ({ id: p.id, name: p.partner_name }))
  } catch { customers.value = [] }
}

function loadAll() { loadData(); loadCounts(); loadCustomers() }
onMounted(() => { loadAll(); document.addEventListener('click', onCustomerClickOutside) })
onBeforeUnmount(() => document.removeEventListener('click', onCustomerClickOutside))
defineExpose({ loadAll })
</script>
