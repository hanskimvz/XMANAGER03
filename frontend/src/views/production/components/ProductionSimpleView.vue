<template>
  <div class="p-4 sm:p-6">
    <!-- 헤더: 검색/필터 + 등록 -->
    <div class="flex flex-wrap items-end justify-between gap-3 mb-4">
      <div class="flex flex-wrap items-end gap-2">
        <!-- 키워드 -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">검색</label>
          <input
            v-model="keyword"
            type="text"
            placeholder="요청번호·고객주문번호"
            class="w-52 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            @keyup.enter="applySearch"
            @input="debouncedSearch"
          />
        </div>
        <!-- 고객사 콤보박스 -->
        <div class="relative" ref="customerBoxRef">
          <label class="block text-xs font-medium text-gray-500 mb-1">고객사</label>
          <div class="relative">
            <input
              v-model="customerSearchText"
              type="text"
              placeholder="검색 또는 선택"
              class="w-44 px-3 py-2 pr-8 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              @focus="showCustomerDropdown = true"
              @input="showCustomerDropdown = true"
            />
            <button
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              @click="showCustomerDropdown = !showCustomerDropdown"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
            </button>
            <div
              v-if="showCustomerDropdown"
              class="absolute z-50 w-56 mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-56 overflow-y-auto"
            >
              <div class="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm" @click="selectCustomer(null, '')">전체</div>
              <div
                v-for="c in filteredCustomers"
                :key="c.id"
                class="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm truncate"
                @click="selectCustomer(c.id, c.name)"
              >{{ c.name }}</div>
              <div v-if="filteredCustomers.length === 0" class="px-3 py-2 text-sm text-gray-400">검색 결과 없음</div>
            </div>
          </div>
        </div>
        <!-- 요청일 기간 -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">요청일</label>
          <div class="flex items-center gap-1">
            <input v-model="fromDate" type="date" @change="applySearch"
              class="px-2 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" />
            <span class="text-gray-400 text-xs">~</span>
            <input v-model="toDate" type="date" @change="applySearch"
              class="px-2 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>
        <button
          class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          @click="applySearch"
        >검색</button>
        <button
          class="px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
          @click="resetFilters"
        >초기화</button>
      </div>
      <div class="flex items-center gap-2">
        <!-- 리스트/캘린더 전환(기본 리스트) -->
        <div class="inline-flex rounded-lg border overflow-hidden">
          <button @click="viewMode='list'" class="px-3 py-2 text-sm"
            :class="viewMode==='list' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'">리스트</button>
          <button @click="viewMode='calendar'" class="px-3 py-2 text-sm border-l"
            :class="viewMode==='calendar' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'">📅 캘린더</button>
        </div>
        <button v-if="isAdmin" @click="showNotifyRecipients = true"
          title="새 생산요청 알림을 받을 생산팀 인원 지정"
          class="px-3 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 text-sm">
          🔔 알림 수신자
        </button>
        <button @click="openCreateModal"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
          + 생산요청 등록
        </button>
      </div>
    </div>

    <ProductionNotifyRecipientsModal v-if="showNotifyRecipients" @close="showNotifyRecipients = false" />

    <!-- 캘린더 뷰 (생산팀 온디맨드) -->
    <div v-if="viewMode==='calendar'" class="bg-white rounded-lg shadow-sm border p-3">
      <ProductionRequestCalendar :customer-id="customerId ?? undefined" @open-detail="openDetail" />
    </div>

    <!-- 상태 탭 -->
    <div v-if="viewMode==='list'" class="flex items-center gap-1 mb-4 border-b overflow-x-auto">
      <button v-for="tab in tabs" :key="tab.status"
        @click="changeTab(tab.status)"
        :class="activeTab === tab.status
          ? 'border-b-2 border-blue-600 text-blue-600 font-semibold'
          : 'text-gray-500 hover:text-gray-700'"
        class="px-4 py-2.5 text-sm whitespace-nowrap transition-colors flex items-center gap-2">
        {{ tab.label }}
        <span v-if="tabCounts[tab.status] !== undefined"
          :class="activeTab === tab.status ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'"
          class="px-1.5 py-0.5 text-[10px] font-bold rounded-full">
          {{ tabCounts[tab.status] || 0 }}
        </span>
      </button>
    </div>

    <!-- 리스트 -->
    <div v-if="viewMode==='list'" class="bg-white rounded-lg shadow-sm border overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400">로딩 중...</div>
      <div v-else-if="items.length === 0" class="p-8 text-center text-gray-400">
        {{ keyword || customerId ? '검색 결과가 없습니다' : (isMergedTab ? '생산요청이 없습니다' : '해당 항목이 없습니다') }}
      </div>

      <!-- 데스크톱 테이블 -->
      <table v-else class="min-w-full divide-y divide-gray-200 hidden sm:table">
        <thead class="bg-gray-50">
          <tr>
            <th @click="setSort('request_number')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 cursor-pointer select-none hover:text-gray-700 whitespace-nowrap">요청번호<span class="text-gray-300">{{ sortArrow('request_number') }}</span></th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">거래처</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">품목</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500">수량</th>
            <th @click="setSort('requested_at')" class="px-4 py-3 text-center text-xs font-medium text-gray-500 whitespace-nowrap cursor-pointer select-none hover:text-gray-700">요청일<span class="text-gray-300">{{ sortArrow('requested_at') }}</span></th>
            <th @click="setSort('due_date')" class="px-4 py-3 text-center text-xs font-medium text-gray-500 whitespace-nowrap cursor-pointer select-none hover:text-gray-700">납기일<span class="text-gray-300">{{ sortArrow('due_date') }}</span></th>
            <th @click="setSort('shipped_at')" class="px-4 py-3 text-center text-xs font-medium text-gray-500 whitespace-nowrap cursor-pointer select-none hover:text-gray-700">출고일<span class="text-gray-300">{{ sortArrow('shipped_at') }}</span></th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 whitespace-nowrap">영업</th>
            <th v-if="isMergedTab" class="px-3 py-3 text-center text-xs font-medium text-gray-500 whitespace-nowrap">확인</th>
            <th v-if="activeTab === 'ALL'" class="px-4 py-3 text-center text-xs font-medium text-gray-500">상태</th>
            <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 whitespace-nowrap">인서트<br>출고</th>
            <th class="px-3 py-3 text-center text-xs font-medium text-gray-500 whitespace-nowrap">검토<br>필요</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500">작업</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          <tr v-for="pr in displayItems" :key="pr.id" class="hover:bg-gray-50 cursor-pointer"
            :class="pr.needs_review ? 'bg-amber-50/60' : ''" @click="openDetail(pr.id)">
            <td class="px-4 py-3">
              <span class="text-sm font-medium text-blue-600">{{ pr.request_number }}</span>
              <div v-if="pr.pi_number" class="text-[10px] text-gray-400">PI: {{ pr.pi_number }}</div>
            </td>
            <td class="px-4 py-3 text-sm text-gray-800">{{ pr.customer?.partner_name || '-' }}</td>
            <td class="px-4 py-3 text-sm">
              <div v-if="pr.items && pr.items.length > 0">
                <span class="text-gray-800 font-mono">{{ partLabel(pr.items![0]!) }}</span>
                <span v-if="pr.items.length > 1" class="text-gray-400 text-xs ml-1">외 {{ pr.items.length - 1 }}건</span>
              </div>
              <span v-else class="text-gray-400">-</span>
            </td>
            <td class="px-4 py-3 text-sm text-center">
              <div v-if="pr.items && pr.items.length > 0" class="space-y-0.5">
                <div v-for="item in pr.items" :key="item.id" class="text-xs">
                  <span class="font-medium">{{ formatQty(item.requested_quantity) }}</span>
                  <span class="text-gray-400 ml-0.5">{{ item.uom || 'EA' }}</span>
                </div>
              </div>
              <span v-else>-</span>
            </td>
            <td class="px-4 py-3 text-sm text-center text-gray-500">{{ formatDate(pr.requested_at) }}</td>
            <td class="px-4 py-3 text-sm text-center" :class="isOverdue(pr.due_date) ? 'text-red-600 font-medium' : 'text-gray-600'">
              {{ formatDate(pr.due_date) }}
            </td>
            <td class="px-4 py-3 text-sm text-center text-gray-500 whitespace-nowrap">{{ pr.shipped_at ? formatDate(pr.shipped_at) : '-' }}</td>
            <td class="px-4 py-3 text-sm text-gray-700">{{ pr.prepared_by_name || '-' }}</td>
            <!-- 확인 체크박스 (생산요청 통합탭): 생산부 확인 여부 기록. 시작과 별개 -->
            <td v-if="isMergedTab" class="px-3 py-3 text-center" @click.stop>
              <label v-if="pr.status === 'REQUESTED' || pr.status === 'APPROVED'"
                class="inline-flex items-center gap-1.5 cursor-pointer"
                :title="pr.status === 'APPROVED' ? '확인됨 — 클릭 시 미확인으로 되돌림' : '생산부 확인으로 기록'">
                <input type="checkbox" :checked="pr.status === 'APPROVED'" @click.prevent="toggleConfirm(pr)"
                  class="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                <span class="text-[11px]" :class="pr.status === 'APPROVED' ? 'text-blue-700 font-medium' : 'text-gray-400'">확인</span>
              </label>
              <span v-else class="text-gray-300 text-xs">-</span>
            </td>
            <td v-if="activeTab === 'ALL'" class="px-4 py-3 text-center">
              <span :class="['px-2 py-0.5 text-[11px] rounded-full whitespace-nowrap', prStatusStyles[pr.status]]">{{ prStatusLabels[pr.status] }}</span>
            </td>
            <!-- 인서트 출고: 3상태(미출고=클릭 확정 / 출고됨=메뉴 수정·취소 / 인서트없음=N/A) -->
            <td class="px-3 py-3 text-center" @click.stop>
              <div class="relative inline-block">
                <!-- 인서트 없음(N/A) -->
                <button v-if="pr.insert_not_applicable" @click="toggleInsertMenu(pr)"
                  title="인서트 없음(해당없음) — 클릭하면 되돌리기"
                  class="px-2 py-1 text-[11px] rounded border bg-gray-100 text-gray-400 border-gray-200 whitespace-nowrap">
                  — 인서트 없음 ▾
                </button>
                <!-- 출고됨 -->
                <button v-else-if="pr.insert_shipped" @click="toggleInsertMenu(pr)"
                  title="클릭: 출고일 수정 / 취소"
                  class="px-2 py-1 text-[11px] rounded border bg-emerald-100 text-emerald-700 border-emerald-200 whitespace-nowrap">
                  ✓ 인서트 {{ fmtMd(pr.insert_shipped_at) }} ▾
                </button>
                <!-- 미출고: 본 클릭=오늘 확정, ▾=메뉴(인서트 없음) -->
                <span v-else class="inline-flex items-stretch rounded border border-gray-200 overflow-hidden">
                  <button @click="setInsert(pr)" title="클릭하면 오늘 날짜로 인서트 출고 확정"
                    class="px-2 py-1 text-[11px] bg-gray-50 text-gray-400 hover:bg-gray-100 whitespace-nowrap">인서트 출고</button>
                  <button @click="toggleInsertMenu(pr)" title="더보기"
                    class="px-1 py-1 text-[11px] bg-gray-50 text-gray-400 hover:bg-gray-100 border-l border-gray-200">▾</button>
                </span>

                <!-- 상태별 메뉴 -->
                <div v-if="insertMenuFor === pr.id"
                  class="absolute z-30 mt-1 right-0 w-48 bg-white border border-gray-200 rounded-lg shadow-lg p-2 text-left">
                  <template v-if="pr.insert_shipped">
                    <label class="block text-[10px] text-gray-500 mb-0.5">출고일 수정</label>
                    <div class="flex items-center gap-1 mb-2">
                      <input v-model="insertEditDate" type="date" class="flex-1 border rounded px-1.5 py-1 text-[11px]" />
                      <button @click="saveInsertDate(pr)" :disabled="insertSaving"
                        class="px-2 py-1 text-[11px] rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">저장</button>
                    </div>
                    <button @click="cancelInsert(pr)"
                      class="w-full px-2 py-1 text-[11px] rounded border border-red-200 text-red-600 hover:bg-red-50 mb-1">✕ 인서트 출고 취소</button>
                    <button @click="markNA(pr)"
                      class="w-full px-2 py-1 text-[11px] rounded border border-gray-200 text-gray-500 hover:bg-gray-50">— 인서트 없음으로 표시</button>
                  </template>
                  <template v-else-if="pr.insert_not_applicable">
                    <button @click="unmarkNA(pr)"
                      class="w-full px-2 py-1 text-[11px] rounded border border-gray-200 text-gray-600 hover:bg-gray-50">↩ 인서트 있음으로 되돌리기</button>
                  </template>
                  <template v-else>
                    <button @click="markNA(pr)"
                      class="w-full px-2 py-1 text-[11px] rounded border border-gray-200 text-gray-500 hover:bg-gray-50">— 인서트 없음으로 표시</button>
                  </template>
                </div>
              </div>
            </td>
            <!-- 검토 필요: 토글 + 사유(영업에 표시) -->
            <td class="px-3 py-3 text-center" @click.stop>
              <button @click="toggleReview(pr)" :title="pr.review_note || '검토 필요 표시 (사유 입력)'"
                :class="pr.needs_review ? 'bg-amber-100 text-amber-700 border-amber-300' : 'bg-gray-50 text-gray-400 border-gray-200 hover:bg-gray-100'"
                class="px-2 py-1 text-[11px] rounded border whitespace-nowrap transition-colors">
                <template v-if="pr.needs_review">⚠ 검토</template>
                <template v-else>검토</template>
              </button>
              <div v-if="pr.needs_review && pr.review_note"
                class="text-[9px] text-amber-600 mt-0.5 max-w-[130px] truncate mx-auto" :title="pr.review_note">{{ pr.review_note }}</div>
            </td>
            <td class="px-4 py-3 text-center" @click.stop>
              <template v-if="nextAction(pr)">
                <button @click="doNextAction(pr)"
                  :class="nextAction(pr)?.class"
                  class="px-3 py-1 text-xs font-medium rounded hover:opacity-90 transition-opacity">
                  {{ nextAction(pr)?.label }}
                </button>
              </template>
              <!-- 발송여부(영업 처리): 생산팀은 파악만. 언제 출고됐는지 표시 -->
              <span v-else-if="pr.status === 'SHIPPED'" class="text-[11px] whitespace-nowrap leading-tight inline-block"
                :title="pr.shipped_at ? `출고 ${formatDate(pr.shipped_at)}` : ''">
                <span class="text-teal-600 font-medium">🚚 출고 {{ fmtMdHm(pr.shipped_at || pr.production_shipped_at) }}</span><br>
                <span class="text-gray-400">발송 대기</span>
                <button @click.stop="openPackingEdit(pr)" title="실제 포장이 바뀐 경우 패킹 정보를 수정합니다 (출고 이력은 유지)"
                  class="block mx-auto mt-0.5 px-1.5 py-0.5 text-[10px] rounded border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-700">📦 패킹 수정</button>
              </span>
              <span v-else-if="pr.status === 'DELIVERED'" class="text-[11px] whitespace-nowrap leading-tight inline-block">
                <span class="text-purple-600">✓ 발송 {{ fmtMd(pr.delivered_at) }}</span>
                <button @click.stop="openPackingEdit(pr)" title="실제 포장이 바뀐 경우 패킹 정보를 수정합니다 (발송 이력은 유지)"
                  class="block mx-auto mt-0.5 px-1.5 py-0.5 text-[10px] rounded border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-700">📦 패킹 수정</button>
              </span>
              <span v-else class="text-gray-300 text-xs">-</span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 모바일 카드 -->
      <div v-if="items.length > 0" class="sm:hidden divide-y divide-gray-200">
        <div v-for="pr in displayItems" :key="pr.id" @click="openDetail(pr.id)"
          class="p-4 hover:bg-gray-50 cursor-pointer">
          <div class="flex justify-between items-start mb-2">
            <div>
              <span class="text-sm font-medium text-blue-600">{{ pr.request_number }}</span>
              <span class="text-xs text-gray-500 ml-2">{{ pr.customer?.partner_name }}</span>
            </div>
            <span :class="['px-2 py-0.5 text-[10px] rounded-full', prStatusStyles[pr.status]]">{{ prStatusLabels[pr.status] }}</span>
          </div>
          <div class="text-xs text-gray-600 mb-1">
            <span v-if="pr.items && pr.items.length > 0">
              <span class="font-mono">{{ partLabel(pr.items![0]!) }}</span>
              <span v-if="pr.items.length > 1" class="text-gray-400">외 {{ pr.items.length - 1 }}건</span>
            </span>
          </div>
          <div class="flex justify-between items-center mt-2">
            <span class="text-xs text-gray-400">요청: {{ formatDate(pr.requested_at) }} · 납기: {{ formatDate(pr.due_date) }}</span>
            <template v-if="nextAction(pr)">
              <button @click.stop="doNextAction(pr)"
                :class="nextAction(pr)?.class"
                class="px-3 py-1 text-xs font-medium rounded">
                {{ nextAction(pr)?.label }}
              </button>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- 페이지네이션 (리스트 뷰 전용) -->
    <div v-if="viewMode==='list' && total > 0" class="mt-4 flex justify-between items-center text-sm">
      <div class="text-gray-500">
        총 {{ total }}건 중 {{ items.length ? skip + 1 : 0 }} - {{ skip + items.length }}건
      </div>
      <div class="flex gap-2 items-center">
        <button
          class="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-50"
          :disabled="currentPage === 1"
          @click="goToPage(currentPage - 1)"
        >이전</button>
        <span class="px-3 py-1">{{ currentPage }} / {{ totalPages }}</span>
        <button
          class="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-50"
          :disabled="!hasMore"
          @click="goToPage(currentPage + 1)"
        >다음</button>
      </div>
    </div>

    <!-- 상세 모달 -->
    <ProductionRequestDetailModal
      v-if="showDetail && selectedId !== null"
      :request-id="selectedId"
      @close="showDetail = false"
      @approve="handleApprove"
      @reject="handleReject"
      @hold="handleHold"
      @release-hold="handleReleaseHold"
      @cancel="handleCancel"
      @delete="handleDelete"
      @edit="openEditModal"
      @resubmit="handleResubmit"
    />

    <!-- 생산요청 등록/수정 모달 -->
    <ProductionRequestFormModal
      v-if="showFormModal"
      :request-id="editingId"
      :customers="customers"
      @close="closeFormModal"
      @saved="handleSaved"
    />

    <!-- 출고 packing list 모달 -->
    <PackingListModal
      v-if="showPacking && packingPr"
      :request-id="packingPr.id"
      :request-number="packingPr.request_number"
      :initial="packingPr.packing_list"
      :edit-mode="packingEditMode"
      @close="showPacking = false; packingPr = null; packingEditMode = false"
      @confirm="handlePackingConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, reactive, computed } from 'vue'
import {
  productionRequestApi,
  prStatusLabels,
  prStatusStyles,
  type ProductionRequestListItem,
  type ProductionRequestStatus,
} from '@/api/productionRequest'
import { partnerApi } from '@/api/partner'
import { useToast } from '@/composables/useToast'
import ProductionRequestDetailModal from '@/views/production/components/ProductionRequestDetailModal.vue'
import ProductionRequestCalendar from '@/views/production/components/ProductionRequestCalendar.vue'
import ProductionRequestFormModal from '@/views/production/components/ProductionRequestFormModal.vue'
import PackingListModal from '@/views/production/components/PackingListModal.vue'
import ProductionNotifyRecipientsModal from '@/views/production/components/ProductionNotifyRecipientsModal.vue'
import type { PackingBox } from '@/api/productionRequest'
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import { useAuth } from '@/stores/auth'

const emit = defineEmits<{ (e: 'data-changed'): void }>()
const { showToast } = useToast()
const { isAdmin } = useAuth()
const showNotifyRecipients = ref(false)

// 'ALL' = 전체(모든 상태 — 보류/반려/취소 포함) / 나머지는 상태 파이프라인
// '생산 요청'은 요청(미확인 REQUESTED)+생산부확인(APPROVED)을 통합 — page에서 확인 토글
const MERGED_REQUEST = 'REQUESTED,APPROVED'
const tabs = [
  { status: 'ALL' as const, label: '전체' },
  { status: MERGED_REQUEST, label: '생산 요청' },
  { status: 'IN_PROGRESS' as const, label: '생산 진행 중' },
  { status: 'SHIPPED' as const, label: '생산 출고' },
  { status: 'DELIVERED' as const, label: '발송 완료' },
  { status: 'REJECTED' as const, label: '반려' },
]

const activeTab = ref<string>(MERGED_REQUEST)
const isMergedTab = computed(() => activeTab.value === MERGED_REQUEST)
const loading = ref(false)
const items = ref<ProductionRequestListItem[]>([])
const tabCounts = reactive<Record<string, number>>({})

// 검색/필터
const keyword = ref('')
const customerId = ref<number | null>(null)
const fromDate = ref('')  // 요청일 시작
const toDate = ref('')    // 요청일 종료
const customerSearchText = ref('')
const showCustomerDropdown = ref(false)
const customerBoxRef = ref<HTMLElement | null>(null)

// 페이지네이션
const PAGE_SIZE = 50
const skip = ref(0)
const total = ref(0)
const hasMore = ref(false)
const currentPage = computed(() => Math.floor(skip.value / PAGE_SIZE) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

// 모달
const viewMode = ref<'list' | 'calendar'>('list')
const showDetail = ref(false)
const selectedId = ref<number | null>(null)
const showFormModal = ref(false)
const editingId = ref<number | null>(null)
const customers = ref<{ id: number; name: string }[]>([])

const filteredCustomers = computed(() => {
  const q = customerSearchText.value.trim().toLowerCase()
  if (!q) return customers.value
  return customers.value.filter((c) => c.name.toLowerCase().includes(q))
})

async function loadCustomers() {
  try {
    const res = await partnerApi.getAll({ is_customer: true, limit: 200 })
    customers.value = (res.data.items || []).map((p: any) => ({ id: p.id, name: p.partner_name }))
  } catch { customers.value = [] }
}

function selectCustomer(id: number | null, name: string) {
  customerId.value = id
  customerSearchText.value = name
  showCustomerDropdown.value = false
  applySearch()
}

function onCustomerClickOutside(e: MouseEvent) {
  if (customerBoxRef.value && !customerBoxRef.value.contains(e.target as Node)) {
    showCustomerDropdown.value = false
  }
}

function openCreateModal() {
  editingId.value = null
  showFormModal.value = true
}
function openEditModal(id: number) {
  editingId.value = id
  showDetail.value = false
  showFormModal.value = true
}
function closeFormModal() {
  showFormModal.value = false
  editingId.value = null
}
function handleSaved() {
  closeFormModal()
  loadAll()
  emit('data-changed')
}

// 탭 전환 → 1페이지부터
function changeTab(status: string) {
  activeTab.value = status
  skip.value = 0
  loadData()
}

const debouncedSearch = useDebouncedSearch(() => applySearch())

// 검색 적용 → 1페이지부터
function applySearch() {
  skip.value = 0
  loadData()
  loadTabCounts()
}

function resetFilters() {
  keyword.value = ''
  customerId.value = null
  customerSearchText.value = ''
  fromDate.value = ''
  toDate.value = ''
  skip.value = 0
  loadData()
  loadTabCounts()
}

function goToPage(page: number) {
  const p = Math.min(Math.max(1, page), totalPages.value)
  skip.value = (p - 1) * PAGE_SIZE
  loadData()
}

function baseParams() {
  // 생산팀 목록·카운트에서는 초안(미전송) 제외 (v0.87.0)
  const p: any = { limit: PAGE_SIZE, order_by: sortBy.value, order_desc: sortDesc.value, is_draft: false }
  if (keyword.value.trim()) p.keyword = keyword.value.trim()
  if (customerId.value) p.customer_id = customerId.value
  if (fromDate.value) p.from_date = fromDate.value
  if (toDate.value) p.to_date = toDate.value
  return p
}

// ── 헤더 클릭 정렬(서버 정렬) ──
const sortBy = ref<string>('created_at')  // 기본: 최신순
const sortDesc = ref<boolean>(true)
const userSorted = computed(() => sortBy.value !== 'created_at')
function setSort(field: string) {
  if (sortBy.value === field) {
    sortDesc.value = !sortDesc.value
  } else {
    sortBy.value = field
    sortDesc.value = false  // 새 컬럼은 오름차순부터
  }
  skip.value = 0
  loadData()
}
function sortArrow(field: string): string {
  if (sortBy.value !== field) return ' ↕'
  return sortDesc.value ? ' ▼' : ' ▲'
}

async function loadData() {
  loading.value = true
  try {
    const params = { ...baseParams(), skip: skip.value }
    if (activeTab.value !== 'ALL') params.status = activeTab.value
    const res = await productionRequestApi.getAll(params)
    items.value = res.items || []
    total.value = res.total || 0
    hasMore.value = !!res.has_more
  } catch {
    items.value = []
    total.value = 0
    hasMore.value = false
  } finally {
    loading.value = false
  }
}

async function loadTabCounts() {
  for (const tab of tabs) {
    try {
      const params: any = { ...baseParams(), limit: 1 }
      if (tab.status !== 'ALL') params.status = tab.status
      const res = await productionRequestApi.getAll(params)
      tabCounts[tab.status] = res.total || 0
    } catch { tabCounts[tab.status] = 0 }
  }
}

function openDetail(id: number) {
  selectedId.value = id
  showDetail.value = true
}

// 각 상태별 다음 액션
// - REQUESTED 확인: '확인' 토글 컬럼에서 처리(중복 방지 위해 여기선 없음)
// - SHIPPED 발송: 영업팀이 처리(생산측 버튼 제거) → 발송여부만 표기
function nextAction(pr: ProductionRequestListItem): { label: string; class: string; status: ProductionRequestStatus } | null {
  const map: Record<string, { label: string; class: string; status: ProductionRequestStatus }> = {
    REQUESTED: { label: '▶ 생산 시작', class: 'bg-indigo-600 text-white', status: 'IN_PROGRESS' },
    APPROVED: { label: '▶ 생산 시작', class: 'bg-indigo-600 text-white', status: 'IN_PROGRESS' },
    IN_PROGRESS: { label: '📦 출고', class: 'bg-green-600 text-white', status: 'SHIPPED' },
    COMPLETED: { label: '📦 출고', class: 'bg-green-600 text-white', status: 'SHIPPED' },
    REJECTED: { label: '↻ 재요청', class: 'bg-orange-500 text-white', status: 'REQUESTED' },
  }
  return map[pr.status] || null
}

// 표시용 목록: 통합 '생산 요청' 탭에서는 미확인(REQUESTED)을 상단에 노출
// (단, 사용자가 헤더로 명시 정렬한 경우엔 그 정렬을 그대로 존중)
const displayItems = computed(() => {
  if (!isMergedTab.value || userSorted.value) return items.value
  return [...items.value].sort((a, b) => {
    const ra = a.status === 'REQUESTED' ? 0 : 1
    const rb = b.status === 'REQUESTED' ? 0 : 1
    return ra - rb  // 안정 정렬 — 동순위는 서버 정렬(요청일) 유지
  })
})

// 확인 토글: 미확인(REQUESTED) → 확인(APPROVED), 확인 → 미확인(취소)
async function toggleConfirm(pr: ProductionRequestListItem) {
  try {
    if (pr.status === 'REQUESTED') {
      await productionRequestApi.approve(pr.id)
      showToast('생산부 확인 완료', 'success')
    } else if (pr.status === 'APPROVED') {
      if (!confirm(`${pr.request_number}\n확인을 취소하고 '미확인'으로 되돌리시겠습니까?`)) return
      await productionRequestApi.changeStatus(pr.id, 'REQUESTED')
      showToast('확인이 취소되었습니다', 'success')
    } else return
    loadData(); loadTabCounts(); emit('data-changed')
  } catch {
    showToast('처리에 실패했습니다', 'error')
  }
}

// 검토 필요 토글: 켜면 사유 입력(영업에 표시), 끄면 사유 정리
async function toggleReview(pr: ProductionRequestListItem) {
  if (!pr.needs_review) {
    const note = prompt('검토가 필요한 사유를 입력하세요. (영업팀 현황에 표시됩니다)', pr.review_note || '')
    if (note === null) return  // 취소
    const trimmed = note.trim()
    pr.needs_review = true
    pr.review_note = trimmed || null
    try {
      await productionRequestApi.updateFlags(pr.id, { needs_review: true, review_note: trimmed })
      emit('data-changed')
    } catch {
      pr.needs_review = false; pr.review_note = null
      showToast('검토 표시에 실패했습니다', 'error')
    }
  } else {
    if (!confirm('검토 필요 표시를 해제하시겠습니까?')) return
    pr.needs_review = false
    pr.review_note = null
    try {
      await productionRequestApi.updateFlags(pr.id, { needs_review: false })
      emit('data-changed')
    } catch {
      pr.needs_review = true
      showToast('해제에 실패했습니다', 'error')
    }
  }
}

async function doNextAction(pr: ProductionRequestListItem) {
  const action = nextAction(pr)
  if (!action) return
  // 출고(SHIPPED): packing list 입력 모달을 먼저 띄운다
  if (action.status === 'SHIPPED') {
    packingPr.value = pr
    showPacking.value = true
    return
  }
  try {
    await productionRequestApi.changeStatus(pr.id, action.status)
    showToast(`${action.label} 처리 완료`, 'success')
    loadData(); loadTabCounts(); emit('data-changed')
  } catch (err: any) {
    const msg = err?.response?.data?.detail || '처리에 실패했습니다'
    showToast(typeof msg === 'string' ? msg : '처리에 실패했습니다', 'error')
  }
}

// 출고 packing list 모달
const showPacking = ref(false)
const packingPr = ref<ProductionRequestListItem | null>(null)
// 출고 후 패킹 정보만 수정하는 모드(상태 전이 없음)
const packingEditMode = ref(false)

// 출고 완료 건의 패킹 정보 수정 열기
function openPackingEdit(pr: ProductionRequestListItem) {
  packingPr.value = pr
  packingEditMode.value = true
  showPacking.value = true
}

async function handlePackingConfirm(packingList: PackingBox[]) {
  const pr = packingPr.value
  if (!pr) return
  const editing = packingEditMode.value
  try {
    if (editing) {
      await productionRequestApi.updatePackingList(pr.id, packingList)
      showToast('패킹 정보가 수정되었습니다', 'success')
    } else {
      await productionRequestApi.ship(pr.id, packingList)
      showToast('출고 완료 처리되었습니다', 'success')
    }
    loadData(); loadTabCounts(); emit('data-changed')
  } catch (err: any) {
    const fallback = editing ? '패킹 정보 수정에 실패했습니다' : '출고 처리에 실패했습니다'
    const msg = err?.response?.data?.detail || fallback
    showToast(typeof msg === 'string' ? msg : fallback, 'error')
  } finally {
    showPacking.value = false
    packingPr.value = null
    packingEditMode.value = false
  }
}

async function handleApprove(id: number) {
  try {
    await productionRequestApi.approve(id)
    showToast('생산부 확인 완료', 'success')
    showDetail.value = false
    loadData(); loadTabCounts(); emit('data-changed')
  } catch { showToast('처리에 실패했습니다', 'error') }
}

async function handleReject(id: number) {
  const reason = prompt('반려 사유를 입력하세요:')
  if (reason === null || !reason.trim()) return
  try {
    await productionRequestApi.reject(id, { rejection_reason: reason.trim() })
    showToast('반려 처리되었습니다', 'success')
    showDetail.value = false
    loadAll(); emit('data-changed')
  } catch (e: any) {
    showToast(e?.response?.data?.detail?.message || '반려 실패', 'error')
  }
}

async function handleHold(id: number) {
  if (!confirm('보류 처리하시겠습니까?')) return
  try {
    await productionRequestApi.hold(id)
    showToast('보류 처리되었습니다', 'success')
    showDetail.value = false
    loadAll(); emit('data-changed')
  } catch (e: any) {
    showToast(e?.response?.data?.detail?.message || '보류 처리 실패', 'error')
  }
}

async function handleReleaseHold(id: number) {
  if (!confirm('보류를 해제하시겠습니까?')) return
  try {
    await productionRequestApi.releaseHold(id)
    showToast('보류가 해제되었습니다', 'success')
    showDetail.value = false
    loadAll(); emit('data-changed')
  } catch (e: any) {
    showToast(e?.response?.data?.detail?.message || '보류 해제 실패', 'error')
  }
}

async function handleCancel(id: number) {
  const reason = prompt('취소 사유를 입력하세요:')
  if (reason === null) return
  try {
    await productionRequestApi.cancel(id, reason)
    showToast('취소 처리되었습니다', 'success')
    showDetail.value = false
    loadAll(); emit('data-changed')
  } catch (e: any) {
    showToast(e?.response?.data?.detail?.message || '취소 실패', 'error')
  }
}

async function handleResubmit(id: number) {
  if (!confirm('반려 사유를 확인·수정하셨나요?\n다시 "생산 요청" 상태로 올립니다.')) return
  try {
    await productionRequestApi.changeStatus(id, 'REQUESTED')
    showToast('재요청되었습니다', 'success')
    showDetail.value = false
    loadAll(); emit('data-changed')
  } catch (e: any) {
    showToast(e?.response?.data?.detail?.message || '재요청 실패', 'error')
  }
}

async function handleDelete(id: number) {
  if (!confirm('생산 요청서를 완전히 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.')) return
  try {
    await productionRequestApi.delete(id)
    showToast('삭제되었습니다', 'success')
    showDetail.value = false
    loadAll(); emit('data-changed')
  } catch (e: any) {
    showToast(e?.response?.data?.detail?.message || '삭제 실패', 'error')
  }
}

// 진행 체크박스 토글 (인서트출고 / 생산출고 / 검토필요)
async function toggleFlag(
  pr: ProductionRequestListItem,
  flag: 'insert_shipped' | 'production_shipped' | 'needs_review',
  value: boolean,
) {
  const prev = (pr as any)[flag]
  ;(pr as any)[flag] = value
  try {
    const updated = await productionRequestApi.updateFlags(pr.id, { [flag]: value })
    // 서버가 기록한 완료 시각 반영
    ;(pr as any).insert_shipped_at = (updated as any).insert_shipped_at
    ;(pr as any).production_shipped_at = (updated as any).production_shipped_at
  } catch {
    ;(pr as any)[flag] = prev
    showToast('체크박스 변경에 실패했습니다', 'error')
  }
}

// ── 인서트 출고: 1회 클릭 확정(고정) + 칩 메뉴로만 수정/취소 ──
const insertMenuFor = ref<number | null>(null)
const insertEditDate = ref('')
const insertSaving = ref(false)

// 미출고 → 오늘 날짜로 확정(고정). 기존 시각은 서버가 보존하므로 재기록 안 됨.
function setInsert(pr: ProductionRequestListItem) {
  insertMenuFor.value = null
  toggleFlag(pr, 'insert_shipped', true)
}
function toggleInsertMenu(pr: ProductionRequestListItem) {
  if (insertMenuFor.value === pr.id) { insertMenuFor.value = null; return }
  insertEditDate.value = (pr.insert_shipped_at ? String(pr.insert_shipped_at).split('T')[0] : '') || todayStr()
  insertMenuFor.value = pr.id
}
function todayStr(): string {
  const d = new Date()
  const p = (x: number) => String(x).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}
async function saveInsertDate(pr: ProductionRequestListItem) {
  if (!insertEditDate.value) { showToast('출고일을 선택하세요', 'warning'); return }
  insertSaving.value = true
  try {
    const updated = await productionRequestApi.updateFlags(pr.id, {
      insert_shipped: true, insert_shipped_at: insertEditDate.value,
    })
    ;(pr as any).insert_shipped = true
    ;(pr as any).insert_shipped_at = (updated as any).insert_shipped_at
    insertMenuFor.value = null
    showToast('인서트 출고일이 수정되었습니다', 'success')
  } catch {
    showToast('출고일 수정에 실패했습니다', 'error')
  } finally {
    insertSaving.value = false
  }
}
async function cancelInsert(pr: ProductionRequestListItem) {
  if (!confirm(`${pr.request_number}\n인서트 출고를 취소(해제)하시겠습니까?`)) return
  insertMenuFor.value = null
  await toggleFlag(pr, 'insert_shipped', false)
}
// 인서트 없음(N/A)으로 표시 — 출고 상태는 해제됨
async function markNA(pr: ProductionRequestListItem) {
  insertMenuFor.value = null
  const prev = { na: (pr as any).insert_not_applicable, sh: pr.insert_shipped, at: pr.insert_shipped_at }
  ;(pr as any).insert_not_applicable = true
  ;(pr as any).insert_shipped = false
  ;(pr as any).insert_shipped_at = null
  try {
    const updated = await productionRequestApi.updateFlags(pr.id, { insert_not_applicable: true })
    ;(pr as any).insert_not_applicable = (updated as any).insert_not_applicable
    ;(pr as any).insert_shipped = (updated as any).insert_shipped
    ;(pr as any).insert_shipped_at = (updated as any).insert_shipped_at
  } catch {
    ;(pr as any).insert_not_applicable = prev.na
    ;(pr as any).insert_shipped = prev.sh
    ;(pr as any).insert_shipped_at = prev.at
    showToast('변경에 실패했습니다', 'error')
  }
}
// 인서트 있음으로 되돌리기(N/A 해제 → 미출고)
async function unmarkNA(pr: ProductionRequestListItem) {
  insertMenuFor.value = null
  const prev = (pr as any).insert_not_applicable
  ;(pr as any).insert_not_applicable = false
  try {
    await productionRequestApi.updateFlags(pr.id, { insert_not_applicable: false })
  } catch {
    ;(pr as any).insert_not_applicable = prev
    showToast('변경에 실패했습니다', 'error')
  }
}
function closeInsertMenu() { insertMenuFor.value = null }

// MM/DD 표기 (완료일 칩)
function fmtMd(d?: string | null): string {
  if (!d) return ''
  const p = (d.split('T')[0] ?? d).split('-')
  return p.length === 3 ? `${p[1]}/${p[2]}` : ''
}
// 출고시각: 월/일 시:분 (없으면 빈문자). 발송 대기 목록에서 언제 출고됐는지 확인용
function fmtMdHm(d?: string | null): string {
  if (!d) return ''
  const dt = new Date(d)
  if (isNaN(dt.getTime())) return fmtMd(d)
  const mm = dt.getMonth() + 1, dd = dt.getDate()
  const h = String(dt.getHours()).padStart(2, '0'), mi = String(dt.getMinutes()).padStart(2, '0')
  return `${mm}/${dd} ${h}:${mi}`
}

function partLabel(item: { product_part?: { part_number_display?: string; part_number?: string; part_name?: string }; custom_product_code?: string | null; custom_product_name?: string | null }): string {
  const p = item.product_part
  return p?.part_number_display || p?.part_number || p?.part_name || item.custom_product_code || item.custom_product_name || '-'
}

// 수량 표시: 무조건 자연수(반올림)
function formatQty(qty: number | undefined | null): string {
  if (qty == null) return '0'
  const n = Number(qty)
  if (Number.isNaN(n)) return '0'
  return String(Math.round(n))
}

function formatDate(d?: string) {
  if (!d) return '-'
  const datePart = d.split('T')[0] ?? d
  return datePart.replace(/-/g, '.')
}
function isOverdue(d?: string) {
  if (!d) return false
  return new Date(d) < new Date()
}

function loadAll() {
  loadData()
  loadTabCounts()
  loadCustomers()
}

onMounted(() => {
  loadAll()
  document.addEventListener('click', onCustomerClickOutside)
  document.addEventListener('click', closeInsertMenu)  // 셀 밖 클릭 시 인서트 메뉴 닫기(@click.stop로 셀 내부는 제외)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onCustomerClickOutside)
  document.removeEventListener('click', closeInsertMenu)
})
defineExpose({ loadAll })
</script>
