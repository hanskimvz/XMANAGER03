<template>
  <Teleport to="body">
    <Transition name="modal">
      <div class="fixed inset-0 z-50 flex items-start justify-center bg-black/50 overflow-y-auto py-8 transition-[padding]"
           :class="showActivityPopup ? 'lg:pr-[580px]' : ''">
        <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4">
          <!-- 헤더 -->
          <div class="flex items-center justify-between px-6 py-4 border-b">
            <h3 class="text-lg font-bold flex items-center gap-2">
              {{ isEdit ? '문서 수정' : typeLabel + ' 생성' }}
              <span v-if="isEdit && document?.document_number" class="text-sm font-normal text-gray-500">
                {{ document.document_number }}
              </span>
              <span v-if="isEdit && documentVersion > 1"
                class="px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-700 rounded">
                v{{ documentVersion }}
              </span>
              <span v-if="isEdit && document?.status && document.status !== 'DRAFT'"
                :class="{
                  'bg-blue-100 text-blue-700': document.status === 'SENT',
                  'bg-green-100 text-green-700': document.status === 'CONFIRMED',
                  'bg-red-100 text-red-700': document.status === 'CANCELLED',
                }"
                class="px-2 py-0.5 text-xs font-medium rounded">
                {{ { SENT: '발송', CONFIRMED: '확정', CANCELLED: '취소' }[document.status] || document.status }}
              </span>
            </h3>
            <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- PI 프로세스 현황 (PI 편집 모드에서만) -->
          <div v-if="isEdit && form.document_type === 'PI' && processSteps.length > 0" class="px-6 pt-4">
            <div class="flex flex-wrap gap-2">
              <div v-for="step in processSteps" :key="step.key"
                class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium"
                :class="step.done
                  ? 'bg-green-50 text-green-700 border border-green-300'
                  : 'bg-gray-50 text-gray-400 border border-gray-200'">
                <svg v-if="step.done" class="w-3.5 h-3.5 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
                <span v-else class="w-3.5 h-3.5 rounded-full border border-gray-300 flex-shrink-0"></span>
                <span>{{ step.label }}</span>
                <span v-if="step.detail" class="text-xs opacity-70">{{ step.detail }}</span>
              </div>
            </div>
          </div>

          <!-- 견적서가 PI/CI로 전환된 경우 경고 -->
          <div v-if="isEdit && form.document_type === 'QUOTATION' && relatedDocs.forward.length > 0"
            class="px-6 pt-3">
            <div class="bg-yellow-50 border border-yellow-300 rounded-lg px-3 py-2 text-xs text-yellow-800">
              ⚠ 이 견적서는 이미 <strong>{{ relatedDocs.forward.map(d => d.document_type + ' ' + d.document_number).join(', ') }}</strong>로 전환되었습니다.
              견적서를 수정해도 후속 문서에는 자동 반영되지 않으므로, 필요 시 후속 문서도 별도로 수정하세요.
            </div>
          </div>

          <!-- PI 생산 진행 현황 + 생산요청 추가 -->
          <div v-if="isEdit && form.document_type === 'PI' && piRemaining"
            class="px-6 pt-3">
            <div class="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
              <div class="flex items-center justify-between mb-2">
                <h4 class="text-sm font-medium text-indigo-800">📦 생산 진행 현황</h4>
                <button
                  v-if="hasRemainingQty"
                  @click="createPrDraft"
                  :disabled="creatingPr"
                  class="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50">
                  {{ creatingPr ? '생성 중...' : (relatedDocs.production_requests.length > 0 ? '+ 생산요청 추가' : '+ 생산요청 생성') }}
                </button>
                <span v-else class="text-xs text-indigo-600 font-medium">✓ 전 품목 생산요청 완료</span>
              </div>
              <table class="w-full text-xs">
                <thead>
                  <tr class="border-b border-indigo-200 text-indigo-700">
                    <th class="text-left py-1">품목</th>
                    <th class="text-right py-1 px-2">PI 수량</th>
                    <th class="text-right py-1 px-2">요청됨</th>
                    <th class="text-right py-1 px-2">잔여</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in piRemaining.items" :key="item.pi_item_id"
                    class="border-b border-indigo-100 last:border-0">
                    <td class="py-1 truncate max-w-[200px]">{{ item.product_code }}</td>
                    <td class="text-right py-1 px-2">{{ item.total_qty }}</td>
                    <td class="text-right py-1 px-2 text-gray-600">{{ item.requested_qty }}</td>
                    <td class="text-right py-1 px-2 font-medium"
                      :class="item.remaining_qty > 0 ? 'text-orange-600' : 'text-gray-400'">
                      {{ item.remaining_qty }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 연결된 영업 대응 현황 바로가기(문서 닫지 않고 히스토리 확인) -->
          <div v-if="isEdit && linkedActivity" class="px-6 pt-3">
            <button type="button" @click="showActivityPopup = !showActivityPopup"
              class="w-full flex items-center gap-2 px-3 py-2 border rounded-lg text-left transition-colors"
              :class="showActivityPopup ? 'bg-emerald-100 border-emerald-300' : 'bg-emerald-50 hover:bg-emerald-100 border-emerald-200'">
              <span class="text-base leading-none">🎯</span>
              <span class="min-w-0 flex-1">
                <span class="block text-xs font-medium text-emerald-800 truncate">영업 건: {{ linkedActivity.title }}</span>
                <span class="block text-[11px] text-emerald-600">진행 히스토리·특이사항 (문서 옆에 열림)</span>
              </span>
              <span class="text-[11px] text-emerald-700 whitespace-nowrap">{{ showActivityPopup ? '닫기 ✕' : '열기 →' }}</span>
            </button>
          </div>

          <!-- 관련 문서 (테이블) — 현재 문서 포함, 다른 문서 클릭 시 이동 -->
          <div v-if="isEdit && docChain.length > 1" class="px-6 pt-3">
            <h4 class="text-sm font-medium text-gray-700 mb-2">📄 관련 문서 ({{ docChain.length }})</h4>
            <div class="border rounded-lg overflow-hidden">
              <table class="w-full text-xs">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-3 py-2 text-left text-gray-500">유형</th>
                    <th class="px-3 py-2 text-left text-gray-500">문서번호</th>
                    <th class="px-3 py-2 text-left text-gray-500">날짜</th>
                    <th class="px-3 py-2 text-right text-gray-500">금액</th>
                    <th class="px-3 py-2 text-center text-gray-500">상태</th>
                  </tr>
                </thead>
                <tbody class="divide-y">
                  <tr v-for="d in docChain" :key="(d.type === 'PR' ? 'pr' : 'd') + d.id"
                    @click="d._current ? null : (d.type === 'PR' ? openProductionRequest(d.id) : openRelatedDoc(d.id))"
                    :class="d._current ? 'bg-blue-50/60' : 'hover:bg-blue-50 cursor-pointer'">
                    <td class="px-3 py-2">
                      <span :class="{
                        'bg-blue-100 text-blue-700': d.document_type === 'QUOTATION',
                        'bg-purple-100 text-purple-700': d.document_type === 'PI',
                        'bg-amber-100 text-amber-700': d.document_type === 'CI',
                        'bg-teal-100 text-teal-700': d.document_type === 'INVOICE',
                        'bg-indigo-100 text-indigo-700': d.type === 'PR',
                      }" class="px-2 py-0.5 text-[10px] font-medium rounded">
                        {{ d.type === 'PR' ? '생산요청' : d.document_type }}
                      </span>
                    </td>
                    <td class="px-3 py-2 font-medium" :class="d._current ? 'text-gray-800' : 'text-blue-600'">
                      {{ d.document_number || d.request_number }}
                      <span v-if="d._current" class="ml-1 text-[9px] text-gray-400">(현재)</span>
                    </td>
                    <td class="px-3 py-2 text-gray-600">{{ d.document_date?.replace(/-/g, '.') || '-' }}</td>
                    <td class="px-3 py-2 text-right font-medium">{{ d.total_amount ? `${d.currency || 'USD'} ${Number(d.total_amount).toLocaleString()}` : '-' }}</td>
                    <td class="px-3 py-2 text-center">
                      <span :class="{
                        'bg-gray-100 text-gray-700': d.status === 'DRAFT',
                        'bg-blue-100 text-blue-700': d.status === 'SENT',
                        'bg-green-100 text-green-700': d.status === 'CONFIRMED',
                        'bg-yellow-100 text-yellow-700': d.status === 'REQUESTED',
                        'bg-red-100 text-red-700': d.status === 'CANCELLED',
                      }" class="px-2 py-0.5 text-[10px] font-medium rounded-full">
                        {{ docStatusLabel(d.status) }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="px-6 py-4 max-h-[70vh] overflow-y-auto">
            <!-- 기본 정보 -->
            <div class="grid grid-cols-2 gap-4 mb-6">
              <div class="relative">
                <label class="block text-sm font-medium text-gray-700 mb-1">고객사 <span class="text-red-500">*</span></label>
                <input
                  v-model="customerSearch"
                  @focus="showCustomerDropdown = true; highlightedIndex = 0"
                  @input="showCustomerDropdown = true; highlightedIndex = 0"
                  @blur="hideCustomerDropdownDelayed"
                  @keydown.down.prevent="moveHighlight(1)"
                  @keydown.up.prevent="moveHighlight(-1)"
                  @keydown.enter.prevent="handleEnter"
                  @keydown.escape="showCustomerDropdown = false"
                  :disabled="isEdit"
                  class="w-full border rounded-md px-3 py-2 text-sm"
                  :placeholder="isEdit ? selectedCustomerName : '고객사명 입력하여 검색...'"
                />
                <!-- 선택된 고객 표시 -->
                <div v-if="form.customer_id && !showCustomerDropdown" class="absolute inset-y-0 right-2 top-6 flex items-center">
                  <button @click="clearCustomer" v-if="!isEdit" class="text-gray-400 hover:text-gray-600">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
                  </button>
                </div>
                <!-- 드롭다운 -->
                <div v-if="showCustomerDropdown && filteredCustomers.length > 0"
                  class="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
                  <div
                    v-for="(c, idx) in filteredCustomers"
                    :key="c.id"
                    @mousedown.prevent="selectCustomer(c)"
                    @mouseenter="highlightedIndex = idx"
                    class="px-3 py-2 text-sm cursor-pointer"
                    :class="highlightedIndex === idx ? 'bg-blue-100 font-medium' : (form.customer_id === c.id ? 'bg-blue-50 font-medium' : 'hover:bg-blue-50')"
                  >
                    {{ c.partner_name }}
                    <span v-if="c.partner_name_en" class="text-gray-400 text-xs ml-1">{{ c.partner_name_en }}</span>
                  </div>
                </div>
              </div>
              <!-- 고객사 담당자 (v0.52.0) -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">담당자</label>
                <div class="flex gap-2">
                  <select v-model.number="form.customer_contact_id" :disabled="!form.customer_id"
                    class="flex-1 border rounded-md px-3 py-2 text-sm disabled:bg-gray-100">
                    <option :value="undefined">{{ form.customer_id ? (contacts.length ? '담당자 선택' : '등록된 담당자 없음') : '고객사 먼저 선택' }}</option>
                    <option v-for="c in contacts" :key="c.id" :value="c.id">
                      {{ c.name }}<template v-if="c.position"> ({{ c.position }})</template><template v-if="c.is_primary"> · 기본</template>
                    </option>
                  </select>
                  <button type="button" :disabled="!form.customer_id" @click="showNewContact = !showNewContact"
                    class="px-2.5 py-2 text-xs border rounded-md text-gray-600 hover:bg-gray-50 disabled:opacity-50 whitespace-nowrap">＋신규</button>
                </div>
                <p class="text-[11px] text-gray-400 mt-1">미선택 시 거래처 기본 담당자가 문서에 표시됩니다.</p>
              </div>

              <!-- 거래처 VAT/TAX ID 표기 (해외 업체가 자사 VAT 기재 요청 시) -->
              <div>
                <label class="inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer select-none">
                  <input type="checkbox" v-model="form.show_customer_tax_id" class="w-4 h-4 rounded" />
                  거래처 VAT/TAX ID(사업자등록번호) 문서에 표기
                </label>
                <p class="text-[11px] text-gray-400 mt-1">
                  체크 시 거래처 정보의 <b>사업자등록번호</b>가 문서에 표기됩니다(해외 업체 VAT/NIP 등).
                  <span class="text-amber-600">거래처에 번호가 없으면 표기되지 않습니다.</span>
                </p>
              </div>

              <!-- CI 원산지 신고문(Statement of Origin) — 고객사에 따라 선택 -->
              <div v-if="!isDomestic">
                <label class="inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer select-none">
                  <input type="checkbox" v-model="form.show_statement_of_origin" class="w-4 h-4 rounded" />
                  CI에 원산지 신고문(Statement of Origin) 표기
                </label>
                <p class="text-[11px] text-gray-400 mt-1">
                  체크 시 CI 하단에 <b>원산지 신고문 + 서명란</b>이 추가됩니다(FTA 특혜원산지 요구 고객사용).
                  거래처 기본값에서 자동 적용되며 문서별로 조정할 수 있습니다.
                </p>
              </div>
              <!-- 신규 담당자 추가 (토글) -->
              <div v-if="showNewContact" class="col-span-2 border rounded-md p-3 bg-gray-50 grid grid-cols-2 sm:grid-cols-4 gap-2 items-end">
                <div><label class="block text-xs text-gray-500 mb-0.5">이름 *</label><input v-model="newContact.name" class="w-full border rounded px-2 py-1.5 text-sm" /></div>
                <div><label class="block text-xs text-gray-500 mb-0.5">직책</label><input v-model="newContact.position" class="w-full border rounded px-2 py-1.5 text-sm" /></div>
                <div><label class="block text-xs text-gray-500 mb-0.5">이메일</label><input v-model="newContact.email" class="w-full border rounded px-2 py-1.5 text-sm" /></div>
                <div><label class="block text-xs text-gray-500 mb-0.5">연락처</label><input v-model="newContact.tel_mobile" class="w-full border rounded px-2 py-1.5 text-sm" /></div>
                <div class="col-span-2 sm:col-span-4 flex justify-end gap-2">
                  <button type="button" @click="showNewContact = false" class="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700">취소</button>
                  <button type="button" :disabled="savingContact" @click="addNewContact" class="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">{{ savingContact ? '저장 중...' : '담당자 저장' }}</button>
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">문서 날짜</label>
                <input v-model="form.document_date" type="date" class="w-full border rounded-md px-3 py-2 text-sm" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">작성자</label>
                <input v-model="form.prepared_by" class="w-full border rounded-md px-3 py-2 text-sm" placeholder="MJ Kim" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">이메일</label>
                <input v-model="form.prepared_email" class="w-full border rounded-md px-3 py-2 text-sm" placeholder="email@xbeamtech.co.kr" />
              </div>
            </div>

            <!-- 수령자 (Ship To / Consignee) — 견적서부터. 거래처 저장 배송지 선택/직접입력 -->
            <div class="border border-gray-200 rounded-lg p-4 mb-6">
              <h4 class="text-sm font-semibold text-gray-700 mb-2">수령자 (Ship To / Consignee)</h4>
              <select v-model="form.ship_to_choice" :disabled="!form.customer_id"
                class="w-full border rounded-md px-3 py-2 text-sm disabled:bg-gray-100">
                <option value="SAME">구매자와 동일 (Same as Buyer)</option>
                <option v-for="s in shippingAddresses" :key="s.id" :value="String(s.id)">
                  🚚 {{ s.label || s.name || '배송지' }}{{ s.address ? ' — ' + s.address.slice(0, 28) : '' }}{{ s.is_default ? ' (기본)' : '' }}
                </option>
                <option value="CUSTOM">직접 입력 (일회성, 저장 안 함)</option>
              </select>
              <p v-if="form.customer_id && shippingAddresses.length === 0" class="text-[11px] text-gray-400 mt-1">
                이 거래처에 저장된 배송지가 없습니다. [거래처 관리]에서 배송지를 등록하면 여기서 바로 선택할 수 있어요.
              </p>
              <!-- 선택된 저장 배송지 미리보기 -->
              <div v-if="selectedShipping" class="text-xs bg-gray-50 rounded p-2 mt-2">
                <div class="font-medium text-gray-700">{{ selectedShipping.name || selectedShipping.label }}</div>
                <div v-if="selectedShipping.address" class="text-gray-500">{{ selectedShipping.address }}</div>
                <div class="text-gray-400">{{ [selectedShipping.contact, selectedShipping.phone, selectedShipping.email].filter(Boolean).join(' · ') }}</div>
              </div>
              <!-- 직접 입력 -->
              <div v-if="form.ship_to_choice === 'CUSTOM'" class="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
                <div class="sm:col-span-2">
                  <label class="block text-xs text-gray-500 mb-0.5">수령처 이름 (Name)</label>
                  <input v-model="form.ship_to_name" class="w-full border rounded-md px-3 py-2 text-sm" placeholder="DOMAR MS. Sp. z o.o." />
                </div>
                <div class="sm:col-span-2">
                  <label class="block text-xs text-gray-500 mb-0.5">주소 (Address)</label>
                  <textarea v-model="form.ship_to_address" rows="4" class="w-full border rounded-md px-3 py-2 text-sm" placeholder="건물/시설명&#10;거리명 + 번호&#10;우편번호 + 도시&#10;국가"></textarea>
                  <p class="text-[11px] text-gray-400 mt-0.5">Enter 줄바꿈이 문서에 그대로 반영됩니다.</p>
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-0.5">담당자 (Contact)</label>
                  <input v-model="form.ship_to_contact" class="w-full border rounded-md px-3 py-2 text-sm" placeholder="Patryk Olesiak" />
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-0.5">전화 (Phone)</label>
                  <input v-model="form.ship_to_phone" class="w-full border rounded-md px-3 py-2 text-sm" placeholder="+48 882 326 281" />
                </div>
                <div class="sm:col-span-2">
                  <label class="block text-xs text-gray-500 mb-0.5">이메일 (Email)</label>
                  <input v-model="form.ship_to_email" class="w-full border rounded-md px-3 py-2 text-sm" placeholder="magazyn@domar.waw.pl" />
                </div>
              </div>
            </div>

            <!-- PO 첨부파일 (PI/CI 편집 모드) -->
            <div v-if="isEdit && (form.document_type === 'PI' || form.document_type === 'CI')"
              class="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
              <div class="flex items-center justify-between mb-2">
                <h4 class="text-sm font-medium text-amber-800">
                  📎 PO 첨부파일 ({{ poAttachments.length }})
                </h4>
                <label class="px-3 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 cursor-pointer">
                  + 파일 추가
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.xlsx,.xls,.doc,.docx,.png,.jpg,.jpeg"
                    @change="onPoFileUpload"
                    class="hidden"
                  />
                </label>
              </div>
              <ul v-if="poAttachments.length > 0" class="space-y-1">
                <li v-for="(f, idx) in poAttachments" :key="idx"
                  class="flex items-center justify-between bg-white rounded px-3 py-1.5 text-sm border border-amber-100">
                  <button type="button" @click="openPoFile(idx)" class="text-left text-blue-600 hover:underline truncate flex-1">
                    📄 {{ f.filename }}
                  </button>
                  <span class="text-xs text-gray-400 mx-2">{{ formatFileSize(f.size) }}</span>
                  <button @click="deletePoFile(idx)" class="text-red-500 hover:text-red-700 text-xs">삭제</button>
                </li>
              </ul>
              <p v-else class="text-xs text-amber-700">아직 첨부된 PO 파일이 없습니다.</p>
            </div>

            <!-- CI 전용: 선적 정보 · 포장 명세 -->
            <div v-if="form.document_type === 'CI'" class="bg-teal-50 border border-teal-200 rounded-lg p-4 mb-6">
              <h4 class="text-sm font-medium text-teal-800 mb-1">🚢 선적 정보 · 포장 명세 (Commercial Invoice)</h4>
              <p class="text-[11px] text-teal-700 mb-3">PDF의 우측 정보란·Package Details에 표기됩니다. Payment/Delivery Terms·HS Code는 아래 Terms에서 입력(PI에서 자동 승계).</p>
              <div class="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <label class="text-xs text-gray-500">Ship From (출발지)</label>
                  <input v-model="form.ship_from" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="예: Seoul, Korea" />
                </div>
                <div>
                  <label class="text-xs text-gray-500">Final Destination (도착지)</label>
                  <input v-model="form.destination" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="예: Kobylanka, Poland" />
                </div>
                <div>
                  <label class="text-xs text-gray-500">Transportation (운송수단)</label>
                  <input v-model="form.transportation" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="예: By Air / By Sea" />
                </div>
                <div>
                  <label class="text-xs text-gray-500">Shipment Date (선적일)</label>
                  <input v-model="form.shipment_date" type="date" class="w-full border rounded px-2 py-1.5 text-sm" />
                </div>
                <div>
                  <label class="text-xs text-gray-500">Country of Origin (원산지)</label>
                  <input v-model="form.country_of_origin" class="w-full border rounded px-2 py-1.5 text-sm" placeholder="Republic of Korea" />
                </div>
              </div>
              <div class="mt-3 pt-3 border-t border-teal-200">
                <div class="flex items-center justify-between mb-2">
                  <label class="text-xs font-medium text-teal-800">Packing List (박스별 포장 명세) · 생산 출고 데이터 자동 반영</label>
                  <button type="button" @click="addCiBox" class="px-2 py-1 text-xs text-teal-700 border border-teal-300 rounded hover:bg-teal-100">+ 박스 추가</button>
                </div>
                <div class="overflow-x-auto">
                  <table class="min-w-full text-xs">
                    <thead>
                      <tr class="text-gray-500 border-b">
                        <th class="px-1 py-1 text-left min-w-[110px]">박스 종류</th>
                        <th class="px-1 py-1 text-center w-12">개수</th>
                        <th class="px-1 py-1 text-center w-16">Gross(kg)</th>
                        <th class="px-1 py-1 text-center w-16">Net(kg)</th>
                        <th class="px-1 py-1 text-center w-12">L(cm)</th>
                        <th class="px-1 py-1 text-center w-12">W(cm)</th>
                        <th class="px-1 py-1 text-center w-12">H(cm)</th>
                        <th class="w-6"></th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(b, i) in form.packing_list" :key="i" class="border-b">
                        <td class="px-1 py-1"><input v-model="b.box_type" list="ciBoxTypes" @change="onCiBoxSelect(b)" class="w-full border rounded px-1.5 py-1" placeholder="박스 선택/직접 입력" /></td>
                        <td class="px-1 py-1"><input v-model.number="b.quantity" type="number" min="1" class="w-full border rounded px-1 py-1 text-center" /></td>
                        <td class="px-1 py-1"><input v-model.number="b.gross_weight" type="number" step="0.01" class="w-full border rounded px-1 py-1 text-center" /></td>
                        <td class="px-1 py-1"><input v-model.number="b.net_weight" type="number" step="0.01" class="w-full border rounded px-1 py-1 text-center" /></td>
                        <td class="px-1 py-1"><input v-model.number="b.length" type="number" step="0.1" class="w-full border rounded px-1 py-1 text-center" /></td>
                        <td class="px-1 py-1"><input v-model.number="b.width" type="number" step="0.1" class="w-full border rounded px-1 py-1 text-center" /></td>
                        <td class="px-1 py-1"><input v-model.number="b.height" type="number" step="0.1" class="w-full border rounded px-1 py-1 text-center" /></td>
                        <td class="px-1 py-1 text-center"><button type="button" @click="removeCiBox(i)" class="text-red-400 hover:text-red-600">✕</button></td>
                      </tr>
                      <tr v-if="!form.packing_list || form.packing_list.length === 0">
                        <td colspan="8" class="px-1 py-2 text-center text-gray-400">생산 출고 시 입력된 packing list가 여기에 자동으로 채워집니다. 필요 시 추가/수정하세요.</td>
                      </tr>
                    </tbody>
                  </table>
                  <datalist id="ciBoxTypes">
                    <option v-for="p in BOX_PRESETS" :key="p.name" :value="p.name">{{ p.l }}×{{ p.w }}×{{ p.h }} cm</option>
                  </datalist>
                  <p class="text-[11px] text-teal-700 mt-1">박스 종류를 선택하면 가로·세로·높이가 자동 입력됩니다(무게는 직접 입력).</p>
                </div>
              </div>
            </div>

            <!-- 거래 조건 -->
            <div class="bg-gray-50 rounded-lg p-4 mb-6">
              <div class="flex items-center justify-between mb-3">
                <h4 class="text-sm font-medium text-gray-700">
                  {{ isDomestic ? '거래 조건' : 'Terms & Bank Details' }}
                  <span v-if="isDomestic" class="ml-2 px-1.5 py-0.5 text-xs bg-green-100 text-green-700 rounded">국내</span>
                  <span v-else class="ml-2 px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">해외</span>
                </h4>
                <button @click="termsEditable = !termsEditable" type="button"
                  class="text-xs px-2 py-1 rounded border"
                  :class="termsEditable ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-100'">
                  {{ termsEditable ? '편집 중 (🔓)' : '편집 잠금 (🔒)' }}
                </button>
              </div>
              <p class="text-xs text-gray-400 mb-2">
                ※ Delivery Terms는 언제든 수정 가능합니다. 나머지 항목은 "편집 잠금" 해제 후 수정하세요.
              </p>
              <div class="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <label class="text-xs text-gray-500">{{ isDomestic ? '결제 조건' : 'Payment Terms' }}</label>
                  <input v-model="form.payment_terms" :readonly="!termsEditable"
                    class="w-full border rounded px-2 py-1.5 text-sm"
                    :class="!termsEditable ? 'bg-gray-100 text-gray-600 cursor-not-allowed' : ''"
                    :placeholder="isDomestic ? '예: 선입금 / 월말 정산' : '예: 100% prepayment'" />
                </div>
                <div>
                  <label class="text-xs text-gray-500">통화</label>
                  <select v-model="form.currency" class="w-full border rounded px-2 py-1.5 text-sm">
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="KRW">KRW (₩)</option>
                    <option value="CNY">CNY (¥)</option>
                    <option value="JPY">JPY (¥)</option>
                    <option value="GBP">GBP (£)</option>
                  </select>
                </div>
                <div>
                  <label class="text-xs text-gray-500 font-medium text-blue-700">
                    {{ isDomestic ? '납품 조건' : 'Delivery Terms' }} <span class="text-[10px] font-normal">(항상 수정 가능)</span>
                  </label>
                  <input v-model="form.delivery_terms" class="w-full border-2 border-blue-300 rounded px-2 py-1.5 text-sm bg-white"
                    :placeholder="isDomestic ? '예: 택배 / 직납' : '예: EXW Seoul'" />
                </div>
                <!-- Incoterms (해외) + 박스당 Freight(CPT 등 운임부담 조건) -->
                <div v-if="!isDomestic">
                  <label class="text-xs text-gray-500 font-medium">Incoterms</label>
                  <select v-model="form.incoterms" class="w-full border rounded px-2 py-1.5 text-sm bg-white">
                    <option value="">(선택 안 함)</option>
                    <option v-for="t in INCOTERMS" :key="t" :value="t">{{ t }}</option>
                  </select>
                </div>
                <div v-if="!isDomestic && FREIGHT_TERMS.includes(form.incoterms || '')">
                  <label class="text-xs text-gray-500 font-medium">Freight (박스당, {{ form.currency || 'USD' }})</label>
                  <input type="number" min="0" step="0.01" v-model.number="form.freight_per_box"
                    class="w-full border rounded px-2 py-1.5 text-sm" placeholder="박스당 운임" />
                  <p class="text-[10px] text-gray-400 mt-0.5">분할선적 시 박스 CI마다 배송비로 가산됩니다.</p>
                </div>
                <div v-if="!isDomestic">
                  <div class="flex items-center justify-between mb-1">
                    <label class="text-xs text-gray-500">HS Code</label>
                    <div class="flex gap-0.5" v-if="termsEditable">
                      <button type="button" @click="applyHsPreset('connector')"
                        :class="currentHsPreset === 'connector' ? 'bg-blue-100 text-blue-700 border-blue-300' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'"
                        class="px-1.5 py-0.5 text-[10px] border rounded-l">커넥터류</button>
                      <button type="button" @click="applyHsPreset('cable')"
                        :class="currentHsPreset === 'cable' ? 'bg-blue-100 text-blue-700 border-blue-300' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'"
                        class="px-1.5 py-0.5 text-[10px] border-y">케이블 조립체</button>
                      <button type="button" @click="applyHsPreset('both')"
                        :class="currentHsPreset === 'both' ? 'bg-blue-100 text-blue-700 border-blue-300' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'"
                        class="px-1.5 py-0.5 text-[10px] border-y" title="커넥터 + 케이블 조립체 (HS Code 2개)">둘 다</button>
                      <button type="button" @click="applyHsPreset('custom')"
                        :class="currentHsPreset === 'custom' ? 'bg-blue-100 text-blue-700 border-blue-300' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'"
                        class="px-1.5 py-0.5 text-[10px] border rounded-r">직접입력</button>
                    </div>
                  </div>
                  <input v-model="form.hs_code" :readonly="!termsEditable"
                    placeholder="예: 8536.70-1000, 8544.70-0000"
                    class="w-full border rounded px-2 py-1.5 text-sm"
                    :class="!termsEditable ? 'bg-gray-100 text-gray-600 cursor-not-allowed' : ''" />
                  <p v-if="termsEditable" class="text-[10px] text-gray-400 mt-0.5">제품별 HS Code가 다르면 쉼표로 여러 개 입력(제품별 매칭은 품목 비고에 표기).</p>
                </div>
                <div>
                  <label class="text-xs text-gray-500">{{ isDomestic ? '유효기간' : 'Valid Until' }}</label>
                  <input v-model="form.valid_until" :readonly="!termsEditable"
                    class="w-full border rounded px-2 py-1.5 text-sm"
                    :class="!termsEditable ? 'bg-gray-100 text-gray-600 cursor-not-allowed' : ''" />
                </div>
              </div>
              <!-- 비고 (PDF 하단에 표시. 국내 견적서는 '1. 직인 생략' 기본) -->
              <div class="mt-3">
                <label class="text-xs text-gray-500">{{ isDomestic ? '비고' : 'Remarks' }}</label>
                <textarea v-model="form.remarks" rows="2"
                  placeholder="예) 1. 직인 생략 / 2. …"
                  class="w-full border rounded px-2 py-1.5 text-sm resize-y"></textarea>
              </div>
              <!-- 해외 전용: Bank Details -->
              <div v-if="!isDomestic" class="grid grid-cols-2 gap-3 text-sm mt-3 pt-3 border-t border-gray-200">
                <div>
                  <label class="text-xs text-gray-500">Bank</label>
                  <input v-model="form.bank_name" :readonly="!termsEditable"
                    class="w-full border rounded px-2 py-1.5 text-sm"
                    :class="!termsEditable ? 'bg-gray-100 text-gray-600 cursor-not-allowed' : ''" />
                </div>
                <div>
                  <label class="text-xs text-gray-500">SWIFT Code</label>
                  <input v-model="form.swift_code" :readonly="!termsEditable"
                    class="w-full border rounded px-2 py-1.5 text-sm"
                    :class="!termsEditable ? 'bg-gray-100 text-gray-600 cursor-not-allowed' : ''" />
                </div>
                <div>
                  <label class="text-xs text-gray-500">Account Name</label>
                  <input v-model="form.account_name" :readonly="!termsEditable"
                    class="w-full border rounded px-2 py-1.5 text-sm"
                    :class="!termsEditable ? 'bg-gray-100 text-gray-600 cursor-not-allowed' : ''" />
                </div>
                <div>
                  <label class="text-xs text-gray-500">Account No.</label>
                  <input v-model="form.account_number" :readonly="!termsEditable"
                    class="w-full border rounded px-2 py-1.5 text-sm"
                    :class="!termsEditable ? 'bg-gray-100 text-gray-600 cursor-not-allowed' : ''" />
                </div>
              </div>
            </div>

            <!-- 품목 -->
            <div class="mb-6">
              <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-3">
                  <h4 class="text-sm font-medium text-gray-700">품목</h4>
                  <label v-if="form.document_type === 'QUOTATION'" class="inline-flex items-center gap-1.5 text-xs cursor-pointer select-none"
                    title="켜면 품목별로 단일 가격(가격 1개)과 MOQ 가격표(가격 2개 이상)를 자유롭게 혼합할 수 있습니다.">
                    <input type="checkbox" v-model="form.is_moq" class="w-3.5 h-3.5 rounded" />
                    <span :class="form.is_moq ? 'text-purple-700 font-medium' : 'text-gray-500'">MOQ 가격표</span>
                  </label>
                  <label v-if="form.document_type === 'PI'" class="inline-flex items-center gap-1.5 text-xs cursor-pointer select-none"
                    title="견적서 대용으로 발행한 PI입니다. 체크하면 매출·미수(미실현/미입금) 집계에서 제외됩니다.">
                    <input type="checkbox" v-model="form.is_quote_only" class="w-3.5 h-3.5 rounded" />
                    <span :class="form.is_quote_only ? 'text-orange-600 font-medium' : 'text-gray-500'">견적 대용 (집계 제외)</span>
                  </label>
                </div>
                <div class="flex items-center gap-2">
                  <div class="flex items-center gap-1.5 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                    <label class="text-xs text-amber-800 font-medium">마진율</label>
                    <input v-model.number="marginRate" type="number" min="0" step="0.1"
                      class="w-14 border rounded px-1.5 py-0.5 text-xs text-right" />
                    <span class="text-xs text-amber-800">%</span>
                    <button @click="applyMarginToAll" title="모든 품목에 마진율 일괄 적용"
                      class="ml-1 px-2 py-0.5 text-xs bg-amber-600 text-white rounded hover:bg-amber-700">
                      적용
                    </button>
                  </div>
                  <button @click="addItem" class="px-3 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100">
                    + 품목 추가
                  </button>
                </div>
              </div>

              <!-- ===== 일반 모드 ===== -->
              <template v-if="!form.is_moq">
                <div v-for="(item, idx) in form.items" :key="idx" class="border rounded-lg p-4 mb-3 bg-white relative">
                  <div class="absolute -top-2 -left-2 w-6 h-6 bg-blue-600 text-white text-xs font-bold rounded-full flex items-center justify-center shadow">
                    {{ Number(idx) + 1 }}
                  </div>
                  <!-- 모바일: 세로 스택 / 데스크톱(sm+): 기존 12칸 그리드 -->
                  <div class="flex flex-col gap-3 sm:grid sm:grid-cols-12 sm:gap-3 sm:items-end">
                    <div class="col-span-5 relative">
                      <label class="text-xs text-gray-500 mb-1 block">오더코드</label>
                      <div class="flex gap-1.5">
                        <MarkupEditor v-model="item.product_code" class="flex-1 min-w-0 text-sm" />
                        <button @click="openPartSearch(item)" title="부품 검색"
                          class="px-2.5 py-1.5 text-xs bg-blue-50 text-blue-600 border border-blue-200 rounded hover:bg-blue-100 whitespace-nowrap">
                          검색
                        </button>
                        <button @click="autoFillItem(item)" title="Description + 단가 자동 조합"
                          class="px-2.5 py-1.5 text-xs bg-green-50 text-green-600 border border-green-200 rounded hover:bg-green-100 whitespace-nowrap">
                          자동
                        </button>
                        <button @click="openCalc(item)" title="견적 산출 — 원가·마진·조립비 등 세부 항목 확인/수정"
                          class="px-2.5 py-1.5 text-xs bg-indigo-50 text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-100 whitespace-nowrap">
                          산출
                        </button>
                      </div>
                    </div>
                    <div class="col-span-1">
                      <label class="text-xs text-gray-500 mb-1 block">
                        수량
                        <span v-if="item.quantity_text" class="ml-1 text-[9px] bg-amber-100 text-amber-700 px-1 rounded">TBD</span>
                      </label>
                      <input :value="fieldDisplay(item, 'quantity')" type="text"
                        @input="parseNumericField(item, 'quantity', ($event.target as HTMLInputElement).value)"
                        placeholder="숫자 또는 TBD"
                        class="w-full border rounded px-2 py-1.5 text-sm text-right [appearance:textfield]" />
                    </div>
                    <div class="col-span-1">
                      <label class="text-xs text-gray-500 mb-1 block">단위</label>
                      <select v-model="item.uom" class="w-full border rounded px-2 py-1.5 text-sm text-center">
                        <option v-if="item.uom && !UOM_OPTIONS.includes(item.uom)" :value="item.uom">{{ item.uom }}</option>
                        <option v-for="u in UOM_OPTIONS" :key="u" :value="u">{{ u }}</option>
                      </select>
                    </div>
                    <div class="col-span-2 relative">
                      <label class="text-xs text-gray-500 mb-1 block">
                        단가 ({{ form.currency || 'USD' }})
                        <span v-if="item.unit_price_text" class="ml-1 text-[9px] bg-amber-100 text-amber-700 px-1 rounded">TBD</span>
                      </label>
                      <input :value="fieldDisplay(item, 'unit_price')" type="text"
                        @input="parseNumericField(item, 'unit_price', ($event.target as HTMLInputElement).value)"
                        placeholder="숫자 또는 TBD"
                        class="w-full border rounded px-2 py-1.5 text-sm text-right [appearance:textfield]" />
                      <div v-if="item._basePrice !== undefined && item._basePrice !== null && item._basePrice > 0 && !item.unit_price_text"
                        class="absolute left-0 right-0 top-full text-[10px] text-gray-400 mt-0.5 text-right pr-1">
                        기준가: {{ Number(item._basePrice).toLocaleString() }}
                      </div>
                    </div>
                    <div class="col-span-2">
                      <label class="text-xs text-gray-500 mb-1 block">금액</label>
                      <input :value="item.amount_text || formatItemAmount(item.amount)" disabled class="w-full border rounded px-2 py-1.5 text-sm bg-gray-50 text-right font-medium" />
                    </div>
                    <div class="col-span-1 flex justify-center pb-1">
                      <button @click="removeItem(Number(idx))" class="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded" title="삭제">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  <!-- 이전 견적 힌트: 정상 흐름 전체폭(줄바꿈돼도 Description과 겹치지 않음) -->
                  <div v-if="item._lastPrice" class="mt-2 text-xs"
                    :class="item._priceWarning ? 'text-red-600 font-medium' : 'text-blue-600'">
                    <span v-if="item._priceWarning">⚠ </span>
                    이전 견적: {{ item._lastPrice.currency }} {{ item._lastPrice.unit_price.toLocaleString() }}<span
                      v-if="item._lastPrice.quantity != null"> × {{ item._lastPrice.quantity.toLocaleString() }}{{ item._lastPrice.uom || '' }}</span>
                    ({{ item._lastPrice.document_number }}, {{ item._lastPrice.document_date }})
                    <span v-if="item._priceWarning"> — 현재 단가가 이전보다 높습니다</span>
                  </div>
                  <div :class="(item._basePrice !== undefined && item._basePrice !== null && item._basePrice > 0) ? 'mt-5' : 'mt-3'">
                    <label class="text-xs text-gray-500 mb-1 block">Description</label>
                    <MarkupEditor v-model="item.description" multiline class="text-sm text-gray-700" />
                  </div>
                  <div class="mt-3">
                    <label class="text-xs text-gray-500 mb-1 block">{{ isDomestic ? '비고' : 'Remark' }} <span class="text-gray-400">(문서 표 우측 칼럼에 표시)</span></label>
                    <input v-model="item.line_remarks" type="text" placeholder="특이사항 등"
                      class="w-full border rounded px-2 py-1.5 text-sm" />
                  </div>
                </div>

                <!-- 합계 + 할인/배송비 -->
                <div class="flex justify-end mt-3">
                  <div class="w-72 space-y-1.5 text-sm">
                    <div class="flex justify-between text-gray-500">
                      <span>소계 (Subtotal)</span>
                      <span>{{ form.currency || 'USD' }} {{ formatItemAmount(totalAmount) }}</span>
                    </div>
                    <!-- 할인 -->
                    <div class="flex justify-between items-center">
                      <label class="flex items-center gap-1.5 text-gray-600 cursor-pointer select-none">
                        <input type="checkbox" v-model="form.discount_enabled" class="w-3.5 h-3.5 rounded" />
                        할인 (Discount)
                      </label>
                      <div v-if="form.discount_enabled" class="flex items-center gap-1">
                        <span class="text-red-500">-</span>
                        <input type="number" min="0" step="0.01" v-model.number="form.discount_amount"
                          class="w-24 border rounded px-2 py-1 text-right text-sm focus:ring-2 focus:ring-blue-500" />
                      </div>
                      <span v-else class="text-gray-300">미적용</span>
                    </div>
                    <!-- 할인 사유 (견적서에 기록) -->
                    <div v-if="form.discount_enabled" class="pl-5">
                      <input type="text" maxlength="300" v-model="form.discount_reason"
                        placeholder="할인 사유 (예: 신규거래 1회성 / 대량주문 할인) — 견적서에 기록됨"
                        class="w-full border rounded px-2 py-1 text-xs focus:ring-2 focus:ring-blue-500" />
                    </div>
                    <!-- 배송비 -->
                    <div class="flex justify-between items-center">
                      <label class="flex items-center gap-1.5 text-gray-600 cursor-pointer select-none">
                        <input type="checkbox" v-model="form.shipping_enabled" class="w-3.5 h-3.5 rounded" />
                        배송비 (Shipping)
                      </label>
                      <div v-if="form.shipping_enabled" class="flex items-center gap-1">
                        <span class="text-emerald-600">+</span>
                        <input type="number" min="0" step="0.01" v-model.number="form.shipping_fee"
                          class="w-24 border rounded px-2 py-1 text-right text-sm focus:ring-2 focus:ring-blue-500" />
                      </div>
                      <span v-else class="text-gray-300">미적용</span>
                    </div>
                    <div class="flex justify-between items-center border-t pt-1.5 mt-1">
                      <span class="text-sm font-semibold text-gray-700">TOTAL</span>
                      <span class="text-lg font-bold">{{ form.currency || 'USD' }} {{ formatItemAmount(grandTotal) }}</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- ===== MOQ 가격표 모드 ===== -->
              <template v-else>
                <div v-for="(group, gIdx) in moqGroups" :key="gIdx" class="border border-purple-200 rounded-lg p-4 mb-3 bg-purple-50/30 relative">
                  <div class="absolute -top-2 -left-2 w-6 h-6 bg-purple-600 text-white text-xs font-bold rounded-full flex items-center justify-center shadow">
                    {{ gIdx + 1 }}
                  </div>
                  <div class="flex gap-2 mb-3">
                    <div class="flex-1">
                      <label class="text-xs text-gray-500 mb-1 block">오더코드</label>
                      <div class="flex gap-1.5">
                        <MarkupEditor v-model="group.product_code" class="flex-1 min-w-0 text-sm" />
                        <button @click="openPartSearch(group)" title="부품 검색"
                          class="px-2.5 py-1.5 text-xs bg-blue-50 text-blue-600 border border-blue-200 rounded hover:bg-blue-100 whitespace-nowrap">검색</button>
                        <button @click="autoFillItem(group)" title="자동 조합"
                          class="px-2.5 py-1.5 text-xs bg-green-50 text-green-600 border border-green-200 rounded hover:bg-green-100 whitespace-nowrap">자동</button>
                      </div>
                    </div>
                    <button @click="removeMoqGroup(gIdx)" class="self-end p-1.5 text-red-400 hover:text-red-600 rounded" title="품목 삭제">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                  <div class="mb-3">
                    <label class="text-xs text-gray-500 mb-1 block">Description</label>
                    <MarkupEditor v-model="group.description" multiline class="text-sm" />
                  </div>
                  <!-- 가격 행들 (1개=단일가, 2개 이상=MOQ 구간) -->
                  <div class="mb-2">
                    <div class="flex items-center justify-between mb-1">
                      <span class="text-xs font-medium text-purple-700">
                        가격
                        <span v-if="group.prices.length === 1"
                          class="ml-1 text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">단일가</span>
                        <span v-else
                          class="ml-1 text-[10px] bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">MOQ {{ group.prices.length }}구간</span>
                      </span>
                      <button @click="addMoqPrice(gIdx)" class="text-xs text-purple-600 hover:text-purple-800">+ 가격 추가</button>
                    </div>
                    <div class="space-y-1">
                      <div v-for="(price, pIdx) in group.prices" :key="pIdx" class="flex flex-wrap items-center gap-2">
                        <input :value="fieldDisplay(price, 'quantity')" type="text"
                          @input="parseNumericField(price, 'quantity', ($event.target as HTMLInputElement).value)"
                          placeholder="MOQ 또는 TBD" class="w-24 border rounded px-2 py-1 text-sm text-right [appearance:textfield]" />
                        <select v-model="price.uom" class="w-16 border rounded px-1 py-1 text-sm text-center">
                          <option v-if="price.uom && !UOM_OPTIONS.includes(price.uom)" :value="price.uom">{{ price.uom }}</option>
                          <option v-for="u in UOM_OPTIONS" :key="u" :value="u">{{ u }}</option>
                        </select>
                        <input :value="fieldDisplay(price, 'unit_price')" type="text"
                          @input="parseNumericField(price, 'unit_price', ($event.target as HTMLInputElement).value)"
                          placeholder="단가 또는 TBD" class="w-28 border rounded px-2 py-1 text-sm text-right [appearance:textfield]" />
                        <span class="text-xs text-gray-400">{{ form.currency || 'USD' }}</span>
                        <span v-if="price.quantity_text || price.unit_price_text"
                          class="text-[9px] bg-amber-100 text-amber-700 px-1 rounded">TBD</span>
                        <button v-if="group.prices.length > 1" @click="group.prices.splice(pIdx, 1)"
                          class="text-red-400 hover:text-red-600 text-xs">삭제</button>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="flex justify-between items-center mt-2">
                  <button @click="addMoqGroup" class="px-3 py-1 text-xs bg-purple-50 text-purple-600 rounded hover:bg-purple-100">+ 품목 추가</button>
                  <span class="text-sm text-gray-400">TOTAL: - (MOQ 견적)</span>
                </div>
              </template>
            </div>
          </div>

          <!-- 하단 버튼 -->
          <div class="flex justify-end gap-2 px-6 py-4 border-t bg-gray-50">
            <button @click="$emit('close')" class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">취소</button>
            <button @click="save" :disabled="saving" class="px-6 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
              {{ saving ? '저장 중...' : '저장' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 부품 검색 모달 -->
    <PartSearchForSalesModal
      v-if="showPartSearch"
      @close="showPartSearch = false"
      @select="onPartSelected"
    />

    <!-- 견적 산출 패널 -->
    <QuotePriceCalcModal
      v-if="showCalc && calcItem"
      :order-code="calcItem.product_code"
      :customer-id="form.customer_id || null"
      :currency="form.currency || 'USD'"
      :length="Number(calcItem.length_m) || 0"
      :quantity="Number(calcItem.quantity) || 1"
      @close="showCalc = false"
      @apply="applyCalc"
    />

    <!-- 영업 대응 현황 히스토리 우측 도킹 패널 (데스크톱: 문서 옆 / 모바일: 전체화면 토글) -->
    <SalesActivityDetailModal
      v-if="showActivityPopup && linkedActivity"
      :activity-id="linkedActivity.id"
      dock
      @close="showActivityPopup = false"
      @updated="loadRelatedDocuments"
    />
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { BOX_PRESETS, findBoxPreset } from '@/constants/packingBoxes'

// 단위(uom) 표준 옵션 — 박스 단위 판매(분할선적) 포함. 기존 커스텀 값은 별도 옵션으로 유지
const UOM_OPTIONS = ['pc', 'EA', 'SET', 'M', 'BOX']
// 인코텀즈(드롭다운) + 운임부담(매도인) 조건 — 이 조건들에서 박스당 Freight 입력
const INCOTERMS = ['EXW', 'FCA', 'CPT', 'CIP', 'CFR', 'CIF', 'DAP', 'DDP']
const FREIGHT_TERMS = ['CPT', 'CIP', 'CFR', 'CIF', 'DAP', 'DDP']
// 유효기간 기본값 — 국내(한글)/해외(영문)
const VALID_UNTIL_EN = 'Within a month after issued date'
const VALID_UNTIL_KO = '발행일로부터 1개월 이내'
import { salesDocumentApi, descriptionCodeApi, type SalesDocument, type SalesDocumentItem, type PIProcessStep, type RelatedDocumentsResponse } from '@/api/salesDocument'
import MarkupEditor from '@/components/common/MarkupEditor.vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import apiClient from '@/api/client'
import { openAuthedUrl } from '@/utils/download'
import PartSearchForSalesModal from './PartSearchForSalesModal.vue'
import QuotePriceCalcModal from './QuotePriceCalcModal.vue'
import { partnerApi, type PartnerContact, type PartnerShippingAddress } from '@/api/partner'
import { settingsApi, type CompanyBankAccount } from '@/api/settings'
import SalesActivityDetailModal from '@/views/sales/activity/SalesActivityDetailModal.vue'

// PO 첨부파일 (편집 모드 데이터 로드 시 사용되므로 미리 선언)
const poAttachments = ref<any[]>([])

// 거래처 배송지 (v0.58.0): 문서에서 저장 배송지 선택
const shippingAddresses = ref<PartnerShippingAddress[]>([])
async function loadShippingAddresses(customerId: number) {
  try {
    const res = await partnerApi.getShippingAddresses(customerId)
    shippingAddresses.value = res.data || []
  } catch { shippingAddresses.value = [] }
}
const selectedShipping = computed(() => {
  const v = form.value?.ship_to_choice
  if (!v || v === 'SAME' || v === 'CUSTOM') return null
  return shippingAddresses.value.find(s => String(s.id) === String(v)) || null
})

// 고객사 담당자 (v0.52.0): 문서별 담당자 선택/신규추가
const contacts = ref<PartnerContact[]>([])
const showNewContact = ref(false)
const savingContact = ref(false)
const newContact = ref({ name: '', position: '', email: '', tel_mobile: '' })

async function loadContacts(customerId: number) {
  try {
    const res = await partnerApi.getContacts(customerId)
    contacts.value = res.data || []
  } catch {
    contacts.value = []
  }
}

async function addNewContact() {
  if (!form.value.customer_id) { showToast('고객사를 먼저 선택하세요', 'error'); return }
  if (!newContact.value.name.trim()) { showToast('담당자 이름을 입력하세요', 'error'); return }
  savingContact.value = true
  try {
    const res = await partnerApi.createContact(form.value.customer_id, {
      name: newContact.value.name.trim(),
      position: newContact.value.position.trim() || undefined,
      email: newContact.value.email.trim() || undefined,
      tel_mobile: newContact.value.tel_mobile.trim() || undefined,
    })
    contacts.value.push(res.data)
    form.value.customer_contact_id = res.data.id
    showNewContact.value = false
    newContact.value = { name: '', position: '', email: '', tel_mobile: '' }
    showToast('담당자가 추가되었습니다', 'success')
  } catch (e: any) {
    showToast(e.response?.data?.detail || '담당자 추가 실패', 'error')
  } finally {
    savingContact.value = false
  }
}

// Terms & Bank Details 편집 가능 토글 (기본: 잠금)
const termsEditable = ref(false)

interface Props {
  document?: SalesDocument | null
  documentType: string
  presetCustomerId?: number
  presetActivityId?: number
  copyFromDocId?: number
}
const props = withDefaults(defineProps<Props>(), {
  document: null,
  presetCustomerId: undefined,
  presetActivityId: undefined,
  copyFromDocId: undefined,
})
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
  (e: 'navigate', payload: { docId: number; docType: string }): void
}>()
const { showToast } = useToast()

const isEdit = computed(() => !!props.document?.id)
const documentVersion = computed(() => props.document?.version || 1)
const _userInfo = JSON.parse(localStorage.getItem('user') || '{}')
const loggedInUserName = _userInfo?.name || ''
const loggedInUserNameEn = _userInfo?.name_en || ''
const loggedInUserEmail = _userInfo?.email || ''

// HS Code 프리셋 (Fix #3)
const HS_CONNECTOR = '8536.70-1000'  // 커넥터류
const HS_CABLE = '8544.70-0000'      // 케이블 조립체
const HS_BOTH = `${HS_CONNECTOR}, ${HS_CABLE}`  // 커넥터+조립체 동시 출고(복수 HS Code)
type HsPreset = 'connector' | 'cable' | 'both' | 'custom'
const typeLabel = computed(() => {
  if (isDomestic.value) {
    return { QUOTATION: '견적서', PI: '발주확인서', CI: '거래명세서' }[props.documentType] || props.documentType
  }
  return { QUOTATION: '견적서 (Quotation)', PI: 'PI (Proforma Invoice)', CI: 'CI (Commercial Invoice)' }[props.documentType] || props.documentType
})

const saving = ref(false)
const customers = ref<{ id: number; partner_name: string; partner_name_en?: string }[]>([])
const customerSearch = ref('')
const showCustomerDropdown = ref(false)
const highlightedIndex = ref(0)

function moveHighlight(delta: number) {
  const list = filteredCustomers.value
  if (list.length === 0) return
  highlightedIndex.value = (highlightedIndex.value + delta + list.length) % list.length
}

function handleEnter() {
  const list = filteredCustomers.value
  if (list.length === 1) { selectCustomer(list[0]!); return }
  if (list.length > 0 && highlightedIndex.value >= 0) {
    selectCustomer(list[highlightedIndex.value]!)
  }
}

function hideCustomerDropdownDelayed() { setTimeout(() => { showCustomerDropdown.value = false }, 200) }

const filteredCustomers = computed(() => {
  if (!customerSearch.value) return customers.value
  const q = customerSearch.value.toLowerCase()
  return customers.value.filter(c =>
    c.partner_name.toLowerCase().includes(q) ||
    (c.partner_name_en && c.partner_name_en.toLowerCase().includes(q))
  )
})

const selectedCustomerName = computed(() => {
  if (!form.value.customer_id) return ''
  const c = customers.value.find(c => c.id === form.value.customer_id)
  return c?.partner_name || ''
})

function selectCustomer(c: { id: number; partner_name: string }) {
  form.value.customer_id = c.id
  customerSearch.value = c.partner_name
  showCustomerDropdown.value = false
  onCustomerChange()
}

function clearCustomer() {
  form.value.customer_id = undefined
  form.value.customer_contact_id = undefined
  customerSearch.value = ''
  contacts.value = []
  showNewContact.value = false
}

const form = ref<any>({
  document_type: props.documentType,
  document_date: new Date().toISOString().split('T')[0],
  customer_id: undefined,
  customer_contact_id: undefined,
  sales_activity_id: props.presetActivityId,
  prepared_by: loggedInUserName,
  prepared_email: loggedInUserEmail,
  payment_terms: '',
  delivery_terms: '',
  incoterms: '',
  freight_per_box: null,
  show_customer_tax_id: false,
  show_statement_of_origin: false,
  hs_code: '',
  remarks: '',
  valid_until: VALID_UNTIL_EN,
  bank_name: 'KEB HANA BANK, HEAD OFFICE',
  bank_address: '35, EULJI-RO, JUNG-GU, SEOUL, KOREA',
  swift_code: 'KOEXKRSE',
  account_name: 'XBEAMTECH CO., LTD.',
  account_number: '332-910005-81138',
  country_of_origin: 'Republic of Korea',
  currency: 'USD',
  is_moq: false,
  is_quote_only: false,
  // 할인/배송비 (체크 시 입력 → 총액 반영)
  discount_enabled: false,
  discount_amount: 0,
  discount_reason: '',
  shipping_enabled: false,
  shipping_fee: 0,
  // 수령자(Ship-To): 'SAME'(구매자와 동일) / '<id>'(저장배송지) / 'CUSTOM'(직접입력)
  ship_to_choice: 'SAME',
  ship_to_address_id: undefined,
  ship_to_name: '',
  ship_to_address: '',
  ship_to_contact: '',
  ship_to_phone: '',
  ship_to_email: '',
  // CI 전용: 선적 정보 · 포장 명세
  ship_from: 'Seoul, Korea',
  destination: '',
  transportation: '',
  shipment_date: '',
  packaging_boxes: undefined as number | undefined,
  packaging_dimensions: '',
  packaging_gross_weight: undefined as number | undefined,
  packaging_net_weight: undefined as number | undefined,
  packing_list: [] as Array<{ box_type?: string; quantity?: number | null; gross_weight?: number | null; net_weight?: number | null; length?: number | null; width?: number | null; height?: number | null; remarks?: string }>,
  items: [{ line_no: 1, product_code: '', description: '', line_remarks: '', quantity: 1, uom: 'pc', unit_price: 0, amount: 0, currency: 'USD' }],
})

function addCiBox() {
  form.value.packing_list.push({ box_type: '', quantity: 1, gross_weight: null, net_weight: null, length: null, width: null, height: null })
}
function removeCiBox(i: number | string) {
  form.value.packing_list.splice(Number(i), 1)
}
// 박스 종류 선택 시 프리셋이면 L·W·H 자동입력(무게 수기 유지)
function onCiBoxSelect(b: { box_type?: string; length?: number | null; width?: number | null; height?: number | null }) {
  const p = findBoxPreset(b.box_type)
  if (p) { b.length = p.l; b.width = p.w; b.height = p.h }
}

// packing list → 저장 페이로드(요약값 재산출 포함)
function buildPackingPayload() {
  const rows = (form.value.packing_list || []).filter((b: any) =>
    b.box_type || b.gross_weight || b.net_weight || b.length || b.width || b.height || b.remarks
  )
  const num = (v: any) => (v === '' || v == null ? null : Number(v))
  const packing_list = rows.map((b: any) => ({
    box_type: (b.box_type || '').trim() || null,
    quantity: Number(b.quantity) || 1,
    gross_weight: num(b.gross_weight),
    net_weight: num(b.net_weight),
    length: num(b.length),
    width: num(b.width),
    height: num(b.height),
    remarks: (b.remarks || '').trim() || null,
  }))
  if (packing_list.length === 0) {
    return { packing_list: null, packaging_boxes: null, packaging_gross_weight: null, packaging_net_weight: null, packaging_dimensions: null }
  }
  let boxes = 0, gross = 0, net = 0
  for (const b of packing_list) {
    const q = b.quantity || 1
    boxes += q
    if (b.gross_weight != null) gross += b.gross_weight * q
    if (b.net_weight != null) net += b.net_weight * q
  }
  const one = packing_list[0]
  const dims = packing_list.length === 1 && one.length != null && one.width != null && one.height != null
    ? `${one.length} x ${one.width} x ${one.height}` : null
  return {
    packing_list,
    packaging_boxes: boxes || null,
    packaging_gross_weight: gross ? Math.round(gross * 100) / 100 : null,
    packaging_net_weight: net ? Math.round(net * 100) / 100 : null,
    packaging_dimensions: dims,
  }
}

// MOQ 가격표 모드
const moqGroups = ref<any[]>([
  { product_code: '', description: '', prices: [{ quantity: 0, uom: 'pc', unit_price: 0 }] }
])

function addMoqGroup() {
  moqGroups.value.push({ product_code: '', description: '', prices: [{ quantity: 0, uom: 'pc', unit_price: 0 }] })
}

function removeMoqGroup(idx: number) {
  if (moqGroups.value.length <= 1) return
  moqGroups.value.splice(idx, 1)
}

function addMoqPrice(groupIdx: number) {
  moqGroups.value[groupIdx].prices.push({ quantity: 0, uom: 'pc', unit_price: 0 })
}

function moqGroupsToItems() {
  const items: any[] = []
  // line_no = 그룹 인덱스(같은 MOQ 그룹 내 여러 수량 구간은 동일 line_no).
  // 편집 시 itemsToMoqGroups가 line_no로 그룹핑하므로 이 형태가 필요.
  // PDF 출력 시에는 mapper가 1,2,3 순차로 다시 부여한다.
  moqGroups.value.forEach((group, gIdx) => {
    const lineNo = gIdx + 1
    group.prices.forEach((p: any) => {
      const qty = Number(p.quantity) || 0
      const up = Number(p.unit_price) || 0
      const hasTbd = p.quantity_text || p.unit_price_text
      items.push({
        line_no: lineNo,
        product_code: group.product_code,
        description: group.description,
        quantity: qty,
        quantity_text: p.quantity_text || null,
        uom: p.uom || 'pc',
        unit_price: up,
        unit_price_text: p.unit_price_text || null,
        amount: hasTbd ? 0 : Math.round(qty * up * 100) / 100,
        amount_text: hasTbd ? 'TBD' : null,
        currency: form.value.currency,
      })
    })
  })
  return items
}

function itemsToMoqGroups(items: any[]) {
  const groups: Record<number, any> = {}
  items.forEach((item: any) => {
    const ln = item.line_no || 1
    if (!groups[ln]) {
      groups[ln] = { product_code: item.product_code, description: item.description, prices: [] }
    }
    groups[ln].prices.push({
      quantity: Number(item.quantity) || 0,
      quantity_text: item.quantity_text || null,
      uom: item.uom || 'pc',
      unit_price: Number(item.unit_price) || 0,
      unit_price_text: item.unit_price_text || null,
    })
  })
  const result = Object.values(groups)
  return result.length > 0 ? result : [{ product_code: '', description: '', prices: [{ quantity: 0, uom: 'pc', unit_price: 0 }] }]
}

// 편집 모드: 기존 데이터 로드
if (props.document) {
  const d = props.document
  poAttachments.value = (d as any).po_attachment_files || []
  form.value = {
    ...form.value,
    document_date: d.document_date,
    customer_id: d.customer_id,
    customer_contact_id: (d as any).customer_contact_id ?? undefined,
    sales_activity_id: (d as any).sales_activity_id || undefined,
    prepared_by: d.prepared_by || '',
    prepared_email: d.prepared_email || '',
    payment_terms: d.payment_terms || '',
    delivery_terms: d.delivery_terms || '',
    incoterms: (d as any).incoterms || '',
    freight_per_box: (d as any).freight_per_box != null ? Number((d as any).freight_per_box) : null,
    show_customer_tax_id: (d as any).show_customer_tax_id || false,
    show_statement_of_origin: (d as any).show_statement_of_origin || false,
    hs_code: d.hs_code || '',
    valid_until: d.valid_until || '',
    bank_name: d.bank_name || '',
    bank_address: d.bank_address || '',
    swift_code: d.swift_code || '',
    account_name: d.account_name || '',
    account_number: d.account_number || '',
    country_of_origin: d.country_of_origin || '',
    currency: d.currency || 'USD',
    is_moq: (d as any).is_moq || false,
    is_quote_only: (d as any).is_quote_only || false,
    // 할인/배송비: 값(≠null)이 있으면 체크 상태로 복원
    discount_enabled: (d as any).discount_amount != null,
    discount_amount: Number((d as any).discount_amount) || 0,
    discount_reason: (d as any).discount_reason || '',
    shipping_enabled: (d as any).shipping_fee != null,
    shipping_fee: Number((d as any).shipping_fee) || 0,
    // 수령자: 저장배송지 id 있으면 그 값, 직접입력 값 있으면 CUSTOM, 아니면 SAME
    ship_to_choice: (d as any).ship_to_address_id
      ? String((d as any).ship_to_address_id)
      : (((d as any).ship_to_name || (d as any).ship_to_address || (d as any).ship_to_contact || (d as any).ship_to_phone || (d as any).ship_to_email) ? 'CUSTOM' : 'SAME'),
    ship_to_address_id: (d as any).ship_to_address_id ?? undefined,
    ship_to_name: (d as any).ship_to_name || '',
    ship_to_address: (d as any).ship_to_address || '',
    ship_to_contact: (d as any).ship_to_contact || '',
    ship_to_phone: (d as any).ship_to_phone || '',
    ship_to_email: (d as any).ship_to_email || '',
    // CI 전용: 선적 정보 · 포장 명세
    ship_from: (d as any).ship_from || '',
    destination: (d as any).destination || '',
    transportation: (d as any).transportation || '',
    shipment_date: ((d as any).shipment_date || '').slice(0, 10),
    packaging_boxes: (d as any).packaging_boxes ?? undefined,
    packaging_dimensions: (d as any).packaging_dimensions || '',
    packaging_gross_weight: (d as any).packaging_gross_weight ?? undefined,
    packaging_net_weight: (d as any).packaging_net_weight ?? undefined,
    packing_list: Array.isArray((d as any).packing_list)
      ? (d as any).packing_list.map((b: any) => ({
          box_type: b.box_type || '',
          quantity: b.quantity ?? 1,
          gross_weight: b.gross_weight ?? null,
          net_weight: b.net_weight ?? null,
          length: b.length ?? null,
          width: b.width ?? null,
          height: b.height ?? null,
          remarks: b.remarks || '',
        }))
      : [],
    remarks: d.remarks || '',
    // 백엔드 Numeric 필드는 문자열("2.000")로 직렬화되므로 숫자로 강제 변환
    // *_text 오버라이드도 함께 보존
    items: d.items?.length
      ? d.items.map((i: any) => ({
          ...i,
          quantity: Number(i.quantity) || 0,
          quantity_text: i.quantity_text || null,
          unit_price: Number(i.unit_price) || 0,
          unit_price_text: i.unit_price_text || null,
          amount: Number(i.amount) || 0,
          amount_text: i.amount_text || null,
        }))
      : form.value.items,
  }
  // MOQ 모드면 items → moqGroups 변환
  if (form.value.is_moq && d.items?.length) {
    moqGroups.value = itemsToMoqGroups(d.items)
  }
  // 편집 시 고객명 초기화
  if (d.customer) {
    customerSearch.value = d.customer.partner_name
  }
}

const totalAmount = computed(() => form.value.items.reduce((sum: number, i: any) => sum + (Number(i.amount) || 0), 0))
// 할인/배송비 반영 최종 총액 (소계 - 할인 + 배송비, 음수면 0)
const grandTotal = computed(() => {
  const disc = form.value.discount_enabled ? (Number(form.value.discount_amount) || 0) : 0
  const ship = form.value.shipping_enabled ? (Number(form.value.shipping_fee) || 0) : 0
  const t = totalAmount.value - disc + ship
  return t > 0 ? t : 0
})

// HS Code 프리셋 — 부품코드에서 HXB##AS 패턴 감지 → 케이블 조립체
// (Fix #3) 직접입력 / 커넥터류 / 케이블 조립체 선택 + 품목 변경 시 자동 감지
const PATTERN_CABLE_ASSEMBLY = /HXB\d+AS/i
function detectHsPresetFromItems(items: any[]): 'connector' | 'cable' | 'both' {
  const codes = (items || []).map((it) => String(it?.product_code || ''))
  const hasCable = codes.some((c) => PATTERN_CABLE_ASSEMBLY.test(c))
  const hasConnector = codes.some((c) => c && !PATTERN_CABLE_ASSEMBLY.test(c))
  if (hasCable && hasConnector) return 'both'   // 조립체+커넥터 동시 → HS Code 두 개
  return hasCable ? 'cable' : 'connector'
}
function hsPresetOf(value: string): HsPreset {
  if (value === HS_BOTH) return 'both'
  if (value === HS_CONNECTOR) return 'connector'
  if (value === HS_CABLE) return 'cable'
  return 'custom'
}
const currentHsPreset = computed<HsPreset>(() => hsPresetOf(form.value.hs_code))
function applyHsPreset(p: HsPreset) {
  if (p === 'connector') form.value.hs_code = HS_CONNECTOR
  else if (p === 'cable') form.value.hs_code = HS_CABLE
  else if (p === 'both') form.value.hs_code = HS_BOTH
  // 'custom' — 현재 값 유지하고 사용자 직접 편집
}
// 품목 변경 시 자동 감지 — 현재 값이 비었거나 다른 프리셋이면 갱신,
// 사용자가 커스텀으로 입력한 값은 보존
watch(
  () => form.value.items?.map((i: any) => i?.product_code || '').join('|'),
  () => {
    if (currentHsPreset.value === 'custom' && form.value.hs_code) return
    const detected = detectHsPresetFromItems(form.value.items)
    applyHsPreset(detected)
  }
)

// 거래 유형 (고객사 기준)
const tradeType = ref<string>('EXPORT')
const isDomestic = computed(() => tradeType.value === 'DOMESTIC')

// 편집 로드 시 onCustomerChange(고객 선택 시에만 실행)가 안 돌아 tradeType이 기본값(EXPORT)로
// 남는 문제 보정 — 이미 복원된 통화(KRW=국내)로 국내/해외 판정. isDomestic 정상화로
// 자동 Description 한글 생성·국내 라벨·은행정보 처리가 편집 시에도 올바르게 동작.
if (props.document && form.value.currency === 'KRW') {
  tradeType.value = 'DOMESTIC'
  // 기존 국내 문서가 영문 유효기간 기본값을 갖고 있으면 한글로 정정(사용자 지정값은 보존)
  if (form.value.valid_until === VALID_UNTIL_EN) {
    form.value.valid_until = VALID_UNTIL_KO
  }
}

// 회사 은행 계좌(통화별) — 관리자 설정에서 로드해 신규 문서에 통화별 계좌 자동 프리필
const bankAccounts = ref<CompanyBankAccount[]>([])
function bankAccountFor(cur: string): CompanyBankAccount | null {
  const c = (cur || '').toUpperCase()
  return bankAccounts.value.find(a => (a.currency || '').toUpperCase() === c)
      || bankAccounts.value.find(a => a.is_default)
      || bankAccounts.value[0] || null
}
function applyBankForCurrency(cur: string) {
  if (isEdit.value) return        // 편집: 저장된 스냅샷 유지(원본 보존)
  if (isDomestic.value) return    // 국내: 은행정보 미표기(별도 클리어 로직 유지)
  const a = bankAccountFor(cur)
  if (!a) return
  form.value.bank_name = a.bank_name || ''
  form.value.bank_address = a.bank_address || ''
  form.value.swift_code = a.swift_code || ''
  form.value.account_name = a.account_name || ''
  form.value.account_number = a.account_number || ''
}
// 신규 문서에서 통화 변경 시 계좌 자동 반영
watch(() => form.value.currency, (cur) => {
  if (!isEdit.value && !isDomestic.value) applyBankForCurrency(cur)
})

// 고객사 변경 → 정보 자동 로드
async function onCustomerChange() {
  if (!form.value.customer_id) return
  // 담당자 목록 로드 + 신규 선택 시 기본 담당자(primary) 자동 선택
  await loadContacts(form.value.customer_id)
  await loadShippingAddresses(form.value.customer_id)
  if (!isEdit.value) {
    const primary = contacts.value.find(c => c.is_primary) || contacts.value[0]
    form.value.customer_contact_id = primary ? primary.id : undefined
    // 거래처 바뀌면 배송지 선택 초기화(구매자와 동일)
    form.value.ship_to_choice = 'SAME'
  }
  try {
    const res = await salesDocumentApi.getCustomerDefaults(form.value.customer_id)
    const d = res.data

    // 거래 유형 설정
    tradeType.value = d.trade_type || 'EXPORT'

    // 통화 + 작성자 이름 자동 분기
    if (!isEdit.value) {
      form.value.currency = isDomestic.value ? 'KRW' : 'USD'
      // 국내 견적서: 비고 기본값 '1. 직인 생략'(비어있을 때만) — 필요 시 추가 작성
      if (isDomestic.value && form.value.document_type === 'QUOTATION' && !(form.value.remarks || '').trim()) {
        form.value.remarks = '1. 직인 생략'
      }
      // 국내 → 한글 이름, 해외 → 영문 이름
      form.value.prepared_by = isDomestic.value
        ? loggedInUserName
        : (loggedInUserNameEn || loggedInUserName)
    }

    if (d.payment_terms) form.value.payment_terms = d.payment_terms
    if (d.delivery_terms) form.value.delivery_terms = d.delivery_terms
    if (d.hs_code) form.value.hs_code = d.hs_code
    // 원산지 신고문: 거래처 기본값 프리필(신규 작성 시)
    if (!isEdit.value && (d as any).show_statement_of_origin !== undefined) {
      form.value.show_statement_of_origin = !!(d as any).show_statement_of_origin
    }

    // 국내 고객: 은행 정보 불필요 (클리어) + 유효기간 기본값 한글화
    if (isDomestic.value) {
      form.value.bank_name = ''
      form.value.bank_address = ''
      form.value.swift_code = ''
      form.value.account_name = ''
      form.value.account_number = ''
      form.value.hs_code = ''
      form.value.country_of_origin = ''
      // 유효기간: 영문 기본값이거나 비었을 때만 한글 기본값으로(사용자 지정값 보존)
      if (!form.value.valid_until || form.value.valid_until === VALID_UNTIL_EN) {
        form.value.valid_until = VALID_UNTIL_KO
      }
    } else {
      // 해외: 회사 은행 계좌(통화별, 관리자 설정)에서 자동 반영 — 하드코딩/거래처값 대신
      applyBankForCurrency(form.value.currency)
      // 해외로 전환 시 한글 기본값이면 영문 기본값으로 되돌림
      if (!form.value.valid_until || form.value.valid_until === VALID_UNTIL_KO) {
        form.value.valid_until = VALID_UNTIL_EN
      }
    }

    if (d.default_margin_rate) marginRate.value = d.default_margin_rate
    showToast(`고객 정보 로드됨 (${isDomestic.value ? '국내' : '해외'}, 마진율: ${marginRate.value}%)`, 'success')
  } catch { /* ignore */ }
}

// 마진율 (고객사에서 로드, 수동 변경 가능)
const marginRate = ref(0)

// 금액 표시 포맷 (천단위 콤마, 소수점 둘째자리까지 반올림)
function formatItemAmount(amount: number | undefined): string {
  if (amount === undefined || amount === null || isNaN(amount)) return '0'
  // 부동소수점 오차 제거를 위해 명시적 반올림
  const rounded = Math.round(Number(amount) * 100) / 100
  return rounded.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

// 수량 변경: 정수로 강제 후 금액 재계산 (text 오버라이드 없는 경우만)
function onQuantityInput(item: any) {
  if (item.quantity_text) { calcAmount(item); return }
  if (item.quantity != null) {
    item.quantity = Math.max(1, Math.floor(Number(item.quantity) || 1))
  }
  calcAmount(item)
}

// TBD 등 비숫자 입력 처리: 숫자면 수치로, 비숫자면 *_text 오버라이드로 저장
function parseNumericField(item: any, field: 'quantity' | 'unit_price', raw: string) {
  const trimmed = String(raw ?? '').trim()
  const textKey = `${field}_text`
  if (trimmed === '') {
    item[field] = field === 'quantity' ? 1 : 0
    item[textKey] = null
  } else {
    const cleaned = trimmed.replace(/,/g, '')
    const num = Number(cleaned)
    if (cleaned !== '' && !Number.isNaN(num) && Number.isFinite(num)) {
      item[field] = field === 'quantity' ? Math.max(1, Math.floor(num)) : num
      item[textKey] = null
    } else {
      item[field] = 0
      item[textKey] = trimmed
    }
  }
  calcAmount(item)
}

// 입력란 표시값: 텍스트 오버라이드 있으면 그것을, 없으면 수치
function fieldDisplay(item: any, field: 'quantity' | 'unit_price'): string {
  const textKey = `${field}_text`
  if (item[textKey]) return item[textKey]
  const v = item[field]
  if (v === undefined || v === null || v === '') return ''
  // 단가는 천단위 콤마로 표시(입력 파싱 시 parseNumericField가 콤마 제거)
  if (field === 'unit_price') {
    const n = Number(v)
    return isNaN(n) ? String(v) : n.toLocaleString('en-US', { maximumFractionDigits: 2 })
  }
  return String(v)
}

// 마진 일괄 적용: 모든 품목의 현재 단가를 기준가로 저장하고 마진 적용
function applyMarginToAll() {
  if (marginRate.value < 0) {
    showToast('마진율은 0 이상이어야 합니다', 'error')
    return
  }
  if (form.value.items.length === 0) {
    showToast('품목이 없습니다', 'warning')
    return
  }

  const rate = Number(marginRate.value) || 0
  let applied = 0
  form.value.items.forEach((item: any) => {
    // 기준가가 없으면 현재 단가를 기준가로 저장
    if (item._basePrice === undefined || item._basePrice === null) {
      item._basePrice = Number(item.unit_price) || 0
    }
    const basePrice = Number(item._basePrice) || 0
    if (basePrice > 0) {
      const marked = Math.round(basePrice * (1 + rate / 100) * 100) / 100
      item.unit_price = marked
      calcAmount(item)
      applied++
    }
  })

  if (applied > 0) {
    showToast(`${applied}개 품목에 마진 ${rate}% 적용 완료`, 'success')
  } else {
    showToast('적용 가능한 품목이 없습니다. 먼저 기준 단가를 입력하세요.', 'warning')
  }
}

// 개별 품목에 마진 재적용 (기준가 리셋 후)
function resetBasePrice(item: any) {
  item._basePrice = Number(item.unit_price) || 0
  showToast(`기준가를 ${item._basePrice.toLocaleString()}로 재설정`, 'info')
}

// 부품 검색 모달
const showPartSearch = ref(false)
const searchTargetItem = ref<any>(null)

function openPartSearch(item: any) {
  searchTargetItem.value = item
  showPartSearch.value = true
}

async function onPartSelected(part: any) {
  if (!searchTargetItem.value) return
  const item = searchTargetItem.value
  // v0.79.0: 전속(독점) 계약 경고 — 이 부품이 다른 고객 전속이면 안내(영업문서는 자유텍스트라 차단 대신 경고)
  if (part.is_protected && part.protected_customer_id && part.protected_customer_id !== form.value.customer_id) {
    const cn = part.protected_customer?.partner_name || '지정 고객'
    showToast(`🔒 전속(독점) 계약 품목: ${cn} 전속입니다. 이 고객 문서에 넣는지 확인하세요.`, 'warning')
  }
  // 부품 정보를 라인에 채움 (레벨 접미사 [X] 제거)
  const rawCode = part.part_number_display || part.part_number || ''
  item.product_code = rawCode.replace(/\s*\[[A-Z]\]\s*$/, '').trim()
  if (part.standard_price && part.standard_price > 0) {
    item.unit_price = Number(part.standard_price)
    calcAmount(item)
  }
  showPartSearch.value = false
  searchTargetItem.value = null
  // 자동 채움 실행 (description 매핑 + 이전 가격 조회)
  await autoFillItem(item)
}

// 자동 채움: Description + BOM 원가 + 마진 적용 단가
async function autoFillItem(item: any) {
  if (!item.product_code) return

  // 1. Description 자동 조합
  try {
    const res = await descriptionCodeApi.compose(item.product_code, isDomestic.value ? 'ko' : 'en')
    const composedDesc = res.data?.description || ''
    const matchedSegments = res.data?.segments || []
    const unmatched = res.data?.unmatched || []

    if (composedDesc && composedDesc.trim()) {
      item.description = composedDesc
      if (unmatched.length > 0) {
        showToast(`일부 매칭 실패: ${unmatched.join(', ')}`, 'warning')
      } else {
        showToast('Description 자동 조합 완료', 'success')
      }
    } else {
      // 매칭 결과가 없어도 기존 description 유지
      showToast(`매칭된 코드가 없습니다 (미매칭: ${unmatched.join(', ') || '없음'})`, 'warning')
    }
  } catch (err: any) {
    console.error('description compose error:', err)
    showToast('Description 자동 조합에 실패했습니다', 'error')
  }

  // 2. 부품 검색 → BOM 원가 조회
  try {
    // part_number_display로 검색 (하이픈 포함)
    const partsRes = await apiClient.get('/parts', { params: { keyword: item.product_code, limit: 5 } })
    const parts = partsRes.data.items || partsRes.data
    if (!parts || parts.length === 0) {
      showToast('해당 오더코드의 부품을 찾을 수 없습니다', 'warning')
      return
    }

    const part = parts[0]

    // BOM 원가 조회
    const costRes = await apiClient.get(`/prices/parts/${part.id}/bom-cost`)
    const costData = costRes.data
    const totalCost = costData.total_cost || costData.material_cost || part.calculated_cost || part.standard_price || 0

    if (totalCost > 0 && marginRate.value > 0) {
      const suggestedPrice = Math.round(totalCost * (1 + marginRate.value / 100) * 100) / 100
      item.unit_price = suggestedPrice
      item.amount = Math.round(suggestedPrice * (item.quantity || 1) * 100) / 100
      item._costInfo = { cost: totalCost, suggested: suggestedPrice, currency: costData.currency || 'KRW' }
      showToast(`원가 ${totalCost.toLocaleString()} + 마진 ${marginRate.value}% → 단가 ${suggestedPrice.toLocaleString()}`, 'success')
    } else if (totalCost > 0) {
      item._costInfo = { cost: totalCost, suggested: totalCost, currency: costData.currency || 'KRW' }
      showToast(`원가: ${totalCost.toLocaleString()} (마진율 미설정 — 거래처에 마진율을 설정하세요)`, 'warning')
    } else {
      showToast('BOM 원가 정보가 없습니다. 수동으로 단가를 입력하세요.', 'warning')
    }
  } catch {
    // BOM 원가 조회 실패 시 Description만 적용
  }

  // 3. 이전 견적 가격 조회
  if (form.value.customer_id && item.product_code) {
    try {
      const lastRes = await salesDocumentApi.getLastQuotedPrice(form.value.customer_id, item.product_code)
      const lastData = lastRes.data
      if (lastData.found) {
        item._lastPrice = lastData
        // 현재 단가가 이전보다 높으면 경고
        if (item.unit_price > 0 && lastData.unit_price && item.unit_price > lastData.unit_price) {
          item._priceWarning = true
        } else {
          item._priceWarning = false
        }
      }
    } catch { /* 이전 이력 없으면 무시 */ }
  }
}

// 금액 계산 + 이전 가격 대비 경고 업데이트
// 견적 산출 패널
const showCalc = ref(false)
const calcItem = ref<any>(null)
function openCalc(item: any) {
  if (!item.product_code) { showToast('오더코드를 먼저 입력하세요', 'warning'); return }
  calcItem.value = item
  showCalc.value = true
}
function applyCalc(payload: { unit_price: number; currency: string }) {
  const item = calcItem.value
  if (!item) return
  item.unit_price = payload.unit_price
  item.unit_price_text = null
  item._basePrice = payload.unit_price
  calcAmount(item)
  showCalc.value = false
  showToast(`산출 단가 ${payload.currency} ${payload.unit_price.toLocaleString()} 적용`, 'success')
}

// 수량/단가 중 하나라도 TBD(텍스트 오버라이드)면 amount_text='TBD'로 설정하고 수치는 0
function calcAmount(item: any) {
  if (item.quantity_text || item.unit_price_text) {
    item.amount = 0
    item.amount_text = 'TBD'
    item._priceWarning = false
    return
  }
  item.amount_text = null
  const qty = Number(item.quantity) || 0
  const price = Number(item.unit_price) || 0
  item.amount = Math.round(qty * price * 100) / 100
  if (item._lastPrice && price > 0) {
    item._priceWarning = price > item._lastPrice.unit_price
  }
}

function addItem() {
  form.value.items.push({
    line_no: form.value.items.length + 1,
    product_code: '', description: '', line_remarks: '', quantity: 1, uom: 'pc', unit_price: 0, amount: 0, currency: form.value.currency,
  })
}

function removeItem(idx: number) {
  form.value.items.splice(idx, 1)
  form.value.items.forEach((item: any, i: number) => { item.line_no = i + 1 })
}

async function save() {
  if (!form.value.customer_id) { showToast('고객사를 선택하세요', 'error'); return }

  // MOQ 모드: moqGroups → items 변환
  let itemsForSave: any[]
  if (form.value.is_moq) {
    itemsForSave = moqGroupsToItems()
    if (itemsForSave.length === 0) { showToast('MOQ 가격을 입력하세요', 'error'); return }
  } else {
    if (form.value.items.length === 0) { showToast('품목을 추가하세요', 'error'); return }
    // 빈 정수 정규화 — Pydantic이 빈 문자열을 정수로 거부함
    // 숫자 문자열("2.000")도 허용 (백엔드 Numeric 직렬화 대응)
    const _num = (v: any, dflt = 0) => {
      if (v === '' || v === null || v === undefined) return dflt
      const n = typeof v === 'number' ? v : Number(v)
      return Number.isNaN(n) ? dflt : n
    }
    itemsForSave = form.value.items.map((i: any, idx: number) => ({
      line_no: idx + 1,
      product_code: i.product_code,
      description: i.description,
      quantity: _num(i.quantity),
      quantity_text: i.quantity_text || null,
      uom: i.uom || 'pc',
      unit_price: _num(i.unit_price),
      unit_price_text: i.unit_price_text || null,
      amount: _num(i.amount),
      amount_text: i.amount_text || null,
      line_remarks: i.line_remarks || null,
      currency: form.value.currency,
    }))
  }

  saving.value = true
  try {
    // 수령자 3갈래: SAME(구매자와 동일) / 저장배송지(id) / CUSTOM(직접입력)
    const { ship_to_choice, ...formRest } = form.value
    const emptyShipTo = { ship_to_address_id: null, ship_to_name: null, ship_to_address: null, ship_to_contact: null, ship_to_phone: null, ship_to_email: null }
    let shipTo
    if (ship_to_choice === 'CUSTOM') {
      shipTo = {
        ship_to_address_id: null,
        ship_to_name: form.value.ship_to_name?.trim() || null,
        ship_to_address: form.value.ship_to_address?.trim() || null,
        ship_to_contact: form.value.ship_to_contact?.trim() || null,
        ship_to_phone: form.value.ship_to_phone?.trim() || null,
        ship_to_email: form.value.ship_to_email?.trim() || null,
      }
    } else if (ship_to_choice && ship_to_choice !== 'SAME') {
      shipTo = { ...emptyShipTo, ship_to_address_id: Number(ship_to_choice) }  // 저장 배송지 선택
    } else {
      shipTo = emptyShipTo  // Same as Buyer
    }
    const payload = {
      ...formRest,
      ...shipTo,
      total_amount: form.value.is_moq ? 0 : grandTotal.value,
      // 체크 해제 시 null(미적용) — 백엔드가 총액을 소계-할인+배송비로 재계산
      discount_amount: form.value.discount_enabled ? (Number(form.value.discount_amount) || 0) : null,
      discount_reason: form.value.discount_enabled ? (form.value.discount_reason?.trim() || null) : null,
      shipping_fee: form.value.shipping_enabled ? (Number(form.value.shipping_fee) || 0) : null,
      // Incoterms/박스당 운임: 빈 값 정규화
      incoterms: form.value.incoterms?.trim() || null,
      freight_per_box: (form.value.freight_per_box != null && form.value.freight_per_box !== '')
        ? Number(form.value.freight_per_box) : null,
      // CI 선적/포장: 빈 값은 null로 정규화(빈 문자열 date는 백엔드 422 방지)
      shipment_date: form.value.shipment_date || null,
      ship_from: form.value.ship_from?.trim() || null,
      destination: form.value.destination?.trim() || null,
      transportation: form.value.transportation?.trim() || null,
      // packing list(박스별) + 요약값 재산출
      ...buildPackingPayload(),
      items: itemsForSave,
    }

    if (isEdit.value) {
      const doc = props.document!

      const res = await salesDocumentApi.update(doc.id, payload)
      const newDoc = res.data
      if (newDoc) {
        showToast(`수정본이 새 문서번호 ${newDoc.document_number}로 저장되었습니다 (원본 보존)`, 'success')
      }
    } else {
      await salesDocumentApi.create(payload)
      showToast('생성되었습니다', 'success')
    }
    emit('saved')
  } catch (err: any) {
    showToast(err.response?.data?.detail || '저장에 실패했습니다', 'error')
  } finally {
    saving.value = false
  }
}

async function loadCustomers() {
  try {
    const res = await apiClient.get('/partners', { params: { is_customer: true, limit: 500 } })
    customers.value = (res.data.items || res.data).map((c: any) => ({
      id: c.id, partner_name: c.partner_name, partner_name_en: c.partner_name_en
    }))
    // 신규 모드에서 presetCustomerId가 있으면 자동 선택
    if (!isEdit.value && props.presetCustomerId) {
      const c = customers.value.find(x => x.id === props.presetCustomerId)
      if (c) {
        form.value.customer_id = c.id
        customerSearch.value = c.partner_name
        await onCustomerChange()
      }
    }
  } catch { /* ignore */ }
}

// PI 프로세스 현황
const processSteps = ref<PIProcessStep[]>([])

// 관련 문서 체인
const router = useRouter()
const relatedDocs = ref<RelatedDocumentsResponse>({
  source: null,
  forward: [],
  production_requests: [],
})

// 관련 문서 통합 목록 (테이블용)
const allRelatedDocs = computed(() => {
  const docs: any[] = []
  // sources (N:M)
  const sources = (relatedDocs.value as any).sources || []
  if (sources.length > 0) {
    docs.push(...sources)
  } else if (relatedDocs.value.source) {
    docs.push(relatedDocs.value.source)
  }
  // forward
  docs.push(...relatedDocs.value.forward)
  // production requests
  for (const pr of relatedDocs.value.production_requests) {
    docs.push({ ...pr, type: 'PR', document_number: pr.request_number })
  }
  return docs
})

// 상태 한글 라벨(사진 양식과 동일: 작성중/발송/확정/취소/요청)
function docStatusLabel(s?: string): string {
  return ({ DRAFT: '작성중', SENT: '발송', CONFIRMED: '확정', CANCELLED: '취소', REQUESTED: '요청' } as Record<string, string>)[s || ''] || (s || '-')
}

// 현재 문서를 포함한 전체 문서 체인(Q→PI→CI→INVOICE→생산요청) — 상단 네비게이터용
const _TYPE_ORDER: Record<string, number> = { QUOTATION: 0, PI: 1, CI: 2, INVOICE: 3 }
const docChain = computed(() => {
  const cur = props.document
  const list: any[] = []
  if (cur?.id) {
    list.push({
      id: cur.id, document_type: form.value.document_type,
      document_number: (cur as any).document_number, document_date: (cur as any).document_date,
      total_amount: (cur as any).total_amount, currency: (cur as any).currency || form.value.currency,
      status: (cur as any).status, _current: true,
    })
  }
  for (const d of allRelatedDocs.value) list.push(d)
  // 유형 순서 정렬(생산요청은 맨 뒤), 안정 정렬
  return list
    .map((d, i) => ({ d, i }))
    .sort((a, b) => {
      const oa = a.d.type === 'PR' ? 10 : (_TYPE_ORDER[a.d.document_type] ?? 9)
      const ob = b.d.type === 'PR' ? 10 : (_TYPE_ORDER[b.d.document_type] ?? 9)
      return oa - ob || a.i - b.i
    })
    .map((x) => x.d)
})

// 연결된 영업 대응 현황(있으면) — 문서에서 바로 히스토리 확인용
const linkedActivity = computed<any>(() => (relatedDocs.value as any).sales_activity || null)
const showActivityPopup = ref(false)

// PI 잔여 수량
const piRemaining = ref<any>(null)
const creatingPr = ref(false)
const hasRemainingQty = computed(() => {
  if (!piRemaining.value) return false
  return piRemaining.value.items.some((i: any) => i.remaining_qty > 0)
})

async function loadPiRemaining() {
  if (!props.document?.id || props.documentType !== 'PI') return
  try {
    const res = await salesDocumentApi.getRemainingQuantities(props.document.id)
    piRemaining.value = res.data
  } catch { /* ignore */ }
}

async function createPrDraft() {
  if (!props.document?.id) return
  if (relatedDocs.value.production_requests.length > 0) {
    if (!confirm(`이 PI에 이미 ${relatedDocs.value.production_requests.length}개의 생산요청이 있습니다.\n잔여 수량으로 추가 생산요청을 생성하시겠습니까?`)) return
  } else {
    if (!confirm('이 PI에서 생산요청 초안을 생성하시겠습니까?')) return
  }
  creatingPr.value = true
  try {
    const res = await salesDocumentApi.createProductionRequestDraft(props.document.id)
    const result = res.data
    let msg = result.message
    if (result.items_skipped && result.items_skipped.length > 0) {
      msg += `\n매칭 실패: ${result.items_skipped.join(', ')}`
    }
    showToast(msg, 'success')
    // 생산요청 페이지로 이동 + 모달 자동 오픈
    emit('close')
    router.push({ path: '/production-requests', query: { edit_id: String(result.production_request_id) } })
  } catch (err: any) {
    const detail = err?.response?.data?.detail || '생산요청 생성에 실패했습니다'
    showToast(typeof detail === 'string' ? detail : '생산요청 생성에 실패했습니다', 'error')
  } finally {
    creatingPr.value = false
  }
}

// PO 첨부파일 헬퍼 — v0.41.0: 인증 헤더를 실어 blob 으로 열기(RBAC enforce 시 401 방지)
function openPoFile(idx: number) {
  if (!props.document?.id) return
  openAuthedUrl(`/sales-documents/${props.document.id}/po-attachments/${idx}/download`)
    .catch((e) => console.error('PO 첨부 열기 실패', e))
}

function formatFileSize(bytes?: number) {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

async function onPoFileUpload(e: Event) {
  const target = e.target as HTMLInputElement
  if (!target.files || target.files.length === 0 || !props.document?.id) return

  for (const file of Array.from(target.files)) {
    try {
      await salesDocumentApi.uploadPoAttachment(props.document.id, file)
    } catch {
      showToast(`${file.name} 업로드에 실패했습니다`, 'error')
    }
  }
  target.value = ''
  showToast('PO 파일이 업로드되었습니다', 'success')
  await reloadAttachments()
}

async function deletePoFile(idx: number) {
  if (!props.document?.id) return
  if (!confirm('이 PO 파일을 삭제하시겠습니까?')) return
  try {
    await salesDocumentApi.deletePoAttachment(props.document.id, idx)
    showToast('파일이 삭제되었습니다', 'success')
    await reloadAttachments()
  } catch {
    showToast('파일 삭제에 실패했습니다', 'error')
  }
}

async function reloadAttachments() {
  if (!props.document?.id) return
  try {
    const res = await salesDocumentApi.getById(props.document.id)
    poAttachments.value = res.data.po_attachment_files || []
  } catch { /* ignore */ }
}

async function loadRelatedDocuments() {
  if (!props.document?.id) return
  try {
    const res = await salesDocumentApi.getRelatedDocuments(props.document.id)
    relatedDocs.value = res.data
  } catch { /* ignore */ }
}

async function openRelatedDoc(docId: number) {
  try {
    const res = await salesDocumentApi.getById(docId)
    // 부모에게 네비게이션 이벤트 전달 (모달 닫고 해당 탭으로 이동 + 새 모달 열기)
    emit('navigate', { docId: res.data.id, docType: res.data.document_type })
    emit('close')
  } catch {
    showToast('관련 문서를 불러오는데 실패했습니다', 'error')
  }
}

function openProductionRequest(prId: number) {
  emit('close')
  router.push({ path: '/production-requests', query: { edit_id: String(prId) } })
}

async function loadProcessStatus() {
  if (!props.document?.id || props.documentType !== 'PI') return
  try {
    const res = await salesDocumentApi.getProcessStatus(props.document.id)
    processSteps.value = res.data.steps
  } catch { /* ignore */ }
}

async function copyItemsFromSourceDoc() {
  if (!props.copyFromDocId || isEdit.value) return
  try {
    const res = await salesDocumentApi.getById(props.copyFromDocId)
    const sourceDoc = res.data
    if (sourceDoc.items && sourceDoc.items.length > 0) {
      // 품목 복사 (id 제거, line_no 재설정)
      form.value.items = sourceDoc.items.map((it: any, idx: number) => ({
        line_no: idx + 1,
        product_code: it.product_code || '',
        description: it.description || '',
        line_remarks: it.line_remarks || '',
        quantity: it.quantity || 1,
        uom: it.uom || 'pc',
        unit_price: it.unit_price || 0,
        amount: it.amount || 0,
        currency: sourceDoc.currency || 'USD',
      }))
      // 통화도 복사 + 국내(KRW) 판정 복원(자동 Description 한글화 등)
      if (sourceDoc.currency) {
        form.value.currency = sourceDoc.currency
        if (sourceDoc.currency === 'KRW') tradeType.value = 'DOMESTIC'
      }
      showToast(`${sourceDoc.document_number}의 품목 ${sourceDoc.items.length}개를 복사했습니다`, 'success')
    }
  } catch {
    showToast('원본 문서 품목 복사에 실패했습니다', 'error')
  }
}

onMounted(() => {
  loadCustomers()
  loadProcessStatus()
  loadRelatedDocuments()
  loadPiRemaining()
  copyItemsFromSourceDoc()
  // 회사 은행 계좌(통화별) 로드 → 신규 해외 문서면 현재 통화 계좌로 프리필(하드코딩 대체)
  settingsApi.getCompanyBankAccounts()
    .then((a) => {
      bankAccounts.value = a
      if (!isEdit.value && !isDomestic.value) applyBankForCurrency(form.value.currency)
    })
    .catch(() => { /* 실패 시 폼 기본값 유지(폴백) */ })
  // 편집 모드: 기존 고객의 담당자 목록 로드(저장된 customer_contact_id preselect 유지)
  if (form.value.customer_id) { loadContacts(form.value.customer_id); loadShippingAddresses(form.value.customer_id) }
})
</script>
