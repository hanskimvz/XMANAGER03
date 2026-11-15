<template>
  <div class="p-4 sm:p-6">
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
      <h2 class="text-xl font-bold text-gray-900">{{ fixedType ? fixedType + ' 관리' : 'PI / CI 관리' }}</h2>
    </div>

    <!-- 필터 -->
    <div class="bg-white rounded-lg shadow-sm border p-4 mb-4">
      <div class="flex flex-wrap gap-3 mb-3 items-center">
        <select v-if="!fixedType" v-model="filters.document_type" @change="loadData" class="border rounded-md px-3 py-2 text-sm">
          <option :value="undefined">전체 유형</option>
          <option value="PI">PI</option>
          <option value="CI">CI</option>
        </select>
        <div class="relative">
          <input v-model="customerFilterSearch"
            @focus="showCustomerFilter = true; highlightedIndex = 0" @input="showCustomerFilter = true; highlightedIndex = 0"
            @blur="hideCustomerFilterDelayed"
            @keydown.down.prevent="moveHighlight(1)"
            @keydown.up.prevent="moveHighlight(-1)"
            @keydown.enter.prevent="handleEnter"
            @keydown.escape="showCustomerFilter = false"
            class="border rounded-md px-3 py-2 text-sm w-48"
            :placeholder="filters.customer_id ? customers.find(c => c.id === filters.customer_id)?.partner_name || '고객사' : '고객사 검색...'"
          />
          <div v-if="showCustomerFilter && filteredCustomerOptions.length > 0"
            class="absolute z-10 w-64 mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
            <div @mousedown.prevent="filters.customer_id = undefined; customerFilterSearch = ''; showCustomerFilter = false; currentPage = 1; loadData()"
              class="px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 text-gray-400">전체 고객사</div>
            <div v-for="(c, idx) in filteredCustomerOptions" :key="c.id"
              @mousedown.prevent="filters.customer_id = c.id; customerFilterSearch = c.partner_name; showCustomerFilter = false; currentPage = 1; loadData()"
              @mouseenter="highlightedIndex = idx"
              class="px-3 py-2 text-sm cursor-pointer"
              :class="highlightedIndex === idx ? 'bg-blue-100' : 'hover:bg-blue-50'">
              {{ c.partner_name }}
            </div>
          </div>
        </div>
        <select v-model="filters.status" @change="loadData" class="border rounded-md px-3 py-2 text-sm">
          <option :value="undefined">전체 상태</option>
          <option value="DRAFT">작성중</option>
          <option value="SENT">발송완료</option>
          <option value="CONFIRMED">확정</option>
          <option value="CANCELLED">취소</option>
        </select>
        <input
          v-model="filters.keyword"
          @input="debouncedLoad"
          placeholder="문서번호 / PO번호 검색..."
          class="border rounded-md px-3 py-2 text-sm flex-1 min-w-[200px]"
        />
        <label class="inline-flex items-center text-xs text-gray-500 cursor-pointer select-none">
          <input type="checkbox" v-model="showAllVersions" @change="currentPage = 1; loadData()" class="w-3.5 h-3.5 mr-1.5 rounded" />
          이전 버전 포함
        </label>
        <button @click="resetFilters" type="button"
          class="px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 whitespace-nowrap">
          🔄 초기화
        </button>
      </div>
      <!-- 입금 상태 필터 (PI 탭에서만) -->
      <div v-if="fixedType === 'PI' || !fixedType" class="flex flex-wrap gap-2 items-center">
        <span class="text-xs text-gray-500 mr-1">입금:</span>
        <button
          v-for="opt in paymentFilterOptions"
          :key="opt.value"
          @click="paymentFilter = opt.value; currentPage = 1; loadData()"
          :class="paymentFilter === opt.value
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'"
          class="px-3 py-1 text-xs font-medium rounded-full border transition-colors"
        >
          {{ opt.label }}
          <span v-if="paymentCounts[opt.value] !== undefined" class="ml-1 opacity-75">({{ paymentCounts[opt.value] }})</span>
        </button>
        <!-- 배송 후 미수 예외(수금현황 통합) -->
        <button
          @click="paymentFilter = 'DELIVERED_UNPAID'; currentPage = 1; loadData()"
          :class="paymentFilter === 'DELIVERED_UNPAID' ? 'bg-amber-600 text-white border-amber-600' : 'bg-amber-50 text-amber-700 border-amber-300 hover:bg-amber-100'"
          class="px-3 py-1 text-xs font-medium rounded-full border transition-colors whitespace-nowrap"
        >
          ⚠ 배송후 미수 <span class="ml-1 opacity-75">({{ deliveredUnpaidCount }})</span>
        </button>
        <span class="ml-auto text-xs text-gray-500">미수금 합계 <strong class="text-red-600">$ {{ formatNumber(unpaidTotal, 'USD') }}</strong></span>
      </div>
    </div>

    <!-- 다중 선택 액션 바 (PI) -->
    <div v-if="fixedType === 'PI' && selectedPiIds.size > 0" class="mb-3 flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
      <span class="text-sm text-blue-700 font-medium">PI {{ selectedPiIds.size }}건 선택</span>
      <!-- PI→CI 합배송은 제거(생산→CI 흐름으로 이동). PI 합치기만 유지. -->
      <button @click="mergeSelected"
        class="px-3 py-1 text-xs font-medium bg-purple-600 text-white rounded hover:bg-purple-700">
        선택 PI 합치기
      </button>
      <button @click="selectedPiIds.clear()" class="text-xs text-gray-500 hover:text-gray-700">선택 해제</button>
    </div>

    <!-- 다중 선택 액션 바 (CI) -->
    <div v-if="fixedType === 'CI' && selectedPiIds.size > 0" class="mb-3 flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2">
      <span class="text-sm text-amber-700 font-medium">CI {{ selectedPiIds.size }}건 선택</span>
      <button @click="mergeSelected"
        class="px-3 py-1 text-xs font-medium bg-amber-600 text-white rounded hover:bg-amber-700">
        선택 CI 합치기
      </button>
      <button @click="selectedPiIds.clear()" class="text-xs text-gray-500 hover:text-gray-700">선택 해제</button>
    </div>

    <!-- 목록 -->
    <div class="bg-white rounded-lg shadow-sm border overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400">로딩 중...</div>
      <div v-else-if="documents.length === 0" class="p-8 text-center text-gray-400">
        <p>PI/CI 문서가 없습니다.</p>
        <p class="text-sm mt-1">견적서 탭에서 Q→PI 전환으로 생성할 수 있습니다.</p>
      </div>
      <div v-else>
      <!-- 모바일 카드 목록 (lg 미만 전용) -->
      <div class="lg:hidden divide-y divide-gray-100">
        <div v-for="doc in filteredDocuments" :key="'m' + doc.id" class="p-3"
          :class="[paymentRowClass(doc), doc.is_latest === false ? 'opacity-60' : '']">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-1.5 min-w-0 cursor-pointer" @click="openDetail(doc)">
              <span :class="doc.document_type === 'PI' ? 'bg-purple-100 text-purple-700' : 'bg-amber-100 text-amber-700'" class="px-1.5 py-0.5 text-[10px] font-medium rounded">{{ doc.document_type }}</span>
              <span class="text-sm font-medium text-blue-600 truncate">{{ doc.document_number }}</span>
              <span v-if="doc.is_latest === false" class="px-1 py-0.5 text-[9px] bg-gray-200 text-gray-500 rounded shrink-0">이전</span>
              <span v-if="doc.is_quote_only" class="px-1 py-0.5 text-[9px] bg-orange-100 text-orange-700 rounded shrink-0">견적대용</span>
            </div>
            <span :class="statusClass(doc.status)" class="px-2 py-0.5 text-[11px] font-medium rounded-full whitespace-nowrap">{{ statusLabel(doc.status) }}</span>
          </div>
          <div class="mt-1 text-sm text-gray-900 truncate cursor-pointer" @click="openDetail(doc)">{{ doc.customer?.partner_name || '-' }}</div>
          <div class="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-gray-500">
            <span v-if="doc.representative_product" class="font-mono truncate max-w-[55%]">{{ doc.representative_product }}</span>
            <span>{{ formatDate(doc.document_date) }}</span>
            <button @click.stop="openPoModal(doc)" class="hover:text-blue-600 hover:underline decoration-dotted">
              PO {{ doc.customer_po_number || '— 입력' }}
            </button>
            <span class="font-medium text-gray-700">{{ doc.currency }} {{ formatNumber(doc.total_amount, doc.currency) }}</span>
          </div>
          <div class="mt-1.5 flex items-center gap-3">
            <button v-if="fixedType !== 'CI' && doc.document_type === 'PI'" @click.stop="openPaymentModal(doc)" :class="paymentStatusClass(doc.payment_status)" class="px-2 py-0.5 text-[11px] font-medium rounded-full">{{ paymentStatusLabel(doc.payment_status) }}</button>
            <ProductionProgressMini v-if="doc.document_type === 'PI'" :progress="doc.production_progress" />
          </div>
        </div>
      </div>
      <!-- 데스크톱 테이블 (lg 이상 전용 — 기존 UI 보존) -->
      <table class="min-w-full divide-y divide-gray-200 hidden lg:table">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-3 py-3 w-8">
              <input type="checkbox" @change="toggleSelectAll" :checked="isAllPiSelected" class="w-4 h-4 rounded" />
            </th>
            <th @click="toggleSort('document_type')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">유형{{ sortIndicator('document_type') }}</th>
            <th @click="toggleSort('document_number')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">문서번호{{ sortIndicator('document_number') }}</th>
            <th @click="toggleSort('document_date')" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">날짜{{ sortIndicator('document_date') }}</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">고객사</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">제품</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">PO No.</th>
            <th @click="toggleSort('total_amount')" class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">금액{{ sortIndicator('total_amount') }}</th>
            <th v-if="fixedType !== 'CI' && fixedType !== 'INVOICE'" class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">입금</th>
            <th v-if="fixedType === 'PI'" class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">진행</th>
            <th @click="toggleSort('status')" class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-800 select-none">상태{{ sortIndicator('status') }}</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">액션</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          <tr v-for="doc in filteredDocuments" :key="doc.id"
            :class="[paymentRowClass(doc), selectedPiIds.has(doc.id) ? 'ring-2 ring-inset ring-blue-300' : '', doc.is_latest === false ? 'opacity-50' : '']"
            class="hover:opacity-90 transition-opacity">
            <td class="px-3 py-3">
              <input type="checkbox" :checked="selectedPiIds.has(doc.id)"
                @change="togglePiSelect(doc.id)" class="w-4 h-4 rounded" />
            </td>
            <td class="px-4 py-3">
              <span :class="doc.document_type === 'PI' ? 'bg-purple-100 text-purple-700' : 'bg-amber-100 text-amber-700'"
                class="px-2 py-0.5 text-xs font-medium rounded">
                {{ doc.document_type }}
              </span>
            </td>
            <td class="px-4 py-3 text-sm font-medium text-blue-600 cursor-pointer" @click="openDetail(doc)">
              {{ doc.document_number }}
              <span v-if="doc.version && doc.version > 1" class="ml-1 px-1 py-0.5 text-[9px] bg-amber-100 text-amber-700 rounded">v{{ doc.version }}</span>
              <span v-if="doc.is_latest === false" class="ml-1 px-1 py-0.5 text-[9px] bg-gray-200 text-gray-500 rounded">이전</span>
              <span v-if="doc.is_quote_only" class="ml-1 px-1 py-0.5 text-[9px] bg-orange-100 text-orange-700 rounded">견적대용</span>
            </td>
            <td class="px-4 py-3 text-sm text-gray-600">{{ formatDate(doc.document_date) }}</td>
            <td class="px-4 py-3 text-sm text-gray-900 max-w-[160px] truncate" :title="doc.customer?.partner_name">{{ doc.customer?.partner_name || '-' }}</td>
            <td class="px-4 py-3 text-xs text-gray-600">
              <div v-if="doc.representative_product" class="max-w-[180px]">
                <span class="font-mono truncate block" :title="doc.representative_product">{{ doc.representative_product }}</span>
                <span v-if="(doc.item_count || 0) > 1" class="text-gray-400 text-[10px]">외 {{ (doc.item_count || 1) - 1 }}건</span>
              </div>
              <span v-else class="text-gray-400">-</span>
            </td>
            <!-- PO 번호: 고객사가 잘못 준 경우 발행 후에도 정정 가능(클릭) -->
            <td class="px-4 py-3 text-sm">
              <button @click.stop="openPoModal(doc)"
                :title="`PO 번호 수정${doc.customer_po_number ? ' — 현재: ' + doc.customer_po_number : ''}`"
                class="text-left text-gray-600 hover:text-blue-600 hover:underline decoration-dotted">
                {{ doc.customer_po_number || '— 입력' }}
              </button>
            </td>
            <td class="px-4 py-3 text-sm text-right font-medium whitespace-nowrap">
              {{ doc.currency }} {{ formatNumber(doc.total_amount, doc.currency) }}
            </td>
            <!-- 입금 (PI) -->
            <td v-if="fixedType !== 'CI' && fixedType !== 'INVOICE'" class="px-4 py-3 text-center">
              <button
                v-if="doc.document_type === 'PI'"
                @click="openPaymentModal(doc)"
                :class="paymentStatusClass(doc.payment_status)"
                class="px-2 py-0.5 text-xs font-medium rounded-full cursor-pointer hover:opacity-80 whitespace-nowrap"
              >
                {{ paymentStatusLabel(doc.payment_status) }}
              </button>
              <span v-else class="text-xs text-gray-400">-</span>
            </td>
            <!-- 진행 (PI): 생산·출고·배송 3칸 스텝퍼 (집계 A: 병목 기준) -->
            <td v-if="fixedType === 'PI'" class="px-4 py-3 text-center">
              <template v-if="doc.document_type === 'PI'">
                <ProductionProgressMini :progress="doc.production_progress" />
                <div v-if="isDeliveredUnpaid(doc)" class="text-[10px] text-amber-600 mt-0.5">⚠ 수령 후 미입금</div>
              </template>
              <span v-else class="text-xs text-gray-400">-</span>
            </td>
            <td class="px-4 py-3 text-center">
              <span :class="statusClass(doc.status)" class="px-2 py-1 text-xs font-medium rounded-full whitespace-nowrap">
                {{ statusLabel(doc.status) }}
              </span>
            </td>
            <td class="px-4 py-3">
              <RowActionMenu :actions="rowActions(doc)" />
            </td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>

    <!-- 페이지네이션 -->
    <div v-if="totalPages > 1" class="flex items-center justify-between px-4 py-3 bg-white border-t">
      <span class="text-xs text-gray-500">총 {{ totalCount }}건 중 {{ (currentPage - 1) * PAGE_SIZE + 1 }}~{{ Math.min(currentPage * PAGE_SIZE, totalCount) }}건</span>
      <div class="flex items-center gap-1">
        <button @click="goToPage(1)" :disabled="currentPage === 1"
          class="px-2 py-1 text-xs border rounded hover:bg-gray-50 disabled:opacity-30">«</button>
        <button @click="goToPage(currentPage - 1)" :disabled="currentPage === 1"
          class="px-2 py-1 text-xs border rounded hover:bg-gray-50 disabled:opacity-30">‹</button>
        <template v-for="p in pageNumbers" :key="p">
          <button @click="goToPage(p)"
            :class="p === currentPage ? 'bg-blue-600 text-white border-blue-600' : 'hover:bg-gray-50'"
            class="px-3 py-1 text-xs border rounded">{{ p }}</button>
        </template>
        <button @click="goToPage(currentPage + 1)" :disabled="currentPage === totalPages"
          class="px-2 py-1 text-xs border rounded hover:bg-gray-50 disabled:opacity-30">›</button>
        <button @click="goToPage(totalPages)" :disabled="currentPage === totalPages"
          class="px-2 py-1 text-xs border rounded hover:bg-gray-50 disabled:opacity-30">»</button>
      </div>
    </div>

    <!-- CI 전환 모달 (문서 날짜 = 출고/매출 인식일) -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showCiConvertModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div class="bg-white rounded-lg shadow-xl w-full max-w-sm mx-4 p-6">
            <h3 class="text-lg font-bold mb-1">{{ ciConvertLabel }} 전환</h3>
            <p class="text-sm text-gray-500 mb-4">
              <template v-if="ciConvertMode === 'single'">{{ ciConvertDoc?.document_number }} → {{ ciConvertLabel }}</template>
              <template v-else>PI {{ ciConvertIds.length }}건 → {{ ciConvertTarget === 'INVOICE' ? 'Invoice' : '합배송 CI' }} 1건</template>
            </p>
            <div class="mb-2">
              <label class="text-sm text-gray-700 mb-1 block">{{ ciConvertLabel }} 문서 날짜{{ ciConvertTarget === 'CI' ? ' (출고일)' : '' }}</label>
              <input v-model="ciConvertDate" type="date" class="w-full border rounded-md px-3 py-2 text-sm" />
            </div>
            <p class="text-[11px] text-gray-400 mb-4">
              {{ ciConvertTarget === 'CI' ? '이 날짜에 출고·매출로 집계됩니다. 실제 출고일에 맞게 조정하세요.' : 'PI와 동일한 양식으로, 제목만 INVOICE로 발행됩니다.' }}
            </p>
            <div class="flex justify-end gap-2">
              <button @click="showCiConvertModal = false" class="px-4 py-2 text-sm text-gray-600">취소</button>
              <button @click="executeCiConvert" :disabled="!ciConvertDate || ciConverting"
                class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {{ ciConverting ? '전환 중...' : ciConvertLabel + ' 전환' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 입금 상태 변경 모달 -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showPaymentModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" >
          <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <h3 class="text-lg font-bold mb-1">입금 상태 변경</h3>
            <p class="text-sm text-gray-500 mb-4">{{ paymentDoc?.document_number }} — {{ paymentDoc?.currency }} {{ formatNumber(paymentDoc?.total_amount || 0, paymentDoc?.currency) }}</p>
            <div class="space-y-3">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">입금 상태</label>
                <select v-model="paymentForm.payment_status" class="w-full border rounded-md px-3 py-2 text-sm">
                  <option value="UNPAID">미입금</option>
                  <option value="PARTIAL">부분입금</option>
                  <option value="PAID">완납</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">입금 금액</label>
                <input v-model.number="paymentForm.paid_amount" type="number" min="0" class="w-full border rounded-md px-3 py-2 text-sm" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">입금 확인일</label>
                <input v-model="paymentForm.paid_date" type="date" class="w-full border rounded-md px-3 py-2 text-sm" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">메모</label>
                <input v-model="paymentForm.payment_remarks" class="w-full border rounded-md px-3 py-2 text-sm" placeholder="입금 관련 메모" />
              </div>
            </div>
            <div class="flex justify-end gap-2 mt-6">
              <button @click="showPaymentModal = false" class="px-4 py-2 text-sm text-gray-600">취소</button>
              <button @click="savePayment" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">저장</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 고객 PO 번호 정정 모달 (발행 후에도 수정 가능 — 버전 재발행 없음) -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showPoModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <h3 class="text-lg font-bold mb-1">PO 번호 수정</h3>
            <p class="text-sm text-gray-500 mb-4">
              {{ poDoc?.document_number }} — {{ poDoc?.customer?.partner_name || '-' }}
            </p>
            <div class="space-y-3">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">고객 PO 번호</label>
                <input v-model="poForm.customer_po_number" ref="poInputRef"
                  class="w-full border rounded-md px-3 py-2 text-sm" placeholder="예: PO-12345"
                  @keyup.enter="savePoNumber" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">고객 PO 날짜</label>
                <input v-model="poForm.customer_po_date" type="date" class="w-full border rounded-md px-3 py-2 text-sm" />
              </div>
              <label class="flex items-start gap-2 text-sm text-gray-700">
                <input v-model="poForm.cascade" type="checkbox" class="mt-0.5 w-4 h-4 rounded" />
                <span>
                  같은 PO 번호를 쓰는 후속 문서(CI 등)도 함께 수정
                  <span class="block text-[11px] text-gray-400">끄면 이 문서와 그 이전 버전만 수정됩니다. 따로 입력된 PO 는 어느 쪽이든 보존됩니다.</span>
                </span>
              </label>
            </div>
            <p class="mt-4 text-[11px] text-gray-400">
              문서번호·상태·금액·품목은 바뀌지 않습니다. 새 버전도 생성되지 않습니다.
            </p>
            <div class="flex justify-end gap-2 mt-4">
              <button @click="showPoModal = false" class="px-4 py-2 text-sm text-gray-600">취소</button>
              <button @click="savePoNumber" :disabled="poSaving"
                class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {{ poSaving ? '저장 중…' : '저장' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 상세 모달 -->
    <SalesDocumentFormModal
      v-if="showFormModal"
      :document="editingDoc"
      :document-type="editingDoc?.document_type || 'PI'"
      @close="showFormModal = false"
      @saved="handleSaved"
      @navigate="(payload) => $emit('navigate-doc', payload)"
    />

    <!-- PDF 미리보기 모달 (PI는 영문만) -->
    <PdfPreviewModal
      v-if="pdfPreview"
      :doc-id="pdfPreview.id"
      :doc-number="pdfPreview.number"
      :doc-type="pdfPreview.type || 'PI'"
      lang="en"
      :version="pdfPreview.version"
      @close="pdfPreview = null"
    />

    <!-- 운송장 업로드/미리보기 모달 (CI 전용) -->
    <ShippingInvoiceModal
      v-if="shippingModal"
      :doc-id="shippingModal.id"
      :doc-number="shippingModal.number"
      :initial-files="shippingModal.files"
      @close="shippingModal = null"
      @updated="onShippingFilesUpdated"
    />

    <!-- 주문 파일함 (Nextcloud 01~06 폴더 브라우저) -->
    <OrderFilesModal
      v-if="orderFilesDoc"
      :doc-id="orderFilesDoc.id"
      :doc-number="orderFilesDoc.number"
      :customer-name="orderFilesDoc.customer"
      @close="orderFilesDoc = null"
    />

    <!-- 생산요청 인라인 편집 모달 (PI에서 초안 생성 직후 도면/특이사항 추가) -->
    <ProductionRequestFormModal
      v-if="prEditingId !== null"
      :request-id="prEditingId"
      :customers="prCustomers"
      @close="closePrEditModal"
      @saved="onPrSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { salesDocumentApi, type SalesDocument, type CollectionDoc } from '@/api/salesDocument'
import { formatAmount } from '@/api/price'
import apiClient from '@/api/client'
import { useToast } from '@/composables/useToast'
import SalesDocumentFormModal from './SalesDocumentFormModal.vue'
import PdfPreviewModal from './PdfPreviewModal.vue'
import ShippingInvoiceModal from './ShippingInvoiceModal.vue'
import OrderFilesModal from './OrderFilesModal.vue'
import ProductionRequestFormModal from '@/views/production/components/ProductionRequestFormModal.vue'
import { partnerApi } from '@/api/partner'
import RowActionMenu, { type RowAction } from '@/components/common/RowActionMenu.vue'
import ProductionProgressMini from './ProductionProgressMini.vue'
import { useAuth, hasPermStrict } from '@/stores/auth'

const props = defineProps<{
  fixedType?: 'PI' | 'CI' | 'INVOICE'
}>()

const emit = defineEmits<{
  (e: 'data-changed'): void
  (e: 'navigate-doc', payload: { docId: number; docType: string }): void
}>()
const router = useRouter()
const route = useRoute()
const { showToast } = useToast()
const { isAdmin } = useAuth()  // 삭제: 관리자 전체 / CI 는 'CI 삭제'(sales:ci_delete) 권한자도
// 서버 판정과 동일하게 전역 모드와 무관한 실제 보유 권한으로 판단(hasPermStrict)
const canDeleteDoc = (doc: SalesDocument) =>
  isAdmin.value || (doc.document_type === 'CI' && hasPermStrict('sales:ci_delete'))

const loading = ref(false)
const documents = ref<SalesDocument[]>([])
const showFormModal = ref(false)
const editingDoc = ref<SalesDocument | null>(null)
const pdfPreview = ref<{ id: number; number: string; version?: number; type?: 'QUOTATION' | 'PI' | 'CI' | 'INVOICE' } | null>(null)
const shippingModal = ref<{ id: number; number: string; files: any[] } | null>(null)
// 주문 파일함(Nextcloud) 모달
const orderFilesDoc = ref<{ id: number; number: string; customer?: string | null } | null>(null)
function openOrderFiles(doc: SalesDocument) {
  orderFilesDoc.value = { id: doc.id, number: doc.document_number, customer: doc.customer?.partner_name || null }
}
const prEditingId = ref<number | null>(null)
const prCustomers = ref<{ id: number; name: string }[]>([])
const filters = ref<{ document_type?: string; customer_id?: number; status?: string; keyword?: string }>({})
const showAllVersions = ref(false)

// 고객사 필터
const customers = ref<{ id: number; partner_name: string }[]>([])
const customerFilterSearch = ref('')
const showCustomerFilter = ref(false)
const highlightedIndex = ref(0)

function moveHighlight(delta: number) {
  const list = filteredCustomerOptions.value
  if (list.length === 0) return
  highlightedIndex.value = (highlightedIndex.value + delta + list.length) % list.length
}

function handleEnter() {
  const list = filteredCustomerOptions.value
  if (list.length === 1) {
    filters.value.customer_id = list[0]!.id; customerFilterSearch.value = list[0]!.partner_name; showCustomerFilter.value = false; currentPage.value = 1; loadData()
    return
  }
  if (list.length > 0 && highlightedIndex.value >= 0) {
    const c = list[highlightedIndex.value]!
    filters.value.customer_id = c.id; customerFilterSearch.value = c.partner_name; showCustomerFilter.value = false; currentPage.value = 1; loadData()
  }
}

function hideCustomerFilterDelayed() { setTimeout(() => { showCustomerFilter.value = false }, 200) }
const filteredCustomerOptions = computed(() => {
  if (!customerFilterSearch.value) return customers.value
  const q = customerFilterSearch.value.toLowerCase()
  return customers.value.filter(c => c.partner_name.toLowerCase().includes(q))
})

async function loadCustomers() {
  try {
    const res = await apiClient.get('/partners', { params: { is_customer: true, limit: 500 } })
    customers.value = (res.data.items || res.data).map((c: any) => ({ id: c.id, partner_name: c.partner_name }))
  } catch { /* ignore */ }
}
const PAGE_SIZE = 20
const currentPage = ref(1)
const totalCount = ref(0)
const sortKey = ref('document_date')
const sortDesc = ref(true)

function toggleSort(key: string) {
  if (sortKey.value === key) sortDesc.value = !sortDesc.value
  else { sortKey.value = key; sortDesc.value = true }
  currentPage.value = 1
  loadData()
}
function sortIndicator(key: string) {
  if (sortKey.value !== key) return ''
  return sortDesc.value ? ' ↓' : ' ↑'
}
const totalPages = computed(() => Math.ceil(totalCount.value / PAGE_SIZE))
const pageNumbers = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const pages: number[] = []
  let start = Math.max(1, current - 2)
  let end = Math.min(total, start + 4)
  start = Math.max(1, end - 4)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

// 다중 선택 (PI → CI 합배송)
const selectedPiIds = ref(new Set<number>())
const selectableDocs = computed(() => filteredDocuments.value)
const isAllPiSelected = computed(() => selectableDocs.value.length > 0 && selectableDocs.value.every(d => selectedPiIds.value.has(d.id)))
function togglePiSelect(id: number) {
  if (selectedPiIds.value.has(id)) selectedPiIds.value.delete(id)
  else selectedPiIds.value.add(id)
}
function toggleSelectAll() {
  if (isAllPiSelected.value) selectedPiIds.value.clear()
  else selectableDocs.value.forEach(d => selectedPiIds.value.add(d.id))
}

async function mergeSelected() {
  const ids = Array.from(selectedPiIds.value)
  if (ids.length < 2) { showToast('2건 이상 선택하세요', 'error'); return }
  const typeName = props.fixedType || 'PI/CI'
  if (!confirm(`${typeName} ${ids.length}건을 합쳐서 새 ${typeName} 1건을 생성합니다.\n기존 문서는 이전 버전으로 보관됩니다.\n\n계속하시겠습니까?`)) return
  try {
    const res = await salesDocumentApi.merge(ids)
    showToast(`${typeName} ${ids.length}건이 합쳐졌습니다 (${res.data.document_number})`, 'success')
    selectedPiIds.value.clear()
    loadData()
    emit('data-changed')
  } catch (err: any) {
    showToast(err.response?.data?.detail || '합치기에 실패했습니다', 'error')
  }
}
// PI → CI / Invoice 전환 모달 (문서 날짜 = 출고/매출 인식일 지정)
const showCiConvertModal = ref(false)
const ciConvertMode = ref<'single' | 'multi'>('single')
const ciConvertTarget = ref<'CI' | 'INVOICE'>('CI')  // 전환 대상 유형
const ciConvertDoc = ref<SalesDocument | null>(null)
const ciConvertIds = ref<number[]>([])
const ciConvertDate = ref('')
const ciConverting = ref(false)

const ciConvertLabel = computed(() => ciConvertTarget.value === 'INVOICE' ? 'Invoice' : 'CI')

function openCiConvert(mode: 'single' | 'multi', doc?: SalesDocument, target: 'CI' | 'INVOICE' = 'CI') {
  ciConvertMode.value = mode
  ciConvertTarget.value = target
  ciConvertDoc.value = doc || null
  ciConvertIds.value = mode === 'single' && doc ? [doc.id] : Array.from(selectedPiIds.value)
  if (ciConvertIds.value.length === 0) { showToast('전환할 PI를 선택하세요', 'error'); return }
  ciConvertDate.value = new Date().toISOString().split('T')[0] as string
  showCiConvertModal.value = true
}

async function executeCiConvert() {
  if (!ciConvertDate.value || ciConverting.value) return
  ciConverting.value = true
  const target = ciConvertTarget.value
  const label = target === 'INVOICE' ? 'Invoice' : 'CI'
  try {
    if (ciConvertMode.value === 'single' && ciConvertDoc.value) {
      await salesDocumentApi.convert(ciConvertDoc.value.id, { document_date: ciConvertDate.value, target_type: target })
      showToast(`${label}(으)로 전환되었습니다`, 'success')
    } else {
      await salesDocumentApi.convertMultiple(ciConvertIds.value, { document_date: ciConvertDate.value, target_type: target })
      showToast(`PI ${ciConvertIds.value.length}건이 ${target === 'INVOICE' ? 'Invoice로' : '합배송 CI로'} 전환되었습니다`, 'success')
      selectedPiIds.value.clear()
    }
    showCiConvertModal.value = false
    loadData(); emit('data-changed')
  } catch {
    showToast(`${label} 전환에 실패했습니다`, 'error')
  } finally {
    ciConverting.value = false
  }
}

// 입금 모달
const showPaymentModal = ref(false)
const paymentDoc = ref<SalesDocument | null>(null)
const paymentForm = ref({ payment_status: 'UNPAID', paid_amount: 0, paid_date: '', payment_remarks: '' })

// 입금 상태 필터
const paymentFilter = ref<string>('ALL')
const paymentFilterOptions = [
  { value: 'ALL', label: '전체' },
  { value: 'UNPAID', label: '미입금' },
  { value: 'PARTIAL', label: '부분입금' },
  { value: 'PAID', label: '완납' },
]

// 입금 상태별 카운트 (서버 전체 기준)
const paymentCounts = ref<Record<string, number>>({ ALL: 0, UNPAID: 0, PARTIAL: 0, PAID: 0 })

async function loadPaymentCounts() {
  if (props.fixedType !== 'PI') return
  try {
    const params: any = { document_type: 'PI' }
    if (filters.value.customer_id) params.customer_id = filters.value.customer_id
    const res = await apiClient.get('/sales-documents/payment-counts', { params })
    paymentCounts.value = res.data
  } catch { /* ignore */ }
}

// 수금현황 통합(v0.79): PI별 배송완료 여부 + '배송 후 미수' 예외
const collectionDocs = ref<CollectionDoc[]>([])
async function loadCollectionInfo() {
  if (props.fixedType !== 'PI') return
  try {
    const res = await salesDocumentApi.getCollectionDocuments()
    collectionDocs.value = res.data.items || []
  } catch { collectionDocs.value = [] }
}
const deliveredMap = computed<Record<number, boolean>>(() => {
  const m: Record<number, boolean> = {}
  for (const d of collectionDocs.value) m[d.id] = d.delivered
  return m
})
const deliveredUnpaidCount = computed(() =>
  collectionDocs.value.filter(d => d.delivered && d.payment_status !== 'PAID').length)
const unpaidTotal = computed(() =>
  collectionDocs.value.reduce((s, d) => s + Math.max(0, (d.total_amount || 0) - (d.paid_amount || 0)), 0))
function isDelivered(doc: SalesDocument): boolean { return !!deliveredMap.value[doc.id] }
function isDeliveredUnpaid(doc: SalesDocument): boolean {
  return doc.document_type === 'PI' && isDelivered(doc) && (doc.payment_status || 'UNPAID') !== 'PAID'
}

// 필터 + 정렬 (미입금 최상단 → 부분입금 → 완납)
const paymentOrder: Record<string, number> = { UNPAID: 0, PARTIAL: 1, PAID: 2 }
const filteredDocuments = computed(() => {
  // 입금 필터는 서버에서 처리(payment_status 파라미터) → 여기선 정렬만
  let list = [...documents.value]
  // '배송 후 미수' 필터는 배송여부(클라 데이터)로 걸러냄
  if (props.fixedType === 'PI' && paymentFilter.value === 'DELIVERED_UNPAID') {
    list = list.filter(isDeliveredUnpaid)
  }
  // 정렬: PI는 입금상태 → 날짜, CI는 뒤에
  list.sort((a, b) => {
    if (a.document_type === 'PI' && b.document_type === 'PI') {
      const sa = paymentOrder[a.payment_status || 'UNPAID'] ?? 99
      const sb = paymentOrder[b.payment_status || 'UNPAID'] ?? 99
      if (sa !== sb) return sa - sb
      return (b.document_date || '').localeCompare(a.document_date || '')
    }
    if (a.document_type === 'PI') return -1
    if (b.document_type === 'PI') return 1
    return (b.document_date || '').localeCompare(a.document_date || '')
  })
  return list
})

// 행 배경색 (입금 상태별 강조)
function paymentRowClass(doc: SalesDocument): string {
  if (doc.document_type !== 'PI') return 'bg-white hover:bg-gray-50'
  const s = doc.payment_status || 'UNPAID'
  if (s === 'UNPAID') return 'bg-red-50 hover:bg-red-100'
  if (s === 'PARTIAL') return 'bg-yellow-50 hover:bg-yellow-100'
  return 'bg-white hover:bg-gray-50'
}

async function loadData() {
  loading.value = true
  try {
    const params: any = {
      ...filters.value,
      skip: (currentPage.value - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
      order_by: sortKey.value,
      order_desc: sortDesc.value,
    }
    if (props.fixedType) {
      params.document_type = props.fixedType
    }
    if (showAllVersions.value) {
      params.include_old_versions = true
    }
    // 입금 필터: 서버에서 걸러 앞페이지부터 채우기(PI 탭 전용)
    if (props.fixedType === 'PI' && paymentFilter.value !== 'ALL') {
      if (paymentFilter.value === 'DELIVERED_UNPAID') {
        // 배송 여부는 서버 필터가 없어 전체(최대 500) 로드 후 클라에서 걸러냄
        params.limit = 500
        params.skip = 0
      } else {
        params.payment_status = paymentFilter.value
      }
    }
    const res = await salesDocumentApi.getList(params)
    // 서버가 이미 document_type(fixedType)로 필터하므로 클라 재필터 불필요 → 페이지 채움 정합성 유지
    documents.value = res.data.items
    totalCount.value = res.data.total || 0
    loadPaymentCounts()
    loadCollectionInfo()
  } catch {
    showToast('문서 목록을 불러오는데 실패했습니다', 'error')
  } finally {
    loading.value = false
  }
}

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadData()
}

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedLoad() { clearTimeout(debounceTimer); debounceTimer = setTimeout(() => { currentPage.value = 1; loadData() }, 300) }

function resetFilters() {
  filters.value = { document_type: undefined, customer_id: undefined, status: undefined, keyword: undefined }
  paymentFilter.value = 'ALL'
  customerFilterSearch.value = ''
  currentPage.value = 1
  loadData()
}

async function deleteDoc(doc: SalesDocument) {
  if (!confirm(`${doc.document_number}을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) return
  try {
    await salesDocumentApi.delete(doc.id, true)
    showToast('삭제되었습니다', 'success')
    loadData()
    emit('data-changed')
  } catch (err: any) {
    showToast(err.response?.data?.detail || '삭제에 실패했습니다', 'error')
  }
}

async function openDetail(doc: SalesDocument) {
  try {
    const res = await salesDocumentApi.getById(doc.id)
    editingDoc.value = res.data
    showFormModal.value = true
  } catch {
    showToast('문서 상세 정보를 불러오는데 실패했습니다', 'error')
  }
}

async function downloadExcel(doc: SalesDocument) {
  try {
    const res = await salesDocumentApi.exportExcel(doc.id)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `${doc.document_number}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
    showToast('엑셀 파일을 다운로드했습니다', 'success')
  } catch { showToast('다운로드에 실패했습니다', 'error') }
}

function openPdfPreview(doc: SalesDocument) {
  pdfPreview.value = {
    id: doc.id,
    number: doc.document_number,
    version: doc.version,
    type: doc.document_type as 'QUOTATION' | 'PI' | 'CI' | 'INVOICE',
  }
}

// PI/CI 행 액션 메뉴 구성
function rowActions(doc: SalesDocument): RowAction[] {
  const isPI = doc.document_type === 'PI'
  const isCI = doc.document_type === 'CI'
  const isInvoice = doc.document_type === 'INVOICE'
  const notCancelled = doc.status !== 'CANCELLED'
  const shippingCount = doc.shipping_invoice_files?.length || 0
  const shippingLabel = shippingCount > 0 ? `송장 (${shippingCount})` : '송장'
  return [
    { label: 'PDF', icon: '📄', show: isPI || isInvoice || isCI, onClick: () => openPdfPreview(doc) },
    { label: shippingLabel, icon: '📦', show: isCI, onClick: () => openShippingInvoice(doc) },
    { label: '엑셀', icon: '📊', onClick: () => downloadExcel(doc) },
    { label: '파일함', icon: '🗂', onClick: () => openOrderFiles(doc) },
    { label: '생산요청', icon: '🏭', show: isPI && notCancelled, onClick: () => createProductionRequestDraft(doc) },
    { label: 'CI 전환', icon: '🔄', show: isPI && notCancelled, onClick: () => openCiConvert('single', doc, 'CI') },
    { label: 'Invoice 전환', icon: '🧾', show: isPI && notCancelled, onClick: () => openCiConvert('single', doc, 'INVOICE') },
    { label: '발송', icon: '📤', show: doc.status === 'DRAFT', onClick: () => updateStatus(doc, 'SENT') },
    { divider: true },
    { label: '삭제', icon: '🗑', variant: 'danger', show: canDeleteDoc(doc), onClick: () => deleteDoc(doc) },
  ]
}

function openShippingInvoice(doc: SalesDocument) {
  shippingModal.value = {
    id: doc.id,
    number: doc.document_number,
    files: doc.shipping_invoice_files || [],
  }
}

function onShippingFilesUpdated(files: any[]) {
  if (!shippingModal.value) return
  const doc = documents.value.find(d => d.id === shippingModal.value!.id)
  if (doc) doc.shipping_invoice_files = files
  shippingModal.value.files = files
}

async function updateStatus(doc: SalesDocument, status: string) {
  try {
    await salesDocumentApi.updateStatus(doc.id, status)
    showToast('상태가 변경되었습니다', 'success')
    loadData(); emit('data-changed')
  } catch { showToast('상태 변경에 실패했습니다', 'error') }
}

async function createProductionRequestDraft(doc: SalesDocument) {
  // 잔여 수량 먼저 확인
  try {
    const remRes = await salesDocumentApi.getRemainingQuantities(doc.id)
    const items = remRes.data.items || []
    const hasRemaining = items.some(i => i.remaining_qty > 0)
    if (!hasRemaining) {
      showToast('잔여 수량이 없습니다. 모든 품목이 이미 생산요청되었습니다.', 'warning')
      return
    }
    // 기존 PR이 있는지 체크
    const relRes = await salesDocumentApi.getRelatedDocuments(doc.id)
    const existingCount = relRes.data.production_requests?.length || 0
    if (existingCount > 0) {
      if (!confirm(`이 PI에 이미 ${existingCount}개의 생산요청이 있습니다.\n잔여 수량으로 추가 생산요청을 생성하시겠습니까?`)) return
    } else {
      if (!confirm(`${doc.document_number}에서 생산요청 초안을 생성하시겠습니까?\n바로 도면/특이사항을 추가할 수 있는 편집창이 열립니다.`)) return
    }
  } catch { /* 잔여 수량 조회 실패 시 그냥 진행 */ }

  try {
    // 거래처 목록 미리 로드 (편집 모달용)
    if (prCustomers.value.length === 0) {
      try {
        const cRes = await partnerApi.getAll({ partner_type: 'CUSTOMER', limit: 1000 })
        prCustomers.value = cRes.data.items.map((p: any) => ({ id: p.id, name: p.partner_name }))
      } catch { /* 로드 실패 시에도 모달은 열어 둠 */ }
    }

    const res = await salesDocumentApi.createProductionRequestDraft(doc.id)
    const result = res.data
    let msg = result.message
    if (result.items_skipped && result.items_skipped.length > 0) {
      msg += `\n\n매칭 실패 품목: ${result.items_skipped.join(', ')}`
    }
    showToast(msg, 'success')
    // PI 탭을 떠나지 않고 인라인 편집 모달 열기 (도면 첨부 등)
    if (result.production_request_id != null) {
      prEditingId.value = result.production_request_id
    }
  } catch (err: any) {
    const detail = err?.response?.data?.detail || '생산요청 초안 생성에 실패했습니다'
    showToast(detail, 'error')
  }
}

function closePrEditModal() {
  prEditingId.value = null
}

function onPrSaved() {
  prEditingId.value = null
  showToast('생산요청이 저장되었습니다', 'success')
  loadData()
  emit('data-changed')
}

function openPaymentModal(doc: SalesDocument) {
  paymentDoc.value = doc
  paymentForm.value = {
    payment_status: doc.payment_status || 'UNPAID',
    paid_amount: doc.paid_amount || 0,
    paid_date: doc.paid_date || '',
    payment_remarks: doc.payment_remarks || '',
  }
  showPaymentModal.value = true
}

async function savePayment() {
  if (!paymentDoc.value) return
  try {
    const payload = {
      ...paymentForm.value,
      paid_date: paymentForm.value.paid_date || undefined,
      paid_amount: paymentForm.value.paid_amount || undefined,
    }
    await salesDocumentApi.updatePayment(paymentDoc.value.id, payload)
    showToast('입금 상태가 변경되었습니다', 'success')
    showPaymentModal.value = false
    loadData(); emit('data-changed')
  } catch { showToast('입금 상태 변경에 실패했습니다', 'error') }
}

// ─────────── 고객 PO 번호 정정 ───────────
// 고객사가 PO 번호를 잘못 준 경우, PI 발행 후에도 바로잡을 수 있어야 한다.
// 일반 수정(update)은 SENT/CONFIRMED 문서에 새 버전을 만들어 문서번호가
// 재발행되므로, 전용 엔드포인트(updatePoNumber)로 제자리 수정한다.
const showPoModal = ref(false)
const poDoc = ref<SalesDocument | null>(null)
const poSaving = ref(false)
const poInputRef = ref<HTMLInputElement | null>(null)
const poForm = ref({ customer_po_number: '', customer_po_date: '', cascade: true })

function openPoModal(doc: SalesDocument) {
  poDoc.value = doc
  poForm.value = {
    customer_po_number: doc.customer_po_number || '',
    customer_po_date: doc.customer_po_date ? String(doc.customer_po_date).slice(0, 10) : '',
    cascade: true,
  }
  showPoModal.value = true
  nextTick(() => poInputRef.value?.focus())
}

async function savePoNumber() {
  if (!poDoc.value || poSaving.value) return
  poSaving.value = true
  try {
    const res = await salesDocumentApi.updatePoNumber(poDoc.value.id, {
      customer_po_number: poForm.value.customer_po_number.trim() || null,
      customer_po_date: poForm.value.customer_po_date || null,
      cascade: poForm.value.cascade,
    })
    const n = res.data?.updated_count ?? 1
    showToast(n > 1 ? `PO 번호를 수정했습니다 (문서 ${n}건)` : 'PO 번호를 수정했습니다', 'success')
    showPoModal.value = false
    loadData(); emit('data-changed')
  } catch (err: any) {
    const msg = err?.response?.data?.detail
    showToast(typeof msg === 'string' ? msg : 'PO 번호 수정에 실패했습니다', 'error')
  } finally {
    poSaving.value = false
  }
}

function paymentStatusLabel(s?: string) {
  return { UNPAID: '미입금', PARTIAL: '부분입금', PAID: '완납' }[s || 'UNPAID'] || s
}
function paymentStatusClass(s?: string) {
  return { UNPAID: 'bg-red-100 text-red-700', PARTIAL: 'bg-yellow-100 text-yellow-700', PAID: 'bg-green-100 text-green-700' }[s || 'UNPAID'] || 'bg-gray-100'
}

function handleSaved() { showFormModal.value = false; loadData(); emit('data-changed') }
function formatDate(d: string) { return d ? d.replace(/-/g, '.') : '-' }
// 통화 인식형 금액 표기 (원/엔/위안 정수, 달러/유로 2자리, 천 단위 콤마)
function formatNumber(n: number | null | undefined, currency = 'KRW') {
  if (n == null || isNaN(Number(n))) return '0'
  return formatAmount(Number(n), currency)
}
function statusLabel(s: string) {
  return { DRAFT: '작성중', SENT: '발송완료', CONFIRMED: '확정', CANCELLED: '취소' }[s] || s
}
function statusClass(s: string) {
  return { DRAFT: 'bg-gray-100 text-gray-700', SENT: 'bg-blue-100 text-blue-700', CONFIRMED: 'bg-green-100 text-green-700', CANCELLED: 'bg-red-100 text-red-700' }[s] || 'bg-gray-100 text-gray-700'
}

// 외부에서 특정 문서 ID로 모달 열기 (양방향 링크용)
async function openDocumentById(docId: number) {
  try {
    const res = await salesDocumentApi.getById(docId)
    editingDoc.value = res.data
    showFormModal.value = true
  } catch {
    showToast('문서를 불러오는데 실패했습니다', 'error')
  }
}

// 이 인스턴스가 처리해야 할 query인지 확인 (탭 라우팅과 일치해야 함)
function shouldHandleOpenDocQuery(): boolean {
  if (!route.query.open_doc_id) return false
  const expectedTab = props.fixedType ? props.fixedType.toLowerCase() : null
  // fixedType 없으면 모든 PI/CI 처리, 있으면 해당 탭일 때만
  return !expectedTab || route.query.tab === expectedTab
}

onMounted(() => {
  loadCustomers()
  loadData()
  if (shouldHandleOpenDocQuery()) {
    openDocumentById(Number(route.query.open_doc_id))
  }
})

watch(() => route.query.open_doc_id, (val) => {
  if (val && shouldHandleOpenDocQuery()) openDocumentById(Number(val))
})

defineExpose({ loadData, openDocumentById })
</script>
