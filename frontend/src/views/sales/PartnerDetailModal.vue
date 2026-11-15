<template>
  <div
    v-if="show && partner"
    ref="modalOverlay"
    class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
    tabindex="-1"
    @keydown.escape="closeModal"
  >
    <div class="relative top-10 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white mb-10" @click.stop>
      <div class="flex justify-between items-center mb-4">
        <div class="flex items-center gap-3">
          <h3 class="text-lg font-bold">거래처 상세 정보</h3>
          <div class="flex gap-1">
            <span
              v-if="partner.is_supplier"
              class="px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-800"
            >
              공급업체
            </span>
            <span
              v-if="partner.is_customer"
              class="px-2 py-0.5 text-xs font-medium rounded bg-purple-100 text-purple-800"
            >
              고객사
            </span>
          </div>
        </div>
        <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <div class="space-y-4">
        <!-- 기본 정보 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3 text-gray-700">기본 정보</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <span class="text-sm text-gray-500">거래처 코드</span>
              <p class="font-medium text-blue-600">{{ partner.partner_code }}</p>
            </div>
            <div>
              <span class="text-sm text-gray-500">거래처명</span>
              <p class="font-medium">{{ partner.partner_name }}</p>
            </div>
            <div>
              <span class="text-sm text-gray-500">사업자등록번호</span>
              <p>{{ partner.business_number || '-' }}</p>
            </div>
            <div>
              <span class="text-sm text-gray-500">거래시작년도</span>
              <p>{{ partner.business_start_year || '-' }}</p>
            </div>
            <div v-if="partner.is_customer">
              <span class="text-sm text-gray-500">거래유형</span>
              <p>
                <span :class="partner.trade_type === 'DOMESTIC' ? 'text-green-700 bg-green-50 border-green-200' : 'text-blue-700 bg-blue-50 border-blue-200'"
                  class="px-2 py-0.5 text-xs font-medium rounded border">
                  {{ partner.trade_type === 'DOMESTIC' ? '국내' : '해외 (수출)' }}
                </span>
              </p>
            </div>
            <div>
              <span class="text-sm text-gray-500">상태</span>
              <span
                :class="[
                  'px-2 inline-flex text-xs leading-5 font-semibold rounded-full',
                  partner.is_active
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-800',
                ]"
              >
                {{ partner.is_active ? '활성' : '비활성' }}
              </span>
            </div>
          </div>
        </div>

        <!-- 국가 및 주소 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3 text-gray-700">국가 및 주소</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <span class="text-sm text-gray-500">대표자명</span>
              <p>{{ partner.representative || '-' }}</p>
            </div>
            <div>
              <span class="text-sm text-gray-500">국가명</span>
              <p>{{ partner.country_name || '-' }}</p>
            </div>
            <div>
              <span class="text-sm text-gray-500">국가코드</span>
              <p>{{ partner.country_code || '-' }}</p>
            </div>
          </div>
          <div class="mt-3">
            <span class="text-sm text-gray-500">주소</span>
            <p>{{ partner.address || '-' }}</p>
          </div>
        </div>

        <!-- 회사 연락처 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3 text-gray-700">회사 연락처</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <span class="text-sm text-gray-500">전화번호</span>
              <p>{{ partner.tel || '-' }}</p>
            </div>
            <div>
              <span class="text-sm text-gray-500">이메일</span>
              <p>{{ partner.email || '-' }}</p>
            </div>
            <div>
              <span class="text-sm text-gray-500">웹사이트</span>
              <p>
                <a
                  v-if="partner.website"
                  :href="partner.website"
                  target="_blank"
                  class="text-blue-600 hover:underline"
                >
                  {{ partner.website }}
                </a>
                <span v-else>-</span>
              </p>
            </div>
          </div>
        </div>

        <!-- 담당자 정보 (다중 등록) -->
        <div class="border-b pb-4">
          <div class="flex items-center justify-between mb-3">
            <h4 class="font-semibold text-gray-700">👤 담당자 ({{ contacts.length }})</h4>
            <button @click="showAddContact = true"
              class="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600">
              + 담당자 추가
            </button>
          </div>

          <!-- 담당자 추가 폼 -->
          <div v-if="showAddContact" class="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div>
                <label class="text-xs text-gray-500">이름 <span class="text-red-500">*</span></label>
                <input v-model="newContact.name" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="이름" />
              </div>
              <div>
                <label class="text-xs text-gray-500">직책</label>
                <input v-model="newContact.position" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="예: 과장" />
              </div>
              <div>
                <label class="text-xs text-gray-500">역할</label>
                <select v-model="newContact.role" class="w-full border rounded px-2 py-1.5 text-sm">
                  <option value="">선택</option>
                  <option value="PURCHASING">구매 담당</option>
                  <option value="TECHNICAL">기술 담당</option>
                  <option value="SALES">영업 담당</option>
                  <option value="GENERAL">일반</option>
                </select>
              </div>
              <div>
                <label class="text-xs text-gray-500">이메일</label>
                <input v-model="newContact.email" class="w-full border rounded px-2 py-1.5 text-sm" type="email" />
              </div>
              <div>
                <label class="text-xs text-gray-500">휴대폰</label>
                <input v-model="newContact.tel_mobile" class="w-full border rounded px-2 py-1.5 text-sm" />
              </div>
              <div class="flex items-end gap-2">
                <label class="inline-flex items-center text-sm">
                  <input v-model="newContact.is_primary" type="checkbox" class="w-4 h-4 mr-1" />
                  기본 담당자
                </label>
              </div>
            </div>
            <div class="flex justify-end gap-2 mt-2">
              <button @click="showAddContact = false; resetNewContact()" class="px-3 py-1 text-xs text-gray-600 hover:text-gray-800">취소</button>
              <button @click="saveNewContact" :disabled="!newContact.name"
                class="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">저장</button>
            </div>
          </div>

          <!-- 담당자 목록 -->
          <div v-if="contacts.length === 0 && !showAddContact" class="text-center py-4 text-gray-400 text-sm bg-gray-50 rounded">
            등록된 담당자가 없습니다.
          </div>
          <div v-else class="space-y-2">
            <div v-for="c in contacts" :key="c.id"
              class="flex items-center justify-between p-3 rounded-lg"
              :class="c.is_primary ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50'">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-sm">{{ c.name }}</span>
                  <span v-if="c.position" class="text-xs text-gray-500">{{ c.position }}</span>
                  <span v-if="c.is_primary" class="px-1.5 py-0.5 text-[10px] font-medium bg-blue-100 text-blue-700 rounded">기본</span>
                  <span v-if="c.role" class="px-1.5 py-0.5 text-[10px] font-medium bg-gray-200 text-gray-600 rounded">
                    {{ contactRoleLabel(c.role) }}
                  </span>
                </div>
                <div class="flex gap-4 mt-1 text-xs text-gray-500">
                  <span v-if="c.email">📧 {{ c.email }}</span>
                  <span v-if="c.tel_mobile">📱 {{ c.tel_mobile }}</span>
                  <span v-if="c.tel_office">📞 {{ c.tel_office }}</span>
                </div>
              </div>
              <div class="flex gap-1 flex-shrink-0 ml-2">
                <button v-if="!c.is_primary" @click="setPrimaryContact(c.id)"
                  class="p-1 text-gray-400 hover:text-blue-500 text-xs" title="기본 담당자로 설정">⭐</button>
                <button @click="deleteContactHandler(c.id)"
                  class="p-1 text-gray-400 hover:text-red-500 text-xs" title="삭제">🗑</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 배송지 (다중 등록) v0.58.0 -->
        <div class="border-b pb-4">
          <div class="flex items-center justify-between mb-3">
            <h4 class="font-semibold text-gray-700">🚚 배송지 ({{ shippingAddresses.length }})</h4>
            <button @click="showAddShipping = true"
              class="px-3 py-1 text-xs bg-emerald-500 text-white rounded hover:bg-emerald-600">+ 배송지 추가</button>
          </div>
          <!-- 추가 폼 -->
          <div v-if="showAddShipping" class="bg-emerald-50 border border-emerald-200 rounded-lg p-3 mb-3">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div><label class="text-xs text-gray-500">이름표</label><input v-model="newShipping.label" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="예: 본사 / ○○물류창고" /></div>
              <div><label class="text-xs text-gray-500">수령처명</label><input v-model="newShipping.name" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="회사/이름" /></div>
              <div class="sm:col-span-2">
                <label class="text-xs text-gray-500">주소</label>
                <textarea v-model="newShipping.address" rows="4" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="건물/시설명&#10;거리명 + 번호&#10;우편번호 + 도시&#10;국가"></textarea>
                <p class="text-[11px] text-gray-400 mt-0.5">Enter로 줄바꿈한 그대로 문서 PDF에 출력됩니다. 권장: 시설명 → 거리+번호 → 우편번호+도시 → 국가</p>
              </div>
              <div><label class="text-xs text-gray-500">담당자</label><input v-model="newShipping.contact" class="w-full border rounded px-2 py-1.5 text-sm" /></div>
              <div><label class="text-xs text-gray-500">전화</label><input v-model="newShipping.phone" class="w-full border rounded px-2 py-1.5 text-sm" /></div>
              <div><label class="text-xs text-gray-500">이메일</label><input v-model="newShipping.email" type="email" class="w-full border rounded px-2 py-1.5 text-sm" /></div>
              <div class="flex items-end"><label class="inline-flex items-center text-sm"><input v-model="newShipping.is_default" type="checkbox" class="w-4 h-4 mr-1" />기본 배송지</label></div>
            </div>
            <div class="flex justify-end gap-2 mt-2">
              <button @click="showAddShipping = false; resetNewShipping()" class="px-3 py-1 text-xs text-gray-600 hover:text-gray-800">취소</button>
              <button @click="saveNewShipping" :disabled="!newShipping.address && !newShipping.name"
                class="px-3 py-1 text-xs bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50">저장</button>
            </div>
          </div>
          <!-- 목록 -->
          <div v-if="shippingAddresses.length === 0 && !showAddShipping" class="text-center py-4 text-gray-400 text-sm bg-gray-50 rounded">
            등록된 배송지가 없습니다. (회사 주소와 배송지가 다르면 등록하세요)
          </div>
          <div v-else class="space-y-2">
            <div v-for="s in shippingAddresses" :key="s.id"
              class="flex items-center justify-between p-3 rounded-lg"
              :class="s.is_default ? 'bg-emerald-50 border border-emerald-200' : 'bg-gray-50'">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-sm">{{ s.label || s.name || '배송지' }}</span>
                  <span v-if="s.is_default" class="px-1.5 py-0.5 text-[10px] font-medium bg-emerald-100 text-emerald-700 rounded">기본</span>
                </div>
                <div v-if="s.address" class="text-xs text-gray-500 mt-1 truncate" :title="s.address">{{ s.address }}</div>
                <div class="flex gap-3 mt-0.5 text-xs text-gray-400">
                  <span v-if="s.contact">👤 {{ s.contact }}</span>
                  <span v-if="s.phone">📱 {{ s.phone }}</span>
                  <span v-if="s.email">📧 {{ s.email }}</span>
                </div>
              </div>
              <div class="flex gap-1 flex-shrink-0 ml-2">
                <button v-if="!s.is_default" @click="setDefaultShipping(s.id)" class="p-1 text-gray-400 hover:text-emerald-500 text-xs" title="기본 배송지로 설정">⭐</button>
                <button @click="deleteShippingHandler(s.id)" class="p-1 text-gray-400 hover:text-red-500 text-xs" title="삭제">🗑</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 거래 조건 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3 text-gray-700">거래 조건</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <span class="text-sm text-gray-500">결제 조건</span>
              <p>{{ partner.payment_terms || '-' }}</p>
            </div>
            <div>
              <span class="text-sm text-gray-500">납품 조건</span>
              <p>{{ partner.delivery_terms || '-' }}</p>
            </div>
            <div v-if="partner.is_customer">
              <span class="text-sm text-gray-500">기본 마진율</span>
              <p>{{ partner.default_margin_rate !== undefined && partner.default_margin_rate !== null ? `${partner.default_margin_rate}%` : '-' }}</p>
            </div>
          </div>
        </div>

        <!-- 최근 주문 이력 / 재주문 (고객사만) -->
        <div v-if="partner.is_customer" class="border-b pb-4">
          <div class="flex items-center justify-between mb-3">
            <h4 class="font-semibold text-gray-700">📦 최근 주문 이력 ({{ recentOrders.length }})</h4>
            <button v-if="recentOrders.length > 0"
              @click="loadRecentOrders"
              class="text-xs text-blue-600 hover:text-blue-800">🔄 새로고침</button>
          </div>

          <div v-if="loadingOrders" class="text-center py-4 text-gray-400 text-sm">
            로딩 중...
          </div>
          <div v-else-if="recentOrders.length === 0" class="text-center py-6 text-gray-400 text-sm bg-gray-50 rounded">
            아직 주문 이력이 없습니다.
          </div>
          <div v-else class="border rounded-lg overflow-hidden">
            <table class="w-full text-xs">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-left text-gray-500">유형</th>
                  <th class="px-3 py-2 text-left text-gray-500">문서번호</th>
                  <th class="px-3 py-2 text-left text-gray-500">날짜</th>
                  <th class="px-3 py-2 text-left text-gray-500">제품</th>
                  <th class="px-3 py-2 text-right text-gray-500">금액</th>
                  <th class="px-3 py-2 text-center text-gray-500">재주문</th>
                </tr>
              </thead>
              <tbody class="divide-y">
                <tr v-for="d in recentOrders" :key="d.id" class="hover:bg-blue-50">
                  <td class="px-3 py-2">
                    <span :class="d.document_type === 'PI' ? 'bg-purple-100 text-purple-700' : 'bg-amber-100 text-amber-700'"
                      class="px-2 py-0.5 text-[10px] font-medium rounded">
                      {{ d.document_type }}
                    </span>
                  </td>
                  <td class="px-3 py-2 font-medium text-blue-600 cursor-pointer hover:underline"
                    @click="goToDocument(d.id, d.document_number)">{{ d.document_number }}</td>
                  <td class="px-3 py-2 text-gray-600">{{ formatOrderDate(d.document_date) }}</td>
                  <td class="px-3 py-2 text-gray-600">
                    <div v-if="d.representative_product" class="max-w-[180px]">
                      <span class="font-mono truncate block" :title="d.representative_product">{{ d.representative_product }}</span>
                      <span v-if="(d.item_count || 0) > 1" class="text-gray-400 text-[10px]">외 {{ (d.item_count || 1) - 1 }}건</span>
                    </div>
                    <span v-else class="text-gray-400">-</span>
                  </td>
                  <td class="px-3 py-2 text-right font-medium">{{ d.currency }} {{ formatOrderNumber(d.total_amount) }}</td>
                  <td class="px-3 py-2 text-center">
                    <button @click="handleReorder(d)"
                      :disabled="reordering"
                      class="px-2 py-0.5 text-[10px] font-medium bg-green-50 text-green-700 hover:bg-green-100 rounded disabled:opacity-50">
                      🔁 재주문
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 전속(독점) 계약 부품 (고객사만) -->
        <div v-if="partner.is_customer" class="border-b pb-4">
          <h4 class="font-semibold text-gray-700 mb-3">🔒 전속(독점) 계약 부품 ({{ protectedParts.length }})</h4>
          <div v-if="loadingProtected" class="text-center py-4 text-gray-400 text-sm">로딩 중...</div>
          <div v-else-if="protectedParts.length === 0" class="text-center py-5 text-gray-400 text-sm bg-gray-50 rounded">
            이 고객의 전속 계약 부품이 없습니다.
          </div>
          <div v-else class="border rounded-lg overflow-hidden">
            <table class="w-full text-xs">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-left text-gray-500">품번</th>
                  <th class="px-3 py-2 text-left text-gray-500">부품명</th>
                  <th class="px-3 py-2 text-left text-gray-500">계약 비고</th>
                </tr>
              </thead>
              <tbody class="divide-y">
                <tr v-for="p in protectedParts" :key="p.id" class="hover:bg-red-50">
                  <td class="px-3 py-2 font-mono text-blue-700">{{ p.part_number_display || p.part_number }}</td>
                  <td class="px-3 py-2 text-gray-700">{{ p.part_name }}</td>
                  <td class="px-3 py-2 text-gray-500">{{ p.protection_note || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 선불 잔액 (고객사만) -->
        <div v-if="partner.is_customer && (balanceData.current_balance > 0 || balanceData.transactions.length > 0)" class="border-b pb-4">
          <div class="flex items-center justify-between mb-3">
            <h4 class="font-semibold text-gray-700">
              💰 선불 잔액:
              <span :class="balanceData.current_balance > 0 ? 'text-green-600' : 'text-gray-400'">
                {{ balanceData.currency }} {{ balanceData.current_balance.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}
              </span>
            </h4>
            <button @click="showDepositForm = !showDepositForm"
              class="px-3 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600">+ 입금</button>
          </div>

          <!-- 입금 폼 -->
          <div v-if="showDepositForm" class="bg-green-50 border border-green-200 rounded-lg p-3 mb-3">
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <div>
                <label class="text-xs text-gray-500">금액</label>
                <input v-model.number="depositAmount" type="number" min="0" step="0.01"
                  class="w-full border rounded px-2 py-1.5 text-sm" placeholder="10000" />
              </div>
              <div>
                <label class="text-xs text-gray-500">통화</label>
                <select v-model="depositCurrency" class="w-full border rounded px-2 py-1.5 text-sm">
                  <option>USD</option><option>EUR</option><option>KRW</option><option>CNY</option><option>JPY</option><option>GBP</option>
                </select>
              </div>
              <div>
                <label class="text-xs text-gray-500">메모</label>
                <input v-model="depositMemo" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="Wire Transfer" />
              </div>
            </div>
            <div class="flex justify-end gap-2 mt-2">
              <button @click="showDepositForm = false" class="text-xs text-gray-500">취소</button>
              <button @click="handleDeposit" :disabled="!depositAmount || depositAmount <= 0"
                class="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50">입금 처리</button>
            </div>
          </div>

          <!-- 입출금 이력 -->
          <div v-if="balanceData.transactions.length > 0" class="border rounded-lg overflow-hidden">
            <table class="w-full text-xs">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-left text-gray-500">일시</th>
                  <th class="px-3 py-2 text-left text-gray-500">구분</th>
                  <th class="px-3 py-2 text-right text-gray-500">금액</th>
                  <th class="px-3 py-2 text-right text-gray-500">잔액</th>
                  <th class="px-3 py-2 text-left text-gray-500">메모</th>
                </tr>
              </thead>
              <tbody class="divide-y">
                <tr v-for="t in balanceData.transactions" :key="t.id">
                  <td class="px-3 py-2 text-gray-500">{{ formatBalanceDate(t.created_at) }}</td>
                  <td class="px-3 py-2">
                    <span :class="t.type === 'DEPOSIT' ? 'text-green-700 bg-green-50' : 'text-red-700 bg-red-50'"
                      class="px-1.5 py-0.5 text-[10px] font-medium rounded">
                      {{ t.type === 'DEPOSIT' ? '입금' : '차감' }}
                    </span>
                  </td>
                  <td class="px-3 py-2 text-right font-medium"
                    :class="t.type === 'DEPOSIT' ? 'text-green-600' : 'text-red-600'">
                    {{ t.type === 'DEPOSIT' ? '+' : '-' }}{{ t.currency }} {{ t.amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}
                  </td>
                  <td class="px-3 py-2 text-right text-gray-600">{{ t.currency }} {{ t.balance_after.toLocaleString(undefined, { minimumFractionDigits: 2 }) }}</td>
                  <td class="px-3 py-2 text-gray-500">
                    <span v-if="t.reference_doc_id" @click="goToDocument(t.reference_doc_id, t.reference_doc_number)"
                      class="text-blue-600 hover:underline cursor-pointer">{{ t.reference_doc_number }}</span>
                    <span v-else>{{ t.memo || '-' }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 히스토리 탭 영역 -->
        <div class="border-b pb-4">
          <div class="flex border-b mb-4">
            <button
              @click="detailTab = 'timeline'"
              :class="detailTab === 'timeline'
                ? 'border-b-2 border-blue-600 text-blue-600 font-semibold'
                : 'text-gray-500 hover:text-gray-700'"
              class="px-4 py-2 text-sm transition-colors">
              통합 히스토리
            </button>
            <button
              @click="detailTab = 'notes'"
              :class="detailTab === 'notes'
                ? 'border-b-2 border-blue-600 text-blue-600 font-semibold'
                : 'text-gray-500 hover:text-gray-700'"
              class="px-4 py-2 text-sm transition-colors">
              메모 ({{ notes.length }})
            </button>
            <button
              @click="detailTab = 'files'"
              :class="detailTab === 'files'
                ? 'border-b-2 border-blue-600 text-blue-600 font-semibold'
                : 'text-gray-500 hover:text-gray-700'"
              class="px-4 py-2 text-sm transition-colors">
              첨부 문서
            </button>
            <button
              @click="detailTab = 'cloud'"
              :class="detailTab === 'cloud'
                ? 'border-b-2 border-blue-600 text-blue-600 font-semibold'
                : 'text-gray-500 hover:text-gray-700'"
              class="px-4 py-2 text-sm transition-colors">
              🗂 파일함
            </button>
          </div>

          <!-- 통합 히스토리 탭 -->
          <div v-if="detailTab === 'timeline'">
            <div v-if="loadingTimeline" class="text-center py-6 text-gray-400 text-sm">로딩 중...</div>
            <div v-else-if="timeline.length === 0" class="text-center py-6 text-gray-400 text-sm bg-gray-50 rounded">
              아직 기록된 이력이 없습니다.
            </div>
            <div v-else class="space-y-3 max-h-[400px] overflow-y-auto pr-1">
              <div v-for="(item, idx) in timeline" :key="idx" class="flex gap-3">
                <!-- 아이콘 -->
                <div class="flex flex-col items-center flex-shrink-0">
                  <div :class="timelineIconClass(item)"
                    class="w-7 h-7 rounded-full border flex items-center justify-center text-sm">
                    {{ timelineIcon(item) }}
                  </div>
                  <div v-if="idx < timeline.length - 1" class="w-0.5 flex-1 bg-gray-200 mt-1"></div>
                </div>
                <!-- 내용 -->
                <div class="flex-1 pb-3 min-w-0">
                  <div class="flex items-baseline gap-2 flex-wrap">
                    <span :class="timelineBadgeClass(item)"
                      class="px-2 py-0.5 text-[10px] font-medium rounded border whitespace-nowrap">
                      {{ timelineLabel(item) }}
                    </span>
                    <span class="text-xs text-gray-400">{{ formatTimelineDate(item.created_at) }}</span>
                    <span v-if="item.created_by" class="text-xs font-medium text-gray-600">{{ item.created_by }}</span>
                    <span v-if="item.is_pinned" class="text-[10px] text-yellow-600">📌 고정</span>
                  </div>
                  <div v-if="item.ref_title" class="text-[11px] text-gray-500 mt-0.5">{{ item.ref_title }}</div>
                  <p class="text-sm mt-0.5 whitespace-pre-wrap text-gray-800"
                    :class="item.type === 'DOCUMENT' && item.ref_id ? 'text-blue-600 hover:underline cursor-pointer' : ''"
                    @click="item.type === 'DOCUMENT' && item.ref_id && goToDocument(item.ref_id, item.doc_number)">
                    {{ item.content }}
                  </p>
                  <div v-if="item.type === 'DOCUMENT' && item.total_amount" class="text-xs text-gray-500 mt-0.5">
                    {{ item.currency }} {{ (item.total_amount || 0).toLocaleString() }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 메모 탭 -->
          <div v-if="detailTab === 'notes'">
            <!-- 메모 입력 -->
            <div class="bg-gray-50 border rounded-lg p-3 mb-4">
              <div class="flex gap-1 mb-2">
                <button v-for="(label, key) in NOTE_TYPE_LABELS" :key="key"
                  @click="newNoteType = key"
                  :class="newNoteType === key
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'"
                  class="px-2 py-0.5 text-[11px] font-medium border rounded transition-colors">
                  {{ label }}
                </button>
              </div>
              <div class="flex gap-2">
                <textarea v-model="newNoteContent" rows="2"
                  class="flex-1 border rounded px-3 py-2 text-sm"
                  placeholder="이 업체에 대한 메모를 남기세요..."
                  @keydown.ctrl.enter="saveNote"
                  @keydown.meta.enter="saveNote"></textarea>
                <div class="flex flex-col gap-1 self-end">
                  <label class="inline-flex items-center text-[10px] text-gray-500">
                    <input v-model="newNotePinned" type="checkbox" class="w-3 h-3 mr-1" /> 고정
                  </label>
                  <button @click="saveNote" :disabled="!newNoteContent.trim()"
                    class="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
                    추가
                  </button>
                </div>
              </div>
            </div>

            <!-- 메모 목록 -->
            <div v-if="notes.length === 0" class="text-center py-4 text-gray-400 text-sm bg-gray-50 rounded">
              등록된 메모가 없습니다.
            </div>
            <div v-else class="space-y-2 max-h-[350px] overflow-y-auto pr-1">
              <div v-for="note in notes" :key="note.id"
                :class="note.is_pinned ? 'border-yellow-300 bg-yellow-50/50' : 'border-gray-200 bg-white'"
                class="border rounded-lg p-3">
                <div class="flex items-center justify-between mb-1">
                  <div class="flex items-center gap-2">
                    <span v-if="note.is_pinned" class="text-[10px] text-yellow-600">📌</span>
                    <span :class="NOTE_TYPE_COLORS[note.note_type] || 'bg-gray-100 text-gray-700'"
                      class="px-2 py-0.5 text-[10px] font-medium rounded">
                      {{ NOTE_TYPE_LABELS[note.note_type] || note.note_type }}
                    </span>
                    <span class="text-xs text-gray-400">{{ formatTimelineDate(note.created_at) }}</span>
                    <span v-if="note.created_by" class="text-xs text-gray-500">{{ note.created_by }}</span>
                  </div>
                  <div class="flex gap-1">
                    <button @click="togglePinNote(note)" class="text-[10px] text-gray-400 hover:text-yellow-600"
                      :title="note.is_pinned ? '고정 해제' : '고정'">
                      {{ note.is_pinned ? '📌' : '📍' }}
                    </button>
                    <button @click="deleteNoteHandler(note.id)" class="text-[10px] text-gray-400 hover:text-red-500">🗑</button>
                  </div>
                </div>
                <p class="text-sm whitespace-pre-wrap text-gray-800">{{ note.content }}</p>
              </div>
            </div>
          </div>

          <!-- 첨부 문서 탭 -->
          <div v-if="detailTab === 'files'">
            <div class="flex justify-end mb-3">
              <label class="cursor-pointer px-3 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 flex items-center gap-1">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                파일 추가
                <input type="file" class="hidden" @change="handleFileUpload"
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif" />
              </label>
            </div>

          <div v-if="isUploading" class="flex items-center justify-center py-4">
            <svg class="animate-spin h-5 w-5 text-blue-500 mr-2" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            <span class="text-gray-600">업로드 중...</span>
          </div>

          <div v-else-if="documentFiles.length === 0" class="text-center py-6 text-gray-400">
            <svg class="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p>첨부된 문서가 없습니다</p>
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="(file, index) in documentFiles"
              :key="index"
              class="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
            >
              <div class="flex items-center gap-3 flex-1 min-w-0">
                <div class="flex-shrink-0">
                  <svg v-if="isPdfFile(file.original_name)" class="w-8 h-8 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
                  </svg>
                  <svg v-else-if="isImageFile(file.original_name)" class="w-8 h-8 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
                  </svg>
                  <svg v-else class="w-8 h-8 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-gray-900 truncate">{{ file.original_name }}</p>
                  <p class="text-xs text-gray-500">
                    {{ formatFileSize(file.file_size) }} · {{ formatUploadDate(file.uploaded_at) }}
                  </p>
                </div>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <button
                  v-if="isImageFile(file.original_name) || isPdfFile(file.original_name)"
                  type="button"
                  @click="openPreviewFile(file.file_path)"
                  class="p-1.5 text-gray-400 hover:text-blue-500"
                  title="미리보기"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </button>
                <button
                  type="button"
                  @click="downloadFile(file.file_path, file.original_name)"
                  class="p-1.5 text-gray-400 hover:text-green-500"
                  title="다운로드"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </button>
                <button
                  @click="handleDeleteFile(index)"
                  class="p-1.5 text-gray-400 hover:text-red-500"
                  title="삭제"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
          </div><!-- /files tab -->

          <!-- 클라우드 파일함 탭 (Nextcloud 브라우저) -->
          <div v-if="detailTab === 'cloud'">
            <CloudFileBrowser
              scope="customer"
              :customer-id="partner?.id ?? null"
              :active="detailTab === 'cloud'"
            />
          </div>
        </div><!-- /tabs -->

        <!-- 등록 정보 -->
        <div class="pb-4">
          <h4 class="font-semibold mb-3 text-gray-700">등록 정보</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <span class="text-sm text-gray-500">등록일시</span>
              <p>{{ formatDateTime(partner.created_at) }}</p>
            </div>
            <div>
              <span class="text-sm text-gray-500">수정일시</span>
              <p>{{ partner.updated_at ? formatDateTime(partner.updated_at) : '-' }}</p>
            </div>
          </div>
        </div>

        <!-- 버튼 -->
        <div class="flex justify-end space-x-3 pt-4 border-t">
          <button
            type="button"
            @click="closeModal"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            닫기
          </button>
          <button
            v-if="partner?.is_customer"
            type="button"
            @click="goToSales"
            class="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
          >
            견적/PI 보기
          </button>
          <button
            type="button"
            @click="editPartner"
            class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            수정
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { navigateToDocument } from '@/utils/documentNav'
import {
  type BusinessPartner, type FileInfo, type RecentOrderDocument,
  type PartnerContact, type PartnerContactCreate,
  type PartnerShippingAddress, type PartnerShippingAddressCreate,
  type PartnerNote, type TimelineItem, type PartnerBalance,
  CONTACT_ROLE_LABELS, NOTE_TYPE_LABELS, NOTE_TYPE_COLORS,
  partnerApi, partnerFileApi,
} from '@/api/partner'
import { downloadAuthedUrl, openAuthedUrl } from '@/utils/download'
import { partApi, type PartListItem } from '@/api/parts'
import CloudFileBrowser from '@/components/CloudFileBrowser.vue'

interface Props {
  show: boolean
  partner: BusinessPartner | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  edit: []
  updated: []
}>()

const router = useRouter()
const isUploading = ref(false)
const documentFiles = ref<FileInfo[]>([])
const detailTab = ref<'timeline' | 'notes' | 'files' | 'cloud'>('timeline')

// 재주문 패널 상태
const recentOrders = ref<RecentOrderDocument[]>([])
const loadingOrders = ref(false)
// v0.79.0: 전속(독점) 계약 부품
const protectedParts = ref<PartListItem[]>([])
const loadingProtected = ref(false)
async function loadProtectedParts() {
  if (!props.partner?.id) return
  loadingProtected.value = true
  try {
    const res = await partApi.getProtectedByCustomer(props.partner.id)
    protectedParts.value = res.data || []
  } catch { protectedParts.value = [] }
  finally { loadingProtected.value = false }
}
const reordering = ref(false)

// 담당자 상태
const contacts = ref<PartnerContact[]>([])
const showAddContact = ref(false)
const newContact = ref<PartnerContactCreate>({
  name: '', position: '', role: '', email: '', tel_mobile: '', is_primary: false,
})

// 배송지 상태 (v0.58.0)
const shippingAddresses = ref<PartnerShippingAddress[]>([])
const showAddShipping = ref(false)
const emptyShipping = (): PartnerShippingAddressCreate => ({
  label: '', name: '', address: '', contact: '', phone: '', email: '', is_default: false,
})
const newShipping = ref<PartnerShippingAddressCreate>(emptyShipping())
function resetNewShipping() { newShipping.value = emptyShipping() }

function goToDocument(docId: number, docNumber?: string) {
  const docType = docNumber?.startsWith('Q-') ? 'QUOTATION' : 'PI'
  emit('close')
  navigateToDocument(router, docId, docType)
}

// 선불 잔액 상태
const balanceData = ref<PartnerBalance>({ partner_id: 0, current_balance: 0, currency: 'USD', transactions: [] })
const showDepositForm = ref(false)
const depositAmount = ref<number>(0)
const depositCurrency = ref('USD')
const depositMemo = ref('')

async function loadBalance() {
  if (!props.partner) return
  try {
    const res = await partnerApi.getBalance(props.partner.id)
    balanceData.value = res.data
  } catch { balanceData.value = { partner_id: 0, current_balance: 0, currency: 'USD', transactions: [] } }
}

async function handleDeposit() {
  if (!props.partner || !depositAmount.value) return
  try {
    await partnerApi.depositBalance(props.partner.id, depositAmount.value, depositCurrency.value, depositMemo.value)
    showDepositForm.value = false
    depositAmount.value = 0
    depositMemo.value = ''
    await loadBalance()
  } catch { alert('입금 처리에 실패했습니다.') }
}

function formatBalanceDate(d?: string) {
  if (!d) return '-'
  const date = new Date(d)
  return `${date.getFullYear()}.${String(date.getMonth()+1).padStart(2,'0')}.${String(date.getDate()).padStart(2,'0')}`
}

// 메모 상태
const notes = ref<PartnerNote[]>([])
const newNoteContent = ref('')
const newNoteType = ref('GENERAL')
const newNotePinned = ref(false)

// 타임라인 상태
const timeline = ref<TimelineItem[]>([])
const loadingTimeline = ref(false)

async function loadNotes() {
  if (!props.partner) return
  try {
    const res = await partnerApi.getNotes(props.partner.id)
    notes.value = res.data
  } catch { notes.value = [] }
}

async function loadTimeline() {
  if (!props.partner) return
  loadingTimeline.value = true
  try {
    const res = await partnerApi.getTimeline(props.partner.id)
    timeline.value = res.data.items || []
  } catch { timeline.value = [] }
  finally { loadingTimeline.value = false }
}

async function saveNote() {
  if (!props.partner || !newNoteContent.value.trim()) return
  const userName = JSON.parse(localStorage.getItem('user') || '{}')?.name || undefined
  try {
    await partnerApi.createNote(props.partner.id, {
      note_type: newNoteType.value,
      content: newNoteContent.value.trim(),
      is_pinned: newNotePinned.value,
      created_by: userName,
    })
    newNoteContent.value = ''
    newNotePinned.value = false
    await loadNotes()
    await loadTimeline()
  } catch { alert('메모 저장에 실패했습니다.') }
}

async function togglePinNote(note: PartnerNote) {
  if (!props.partner) return
  try {
    await partnerApi.updateNote(props.partner.id, note.id, { is_pinned: !note.is_pinned })
    await loadNotes()
    await loadTimeline()
  } catch { alert('변경에 실패했습니다.') }
}

async function deleteNoteHandler(noteId: number) {
  if (!props.partner || !confirm('이 메모를 삭제하시겠습니까?')) return
  try {
    await partnerApi.deleteNote(props.partner.id, noteId)
    await loadNotes()
    await loadTimeline()
  } catch { alert('삭제에 실패했습니다.') }
}

// 타임라인 헬퍼
function timelineIcon(item: TimelineItem) {
  if (item.type === 'NOTE') return '📝'
  if (item.type === 'DOCUMENT') return '📄'
  // ACTIVITY_LOG
  const icons: Record<string, string> = {
    COMMENT: '💬', CONTACT: '📞', CURRENT_STATUS: '🎯', NEXT_STEP: '📋',
    ISSUE: '⚠', STATUS: '📋', STEP_UPDATE: '📋', INQUIRY_TYPE: '🏷', ASSIGNEE: '👤',
  }
  return icons[item.log_type || ''] || '·'
}

function timelineIconClass(item: TimelineItem) {
  if (item.type === 'NOTE') return 'bg-yellow-50 text-yellow-700 border-yellow-300'
  if (item.type === 'DOCUMENT') return 'bg-purple-50 text-purple-700 border-purple-300'
  return 'bg-gray-50 text-gray-700 border-gray-300'
}

function timelineBadgeClass(item: TimelineItem) {
  if (item.type === 'NOTE') return NOTE_TYPE_COLORS[item.note_type || 'GENERAL'] || 'bg-gray-100 text-gray-700'
  if (item.type === 'DOCUMENT') {
    const c: Record<string, string> = { QUOTATION: 'bg-blue-100 text-blue-700', PI: 'bg-purple-100 text-purple-700', CI: 'bg-amber-100 text-amber-700' }
    return c[item.doc_type || ''] || 'bg-gray-100 text-gray-700'
  }
  return 'bg-gray-100 text-gray-700 border-gray-300'
}

function timelineLabel(item: TimelineItem) {
  if (item.type === 'NOTE') return `메모 · ${NOTE_TYPE_LABELS[item.note_type || 'GENERAL'] || item.note_type}`
  if (item.type === 'DOCUMENT') return item.doc_type || '문서'
  const labels: Record<string, string> = {
    COMMENT: '코멘트', CONTACT: '고객 컨택', CURRENT_STATUS: '진행 상황', NEXT_STEP: '다음 단계',
    ISSUE: '이슈', STATUS: '상태 변경', STEP_UPDATE: '단계 업데이트', INQUIRY_TYPE: '문의 유형', ASSIGNEE: '담당자',
  }
  return labels[item.log_type || ''] || item.log_type || '활동'
}

function formatTimelineDate(d?: string) {
  if (!d) return ''
  const date = new Date(d)
  return `${date.getFullYear()}.${String(date.getMonth()+1).padStart(2,'0')}.${String(date.getDate()).padStart(2,'0')} ${String(date.getHours()).padStart(2,'0')}:${String(date.getMinutes()).padStart(2,'0')}`
}

function resetNewContact() {
  newContact.value = { name: '', position: '', role: '', email: '', tel_mobile: '', is_primary: false }
}

function contactRoleLabel(role: string) {
  return CONTACT_ROLE_LABELS[role] || role
}

async function loadContacts() {
  if (!props.partner) return
  try {
    const res = await partnerApi.getContacts(props.partner.id)
    contacts.value = res.data
  } catch { contacts.value = [] }
}

async function saveNewContact() {
  if (!props.partner || !newContact.value.name) return
  try {
    await partnerApi.createContact(props.partner.id, newContact.value)
    showAddContact.value = false
    resetNewContact()
    await loadContacts()
    emit('updated')
  } catch { alert('담당자 추가에 실패했습니다.') }
}

async function setPrimaryContact(contactId: number) {
  if (!props.partner) return
  try {
    await partnerApi.updateContact(props.partner.id, contactId, { is_primary: true })
    await loadContacts()
    emit('updated')
  } catch { alert('설정에 실패했습니다.') }
}

async function deleteContactHandler(contactId: number) {
  if (!props.partner || !confirm('이 담당자를 삭제하시겠습니까?')) return
  try {
    await partnerApi.deleteContact(props.partner.id, contactId)
    await loadContacts()
    emit('updated')
  } catch { alert('삭제에 실패했습니다.') }
}

// ── 배송지 (v0.58.0) ──
async function loadShipping() {
  if (!props.partner) return
  try {
    const res = await partnerApi.getShippingAddresses(props.partner.id)
    shippingAddresses.value = res.data
  } catch { shippingAddresses.value = [] }
}
async function saveNewShipping() {
  if (!props.partner) return
  if (!newShipping.value.address && !newShipping.value.name) return
  try {
    await partnerApi.createShippingAddress(props.partner.id, newShipping.value)
    showAddShipping.value = false
    resetNewShipping()
    await loadShipping()
    emit('updated')
  } catch { alert('배송지 추가에 실패했습니다.') }
}
async function setDefaultShipping(addressId: number) {
  if (!props.partner) return
  try {
    await partnerApi.updateShippingAddress(props.partner.id, addressId, { is_default: true })
    await loadShipping()
  } catch { alert('설정에 실패했습니다.') }
}
async function deleteShippingHandler(addressId: number) {
  if (!props.partner || !confirm('이 배송지를 삭제하시겠습니까?')) return
  try {
    await partnerApi.deleteShippingAddress(props.partner.id, addressId)
    await loadShipping()
  } catch { alert('삭제에 실패했습니다.') }
}

// partner가 변경되면 파일 목록 + 최근 주문 + 담당자 로드
watch(() => props.partner, (newPartner) => {
  if (newPartner) {
    documentFiles.value = newPartner.document_files || []
    detailTab.value = 'timeline'
    loadContacts()
    loadShipping()
    loadNotes()
    loadTimeline()
    if (newPartner.is_customer) loadBalance()
    if (newPartner.is_customer) {
      loadRecentOrders()
      loadProtectedParts()
    } else {
      recentOrders.value = []
      protectedParts.value = []
    }
  } else {
    documentFiles.value = []
    recentOrders.value = []
    protectedParts.value = []
    contacts.value = []
    notes.value = []
    timeline.value = []
  }
}, { immediate: true })

async function loadRecentOrders() {
  if (!props.partner) return
  loadingOrders.value = true
  try {
    const res = await partnerApi.getRecentOrders(props.partner.id, 10)
    recentOrders.value = res.data.documents || []
  } catch {
    recentOrders.value = []
  } finally {
    loadingOrders.value = false
  }
}

async function handleReorder(d: RecentOrderDocument) {
  if (!props.partner) return
  if (!confirm(`${d.document_number} 기반으로 재주문 견적을 시작하시겠습니까?\n\n새 영업활동이 자동으로 생성되고, 견적서 화면으로 이동합니다.`)) return

  reordering.value = true
  try {
    const res = await partnerApi.createReorder(props.partner.id, d.id)
    const result = res.data
    emit('close')
    // 견적서 탭으로 이동 + 영업활동 ID + 원본 문서 ID 전달
    router.push({
      path: '/sales',
      query: {
        tab: 'quotations',
        customer_id: String(result.customer_id),
        new_quotation: '1',
        activity_id: String(result.activity_id),
        copy_from_doc: String(result.source_document_id),
      },
    })
  } catch {
    alert('재주문 생성에 실패했습니다.')
  } finally {
    reordering.value = false
  }
}

function formatOrderDate(d?: string) {
  if (!d) return '-'
  return d.replace(/-/g, '.')
}
function formatOrderNumber(n: number) {
  return (n || 0).toLocaleString()
}

// 파일 업로드 처리
const handleFileUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !props.partner) return

  isUploading.value = true

  try {
    await partnerApi.uploadDocument(props.partner.id, file)
    // 파일 목록 갱신
    const filesResponse = await partnerApi.getFiles(props.partner.id)
    documentFiles.value = filesResponse.data.files || []
    emit('updated')
  } catch (error) {
    console.error('파일 업로드 실패:', error)
    alert('파일 업로드에 실패했습니다.')
  } finally {
    isUploading.value = false
    input.value = '' // 입력 초기화
  }
}

// 파일 삭제 처리
const handleDeleteFile = async (fileIndex: number) => {
  if (!props.partner) return

  if (!confirm('이 파일을 삭제하시겠습니까?')) return

  try {
    await partnerApi.deleteFile(props.partner.id, fileIndex)
    // 파일 목록 갱신
    const filesResponse = await partnerApi.getFiles(props.partner.id)
    documentFiles.value = filesResponse.data.files || []
    emit('updated')
  } catch (error) {
    console.error('파일 삭제 실패:', error)
    alert('파일 삭제에 실패했습니다.')
  }
}

// 파일 유틸리티 함수들
const formatFileSize = partnerFileApi.formatFileSize
const isImageFile = partnerFileApi.isImageFile
const isPdfFile = partnerFileApi.isPdfFile
// v0.41.0: 인증 헤더를 실어 blob 으로 미리보기/다운로드(RBAC enforce 시 401 방지)
const openPreviewFile = (filePath: string) =>
  openAuthedUrl(`/files/${filePath}`, { preview: true }).catch((e) => console.error('미리보기 실패', e))
const downloadFile = (filePath: string, name: string) =>
  downloadAuthedUrl(`/files/${filePath}`, name).catch((e) => console.error('다운로드 실패', e))

const formatUploadDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

const closeModal = () => {
  emit('close')
}

const editPartner = () => {
  emit('edit')
}

const goToSales = () => {
  if (props.partner) {
    router.push({ path: '/sales', query: { tab: 'quotations', customer_id: String(props.partner.id) } })
    emit('close')
  }
}

const formatDateTime = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(value)
}
</script>
