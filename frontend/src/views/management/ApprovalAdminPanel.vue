<template>
  <div class="approval-admin-panel">
    <!-- 섹션 탭 -->
    <div class="border-b border-gray-200 mb-4">
      <nav class="-mb-px flex space-x-6">
        <button
          v-for="t in sectionTabs"
          :key="t.key"
          @click="activeSection = t.key"
          :class="[
            'py-2 px-1 border-b-2 text-sm font-medium transition-colors',
            activeSection === t.key
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >{{ t.label }}</button>
      </nav>
    </div>

    <!-- ===== 집행 담당 지정 ===== -->
    <DisbursementApproverPanel v-if="activeSection === 'disbursement'" />

    <!-- ===== 프로젝트 관리 ===== -->
    <div v-if="activeSection === 'projects'">
      <!-- 추가 -->
      <div class="bg-white rounded-lg shadow p-4 mb-4">
        <h3 class="text-sm font-bold text-gray-700 mb-3">프로젝트 추가</h3>
        <div class="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div>
            <label class="block text-xs text-gray-500 mb-1">코드 <span class="text-red-500">*</span></label>
            <input
              v-model="newProject.code"
              type="text"
              placeholder="PRJ-001"
              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div class="sm:col-span-2">
            <label class="block text-xs text-gray-500 mb-1">이름 <span class="text-red-500">*</span></label>
            <input
              v-model="newProject.name"
              type="text"
              placeholder="프로젝트명"
              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-xs text-gray-500 mb-1">정렬</label>
            <input
              v-model.number="newProject.sort_order"
              type="number"
              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <div class="flex justify-end mt-3">
          <button
            @click="onCreateProject"
            :disabled="projectSaving || !newProject.code.trim() || !newProject.name.trim()"
            class="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >{{ projectSaving ? '저장 중...' : '추가' }}</button>
        </div>
      </div>

      <!-- 목록 -->
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <div v-if="projectsLoading" class="py-10 text-center text-gray-500 text-sm">로딩 중...</div>
        <table v-else class="min-w-full text-sm">
          <thead>
            <tr class="bg-gray-50 text-left text-gray-600">
              <th class="px-3 py-2 font-medium">코드</th>
              <th class="px-3 py-2 font-medium">이름</th>
              <th class="px-3 py-2 font-medium">정렬</th>
              <th class="px-3 py-2 font-medium">활성</th>
              <th class="px-3 py-2 font-medium text-right">작업</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="p in projects" :key="p.id" class="hover:bg-gray-50">
              <td class="px-3 py-2 font-mono text-blue-600 whitespace-nowrap">{{ p.code }}</td>
              <td class="px-3 py-2">
                <input
                  v-model="p.name"
                  type="text"
                  class="w-full px-2 py-1 border border-gray-200 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </td>
              <td class="px-3 py-2 text-gray-700 whitespace-nowrap">{{ p.sort_order }}</td>
              <td class="px-3 py-2 whitespace-nowrap">
                <span
                  class="px-2 py-0.5 text-xs font-medium rounded-full"
                  :class="p.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
                >{{ p.is_active ? '활성' : '비활성' }}</span>
              </td>
              <td class="px-3 py-2 text-right whitespace-nowrap">
                <button
                  @click="onRenameProject(p)"
                  class="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 mr-1"
                >이름 저장</button>
                <button
                  @click="onToggleProject(p)"
                  class="px-3 py-1 text-xs rounded text-white"
                  :class="p.is_active ? 'bg-yellow-500 hover:bg-yellow-600' : 'bg-green-600 hover:bg-green-700'"
                >{{ p.is_active ? '비활성화' : '활성화' }}</button>
              </td>
            </tr>
            <tr v-if="!projects.length">
              <td colspan="5" class="px-3 py-10 text-center text-gray-400">프로젝트가 없습니다.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 검색 영역 -->
    <template v-else>
    <div class="bg-white rounded-lg shadow p-4 mb-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div class="lg:col-span-2">
          <label class="block text-xs text-gray-500 mb-1">키워드 (제목/문서번호)</label>
          <input
            v-model="search.keyword"
            type="text"
            placeholder="제목, 문서번호, 기안자"
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            @keyup.enter="onSearch"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">상태</label>
          <select
            v-model="search.status"
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">전체</option>
            <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">
              {{ APPROVAL_STATUS_LABELS[s] }}
            </option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">생성일 (From)</label>
          <input
            v-model="search.date_from"
            type="date"
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">생성일 (To)</label>
          <input
            v-model="search.date_to"
            type="date"
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
      <div class="flex justify-end gap-2 mt-3">
        <button
          @click="onReset"
          class="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
        >초기화</button>
        <button
          @click="onSearch"
          :disabled="listLoading"
          class="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >검색</button>
      </div>
    </div>

    <!-- 결과 표 -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <div v-if="listLoading" class="py-10 text-center text-gray-500 text-sm">로딩 중...</div>
      <table v-else class="min-w-full text-sm">
        <thead>
          <tr class="bg-gray-50 text-left text-gray-600">
            <th class="px-3 py-2 font-medium">문서번호</th>
            <th class="px-3 py-2 font-medium">제목</th>
            <th class="px-3 py-2 font-medium">기안자</th>
            <th class="px-3 py-2 font-medium">상태</th>
            <th class="px-3 py-2 font-medium">현재단계</th>
            <th class="px-3 py-2 font-medium">상신일</th>
            <th class="px-3 py-2 font-medium">생성일</th>
            <th class="px-3 py-2 font-medium text-right">작업</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr
            v-for="item in items"
            :key="item.id"
            class="hover:bg-blue-50 cursor-pointer"
            @click="openDetail(item.id)"
          >
            <td class="px-3 py-2 font-mono text-blue-600 whitespace-nowrap">{{ item.doc_number }}</td>
            <td class="px-3 py-2 text-gray-800">{{ item.title }}</td>
            <td class="px-3 py-2 text-gray-700 whitespace-nowrap">{{ item.drafter_name || '-' }}</td>
            <td class="px-3 py-2 whitespace-nowrap">
              <span class="px-2 py-0.5 text-xs font-medium rounded-full" :class="APPROVAL_STATUS_BADGE[item.status]">
                {{ APPROVAL_STATUS_LABELS[item.status] }}
              </span>
            </td>
            <td class="px-3 py-2 text-gray-700 whitespace-nowrap">{{ item.current_step }}차</td>
            <td class="px-3 py-2 text-gray-500 whitespace-nowrap">{{ formatDateTime(item.drafted_at) }}</td>
            <td class="px-3 py-2 text-gray-500 whitespace-nowrap">{{ formatDateTime(item.created_at) }}</td>
            <td class="px-3 py-2 text-right whitespace-nowrap">
              <button
                @click.stop="openDetail(item.id)"
                class="px-3 py-1 text-xs bg-orange-500 text-white rounded hover:bg-orange-600"
              >정정</button>
            </td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="8" class="px-3 py-10 text-center text-gray-400">검색 결과가 없습니다.</td>
          </tr>
        </tbody>
      </table>
      <Pagination
        v-if="total > 0"
        :total="total"
        :page-size="pageSize"
        :current-page="currentPage"
        @update:current-page="onPageChange"
        @update:page-size="onPageSizeChange"
      />
    </div>
    </template>

    <!-- 상세 / 정정 모달 -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="detailOpen"
          class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
          @click.self="closeDetail"
        >
          <div class="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] overflow-y-auto">
            <!-- 헤더 -->
            <div class="flex justify-between items-center px-5 py-3 border-b sticky top-0 bg-white z-10">
              <div class="flex items-center gap-3">
                <h3 class="text-lg font-bold text-gray-800">결재 문서 정정</h3>
                <button v-if="doc" @click="openFullEdit"
                  title="작성 화면을 그대로 열어 제목·본문·품목표·거래처·사유 등 전체를 수정합니다(상태·결재선 보존)"
                  class="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 whitespace-nowrap">
                  ✎ 작성 화면에서 전체 수정
                </button>
              </div>
              <button class="text-gray-400 hover:text-gray-700 text-2xl leading-none" @click="closeDetail">&times;</button>
            </div>

            <div v-if="detailLoading" class="py-16 text-center text-gray-500">로딩 중...</div>

            <div v-else-if="doc" class="p-5 space-y-5">
              <!-- 문서 요약 -->
              <div>
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-mono text-sm text-blue-600">{{ doc.doc_number }}</span>
                  <span class="px-2 py-0.5 text-xs font-medium rounded-full" :class="APPROVAL_STATUS_BADGE[doc.status]">
                    {{ APPROVAL_STATUS_LABELS[doc.status] }}
                  </span>
                  <span v-if="doc.is_corrected" class="px-2 py-0.5 text-xs rounded bg-orange-100 text-orange-700">관리자 정정됨</span>
                </div>
                <h4 class="text-xl font-bold text-gray-800 mt-1">{{ doc.title }}</h4>
              </div>

              <!-- 메타 -->
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm border rounded-lg p-3">
                <div><span class="text-gray-400">기안자</span><div class="font-medium text-gray-800">{{ doc.drafter_name || '-' }}</div></div>
                <div><span class="text-gray-400">상신일시</span><div class="font-medium text-gray-800">{{ formatDateTime(doc.drafted_at) }}</div></div>
                <div><span class="text-gray-400">완료일시</span><div class="font-medium text-gray-800">{{ formatDateTime(doc.completed_at) }}</div></div>
                <div><span class="text-gray-400">현재단계</span><div class="font-medium text-gray-800">{{ doc.current_step }}차</div></div>
              </div>

              <!-- 본문 -->
              <div>
                <h5 class="text-sm font-semibold text-gray-600 mb-1">본문</h5>
                <div v-if="doc.content" class="border rounded-lg p-3 text-sm text-gray-800 whitespace-pre-wrap max-h-40 overflow-y-auto" v-html="doc.content"></div>
                <div v-else class="text-sm text-gray-400">내용 없음</div>
              </div>

              <!-- 결재선 -->
              <div>
                <h5 class="text-sm font-semibold text-gray-600 mb-1">결재선</h5>
                <table class="min-w-full text-sm border rounded-lg overflow-hidden">
                  <thead>
                    <tr class="bg-gray-50 text-left text-gray-500">
                      <th class="px-3 py-1.5 font-medium">단계</th>
                      <th class="px-3 py-1.5 font-medium">결재자</th>
                      <th class="px-3 py-1.5 font-medium">직위</th>
                      <th class="px-3 py-1.5 font-medium">상태</th>
                      <th class="px-3 py-1.5 font-medium">처리일시</th>
                      <th class="px-3 py-1.5 font-medium">의견</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-100">
                    <tr v-for="line in sortedLines" :key="line.id">
                      <td class="px-3 py-1.5">{{ line.step_order }}차</td>
                      <td class="px-3 py-1.5">{{ line.approver_name || '-' }}</td>
                      <td class="px-3 py-1.5">{{ line.approver_position || '-' }}</td>
                      <td class="px-3 py-1.5">{{ LINE_STATUS_LABELS[line.status] }}</td>
                      <td class="px-3 py-1.5 text-gray-500">{{ formatDateTime(line.acted_at) }}</td>
                      <td class="px-3 py-1.5 text-gray-600">{{ line.comment || '-' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- 처리 이력 -->
              <div>
                <h5 class="text-sm font-semibold text-gray-600 mb-1">처리 이력</h5>
                <table class="min-w-full text-sm border rounded-lg overflow-hidden">
                  <thead>
                    <tr class="bg-gray-50 text-left text-gray-500">
                      <th class="px-3 py-1.5 font-medium">행위</th>
                      <th class="px-3 py-1.5 font-medium">처리자</th>
                      <th class="px-3 py-1.5 font-medium">처리일시</th>
                      <th class="px-3 py-1.5 font-medium">의견</th>
                      <th class="px-3 py-1.5 font-medium">IP</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-100">
                    <tr v-for="act in doc.actions" :key="act.id">
                      <td class="px-3 py-1.5">{{ ACTION_LABELS[act.action] }}</td>
                      <td class="px-3 py-1.5">{{ act.actor_name || '-' }}</td>
                      <td class="px-3 py-1.5 text-gray-500">{{ formatDateTime(act.acted_at) }}</td>
                      <td class="px-3 py-1.5 text-gray-600">{{ act.comment || '-' }}</td>
                      <td class="px-3 py-1.5 text-gray-400 font-mono text-xs">{{ act.ip_address || '-' }}</td>
                    </tr>
                    <tr v-if="!doc.actions.length">
                      <td colspan="5" class="px-3 py-4 text-center text-gray-400">이력이 없습니다.</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- 정정 폼 -->
              <div class="border-2 border-orange-200 rounded-lg p-4 bg-orange-50/40">
                <h5 class="text-sm font-bold text-orange-700 mb-3">정정 입력</h5>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div class="sm:col-span-2">
                    <label class="block text-xs text-gray-500 mb-1">정정 항목</label>
                    <select
                      v-model="selectedTargetKey"
                      class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                    >
                      <option value="">선택하세요</option>
                      <option v-for="t in correctTargets" :key="t.key" :value="t.key">{{ t.label }}</option>
                    </select>
                  </div>
                  <div class="sm:col-span-2">
                    <label class="block text-xs text-gray-500 mb-1">
                      {{ isContentField ? '문서 본문 (현재 내용을 그 자리에서 수정)' : '새 값' }}
                    </label>
                    <!-- 문서 본문: 작성 화면과 동일한 리치 에디터로, 현재 내용 그대로 보고 수정 -->
                    <MarkupEditor
                      v-if="isContentField"
                      v-model="newValue"
                      multiline
                      images
                      min-height="260px"
                    />
                    <input
                      v-else-if="selectedTarget && selectedTarget.kind === 'date'"
                      v-model="newValue"
                      type="date"
                      class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                    />
                    <input
                      v-else-if="selectedTarget && selectedTarget.kind === 'datetime'"
                      v-model="newValue"
                      type="datetime-local"
                      class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                    />
                    <textarea
                      v-else-if="selectedTarget && selectedTarget.kind === 'textarea'"
                      v-model="newValue"
                      rows="4"
                      class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                    ></textarea>
                    <input
                      v-else
                      v-model="newValue"
                      type="text"
                      :disabled="!selectedTarget"
                      class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 disabled:bg-gray-100"
                    />
                  </div>
                  <div v-if="selectedTarget && !selectedTarget.dateField" class="sm:col-span-2">
                    <label class="block text-xs text-gray-500 mb-1">정정 사유 (필수)</label>
                    <textarea
                      v-model="reason"
                      rows="2"
                      placeholder="정정 사유를 입력하세요"
                      class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                    ></textarea>
                  </div>
                  <p v-else-if="selectedTarget && selectedTarget.dateField" class="sm:col-span-2 text-xs text-gray-400">
                    이 항목은 사유 없이 즉시 반영되며, 정정 이력에 남지 않습니다.
                  </p>
                </div>
                <div class="flex justify-end mt-3">
                  <button
                    @click="onSaveCorrection"
                    :disabled="saving || !selectedTarget || (!selectedTarget.dateField && !reason.trim())"
                    class="px-4 py-2 text-sm bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50"
                  >{{ saving ? '저장 중...' : (selectedTarget && selectedTarget.dateField ? '저장' : '정정 저장') }}</button>
                </div>
              </div>

              <!-- 정정 이력 -->
              <div>
                <h5 class="text-sm font-semibold text-gray-600 mb-1">정정 이력</h5>
                <table class="min-w-full text-sm border rounded-lg overflow-hidden">
                  <thead>
                    <tr class="bg-gray-50 text-left text-gray-500">
                      <th class="px-3 py-1.5 font-medium">항목</th>
                      <th class="px-3 py-1.5 font-medium">이전값</th>
                      <th class="px-3 py-1.5 font-medium">새값</th>
                      <th class="px-3 py-1.5 font-medium">사유</th>
                      <th class="px-3 py-1.5 font-medium">정정자</th>
                      <th class="px-3 py-1.5 font-medium">정정일시</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-100">
                    <tr v-for="c in corrections" :key="c.id">
                      <td class="px-3 py-1.5 whitespace-nowrap">{{ c.target_table }}.{{ c.field_name }}</td>
                      <td class="px-3 py-1.5 text-gray-500 max-w-[12rem] truncate" :title="c.old_value || ''">{{ c.old_value || '-' }}</td>
                      <td class="px-3 py-1.5 text-gray-800 max-w-[12rem] truncate" :title="c.new_value || ''">{{ c.new_value || '-' }}</td>
                      <td class="px-3 py-1.5 text-gray-600 max-w-[12rem] truncate" :title="c.reason">{{ c.reason }}</td>
                      <td class="px-3 py-1.5 text-gray-500 whitespace-nowrap">{{ c.corrected_by || '-' }}</td>
                      <td class="px-3 py-1.5 text-gray-500 whitespace-nowrap">{{ formatDateTime(c.corrected_at) }}</td>
                    </tr>
                    <tr v-if="!corrections.length">
                      <td colspan="6" class="px-3 py-4 text-center text-gray-400">정정 이력이 없습니다.</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import Pagination from '@/components/Pagination.vue'
import DisbursementApproverPanel from '@/views/management/DisbursementApproverPanel.vue'
import MarkupEditor from '@/components/common/MarkupEditor.vue'
import { useToast } from '@/composables/useToast'
import {
  approvalApi,
  APPROVAL_STATUS_BADGE,
  APPROVAL_STATUS_LABELS,
  LINE_STATUS_LABELS,
  ACTION_LABELS,
  type ApprovalStatus,
  type ApprovalDocument,
  type ApprovalListItem,
  type ApprovalCorrection,
  type ApprovalProject,
} from '@/api/approval'

const { success, error, warning } = useToast()

// ─────────── 섹션 탭 ───────────
type SectionKey = 'search' | 'projects' | 'disbursement'
const sectionTabs: { key: SectionKey; label: string }[] = [
  { key: 'search', label: '결재 검색/정정' },
  { key: 'projects', label: '프로젝트 관리' },
  { key: 'disbursement', label: '집행 담당 지정' },
]
const activeSection = ref<SectionKey>('search')

// ─────────── 프로젝트 관리 ───────────
const projects = ref<ApprovalProject[]>([])
const projectsLoading = ref(false)
const projectSaving = ref(false)
const newProject = ref<{ code: string; name: string; sort_order: number }>({
  code: '',
  name: '',
  sort_order: 0,
})

const loadProjects = async () => {
  projectsLoading.value = true
  try {
    const res = await approvalApi.adminListProjects()
    projects.value = res.data
  } catch {
    error('프로젝트 목록을 불러오지 못했습니다')
  } finally {
    projectsLoading.value = false
  }
}

const onCreateProject = async () => {
  const code = newProject.value.code.trim()
  const name = newProject.value.name.trim()
  if (!code || !name) {
    warning('코드와 이름을 입력하세요')
    return
  }
  projectSaving.value = true
  try {
    await approvalApi.adminCreateProject({
      code,
      name,
      sort_order: newProject.value.sort_order || undefined,
    })
    success('프로젝트가 추가되었습니다')
    newProject.value = { code: '', name: '', sort_order: 0 }
    await loadProjects()
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    if (status === 409 || status === 400) error('이미 존재하는 코드입니다')
    else error('프로젝트 추가에 실패했습니다')
  } finally {
    projectSaving.value = false
  }
}

const onToggleProject = async (p: ApprovalProject) => {
  try {
    await approvalApi.adminUpdateProject(p.id, { is_active: !p.is_active })
    success(p.is_active ? '비활성화되었습니다' : '활성화되었습니다')
    await loadProjects()
  } catch {
    error('상태 변경에 실패했습니다')
  }
}

const onRenameProject = async (p: ApprovalProject) => {
  const name = p.name.trim()
  if (!name) {
    warning('이름을 입력하세요')
    return
  }
  try {
    await approvalApi.adminUpdateProject(p.id, { name })
    success('이름이 저장되었습니다')
    await loadProjects()
  } catch {
    error('이름 저장에 실패했습니다')
  }
}

const STATUS_OPTIONS: ApprovalStatus[] = ['DRAFT', 'IN_PROGRESS', 'APPROVED', 'REJECTED', 'CANCELED']

// ─────────── 검색 / 목록 ───────────
const search = ref<{ keyword: string; status: ApprovalStatus | ''; date_from: string; date_to: string }>({
  keyword: '',
  status: '',
  date_from: '',
  date_to: '',
})
const items = ref<ApprovalListItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const listLoading = ref(false)

const formatDateTime = (v?: string | null) => (v ? new Date(v).toLocaleString('ko-KR') : '-')

const loadList = async () => {
  listLoading.value = true
  try {
    const res = await approvalApi.adminSearch({
      keyword: search.value.keyword || undefined,
      status: search.value.status || undefined,
      date_from: search.value.date_from || undefined,
      date_to: search.value.date_to || undefined,
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    })
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    error('결재 문서 검색에 실패했습니다')
  } finally {
    listLoading.value = false
  }
}

const onSearch = () => {
  currentPage.value = 1
  loadList()
}

const onReset = () => {
  search.value = { keyword: '', status: '', date_from: '', date_to: '' }
  currentPage.value = 1
  loadList()
}

const onPageChange = (page: number) => {
  currentPage.value = page
  loadList()
}

const onPageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  loadList()
}

// ─────────── 상세 / 정정 ───────────
const detailOpen = ref(false)
const detailLoading = ref(false)
const doc = ref<ApprovalDocument | null>(null)
const corrections = ref<ApprovalCorrection[]>([])
const saving = ref(false)

const selectedTargetKey = ref('')
const newValue = ref('')
const reason = ref('')

const sortedLines = computed(() =>
  doc.value ? [...doc.value.lines].sort((a, b) => a.step_order - b.step_order) : [],
)

type FieldKind = 'text' | 'textarea' | 'datetime' | 'date'
interface CorrectTarget {
  key: string
  label: string
  kind: FieldKind
  // 일반 정정(사유 필수 + 이력 기록)
  target_table?: string
  target_id?: number
  field_name?: string
  // 무흔적 일자 수정(사유·이력 없음): 'executed_at'=시행일자, 'exec_date'=결제·집행일
  dateField?: 'executed_at' | 'exec_date'
}

// 정정 가능 항목 구성 (백엔드 허용 필드만)
const correctTargets = computed<CorrectTarget[]>(() => {
  if (!doc.value) return []
  const d = doc.value
  const targets: CorrectTarget[] = []
  // ── 무흔적 일자 수정 (사유·이력 없음) ──
  if (d.execution_status || d.executor_name || d.form_code === 'PURCHASE') {
    targets.push({ key: `dates-${d.id}-executed_at`, label: '시행일자 (이력 없음)', kind: 'date', dateField: 'executed_at' })
  }
  if (d.form_code === 'DISBURSEMENT' || (d.form_data && Object.prototype.hasOwnProperty.call(d.form_data, 'exec_date'))) {
    targets.push({ key: `dates-${d.id}-exec_date`, label: '결제·집행일 (이력 없음)', kind: 'date', dateField: 'exec_date' })
  }
  targets.push(
    { key: `documents-${d.id}-title`, label: '문서 제목', target_table: 'documents', target_id: d.id, field_name: 'title', kind: 'text' },
    { key: `documents-${d.id}-content`, label: '문서 본문', target_table: 'documents', target_id: d.id, field_name: 'content', kind: 'textarea' },
    { key: `documents-${d.id}-drafted_at`, label: '문서 상신일시', target_table: 'documents', target_id: d.id, field_name: 'drafted_at', kind: 'datetime' },
    { key: `documents-${d.id}-completed_at`, label: '문서 완료일시', target_table: 'documents', target_id: d.id, field_name: 'completed_at', kind: 'datetime' },
  )
  for (const line of sortedLines.value) {
    const stepLabel = `${line.step_order}차 결재(${line.approver_name || '미지정'})`
    targets.push(
      { key: `lines-${line.id}-comment`, label: `${stepLabel} 의견`, target_table: 'lines', target_id: line.id, field_name: 'comment', kind: 'textarea' },
      { key: `lines-${line.id}-acted_at`, label: `${stepLabel} 처리일시`, target_table: 'lines', target_id: line.id, field_name: 'acted_at', kind: 'datetime' },
      { key: `lines-${line.id}-approver_name`, label: `${stepLabel} 결재자명`, target_table: 'lines', target_id: line.id, field_name: 'approver_name', kind: 'text' },
      { key: `lines-${line.id}-approver_position`, label: `${stepLabel} 결재자 직위`, target_table: 'lines', target_id: line.id, field_name: 'approver_position', kind: 'text' },
    )
  }
  for (const act of d.actions) {
    const actLabel = `이력 #${act.id} ${ACTION_LABELS[act.action]}(${act.actor_name || '-'})`
    targets.push(
      { key: `actions-${act.id}-comment`, label: `${actLabel} 의견`, target_table: 'actions', target_id: act.id, field_name: 'comment', kind: 'textarea' },
      { key: `actions-${act.id}-acted_at`, label: `${actLabel} 처리일시`, target_table: 'actions', target_id: act.id, field_name: 'acted_at', kind: 'datetime' },
    )
  }
  return targets
})

const selectedTarget = computed<CorrectTarget | null>(
  () => correctTargets.value.find((t) => t.key === selectedTargetKey.value) || null,
)

// 본문(content) 항목 여부 — 작성 화면과 동일하게 MarkupEditor로 편집
const isContentField = computed(() =>
  selectedTarget.value?.target_table === 'documents' && selectedTarget.value?.field_name === 'content'
)

// ISO/문자열 → datetime-local 입력값('YYYY-MM-DDTHH:MM')
function toDatetimeLocal(v?: string | null): string {
  if (!v) return ''
  return String(v).replace(' ', 'T').slice(0, 16)
}

// 선택한 정정 항목의 '현재 값'을 읽어와 프리필(원본을 보고 그 자리에서 수정)
function currentValueFor(t: CorrectTarget): string {
  const d: any = doc.value
  if (!d) return ''
  if (t.dateField === 'executed_at') return d.executed_at ? String(d.executed_at).slice(0, 10) : ''
  if (t.dateField === 'exec_date') { const ed = d.form_data?.exec_date; return ed ? String(ed).slice(0, 10) : '' }
  if (t.target_table === 'documents') {
    if (t.field_name === 'title') return d.title || ''
    if (t.field_name === 'content') return d.content || ''
    if (t.field_name === 'drafted_at') return toDatetimeLocal(d.drafted_at)
    if (t.field_name === 'completed_at') return toDatetimeLocal(d.completed_at)
  }
  if (t.target_table === 'lines') {
    const ln = (d.lines || []).find((l: any) => l.id === t.target_id)
    if (ln) {
      if (t.field_name === 'comment') return ln.comment || ''
      if (t.field_name === 'approver_name') return ln.approver_name || ''
      if (t.field_name === 'approver_position') return ln.approver_position || ''
      if (t.field_name === 'acted_at') return toDatetimeLocal(ln.acted_at)
    }
  }
  if (t.target_table === 'actions') {
    const ac = (d.actions || []).find((a: any) => a.id === t.target_id)
    if (ac) {
      if (t.field_name === 'comment') return ac.comment || ''
      if (t.field_name === 'acted_at') return toDatetimeLocal(ac.acted_at)
    }
  }
  return ''
}

// 항목 선택 시: 현재 값을 프리필(원본 표시) → 그 자리에서 수정
watch(selectedTargetKey, () => {
  reason.value = ''
  const t = selectedTarget.value
  newValue.value = t ? currentValueFor(t) : ''
})

const openDetail = async (id: number) => {
  detailOpen.value = true
  detailLoading.value = true
  selectedTargetKey.value = ''
  newValue.value = ''
  reason.value = ''
  doc.value = null
  corrections.value = []
  try {
    const [docRes, corrRes] = await Promise.all([
      approvalApi.getById(id),
      approvalApi.getCorrections(id),
    ])
    doc.value = docRes.data
    corrections.value = corrRes.data
  } catch {
    error('문서를 불러오지 못했습니다')
    detailOpen.value = false
  } finally {
    detailLoading.value = false
  }
}

const closeDetail = () => {
  detailOpen.value = false
}

// 작성 화면(관리자 전체수정 모드)으로 이동 — 상태·결재선 보존, 문서 전체 수정
const router = useRouter()
function openFullEdit() {
  if (!doc.value) return
  router.push(`/approvals/${doc.value.id}/edit?admin=1`)
}

// datetime-local('YYYY-MM-DDTHH:MM') → 'YYYY-MM-DD HH:MM'
const normalizeDateValue = (v: string) => v.replace('T', ' ')

const onSaveCorrection = async () => {
  if (!doc.value || !selectedTarget.value) return
  const t = selectedTarget.value
  saving.value = true
  try {
    if (t.dateField) {
      // 무흔적 일자 수정 (사유·정정이력 없음)
      const payload = t.dateField === 'executed_at'
        ? { executed_at: newValue.value }
        : { exec_date: newValue.value }
      await approvalApi.adminSetDates(doc.value.id, payload)
      success('일자가 수정되었습니다')
    } else {
      if (!reason.value.trim()) {
        warning('정정 사유를 입력하세요')
        saving.value = false
        return
      }
      const value = t.kind === 'datetime' ? normalizeDateValue(newValue.value) : newValue.value
      await approvalApi.adminCorrect(doc.value.id, {
        target_table: t.target_table!,
        target_id: t.target_id!,
        field_name: t.field_name!,
        new_value: value,
        reason: reason.value.trim(),
      })
      success('정정이 저장되었습니다')
    }
    // 상세 / 이력 새로고침
    const id = doc.value.id
    const [docRes, corrRes] = await Promise.all([
      approvalApi.getById(id),
      approvalApi.getCorrections(id),
    ])
    doc.value = docRes.data
    corrections.value = corrRes.data
    selectedTargetKey.value = ''
    newValue.value = ''
    reason.value = ''
    // 목록 상태 갱신
    loadList()
  } catch {
    error('정정 저장에 실패했습니다')
  } finally {
    saving.value = false
  }
}

// 프로젝트 탭 최초 진입 시 로드
watch(activeSection, (s) => {
  if (s === 'projects' && !projects.value.length) loadProjects()
})

onMounted(() => {
  loadList()
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
