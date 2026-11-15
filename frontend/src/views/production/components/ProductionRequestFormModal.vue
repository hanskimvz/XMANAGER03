<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
      <!-- 헤더 -->
      <div class="px-6 py-4 border-b flex justify-between items-center">
        <h2 class="text-xl font-bold text-gray-800">
          {{ requestId ? '생산 요청서 수정' : '생산 요청서 등록' }}
        </h2>
        <button @click="$emit('close')" class="text-gray-500 hover:text-gray-700">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 폼 -->
      <form @submit.prevent="handleSubmit" @paste="handlePaste" class="p-6 space-y-4">
        <!-- 제품 목록 (v0.22.0 다중 제품) -->
        <div>
          <div class="flex justify-between items-center mb-2">
            <label class="block text-sm font-medium text-gray-700">제품 목록 <span class="text-red-500">*</span></label>
            <div class="flex items-center gap-1.5">
              <button
                type="button"
                @click="addCustomItem"
                title="BOM에 없는 제품(외주 부품 등)을 품번/품명 직접 입력으로 추가"
                class="px-3 py-1 border border-gray-300 text-gray-700 text-sm rounded hover:bg-gray-50 flex items-center gap-1"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
                직접 입력 (외주)
              </button>
              <button
                type="button"
                @click="openPartSearch"
                class="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 flex items-center gap-1"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                제품 추가
              </button>
            </div>
          </div>

          <!-- 전속(독점) 계약 위반 경고 -->
          <div v-if="protectionViolations.length > 0"
            class="mb-2 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
            🔒 <strong>전속(독점) 계약 위반 가능</strong> — 아래 품목은 선택한 고객의 전속 품목이 아닙니다:
            <ul class="mt-1 ml-4 list-disc text-xs">
              <li v-for="v in protectionViolations" :key="v.product_part_id ?? v.part_number ?? v.custom_product_code">
                {{ v.part_number_display || v.part_number }} → 전속: {{ v.protected_customer_name || '지정 고객' }}
              </li>
            </ul>
            <div class="text-xs mt-1">{{ isAdmin ? '관리자는 저장 시 강제 진행할 수 있습니다.' : '전속 고객으로 변경하거나 관리자에게 문의하세요.' }}</div>
          </div>

          <!-- 제품 카드 목록: 품목 + 그 아래 특이사항 텍스트박스 -->
          <div v-if="items.length === 0"
            class="border border-dashed rounded-lg px-3 py-8 text-center text-gray-400">
            제품을 추가하세요
          </div>

          <div v-else class="space-y-3">
            <div v-for="(item, index) in items" :key="index"
              class="border rounded-lg bg-white overflow-hidden">
              <!-- 품목 헤더 -->
              <div class="flex items-center gap-3 px-3 py-2 bg-gray-50 border-b">
                <span class="text-xs font-semibold text-gray-400 w-5 text-center">{{ index + 1 }}</span>
                <!-- 커스텀(외주) 항목: 품번/품명 직접 입력 -->
                <div v-if="item.is_custom" class="flex-1 min-w-0 grid grid-cols-2 gap-1.5">
                  <div>
                    <label class="block text-[10px] text-gray-400">품번 (외주)</label>
                    <input v-model="item.custom_product_code" type="text" placeholder="예: OEM-1234"
                      class="w-full px-2 py-1 border border-gray-300 rounded text-sm font-mono focus:ring-2 focus:ring-blue-500" />
                  </div>
                  <div>
                    <label class="block text-[10px] text-gray-400">품명 <span class="text-red-500">*</span></label>
                    <input v-model="item.custom_product_name" type="text" placeholder="제품명"
                      class="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500" />
                  </div>
                </div>
                <!-- BOM 부품 항목: 선택된 품번/품명 표시 -->
                <div v-else class="flex-1 min-w-0">
                  <div class="font-mono font-medium text-gray-900 text-sm truncate flex items-center gap-1">
                    {{ item.part_number_display || item.part_number || '-' }}
                    <span v-if="item.is_protected"
                      :title="`전속: ${item.protected_customer_name || '지정 고객'}`"
                      :class="item.protected_customer_id && item.protected_customer_id !== formData.customer_id ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'"
                      class="px-1.5 py-0.5 text-[10px] rounded-full whitespace-nowrap">🔒 전속</span>
                  </div>
                  <div class="text-xs text-gray-500 truncate">{{ item.part_name || '-' }}</div>
                </div>
                <div class="flex items-center gap-1">
                  <input
                    v-model.number="item.requested_quantity"
                    type="number"
                    min="1"
                    step="1"
                    @blur="item.requested_quantity = Math.max(1, Math.floor(item.requested_quantity || 1))"
                    class="w-20 px-2 py-1 border border-gray-300 rounded text-right text-sm focus:ring-2 focus:ring-blue-500"
                  />
                  <span class="text-xs text-gray-500">{{ item.uom || 'EA' }}</span>
                </div>
                <button
                  type="button"
                  @click="removeItem(index)"
                  class="text-red-400 hover:text-red-600 ml-1"
                  title="삭제"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
              <!-- 품목별 특이사항 -->
              <div class="px-3 py-2">
                <label class="block text-xs font-medium text-gray-500 mb-1">특이사항</label>
                <textarea
                  v-model="item.customer_requirements"
                  rows="3"
                  placeholder="이 품목의 특이사항 (도면 참조, 사양, 요청 등)"
                  class="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 resize-y"
                ></textarea>
              </div>
              <!-- 품목별 도면 (선택 · 드래그앤드롭 · 캡쳐 붙여넣기) -->
              <div class="px-3 pb-2"
                @dragover.prevent="dragItemIndex = index"
                @dragleave.prevent="dragItemIndex === index && (dragItemIndex = null)"
                @drop.prevent="onItemDrop(item, index, $event)"
                @click="pasteItemIndex = index">
                <div class="flex items-center gap-1.5 flex-wrap rounded p-1 transition-colors"
                  :class="dragItemIndex === index ? 'ring-2 ring-blue-400 bg-blue-50' : (pasteItemIndex === index ? 'bg-amber-50' : '')">
                  <span class="text-xs font-medium text-gray-500 mr-1">도면</span>
                  <span v-for="(f, fi) in (item.attachment_files || [])" :key="'e' + fi"
                    class="inline-flex items-center gap-1 text-[11px] bg-sky-50 text-sky-700 rounded px-1.5 py-0.5">
                    📄 <span class="max-w-[130px] truncate">{{ f.filename }}</span>
                    <button type="button" class="text-red-400 hover:text-red-600" @click="removeExistingItemFile(item, fi)">✕</button>
                  </span>
                  <span v-for="(f, fi) in (item._newFiles || [])" :key="'n' + fi"
                    class="inline-flex items-center gap-1 text-[11px] bg-emerald-50 text-emerald-700 rounded px-1.5 py-0.5">
                    + <span class="max-w-[130px] truncate">{{ f.name }}</span>
                    <button type="button" class="text-red-400 hover:text-red-600" @click="item._newFiles!.splice(fi, 1)">✕</button>
                  </span>
                  <label class="inline-flex items-center text-[11px] px-2 py-0.5 border border-dashed border-gray-300 rounded cursor-pointer hover:bg-gray-50 text-gray-600">
                    + 도면 추가
                    <input type="file" multiple class="hidden"
                      accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.xlsx,.xls,.doc,.docx"
                      @change="onItemFileSelect(item, $event)" />
                  </label>
                  <span class="text-[10px] text-gray-400 ml-1">끌어다 놓기 · {{ pasteItemIndex === index ? '여기에 Ctrl+V 붙여넣기' : '클릭 후 Ctrl+V' }}</span>
                </div>
              </div>
            </div>
          </div>
          <p class="text-xs text-gray-500 mt-1">* 하나의 생산요청서에 여러 제품을 등록할 수 있습니다.</p>
        </div>

        <!-- 전체 특이사항 (품목 공통) -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">전체 특이사항</label>
          <textarea
            v-model="formData.remarks"
            rows="3"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 resize-y"
            placeholder="전체 품목에 공통으로 적용되는 특이사항 / 요청사항"
          ></textarea>
        </div>

        <!-- 첨부파일 (전체 특이사항 공통 사진·도면) -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">첨부파일 · 전체 특이사항 사진/도면 <span class="text-xs font-normal text-gray-400">(드래그앤드롭 · Ctrl+V 붙여넣기)</span></label>

          <!-- 파일 업로드 드래그앤드롭 영역 -->
          <div
            class="border-2 border-dashed border-gray-300 rounded-lg p-3 hover:border-blue-400 transition-colors"
            :class="{ 'border-blue-500 bg-blue-50': isDragOver }"
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
            @drop.prevent="handleFileDrop"
          >
            <div class="flex items-center justify-center gap-3">
              <svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <input
                ref="fileInputRef"
                type="file"
                accept=".pdf,.xlsx,.xls,.doc,.docx,.png,.jpg,.jpeg"
                multiple
                class="hidden"
                @change="handleFileSelect"
              />
              <span class="text-sm text-gray-600">파일 드래그 또는</span>
              <button
                type="button"
                @click="fileInputRef?.click()"
                class="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                선택
              </button>
              <span class="text-xs text-gray-400">(PDF, Excel, Word, 이미지 / 최대 200MB / Ctrl+V 붙여넣기 가능)</span>
            </div>
          </div>

          <!-- 이미지 인라인 미리보기 (큰 사이즈) -->
          <div v-if="imageFiles.length > 0" class="mt-3 space-y-3">
            <div
              v-for="(img, index) in imageFiles"
              :key="'img-' + index"
              class="relative group border border-gray-200 rounded-lg overflow-hidden bg-gray-50"
            >
              <img
                :src="img.previewUrl"
                :alt="img.filename"
                class="w-full max-h-[400px] object-contain bg-white"
              />
              <!-- 파일명 + 삭제 바 -->
              <div class="flex items-center justify-between px-3 py-1.5 bg-gray-50 border-t">
                <a
                  :href="img.previewUrl"
                  :download="img.filename"
                  class="text-xs text-blue-600 hover:text-blue-800 underline truncate"
                  @click.stop
                >{{ img.filename }}</a>
                <button
                  type="button"
                  @click="removeFile(img.originalIndex)"
                  class="text-red-500 hover:text-red-700 text-xs flex items-center gap-1"
                  title="삭제"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  삭제
                </button>
              </div>
            </div>
          </div>

          <!-- PDF 인라인 미리보기 -->
          <div v-if="pdfFiles.length > 0" class="mt-3 space-y-3">
            <div
              v-for="(file, index) in pdfFiles"
              :key="'pdf-' + index"
              class="border border-gray-200 rounded-lg overflow-hidden"
            >
              <iframe
                :src="file.previewUrl"
                class="w-full h-[400px] border-0 bg-white"
              ></iframe>
              <div class="flex items-center justify-between px-3 py-1.5 bg-gray-50 border-t">
                <a
                  :href="file.previewUrl"
                  :download="file.filename"
                  class="text-xs text-blue-600 hover:text-blue-800 underline truncate"
                  @click.stop
                >{{ file.filename }}</a>
                <button
                  type="button"
                  @click="removeFile(file.originalIndex)"
                  class="text-red-500 hover:text-red-700 text-xs flex items-center gap-1 ml-2 flex-shrink-0"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  삭제
                </button>
              </div>
            </div>
          </div>

          <!-- 기타 문서 파일 목록 (이미지, PDF 제외) -->
          <div v-if="otherFiles.length > 0" class="mt-2 space-y-1">
            <div
              v-for="(file, index) in otherFiles"
              :key="'doc-' + index"
              class="flex items-center justify-between bg-gray-50 rounded px-3 py-1.5"
            >
              <div class="flex items-center gap-2 min-w-0 flex-1">
                <svg v-if="isExcelFile(file)" class="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
                </svg>
                <svg v-else class="w-4 h-4 text-gray-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
                </svg>
                <span class="text-sm truncate">{{ file.filename }}</span>
                <span class="text-xs text-gray-400">{{ formatFileSize(file.size) }}</span>
              </div>
              <button
                type="button"
                @click="removeFile(file.originalIndex)"
                class="p-1 text-red-500 hover:text-red-700 flex-shrink-0"
                title="삭제"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- 고객사 & 우선순위 (한 줄) -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">고객사</label>
            <div class="relative" ref="customerDropdownRef">
              <input
                ref="customerInputRef"
                type="text"
                v-model="customerSearch"
                placeholder="고객사 검색 또는 선택"
                class="w-full px-3 py-2 pr-16 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                @focus="customerDropdownOpen = true"
                @input="customerDropdownOpen = true"
              />
              <div
                v-if="selectedCustomerName && !customerDropdownOpen && !customerSearch"
                class="absolute inset-0 flex items-center px-3 pr-16 pointer-events-none"
              >
                <span class="truncate text-gray-900 text-sm">{{ selectedCustomerName }}</span>
              </div>
              <button
                v-if="formData.customer_id"
                type="button"
                class="absolute inset-y-0 right-7 flex items-center px-1 text-gray-400 hover:text-red-500"
                @click.stop="clearCustomer"
                title="선택 해제"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
              <button
                type="button"
                class="absolute inset-y-0 right-0 flex items-center px-2 text-gray-400 hover:text-gray-600"
                @click.stop="customerDropdownOpen = !customerDropdownOpen"
              >
                <svg class="w-4 h-4 transition-transform" :class="{ 'rotate-180': customerDropdownOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              <div
                v-if="customerDropdownOpen"
                class="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto"
              >
                <div v-if="filteredCustomers.length === 0" class="px-3 py-2 text-gray-500 text-sm">
                  검색 결과가 없습니다
                </div>
                <div
                  v-for="c in filteredCustomers"
                  :key="c.id"
                  :class="[
                    'px-3 py-2 cursor-pointer text-sm hover:bg-blue-50',
                    formData.customer_id === c.id ? 'bg-blue-50 font-medium text-blue-700' : 'text-gray-900'
                  ]"
                  @click="selectCustomer(c)"
                >
                  {{ c.name }}
                </div>
              </div>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">우선순위</label>
            <select
              v-model.number="formData.priority"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option :value="0">보통</option>
              <option :value="1">높음</option>
              <option :value="2">긴급</option>
            </select>
          </div>
        </div>

        <!-- PI & PO (한 줄) -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">PI (Proforma Invoice)</label>
            <input
              v-model="formData.pi_number"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="PI 번호 입력"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">PO (고객 주문번호)</label>
            <input
              v-model="formData.customer_order_no"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="고객 주문번호 입력"
            />
          </div>
        </div>

        <!-- 희망납기일 & 생산기간 & 입금현황 -->
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">납기예정일</label>
            <input v-model="formData.due_date" type="date"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">생산기간</label>
            <input v-model="formData.production_period" type="text" placeholder="예: 5주"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">입금현황</label>
            <select v-model="formData.payment_status"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
              <option value="UNPAID">미입금</option>
              <option value="PARTIAL">부분입금</option>
              <option value="PAID">입금완료</option>
            </select>
          </div>
        </div>

        <!-- 작성자 & 국가 -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">작성자</label>
            <input v-model="formData.prepared_by_name" type="text" placeholder="유현성"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">국가</label>
            <input v-model="formData.country" type="text" placeholder="Czech Republic"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>

        <!-- SHIPPING MARK & CONSIGNEE -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">SHIPPING MARK</label>
            <textarea v-model="formData.shipping_mark" rows="2" placeholder="쉬핑마크 내용"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"></textarea>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">CONSIGNEE (수하인)</label>
            <textarea v-model="formData.consignee" rows="2" placeholder="수하인 정보"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"></textarea>
          </div>
        </div>

        <!-- DESTINATION (도착지) -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">DESTINATION (도착지)</label>
          <input v-model="formData.destination" type="text" placeholder="예: Shenzhen, China"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
        </div>

        <!-- 버튼 -->
        <div class="flex justify-end gap-2 pt-4 border-t">
          <button
            type="button"
            @click="$emit('close')"
            class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            취소
          </button>
          <button
            type="submit"
            :disabled="saving || items.length === 0"
            class="px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 disabled:opacity-50"
          >
            {{ saving && !submitAfterSave ? '저장 중...' : (isDraft ? '임시 저장' : '저장') }}
          </button>
          <!-- 초안: 저장 후 생산팀에 요청(전송) -->
          <button
            v-if="isDraft"
            type="button"
            :disabled="saving || items.length === 0"
            @click="submitToProduction"
            title="특이사항 입력을 마쳤으면 생산팀에 요청합니다(이때 생산팀에 알림)"
            class="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50"
          >
            {{ saving && submitAfterSave ? '전송 중...' : '📤 생산팀에 요청' }}
          </button>
        </div>
      </form>
    </div>

    <!-- BOM 부품 검색 모달 -->
    <BomPartSearchModal
      :show="showPartSearch"
      @select="handlePartSelect"
      @close="showPartSearch = false"
    />

    <!-- 첨부파일 미리보기 모달 -->
    <div v-if="showPreviewModal" class="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-[60]">
      <div class="bg-white rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        <!-- 모달 헤더 -->
        <div class="px-4 py-3 border-b flex justify-between items-center flex-shrink-0">
          <h3 class="font-medium text-gray-800 truncate">{{ previewFilename }}</h3>
          <button @click="closePreview" class="text-gray-500 hover:text-gray-700 p-1">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <!-- 미리보기 콘텐츠 -->
        <div class="flex-1 overflow-auto p-4 bg-gray-100">
          <!-- PDF 미리보기 -->
          <iframe
            v-if="previewFilename.toLowerCase().endsWith('.pdf')"
            :src="previewUrl"
            class="w-full h-[70vh] border-0 bg-white"
          ></iframe>
          <!-- 이미지 미리보기 -->
          <img
            v-else
            :src="previewUrl"
            :alt="previewFilename"
            class="max-w-full max-h-[70vh] mx-auto object-contain bg-white rounded shadow"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { productionRequestApi } from '@/api/productionRequest'
import { partnerApi } from '@/api/partner'
import { useAuth } from '@/stores/auth'
import BomPartSearchModal from '@/views/production/components/BomPartSearchModal.vue'

// 제품 항목 타입
interface ProductItem {
  id?: number  // 기존 항목 id (수정 시 in-place 반영 → PI 링크 보존)
  product_part_id?: number | null   // 커스텀(외주) 항목이면 null
  custom_product_code?: string      // BOM 미등록 품번(직접 입력)
  custom_product_name?: string      // BOM 미등록 품명(직접 입력)
  is_custom?: boolean               // 커스텀 항목 여부(UI 편집 표시)
  part_number?: string
  part_number_display?: string
  part_name?: string
  requested_quantity: number
  uom?: string
  line_remarks?: string
  customer_requirements?: string
  sort_order: number
  attachment_files?: Array<{ filename: string; filepath?: string; mimetype?: string; size?: number }>  // 저장된 도면
  _newFiles?: File[]  // 저장 전 스테이징된 도면
  // v0.79.0: 전속(독점) 계약 정보(경고용)
  is_protected?: boolean
  protected_customer_id?: number | null
  protected_customer_name?: string | null
}

// 첨부파일 타입
interface AttachmentFile {
  filename: string
  filepath?: string
  mimetype: string
  size: number
  file?: File  // 업로드 전 파일 객체
  isNew?: boolean  // 새로 추가된 파일 여부
}

const props = defineProps<{
  requestId?: number | null
  customers: { id: number; name: string }[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
}>()

// 상태
const saving = ref(false)
const isDraft = ref(false)          // 로드된 생산요청이 초안(미전송)인지
const submitAfterSave = ref(false)  // '생산팀에 요청' — 저장 후 submit
const showPartSearch = ref(false)
const loggedInUserName = JSON.parse(localStorage.getItem('user') || '{}')?.name || ''

// 제품 목록 (v0.22.0)
const items = ref<ProductItem[]>([])

// 첨부파일 (v0.22.0)
const attachmentFiles = ref<AttachmentFile[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)
const isDragOver = ref(false)

// 미리보기 모달
const showPreviewModal = ref(false)
const previewUrl = ref('')
const previewFilename = ref('')

// 고객사 콤보박스
const customerDropdownRef = ref<HTMLElement | null>(null)
const customerInputRef = ref<HTMLInputElement | null>(null)
const customerDropdownOpen = ref(false)
const customerSearch = ref('')

const selectedCustomerName = computed(() => {
  if (!formData.value.customer_id) return ''
  const c = props.customers.find(c => c.id === formData.value.customer_id)
  return c?.name || ''
})

const filteredCustomers = computed(() => {
  if (!customerSearch.value) return props.customers
  const q = customerSearch.value.toLowerCase()
  return props.customers.filter(c => c.name.toLowerCase().includes(q))
})

function selectCustomer(c: { id: number; name: string }) {
  // customer_id 변경 → watch가 기본 SHIPPING MARK/CONSIGNEE 자동 채움
  formData.value.customer_id = c.id
  customerSearch.value = ''
  customerDropdownOpen.value = false
}

function clearCustomer() {
  formData.value.customer_id = null
  customerSearch.value = ''
}

function handleCustomerClickOutside(event: MouseEvent) {
  if (customerDropdownRef.value && !customerDropdownRef.value.contains(event.target as Node)) {
    customerDropdownOpen.value = false
    customerSearch.value = ''
  }
}

const formData = ref<{
  customer_id: number | null
  customer_order_no: string
  due_date: string
  priority: number
  pi_number: string
  payment_status: string
  country: string
  production_period: string
  shipping_mark: string
  consignee: string
  destination: string
  prepared_by_name: string
  remarks: string
}>({
  customer_id: null,
  customer_order_no: '',
  due_date: '',
  priority: 0,
  pi_number: '',
  payment_status: 'UNPAID',
  country: '',
  production_period: '',
  shipping_mark: '',
  consignee: '',
  destination: '',
  prepared_by_name: loggedInUserName,
  remarks: ''
})

// 고객 선택 시 기본 SHIPPING MARK / CONSIGNEE 자동 채움.
// - 콤보박스 클릭·PI 초안·수정 로드 등 customer_id가 어떤 경로로 바뀌든 동작(watch)
// - 사용자가 직접 입력/수정한 값은 절대 덮어쓰지 않음(자동으로 채워둔 값만 갱신)
const autoFilledMark = ref('')
const autoFilledConsignee = ref('')
const autoFilledDestination = ref('')
watch(() => formData.value.customer_id, async (id) => {
  if (!id) return
  try {
    const { data } = await partnerApi.getById(id)
    const mark = data?.default_shipping_mark || ''
    const cons = data?.default_consignee || ''
    const dest = data?.default_destination || ''
    // 비어 있거나, 직전 자동채움값 그대로일 때만 갱신 → 사용자가 손댄 값은 보존
    const curMark = formData.value.shipping_mark || ''
    if (mark && (!curMark.trim() || curMark === autoFilledMark.value)) {
      formData.value.shipping_mark = mark
      autoFilledMark.value = mark
    }
    const curCons = formData.value.consignee || ''
    if (cons && (!curCons.trim() || curCons === autoFilledConsignee.value)) {
      formData.value.consignee = cons
      autoFilledConsignee.value = cons
    }
    const curDest = formData.value.destination || ''
    if (dest && (!curDest.trim() || curDest === autoFilledDestination.value)) {
      formData.value.destination = dest
      autoFilledDestination.value = dest
    }
  } catch { /* 기본값 로드 실패는 무시 */ }
})

// API Base URL (프록시 없이 백엔드 직접 접근)
// Blob URL 캐시 (깜빡임 방지)
const blobUrlCache = new Map<File, string>()

function getCachedBlobUrl(file: File): string {
  if (!blobUrlCache.has(file)) {
    blobUrlCache.set(file, URL.createObjectURL(file))
  }
  return blobUrlCache.get(file)!
}

// 기존(업로드됨) 첨부의 blob URL 맵 (index→objectURL) — 인증 헤더 실림 → 401 방지
const existingBlobUrls = ref<Record<number, string>>({})
async function loadExistingBlobs() {
  Object.values(existingBlobUrls.value).forEach(u => { try { URL.revokeObjectURL(u) } catch { /* noop */ } })
  const map: Record<number, string> = {}
  if (props.requestId) {
    await Promise.all(attachmentFiles.value.map(async (f, i) => {
      if (f.isNew || (!isImageFile(f) && !isPdfFile(f))) return
      try {
        const blob = await productionRequestApi.fetchAttachmentBlob(props.requestId!, i)
        map[i] = URL.createObjectURL(blob)
      } catch { /* 개별 실패 무시 */ }
    }))
  }
  existingBlobUrls.value = map
}

// 파일 분류 (with originalIndex + 캐싱된 previewUrl)
const imageFiles = computed(() => {
  return attachmentFiles.value
    .map((f, i) => ({
      ...f,
      originalIndex: i,
      previewUrl: f.isNew && f.file ? getCachedBlobUrl(f.file) : (existingBlobUrls.value[i] || '')
    }))
    .filter(f => isImageFile(f))
})

const pdfFiles = computed(() => {
  return attachmentFiles.value
    .map((f, i) => ({
      ...f,
      originalIndex: i,
      previewUrl: f.isNew && f.file ? getCachedBlobUrl(f.file) : (existingBlobUrls.value[i] || '')
    }))
    .filter(f => isPdfFile(f))
})

const otherFiles = computed(() => {
  return attachmentFiles.value
    .map((f, i) => ({ ...f, originalIndex: i }))
    .filter(f => !isImageFile(f) && !isPdfFile(f))
})

// 부품 검색 열기
function openPartSearch() {
  showPartSearch.value = true
}

// 부품 선택 처리
function handlePartSelect(part: any) {
  // 이미 추가된 제품인지 확인
  const exists = items.value.some(item => item.product_part_id === part.id)
  if (exists) {
    alert('이미 추가된 제품입니다.')
    return
  }

  items.value.push({
    product_part_id: part.id,
    part_number: part.part_number,
    part_number_display: part.part_number_display,
    part_name: part.part_name,
    requested_quantity: 1,
    sort_order: items.value.length,
    attachment_files: [],
    _newFiles: [],
    // v0.79.0: 전속 계약 정보(경고용)
    is_protected: (part as any).is_protected || false,
    protected_customer_id: (part as any).protected_customer_id ?? null,
    protected_customer_name: (part as any).protected_customer?.partner_name ?? null,
  })
  showPartSearch.value = false
}

// BOM 미등록(외주) 제품 — 품번/품명 직접 입력 항목 추가
function addCustomItem() {
  items.value.push({
    product_part_id: null,
    is_custom: true,
    custom_product_code: '',
    custom_product_name: '',
    requested_quantity: 1,
    uom: 'EA',
    sort_order: items.value.length,
    attachment_files: [],
    _newFiles: [],
  })
}

// v0.79.0: 전속계약 위반(보호 부품 + 다른 고객) 품목
const { isAdmin } = useAuth()
const protectionViolations = computed(() =>
  items.value.filter(it => it.is_protected && it.protected_customer_id && it.protected_customer_id !== formData.value.customer_id)
)

// 항목 삭제
function removeItem(index: number) {
  items.value.splice(index, 1)
  // sort_order 재정렬
  items.value.forEach((item, idx) => {
    item.sort_order = idx
  })
}

// ── 품목별 도면 (선택 · 드래그앤드롭 · 캡쳐 붙여넣기) ──
const dragItemIndex = ref<number | null>(null)   // 드롭 하이라이트용
const pasteItemIndex = ref<number>(0)            // Ctrl+V 붙여넣기 대상 품목

function addItemFiles(item: ProductItem, files: File[]) {
  if (!item._newFiles) item._newFiles = []
  for (const f of files) {
    if (f.size > 200 * 1024 * 1024) { alert(`파일이 너무 큽니다(최대 200MB): ${f.name}`); continue }
    item._newFiles.push(f)
  }
}
function onItemFileSelect(item: ProductItem, e: Event) {
  const input = e.target as HTMLInputElement
  addItemFiles(item, Array.from(input.files || []))
  input.value = ''
}
function onItemDrop(item: ProductItem, index: number, e: DragEvent) {
  dragItemIndex.value = null
  pasteItemIndex.value = index
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length) addItemFiles(item, files)
}
// 캡쳐(클립보드 이미지) 붙여넣기 → 현재 선택된 품목의 도면에 추가
function onItemPaste(e: ClipboardEvent) {
  const cd = e.clipboardData
  if (!cd) return
  const imgs: File[] = []
  for (const it of Array.from(cd.items)) {
    if (it.kind === 'file') {
      const f = it.getAsFile()
      if (f && (f.type || '').startsWith('image/')) imgs.push(f)
    }
  }
  if (!imgs.length) return  // 이미지가 아니면(텍스트 등) 기본 붙여넣기 동작 유지
  const idx = pasteItemIndex.value
  const target = items.value[idx] || items.value[0]
  if (!target) return
  e.preventDefault()
  const named = imgs.map((f, i) => new File(
    [f], (f.name && f.name !== 'image.png') ? f.name : `capture_${Date.now()}_${i + 1}.png`,
    { type: f.type },
  ))
  addItemFiles(target, named)
}
async function removeExistingItemFile(item: ProductItem, fi: number) {
  if (item.id && props.requestId) {
    try { await productionRequestApi.deleteItemAttachment(props.requestId, item.id, fi) }
    catch (e) { console.error('품목 도면 삭제 실패:', e) }
  }
  item.attachment_files?.splice(fi, 1)
}

// 기존 데이터 로드
async function loadData() {
  if (!props.requestId) return
  try {
    const data = await productionRequestApi.getById(props.requestId)
    isDraft.value = !!(data as any).is_draft
    formData.value = {
      customer_id: data.customer_id || null,
      customer_order_no: data.customer_order_no || '',
      due_date: data.due_date || '',
      priority: data.priority,
      pi_number: data.pi_number || '',
      payment_status: data.payment_status || 'UNPAID',
      country: data.country || '',
      production_period: data.production_period || '',
      shipping_mark: data.shipping_mark || '',
      consignee: data.consignee || '',
      destination: data.destination || '',
      prepared_by_name: data.prepared_by_name || '',
      remarks: data.remarks || ''
    }

    // 제품 항목 로드 (v0.22.0)
    if (data.items && data.items.length > 0) {
      items.value = data.items.map((item: any, idx: number) => ({
        id: item.id,
        product_part_id: item.product_part_id,
        // BOM 미등록(외주) 항목: product_part_id 없음 → 직접 입력 필드 사용
        is_custom: !item.product_part_id,
        custom_product_code: item.custom_product_code || '',
        custom_product_name: item.custom_product_name || '',
        part_number: item.product_part?.part_number,
        part_number_display: item.product_part?.part_number_display,
        part_name: item.product_part?.part_name,
        requested_quantity: Number(item.requested_quantity),
        uom: item.uom,
        line_remarks: item.line_remarks,
        customer_requirements: item.customer_requirements,
        sort_order: item.sort_order ?? idx,
        attachment_files: item.attachment_files || [],
        _newFiles: []
      }))
    } else if (data.product_part_id) {
      // 레거시 단일 제품 호환
      items.value = [{
        product_part_id: data.product_part_id,
        part_number: data.product_part?.part_number,
        part_number_display: data.product_part?.part_number_display,
        part_name: data.product_part?.part_name,
        requested_quantity: Number(data.requested_quantity),
        sort_order: 0
      }]
    }

    // 첨부파일 로드 (v0.22.0)
    if (data.attachment_files && data.attachment_files.length > 0) {
      attachmentFiles.value = data.attachment_files.map((f: any) => ({
        ...f,
        isNew: false
      }))
      await loadExistingBlobs()
    }
  } catch (error) {
    console.error('데이터 로드 실패:', error)
  }
}

// 제출 처리
async function handleSubmit() {
  if (items.value.length === 0) {
    alert('최소 하나의 제품을 추가하세요.')
    return
  }

  // 수량 검증
  for (const item of items.value) {
    if (!item.requested_quantity || item.requested_quantity <= 0) {
      alert('모든 제품의 요청 수량을 입력하세요.')
      return
    }
  }

  // 커스텀(외주) 항목 품명 검증 — BOM 부품이 아니면 품명 필수
  for (const item of items.value) {
    if (item.is_custom && !(item.custom_product_name && item.custom_product_name.trim())) {
      alert('직접 입력(외주) 항목의 품명을 입력하세요.')
      return
    }
  }

  // v0.79.0: 전속(독점) 계약 위반 가드 — 관리자만 강제 진행 가능
  let overrideProtection = false
  if (protectionViolations.value.length > 0) {
    const list = protectionViolations.value
      .map(v => `• ${v.part_number_display || v.part_number} → 전속: ${v.protected_customer_name || '지정 고객'}`)
      .join('\n')
    if (isAdmin.value) {
      if (!confirm(`⚠ 전속(독점) 계약 위반 품목이 있습니다:\n${list}\n\n선택한 고객은 전속 고객이 아닙니다. 관리자 권한으로 강제 진행할까요?`)) return
      overrideProtection = true
    } else {
      alert(`전속(독점) 계약 위반 품목이 있어 저장할 수 없습니다:\n${list}\n\n전속 고객으로 변경하거나 관리자에게 문의하세요.`)
      return
    }
  }

  saving.value = true
  try {
    // items 데이터 구성
    const itemsData = items.value.map((item, idx) => ({
      ...(item.id ? { id: item.id } : {}),
      product_part_id: item.is_custom ? null : item.product_part_id,
      custom_product_code: item.is_custom ? (item.custom_product_code?.trim() || null) : null,
      custom_product_name: item.is_custom ? (item.custom_product_name?.trim() || null) : null,
      requested_quantity: item.requested_quantity,
      uom: item.uom,
      line_remarks: item.line_remarks,
      customer_requirements: item.customer_requirements,
      sort_order: idx
    }))

    let prId = props.requestId

    // 빈 정수 정규화 — Pydantic이 빈 문자열을 정수로 거부함
    const _priority = (typeof formData.value.priority === 'number' && !Number.isNaN(formData.value.priority))
      ? formData.value.priority
      : undefined

    let savedPr: any = null
    if (props.requestId) {
      // 수정
      savedPr = await productionRequestApi.update(props.requestId, {
        customer_id: formData.value.customer_id || undefined,
        customer_order_no: formData.value.customer_order_no || undefined,
        due_date: formData.value.due_date || undefined,
        priority: _priority,
        pi_number: formData.value.pi_number || undefined,
        payment_status: formData.value.payment_status || undefined,
        country: formData.value.country || undefined,
        production_period: formData.value.production_period || undefined,
        shipping_mark: formData.value.shipping_mark || undefined,
        consignee: formData.value.consignee || undefined,
        destination: formData.value.destination || undefined,
        prepared_by_name: formData.value.prepared_by_name || undefined,
        remarks: formData.value.remarks || undefined,
        items: itemsData
      }, overrideProtection)
    } else {
      // 생성
      savedPr = await productionRequestApi.create({
        customer_id: formData.value.customer_id || undefined,
        customer_order_no: formData.value.customer_order_no || undefined,
        due_date: formData.value.due_date || undefined,
        priority: _priority,
        pi_number: formData.value.pi_number || undefined,
        payment_status: formData.value.payment_status || undefined,
        country: formData.value.country || undefined,
        production_period: formData.value.production_period || undefined,
        shipping_mark: formData.value.shipping_mark || undefined,
        consignee: formData.value.consignee || undefined,
        destination: formData.value.destination || undefined,
        prepared_by_name: formData.value.prepared_by_name || undefined,
        remarks: formData.value.remarks || undefined,
        items: itemsData
      }, overrideProtection)
      prId = savedPr.id
    }

    // 요청 단위 새 파일 업로드
    if (prId) {
      await uploadNewFiles(prId)
    }
    // 품목별 도면 업로드 (저장된 품목 id에 매칭)
    await uploadItemFiles(savedPr)

    // 초안 → '생산팀에 요청' 눌렀으면 저장 후 전송(is_draft 해제 + 생산팀 알림)
    if (submitAfterSave.value && prId) {
      await productionRequestApi.submitDraft(prId)
      isDraft.value = false
    }
    emit('saved')
  } catch (error: any) {
    const detail = error.response?.data?.detail
    const message = typeof detail === 'string' ? detail
      : detail?.message ? detail.message
      : Array.isArray(detail) ? detail.map((e: any) => e.msg).join(', ')
      : '저장 실패'
    alert(message)
  } finally {
    saving.value = false
    submitAfterSave.value = false
  }
}

// 초안: 저장 후 생산팀에 요청(전송)
function submitToProduction() {
  submitAfterSave.value = true
  handleSubmit()
}

// ==================== 첨부파일 처리 (v0.22.0) ====================

// 파일 선택 처리
function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files) {
    addFiles(Array.from(input.files))
    input.value = ''  // 같은 파일 재선택 허용
  }
}

// 파일 드롭 처리
function handleFileDrop(event: DragEvent) {
  isDragOver.value = false
  if (event.dataTransfer?.files) {
    addFiles(Array.from(event.dataTransfer.files))
  }
}

// 클립보드 붙여넣기 처리
function handlePaste(event: ClipboardEvent) {
  const items = event.clipboardData?.items
  if (!items) return

  const pastedFiles: File[] = []
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (item && item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        // 클립보드 이미지는 이름이 'image.png' 등으로 오므로 타임스탬프를 붙여 구분
        const ext = file.type.split('/')[1] || 'png'
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
        const renamedFile = new File([file], `clipboard-${timestamp}.${ext}`, { type: file.type })
        pastedFiles.push(renamedFile)
      }
    }
  }

  if (pastedFiles.length > 0) {
    event.preventDefault()
    addFiles(pastedFiles)
  }
}

// 파일 추가
function addFiles(files: File[]) {
  const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel', 'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/png', 'image/jpeg', 'image/jpg']

  for (const file of files) {
    // 파일 타입 검증
    if (!allowedTypes.includes(file.type)) {
      alert(`지원하지 않는 파일 형식입니다: ${file.name}`)
      continue
    }

    // 파일 크기 검증 (200MB)
    if (file.size > 200 * 1024 * 1024) {
      alert(`파일이 너무 큽니다 (최대 200MB): ${file.name}`)
      continue
    }

    attachmentFiles.value.push({
      filename: file.name,
      mimetype: file.type,
      size: file.size,
      file: file,
      isNew: true
    })
  }
}

// 파일 삭제
function removeFile(index: number) {
  const file = attachmentFiles.value[index]
  if (!file) return

  // Blob URL 해제
  if (file.file && blobUrlCache.has(file.file)) {
    URL.revokeObjectURL(blobUrlCache.get(file.file)!)
    blobUrlCache.delete(file.file)
  }

  // 기존 파일이면 서버에서 삭제
  if (!file.isNew && props.requestId && file.filepath) {
    productionRequestApi.deleteAttachment(props.requestId, index).catch(console.error)
  }

  attachmentFiles.value.splice(index, 1)
}

// 새 파일 업로드
async function uploadNewFiles(prId: number) {
  const newFiles = attachmentFiles.value.filter(f => f.isNew && f.file)

  for (const fileInfo of newFiles) {
    if (!fileInfo.file) continue
    try {
      await productionRequestApi.uploadAttachment(prId, fileInfo.file)
    } catch (error) {
      console.error('파일 업로드 실패:', fileInfo.filename, error)
    }
  }
}

// 품목별 도면 업로드 (저장된 품목 id에 sort_order 순으로 매칭)
async function uploadItemFiles(savedPr: any) {
  if (!savedPr?.id) return
  const savedItems = [...(savedPr.items || [])].sort(
    (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)
  )
  for (let i = 0; i < items.value.length; i++) {
    const formItem = items.value[i]
    const staged = formItem?._newFiles || []
    const serverItem = savedItems[i]
    if (!formItem || !serverItem?.id || !staged.length) continue
    for (const f of staged) {
      try {
        await productionRequestApi.uploadItemAttachment(savedPr.id, serverItem.id, f)
      } catch (error) {
        console.error('품목 도면 업로드 실패:', f.name, error)
      }
    }
    formItem._newFiles = []
  }
}

// 파일 크기 포맷
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

// 이미지 파일 확인
function isImageFile(file: AttachmentFile): boolean {
  return file.mimetype?.startsWith('image/') ||
    /\.(png|jpg|jpeg|gif|webp)$/i.test(file.filename)
}

// 이미지 썸네일 URL 생성
function getImageThumbnailUrl(file: AttachmentFile & { originalIndex: number }): string {
  if (file.isNew && file.file) {
    return URL.createObjectURL(file.file)
  } else if (props.requestId) {
    return `/api/v1/production-requests/${props.requestId}/attachments/${file.originalIndex}/preview`
  }
  return ''
}

// PDF 미리보기 URL 생성
function getPdfPreviewUrl(file: AttachmentFile & { originalIndex: number }): string {
  if (file.isNew && file.file) {
    return URL.createObjectURL(file.file)
  } else if (props.requestId) {
    return `/api/v1/production-requests/${props.requestId}/attachments/${file.originalIndex}/preview`
  }
  return ''
}

// PDF 파일 확인
function isPdfFile(file: AttachmentFile): boolean {
  return file.mimetype === 'application/pdf' ||
    file.filename.toLowerCase().endsWith('.pdf')
}

// Excel 파일 확인
function isExcelFile(file: AttachmentFile): boolean {
  return file.mimetype.includes('spreadsheet') ||
    file.mimetype.includes('excel') ||
    file.filename.toLowerCase().endsWith('.xlsx') ||
    file.filename.toLowerCase().endsWith('.xls')
}

// 미리보기 가능 여부
function canPreview(file: AttachmentFile): boolean {
  return isPdfFile(file) ||
    file.mimetype.startsWith('image/')
}

// 파일 미리보기
function previewFile(file: AttachmentFile, index: number) {
  if (file.isNew && file.file) {
    // 새 파일: URL.createObjectURL 사용
    previewUrl.value = URL.createObjectURL(file.file)
  } else if (props.requestId) {
    // 기존 파일: 서버 미리보기 API 사용
    previewUrl.value = `/api/v1/production-requests/${props.requestId}/attachments/${index}/preview`
  }

  previewFilename.value = file.filename
  showPreviewModal.value = true
}

// 미리보기 모달 닫기
function closePreview() {
  // 새 파일 URL 해제
  if (previewUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewUrl.value)
  }
  showPreviewModal.value = false
  previewUrl.value = ''
  previewFilename.value = ''
}

onMounted(() => {
  loadData()
  document.addEventListener('click', handleCustomerClickOutside)
  document.addEventListener('paste', onItemPaste)
})

onUnmounted(() => {
  document.removeEventListener('click', handleCustomerClickOutside)
  document.removeEventListener('paste', onItemPaste)
  // Blob URL 전체 해제
  blobUrlCache.forEach(url => URL.revokeObjectURL(url))
  blobUrlCache.clear()
  Object.values(existingBlobUrls.value).forEach(u => { try { URL.revokeObjectURL(u) } catch { /* noop */ } })
})
</script>
