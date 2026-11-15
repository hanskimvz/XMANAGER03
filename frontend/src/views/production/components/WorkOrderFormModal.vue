<template>
  <div
    ref="modalOverlay"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    tabindex="-1"
    @keydown.escape="$emit('close')"
  >
    <div class="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] overflow-hidden" @click.stop>
      <!-- 헤더 -->
      <div class="flex justify-between items-center px-6 py-4 border-b">
        <div>
          <h2 class="text-xl font-bold text-gray-800">
            {{ isEdit ? '작업지시서 상세' : '작업지시서 등록' }}
          </h2>
          <p v-if="isEdit && workOrder" class="text-sm text-gray-500">{{ workOrder.wo_number }}</p>
        </div>
        <button @click="$emit('close')" class="text-gray-500 hover:text-gray-700">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 본문 -->
      <div class="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
        <!-- 로딩 -->
        <div v-if="loading" class="text-center py-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p class="mt-2 text-gray-500">로딩 중...</p>
        </div>

        <div v-else>
          <!-- v0.21.0: 원본 요청서 수정 알림 배너 -->
          <div
            v-if="isEdit && workOrder?.source_request_modified"
            class="mb-4 p-3 bg-yellow-50 border border-yellow-300 rounded-lg flex items-center justify-between"
          >
            <div class="flex items-center gap-2 text-yellow-800">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              <span class="text-sm font-medium">원본 생산요청서가 수정되었습니다</span>
            </div>
            <button
              @click="handleAcknowledgeModification"
              class="px-3 py-1 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700"
            >
              확인함
            </button>
          </div>

          <!-- v0.31.0: 작업지시 체인 (선행/후속 관계) -->
          <div v-if="isEdit && (woChain.parent || woChain.children.length > 0)" class="mb-4">
            <div class="bg-indigo-50 border border-indigo-200 rounded-lg px-4 py-2">
              <div class="flex flex-wrap items-center gap-2 text-xs">
                <span class="text-indigo-600 font-medium">🔗 작업 체인:</span>

                <!-- 하위(선행) WO -->
                <template v-for="child in woChain.children" :key="'child-' + child.id">
                  <span class="inline-flex items-center gap-1 px-2 py-1 bg-white border border-indigo-300 rounded text-indigo-700">
                    <span class="text-gray-400">←</span>
                    {{ child.wo_number }}
                    <span v-if="child.target_part" class="text-gray-500">({{ child.target_part.part_name }})</span>
                  </span>
                </template>

                <!-- 현재 WO -->
                <span class="inline-flex items-center gap-1 px-2 py-1 bg-indigo-600 text-white rounded font-medium">
                  현재: {{ workOrder?.wo_number }}
                </span>

                <!-- 상위(후속) WO -->
                <template v-if="woChain.parent">
                  <span class="inline-flex items-center gap-1 px-2 py-1 bg-white border border-indigo-300 rounded text-indigo-700">
                    <span class="text-gray-400">→</span>
                    {{ woChain.parent.wo_number }}
                  </span>
                </template>
              </div>
            </div>
          </div>

          <!-- 공정 단계 스텝퍼 (수정 모드) -->
          <div v-if="isEdit && workOrder" class="mb-6">
            <!-- 취소 상태 배너 -->
            <div v-if="workOrder.status === 'CANCELLED'" class="flex items-center gap-2 px-4 py-2 bg-red-50 border border-red-200 rounded-lg mb-3">
              <span class="w-3 h-3 bg-red-500 rounded-full"></span>
              <span class="text-sm font-semibold text-red-700">취소됨</span>
            </div>
            <!-- 스텝퍼 -->
            <div class="flex items-center">
              <template v-for="(step, idx) in stepperSteps" :key="step.status">
                <!-- 연결선 (첫 번째 제외) -->
                <div v-if="idx > 0" class="flex-1 h-0.5 mx-0.5"
                  :class="step.state === 'completed' || step.state === 'current' ? 'bg-blue-400' : 'bg-gray-200'">
                </div>
                <!-- 단계 -->
                <div class="flex flex-col items-center" style="min-width: 56px;">
                  <div class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all"
                    :class="{
                      'bg-blue-500 border-blue-500 text-white': step.state === 'current',
                      'bg-blue-100 border-blue-400 text-blue-700': step.state === 'completed',
                      'bg-gray-100 border-gray-300 text-gray-400': step.state === 'pending',
                    }">
                    <svg v-if="step.state === 'completed'" class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                    </svg>
                    <span v-else>{{ idx + 1 }}</span>
                  </div>
                  <span class="text-xs mt-1 whitespace-nowrap"
                    :class="{
                      'text-blue-700 font-semibold': step.state === 'current',
                      'text-blue-600': step.state === 'completed',
                      'text-gray-400': step.state === 'pending',
                    }">
                    {{ step.label }}
                  </span>
                </div>
              </template>
            </div>
          </div>

          <!-- 제품 목록 (v0.19.0 다중 제품 지원) -->
          <div class="mb-6">
            <div class="flex justify-between items-center mb-3">
              <label class="block text-sm font-medium text-gray-700">
                제품 목록 <span class="text-red-500">*</span>
              </label>
              <button
                v-if="!isEdit"
                @click="showPartSearch = true"
                class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 flex items-center gap-1"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                제품 추가
              </button>
            </div>

            <!-- 제품 테이블 -->
            <div class="border rounded-lg overflow-hidden">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 w-12">#</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">품번</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">제품명</th>
                    <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 w-32">지시수량</th>
                    <th v-if="isEdit" class="px-4 py-2 text-right text-xs font-medium text-gray-500 w-24">완료</th>
                    <th v-if="isEdit" class="px-4 py-2 text-right text-xs font-medium text-gray-500 w-24">불량</th>
                    <th v-if="!isEdit" class="px-4 py-2 text-center text-xs font-medium text-gray-500 w-16">삭제</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr v-for="(product, idx) in productList" :key="idx" class="hover:bg-gray-50">
                    <td class="px-4 py-2 text-sm text-gray-500">{{ idx + 1 }}</td>
                    <td class="px-4 py-2 text-sm font-mono text-blue-600">
                      {{ product.product_part?.part_number_display || product.product_part?.part_number || '-' }}
                    </td>
                    <td class="px-4 py-2 text-sm">{{ product.product_part?.part_name || '-' }}</td>
                    <td class="px-4 py-2 text-right">
                      <input
                        v-model.number="product.order_quantity"
                        type="number"
                        min="1"
                        :disabled="isEdit"
                        class="w-24 px-2 py-1 text-right border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 text-sm"
                        @input="onProductQuantityChange(idx)"
                      />
                    </td>
                    <td v-if="isEdit" class="px-4 py-2 text-sm text-right text-green-600">{{ product.completed_quantity || 0 }}</td>
                    <td v-if="isEdit" class="px-4 py-2 text-sm text-right text-red-600">{{ product.defective_quantity || 0 }}</td>
                    <td v-if="!isEdit" class="px-4 py-2 text-center">
                      <button
                        @click="removeProduct(idx)"
                        class="text-red-500 hover:text-red-700"
                        title="삭제"
                      >
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                  <tr v-if="productList.length === 0">
                    <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                      제품을 추가하세요
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="text-xs text-gray-500 mt-1">* 하나의 작업지시서에 여러 제품을 등록할 수 있습니다.</p>
          </div>

          <!-- 기본 정보 -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <!-- 거래처 (검색 모달) -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">거래처</label>
              <div class="flex gap-2">
                <input
                  :value="selectedCustomer?.partner_name || ''"
                  type="text"
                  readonly
                  placeholder="거래처를 선택하세요"
                  class="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                  :class="{ 'cursor-not-allowed': !isEditable }"
                />
                <button
                  v-if="isEditable"
                  @click="showCustomerSearch = true"
                  class="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  검색
                </button>
                <button
                  v-if="selectedCustomer && isEditable"
                  @click="clearCustomer"
                  class="px-3 py-2 bg-gray-400 text-white rounded-lg hover:bg-gray-500"
                  title="선택 해제"
                >
                  X
                </button>
              </div>
              <p v-if="selectedCustomer" class="text-xs text-gray-500 mt-1 font-mono">
                {{ selectedCustomer.partner_code }}
              </p>
            </div>

            <!-- 고객 주문번호 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">고객 주문번호</label>
              <input
                v-model="formData.customer_order_no"
                type="text"
                :disabled="!isEditable"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              />
            </div>

            <!-- 우선순위 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">우선순위</label>
              <select
                v-model.number="formData.priority"
                :disabled="!isEditable"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              >
                <option :value="0">보통</option>
                <option :value="1">높음</option>
                <option :value="2">긴급</option>
              </select>
            </div>

            <!-- 출하예정일 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">출하예정일</label>
              <input
                v-model="formData.shipping_scheduled_date"
                type="date"
                :disabled="!isEditable"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              />
            </div>
          </div>

          <!-- 생산 가능 수량 분석 (신규 등록 시) - 첫 번째 제품 기준 -->
          <ProductionAvailabilityCard
            v-if="!isEdit && productList.length > 0 && productList[0]"
            :product-part-id="productList[0].product_part_id"
            :requested-quantity="productList[0].order_quantity ?? 0"
          />

          <!-- 예정일 (접기/펼치기) -->
          <div class="mb-6">
            <button
              @click="showScheduleDates = !showScheduleDates"
              class="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800"
            >
              <svg
                class="w-4 h-4 transition-transform"
                :class="{ 'rotate-90': showScheduleDates }"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
              단계별 예정일
            </button>
            <div v-if="showScheduleDates" class="mt-3 grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <label class="block text-xs text-gray-500 mb-1">부품출고 예정일</label>
                <input
                  v-model="formData.issue_scheduled_date"
                  type="date"
                  :disabled="!isEditable"
                  class="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                />
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-1">작업 예정일</label>
                <input
                  v-model="formData.production_scheduled_date"
                  type="date"
                  :disabled="!isEditable"
                  class="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                />
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-1">검사 예정일</label>
                <input
                  v-model="formData.inspection_scheduled_date"
                  type="date"
                  :disabled="!isEditable"
                  class="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                />
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-1">포장 예정일</label>
                <input
                  v-model="formData.packing_scheduled_date"
                  type="date"
                  :disabled="!isEditable"
                  class="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                />
              </div>
            </div>
          </div>

          <!-- BOM 미리보기 (신규 등록 시) - 다중 제품 -->
          <div v-if="!isEdit && bomPreviews.length > 0" class="mb-6">
            <div v-for="(preview, pIdx) in bomPreviews" :key="pIdx" class="mb-4">
              <div class="flex justify-between items-center mb-3">
                <h3 class="text-lg font-semibold">
                  <span class="text-blue-600 mr-2">[{{ pIdx + 1 }}]</span>
                  {{ preview.product_part_name }} BOM 구성부품
                </h3>
                <div v-if="preview.has_insufficient_stock" class="text-sm text-red-600">
                  <span class="mr-1">!</span> 재고 부족 항목이 있습니다
                </div>
              </div>
              <div class="overflow-x-auto border rounded-lg">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">레벨</th>
                      <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">품번</th>
                      <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">부품명</th>
                      <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">소요량</th>
                      <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">필요수량</th>
                      <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">현재고</th>
                      <th class="px-4 py-2 text-center text-xs font-medium text-gray-500">상태</th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr v-for="item in preview.items" :key="item.part_id" class="hover:bg-gray-50">
                      <td class="px-4 py-2 text-sm text-gray-500">
                        <span :style="{ paddingLeft: (item.bom_level - 1) * 12 + 'px' }">
                          L{{ item.bom_level }}
                        </span>
                      </td>
                      <td class="px-4 py-2 text-sm font-mono text-blue-600">
                        {{ item.part_number_display || item.part_number }}
                      </td>
                      <td class="px-4 py-2 text-sm">{{ item.part_name }}</td>
                      <td class="px-4 py-2 text-sm text-right">{{ item.unit_quantity }}</td>
                      <td class="px-4 py-2 text-sm text-right font-medium">{{ item.total_quantity }}</td>
                      <td class="px-4 py-2 text-sm text-right">{{ item.current_stock ?? '-' }}</td>
                      <td class="px-4 py-2 text-center">
                        <span
                          :class="[
                            'px-2 py-1 text-xs rounded-full',
                            item.stock_status === 'SUFFICIENT' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          ]"
                        >
                          {{ item.stock_status === 'SUFFICIENT' ? '충분' : '부족' }}
                        </span>
                      </td>
                    </tr>
                    <tr v-if="!preview.items.length">
                      <td colspan="7" class="px-4 py-4 text-center text-gray-500">BOM 구성부품이 없습니다.</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- 비고 -->
          <div class="mb-6">
            <label class="block text-sm font-medium text-gray-700 mb-1">비고</label>
            <textarea
              v-model="formData.remarks"
              rows="3"
              :disabled="!isEditable"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              placeholder="작업지시 관련 비고사항"
            ></textarea>
          </div>

          <!-- 생산요청서 첨부자료 (v0.22.0: 원본 참조, 인라인 미리보기) - 첨부파일보다 위로 이동 -->
          <div v-if="prAttachmentFiles.length > 0" class="mb-6">
            <h3 class="text-lg font-semibold mb-3">
              <span class="text-blue-700">생산요청서 첨부자료</span>
              <span v-if="isEdit && workOrder?.source_request_number" class="text-sm font-normal text-gray-500 ml-2">
                ({{ workOrder.source_request_number }})
              </span>
            </h3>
            <div class="border-2 border-blue-200 rounded-lg p-4 bg-blue-50 space-y-4">
              <!-- 이미지 파일 인라인 미리보기 -->
              <div v-for="file in prImageFiles" :key="'pr-img-'+file.originalIndex" class="space-y-1">
                <img
                  :src="getPRAttachmentUrl(file.originalIndex)"
                  :alt="file.filename"
                  class="w-full max-h-[500px] object-contain rounded border bg-white"
                />
                <a
                  :href="getPRAttachmentDownloadUrl(file.originalIndex)"
                  :download="file.filename"
                  class="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                >{{ file.filename }}</a>
              </div>
              <!-- PDF 파일 인라인 미리보기 -->
              <div v-for="file in prPdfFiles" :key="'pr-pdf-'+file.originalIndex" class="space-y-1">
                <iframe
                  :src="getPRAttachmentUrl(file.originalIndex)"
                  class="w-full h-[500px] border rounded bg-white"
                ></iframe>
                <a
                  :href="getPRAttachmentDownloadUrl(file.originalIndex)"
                  :download="file.filename"
                  class="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                >{{ file.filename }}</a>
              </div>
              <!-- 기타 파일 -->
              <div v-for="file in prOtherFiles" :key="'pr-other-'+file.originalIndex"
                   class="flex items-center gap-2 py-1">
                <svg class="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M4 18h12a2 2 0 002-2V6l-4-4H4a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
                <a
                  :href="getPRAttachmentDownloadUrl(file.originalIndex)"
                  :download="file.filename"
                  class="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                >{{ file.filename }}</a>
                <span v-if="file.size" class="text-xs text-gray-400">({{ formatFileSize(file.size) }})</span>
              </div>
            </div>
          </div>

          <!-- 작업지시서 첨부파일 (인라인 미리보기 + 드래그앤드롭 + 붙여넣기) -->
          <div class="mb-6" @paste="handlePaste">
            <h3 class="text-lg font-semibold mb-3">첨부파일</h3>
            <div class="border rounded-lg p-4 bg-gray-50 space-y-4">
              <!-- 기존 파일 인라인 미리보기 (수정 모드) -->
              <template v-if="isEdit && workOrder?.document_files?.length">
                <!-- 이미지 파일 -->
                <div v-for="file in woExistingImageFiles" :key="'wo-img-'+file.originalIndex" class="space-y-1">
                  <img
                    :src="getWOFileUrl(file.originalIndex)"
                    :alt="file.file_name"
                    class="w-full max-h-[400px] object-contain rounded border bg-white"
                  />
                  <div class="flex items-center justify-between">
                    <a
                      :href="getWOFileDownloadUrl(file.originalIndex)"
                      :download="file.file_name"
                      class="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                    >{{ file.file_name }}</a>
                    <button v-if="isEditable" @click="handleDeleteFile(file.originalIndex)" class="text-red-500 hover:text-red-700 text-sm">삭제</button>
                  </div>
                </div>
                <!-- PDF 파일 -->
                <div v-for="file in woExistingPdfFiles" :key="'wo-pdf-'+file.originalIndex" class="space-y-1">
                  <iframe
                    :src="getWOFileUrl(file.originalIndex)"
                    class="w-full h-[400px] border rounded bg-white"
                  ></iframe>
                  <div class="flex items-center justify-between">
                    <a
                      :href="getWOFileDownloadUrl(file.originalIndex)"
                      :download="file.file_name"
                      class="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                    >{{ file.file_name }}</a>
                    <button v-if="isEditable" @click="handleDeleteFile(file.originalIndex)" class="text-red-500 hover:text-red-700 text-sm">삭제</button>
                  </div>
                </div>
                <!-- 기타 파일 -->
                <div v-for="file in woExistingOtherFiles" :key="'wo-other-'+file.originalIndex"
                     class="flex items-center justify-between py-1">
                  <div class="flex items-center gap-2">
                    <svg class="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M4 18h12a2 2 0 002-2V6l-4-4H4a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                    </svg>
                    <a
                      :href="getWOFileDownloadUrl(file.originalIndex)"
                      :download="file.file_name"
                      class="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                    >{{ file.file_name }}</a>
                    <span v-if="file.file_size" class="text-xs text-gray-400">({{ formatFileSize(file.file_size) }})</span>
                  </div>
                  <button v-if="isEditable" @click="handleDeleteFile(file.originalIndex)" class="text-red-500 hover:text-red-700 text-sm">삭제</button>
                </div>
              </template>
              <div v-else-if="isEdit && !selectedFiles.length" class="text-sm text-gray-500">첨부된 파일이 없습니다.</div>

              <!-- 신규 파일 인라인 미리보기 -->
              <template v-if="selectedFiles.length > 0">
                <!-- 신규 이미지 -->
                <div v-for="file in newImageFiles" :key="'new-img-'+file.originalIndex" class="space-y-1">
                  <img
                    :src="file.previewUrl"
                    :alt="file.file.name"
                    class="w-full max-h-[400px] object-contain rounded border bg-white"
                  />
                  <div class="flex items-center justify-between">
                    <span class="text-sm text-gray-700">{{ file.file.name }}</span>
                    <button @click="removeSelectedFile(file.originalIndex)" class="text-red-500 hover:text-red-700 text-sm">제거</button>
                  </div>
                </div>
                <!-- 신규 PDF -->
                <div v-for="file in newPdfFiles" :key="'new-pdf-'+file.originalIndex" class="space-y-1">
                  <iframe
                    :src="file.previewUrl"
                    class="w-full h-[400px] border rounded bg-white"
                  ></iframe>
                  <div class="flex items-center justify-between">
                    <span class="text-sm text-gray-700">{{ file.file.name }}</span>
                    <button @click="removeSelectedFile(file.originalIndex)" class="text-red-500 hover:text-red-700 text-sm">제거</button>
                  </div>
                </div>
                <!-- 신규 기타 -->
                <div v-for="file in newOtherFiles" :key="'new-other-'+file.originalIndex"
                     class="flex items-center justify-between py-1">
                  <div class="flex items-center gap-2">
                    <svg class="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M4 18h12a2 2 0 002-2V6l-4-4H4a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                    </svg>
                    <span class="text-sm text-gray-700">{{ file.file.name }}</span>
                  </div>
                  <button @click="removeSelectedFile(file.originalIndex)" class="text-red-500 hover:text-red-700 text-sm">제거</button>
                </div>
              </template>

              <!-- 드래그앤드롭 + 파일 선택 영역 -->
              <div v-if="isEditable">
                <input ref="fileInputRef" type="file" multiple class="hidden" @change="handleFileSelect" />
                <div
                  class="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors"
                  :class="isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-100'"
                  @click="fileInputRef?.click()"
                  @dragover.prevent="isDragging = true"
                  @dragleave.prevent="isDragging = false"
                  @drop.prevent="handleDrop"
                >
                  <svg class="w-8 h-8 mx-auto text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <p class="text-sm text-gray-500">파일을 드래그하거나 클릭하여 선택</p>
                  <p class="text-xs text-gray-400 mt-1">Ctrl+V로 캡처 이미지 붙여넣기 가능</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 구성부품 목록 (수정 모드, 접기/펼치기) -->
          <div v-if="isEdit && workOrder?.items?.length" class="mb-6">
            <button @click="showBomItems = !showBomItems" type="button"
              class="flex items-center gap-2 w-full text-left">
              <h3 class="text-lg font-semibold">구성부품</h3>
              <span class="text-xs text-gray-500">({{ workOrder.items.length }}개)</span>
              <svg :class="showBomItems ? 'rotate-180' : ''" class="w-4 h-4 text-gray-400 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <div v-if="showBomItems" class="overflow-x-auto border rounded-lg mt-3">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">레벨</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">품번</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">부품명</th>
                    <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">필요수량</th>
                    <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">출고수량</th>
                    <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">추가출고</th>
                    <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">반납</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr v-for="item in workOrder.items" :key="item.id" class="hover:bg-gray-50">
                    <td class="px-4 py-2 text-sm text-gray-500">
                      <span :style="{ paddingLeft: (item.bom_level - 1) * 12 + 'px' }">
                        L{{ item.bom_level }}
                      </span>
                    </td>
                    <td class="px-4 py-2 text-sm font-mono text-blue-600">
                      {{ item.part?.part_number_display || item.part?.part_number || '-' }}
                    </td>
                    <td class="px-4 py-2 text-sm">{{ item.part?.part_name || '-' }}</td>
                    <td class="px-4 py-2 text-sm text-right">{{ item.required_quantity }}</td>
                    <td class="px-4 py-2 text-sm text-right text-green-600">{{ item.issued_quantity }}</td>
                    <td class="px-4 py-2 text-sm text-right text-orange-600">{{ item.additional_quantity }}</td>
                    <td class="px-4 py-2 text-sm text-right text-blue-600">{{ item.returned_quantity }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 공정 체크리스트 (수정 모드) v0.29.0 -->
          <div v-if="isEdit && workOrder" class="mb-6">
            <div class="flex justify-between items-center mb-3">
              <h3 class="text-lg font-semibold">공정 진행</h3>
              <div class="flex gap-2">
                <button @click="showAddTask = !showAddTask" class="text-sm text-blue-600 hover:text-blue-800">
                  + 공정 추가
                </button>
              </div>
            </div>

            <!-- 공정 추가 폼 -->
            <div v-if="showAddTask" class="flex gap-2 mb-3">
              <input v-model="newTaskName" placeholder="공정명 (인서트, 조립 등)" class="flex-1 border rounded px-3 py-1.5 text-sm" />
              <input v-model="newTaskTeam" placeholder="담당팀" class="w-28 border rounded px-3 py-1.5 text-sm" />
              <button @click="addTask" :disabled="!newTaskName.trim()" class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">추가</button>
            </div>

            <!-- 공정 목록 -->
            <div v-if="tasks.length > 0" class="space-y-2">
              <div v-for="task in tasks" :key="task.id"
                class="flex items-center gap-3 px-3 py-2 rounded-lg border"
                :class="{
                  'border-green-200 bg-green-50': task.status === 'COMPLETED',
                  'border-blue-200 bg-blue-50': task.status === 'IN_PROGRESS',
                  'border-gray-200': task.status === 'PENDING',
                }">
                <!-- 체크/상태 아이콘 -->
                <div class="flex-shrink-0">
                  <svg v-if="task.status === 'COMPLETED'" class="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                  </svg>
                  <div v-else-if="task.status === 'IN_PROGRESS'" class="w-5 h-5 border-2 border-blue-500 rounded-full flex items-center justify-center">
                    <div class="w-2 h-2 bg-blue-500 rounded-full"></div>
                  </div>
                  <div v-else class="w-5 h-5 border-2 border-gray-300 rounded-full"></div>
                </div>

                <!-- 공정 정보 -->
                <div class="flex-1 min-w-0">
                  <span class="text-sm font-medium">{{ task.task_name }}</span>
                  <span v-if="task.assigned_team" class="text-xs text-gray-400 ml-2">[{{ task.assigned_team }}]</span>
                  <div v-if="task.completed_at" class="text-xs text-gray-400">
                    완료: {{ formatTaskDate(task.completed_at) }}
                  </div>
                  <div v-else-if="task.started_at" class="text-xs text-gray-400">
                    시작: {{ formatTaskDate(task.started_at) }}
                  </div>
                </div>

                <!-- 액션 버튼 -->
                <div class="flex gap-1 flex-shrink-0">
                  <button v-if="task.status === 'PENDING'" @click="startTaskAction(task.id)"
                    class="px-2 py-0.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700">시작</button>
                  <button v-if="task.status === 'IN_PROGRESS'" @click="completeTaskAction(task.id)"
                    class="px-2 py-0.5 text-xs bg-green-600 text-white rounded hover:bg-green-700">완료</button>
                  <button @click="deleteTaskAction(task.id)"
                    class="px-2 py-0.5 text-xs text-red-400 hover:text-red-600">삭제</button>
                </div>
              </div>
            </div>
            <p v-else class="text-sm text-gray-400">등록된 공정이 없습니다. [+ 공정 추가]로 추가하세요.</p>
          </div>

          <!-- 타임라인 (수정 모드) -->
          <div v-if="isEdit && workOrder" class="mb-6">
            <h3 class="text-lg font-semibold mb-3">진행 이력</h3>
            <div class="border rounded-lg p-4 bg-gray-50">
              <!-- process_logs 기반 (담당자 표시) -->
              <div v-if="processLogs.length > 0" class="space-y-3">
                <div v-for="log in processLogs" :key="log.id" class="flex items-center gap-3">
                  <div class="w-28 text-sm font-medium text-gray-600">{{ log.process_name }}</div>
                  <div class="text-sm text-gray-800">{{ formatDateTime(log.completed_at) }}</div>
                  <span v-if="log.worker_name" class="text-xs text-blue-600 font-medium bg-blue-50 px-2 py-0.5 rounded">
                    {{ log.worker_name }}
                  </span>
                  <span v-if="log.duration_hours" class="text-xs text-gray-400">
                    ({{ formatDuration(log.duration_hours) }})
                  </span>
                </div>
              </div>
              <!-- fallback: 날짜 필드 기반 (로그가 없을 때) -->
              <div v-else class="space-y-3">
                <div v-if="workOrder.received_date" class="flex items-center gap-3">
                  <div class="w-28 text-sm text-gray-500">접수</div>
                  <div class="text-sm">{{ formatDateTime(workOrder.received_date) }}</div>
                </div>
                <div v-if="workOrder.approved_date" class="flex items-center gap-3">
                  <div class="w-28 text-sm text-gray-500">승인</div>
                  <div class="text-sm">{{ formatDateTime(workOrder.approved_date) }}</div>
                </div>
                <div v-if="workOrder.shipping_completed_date" class="flex items-center gap-3">
                  <div class="w-28 text-sm text-gray-500">출하완료</div>
                  <div class="text-sm">{{ formatDateTime(workOrder.shipping_completed_date) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 푸터 -->
      <div class="flex justify-between items-center px-6 py-4 border-t bg-gray-50">
        <!-- 왼쪽: 상태 변경 버튼 -->
        <div v-if="isEdit" class="flex gap-2">
          <!-- 롤백 버튼 -->
          <button
            v-if="canRollback"
            type="button"
            @click="handleRollback"
            class="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
          >
            {{ rollbackLabels[workOrder?.status || ''] }} 롤백
          </button>
          <!-- 취소 버튼 -->
          <button
            v-if="canCancel"
            type="button"
            @click="handleCancel"
            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            취소
          </button>
          <!-- 복원 버튼 -->
          <button
            v-if="canRestore"
            type="button"
            @click="handleRestore"
            class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            복원
          </button>
        </div>
        <div v-else></div>

        <!-- 오른쪽: 닫기/저장 버튼 -->
        <div class="flex gap-3">
          <button
            @click="$emit('close')"
            class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            {{ isEdit ? '닫기' : '취소' }}
          </button>
          <button
            v-if="isEditable"
            @click="handleSave"
            :disabled="saving || !canSave"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ saving ? '저장 중...' : '저장' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 부품 검색 모달 -->
    <PartSearchModal
      :show="showPartSearch"
      @close="showPartSearch = false"
      @select="handleProductSelect"
    />

    <!-- 거래처 검색 모달 -->
    <SupplierSearchModal
      :show="showCustomerSearch"
      partner-type="all"
      @close="showCustomerSearch = false"
      @select="handleCustomerSelect"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import {
  workOrderApi,
  type WorkOrder,
  type WorkOrderCreate,
  type WorkOrderUpdate,
  type WorkOrderStatus,
  type WorkOrderProduct,
  type WorkOrderProductCreate,
  type BOMPreviewResponse,
  woStatusLabels,
} from '@/api/workOrder'
import PartSearchModal from '@/views/production/components/PartSearchModal.vue'
import ProductionAvailabilityCard from '@/views/production/components/ProductionAvailabilityCard.vue'
import SupplierSearchModal from '@/views/production/components/SupplierSearchModal.vue'
import type { BusinessPartner } from '@/api/partner'

// Props
const props = defineProps<{
  workOrderId: number | null
}>()

// Emits
const emit = defineEmits<{
  close: []
  saved: []
}>()

// 상태
const loading = ref(false)
const saving = ref(false)
const workOrder = ref<WorkOrder | null>(null)

// v0.31.0: 작업지시 체인
const woChain = ref<{ parent: any; children: any[] }>({ parent: null, children: [] })

// v0.31.0: 공정 로그 (진행 이력 + 담당자)
const processLogs = ref<any[]>([])

function formatDuration(hours: number): string {
  if (hours < 1/60) return '1분 미만'
  if (hours < 1) return `${Math.round(hours * 60)}분`
  if (hours < 24) {
    const h = Math.floor(hours)
    const m = Math.round((hours - h) * 60)
    return m > 0 ? `${h}시간 ${m}분` : `${h}시간`
  }
  const d = Math.floor(hours / 24)
  const h = Math.round(hours % 24)
  return h > 0 ? `${d}일 ${h}시간` : `${d}일`
}

async function loadProcessLogs() {
  if (!props.workOrderId) return
  try {
    const res = await apiClient.get(`/work-orders/${props.workOrderId}/process-logs`)
    processLogs.value = res.data || []
  } catch { processLogs.value = [] }
}

async function loadChain() {
  if (!props.workOrderId) return
  try {
    const data = await workOrderApi.getChain(props.workOrderId)
    woChain.value = { parent: data.parent, children: data.children }
  } catch { woChain.value = { parent: null, children: [] } }
}
const showPartSearch = ref(false)
const showCustomerSearch = ref(false)
const showBomItems = ref(false)  // 구성부품 접기/펼치기 (기본: 접힘)
const showScheduleDates = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFiles = ref<File[]>([])
const isDragging = ref(false)

// API Base URL — apiClient 와 같은 주소를 쓴다 (운용: 같은 origin 의 /api/v1, 개발: vite 프록시)
function getApiBaseUrl(): string {
  return apiClient.defaults.baseURL || '/api/v1'
}

// Blob URL 캐시 (깜빡임 방지)
const blobUrlCache = new Map<File, string>()
function getCachedBlobUrl(file: File): string {
  if (!blobUrlCache.has(file)) {
    blobUrlCache.set(file, URL.createObjectURL(file))
  }
  return blobUrlCache.get(file)!
}

// 컴포넌트 해제 시 Blob URL 정리
onBeforeUnmount(() => {
  blobUrlCache.forEach(url => URL.revokeObjectURL(url))
  blobUrlCache.clear()
})

// 롤백 라벨
const rollbackLabels: Record<string, string> = {
  'APPROVED': '접수로',
  'ISSUED': '승인으로',
  'IN_PROGRESS': '출고로',
  'INSPECTION': '작업중으로',
  'PACKED': '검사로',
}

// v0.19.0: 제품 목록 (다중 제품 지원)
interface ProductListItem {
  product_part_id: number
  order_quantity: number
  completed_quantity?: number
  defective_quantity?: number
  line_remarks?: string
  sort_order?: number
  product_part?: {
    id: number
    part_number: string
    part_number_display?: string
    part_name: string
  }
}
const productList = ref<ProductListItem[]>([])

// 선택된 거래처
const selectedCustomer = ref<{
  id: number
  partner_code: string
  partner_name: string
} | null>(null)

// BOM 미리보기 (다중 제품)
const bomPreviews = ref<BOMPreviewResponse[]>([])

// 폼 데이터
const formData = reactive<WorkOrderCreate & WorkOrderUpdate>({
  product_part_id: 0,
  order_quantity: 1,
  customer_id: undefined,
  customer_order_no: '',
  priority: 0,
  remarks: '',
  auto_expand_bom: true,
  issue_scheduled_date: '',
  production_scheduled_date: '',
  inspection_scheduled_date: '',
  packing_scheduled_date: '',
  shipping_scheduled_date: '',
})

// v0.20.0: 생산요청에서 작업지시서 생성 시 참조
const productionRequestId = ref<number | null>(null)
// v0.22.0: 생산요청서 첨부파일 (생성 시 전달받은 데이터)
const sourceAttachments = ref<Array<{ filename: string; filepath: string; mimetype: string; size?: number }>>([])

// 계산된 속성
const isEdit = computed(() => props.workOrderId !== null)

// v0.22.0: 생산요청서 첨부파일 (생성 시 sourceAttachments, 수정 시 workOrder에서 참조)
const prAttachmentFiles = computed(() => {
  if (sourceAttachments.value.length > 0) return sourceAttachments.value
  if (isEdit.value && workOrder.value?.source_request_attachments?.length) {
    return workOrder.value.source_request_attachments
  }
  return []
})

// v0.22.0: 현재 참조 중인 생산요청 ID (생성/수정 모두 사용)
const currentPRId = computed(() => {
  return productionRequestId.value || workOrder.value?.production_request_id || null
})

// 취소, 출하완료 상태가 아니면 수정 가능
const isEditable = computed(() => {
  if (!isEdit.value) return true
  const status = workOrder.value?.status
  return status !== 'CANCELLED' && status !== 'SHIPPED'
})

// 롤백 가능 여부 (RECEIVED, SHIPPED, CANCELLED는 롤백 불가)
const canRollback = computed(() => {
  const status = workOrder.value?.status
  return status && !['RECEIVED', 'SHIPPED', 'CANCELLED'].includes(status)
})

// 취소 가능 여부 (출하완료, 취소 상태가 아니면 취소 가능)
const canCancel = computed(() => {
  const status = workOrder.value?.status
  return status && status !== 'SHIPPED' && status !== 'CANCELLED'
})

// 복원 가능 여부 (취소 상태만 복원 가능)
const canRestore = computed(() => {
  const status = workOrder.value?.status
  return status === 'CANCELLED'
})

const canSave = computed(() => {
  // v0.19.0: 제품 목록이 하나 이상 있어야 함
  return productList.value.length > 0 && productList.value.every(p => p.order_quantity > 0)
})

// 공정 스텝퍼
const statusOrder: WorkOrderStatus[] = ['RECEIVED', 'APPROVED', 'ISSUED', 'IN_PROGRESS', 'INSPECTION', 'PACKED', 'SHIPPED']
const stepLabels: Record<string, string> = {
  RECEIVED: '접수', APPROVED: '승인', ISSUED: '부품출고',
  IN_PROGRESS: '작업중', INSPECTION: '검사', PACKED: '포장완료', SHIPPED: '출하완료',
}

const stepperSteps = computed(() => {
  const current = workOrder.value?.status as WorkOrderStatus
  const currentIdx = statusOrder.indexOf(current)
  return statusOrder.map((status, idx) => ({
    status,
    label: stepLabels[status],
    state: idx < currentIdx ? 'completed' as const
         : idx === currentIdx ? 'current' as const
         : 'pending' as const,
  }))
})

// 데이터 로드
async function loadData() {
  if (!props.workOrderId) return

  loading.value = true
  try {
    workOrder.value = await workOrderApi.getById(props.workOrderId)

    // 폼 데이터 설정
    formData.product_part_id = workOrder.value.product_part_id
    formData.order_quantity = workOrder.value.order_quantity
    formData.customer_id = workOrder.value.customer_id
    formData.customer_order_no = workOrder.value.customer_order_no || ''
    formData.priority = workOrder.value.priority
    formData.remarks = workOrder.value.remarks || ''
    formData.issue_scheduled_date = workOrder.value.issue_scheduled_date?.split('T')[0] || ''
    formData.production_scheduled_date = workOrder.value.production_scheduled_date?.split('T')[0] || ''
    formData.inspection_scheduled_date = workOrder.value.inspection_scheduled_date?.split('T')[0] || ''
    formData.packing_scheduled_date = workOrder.value.packing_scheduled_date?.split('T')[0] || ''
    formData.shipping_scheduled_date = workOrder.value.shipping_scheduled_date?.split('T')[0] || ''

    // v0.19.0: 제품 목록 설정
    if (workOrder.value.products && workOrder.value.products.length > 0) {
      productList.value = workOrder.value.products.map(p => ({
        product_part_id: p.product_part_id,
        order_quantity: p.order_quantity,
        completed_quantity: p.completed_quantity,
        defective_quantity: p.defective_quantity,
        line_remarks: p.line_remarks,
        sort_order: p.sort_order,
        product_part: p.product_part,
      }))
    } else if (workOrder.value.product_part) {
      // 기존 호환성: 단일 제품
      productList.value = [{
        product_part_id: workOrder.value.product_part_id!,
        order_quantity: workOrder.value.order_quantity || 0,
        completed_quantity: workOrder.value.completed_quantity,
        defective_quantity: workOrder.value.defective_quantity,
        product_part: {
          id: workOrder.value.product_part.id,
          part_number: workOrder.value.product_part.part_number,
          part_number_display: workOrder.value.product_part.part_number_display,
          part_name: workOrder.value.product_part.part_name,
        },
      }]
    }

    // 선택된 거래처 설정
    if (workOrder.value.customer) {
      selectedCustomer.value = {
        id: workOrder.value.customer.id,
        partner_code: workOrder.value.customer.partner_code || '',
        partner_name: workOrder.value.customer.name || workOrder.value.customer.partner_name || '',
      }
    }
  } catch (error) {
    console.error('작업지시서 조회 실패:', error)
    alert('작업지시서 정보를 불러오는데 실패했습니다.')
    emit('close')
  } finally {
    loading.value = false
  }
}

// v0.19.0: 제품 선택 (다중 제품)
function handleProductSelect(part: any) {
  // 이미 추가된 제품인지 확인
  const exists = productList.value.some(p => p.product_part_id === part.id)
  if (exists) {
    alert('이미 추가된 제품입니다.')
    showPartSearch.value = false
    return
  }

  // 제품 목록에 추가
  productList.value.push({
    product_part_id: part.id,
    order_quantity: 1,
    product_part: {
      id: part.id,
      part_number: part.part_number,
      part_number_display: part.part_number_display,
      part_name: part.part_name,
    },
  })
  showPartSearch.value = false

  // BOM 미리보기 로드
  loadBOMPreviews()
}

// v0.19.0: 제품 삭제
function removeProduct(index: number) {
  productList.value.splice(index, 1)
  loadBOMPreviews()
}

// v0.19.0: 제품 수량 변경
function onProductQuantityChange(index: number) {
  loadBOMPreviews()
}

// 거래처 선택
function handleCustomerSelect(partner: BusinessPartner) {
  selectedCustomer.value = {
    id: partner.id,
    partner_code: partner.partner_code,
    partner_name: partner.partner_name,
  }
  formData.customer_id = partner.id
  showCustomerSearch.value = false
}

// 거래처 선택 해제
function clearCustomer() {
  selectedCustomer.value = null
  formData.customer_id = undefined
}

// v0.19.0: 다중 제품 BOM 미리보기 로드
async function loadBOMPreviews() {
  if (productList.value.length === 0) {
    bomPreviews.value = []
    return
  }

  try {
    const previews: BOMPreviewResponse[] = []
    for (const product of productList.value) {
      if (product.product_part_id && product.order_quantity > 0) {
        const preview = await workOrderApi.getBOMPreview(
          product.product_part_id,
          product.order_quantity
        )
        previews.push(preview)
      }
    }
    bomPreviews.value = previews
  } catch (error) {
    console.error('BOM 미리보기 조회 실패:', error)
    bomPreviews.value = []
  }
}

// 저장
async function handleSave() {
  if (!canSave.value) return

  saving.value = true
  try {
    // 빈 정수 정규화 — Pydantic이 빈 문자열을 정수로 거부함
    const _priority = (typeof formData.priority === 'number' && !Number.isNaN(formData.priority))
      ? formData.priority
      : undefined

    if (isEdit.value && props.workOrderId) {
      // 수정
      const updateData: WorkOrderUpdate = {
        customer_id: formData.customer_id || undefined,
        customer_order_no: formData.customer_order_no || undefined,
        priority: _priority,
        remarks: formData.remarks || undefined,
        issue_scheduled_date: formData.issue_scheduled_date || undefined,
        production_scheduled_date: formData.production_scheduled_date || undefined,
        inspection_scheduled_date: formData.inspection_scheduled_date || undefined,
        packing_scheduled_date: formData.packing_scheduled_date || undefined,
        shipping_scheduled_date: formData.shipping_scheduled_date || undefined,
      }
      await workOrderApi.update(props.workOrderId, updateData)
      alert('수정되었습니다.')
    } else {
      // v0.19.0: 생성 (다중 제품), v0.20.0: 생산요청 연결
      const createData: WorkOrderCreate = {
        products: productList.value.map((p, idx) => ({
          product_part_id: p.product_part_id,
          order_quantity: (typeof p.order_quantity === 'number' && !Number.isNaN(p.order_quantity)) ? p.order_quantity : 0,
          line_remarks: p.line_remarks,
          sort_order: idx,
        })),
        production_request_id: productionRequestId.value || undefined,  // v0.20.0
        customer_id: formData.customer_id || undefined,
        customer_order_no: formData.customer_order_no || undefined,
        priority: _priority,
        remarks: formData.remarks || undefined,
        auto_expand_bom: true,
        issue_scheduled_date: formData.issue_scheduled_date || undefined,
        production_scheduled_date: formData.production_scheduled_date || undefined,
        inspection_scheduled_date: formData.inspection_scheduled_date || undefined,
        packing_scheduled_date: formData.packing_scheduled_date || undefined,
        shipping_scheduled_date: formData.shipping_scheduled_date || undefined,
      }
      const newWorkOrder = await workOrderApi.create(createData)

      // 선택된 파일 업로드
      if (selectedFiles.value.length > 0) {
        for (const file of selectedFiles.value) {
          try {
            await workOrderApi.uploadDocument(newWorkOrder.id, file)
          } catch (error) {
            console.error('파일 업로드 실패:', error)
          }
        }
      }

      // v0.22.0: 생산요청에서 생성한 경우, WO 등록 완료 후 PR 승인 처리
      if (productionRequestId.value) {
        try {
          const { productionRequestApi } = await import('@/api/productionRequest')
          await productionRequestApi.approve(productionRequestId.value)
        } catch (approveError) {
          console.error('생산요청 승인 처리 실패:', approveError)
        }
      }

      alert('작업지시서가 등록되었습니다.')
    }
    emit('saved')
  } catch (error: any) {
    console.error('저장 실패:', error)
    alert(error.response?.data?.detail?.message || '저장에 실패했습니다.')
  } finally {
    saving.value = false
  }
}

// 롤백 처리
async function handleRollback() {
  if (!workOrder.value || !props.workOrderId) return

  const reason = prompt('롤백 사유를 입력하세요 (선택사항):')
  if (reason === null) return // 취소됨

  try {
    saving.value = true
    await workOrderApi.rollback(props.workOrderId, reason || undefined)
    alert('이전 상태로 롤백되었습니다.')
    emit('saved')
  } catch (error: any) {
    console.error('롤백 실패:', error)
    alert(error.response?.data?.detail?.message || error.response?.data?.detail || '롤백에 실패했습니다.')
  } finally {
    saving.value = false
  }
}

// 취소 처리
async function handleCancel() {
  if (!workOrder.value || !props.workOrderId) return

  if (!confirm('작업지시서를 취소하시겠습니까? 출고된 부품은 재고로 복구됩니다.')) return

  const reason = prompt('취소 사유를 입력하세요 (선택사항):')
  if (reason === null) return // 취소됨

  try {
    saving.value = true
    await workOrderApi.cancel(props.workOrderId, reason || undefined)
    alert('작업지시서가 취소되었습니다.')
    emit('saved')
  } catch (error: any) {
    console.error('취소 실패:', error)
    alert(error.response?.data?.detail?.message || error.response?.data?.detail || '취소에 실패했습니다.')
  } finally {
    saving.value = false
  }
}

// 복원 처리
async function handleRestore() {
  if (!workOrder.value || !props.workOrderId) return

  if (!confirm('취소된 작업지시서를 복원하시겠습니까?\n출고 상태였던 경우 승인 상태로 복원됩니다.')) return

  const reason = prompt('복원 사유를 입력하세요 (선택사항):')
  if (reason === null) return // 취소됨

  try {
    saving.value = true
    await workOrderApi.restore(props.workOrderId, reason || undefined)
    alert('작업지시서가 복원되었습니다.')
    emit('saved')
  } catch (error: any) {
    console.error('복원 실패:', error)
    alert(error.response?.data?.detail?.message || error.response?.data?.detail || '복원에 실패했습니다.')
  } finally {
    saving.value = false
  }
}

// v0.21.0: 원본 요청서 수정 알림 확인
async function handleAcknowledgeModification() {
  if (!workOrder.value || !props.workOrderId) return

  try {
    await workOrderApi.acknowledgeModification(props.workOrderId)
    // 플래그 리셋
    workOrder.value.source_request_modified = false
    emit('saved')  // 부모에게 알려 목록 새로고침
  } catch (error: any) {
    console.error('알림 확인 실패:', error)
    alert(error.response?.data?.detail?.message || '알림 확인에 실패했습니다.')
  }
}

// 파일 선택 처리
function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files) return
  addFilesToList(Array.from(input.files))
  input.value = ''
}

// 기존 파일 삭제
async function handleDeleteFile(fileIndex: number) {
  if (!props.workOrderId) return

  if (!confirm('첨부파일을 삭제하시겠습니까?')) return

  try {
    await workOrderApi.deleteDocument(props.workOrderId, fileIndex)
    await loadData()
    alert('파일이 삭제되었습니다.')
  } catch (error: any) {
    console.error('파일 삭제 실패:', error)
    alert(error.response?.data?.detail?.message || '파일 삭제에 실패했습니다.')
  }
}

// 선택된 파일 제거 (신규 등록 시)
function removeSelectedFile(index: number) {
  const file = selectedFiles.value[index]
  if (file && blobUrlCache.has(file)) {
    URL.revokeObjectURL(blobUrlCache.get(file)!)
    blobUrlCache.delete(file)
  }
  selectedFiles.value.splice(index, 1)
}

// ==================== 파일 분류 및 인라인 미리보기 ====================

function isImageMime(mimetype?: string): boolean {
  return !!mimetype && mimetype.startsWith('image/')
}
function isPdfMime(mimetype?: string): boolean {
  return !!mimetype && mimetype.includes('pdf')
}

// PR 첨부파일 URL (절대 경로)
function getPRAttachmentUrl(fileIndex: number): string {
  if (!currentPRId.value) return ''
  return `${getApiBaseUrl()}/production-requests/${currentPRId.value}/attachments/${fileIndex}/preview`
}
function getPRAttachmentDownloadUrl(fileIndex: number): string {
  if (!currentPRId.value) return ''
  return `${getApiBaseUrl()}/production-requests/${currentPRId.value}/attachments/${fileIndex}/download`
}

// WO 기존 파일 URL (절대 경로)
function getWOFileUrl(fileIndex: number): string {
  if (!workOrder.value?.id) return ''
  return `${getApiBaseUrl()}/work-orders/${workOrder.value.id}/files/${fileIndex}/preview`
}
function getWOFileDownloadUrl(fileIndex: number): string {
  if (!workOrder.value?.id) return ''
  return `${getApiBaseUrl()}/work-orders/${workOrder.value.id}/files/${fileIndex}/download`
}

// PR 첨부파일 분류
const prImageFiles = computed(() =>
  prAttachmentFiles.value.map((f, i) => ({ ...f, originalIndex: i })).filter(f => isImageMime(f.mimetype))
)
const prPdfFiles = computed(() =>
  prAttachmentFiles.value.map((f, i) => ({ ...f, originalIndex: i })).filter(f => isPdfMime(f.mimetype))
)
const prOtherFiles = computed(() =>
  prAttachmentFiles.value.map((f, i) => ({ ...f, originalIndex: i })).filter(f => !isImageMime(f.mimetype) && !isPdfMime(f.mimetype))
)

// WO 기존 파일 분류
const woExistingImageFiles = computed(() =>
  (workOrder.value?.document_files || []).map((f: any, i: number) => ({ ...f, originalIndex: i })).filter((f: any) => isImageMime(f.content_type))
)
const woExistingPdfFiles = computed(() =>
  (workOrder.value?.document_files || []).map((f: any, i: number) => ({ ...f, originalIndex: i })).filter((f: any) => isPdfMime(f.content_type))
)
const woExistingOtherFiles = computed(() =>
  (workOrder.value?.document_files || []).map((f: any, i: number) => ({ ...f, originalIndex: i })).filter((f: any) => !isImageMime(f.content_type) && !isPdfMime(f.content_type))
)

// 신규 파일 분류 (blob URL 캐싱)
const newImageFiles = computed(() =>
  selectedFiles.value.map((f, i) => ({ file: f, originalIndex: i, previewUrl: getCachedBlobUrl(f) })).filter(f => f.file.type.startsWith('image/'))
)
const newPdfFiles = computed(() =>
  selectedFiles.value.map((f, i) => ({ file: f, originalIndex: i, previewUrl: getCachedBlobUrl(f) })).filter(f => f.file.type.includes('pdf'))
)
const newOtherFiles = computed(() =>
  selectedFiles.value.map((f, i) => ({ file: f, originalIndex: i })).filter(f => !f.file.type.startsWith('image/') && !f.file.type.includes('pdf'))
)

// 클립보드 붙여넣기
function handlePaste(event: ClipboardEvent) {
  if (!isEditable.value) return
  const items = event.clipboardData?.items
  if (!items) return
  const pastedFiles: File[] = []
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (item && item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        const ext = file.type.split('/')[1] || 'png'
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
        const renamedFile = new File([file], `clipboard-${timestamp}.${ext}`, { type: file.type })
        pastedFiles.push(renamedFile)
      }
    }
  }
  if (pastedFiles.length > 0) {
    event.preventDefault()
    addFilesToList(pastedFiles)
  }
}

// 드래그앤드롭
function handleDrop(event: DragEvent) {
  isDragging.value = false
  const files = event.dataTransfer?.files
  if (!files || files.length === 0) return
  addFilesToList(Array.from(files))
}

// 파일 목록에 추가 (신규/수정 모드 공용)
function addFilesToList(files: File[]) {
  if (isEdit.value && props.workOrderId) {
    files.forEach(async (file) => {
      try {
        await workOrderApi.uploadDocument(props.workOrderId!, file)
        await loadData()
      } catch (error: any) {
        console.error('파일 업로드 실패:', error)
        alert(`파일 업로드 실패: ${file.name}`)
      }
    })
  } else {
    selectedFiles.value = [...selectedFiles.value, ...files]
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// 포맷
function formatDateTime(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('ko-KR')
}

// v0.20.0: 생산요청에서 작업지시서 생성 시 데이터 로드
async function loadFromProductionRequest() {
  const prData = sessionStorage.getItem('createFromPR')
  if (!prData) return

  try {
    const data = JSON.parse(prData)
    sessionStorage.removeItem('createFromPR') // 사용 후 삭제

    productionRequestId.value = data.production_request_id

    // v0.22.0: 첨부파일 정보 저장 (생산요청서 첨부자료 표시용)
    if (data.attachment_files && data.attachment_files.length > 0) {
      sourceAttachments.value = data.attachment_files
    }

    // 고객 주문번호 설정
    if (data.customer_order_no) {
      formData.customer_order_no = data.customer_order_no
    }

    // 고객사 설정 (ID로 조회)
    if (data.customer_id) {
      formData.customer_id = data.customer_id
      try {
        const { partnerApi } = await import('@/api/partner')
        const res = await partnerApi.getById(data.customer_id)
        const customerData = res.data
        selectedCustomer.value = {
          id: customerData.id,
          partner_code: customerData.partner_code || '',
          partner_name: customerData.partner_name,
        }
      } catch (error) {
        console.error('고객사 조회 실패:', error)
      }
    }

    // v0.22.0: 다중 제품 항목 처리 (PR items에 포함된 product_part 정보를 직접 사용)
    const items = data.items as Array<any> | undefined
    if (items && items.length > 0) {
      for (const item of items) {
        const pp = item.product_part
        if (pp) {
          // PR 응답에 포함된 product_part 정보 직접 사용
          productList.value.push({
            product_part_id: item.product_part_id || pp.id,
            order_quantity: item.requested_quantity || 1,
            line_remarks: item.line_remarks,
            product_part: {
              id: pp.id,
              part_number: pp.part_number || '',
              part_number_display: pp.part_number_display,
              part_name: pp.part_name || pp.part_name_en || '',
            },
          })
        } else if (item.product_part_id) {
          // product_part 없으면 API 조회 fallback
          try {
            const { partApi } = await import('@/api/parts')
            const partRes = await partApi.getById(item.product_part_id)
            const partData = partRes.data
            productList.value.push({
              product_part_id: partData.id,
              order_quantity: item.requested_quantity || 1,
              line_remarks: item.line_remarks,
              product_part: {
                id: partData.id,
                part_number: partData.part_number || '',
                part_number_display: partData.part_number_display,
                part_name: partData.part_name || partData.part_name_en || '',
              },
            })
          } catch (error) {
            console.error('제품 조회 실패:', error)
          }
        }
      }
      loadBOMPreviews()
    } else if (data.product_part_id) {
      // deprecated: 단일 제품 호환
      try {
        const { partApi } = await import('@/api/parts')
        const partRes = await partApi.getById(data.product_part_id)
        const partData = partRes.data
        productList.value.push({
          product_part_id: partData.id,
          order_quantity: data.order_quantity || 1,
          product_part: {
            id: partData.id,
            part_number: partData.part_number || '',
            part_number_display: partData.part_number_display,
            part_name: partData.part_name || partData.part_name_en || '',
          },
        })
        loadBOMPreviews()
      } catch (error) {
        console.error('제품 조회 실패:', error)
      }
    }
  } catch (error) {
    console.error('생산요청 데이터 파싱 실패:', error)
  }
}

// ==================== 공정 체크리스트 (v0.29.0) ====================
import { workOrderTaskApi, type WorkOrderTask } from '@/api/workOrderTask'
import apiClient from '@/api/client'

const tasks = ref<WorkOrderTask[]>([])
const showAddTask = ref(false)
const newTaskName = ref('')
const newTaskTeam = ref('')
const templates = ref<any[]>([])

async function loadTemplates() {
  try {
    const res = await apiClient.get('/process-templates')
    templates.value = res.data
  } catch { /* ignore */ }
}

async function applyTemplate(event: Event) {
  const select = event.target as HTMLSelectElement
  const templateId = select.value
  if (!templateId || !props.workOrderId) return
  if (!confirm('선택한 템플릿의 공정을 추가하시겠습니까?')) { select.value = ''; return }
  try {
    await apiClient.post(`/process-templates/${templateId}/apply/${props.workOrderId}`)
    loadTasks()
  } catch { /* ignore */ }
  select.value = ''
}

async function loadTasks() {
  if (!props.workOrderId) return
  try {
    const res = await workOrderTaskApi.getTasks(props.workOrderId)
    tasks.value = res.data
  } catch { /* ignore */ }
}

async function addTask() {
  if (!props.workOrderId || !newTaskName.value.trim()) return
  await workOrderTaskApi.createTask(props.workOrderId, {
    task_name: newTaskName.value.trim(),
    assigned_team: newTaskTeam.value.trim() || undefined,
    sort_order: tasks.value.length,
  })
  newTaskName.value = ''
  newTaskTeam.value = ''
  showAddTask.value = false
  loadTasks()
}

async function startTaskAction(taskId: number) {
  if (!props.workOrderId) return
  await workOrderTaskApi.startTask(props.workOrderId, taskId)
  loadTasks()
}

async function completeTaskAction(taskId: number) {
  if (!props.workOrderId) return
  await workOrderTaskApi.completeTask(props.workOrderId, taskId)
  loadTasks()
}

async function deleteTaskAction(taskId: number) {
  if (!props.workOrderId || !confirm('이 공정을 삭제하시겠습니까?')) return
  await workOrderTaskApi.deleteTask(props.workOrderId, taskId)
  loadTasks()
}

function formatTaskDate(d?: string) {
  if (!d) return ''
  const date = new Date(d)
  return `${date.getMonth()+1}.${date.getDate()} ${String(date.getHours()).padStart(2,'0')}:${String(date.getMinutes()).padStart(2,'0')}`
}

// 초기화
onMounted(() => {
  loadTemplates()
  if (isEdit.value) {
    loadData()
    loadTasks()
    loadChain()  // v0.31.0
    loadProcessLogs()  // v0.31.0
  } else {
    // v0.20.0: 생산요청에서 작업지시서 생성 시 데이터 로드
    loadFromProductionRequest()
  }
})
</script>
