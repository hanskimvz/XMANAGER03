<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-6xl mx-4 max-h-[90vh] flex flex-col overflow-hidden">
      <!-- 헤더 (고정) -->
      <div class="px-6 py-4 border-b flex justify-between items-center shrink-0">
        <h2 class="text-xl font-bold text-gray-800">생산 요청서 상세</h2>
        <button @click="$emit('close')" class="text-gray-500 hover:text-gray-700">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 스크롤 영역 (헤더 제외 본문만 스크롤) -->
      <div class="flex-1 overflow-y-auto min-h-0">
      <!-- 로딩 -->
      <div v-if="loading" class="p-6 text-center text-gray-500">로딩 중...</div>

      <!-- 내용 -->
      <div v-else-if="request" class="p-6">
        <!-- 기본 정보 -->
        <div class="grid grid-cols-2 gap-4 mb-6">
          <div>
            <span class="text-sm text-gray-500">요청번호</span>
            <p class="font-medium">{{ request.request_number }}</p>
          </div>
          <div>
            <span class="text-sm text-gray-500">상태</span>
            <p>
              <span :class="['px-2 py-1 text-xs rounded-full', prStatusStyles[request.status]]">
                {{ prStatusLabels[request.status] }}
              </span>
            </p>
          </div>
          <div>
            <span class="text-sm text-gray-500">고객사</span>
            <p class="font-medium">{{ request.customer?.partner_name || '-' }}</p>
          </div>
          <div>
            <span class="text-sm text-gray-500">우선순위</span>
            <p>
              <span :class="['px-2 py-1 text-xs rounded-full', priorityStyles[request.priority]]">
                {{ priorityLabels[request.priority] }}
              </span>
            </p>
          </div>
          <div>
            <span class="text-sm text-gray-500">PI (Proforma Invoice)</span>
            <p class="font-medium">{{ request.pi_number || '-' }}</p>
          </div>
          <div>
            <span class="text-sm text-gray-500">PO (고객 주문번호)</span>
            <p class="font-medium">{{ request.customer_order_no || '-' }}</p>
          </div>
          <div>
            <span class="text-sm text-gray-500">희망 납기일</span>
            <p class="font-medium">{{ request.due_date ? formatDate(request.due_date) : '-' }}</p>
          </div>
          <div>
            <span class="text-sm text-gray-500">입금현황</span>
            <p>
              <span :class="['px-2 py-1 text-xs rounded-full', paymentStatusStyle(request.payment_status)]">
                {{ paymentStatusLabel(request.payment_status) }}
              </span>
            </p>
          </div>
          <div>
            <span class="text-sm text-gray-500">요청일시</span>
            <p class="font-medium">{{ request.requested_at ? formatDateTime(request.requested_at) : '-' }}</p>
          </div>
          <div v-if="request.approved_at">
            <span class="text-sm text-gray-500">승인일시</span>
            <p class="font-medium">{{ formatDateTime(request.approved_at) }}</p>
          </div>
          <div>
            <span class="text-sm text-gray-500">영업담당자</span>
            <p class="font-medium">{{ request.prepared_by_name || '-' }}</p>
          </div>
          <div v-if="(request as any).country">
            <span class="text-sm text-gray-500">국가</span>
            <p class="font-medium">{{ (request as any).country }}</p>
          </div>
          <div v-if="(request as any).production_period">
            <span class="text-sm text-gray-500">생산기간</span>
            <p class="font-medium">{{ (request as any).production_period }}</p>
          </div>
          <div v-if="(request as any).destination">
            <span class="text-sm text-gray-500">도착지 (DESTINATION)</span>
            <p class="font-medium">{{ (request as any).destination }}</p>
          </div>
          <div v-if="(request as any).shipping_mark" class="col-span-2">
            <span class="text-sm text-gray-500">SHIPPING MARK</span>
            <p class="font-medium whitespace-pre-wrap">{{ (request as any).shipping_mark }}</p>
          </div>
          <div v-if="(request as any).consignee" class="col-span-2">
            <span class="text-sm text-gray-500">CONSIGNEE (수하인)</span>
            <p class="font-medium whitespace-pre-wrap">{{ (request as any).consignee }}</p>
          </div>
        </div>

        <!-- 도면 / 첨부파일 (생산팀 우선 확인 — 최상단 배치) -->
        <div class="mb-6 border rounded-lg p-4 transition-colors"
          :class="drawingDragOver ? 'border-blue-500 border-2 border-dashed bg-blue-100/60' : 'border-blue-200 bg-blue-50/40'"
          @dragover.prevent="canUploadDrawing && (drawingDragOver = true)"
          @dragleave.prevent="drawingDragOver = false"
          @drop.prevent="onDrawingDrop">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-bold text-blue-800 flex items-center gap-1.5">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              도면 / 첨부파일 ({{ request.attachment_files?.length || 0 }})
            </h3>
            <label v-if="canUploadDrawing" class="text-xs px-3 py-1.5 bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700">
              + 도면 업로드
              <input type="file" multiple class="hidden"
                accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.xlsx,.xls,.doc,.docx"
                @change="onDrawingSelected" />
            </label>
          </div>
          <p v-if="canUploadDrawing" class="text-[11px] text-blue-500 mb-2">
            📎 파일을 이 영역에 <strong>끌어다 놓거나(드래그 앤 드롭)</strong> "도면 업로드"로 추가 (여러 개 가능)
          </p>
          <div v-if="drawingDragOver" class="text-center text-sm text-blue-700 font-medium py-3">여기에 놓으면 업로드됩니다</div>
          <div v-if="uploadingDrawing" class="text-xs text-blue-600 mb-2">업로드 중...</div>

          <div v-if="!request.attachment_files || request.attachment_files.length === 0"
            class="text-sm text-gray-400 py-4 text-center">
            첨부된 도면이 없습니다.{{ canUploadDrawing ? ' 우측 "도면 업로드"로 추가하세요.' : '' }}
          </div>

          <!-- 이미지 인라인 미리보기 (큰 사이즈) -->
          <div v-if="detailImageFiles.length > 0" class="mb-3 space-y-3">
            <div
              v-for="(img, idx) in detailImageFiles"
              :key="'dimg-' + idx"
              class="border border-gray-200 rounded-lg overflow-hidden bg-gray-50"
            >
              <img
                v-if="attachmentUrls[img.index]"
                :src="attachmentUrls[img.index]"
                :alt="img.filename"
                class="w-full max-h-[500px] object-contain bg-white"
              />
              <div v-else class="p-8 text-center text-xs text-gray-400 bg-white">불러오는 중...</div>
              <div class="px-3 py-1.5 bg-gray-50 border-t flex items-center justify-between gap-2">
                <button
                  @click="downloadAttachmentFile(img.index, img.filename)"
                  class="text-xs text-blue-600 hover:text-blue-800 underline truncate"
                >{{ img.filename }}</button>
                <button v-if="canUploadDrawing" @click="removeAttachment(img.index)"
                  class="text-xs text-red-500 hover:text-red-700 flex-shrink-0">삭제</button>
              </div>
            </div>
          </div>

          <!-- PDF 인라인 미리보기 -->
          <div v-if="detailPdfFiles.length > 0" class="mb-3 space-y-3">
            <div
              v-for="(file, idx) in detailPdfFiles"
              :key="'dpdf-' + idx"
              class="border border-gray-200 rounded-lg overflow-hidden"
            >
              <iframe
                v-if="attachmentUrls[file.index]"
                :src="attachmentUrls[file.index]"
                class="w-full h-[500px] border-0 bg-white"
              ></iframe>
              <div v-else class="p-8 text-center text-xs text-gray-400 bg-white">불러오는 중...</div>
              <div class="px-3 py-1.5 bg-gray-50 border-t flex items-center justify-between gap-2">
                <button
                  @click="downloadAttachmentFile(file.index, file.filename)"
                  class="text-xs text-blue-600 hover:text-blue-800 underline truncate"
                >{{ file.filename }}</button>
                <button v-if="canUploadDrawing" @click="removeAttachment(file.index)"
                  class="text-xs text-red-500 hover:text-red-700 flex-shrink-0">삭제</button>
              </div>
            </div>
          </div>

          <!-- 기타 문서 파일 -->
          <div v-if="detailOtherFiles.length > 0" class="space-y-1">
            <div
              v-for="(file, idx) in detailOtherFiles"
              :key="'ddoc-' + idx"
              class="flex items-center justify-between bg-white rounded px-3 py-2"
            >
              <div class="flex items-center gap-2 min-w-0 flex-1">
                <svg class="w-4 h-4 text-gray-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
                </svg>
                <span class="text-sm truncate">{{ file.filename }}</span>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <button
                  @click="downloadAttachmentFile(file.index, file.filename)"
                  class="text-sm text-blue-600 hover:text-blue-800 underline"
                >다운로드</button>
                <button v-if="canUploadDrawing" @click="removeAttachment(file.index)"
                  class="text-sm text-red-500 hover:text-red-700">삭제</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 관련 문서 -->
        <div v-if="relatedDocs.length > 0" class="mb-6">
          <h3 class="text-sm font-medium text-gray-700 mb-2">📄 관련 문서 ({{ relatedDocs.length }})</h3>
          <div class="border rounded-lg overflow-hidden">
            <table class="min-w-full divide-y divide-gray-200 text-xs">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-left text-gray-500">유형</th>
                  <th class="px-3 py-2 text-left text-gray-500">문서번호</th>
                  <th class="px-3 py-2 text-left text-gray-500">날짜</th>
                  <th class="px-3 py-2 text-center text-gray-500">상태</th>
                </tr>
              </thead>
              <tbody class="divide-y">
                <tr v-for="d in relatedDocs" :key="d.id" class="hover:bg-blue-50 cursor-pointer" @click="openDocument(d)">
                  <td class="px-3 py-2">
                    <span :class="{
                      'bg-blue-100 text-blue-700': d.document_type === 'QUOTATION',
                      'bg-purple-100 text-purple-700': d.document_type === 'PI',
                      'bg-amber-100 text-amber-700': d.document_type === 'CI',
                    }" class="px-2 py-0.5 text-[10px] font-medium rounded">{{ d.document_type }}</span>
                  </td>
                  <td class="px-3 py-2 font-medium text-blue-600">{{ d.document_number }}</td>
                  <td class="px-3 py-2 text-gray-600">{{ d.document_date?.replace(/-/g, '.') || '-' }}</td>
                  <td class="px-3 py-2 text-center">
                    <span :class="{
                      'bg-gray-100 text-gray-700': d.status === 'DRAFT',
                      'bg-blue-100 text-blue-700': d.status === 'SENT',
                      'bg-green-100 text-green-700': d.status === 'CONFIRMED',
                    }" class="px-2 py-0.5 text-[10px] font-medium rounded-full">
                      {{ ({ DRAFT: '작성중', SENT: '발송', CONFIRMED: '확정', CANCELLED: '취소' } as Record<string, string>)[d.status] || d.status }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 제품 목록 (v0.22.0 다중 제품) -->
        <div class="mb-6">
          <h3 class="text-sm font-medium text-gray-700 mb-2">제품 목록</h3>
          <div class="border rounded-lg overflow-hidden">
            <table class="min-w-full divide-y divide-gray-200 text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">#</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">품번</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">제품명</th>
                  <th class="px-4 py-2 text-right text-xs font-medium text-gray-500">요청수량</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 min-w-[200px]">특이사항</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">도면</th>
                  <th v-if="request.status === 'APPROVED' || request.status === 'IN_PROGRESS'"
                    class="px-4 py-2 text-center text-xs font-medium text-gray-500 whitespace-nowrap">작업지시</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <!-- 다중 제품 (v0.22.0) -->
                <template v-if="request.items && request.items.length > 0">
                  <tr v-for="(item, index) in request.items" :key="item.id">
                    <td class="px-4 py-2 text-gray-500">{{ index + 1 }}</td>
                    <td class="px-4 py-2 font-medium text-gray-900">
                      {{ item.product_part?.part_number_display || item.product_part?.part_number || item.custom_product_code || '-' }}
                      <span v-if="!item.product_part_id" class="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-slate-100 text-slate-600 align-middle whitespace-nowrap">외주</span>
                    </td>
                    <td class="px-4 py-2 text-gray-700">
                      {{ item.product_part?.part_name || item.custom_product_name || '-' }}
                    </td>
                    <td class="px-4 py-2 text-right text-gray-900">
                      {{ formatNumber(item.requested_quantity) }} <span class="text-xs text-gray-400">{{ item.uom || 'EA' }}</span>
                    </td>
                    <td class="px-4 py-2 text-gray-700 whitespace-pre-wrap align-top"
                      :class="item.customer_requirements ? 'bg-amber-50' : ''">
                      {{ item.customer_requirements || '-' }}
                    </td>
                    <td class="px-4 py-2 align-top">
                      <div v-if="item.attachment_files && item.attachment_files.length" class="flex flex-wrap gap-1.5">
                        <button v-for="(f, fi) in item.attachment_files" :key="fi" type="button"
                          @click="openItemAttachment(item.id, fi, f.filename)"
                          class="group relative flex items-center gap-1 border rounded overflow-hidden hover:ring-2 hover:ring-blue-400"
                          :title="f.filename">
                          <img v-if="itemAttachmentUrls[`${item.id}_${fi}`]"
                            :src="itemAttachmentUrls[`${item.id}_${fi}`]"
                            class="w-10 h-10 object-cover" />
                          <span v-else class="w-10 h-10 flex items-center justify-center bg-gray-50 text-[10px] text-gray-500 px-0.5 text-center leading-tight">
                            {{ (f.filename.split('.').pop() || 'FILE').toUpperCase() }}
                          </span>
                        </button>
                      </div>
                      <span v-else class="text-gray-300 text-xs">-</span>
                    </td>
                    <td v-if="request.status === 'APPROVED' || request.status === 'IN_PROGRESS'"
                      class="px-4 py-2 text-center align-top whitespace-nowrap">
                      <span v-if="item.work_order_id" class="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded whitespace-nowrap">
                        생성됨
                      </span>
                      <span v-else-if="!item.product_part_id" class="text-[11px] text-gray-400 whitespace-nowrap" title="BOM 미등록(외주) 항목은 작업지시서를 생성하지 않습니다">외주 · 해당없음</span>
                      <button v-else @click="createWOForItem(item.id)"
                        class="px-2 py-0.5 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700 whitespace-nowrap">
                        작업지시 생성
                      </button>
                    </td>
                  </tr>
                </template>
                <!-- 레거시 단일 제품 (호환성) -->
                <tr v-else-if="request.product_part">
                  <td class="px-4 py-2 text-gray-500">1</td>
                  <td class="px-4 py-2 font-medium text-gray-900">
                    {{ request.product_part?.part_number_display || request.product_part?.part_number || '-' }}
                  </td>
                  <td class="px-4 py-2 text-gray-700">
                    {{ request.product_part?.part_name || '-' }}
                  </td>
                  <td class="px-4 py-2 text-right text-gray-900">
                    {{ formatNumber(request.requested_quantity ?? 0) }}
                  </td>
                  <td class="px-4 py-2 text-gray-400">-</td>
                  <td class="px-4 py-2 text-gray-400">-</td>
                </tr>
                <tr v-else>
                  <td colspan="6" class="px-4 py-4 text-center text-gray-500">
                    제품 정보가 없습니다.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 분할선적 박스 분할계획 (영업 작성 → 생산 포장 지시) -->
        <div v-if="request.box_plan && request.box_plan.length" class="mb-6">
          <h3 class="text-sm font-medium text-gray-700 mb-2">
            📦 분할선적 박스 분할계획
            <span class="ml-1 text-xs text-indigo-500">· 영업 작성 · 이대로 나눠서 포장</span>
          </h3>
          <div class="border rounded-lg overflow-hidden overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200 text-sm">
              <thead class="bg-indigo-50/60">
                <tr>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 w-16">박스</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">내용물 (품번 × 수량)</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">비고</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr v-for="(box, i) in request.box_plan" :key="i">
                  <td class="px-3 py-2 text-gray-800 font-semibold align-top">#{{ box.box_no }}</td>
                  <td class="px-3 py-2 text-gray-700 align-top">
                    <div v-for="(ln, li) in box.items" :key="li" class="whitespace-nowrap">
                      <span class="font-mono">{{ ln.product_code || boxLineCode(ln) }}</span>
                      <span class="mx-1 text-gray-400">×</span>
                      <span class="tabular-nums font-medium">{{ ln.quantity }}</span>
                    </div>
                  </td>
                  <td class="px-3 py-2 text-gray-600 align-top">{{ box.remarks || '-' }}</td>
                </tr>
              </tbody>
              <tfoot class="bg-gray-50">
                <tr>
                  <td class="px-3 py-1.5 text-xs text-gray-500" colspan="3">
                    총 {{ request.box_plan.length }}박스
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        <!-- 출고 포장 명세 (Packing List) -->
        <div v-if="request.packing_list && request.packing_list.length" class="mb-6">
          <h3 class="text-sm font-medium text-gray-700 mb-2">
            📦 출고 포장 명세 (Packing List)
            <span v-if="request.shipped_at" class="ml-1 text-xs text-gray-400">· 출고 {{ formatDate(request.shipped_at) }}</span>
          </h3>
          <div class="border rounded-lg overflow-hidden overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200 text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">#</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">박스 종류</th>
                  <th class="px-3 py-2 text-center text-xs font-medium text-gray-500">개수</th>
                  <th class="px-3 py-2 text-center text-xs font-medium text-gray-500">Gross(kg)</th>
                  <th class="px-3 py-2 text-center text-xs font-medium text-gray-500">Net(kg)</th>
                  <th class="px-3 py-2 text-center text-xs font-medium text-gray-500">치수(L×W×H,cm)</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">비고</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr v-for="(b, i) in request.packing_list" :key="i">
                  <td class="px-3 py-2 text-gray-500">{{ i + 1 }}</td>
                  <td class="px-3 py-2 text-gray-800">{{ b.box_type || '-' }}</td>
                  <td class="px-3 py-2 text-center">{{ b.quantity ?? '-' }}</td>
                  <td class="px-3 py-2 text-center">{{ b.gross_weight ?? '-' }}</td>
                  <td class="px-3 py-2 text-center">{{ b.net_weight ?? '-' }}</td>
                  <td class="px-3 py-2 text-center">{{ boxDims(b) }}</td>
                  <td class="px-3 py-2 text-gray-600">{{ b.remarks || '-' }}</td>
                </tr>
                <tr class="bg-gray-50 font-medium">
                  <td class="px-3 py-2 text-gray-600" colspan="2">합계</td>
                  <td class="px-3 py-2 text-center">{{ packTotals.boxes }}</td>
                  <td class="px-3 py-2 text-center">{{ packTotals.gross.toFixed(1) }}</td>
                  <td class="px-3 py-2 text-center">{{ packTotals.net.toFixed(1) }}</td>
                  <td class="px-3 py-2" colspan="2"></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 반려 사유 -->
        <div v-if="request.rejection_reason" class="mb-6 p-4 bg-red-50 rounded-lg">
          <span class="text-sm text-red-600 font-medium">반려 사유</span>
          <p class="text-red-800 mt-1">{{ request.rejection_reason }}</p>
        </div>

        <!-- 비고 -->
        <div v-if="request.remarks" class="mb-6">
          <span class="text-sm text-gray-500">전체 특이사항</span>
          <p class="mt-1 whitespace-pre-wrap">{{ request.remarks }}</p>
        </div>

        <!-- 생산팀 총괄자 메모 (확인/생산 시작 단계) -->
        <div v-if="showManagerMemo" class="mb-6">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-bold text-gray-700">생산팀 총괄자 메모</h3>
            <span class="text-xs text-gray-400">생산 시작 전 작성</span>
          </div>
          <textarea
            v-model="managerMemo"
            :readonly="!canEditNotes"
            rows="3"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 resize-y"
            :class="canEditNotes ? '' : 'bg-gray-50 text-gray-600'"
            placeholder="생산 시작 전 총괄자 지시/주의사항 등"
          ></textarea>
        </div>

        <!-- 공정 확인표 (생산 시작 후 표시) -->
        <div v-if="showProcessChecks" class="mb-6">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-bold text-gray-700">공정 확인표</h3>
            <span class="text-xs text-red-500">확인자 서명 없을 시 다음 공정 진행 불가</span>
          </div>
          <div class="border rounded-lg overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200 text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-2 py-2 text-center text-xs font-medium text-gray-500 w-10">순번</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 min-w-[180px]">검사내용</th>
                  <th class="px-2 py-2 text-center text-xs font-medium text-gray-500 w-32">일자</th>
                  <th class="px-2 py-2 text-center text-xs font-medium text-gray-500 w-24">확인자</th>
                  <th class="px-2 py-2 text-left text-xs font-medium text-gray-500 min-w-[120px]">특이사항</th>
                  <th class="px-2 py-2 text-left text-xs font-medium text-gray-500 min-w-[120px]">조치내용</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr v-for="row in processChecks" :key="row.seq">
                  <td class="px-2 py-2 text-center text-gray-500">{{ row.seq }}</td>
                  <td class="px-3 py-2 text-gray-800 whitespace-pre-wrap">{{ row.content }}</td>
                  <td class="px-2 py-2">
                    <input v-model="row.date" :readonly="!canEditNotes" type="date"
                      class="w-full px-1 py-1 border border-gray-300 rounded text-xs focus:ring-2 focus:ring-blue-500" />
                  </td>
                  <td class="px-2 py-2">
                    <input v-model="row.checker" :readonly="!canEditNotes" type="text" placeholder="확인자"
                      class="w-full px-1 py-1 border border-gray-300 rounded text-xs focus:ring-2 focus:ring-blue-500" />
                  </td>
                  <td class="px-2 py-2">
                    <input v-model="row.note" :readonly="!canEditNotes" type="text"
                      class="w-full px-1 py-1 border border-gray-300 rounded text-xs focus:ring-2 focus:ring-blue-500" />
                  </td>
                  <td class="px-2 py-2">
                    <input v-model="row.action" :readonly="!canEditNotes" type="text"
                      class="w-full px-1 py-1 border border-gray-300 rounded text-xs focus:ring-2 focus:ring-blue-500" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 출고 포장사진 (납품 트리 자동 폴더) -->
        <div class="mb-6">
          <h3 class="text-sm font-medium text-gray-700 mb-2">📷 출고 포장사진</h3>
          <PackingPhotos :request-id="request.id" :readonly="readonly" />
        </div>

        <!-- 측정자료 (손실값측정 엑셀 등, 납품 트리 자동 폴더) -->
        <div class="mb-6">
          <h3 class="text-sm font-medium text-gray-700 mb-2">📊 측정자료 <span class="text-xs text-gray-400 font-normal">(손실값측정 엑셀 등)</span></h3>
          <MeasurementFiles :request-id="request.id" :readonly="readonly" />
        </div>

        <!-- 생산 자료 저장 / 출력 -->
        <div v-if="showManagerMemo || showProcessChecks" class="mb-6 flex gap-2">
          <button v-if="canEditNotes" @click="saveNotes" :disabled="savingNotes"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm">
            {{ savingNotes ? '저장 중...' : '생산 자료 저장' }}
          </button>
          <label class="flex items-center gap-1.5 text-sm text-gray-600 ml-auto" title="인쇄 시 도면/사진 크기">
            도면 크기
            <select v-model="printDrawingSize" class="border border-gray-300 rounded px-2 py-1.5 text-sm">
              <option value="small">작게 (여러 장)</option>
              <option value="medium">보통</option>
              <option value="large">크게 (한 장씩)</option>
            </select>
          </label>
          <button @click="printProductionSheet"
            class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm">
            🖨 출력 (PDF)
          </button>
        </div>

        <!-- 연결된 작업지시서 -->
        <div v-if="request.work_orders && request.work_orders.length > 0" class="mb-6">
          <h3 class="text-sm font-medium text-gray-700 mb-2">연결된 작업지시서</h3>
          <div class="border rounded-lg overflow-hidden">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">작업지시번호</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-gray-500">상태</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-gray-500">생성일</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr v-for="wo in request.work_orders" :key="wo.id">
                  <td class="px-4 py-2 text-sm text-blue-600">{{ wo.wo_number }}</td>
                  <td class="px-4 py-2 text-sm text-center">{{ wo.status }}</td>
                  <td class="px-4 py-2 text-sm text-center text-gray-500">
                    {{ wo.created_at ? formatDate(wo.created_at) : '-' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 버튼 -->
        <div class="flex justify-between border-t pt-4">
          <div>
            <!-- 수정 버튼: 완료/취소/반려 상태 제외하고 표시 -->
            <button
              v-if="canEdit"
              @click="$emit('edit', request.id)"
              class="px-4 py-2 border border-blue-500 text-blue-600 rounded-lg hover:bg-blue-50"
            >
              수정
            </button>
          </div>
          <div class="flex gap-2">
            <template v-if="!readonly">
            <button
              v-if="request.status === 'REJECTED'"
              @click="$emit('resubmit', request.id)"
              class="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
              title="반려 사유 수정 후 다시 요청"
            >
              ↻ 재요청
            </button>
            <button
              v-if="request.status === 'REQUESTED'"
              @click="$emit('approve', request.id)"
              class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              승인
            </button>
            <button
              v-if="request.status === 'REQUESTED'"
              @click="$emit('hold', request.id)"
              class="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
            >
              보류
            </button>
            <button
              v-if="request.status === 'HOLD'"
              @click="$emit('release-hold', request.id)"
              class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              보류 해제
            </button>
            <button
              v-if="request.status === 'REQUESTED' || request.status === 'HOLD'"
              @click="$emit('reject', request.id)"
              class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              반려
            </button>
            <button
              v-if="canCancel"
              @click="$emit('cancel', request.id)"
              class="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
            >
              취소
            </button>
            <button
              v-if="canDelete"
              @click="$emit('delete', request.id)"
              class="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50"
            >
              삭제
            </button>
            </template>
            <button
              @click="$emit('close')"
              class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              닫기
            </button>
          </div>
        </div>
      </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import {
  productionRequestApi,
  prStatusLabels,
  prStatusStyles,
  priorityLabels,
  priorityStyles,
  type ProductionRequest,
  type ProcessCheckRow
} from '@/api/productionRequest'
import apiClient from '@/api/client'
import { navigateToDocument } from '@/utils/documentNav'
import PackingPhotos from '@/views/production/components/PackingPhotos.vue'
import MeasurementFiles from '@/views/production/components/MeasurementFiles.vue'

const props = defineProps<{
  requestId: number
  readonly?: boolean  // 영업팀 등 보기 전용 — 생산 액션/편집/업로드 숨김
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'edit', id: number): void
  (e: 'approve', id: number): void
  (e: 'reject', id: number): void
  (e: 'hold', id: number): void
  (e: 'release-hold', id: number): void
  (e: 'cancel', id: number): void
  (e: 'delete', id: number): void
  (e: 'resubmit', id: number): void
}>()

const router = useRouter()
const loading = ref(false)
const request = ref<ProductionRequest | null>(null)
const relatedDocs = ref<any[]>([])

// 생산 시작 단계 자료 (총괄자 메모 / 공정 확인표)
const managerMemo = ref('')
const processChecks = ref<ProcessCheckRow[]>([])
const savingNotes = ref(false)

// 총괄자 메모: 확인(APPROVED) 이후 표시 / 공정 확인표: 생산 시작(IN_PROGRESS) 이후 표시
const showManagerMemo = computed(() =>
  !!request.value && ['APPROVED', 'IN_PROGRESS', 'COMPLETED', 'SHIPPED', 'DELIVERED'].includes(request.value.status))
const showProcessChecks = computed(() =>
  !!request.value && ['IN_PROGRESS', 'COMPLETED', 'SHIPPED', 'DELIVERED'].includes(request.value.status) && processChecks.value.length > 0)
// 편집 가능: 생산 진행 단계(APPROVED/IN_PROGRESS)까지, 출고 이후엔 읽기전용
const canEditNotes = computed(() =>
  !props.readonly && !!request.value && ['APPROVED', 'IN_PROGRESS'].includes(request.value.status))

// ── 첨부(도면) blob 미리보기 / 업로드 (인증 헤더 실림 → 401 방지) ──
const attachmentUrls = ref<Record<number, string>>({})
const imageDataUrls = ref<{ filename: string; dataUrl: string }[]>([])  // 출력용(요청-레벨/전체 특이사항 공통 첨부)
const itemImagesForPrint = ref<{ label: string; imgs: { filename: string; dataUrl: string }[] }[]>([])  // 출력용(품목별 도면)
const printDrawingSize = ref<'small' | 'medium' | 'large'>('medium')     // 도면 인쇄 크기(전체 공통)
const uploadingDrawing = ref(false)
// 품목별 도면 blob URL (key: `${itemId}_${index}`)
const itemAttachmentUrls = ref<Record<string, string>>({})

const canUploadDrawing = computed(() =>
  !props.readonly && !!request.value && ['REQUESTED', 'HOLD', 'APPROVED', 'IN_PROGRESS'].includes(request.value.status))

function revokeAttachmentUrls() {
  Object.values(attachmentUrls.value).forEach(u => { try { URL.revokeObjectURL(u) } catch { /* noop */ } })
  attachmentUrls.value = {}
  imageDataUrls.value = []
  Object.values(itemAttachmentUrls.value).forEach(u => { try { URL.revokeObjectURL(u) } catch { /* noop */ } })
  itemAttachmentUrls.value = {}
  itemImagesForPrint.value = []
}

// 품목별 도면 이미지 로드 (썸네일용 objectURL + 인쇄용 dataURL, 인증 헤더 → 401 방지)
async function loadItemAttachmentBlobs() {
  const items: any[] = request.value?.items || []
  const urls: Record<string, string> = {}
  const perItem: { label: string; imgs: { filename: string; dataUrl: string }[] }[] = []
  for (const it of items) {
    const imgs: { filename: string; dataUrl: string }[] = []
    await Promise.all((it.attachment_files || []).map(async (f: any, index: number) => {
      const isImg = /\.(png|jpg|jpeg|gif|webp)$/i.test(f.filename) || f.mimetype?.startsWith?.('image/')
      if (!isImg) return
      try {
        const blob = await productionRequestApi.fetchItemAttachmentBlob(request.value!.id, it.id, index)
        urls[`${it.id}_${index}`] = URL.createObjectURL(blob)
        imgs.push({ filename: f.filename, dataUrl: await blobToDataUrl(blob) })
      } catch { /* 개별 실패 무시 */ }
    }))
    if (imgs.length) {
      const label = it.product_part?.part_number_display || it.product_part?.part_number || it.custom_product_code || it.custom_product_name || '품목'
      perItem.push({ label, imgs })
    }
  }
  itemAttachmentUrls.value = urls
  itemImagesForPrint.value = perItem
}

// 품목 도면 다운로드/열기
async function openItemAttachment(itemId: number, index: number, filename: string) {
  if (!request.value) return
  try {
    const blob = await productionRequestApi.fetchItemAttachmentBlob(request.value.id, itemId, index)
    const url = URL.createObjectURL(blob)
    const isImgOrPdf = /\.(png|jpg|jpeg|gif|webp|pdf)$/i.test(filename)
    if (isImgOrPdf) {
      window.open(url, '_blank')
    } else {
      const a = document.createElement('a')
      a.href = url; a.download = filename
      document.body.appendChild(a); a.click(); a.remove()
    }
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch { alert('도면을 여는 데 실패했습니다') }
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const fr = new FileReader()
    fr.onload = () => resolve(fr.result as string)
    fr.onerror = reject
    fr.readAsDataURL(blob)
  })
}

async function loadAttachmentBlobs() {
  revokeAttachmentUrls()
  const files: any[] = request.value?.attachment_files || []
  const urls: Record<number, string> = {}
  const imgs: { filename: string; dataUrl: string }[] = []
  await Promise.all(files.map(async (f: any, index: number) => {
    const isImg = /\.(png|jpg|jpeg|gif|webp)$/i.test(f.filename) || f.mimetype?.startsWith?.('image/')
    const isPdf = f.filename.toLowerCase().endsWith('.pdf') || f.mimetype === 'application/pdf'
    if (!isImg && !isPdf) return
    try {
      const blob = await productionRequestApi.fetchAttachmentBlob(request.value!.id, index)
      urls[index] = URL.createObjectURL(blob)
      if (isImg) imgs.push({ filename: f.filename, dataUrl: await blobToDataUrl(blob) })
    } catch { /* 개별 실패는 무시 */ }
  }))
  attachmentUrls.value = urls
  imageDataUrls.value = imgs
}

async function downloadAttachmentFile(index: number, filename: string) {
  if (!request.value) return
  try {
    const blob = await productionRequestApi.fetchAttachmentBlob(request.value.id, index)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = filename
    document.body.appendChild(a); a.click(); a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch { alert('다운로드에 실패했습니다') }
}

async function uploadDrawingFiles(files: File[]) {
  if (!files.length || !request.value) return
  uploadingDrawing.value = true
  try {
    for (const f of files) await productionRequestApi.uploadAttachment(request.value.id, f)
    await loadData()
  } catch (err: any) {
    alert(err?.response?.data?.detail?.message || err?.response?.data?.detail || '업로드에 실패했습니다')
  } finally { uploadingDrawing.value = false }
}

async function onDrawingSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  await uploadDrawingFiles(files)
}

// 드래그 앤 드롭 업로드
const drawingDragOver = ref(false)
async function onDrawingDrop(e: DragEvent) {
  drawingDragOver.value = false
  if (!canUploadDrawing.value) return
  const files = Array.from(e.dataTransfer?.files || [])
  await uploadDrawingFiles(files)
}

async function removeAttachment(index: number) {
  if (!request.value) return
  if (!confirm('이 첨부(도면)를 삭제하시겠습니까?')) return
  try {
    await productionRequestApi.deleteAttachment(request.value.id, index)
    await loadData()
  } catch { alert('삭제에 실패했습니다') }
}

async function saveNotes() {
  if (!request.value) return
  savingNotes.value = true
  try {
    const updated = await productionRequestApi.updateProductionNotes(request.value.id, {
      manager_memo: managerMemo.value,
      process_checks: processChecks.value,
    })
    request.value = updated
    managerMemo.value = updated.manager_memo || ''
    processChecks.value = (updated.process_checks || []).map(r => ({ ...r }))
    alert('생산 자료가 저장되었습니다')
  } catch (e: any) {
    alert(e.response?.data?.detail?.message || e.response?.data?.detail || '저장에 실패했습니다')
  } finally {
    savingNotes.value = false
  }
}

function printProductionSheet() {
  const r = request.value
  if (!r) return
  const esc = (v: any) => String(v ?? '').replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' } as any)[c])
  const items = (r.items || []).map((it, i) => `
    <tr>
      <td style="text-align:center">${i + 1}</td>
      <td>${esc(it.product_part?.part_number_display || it.product_part?.part_number || it.custom_product_code || '-')}${!it.product_part_id ? ' <span style="font-size:10px;color:#888">(외주)</span>' : ''}<br>
        <span style="color:#666;font-size:11px">${esc(it.product_part?.part_name || it.custom_product_name || '')}</span></td>
      <td style="text-align:center">${esc(Math.round(Number(it.requested_quantity)))} ${esc(it.uom || 'EA')}</td>
      <td style="white-space:pre-wrap">${esc(it.customer_requirements || '')}</td>
    </tr>`).join('')
  const checks = (processChecks.value || []).map(row => `
    <tr>
      <td style="text-align:center">${row.seq}</td>
      <td style="white-space:pre-wrap">${esc(row.content)}</td>
      <td style="text-align:center">${esc(row.date)}</td>
      <td style="text-align:center">${esc(row.checker)}</td>
      <td>${esc(row.note)}</td>
      <td>${esc(row.action)}</td>
    </tr>`).join('')
  // 도면/사진 이미지(출력 포함). 크기: 작게(한 줄에 여러 장)/보통/크게(한 장씩) — 전체 공통 적용.
  const drawW = { small: '32%', medium: '48%', large: '100%' }[printDrawingSize.value]
  const imgGrid = (imgs: { filename: string; dataUrl: string }[]) =>
    `<div style="display:flex;flex-wrap:wrap;gap:8px">` + imgs.map(im => `
      <div style="width:${drawW};page-break-inside:avoid">
        <img src="${im.dataUrl}" style="width:100%;border:1px solid #ccc" />
        <div style="font-size:9px;color:#666;margin-top:2px;word-break:break-all">${esc(im.filename)}</div>
      </div>`).join('') + `</div>`
  // 공통 첨부(전체 특이사항 사진·도면)
  const drawings = (imageDataUrls.value || []).length ? imgGrid(imageDataUrls.value) : ''
  // 품목별 도면
  const itemDrawings = (itemImagesForPrint.value || []).filter(g => g.imgs.length).map(g => `
    <div style="margin-bottom:6px;page-break-inside:avoid">
      <div style="font-size:10px;font-weight:700;color:#333;margin:2px 0">▸ ${esc(g.label)}</div>
      ${imgGrid(g.imgs)}
    </div>`).join('')
  const html = `<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>생산요청서 ${esc(r.request_number)}</title>
    <style>
      @page{size:A4 portrait;margin:9mm}
      *{font-family:'Malgun Gothic',sans-serif;box-sizing:border-box}
      body{margin:0;color:#111;font-size:11px}
      h1{font-size:16px;text-align:center;margin:0 0 6px}
      h2{font-size:12px;margin:9px 0 4px;border-left:3px solid #333;padding-left:6px}
      table{width:100%;border-collapse:collapse;margin-bottom:6px}
      th,td{border:1px solid #999;padding:3px 5px;vertical-align:top}
      th{background:#f0f0f0;font-size:10.5px}
      .info th{text-align:left;color:#333;white-space:nowrap}
      .info td{font-weight:600;overflow-wrap:anywhere}
      .memo{border:1px solid #999;padding:6px;min-height:30px;white-space:pre-wrap}
      .two-col{display:flex;gap:8px}
      .two-col>div{flex:1;min-width:0}
      .two-col h2{margin-top:0}
      /* 공정확인표: 손글씨 기입 높이(콤팩트) */
      .checks td{height:30px;vertical-align:top}
      @media print{body{margin:0}}
    </style></head><body>
    <h1>생 산 요 청 서 (PRODUCTION REQUEST)</h1>
    <table class="info">
      <colgroup><col style="width:76px"><col><col style="width:76px"><col></colgroup>
      <tr>
        <th>생산번호</th><td>${esc(r.request_number)}</td>
        <th>거래처</th><td>${esc(r.customer?.partner_name || '')}</td>
      </tr>
      <tr>
        <th>PI No.</th><td>${esc(r.pi_number || '')}</td>
        <th>PO No.</th><td>${esc(r.customer_order_no || '')}</td>
      </tr>
      <tr>
        <th>국가</th><td>${esc((r as any).country || '')}</td>
        <th>납기예정일</th><td>${esc(r.due_date || '')}</td>
      </tr>
      <tr>
        <th>생산기간</th><td>${esc(r.production_period || '')}</td>
        <th>작성자</th><td>${esc(r.prepared_by_name || '')}</td>
      </tr>
      <tr>
        <th>DESTINATION</th><td colspan="3">${esc(r.destination || '')}</td>
      </tr>
      <tr>
        <th>SHIPPING MARK</th><td colspan="3" style="white-space:pre-wrap">${esc((r as any).shipping_mark || '')}</td>
      </tr>
      <tr>
        <th>CONSIGNEE</th><td colspan="3" style="white-space:pre-wrap">${esc((r as any).consignee || '')}</td>
      </tr>
    </table>
    <h2>제품 목록</h2>
    <table><thead><tr><th style="width:36px">No.</th><th>품목</th><th style="width:70px">수량</th><th>특이사항</th></tr></thead>
      <tbody>${items || '<tr><td colspan="4" style="text-align:center">-</td></tr>'}</tbody></table>
    <div class="two-col">
      <div>
        <h2>전체 특이사항 (영업 작성)</h2>
        <div class="memo">${esc(r.remarks || '')}</div>
      </div>
      <div>
        <h2>생산팀 총괄자 메모</h2>
        <div class="memo">${esc(managerMemo.value)}</div>
      </div>
    </div>
    <h2>공 정 확 인 표</h2>
    <table class="checks"><thead><tr><th style="width:26px">순번</th><th style="width:32%">검사내용</th><th style="width:54px">일자</th><th style="width:48px">확인자</th><th>특이사항</th><th>조치내용</th></tr></thead>
      <tbody>${checks || '<tr><td colspan="6" style="text-align:center">생산 시작 후 생성됩니다</td></tr>'}</tbody></table>
    <p style="color:#c00;font-size:10px;margin:3px 0 0">▶ 확인자 서명 없을 시 다음 공정 진행 불가 ▶ 해당 작업자 전원 서명할 것</p>
    ${drawings ? '<h2>전체 특이사항 · 첨부 도면·사진</h2>' + drawings : ''}
    ${itemDrawings ? '<h2>품목별 도면</h2>' + itemDrawings : ''}
    <script>window.onload=function(){window.print()}<\/script>
    </body></html>`
  const w = window.open('', '_blank')
  if (!w) { alert('팝업이 차단되었습니다. 팝업을 허용해 주세요.'); return }
  w.document.write(html)
  w.document.close()
}

async function loadRelatedDocs() {
  if (!request.value?.pi_number) { relatedDocs.value = []; return }
  try {
    // PI 번호로 문서 검색
    const res = await apiClient.get('/sales-documents', {
      params: { keyword: request.value.pi_number, limit: 20 }
    })
    const piDocs = (res.data.items || [])
    // PI 문서를 찾으면 해당 PI의 관련 문서 체인도 로드
    const allDocs: any[] = []
    const seenIds = new Set<number>()
    for (const doc of piDocs) {
      if (seenIds.has(doc.id)) continue
      seenIds.add(doc.id)
      allDocs.push(doc)
      try {
        const relRes = await apiClient.get(`/sales-documents/${doc.id}/related`)
        const rel = relRes.data
        for (const s of (rel.sources || [])) {
          if (!seenIds.has(s.id)) { seenIds.add(s.id); allDocs.push(s) }
        }
        for (const f of (rel.forward || [])) {
          if (!seenIds.has(f.id)) { seenIds.add(f.id); allDocs.push(f) }
        }
      } catch { /* ignore */ }
    }
    relatedDocs.value = allDocs.sort((a: any, b: any) => (a.document_date || '').localeCompare(b.document_date || ''))
  } catch { relatedDocs.value = [] }
}

function openDocument(doc: any) {
  emit('close')
  navigateToDocument(router, doc.id, doc.document_type)
}



// 첨부파일 분류
const detailImageFiles = computed(() => {
  if (!request.value?.attachment_files) return []
  return request.value.attachment_files
    .map((f, i) => ({ ...f, index: i }))
    .filter(f => /\.(png|jpg|jpeg|gif|webp)$/i.test(f.filename) || f.mimetype?.startsWith('image/'))
})

const detailPdfFiles = computed(() => {
  if (!request.value?.attachment_files) return []
  return request.value.attachment_files
    .map((f, i) => ({ ...f, index: i }))
    .filter(f => f.filename.toLowerCase().endsWith('.pdf') || f.mimetype === 'application/pdf')
})

const detailOtherFiles = computed(() => {
  if (!request.value?.attachment_files) return []
  return request.value.attachment_files
    .map((f, i) => ({ ...f, index: i }))
    .filter(f => {
      const isImg = /\.(png|jpg|jpeg|gif|webp)$/i.test(f.filename) || f.mimetype?.startsWith('image/')
      const isPdf = f.filename.toLowerCase().endsWith('.pdf') || f.mimetype === 'application/pdf'
      return !isImg && !isPdf
    })
})

const canCancel = computed(() => {
  if (props.readonly || !request.value) return false
  return ['REQUESTED', 'HOLD', 'APPROVED', 'IN_PROGRESS'].includes(request.value.status)
})

// 수정 가능 여부 (반려 후 수정→재요청 허용)
const canEdit = computed(() => {
  if (props.readonly || !request.value) return false
  return ['REQUESTED', 'HOLD', 'APPROVED', 'REJECTED'].includes(request.value.status)
})

// 삭제 가능 여부 (요청됨 상태에서만)
const canDelete = computed(() => {
  if (props.readonly || !request.value) return false
  return request.value.status === 'REQUESTED'
})

async function loadData() {
  loading.value = true
  try {
    request.value = await productionRequestApi.getById(props.requestId)
    managerMemo.value = request.value.manager_memo || ''
    processChecks.value = (request.value.process_checks || []).map(r => ({ ...r }))
    await loadAttachmentBlobs()
    await loadItemAttachmentBlobs()
    await loadRelatedDocs()
  } catch (error) {
    console.error('데이터 로드 실패:', error)
  } finally {
    loading.value = false
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('ko-KR')
}

function formatDateTime(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('ko-KR')
}

// 출고 포장 명세 표기
function boxDims(b: any): string {
  if (b?.length != null && b?.width != null && b?.height != null) {
    return `${b.length} x ${b.width} x ${b.height}`
  }
  return '-'
}
// 박스계획 라인: 스냅샷 product_code가 없으면 pr_item_id로 현재 품목에서 역참조
function boxLineCode(ln: any): string {
  const it = (request.value?.items || []).find((x: any) => x.id === ln.pr_item_id)
  if (!it) return '(품목)'
  return it.product_part?.part_number_display || it.product_part?.part_number || it.custom_product_code || '(품목)'
}
const packTotals = computed(() => {
  const list: any[] = request.value?.packing_list || []
  let boxes = 0, gross = 0, net = 0
  for (const b of list) {
    const q = Number(b.quantity) || 0
    boxes += q
    gross += (Number(b.gross_weight) || 0) * q
    net += (Number(b.net_weight) || 0) * q
  }
  return { boxes, gross, net }
})

// 생산요청 수량은 무조건 자연수 표기 (백엔드 Numeric "2.000" 문자열 → 정수 반올림)
function formatNumber(num: number): string {
  const n = Number(num)
  if (Number.isNaN(n)) return '0'
  return Math.round(n).toLocaleString('ko-KR')
}

function paymentStatusLabel(status?: string): string {
  const labels: Record<string, string> = { UNPAID: '미입금', PARTIAL: '부분입금', PAID: '입금완료' }
  return labels[status || ''] || '미입금'
}

function paymentStatusStyle(status?: string): string {
  const styles: Record<string, string> = {
    UNPAID: 'bg-gray-100 text-gray-800',
    PARTIAL: 'bg-yellow-100 text-yellow-800',
    PAID: 'bg-green-100 text-green-800'
  }
  return styles[status || ''] || 'bg-gray-100 text-gray-800'
}

async function createWOForItem(itemId: number) {
  if (!request.value) return
  if (!confirm('이 품목에 대한 작업지시서를 생성하시겠습니까?')) return
  try {
    const res = await productionRequestApi.createWOForItem(request.value.id, itemId)
    alert(res.data?.message || '작업지시서가 생성되었습니다')
    loadData()  // 상세 새로고침
  } catch (err: any) {
    alert(err.response?.data?.detail?.message || err.response?.data?.detail || '작업지시서 생성에 실패했습니다')
  }
}

onMounted(() => {
  loadData()
})
onBeforeUnmount(() => revokeAttachmentUrls())
</script>
