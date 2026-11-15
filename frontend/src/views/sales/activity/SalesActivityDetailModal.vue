<template>
  <Teleport to="body">
    <div :class="dock
          ? 'fixed inset-y-0 right-0 z-[60] w-full lg:w-[560px] bg-white shadow-2xl border-l overflow-y-auto'
          : ['fixed inset-0 flex items-start justify-center overflow-y-auto py-8', overlay ? 'z-[70] bg-black/30' : 'z-50 bg-black/50']">
      <div :class="dock ? 'bg-white w-full min-h-full' : 'bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4'">
        <!-- 헤더 -->
        <div class="flex items-center justify-between px-6 py-4 border-b">
          <h3 class="text-lg font-bold">{{ activity?.title || '로딩 중...' }}</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div v-if="loading" class="p-8 text-center text-gray-400">로딩 중...</div>

        <div v-else-if="activity" class="px-6 py-4">
          <!-- 기본 정보 -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
            <div>
              <span class="text-xs text-gray-500">상태</span>
              <div class="mt-1">
                <select v-model="activity.status" @change="updateField('status', activity.status)" class="border rounded px-2 py-1 text-sm w-full">
                  <option value="IN_PROGRESS">진행중</option>
                  <option value="WAITING">대기</option>
                  <option value="COMPLETED">완료</option>
                  <option value="ON_HOLD">보류</option>
                  <option value="DROPPED">무산</option>
                </select>
              </div>
            </div>
            <div>
              <span class="text-xs text-gray-500">문의 유형</span>
              <div class="mt-1">
                <select v-model="activity.inquiry_type" @change="updateField('inquiry_type', activity.inquiry_type)" class="border rounded px-2 py-1 text-sm w-full">
                  <option value="GENERAL">일반 문의</option>
                  <option value="TECHNICAL">기술 문의</option>
                  <option value="QUOTATION">견적 문의</option>
                  <option value="SAMPLE">샘플 요청</option>
                  <option value="CLAIM">클레임</option>
                  <option value="OTHER">기타</option>
                </select>
              </div>
            </div>
            <div>
              <span class="text-xs text-gray-500">거래처</span>
              <p class="text-sm font-medium mt-1">{{ activity.customer_name || activity.customer?.partner_name || '-' }}</p>
              <p v-if="activity.country" class="text-xs text-gray-400">{{ activity.country }}</p>
            </div>
            <div>
              <span class="text-xs text-gray-500">담당자</span>
              <p class="text-sm font-medium mt-1">{{ activity.assigned_to || '-' }}</p>
            </div>
          </div>

          <!-- 우선순위 (긴급/중요) -->
          <div class="mb-6 flex items-center gap-4 flex-wrap">
            <span class="text-xs text-gray-500">우선순위</span>
            <label class="inline-flex items-center gap-1.5 text-sm cursor-pointer">
              <input type="checkbox" v-model="activity.is_urgent" @change="updateField('is_urgent', activity.is_urgent)" class="w-4 h-4 rounded" />
              <span :class="activity.is_urgent ? 'text-rose-600 font-medium' : 'text-gray-600'">🔴 긴급</span>
            </label>
            <label class="inline-flex items-center gap-1.5 text-sm cursor-pointer">
              <input type="checkbox" v-model="activity.is_important" @change="updateField('is_important', activity.is_important)" class="w-4 h-4 rounded" />
              <span :class="activity.is_important ? 'text-amber-600 font-medium' : 'text-gray-600'">🟠 중요</span>
            </label>
          </div>

          <!-- Nextcloud 저장 폴더 (전체 상세에서만) -->
          <div v-if="!overlay && !dock" class="mb-6">
            <h4 class="text-sm font-medium text-gray-700 mb-2">📁 Nextcloud 저장 폴더</h4>
            <div v-if="activity.nextcloud_folder"
              class="text-xs bg-emerald-50 border border-emerald-200 rounded p-3 text-emerald-800 break-all">
              {{ activity.nextcloud_folder }}
              <span class="block text-[11px] text-emerald-600 mt-0.5">이 영업 건에서 만든 문서는 여기로 자동 저장됩니다.</span>
            </div>
            <template v-else>
              <div class="flex gap-2 items-center">
                <input v-model="folderNameInput" placeholder="문의건 폴더명 (예: 260709_프로젝트명)"
                  class="flex-1 border rounded px-3 py-2 text-sm" />
                <button type="button" @click="autoFillFolderName"
                  class="px-3 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50 whitespace-nowrap">자동생성</button>
                <button type="button" @click="createFolder" :disabled="!folderNameInput.trim() || creatingFolder"
                  class="px-3 py-2 text-sm bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50 whitespace-nowrap">
                  {{ creatingFolder ? '생성 중...' : '폴더 만들기' }}
                </button>
              </div>
              <p class="text-[11px] text-gray-400 mt-1">자동생성 = 오늘 날짜 + 프로젝트명. 거래처 폴더는 없으면 자동 생성됩니다.</p>
            </template>
          </div>

          <!-- 관련 문서 (견적서/PI/CI) — 오버레이/도킹(문서 옆)에선 숨김: 이미 문서 작업 중이라 이동 불필요 -->
          <div v-if="!overlay && !dock" class="mb-6">
            <div class="flex items-center justify-between mb-2">
              <h4 class="text-sm font-medium text-gray-700">📄 관련 문서 ({{ relatedDocs.length }})</h4>
            </div>
            <div v-if="relatedDocs.length === 0" class="text-xs text-gray-400 bg-gray-50 rounded p-3 text-center">
              아직 연결된 견적서/PI/CI가 없습니다. 하단 <strong>[견적서 추가]</strong> 버튼으로 시작하세요.
            </div>
            <div v-else class="border rounded-lg overflow-hidden">
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
                  <tr v-for="d in relatedDocs" :key="d.id"
                    @click="openDocument(d)"
                    class="hover:bg-blue-50 cursor-pointer">
                    <td class="px-3 py-2">
                      <span :class="docTypeClass(d.document_type)" class="px-2 py-0.5 text-[10px] font-medium rounded">
                        {{ d.document_type }}
                      </span>
                    </td>
                    <td class="px-3 py-2 font-medium text-blue-600">{{ d.document_number }}</td>
                    <td class="px-3 py-2 text-gray-600">{{ formatDate(d.document_date) }}</td>
                    <td class="px-3 py-2 text-right font-medium">{{ d.currency }} {{ formatNumber(d.total_amount) }}</td>
                    <td class="px-3 py-2 text-center">
                      <span :class="docStatusClass(d.status)" class="px-2 py-0.5 text-[10px] font-medium rounded-full">
                        {{ docStatusLabel(d.status) }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 진행 상황 (통합 타임라인) -->
          <div class="mb-6">
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-sm font-medium text-gray-700">진행 상황 (히스토리)</h4>
            </div>

            <!-- 신규 로그 입력 폼 -->
            <div class="border rounded-lg p-3 mb-4 transition-colors"
              :class="composerDragOver ? 'border-blue-500 border-dashed bg-blue-50' : 'bg-gray-50 border-gray-200'"
              @dragover.prevent="composerDragOver = true" @dragleave.prevent="composerDragOver = false" @drop.prevent="onComposerDrop">
              <!-- 유형 선택 (탭 스타일) -->
              <div class="flex flex-wrap gap-1 mb-2">
                <button
                  v-for="opt in userLogTypes"
                  :key="opt.value"
                  type="button"
                  @click="newLogType = opt.value"
                  :class="newLogType === opt.value
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'"
                  class="px-2.5 py-1 text-xs font-medium border rounded transition-colors">
                  {{ opt.label }}
                </button>
              </div>
              <div class="flex gap-2">
                <textarea
                  v-model="newLogContent"
                  rows="7"
                  @keydown.ctrl.enter="addLog"
                  @keydown.meta.enter="addLog"
                  @paste="handlePaste"
                  class="flex-1 border rounded px-3 py-2 text-sm leading-relaxed resize-y min-h-[8rem] max-h-[60vh]"
                  :placeholder="newLogPlaceholder"
                />
                <button
                  @click="addLog"
                  :disabled="!newLogContent.trim() && stagedFiles.length === 0"
                  class="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 self-end">
                  추가
                </button>
              </div>
              <!-- 스테이징된 첨부(붙여넣기/선택) 미리보기 -->
              <div v-if="stagedFiles.length" class="flex flex-wrap gap-2 mt-2">
                <div v-for="(s, i) in stagedFiles" :key="i" class="relative">
                  <img v-if="s.url" :src="s.url" class="w-16 h-16 object-cover rounded border" />
                  <span v-else class="w-16 h-16 flex items-center justify-center bg-gray-100 rounded border text-[9px] text-gray-500 px-1 text-center break-all">{{ s.file.name }}</span>
                  <button type="button" @click="removeStaged(i)"
                    class="absolute -top-1.5 -right-1.5 bg-red-500 text-white rounded-full w-4 h-4 flex items-center justify-center text-[10px] leading-none">✕</button>
                </div>
              </div>
              <div class="flex items-center justify-between mt-1">
                <p class="text-[10px] text-gray-400">Ctrl + Enter로 추가 · 이미지 <strong>붙여넣기(Ctrl+V)</strong> 또는 첨부 가능</p>
                <label class="text-[11px] text-blue-600 cursor-pointer hover:underline whitespace-nowrap">
                  📎 사진/파일 첨부
                  <input type="file" multiple accept="image/*,.pdf,.xlsx,.xls,.doc,.docx,.ppt,.pptx" class="hidden" @change="onFileSelect" />
                </label>
              </div>
            </div>

            <!-- 타임라인 -->
            <div v-if="activity.logs && activity.logs.length > 0" class="space-y-3">
              <div v-for="log in activity.logs" :key="log.id" class="flex gap-3">
                <!-- 좌측 아이콘 + 라인 -->
                <div class="flex flex-col items-center flex-shrink-0">
                  <div :class="logIconClass(log.log_type)"
                    class="w-7 h-7 rounded-full border flex items-center justify-center text-sm">
                    {{ logIcon(log.log_type) }}
                  </div>
                  <div class="w-0.5 flex-1 bg-gray-200 mt-1"></div>
                </div>
                <!-- 로그 내용 -->
                <div class="flex-1 pb-3">
                  <div class="flex items-baseline gap-2 flex-wrap">
                    <span :class="logBadgeClass(log.log_type)"
                      class="px-2 py-0.5 text-[10px] font-medium rounded border">
                      {{ logLabel(log.log_type) }}
                    </span>
                    <span class="text-xs text-gray-400">{{ formatDateTime(log.created_at) }}</span>
                    <span v-if="log.logged_by" class="text-xs font-medium text-gray-600">{{ log.logged_by }}</span>
                    <span v-if="log.edited_at" class="text-[11px] text-gray-400 italic"
                      :title="`수정: ${log.edited_by || '-'} · ${formatDateTime(log.edited_at)}`">
                      (수정됨 · {{ log.edited_by || '-' }} {{ formatDateTime(log.edited_at) }})
                    </span>
                    <button v-if="canEditLog(log) && editingLogId !== log.id" type="button"
                      @click="startEditLog(log)"
                      class="text-[11px] text-blue-500 hover:text-blue-700 hover:underline">✎ 수정</button>
                  </div>
                  <!-- 수정 모드 -->
                  <div v-if="editingLogId === log.id" class="mt-1"
                    @dragover.prevent="editDragOver = true" @dragleave.prevent="editDragOver = false" @drop.prevent="onEditDrop">
                    <textarea v-model="editingContent" rows="4" @paste="onEditPaste"
                      class="w-full border rounded px-3 py-2 text-sm leading-relaxed resize-y"></textarea>

                    <!-- 기존 첨부: 삭제 가능 -->
                    <div v-if="log.attachment_files && log.attachment_files.length" class="flex flex-wrap gap-2 mt-2">
                      <div v-for="(f, idx) in log.attachment_files" :key="'ex' + idx" class="relative">
                        <img v-if="logAttUrls[`${log.id}_${idx}`]" :src="logAttUrls[`${log.id}_${idx}`]" class="w-16 h-16 object-cover rounded border" :title="f.filename" />
                        <span v-else class="w-16 h-16 flex items-center justify-center bg-gray-100 rounded border text-[9px] text-gray-500 px-1 text-center break-all">{{ f.filename }}</span>
                        <button type="button" @click="deleteExistingLogAttachment(log, idx)"
                          class="absolute -top-1.5 -right-1.5 bg-red-500 text-white rounded-full w-4 h-4 flex items-center justify-center text-[10px] leading-none" title="삭제">✕</button>
                      </div>
                    </div>

                    <!-- 새 첨부 스테이징 -->
                    <div v-if="editStagedFiles.length" class="flex flex-wrap gap-2 mt-2">
                      <div v-for="(s, i) in editStagedFiles" :key="'st' + i" class="relative">
                        <img v-if="s.url" :src="s.url" class="w-16 h-16 object-cover rounded border ring-1 ring-emerald-300" />
                        <span v-else class="w-16 h-16 flex items-center justify-center bg-emerald-50 rounded border text-[9px] text-gray-500 px-1 text-center break-all">{{ s.file.name }}</span>
                        <button type="button" @click="removeEditStaged(i)" class="absolute -top-1.5 -right-1.5 bg-red-500 text-white rounded-full w-4 h-4 flex items-center justify-center text-[10px] leading-none">✕</button>
                      </div>
                    </div>

                    <div class="flex items-center gap-2 mt-1">
                      <button @click="saveEditLog(log)" :disabled="savingEdit"
                        class="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
                        {{ savingEdit ? '저장 중…' : '저장' }}
                      </button>
                      <button @click="cancelEditLog" class="px-3 py-1 text-xs border border-gray-300 rounded hover:bg-gray-100">취소</button>
                      <label class="text-[11px] text-blue-600 cursor-pointer hover:underline whitespace-nowrap">
                        📎 첨부 추가
                        <input type="file" multiple accept="image/*,.pdf,.xlsx,.xls,.doc,.docx,.ppt,.pptx" class="hidden" @change="onEditFileSelect" />
                      </label>
                      <span class="text-[11px]" :class="editDragOver ? 'text-blue-600 font-medium' : 'text-gray-400'">
                        {{ editDragOver ? '여기에 놓으면 추가됩니다' : '· 끌어다 놓기/붙여넣기(Ctrl+V)로 첨부 추가' }}
                      </span>
                    </div>
                  </div>
                  <p v-else class="text-sm mt-1 whitespace-pre-wrap text-gray-800">{{ log.content }}</p>
                  <!-- 첨부(스크린샷/사진): 히스토리에서 바로 식별 가능하게 크게 인라인 표시 -->
                  <div v-if="log.attachment_files && log.attachment_files.length" class="mt-2 space-y-2">
                    <template v-for="(f, idx) in log.attachment_files" :key="idx">
                      <!-- 이미지: 원본 비율 그대로 크게, 클릭 시 새 탭 확대 -->
                      <img v-if="logAttUrls[`${log.id}_${idx}`]"
                        :src="logAttUrls[`${log.id}_${idx}`]"
                        @click="openLogAttachment(log, idx, f.filename)"
                        :title="`${f.filename} (클릭하면 원본 크기)`"
                        class="block w-full max-w-2xl max-h-[32rem] rounded border object-contain bg-gray-50 cursor-zoom-in" />
                      <!-- 이미지 외 파일: 링크 칩 -->
                      <button v-else type="button" @click="openLogAttachment(log, idx, f.filename)"
                        class="inline-flex items-center gap-1 px-2 py-1 text-xs border rounded text-blue-600 hover:bg-blue-50">
                        📎 {{ f.filename }}
                      </button>
                    </template>
                  </div>
                </div>
              </div>
            </div>
            <p v-else class="text-sm text-gray-400 text-center py-4">아직 기록된 이력이 없습니다.</p>
          </div>
        </div>

        <!-- 하단 버튼 -->
        <div v-if="activity" class="flex justify-between px-6 py-4 border-t bg-gray-50">
          <!-- 오버레이/도킹에선 활동 수정/견적추가/연결 액션 숨김 — 히스토리 확인·코멘트만 -->
          <div v-if="!overlay && !dock" class="flex gap-2">
            <button @click="$emit('edit', activity.id)" class="px-4 py-2 text-sm border border-blue-500 text-blue-600 rounded-lg hover:bg-blue-50">수정</button>
            <button
              v-if="activity.customer_id"
              @click="addQuotationFromActivity"
              class="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700">
              📄 견적서 추가
            </button>
            <button @click="showLinkDocModal = true"
              class="px-4 py-2 text-sm border border-purple-500 text-purple-600 rounded-lg hover:bg-purple-50">
              📎 기존 문서 연결
            </button>
            <button v-if="isAdmin" @click="deleteActivity"
              class="px-4 py-2 text-sm border border-red-500 text-red-600 rounded-lg hover:bg-red-50">
              🗑 삭제
            </button>
          </div>
          <button @click="$emit('close')" class="px-4 py-2 text-sm text-gray-600">닫기</button>
        </div>
      </div>
    </div>

    <!-- 기존 문서 연결 모달 -->
    <div v-if="showLinkDocModal" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 p-6">
        <h3 class="text-lg font-bold mb-3">기존 문서 연결</h3>
        <div class="mb-3">
          <input v-model="linkDocSearch" @input="searchDocuments" placeholder="문서번호 검색 (예: Q-HT260, PI-OP)"
            class="w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div v-if="linkDocLoading" class="text-center py-4 text-gray-400 text-sm">검색 중...</div>
        <div v-else-if="linkDocResults.length === 0 && linkDocSearch" class="text-center py-4 text-gray-400 text-sm">
          검색 결과가 없습니다
        </div>
        <div v-else class="max-h-[300px] overflow-y-auto">
          <div v-for="doc in linkDocResults" :key="doc.id"
            class="flex items-center justify-between p-3 border-b hover:bg-gray-50">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span :class="{
                  'bg-blue-100 text-blue-700': doc.document_type === 'QUOTATION',
                  'bg-purple-100 text-purple-700': doc.document_type === 'PI',
                  'bg-amber-100 text-amber-700': doc.document_type === 'CI',
                }" class="px-2 py-0.5 text-[10px] font-medium rounded">{{ doc.document_type }}</span>
                <span class="text-sm font-medium text-blue-600">{{ doc.document_number }}</span>
              </div>
              <div class="text-xs text-gray-500 mt-0.5">
                {{ doc.customer?.partner_name || '-' }} · {{ doc.currency }} {{ Number(doc.total_amount).toLocaleString() }}
                <span v-if="doc.sales_activity_id && doc.sales_activity_id === activity?.id" class="text-green-500 ml-1">(현재 연결됨)</span>
                <span v-else-if="doc.sales_activity_id" class="text-orange-500 ml-1">(다른 활동에 연결됨)</span>
              </div>
            </div>
            <button v-if="!doc.sales_activity_id || doc.sales_activity_id !== activity?.id" @click="linkDocument(doc.id)"
              class="px-3 py-1 text-xs bg-purple-600 text-white rounded hover:bg-purple-700 flex-shrink-0">
              {{ doc.sales_activity_id ? '재연결' : '연결' }}
            </button>
            <span v-else class="text-xs text-green-600 flex-shrink-0">현재 연결됨</span>
          </div>
        </div>
        <div class="flex justify-end mt-4">
          <button @click="showLinkDocModal = false" class="px-4 py-2 text-sm text-gray-600">닫기</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import {
  salesActivityApi,
  LOG_TYPE_LABELS,
  LOG_TYPE_ICONS,
  LOG_TYPE_COLORS,
  USER_LOG_TYPES,
  type SalesActivity,
  type SalesActivityLog,
  type ActivityRelatedDocument,
} from '@/api/salesActivity'
import { salesDocumentApi } from '@/api/salesDocument'
import apiClient from '@/api/client'
import { useToast } from '@/composables/useToast'
import { useAuth } from '@/stores/auth'

const props = defineProps<{ activityId: number; overlay?: boolean; dock?: boolean }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'edit', id: number): void
  (e: 'updated'): void
}>()
const router = useRouter()
const { showToast } = useToast()
const { isAdmin } = useAuth()  // 삭제는 관리자만

const loading = ref(false)
const activity = ref<SalesActivity | null>(null)
const relatedDocs = ref<ActivityRelatedDocument[]>([])

// Nextcloud 폴더 (v0.60.0)
const folderNameInput = ref('')
const creatingFolder = ref(false)
function autoFillFolderName() {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  const ymd = `${String(d.getFullYear()).slice(2)}${p(d.getMonth() + 1)}${p(d.getDate())}`
  folderNameInput.value = `${ymd}_${activity.value?.title || ''}`.trim()
}
async function createFolder() {
  if (!activity.value || !folderNameInput.value.trim()) return
  creatingFolder.value = true
  try {
    const res = await salesActivityApi.createNextcloudFolder(activity.value.id, folderNameInput.value.trim())
    activity.value.nextcloud_folder = res.data.folder
    showToast('Nextcloud 폴더가 생성되었습니다', 'success')
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '폴더 생성에 실패했습니다', 'error')
  } finally {
    creatingFolder.value = false
  }
}

// 신규 로그 입력 상태
const newLogContent = ref('')
const newLogType = ref<string>('COMMENT')
const userLogTypes = USER_LOG_TYPES

const newLogPlaceholder = computed(() => {
  const opt = USER_LOG_TYPES.find(o => o.value === newLogType.value)
  return opt?.placeholder || '입력하세요...'
})

// ── 코멘트 첨부(스크린샷/사진) — 붙여넣기 & 파일 첨부 ──
interface StagedFile { file: File; url: string | null }
const stagedFiles = ref<StagedFile[]>([])

function addStagedFiles(files: File[]) {
  for (const f of files) {
    if (f.size > 200 * 1024 * 1024) { showToast(`파일이 너무 큽니다(최대 200MB): ${f.name}`, 'error'); continue }
    stagedFiles.value.push({ file: f, url: f.type.startsWith('image/') ? URL.createObjectURL(f) : null })
  }
}
function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  addStagedFiles(Array.from(input.files || []))
  input.value = ''
}
function handlePaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  const imgs: File[] = []
  for (const it of Array.from(items)) {
    if (it.type.startsWith('image/')) {
      const f = it.getAsFile()
      if (f) {
        const ext = (it.type.split('/')[1] || 'png')
        imgs.push(new File([f], `clipboard-${Date.now()}.${ext}`, { type: it.type }))
      }
    }
  }
  if (imgs.length) { e.preventDefault(); addStagedFiles(imgs) }
}
function removeStaged(i: number) {
  const s = stagedFiles.value[i]
  if (s?.url) { try { URL.revokeObjectURL(s.url) } catch { /* noop */ } }
  stagedFiles.value.splice(i, 1)
}
function clearStaged() {
  stagedFiles.value.forEach(s => { if (s.url) { try { URL.revokeObjectURL(s.url) } catch { /* noop */ } } })
  stagedFiles.value = []
}
// 작성 composer 드래그 앤 드롭
const composerDragOver = ref(false)
function onComposerDrop(e: DragEvent) {
  composerDragOver.value = false
  addStagedFiles(Array.from(e.dataTransfer?.files || []))
}

// ── 수정 모드 첨부(삭제/추가) ──
const editStagedFiles = ref<StagedFile[]>([])
const editDragOver = ref(false)
function pushEditStaged(files: File[]) {
  for (const f of files) {
    if (f.size > 200 * 1024 * 1024) { showToast(`파일이 너무 큽니다(최대 200MB): ${f.name}`, 'error'); continue }
    editStagedFiles.value.push({ file: f, url: f.type.startsWith('image/') ? URL.createObjectURL(f) : null })
  }
}
function onEditFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  pushEditStaged(Array.from(input.files || []))
  input.value = ''
}
function onEditPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  const imgs: File[] = []
  for (const it of Array.from(items)) {
    if (it.type.startsWith('image/')) {
      const f = it.getAsFile()
      if (f) imgs.push(new File([f], `clipboard-${Date.now()}.${(it.type.split('/')[1] || 'png')}`, { type: it.type }))
    }
  }
  if (imgs.length) { e.preventDefault(); pushEditStaged(imgs) }
}
function onEditDrop(e: DragEvent) {
  editDragOver.value = false
  pushEditStaged(Array.from(e.dataTransfer?.files || []))
}
function removeEditStaged(i: number) {
  const s = editStagedFiles.value[i]
  if (s?.url) { try { URL.revokeObjectURL(s.url) } catch { /* noop */ } }
  editStagedFiles.value.splice(i, 1)
}
function clearEditStaged() {
  editStagedFiles.value.forEach(s => { if (s.url) { try { URL.revokeObjectURL(s.url) } catch { /* noop */ } } })
  editStagedFiles.value = []
}
// 기존 첨부 즉시 삭제(확인 후) — 목록 새로고침(수정 모드 유지)
async function deleteExistingLogAttachment(log: SalesActivityLog, idx: number) {
  if (!activity.value) return
  if (!confirm('이 첨부를 삭제하시겠습니까?')) return
  try {
    await salesActivityApi.deleteLogAttachment(activity.value.id, log.id, idx)
    await loadData()  // editingLogId 유지 → 수정 모드 계속, 인덱스 정합성 확보
  } catch { showToast('첨부 삭제에 실패했습니다', 'error') }
}

// 저장된 코멘트 첨부 이미지 blob URL (key: `${logId}_${idx}`) — 인증 헤더 실림
const logAttUrls = ref<Record<string, string>>({})
function revokeLogAttUrls() {
  Object.values(logAttUrls.value).forEach(u => { try { URL.revokeObjectURL(u) } catch { /* noop */ } })
  logAttUrls.value = {}
}
async function loadLogAttachments() {
  revokeLogAttUrls()
  const logs = activity.value?.logs || []
  const map: Record<string, string> = {}
  await Promise.all(logs.flatMap(log =>
    (log.attachment_files || []).map(async (f: any, idx: number) => {
      const isImg = /\.(png|jpe?g|gif|webp)$/i.test(f.filename) || f.mimetype?.startsWith?.('image/')
      if (!isImg) return
      try {
        const blob = await salesActivityApi.fetchLogAttachmentBlob(activity.value!.id, log.id, idx)
        map[`${log.id}_${idx}`] = URL.createObjectURL(blob)
      } catch { /* 개별 실패 무시 */ }
    })
  ))
  logAttUrls.value = map
}
async function openLogAttachment(log: any, idx: number, filename: string) {
  try {
    const blob = await salesActivityApi.fetchLogAttachmentBlob(activity.value!.id, log.id, idx)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
    setTimeout(() => { try { URL.revokeObjectURL(url) } catch { /* noop */ } }, 60000)
  } catch { showToast('첨부를 여는 데 실패했습니다', 'error') }
}

async function loadData() {
  loading.value = true
  try {
    const res = await salesActivityApi.getById(props.activityId)
    activity.value = res.data
    loadLogAttachments()  // 코멘트 첨부 이미지 blob 로드(비동기)
    try {
      const docsRes = await salesActivityApi.getDocuments(props.activityId)
      relatedDocs.value = docsRes.data.documents || []
    } catch { relatedDocs.value = [] }
  } catch {
    showToast('데이터를 불러오는데 실패했습니다', 'error')
  } finally {
    loading.value = false
  }
}

async function updateField(field: string, value: any) {
  if (!activity.value) return
  try {
    await salesActivityApi.update(activity.value.id, { [field]: value })
    showToast('변경되었습니다', 'success')
    // 변경 이력 자동 생성됐으니 데이터 다시 로드
    await loadData()
    emit('updated')
  } catch {
    showToast('변경에 실패했습니다', 'error')
  }
}

async function deleteActivity() {
  if (!activity.value) return
  const linked = relatedDocs.value.length
  const warn = linked > 0
    ? `\n연결된 견적서/PI/CI ${linked}건은 삭제되지 않고 연결만 해제됩니다.`
    : ''
  if (!confirm(`영업활동 "${activity.value.title}"을(를) 삭제할까요?${warn}\n되돌릴 수 없습니다.`)) return
  try {
    await salesActivityApi.delete(activity.value.id)
    showToast('삭제되었습니다', 'success')
    emit('updated')
    emit('close')
  } catch (err: any) {
    showToast(err.response?.data?.detail || '삭제에 실패했습니다', 'error')
  }
}

async function addLog() {
  if (!activity.value) return
  const content = newLogContent.value.trim() || (stagedFiles.value.length ? '(첨부)' : '')
  if (!content) return
  try {
    const loggedByName = JSON.parse(localStorage.getItem('user') || '{}')?.name || undefined
    const res = await salesActivityApi.addLog(activity.value.id, {
      content,
      log_type: newLogType.value,
      logged_by: loggedByName,
    })
    // 스테이징된 첨부(스크린샷/사진)를 새 코멘트에 업로드
    const newLog = res.data
    if (newLog?.id && stagedFiles.value.length) {
      for (const s of stagedFiles.value) {
        try { await salesActivityApi.uploadLogAttachment(activity.value.id, newLog.id, s.file) }
        catch (err) { console.error('첨부 업로드 실패:', err) }
      }
    }
    newLogContent.value = ''
    clearStaged()
    showToast('기록되었습니다', 'success')
    await loadData()
    emit('updated')
  } catch {
    showToast('기록에 실패했습니다', 'error')
  }
}

// ── 코멘트 수정 (누가/언제 기록) ──
const editingLogId = ref<number | null>(null)
const editingContent = ref('')
const savingEdit = ref(false)
// 사용자가 직접 작성한 로그만 수정 허용(자동 변경 이력은 제외)
function canEditLog(log: SalesActivityLog): boolean {
  return USER_LOG_TYPES.some(o => o.value === log.log_type)
}
function startEditLog(log: SalesActivityLog) {
  editingLogId.value = log.id
  editingContent.value = log.content
  clearEditStaged()
}
function cancelEditLog() {
  editingLogId.value = null
  editingContent.value = ''
  clearEditStaged()
}
async function saveEditLog(log: SalesActivityLog) {
  if (!activity.value) return
  const content = editingContent.value.trim() || (log.attachment_files?.length || editStagedFiles.value.length ? '(첨부)' : '')
  if (!content) return
  savingEdit.value = true
  try {
    const editedBy = JSON.parse(localStorage.getItem('user') || '{}')?.name || undefined
    await salesActivityApi.updateLog(activity.value.id, log.id, { content, edited_by: editedBy })
    // 새로 추가한 첨부 업로드
    for (const s of editStagedFiles.value) {
      try { await salesActivityApi.uploadLogAttachment(activity.value.id, log.id, s.file) }
      catch (err) { console.error('첨부 업로드 실패:', err) }
    }
    clearEditStaged()
    editingLogId.value = null
    editingContent.value = ''
    showToast('코멘트가 수정되었습니다', 'success')
    await loadData()
    emit('updated')
  } catch {
    showToast('수정에 실패했습니다', 'error')
  } finally {
    savingEdit.value = false
  }
}

async function addQuotationFromActivity() {
  if (!activity.value || !activity.value.customer_id) {
    showToast('거래처가 지정되지 않은 영업활동입니다', 'error')
    return
  }
  emit('close')
  router.push({
    path: '/sales',
    query: {
      tab: 'quotations',
      customer_id: String(activity.value.customer_id),
      new_quotation: '1',
      activity_id: String(activity.value.id),
    },
  })
}

async function openDocument(d: ActivityRelatedDocument) {
  emit('close')
  const tabMap: Record<string, string> = {
    QUOTATION: 'quotations',
    PI: 'pi',
    CI: 'ci',
  }
  const targetTab = tabMap[d.document_type] || 'quotations'
  router.push({
    path: '/sales',
    query: {
      tab: targetTab,
      open_doc_id: String(d.id),
    },
  })
}

// 포맷 헬퍼
function formatDate(d?: string) {
  if (!d) return '-'
  return d.replace(/-/g, '.')
}
function formatNumber(n: number) {
  return (n || 0).toLocaleString()
}
function docTypeClass(type: string) {
  return {
    QUOTATION: 'bg-blue-100 text-blue-700',
    PI: 'bg-purple-100 text-purple-700',
    CI: 'bg-amber-100 text-amber-700',
  }[type] || 'bg-gray-100 text-gray-700'
}
function docStatusLabel(s: string) {
  return { DRAFT: '작성중', SENT: '발송', CONFIRMED: '확정', CANCELLED: '취소' }[s] || s
}
function docStatusClass(s: string) {
  return {
    DRAFT: 'bg-gray-100 text-gray-700',
    SENT: 'bg-blue-100 text-blue-700',
    CONFIRMED: 'bg-green-100 text-green-700',
    CANCELLED: 'bg-red-100 text-red-700',
  }[s] || 'bg-gray-100 text-gray-700'
}

// 로그 유형별 표시
function logLabel(type: string) {
  return LOG_TYPE_LABELS[type] || type
}
function logIcon(type: string) {
  return LOG_TYPE_ICONS[type] || '·'
}
function logBadgeClass(type: string) {
  return LOG_TYPE_COLORS[type] || 'bg-gray-100 text-gray-700 border-gray-300'
}
function logIconClass(type: string) {
  return LOG_TYPE_COLORS[type] || 'bg-gray-100 text-gray-700 border-gray-300'
}

function formatDateTime(d: string) {
  if (!d) return ''
  const date = new Date(d)
  return `${date.getFullYear()}.${String(date.getMonth()+1).padStart(2,'0')}.${String(date.getDate()).padStart(2,'0')} ${String(date.getHours()).padStart(2,'0')}:${String(date.getMinutes()).padStart(2,'0')}`
}

// 기존 문서 연결
const showLinkDocModal = ref(false)
const linkDocSearch = ref('')
const linkDocResults = ref<any[]>([])
const linkDocLoading = ref(false)
let linkDocTimer: ReturnType<typeof setTimeout>

function searchDocuments() {
  clearTimeout(linkDocTimer)
  if (!linkDocSearch.value || linkDocSearch.value.length < 2) {
    linkDocResults.value = []
    return
  }
  linkDocTimer = setTimeout(async () => {
    linkDocLoading.value = true
    try {
      const res = await salesDocumentApi.getList({ keyword: linkDocSearch.value, limit: 20 })
      linkDocResults.value = res.data.items || []
    } catch { linkDocResults.value = [] }
    finally { linkDocLoading.value = false }
  }, 300)
}

async function linkDocument(docId: number) {
  if (!activity.value) return
  try {
    const res = await apiClient.post(`/sales-documents/${docId}/link-activity?activity_id=${activity.value.id}`)
    const count = res.data?.linked_count || 1
    showToast(`문서 ${count}건이 연결되었습니다 (관련 Q/PI/CI 자동 포함)`, 'success')
    // 검색 결과에서 연결됨 표시
    const doc = linkDocResults.value.find((d: any) => d.id === docId)
    if (doc) doc.sales_activity_id = activity.value.id
    await loadData()
    emit('updated')
  } catch {
    showToast('연결에 실패했습니다', 'error')
  }
}

onMounted(loadData)
onBeforeUnmount(() => { revokeLogAttUrls(); clearStaged(); clearEditStaged() })
</script>
