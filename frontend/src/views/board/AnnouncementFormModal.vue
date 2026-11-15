<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { departments, loadDepartments, departmentLabel } from '@/api/department'
import { announcementApi, type AnnouncementDetail, type AnnouncementAttachment } from '@/api/announcement'
import RichTextEditor from '@/components/editor/RichTextEditor.vue'
import FileManager, { type FileManagerItem } from '@/components/files/FileManager.vue'

const props = defineProps<{ announcement?: AnnouncementDetail | null }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'saved'): void }>()
const { success, error, warning } = useToast()

const isEdit = computed(() => !!props.announcement)
const busy = ref(false)

const title = ref(props.announcement?.title || '')
const body = ref(props.announcement?.body || '')
const isPinned = ref(props.announcement?.is_pinned || false)
// null/[] = 전체. 선택된 부서코드 Set
const allDepts = ref(!props.announcement?.target_departments || props.announcement.target_departments.length === 0)
const selectedDepts = ref<Set<string>>(new Set(props.announcement?.target_departments || []))

// 첨부: 편집모드는 기존 목록 즉시 반영, 작성모드는 파일을 스테이징 후 생성 직후 업로드
const existing = ref<AnnouncementAttachment[]>(props.announcement?.attachments ? [...props.announcement.attachments] : [])
const staged = ref<File[]>([])

onMounted(loadDepartments)

function toggleDept(code: string) {
  const s = new Set(selectedDepts.value)
  s.has(code) ? s.delete(code) : s.add(code)
  selectedDepts.value = s
}

// FileManager 표시용 목록: 업로드된 첨부 + 업로드 대기 파일
const fileItems = computed<FileManagerItem[]>(() => [
  ...existing.value.map((a) => ({ key: `e${a.id}`, name: a.original_name, size: a.file_size })),
  ...staged.value.map((f, i) => ({ key: `s${i}`, name: f.name, size: f.size, pending: true })),
])

function onRemoveFile(item: FileManagerItem) {
  const key = String(item.key)
  if (key.startsWith('s')) return removeStaged(Number(key.slice(1)))
  const att = existing.value.find((a) => `e${a.id}` === key)
  if (att) removeExisting(att)
}

function onAddFiles(files: File[]) {
  if (isEdit.value && props.announcement) {
    uploadNow(files)
  } else {
    staged.value.push(...files)
  }
}

async function uploadNow(files: File[]) {
  if (!props.announcement) return
  busy.value = true
  try {
    for (const f of files) {
      const att = await announcementApi.uploadAttachment(props.announcement.id, f)
      existing.value.push(att)
    }
    success('첨부 업로드됨')
  } catch (e: any) {
    error(e?.response?.data?.detail || '첨부 업로드 실패')
  } finally {
    busy.value = false
  }
}

async function removeExisting(att: AnnouncementAttachment) {
  if (!props.announcement) return
  if (!confirm(`첨부 '${att.original_name}' 삭제할까요?`)) return
  try {
    await announcementApi.deleteAttachment(props.announcement.id, att.id)
    existing.value = existing.value.filter((a) => a.id !== att.id)
    success('첨부 삭제됨')
  } catch (e: any) {
    error(e?.response?.data?.detail || '첨부 삭제 실패')
  }
}

function removeStaged(idx: number) {
  staged.value.splice(idx, 1)
}

async function submit() {
  if (busy.value) return  // 중복 제출(더블클릭) 방지
  if (!title.value.trim()) return warning('제목을 입력하세요')
  const targets = allDepts.value ? null : Array.from(selectedDepts.value)
  if (!allDepts.value && (!targets || targets.length === 0)) return warning('대상 부서를 선택하거나 전체 공개를 선택하세요')
  busy.value = true
  try {
    const payload = { title: title.value.trim(), body: body.value, is_pinned: isPinned.value, target_departments: targets }
    if (isEdit.value && props.announcement) {
      await announcementApi.update(props.announcement.id, payload)
    } else {
      const created = await announcementApi.create(payload)
      // 작성모드 스테이징 첨부 업로드
      for (const f of staged.value) {
        await announcementApi.uploadAttachment(created.id, f)
      }
    }
    success(isEdit.value ? '공지 수정됨' : '공지 등록됨')
    emit('saved')
  } catch (e: any) {
    error(e?.response?.data?.detail || '저장 실패')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" @click.self="emit('close')">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[92vh]">
      <div class="flex items-center justify-between px-5 py-3 border-b">
        <h3 class="text-base font-semibold text-gray-800">{{ isEdit ? '공지 수정' : '새 공지 작성' }}</h3>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600" aria-label="닫기">✕</button>
      </div>

      <div class="px-5 py-4 space-y-4 overflow-y-auto">
        <div>
          <label class="block text-xs text-gray-500 mb-1">제목</label>
          <input v-model="title" class="inp w-full" placeholder="공지 제목" maxlength="300" />
        </div>

        <div>
          <label class="block text-xs text-gray-500 mb-1">본문</label>
          <!-- preserve-legacy-blocks: 이전 에디터로 쓴 공지의 제목/목록/인용이 수정 시 사라지지 않도록 -->
          <RichTextEditor v-model="body" placeholder="공지 내용을 입력하세요" preserve-legacy-blocks />
        </div>

        <div class="flex items-center gap-4">
          <label class="inline-flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" v-model="isPinned" /> 상단 고정(핀)
          </label>
        </div>

        <div>
          <label class="block text-xs text-gray-500 mb-1">대상</label>
          <label class="inline-flex items-center gap-2 text-sm text-gray-700 mb-2">
            <input type="checkbox" v-model="allDepts" /> 전체 공개(모든 부서)
          </label>
          <div v-if="!allDepts" class="flex flex-wrap gap-2">
            <label v-for="d in departments" :key="d.code"
                   class="inline-flex items-center gap-1.5 px-2 py-1 border rounded text-sm cursor-pointer"
                   :class="selectedDepts.has(d.code) ? 'bg-blue-50 border-blue-400 text-blue-700' : 'border-gray-300 text-gray-600'">
              <input type="checkbox" :checked="selectedDepts.has(d.code)" @change="toggleDept(d.code)" />
              {{ d.name }}
            </label>
            <span v-if="!departments.length" class="text-xs text-gray-400">부서 목록 없음</span>
          </div>
        </div>

        <FileManager title="첨부파일" :items="fileItems" :busy="busy" @add="onAddFiles" @remove="onRemoveFile" />
      </div>

      <div class="px-5 py-3 border-t flex justify-end gap-2">
        <button type="button" @click="emit('close')" class="px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded">취소</button>
        <button :disabled="busy" @click="submit" class="px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50">
          {{ busy ? '저장 중...' : (isEdit ? '수정' : '등록') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.inp { @apply px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500; }
</style>
