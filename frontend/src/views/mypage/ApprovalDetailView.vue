<template>
  <div class="p-4 sm:p-6 max-w-4xl mx-auto">
    <div v-if="loading" class="py-10 text-center text-gray-500">로딩 중...</div>

    <div v-else-if="doc">
      <!-- 헤더 -->
      <div class="flex justify-between items-start mb-4">
        <div>
          <div class="flex items-center gap-2">
            <span class="font-mono text-sm text-blue-600">{{ doc.doc_number }}</span>
            <span class="px-2 py-0.5 text-xs font-medium rounded-full" :class="APPROVAL_STATUS_BADGE[doc.status]">
              {{ APPROVAL_STATUS_LABELS[doc.status] }}
            </span>
            <span v-if="doc.is_corrected" class="px-2 py-0.5 text-xs rounded bg-orange-100 text-orange-700 print:hidden">관리자 정정됨</span>
          </div>
          <h1 class="text-xl sm:text-2xl font-bold text-gray-800 mt-1 break-words">{{ doc.title }}</h1>
        </div>
        <RouterLink to="/approvals" class="text-sm text-gray-500 hover:text-gray-700 print:hidden">목록으로</RouterLink>
      </div>

      <!-- 결재란 -->
      <div class="bg-white rounded-lg shadow p-5 mb-5">
        <h2 class="text-sm font-semibold text-gray-600 mb-3">결재란</h2>
        <div class="flex flex-wrap gap-3">
          <div
            v-for="(line, idx) in sortedLines"
            :key="line.id"
            class="w-32 border rounded-lg overflow-hidden"
          >
            <div
              class="px-2 py-1 text-center text-xs font-semibold border-b"
              :class="idx === sortedLines.length - 1 ? 'bg-red-50 text-red-700' : 'bg-gray-50 text-gray-600'"
            >
              {{ idx === sortedLines.length - 1 ? '최종' : (idx + 1) + '단' }}
              <span v-if="line.approver_position" class="font-normal text-gray-400">· {{ line.approver_position }}</span>
            </div>
            <div class="h-20 flex items-center justify-center bg-white">
              <!-- 승인: 백엔드가 내려준 인라인 도장 SVG / 그 외: 상태 표시 -->
              <div
                v-if="line.status === 'APPROVED' && line.seal_svg"
                class="h-16 w-16 flex items-center justify-center [&>svg]:h-16 [&>svg]:w-16"
                v-html="line.seal_svg"
              ></div>
              <span
                v-else-if="line.status === 'APPROVED'"
                class="text-red-600 text-xs font-bold border border-red-500 rounded-full w-14 h-14 flex items-center justify-center"
              >{{ line.approver_name || '승인' }}</span>
              <span
                v-else
                class="text-xs px-2 py-0.5 rounded"
                :class="lineBadgeClass(line.status)"
              >{{ LINE_STATUS_LABELS[line.status] }}</span>
            </div>
            <div class="px-2 py-1 text-center border-t">
              <div class="text-xs font-medium text-gray-800 truncate">{{ line.approver_name || '-' }}</div>
              <div class="text-[10px] text-gray-400">{{ line.acted_at ? formatDate(line.acted_at) : '' }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 메타 -->
      <div class="bg-white rounded-lg shadow p-5 mb-5 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div><span class="text-gray-400">기안자</span><div class="font-medium text-gray-800">{{ doc.drafter_name || '-' }}</div></div>
        <div><span class="text-gray-400">종류</span><div class="font-medium text-gray-800">{{ doc.form_name || '-' }}</div></div>
        <div><span class="text-gray-400">프로젝트</span><div class="font-medium text-gray-800">{{ doc.project_name || '-' }}</div></div>
        <div><span class="text-gray-400">상신일</span><div class="font-medium text-gray-800">{{ formatDateTime(doc.drafted_at) }}</div></div>
        <div><span class="text-gray-400">완료일</span><div class="font-medium text-gray-800">{{ formatDateTime(doc.completed_at) }}</div></div>
        <div><span class="text-gray-400">검증번호</span><div class="font-mono font-medium text-gray-800">{{ doc.doc_number }}-{{ doc.verify_code || '----' }}</div></div>
        <div v-if="doc.purchase_category"><span class="text-gray-400">구매 구분</span><div class="font-medium text-gray-800">{{ doc.purchase_category }}</div></div>
        <div v-if="doc.executor_name"><span class="text-gray-400">시행자</span><div class="font-medium text-gray-800">{{ doc.executor_name }}</div></div>
        <div v-if="doc.execution_status">
          <span class="text-gray-400">시행 상태</span>
          <div class="font-medium">
            <span v-if="doc.execution_status === 'DONE'" class="text-emerald-700">시행완료 <span class="text-xs text-gray-400">{{ formatDateTime(doc.executed_at) }}</span></span>
            <span v-else class="text-amber-600">시행전(대기)</span>
          </div>
        </div>
        <div v-if="(doc.related_documents && doc.related_documents.length) || doc.related_doc_number" class="col-span-2 sm:col-span-4">
          <span class="text-gray-400">관련 문서 (선행){{ doc.related_documents && doc.related_documents.length > 1 ? ` · ${doc.related_documents.length}건` : '' }}</span>
          <div v-if="doc.related_documents && doc.related_documents.length" class="flex flex-col gap-0.5">
            <RouterLink
              v-for="rd in doc.related_documents" :key="rd.id"
              :to="`/approvals/${rd.id}`"
              class="font-medium text-blue-600 hover:underline"
            >
              <span class="font-mono">{{ rd.doc_number }}</span>
              <span v-if="rd.title"> {{ rd.title }}</span>
            </RouterLink>
          </div>
          <div v-else>
            <RouterLink
              v-if="doc.related_document_id"
              :to="`/approvals/${doc.related_document_id}`"
              class="font-medium text-blue-600 hover:underline"
            >
              <span class="font-mono">{{ doc.related_doc_number }}</span>
              <span v-if="doc.related_title"> {{ doc.related_title }}</span>
            </RouterLink>
          </div>
        </div>
        <!-- 후속 문서 체인 -->
        <div v-if="doc.linked_documents && doc.linked_documents.length" class="col-span-2 sm:col-span-4">
          <span class="text-gray-400">후속 문서</span>
          <ul class="mt-1 space-y-1">
            <li v-for="ld in doc.linked_documents" :key="ld.id">
              <RouterLink :to="`/approvals/${ld.id}`" class="inline-flex items-center gap-2 hover:underline">
                <span class="font-mono text-blue-600">{{ ld.doc_number }}</span>
                <span class="text-gray-800">{{ ld.title }}</span>
                <span
                  class="px-2 py-0.5 text-xs font-medium rounded-full"
                  :class="APPROVAL_STATUS_BADGE[ld.status as ApprovalStatus] || 'bg-gray-100 text-gray-700'"
                >{{ APPROVAL_STATUS_LABELS[ld.status as ApprovalStatus] || ld.status }}</span>
              </RouterLink>
            </li>
          </ul>
        </div>
      </div>

      <!-- 양식 항목 (양식 문서) -->
      <div v-if="formRows.length" class="bg-white rounded-lg shadow p-5 mb-5">
        <h2 class="text-sm font-semibold text-gray-600 mb-3">{{ doc.form_name || '양식 항목' }}</h2>
        <table class="min-w-full text-sm">
          <tbody class="divide-y divide-gray-100">
            <tr v-for="row in formRows" :key="row.key">
              <th class="py-2 pr-4 text-left text-gray-500 font-medium w-40 align-top">{{ row.label }}</th>
              <td class="py-2 text-gray-800 whitespace-pre-wrap">
                <ul v-if="row.attendees" class="space-y-0.5">
                  <li v-for="(a, ai) in row.attendees" :key="ai">
                    <span v-if="a.org" class="text-gray-500">{{ a.org }}</span>
                    <span class="font-medium">{{ a.name || '-' }}</span>
                    <span v-if="a.title" class="text-gray-500"> {{ a.title }}</span>
                  </li>
                  <li v-if="!row.attendees.length" class="text-gray-400">-</li>
                </ul>
                <table v-else-if="row.items" class="text-sm border border-gray-200 rounded w-full">
                  <thead>
                    <tr class="bg-gray-50 text-gray-500">
                      <th class="px-2 py-1 text-left font-medium">품목</th>
                      <th class="px-2 py-1 text-right font-medium w-14">수량</th>
                      <th class="px-2 py-1 text-right font-medium w-24">단가</th>
                      <th class="px-2 py-1 text-left font-medium">비고</th>
                      <th class="px-2 py-1 text-right font-medium w-28">금액</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(it, ii) in row.items" :key="ii" class="border-t border-gray-100">
                      <td class="px-2 py-1">{{ it.name || '-' }}</td>
                      <td class="px-2 py-1 text-right">{{ itemsMoney(it.qty) }}</td>
                      <td class="px-2 py-1 text-right">{{ itemsMoney(it.unit_price) }}</td>
                      <td class="px-2 py-1 text-gray-600">{{ it.note || '-' }}</td>
                      <td class="px-2 py-1 text-right">{{ itemsMoney(it.amount) }}</td>
                    </tr>
                    <tr v-if="!row.items.length"><td colspan="5" class="px-2 py-1 text-gray-400">-</td></tr>
                    <tr v-else class="border-t border-gray-200 font-semibold bg-gray-50">
                      <td class="px-2 py-1" colspan="4">합계</td>
                      <td class="px-2 py-1 text-right">{{ itemsMoney(row.items.reduce((s, x) => s + x.amount, 0)) }} {{ currencySuffix }}</td>
                    </tr>
                  </tbody>
                </table>
                <div v-else-if="row.itemsFree != null" class="whitespace-pre-wrap text-gray-800">{{ row.itemsFree || '-' }}</div>
                <template v-else>{{ row.value || '-' }}</template>
                <!-- 부가세 포함/별도 (품목 필드 공통) -->
                <div v-if="row.items || row.itemsFree != null" class="mt-2">
                  <span class="inline-block px-2 py-0.5 text-[11px] font-semibold rounded-full"
                    :class="vatIncluded ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'">
                    {{ vatIncluded ? '부가세 포함 금액' : '부가세 별도 (VAT 미포함)' }}
                  </span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 본문 -->
      <div class="bg-white rounded-lg shadow p-5 mb-5">
        <h2 class="text-sm font-semibold text-gray-600 mb-3">본문</h2>
        <div v-if="doc.content" class="prose max-w-none text-gray-800" v-html="contentHtml"></div>
        <div v-else class="text-sm text-gray-400">내용 없음</div>
      </div>

      <!-- 참조자 -->
      <div v-if="doc.references && doc.references.length" class="bg-white rounded-lg shadow p-5 mb-5">
        <h2 class="text-sm font-semibold text-gray-600 mb-3">참조자</h2>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="ref in doc.references"
            :key="ref.user_id"
            class="px-3 py-1 bg-gray-100 rounded-full text-sm text-gray-800"
          >
            {{ ref.name }}<span v-if="ref.position" class="text-gray-400"> · {{ ref.position }}</span>
          </span>
        </div>
      </div>

      <!-- 첨부파일 -->
      <div v-if="doc.attachments && doc.attachments.length" class="bg-white rounded-lg shadow p-5 mb-5">
        <h2 class="text-sm font-semibold text-gray-600 mb-3">첨부파일</h2>
        <ul class="divide-y divide-gray-200 border rounded-lg">
          <li v-for="att in doc.attachments" :key="att.id" class="flex items-center gap-3 px-3 py-2 text-sm">
            <span class="flex-1 text-gray-800 truncate">{{ att.original_name }}</span>
            <span class="text-xs text-gray-400 whitespace-nowrap">{{ formatFileSize(att.file_size) }}</span>
            <button
              v-if="isPrintable(att)"
              @click="openPreview(att)"
              class="px-3 py-1 text-gray-700 hover:bg-gray-50 rounded border border-gray-300 whitespace-nowrap"
            >👁 미리보기</button>
            <button
              v-if="isPrintable(att)"
              @click="printAttachment(att)"
              class="px-3 py-1 text-gray-600 hover:bg-gray-50 rounded border border-gray-300 whitespace-nowrap"
            >인쇄</button>
            <button
              @click="downloadAttachment(att)"
              class="px-3 py-1 text-blue-600 hover:bg-blue-50 rounded border border-blue-200 whitespace-nowrap"
            >다운로드</button>
            <button
              v-if="canDeleteAttachment"
              @click="onDeleteAttachment(att)"
              class="px-3 py-1 text-red-500 hover:bg-red-50 rounded border border-red-200 whitespace-nowrap"
            >삭제</button>
          </li>
        </ul>
      </div>

      <!-- 처리 이력 (인쇄 제외: 상신/승인 이력은 기안서 출력에 넣지 않음) -->
      <div class="bg-white rounded-lg shadow p-5 mb-5 print:hidden">
        <h2 class="text-sm font-semibold text-gray-600 mb-3">처리 이력</h2>
        <ol v-if="doc.actions.length" class="relative border-l border-gray-200 ml-2">
          <li v-for="act in doc.actions" :key="act.id" class="mb-4 ml-4">
            <div class="absolute -left-1.5 w-3 h-3 rounded-full bg-blue-500"></div>
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-gray-800">{{ ACTION_LABELS[act.action] }}</span>
              <span class="text-xs text-gray-500">{{ act.actor_name || '-' }}</span>
              <span class="text-xs text-gray-400">{{ formatDateTime(act.acted_at) }}</span>
            </div>
            <p v-if="act.comment" class="text-sm text-gray-600 mt-0.5">{{ act.comment }}</p>
          </li>
        </ol>
        <div v-else class="text-sm text-gray-400">이력이 없습니다</div>
      </div>

      <!-- 결재의견 (댓글) — 인쇄 제외 -->
      <div class="bg-white rounded-lg shadow p-5 mb-5 print:hidden">
        <div class="flex items-center gap-2 mb-3">
          <h2 class="text-sm font-semibold text-gray-600">결재의견</h2>
          <button @click="loadComments" :disabled="commentsLoading" title="새로고침"
            class="text-gray-400 hover:text-gray-600 disabled:opacity-40">
            <svg class="w-4 h-4" :class="{ 'animate-spin': commentsLoading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <span v-if="comments.length" class="text-xs text-gray-400">{{ comments.length }}</span>
        </div>

        <ul class="border rounded-lg divide-y divide-gray-100">
          <li v-for="c in comments" :key="c.id" class="flex items-start gap-3 px-3 py-2.5">
            <div class="w-7 h-7 shrink-0 rounded-full bg-gray-200 text-gray-500 flex items-center justify-center text-xs font-semibold">
              {{ (c.user_name || '?').slice(0, 1) }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-gray-800">{{ c.user_name || '-' }}</span>
                <span class="text-xs text-gray-400">{{ formatDateTime(c.created_at) }}</span>
                <button v-if="c.can_delete" @click="onDeleteComment(c)"
                  class="ml-auto text-xs text-gray-400 hover:text-red-500">삭제</button>
              </div>
              <p class="text-sm text-gray-700 whitespace-pre-wrap break-words mt-0.5">{{ c.content }}</p>
            </div>
          </li>

          <!-- 입력 -->
          <li class="flex items-start gap-3 px-3 py-2.5">
            <div class="w-7 h-7 shrink-0 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-semibold">
              {{ (user?.name || '?').slice(0, 1) }}
            </div>
            <div class="flex-1 min-w-0">
              <textarea v-model="newComment" rows="1" placeholder="댓글을 입력하세요."
                @keydown.enter.exact.prevent="onAddComment"
                class="w-full border rounded px-2 py-1.5 text-sm resize-y focus:border-blue-500 focus:ring-1 focus:ring-blue-500"></textarea>
            </div>
            <button @click="onAddComment" :disabled="commentPosting || !newComment.trim()"
              class="shrink-0 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-40 self-start">
              {{ commentPosting ? '등록 중' : '등록' }}
            </button>
          </li>
        </ul>
        <p class="text-[11px] text-gray-400 mt-2">등록하면 문서 연관자(기안자·결재자·참조자·시행자)에게 알림이 갑니다. Enter로 등록, Shift+Enter 줄바꿈.</p>
      </div>

      <!-- 액션 버튼 — 인쇄 제외 -->
      <div class="flex flex-wrap justify-end gap-2 print:hidden">
        <!-- 인쇄 + 옵션 (처리이력은 기안서 출력에서 제외) -->
        <label class="flex items-center gap-1.5 text-sm text-gray-600 mr-1 select-none">
          <input type="checkbox" v-model="printOpts.references" class="rounded border-gray-300" />
          참조자 포함
        </label>
        <label class="flex items-center gap-1.5 text-sm text-gray-600 mr-1 select-none">
          <input type="checkbox" v-model="printOpts.printDate" class="rounded border-gray-300" />
          출력일 포함
        </label>
        <label class="flex items-center gap-1.5 text-sm text-gray-600 mr-1 select-none">
          <input type="checkbox" v-model="printOpts.attachments" class="rounded border-gray-300" />
          첨부파일 포함
        </label>
        <label class="flex items-center gap-1.5 text-sm text-gray-600 mr-1 select-none">
          <input type="checkbox" v-model="printOpts.docNumber" class="rounded border-gray-300" />
          문서번호 표시
        </label>
        <button
          @click="onPrint"
          :disabled="printing"
          class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
        >{{ printing ? '준비 중...' : '인쇄' }}</button>

        <!-- 참석자 서명부 (회의 계열: form_data.attendees 존재) -->
        <button
          v-if="hasAttendees"
          @click="openAttendance"
          class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
        >참석자 서명부</button>

        <!-- 후속 문서 작성 (사전→사후, 다중 양식) -->
        <template v-if="doc.can_create_followup">
          <RouterLink
            v-for="f in followupForms"
            :key="f.form_code"
            :to="`/approvals/write?form=${f.form_code}&related=${doc.id}`"
            class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
          >후속: {{ f.form_name || '문서' }} 작성</RouterLink>
        </template>

        <!-- 기안자: 승인 전 수정 (임시저장 | 진행중·미승인) -->
        <RouterLink
          v-if="canEdit"
          :to="`/approvals/${doc.id}/edit`"
          class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
        >수정</RouterLink>

        <!-- 기안자: 회수 (최종 승인 전 진행중이면 언제든 → 임시저장으로 되돌려 수정·재상신) -->
        <button
          v-if="canCancel"
          @click="onCancel"
          :disabled="acting"
          class="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50"
        >회수</button>

        <!-- 기안자: 재상신 (REJECTED) -->
        <button
          v-if="isDrafter && doc.status === 'REJECTED'"
          @click="onResubmit"
          :disabled="acting"
          class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >재상신</button>

        <!-- 시행자: 시행 완료 (승인완료+시행전) -->
        <button
          v-if="doc.can_execute"
          @click="onExecute"
          :disabled="acting"
          class="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50"
        >시행 완료</button>

        <!-- 삭제: 관리자(상태 무관) 또는 본인 임시저장(DRAFT) -->
        <button
          v-if="canDelete"
          @click="onDelete"
          :disabled="acting"
          class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
        >🗑 삭제</button>

        <!-- 결재자: 승인 / 반려 -->
        <template v-if="doc.can_act">
          <!-- 지출결의서 집행(최종 승인): 시행일 입력 (v0.46.0) -->
          <div v-if="isDisbursementApproval" class="flex items-center gap-2 mr-2">
            <label class="text-sm text-gray-500">시행일(집행일)</label>
            <input v-model="execDate" type="date" class="px-2 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-green-500" />
          </div>
          <button
            @click="onApprove"
            :disabled="acting"
            class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >{{ isDisbursementApproval ? '집행 승인' : '승인' }}</button>
          <button
            @click="openReject"
            :disabled="acting"
            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
          >반려</button>
        </template>

        <!-- 이미 승인한 결재자: 진행 중이면 반려로 되돌리기 가능(내 차례가 아니어도) -->
        <template v-else-if="doc.can_reject">
          <button
            @click="openReject"
            :disabled="acting"
            title="이미 승인했지만, 결재 진행 중이라 반려로 되돌릴 수 있습니다(기안자가 수정 후 재상신)."
            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
          >반려(승인 취소)</button>
        </template>
      </div>
    </div>

    <!-- 반려 의견 모달 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="rejectOpen" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="rejectOpen = false">
          <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
            <h3 class="text-lg font-bold text-gray-800 mb-3">반려 의견</h3>
            <textarea
              v-model="rejectComment"
              rows="4"
              placeholder="반려 사유를 입력하세요 (필수)"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
            ></textarea>
            <div class="flex justify-end gap-2 mt-4">
              <button @click="rejectOpen = false" class="px-4 py-2 text-gray-600 hover:text-gray-800">취소</button>
              <button
                @click="onReject"
                :disabled="acting || !rejectComment.trim()"
                class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >반려</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 참석자 서명부 (편집 가능) 모달 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="attendanceOpen" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" @click.self="attendanceOpen = false">
          <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl p-5 max-h-[90vh] overflow-y-auto">
            <h3 class="text-lg font-bold text-gray-800 mb-1">참석자 서명부</h3>
            <p class="text-xs text-gray-400 mb-3">인쇄 전에 참석자를 수정/추가/삭제할 수 있습니다</p>
            <div class="space-y-2">
              <div
                v-for="(row, ridx) in attendanceRows"
                :key="ridx"
                class="flex flex-col sm:flex-row gap-2"
              >
                <input
                  v-model="row.org"
                  type="text"
                  placeholder="소속"
                  class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <input
                  v-model="row.name"
                  type="text"
                  placeholder="이름"
                  class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <input
                  v-model="row.title"
                  type="text"
                  placeholder="직책"
                  class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="button"
                  @click="removeAttendanceRow(ridx)"
                  class="px-3 py-2 text-red-400 hover:text-red-600"
                  title="삭제"
                >✕</button>
              </div>
              <button
                type="button"
                @click="addAttendanceRow"
                class="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >+ 참석자 추가</button>
            </div>
            <div class="flex justify-end gap-2 mt-4">
              <button @click="attendanceOpen = false" class="px-4 py-2 text-gray-600 hover:text-gray-800">닫기</button>
              <button
                @click="printAttendance"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >서명부 인쇄</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 첨부 미리보기 모달 -->
    <AttachmentPreviewModal
      :open="previewOpen"
      :url="previewUrl"
      :kind="previewKind"
      :name="previewName"
      :loading="previewLoading"
      @close="closePreview"
      @download="previewDownload"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { useAuth } from '@/stores/auth'
import { markupToHtml } from '@/utils/highlightMarkup'
import { printAttendanceSheet } from '@/utils/attendanceSheet'
import AttachmentPreviewModal from '@/views/mypage/approval/AttachmentPreviewModal.vue'
import {
  approvalApi,
  APPROVAL_STATUS_BADGE,
  APPROVAL_STATUS_LABELS,
  LINE_STATUS_LABELS,
  ACTION_LABELS,
  type ApprovalDocument,
  type ApprovalAttachment,
  type ApprovalComment,
  type ApprovalForm,
  type ApprovalStatus,
  type LineStatus,
} from '@/api/approval'

const route = useRoute()
const router = useRouter()
const { success, error, warning } = useToast()
const { user } = useAuth()

const docId = computed(() => Number(route.params.id))
const doc = ref<ApprovalDocument | null>(null)
const loading = ref(false)
const acting = ref(false)
const rejectOpen = ref(false)
const rejectComment = ref('')
const printing = ref(false)
// 기안서 인쇄 옵션 — 기본 모두 해제(깔끔한 기본 출력). 처리이력은 출력에서 제외(체크박스 없음).
const printOpts = ref({ history: false, references: false, printDate: false, attachments: false, docNumber: false })
const forms = ref<ApprovalForm[]>([])

const sortedLines = computed(() =>
  doc.value ? [...doc.value.lines].sort((a, b) => a.step_order - b.step_order) : [],
)

// 작성 가능한 후속 양식 목록 (다중). followups 우선, 없으면 단일 필드 fallback
const followupForms = computed<{ form_code: string; form_name: string }[]>(() => {
  if (!doc.value) return []
  if (doc.value.followups && doc.value.followups.length) return doc.value.followups
  if (doc.value.followup_form_code) {
    return [{ form_code: doc.value.followup_form_code, form_name: doc.value.followup_form_name || '문서' }]
  }
  return []
})
// 지출결재서 최종 승인 = 집행 → 시행일 입력 (v0.46.0)
// 기본값 = 당일(집행일 미입력 방지, v0.46.1). 집행자가 필요 시 변경.
const _todayLocal = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const execDate = ref(_todayLocal())
const isDisbursementApproval = computed(() => {
  if (!doc.value || !doc.value.can_act) return false
  if (doc.value.form_code !== 'DISBURSEMENT') return false
  const maxStep = Math.max(...doc.value.lines.map((l) => l.step_order), 0)
  return doc.value.current_step >= maxStep // 현재 결재자가 마지막 차례(=집행)
})

// 본문은 마크업(줄바꿈=\n, 하이라이트={critical:..} 등)으로 저장 → 표시 시 HTML로 변환
const contentHtml = computed(() => markupToHtml(doc.value?.content || ''))
const isDrafter = computed(() => !!doc.value && !!user.value && doc.value.drafter_id === user.value.id)
const isAdmin = computed(() => user.value?.role === 'ADMIN')

// 삭제 가능: 관리자(상태 무관) 또는 본인이 작성한 임시저장(DRAFT) 문서
const canDelete = computed(() => isAdmin.value || (isDrafter.value && doc.value?.status === 'DRAFT'))
// 첨부 삭제 가능: 기안자 + 편집 가능 상태(임시저장/반려/진행중이면서 아직 아무도 승인 안 함)
const canDeleteAttachment = computed(() => {
  if (!doc.value || !isDrafter.value) return false
  if (doc.value.status === 'DRAFT' || doc.value.status === 'REJECTED') return true
  if (doc.value.status === 'IN_PROGRESS') return !(doc.value.lines || []).some((l) => l.status === 'APPROVED')
  return false
})
// 회수: 기안자 + 결재 진행 중(최종 승인 전)이면 언제든 가능
const canCancel = computed(() => {
  if (!doc.value || !isDrafter.value) return false
  return doc.value.status === 'IN_PROGRESS'
})
// 수정: 기안자 + (임시저장 | 진행중이면서 아직 아무도 승인 안 함)
const canEdit = computed(() => {
  if (!doc.value || !isDrafter.value) return false
  if (doc.value.status === 'DRAFT') return true
  if (doc.value.status === 'REJECTED') return true  // 반려: 수정 후 재상신
  if (doc.value.status === 'IN_PROGRESS') return !(doc.value.lines || []).some((l) => l.status === 'APPROVED')
  return false
})

const formatDate = (v?: string | null) => (v ? new Date(v).toLocaleDateString('ko-KR') : '-')
const formatDateTime = (v?: string | null) => (v ? new Date(v).toLocaleString('ko-KR') : '-')

const formatFileSize = (bytes: number): string => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

// 양식 항목 라벨 매핑 (form_code 또는 form_id 기준)
const formRows = computed(() => {
  if (!doc.value || !doc.value.form_data) return []
  const data = doc.value.form_data
  const form = forms.value.find(
    (f) => f.id === doc.value!.form_id || f.code === doc.value!.form_code,
  )
  const isFreeItems = (data as any)['items_mode'] === 'FREE'
  if (form) {
    const rows = form.fields_schema.map((field) => ({
      key: field.key,
      label: field.label,
      value: formatFieldValue(field, data[field.key]),
      attendees: field.key === 'attendees' ? toAttendeeList(data[field.key]) : null,
      items: field.key === 'items' && !isFreeItems ? toItemList(data[field.key]) : null,
      itemsFree: field.key === 'items' && isFreeItems ? String((data as any)['items_free'] || '') : null,
    }))
    // 과제 구매기안서: 품목 바로 아래 RCMS 항목(비목)·세부항목
    const budgetItem = (data as any)['budget_item']
    if (budgetItem) {
      const cat = (data as any)['budget_category']
      const idx = rows.findIndex((r) => r.key === 'items')
      rows.splice(idx >= 0 ? idx + 1 : rows.length, 0,
        { key: 'budget_item', label: '항목', value: cat ? `[${cat}] ${budgetItem}` : String(budgetItem), attendees: null, items: null, itemsFree: null },
        { key: 'budget_detail', label: '세부항목', value: String((data as any)['budget_detail'] || '-'), attendees: null, items: null, itemsFree: null },
      )
    }
    return rows
  }
  // 양식 메타가 없으면 raw key 노출
  return Object.entries(data).map(([key, value]) => ({
    key,
    label: key,
    value: value != null ? String(value) : '',
    attendees: key === 'attendees' ? toAttendeeList(value) : null,
    items: key === 'items' && !isFreeItems ? toItemList(value) : null,
    itemsFree: key === 'items' && isFreeItems ? String((data as any)['items_free'] || '') : null,
  }))
})

// items 값이 객체 배열이면 표시용 리스트로
const toItemList = (
  raw: unknown,
): { name: string; qty: number; unit_price: number; note: string; amount: number }[] | null => {
  if (!Array.isArray(raw)) return null
  return raw.map((r) => {
    const o = (r ?? {}) as Record<string, unknown>
    const qty = Number(o.qty) || 0
    const unit_price = Number(o.unit_price) || 0
    return {
      name: o.name != null ? String(o.name) : '',
      qty, unit_price,
      note: o.note != null ? String(o.note) : '',
      amount: Number(o.amount) || qty * unit_price,
    }
  })
}
const itemsMoney = (n: number) => (Number(n) || 0).toLocaleString('ko-KR')

// 통화(구매기안서/지출결의서) — form_data.currency 기준 금액 표기 단위
const CURRENCY_SUFFIX: Record<string, string> = { KRW: '원', USD: 'USD', JPY: 'JPY', CNY: 'CNY', EUR: 'EUR' }
const docCurrency = computed(() => String((doc.value?.form_data as any)?.['currency'] || 'KRW'))
// 부가세 포함(true)/별도(false) — 품목 작성 시 지정
const vatIncluded = computed(() => !!(doc.value?.form_data as any)?.['vat_included'])
const currencySuffix = computed(() => CURRENCY_SUFFIX[docCurrency.value] || docCurrency.value)
// number 타입 필드는 금액으로 간주(천단위 콤마+통화). 단 휴가 일수(days) 등은 제외.
const NON_MONEY_NUMBER_KEYS = new Set(['days'])
const isMoneyField = (field: { key: string; type?: string }) =>
  field.type === 'number' && !NON_MONEY_NUMBER_KEYS.has(field.key)
// 스칼라 필드 표시값: 금액계열(number)은 천단위+통화, 그 외는 원본 문자열
const formatFieldValue = (field: { key: string; type?: string }, v: unknown): string => {
  if (v == null || v === '') return ''
  if (isMoneyField(field)) return `${itemsMoney(Number(v))} ${currencySuffix.value}`
  return String(v)
}

// attendees 값이 객체 배열이면 표시용 리스트로, 아니면 null (문자열은 기존대로)
const toAttendeeList = (
  raw: unknown,
): { org: string; name: string; title: string }[] | null => {
  if (!Array.isArray(raw)) return null
  return raw.map((r) => {
    const o = (r ?? {}) as Record<string, unknown>
    return {
      org: o.org != null ? String(o.org) : '',
      name: o.name != null ? String(o.name) : '',
      title: o.title != null ? String(o.title) : '',
    }
  })
}

// ── 참석자 서명부 (편집 가능 모달) ──
interface AttendanceRow { org: string; name: string; title: string }
const attendanceOpen = ref(false)
const attendanceRows = ref<AttendanceRow[]>([])

const hasAttendees = computed(() => {
  const raw = doc.value?.form_data?.['attendees']
  if (Array.isArray(raw)) return raw.length > 0
  return typeof raw === 'string' && raw.trim().length > 0
})

const openAttendance = () => {
  const raw = doc.value?.form_data?.['attendees']
  if (Array.isArray(raw)) {
    attendanceRows.value = raw.map((r) => {
      const o = (r ?? {}) as Record<string, unknown>
      return {
        org: o.org != null ? String(o.org) : '',
        name: o.name != null ? String(o.name) : '',
        title: o.title != null ? String(o.title) : '',
      }
    })
  } else if (typeof raw === 'string' && raw.trim()) {
    // 레거시: 문자열이면 한 행 이름으로 관대 복원
    attendanceRows.value = [{ org: '', name: raw.trim(), title: '' }]
  } else {
    attendanceRows.value = []
  }
  attendanceOpen.value = true
}

const addAttendanceRow = () => attendanceRows.value.push({ org: '', name: '', title: '' })
const removeAttendanceRow = (idx: number) => attendanceRows.value.splice(idx, 1)

const printAttendance = () => {
  if (!doc.value) return
  const fd = doc.value.form_data || {}
  const dateStr = fd['meeting_at'] || fd['meeting_date'] || fd['date'] || ''
  try {
    printAttendanceSheet({
      title: doc.value.title,
      dateStr: dateStr ? String(dateStr) : undefined,
      attendees: attendanceRows.value,
    })
  } catch {
    warning('팝업이 차단되었습니다. 팝업을 허용해주세요')
  }
}

const lineBadgeClass = (s: LineStatus) =>
  ({
    WAITING: 'bg-gray-100 text-gray-500',
    PENDING: 'bg-blue-100 text-blue-700',
    APPROVED: 'bg-green-100 text-green-700',
    REJECTED: 'bg-red-100 text-red-700',
  })[s]

const load = async () => {
  loading.value = true
  try {
    const res = await approvalApi.getById(docId.value)
    doc.value = res.data
    loadComments()
  } catch {
    error('문서를 불러오지 못했습니다')
    router.replace('/approvals')
  } finally {
    loading.value = false
  }
}

// ── 결재의견(댓글) ──
const comments = ref<ApprovalComment[]>([])
const commentsLoading = ref(false)
const newComment = ref('')
const commentPosting = ref(false)

const loadComments = async () => {
  if (!docId.value) return
  commentsLoading.value = true
  try {
    const res = await approvalApi.listComments(docId.value)
    comments.value = res.data
  } catch {
    /* 열람권한 없거나 실패 시 조용히 비움 */
    comments.value = []
  } finally {
    commentsLoading.value = false
  }
}
const onAddComment = async () => {
  const text = newComment.value.trim()
  if (!text || commentPosting.value) return
  commentPosting.value = true
  try {
    await approvalApi.addComment(docId.value, text)
    newComment.value = ''
    await loadComments()
  } catch {
    error('댓글 등록에 실패했습니다')
  } finally {
    commentPosting.value = false
  }
}
const onDeleteComment = async (c: ApprovalComment) => {
  if (!confirm('이 댓글을 삭제할까요?')) return
  try {
    await approvalApi.deleteComment(docId.value, c.id)
    await loadComments()
  } catch {
    error('댓글 삭제에 실패했습니다')
  }
}

const onApprove = async () => {
  if (!doc.value) return
  // 지출결의서 집행(최종 승인)인데 시행일 비웠으면 당일로 기록됨을 안내
  if (isDisbursementApproval.value && !execDate.value) {
    if (!confirm('시행일(집행일)이 비어 있어 당일(오늘)로 집행 기록됩니다. 진행할까요?')) return
  }
  acting.value = true
  try {
    const payload = isDisbursementApproval.value && execDate.value ? { exec_date: execDate.value } : undefined
    await approvalApi.approve(doc.value.id, payload)
    success(isDisbursementApproval.value ? '집행 승인되었습니다' : '승인되었습니다')
    await load()
  } catch {
    error('승인에 실패했습니다')
  } finally {
    acting.value = false
  }
}

const openReject = () => {
  rejectComment.value = ''
  rejectOpen.value = true
}

const onReject = async () => {
  if (!doc.value) return
  if (!rejectComment.value.trim()) {
    warning('반려 사유를 입력하세요')
    return
  }
  acting.value = true
  try {
    await approvalApi.reject(doc.value.id, { comment: rejectComment.value.trim() })
    success('반려되었습니다')
    rejectOpen.value = false
    await load()
  } catch {
    error('반려에 실패했습니다')
  } finally {
    acting.value = false
  }
}

const onCancel = async () => {
  if (!doc.value) return
  acting.value = true
  try {
    await approvalApi.cancel(doc.value.id)
    success('회수되었습니다')
    await load()
  } catch {
    error('회수에 실패했습니다')
  } finally {
    acting.value = false
  }
}

const onExecute = async () => {
  if (!doc.value) return
  if (!confirm(`${doc.value.doc_number} 구매/집행(시행)을 완료 처리할까요?`)) return
  acting.value = true
  try {
    await approvalApi.execute(doc.value.id)
    success('시행 완료 처리되었습니다')
    await load()
  } catch (e: any) {
    error(e?.response?.data?.detail || '시행 완료에 실패했습니다')
  } finally {
    acting.value = false
  }
}

const onDelete = async () => {
  if (!doc.value) return
  if (!confirm(`이 결재 문서(${doc.value.doc_number})를 삭제할까요?\n목록·집계에서 제거됩니다(감사용 기록은 보존, 되돌릴 수 없음).`)) return
  acting.value = true
  try {
    await approvalApi.remove(doc.value.id)
    success('삭제되었습니다')
    router.push('/approvals')
  } catch {
    error('삭제에 실패했습니다')
  } finally {
    acting.value = false
  }
}

const onResubmit = async () => {
  if (!doc.value) return
  acting.value = true
  try {
    await approvalApi.resubmit(doc.value.id)
    success('재상신되었습니다')
    await load()
  } catch {
    error('재상신에 실패했습니다')
  } finally {
    acting.value = false
  }
}

// 첨부 다운로드 (Bearer 인증 유지 — blob 방식)
const downloadAttachment = async (att: ApprovalAttachment) => {
  if (!doc.value) return
  try {
    const res = await approvalApi.downloadAttachment(doc.value.id, att.id)
    const blob = new Blob([res.data as BlobPart])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = att.original_name
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch {
    error('다운로드에 실패했습니다')
  }
}

// 첨부 삭제 (기안자 + 임시저장/반려/진행중·미승인) — 잘못 올린 첨부 교체용
const onDeleteAttachment = async (att: ApprovalAttachment) => {
  if (!doc.value) return
  if (!confirm(`첨부파일 '${att.original_name}'을(를) 삭제할까요?`)) return
  try {
    await approvalApi.deleteAttachment(doc.value.id, att.id)
    success('첨부파일이 삭제되었습니다')
    await load()
  } catch (err: any) {
    error(err?.response?.data?.detail?.message || '첨부 삭제에 실패했습니다')
  }
}

// 첨부 인쇄 가능 여부 판별 (content_type 우선, 없으면 확장자)
const fileExt = (name: string): string => {
  const m = /\.([^.]+)$/.exec(name || '')
  return m && m[1] ? m[1].toLowerCase() : ''
}
const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
const isImageAttachment = (att: ApprovalAttachment): boolean => {
  if (att.content_type && att.content_type.startsWith('image/')) return true
  return IMAGE_EXTS.includes(fileExt(att.original_name))
}
const isPdfAttachment = (att: ApprovalAttachment): boolean => {
  if (att.content_type === 'application/pdf') return true
  return fileExt(att.original_name) === 'pdf'
}
const isPrintable = (att: ApprovalAttachment): boolean =>
  isImageAttachment(att) || isPdfAttachment(att)

// 첨부 직접 인쇄 (이미지: 새 창 img onload print / PDF: 새 탭 뷰어)
const printAttachment = async (att: ApprovalAttachment) => {
  if (!doc.value) return
  try {
    const res = await approvalApi.downloadAttachment(doc.value.id, att.id)
    const type = att.content_type || (isPdfAttachment(att) ? 'application/pdf' : '')
    const blob = new Blob([res.data as BlobPart], type ? { type } : undefined)
    const url = window.URL.createObjectURL(blob)
    if (isImageAttachment(att)) {
      const win = window.open('', '_blank')
      if (!win) {
        warning('팝업이 차단되었습니다. 팝업을 허용해주세요')
        window.URL.revokeObjectURL(url)
        return
      }
      // 파일명은 업로더가 정한 값 → HTML 이스케이프(제목 삽입 XSS 차단). url 은 안전한 blob: 주소.
      const escHtml = (s: string) =>
        s.replace(/[&<>"']/g, (c) =>
          ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string),
        )
      win.document.open()
      win.document.write(
        `<html><head><title>${escHtml(att.original_name)}</title></head><body style="margin:0">` +
          `<img src="${url}" style="max-width:100%" onload="window.focus();window.print()" />` +
          `</body></html>`,
      )
      win.document.close()
    } else {
      // PDF: 새 탭에서 브라우저 PDF 뷰어로 열기
      const win = window.open(url, '_blank')
      if (!win) {
        warning('팝업이 차단되었습니다. 팝업을 허용해주세요')
        window.URL.revokeObjectURL(url)
        return
      }
    }
    // blob URL 은 즉시 해제하지 않고 일정 시간 후 정리 (인쇄/렌더 보장)
    setTimeout(() => window.URL.revokeObjectURL(url), 60000)
  } catch {
    error('인쇄에 실패했습니다')
  }
}

// ── 앱 내 미리보기 모달 (다운로드 없이 이미지/PDF 확인) ──
const previewOpen = ref(false)
const previewUrl = ref('')
const previewKind = ref<'image' | 'pdf' | 'other'>('other')
const previewName = ref('')
const previewLoading = ref(false)
let previewAtt: ApprovalAttachment | null = null

const openPreview = async (att: ApprovalAttachment) => {
  if (!doc.value) return
  previewAtt = att
  previewName.value = att.original_name
  previewKind.value = isImageAttachment(att) ? 'image' : isPdfAttachment(att) ? 'pdf' : 'other'
  previewLoading.value = true
  previewOpen.value = true
  try {
    const res = await approvalApi.downloadAttachment(doc.value.id, att.id)
    const type = att.content_type || (isPdfAttachment(att) ? 'application/pdf' : '')
    const blob = new Blob([res.data as BlobPart], type ? { type } : undefined)
    if (previewUrl.value) window.URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = window.URL.createObjectURL(blob)
  } catch {
    error('미리보기를 불러오지 못했습니다')
    previewOpen.value = false
  } finally {
    previewLoading.value = false
  }
}
const closePreview = () => {
  previewOpen.value = false
  if (previewUrl.value) { window.URL.revokeObjectURL(previewUrl.value); previewUrl.value = '' }
}
const previewDownload = () => { if (previewAtt) downloadAttachment(previewAtt) }

// 인쇄 (HTML 받아 새 창에서 출력 — 인증 유지)
const onPrint = async () => {
  if (!doc.value) return
  printing.value = true
  try {
    const res = await approvalApi.getPrintHtml(doc.value.id, printOpts.value)
    const html = res.data as unknown as string
    const win = window.open('', '_blank')
    if (!win) {
      warning('팝업이 차단되었습니다. 팝업을 허용해주세요')
      return
    }
    win.document.open()
    win.document.write(html)
    win.document.close()
    win.focus()
    // 렌더 후 인쇄
    setTimeout(() => win.print(), 300)
  } catch {
    error('인쇄 준비에 실패했습니다')
  } finally {
    printing.value = false
  }
}

const loadForms = async () => {
  try {
    const res = await approvalApi.getForms()
    forms.value = res.data
  } catch {
    forms.value = []
  }
}

onMounted(async () => {
  await Promise.all([load(), loadForms()])
})

// 같은 컴포넌트 내에서 문서 id 가 바뀌면(예: 선행/후속 문서 링크 이동) 다시 로드
watch(() => route.params.id, () => {
  load()
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
