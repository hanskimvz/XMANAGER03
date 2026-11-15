<!--
  BOM 편집 화면 좌측 부품 팔레트 (BOM 개편 2026-09)
  - 찾기 또는 만들기(find-or-create): 검색 재사용 + 없으면 이름만으로 즉석 생성(미분류)
  - 드래그하여 우측 트리에 배치. 여러 개 선택 시 일괄 드래그(P3)
  - placedCounts로 '배치×N' 배지 + '미배치만' 필터. '더 보기'로 결과 확장(P4)
-->
<template>
  <div class="pal">
    <div class="pal-head">
      <div class="pal-search">
        <input
          ref="searchInput"
          v-model="keyword"
          type="text"
          placeholder="부품 검색 또는 새 이름 입력…"
          @input="onSearch"
        />
        <span v-if="loading" class="pal-spin">…</span>
      </div>
      <div class="pal-headrow">
        <label class="pal-filter"><input type="checkbox" v-model="unplacedOnly" /> 미배치만</label>
        <span class="pal-count-total" v-if="total > 0">총 {{ total }}</span>
      </div>
    </div>

    <!-- 다중선택 바 -->
    <div v-if="selectedMap.size > 0" class="pal-selbar">
      <span><b>{{ selectedMap.size }}개</b> 선택 — 드래그하면 함께 배치</span>
      <button @click="clearSel">해제</button>
    </div>

    <div class="pal-body">
      <!-- 새로 만들어 바로 추가 (검색어가 있으면 항상 노출 — 유사 부품이 있어도 새로 만들 수 있음) -->
      <button v-if="keyword.trim()" class="pal-create-row" @click="createAndPlace" :disabled="creating">
        <span class="pal-create-ic">＋</span>
        <span>‘{{ keyword.trim() }}’ {{ creating ? '추가 중…' : '새로 만들어 최상위에 추가' }}</span>
      </button>

      <div v-if="!loading && results.length === 0 && keyword.trim()" class="pal-note">‘{{ keyword.trim() }}’ 검색 결과가 없습니다.</div>
      <div v-else-if="!loading && results.length === 0 && !keyword.trim()" class="pal-empty">
        <div class="pal-empty-t">부품을 검색하거나 이름을 입력해 새로 만들 수 있습니다.</div>
      </div>

      <!-- 부품 카드 목록 -->
      <div
        v-for="p in filteredResults"
        :key="p.id"
        class="pal-card"
        :class="{ 'pal-just': p.id === justCreatedId, 'pal-sel': selectedMap.has(p.id) }"
        draggable="true"
        @dragstart="onDragStart($event, p)"
        @dragend="onDragEnd"
        @dblclick="$emit('placeUnderRoot', p)"
        title="드래그하여 트리에 배치 (더블클릭 = 최상위 하위로 추가)"
      >
        <input type="checkbox" class="pal-chk" :checked="selectedMap.has(p.id)" @change="toggleSel(p)" @click.stop @dragstart.stop.prevent />
        <span class="pal-grip">⋮⋮</span>
        <div class="pal-info">
          <div class="pal-num">
            <span v-if="p.is_classified !== false">{{ p.part_number_display || p.part_number }}</span>
            <span v-if="p.is_classified === false" class="pal-unc">미분류</span>
          </div>
          <div class="pal-name">{{ p.part_name }}</div>
        </div>
        <span class="pal-count" :class="{ 'pal-count-0': (placedCounts[p.id] || 0) === 0 }">
          배치 ×{{ placedCounts[p.id] || 0 }}
        </span>
      </div>

      <!-- 더 보기 -->
      <button v-if="hasMore && !loading" class="pal-more" @click="loadMore">더 보기 ({{ results.length }}/{{ total }})</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, onMounted, nextTick } from 'vue'
import { partApi, type PartListItem } from '@/api/parts'
import { handleApiError } from '@/utils/errorHandler'
import { useToast } from '@/composables/useToast'

const props = defineProps<{ placedCounts: Record<number, number> }>()
const emit = defineEmits<{ (e: 'placeUnderRoot', part: PartListItem): void }>()

const toast = useToast()
const drag = inject<any>('bomDrag')

const keyword = ref('')
const results = ref<PartListItem[]>([])
const total = ref(0)
const loading = ref(false)
const unplacedOnly = ref(false)
const justCreatedId = ref<number | null>(null)
const searchInput = ref<HTMLInputElement | null>(null)
const PAGE = 30
const limit = ref(PAGE)

// 다중선택(P3)
const selectedMap = ref<Map<number, PartListItem>>(new Map())
function toggleSel(p: PartListItem) {
  const m = new Map(selectedMap.value)
  m.has(p.id) ? m.delete(p.id) : m.set(p.id, p)
  selectedMap.value = m
}
function clearSel() { selectedMap.value = new Map() }

const hasMore = computed(() => results.value.length < total.value)
const filteredResults = computed(() =>
  unplacedOnly.value ? results.value.filter(p => (props.placedCounts[p.id] || 0) === 0) : results.value
)

let timer: ReturnType<typeof setTimeout> | null = null
function onSearch() {
  if (timer) clearTimeout(timer)
  limit.value = PAGE
  const kw = keyword.value.trim()
  if (!kw) { results.value = []; total.value = 0; loading.value = false; return }
  loading.value = true
  timer = setTimeout(() => runSearch(kw), 280)
}
async function runSearch(kw: string) {
  try {
    const res = (await partApi.getAll({ keyword: kw, limit: limit.value })).data
    results.value = res.items
    total.value = res.total
  } catch { results.value = []; total.value = 0 }
  finally { loading.value = false }
}
function loadMore() { limit.value += PAGE; runSearch(keyword.value.trim()) }

const creating = ref(false)
// 새 부품을 만들고 곧바로 최상위 하위로 배치(BOM에 실제로 추가). 팔레트에도 카드로 남김.
async function createAndPlace() {
  const name = keyword.value.trim()
  if (!name) { toast.error('부품 이름을 입력하세요.'); return }
  if (creating.value) return
  creating.value = true
  try {
    const created = (await partApi.createMinimal(name)).data
    const card: PartListItem = {
      id: created.id,
      part_number: created.part_number,
      part_number_display: created.part_number_display,
      part_name: created.part_name,
      is_active: true,
      is_classified: false,
      created_at: new Date().toISOString(),
    } as PartListItem
    results.value = [card, ...results.value]
    total.value += 1
    justCreatedId.value = created.id
    emit('placeUnderRoot', card)  // 실제 BOM(최상위 하위)에 추가 → 트리에 바로 표시
    toast.success(`‘${name}’ 을(를) 만들어 최상위에 추가했습니다.`)
  } catch (e: any) { toast.error(handleApiError(e)) }
  finally { creating.value = false }
}

function onDragStart(e: DragEvent, p: PartListItem) {
  // 선택된 카드를 끌면 선택 전체를 함께(다중), 아니면 단일
  if (selectedMap.value.has(p.id) && selectedMap.value.size > 1) {
    const items = Array.from(selectedMap.value.values()).map(x => ({ partId: x.id, name: x.part_name }))
    drag.value = { kind: 'palette-add-multi', items }
  } else {
    drag.value = { kind: 'palette-add', partId: p.id, name: p.part_name }
  }
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'copy'
}
function onDragEnd() { drag.value = null; clearSel() }

onMounted(() => nextTick(() => searchInput.value?.focus()))
</script>

<style scoped>
.pal { display: flex; flex-direction: column; height: 100%; border: 1px solid #e5e7eb; border-radius: 12px; background: #fff; overflow: hidden; }
.pal-head { padding: 10px; border-bottom: 1px solid #eef1f5; display: flex; flex-direction: column; gap: 8px; }
.pal-search { position: relative; }
.pal-search input { width: 100%; padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 13px; }
.pal-search input:focus { outline: none; border-color: #7c3aed; box-shadow: 0 0 0 2px #ede9fe; }
.pal-spin { position: absolute; right: 10px; top: 8px; color: #9ca3af; }
.pal-headrow { display: flex; align-items: center; justify-content: space-between; }
.pal-filter { font-size: 12px; color: #6b7280; display: flex; align-items: center; gap: 5px; cursor: pointer; }
.pal-count-total { font-size: 11px; color: #9ca3af; }
.pal-selbar { display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; background: #f5f3ff; border-bottom: 1px solid #e9e5fb; font-size: 12px; color: #6d28d9; }
.pal-selbar button { background: none; border: none; color: #6d28d9; cursor: pointer; text-decoration: underline; font-size: 12px; }
.pal-body { flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 6px; }
.pal-empty { text-align: center; color: #9ca3af; padding: 20px 8px; font-size: 12.5px; }
.pal-empty-t { margin-bottom: 8px; }
.pal-note { text-align: center; color: #9ca3af; padding: 4px 8px 2px; font-size: 11.5px; }
.pal-create-row { display: flex; align-items: center; gap: 8px; width: 100%; text-align: left; padding: 9px 10px; border: 1px dashed #c4b5fd; border-radius: 9px; background: #faf9ff; color: #6d28d9; font-size: 12.5px; font-weight: 600; cursor: pointer; }
.pal-create-row:hover { background: #f5f3ff; border-color: #a78bfa; }
.pal-create-row:disabled { opacity: 0.6; cursor: default; }
.pal-create-ic { display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: #7c3aed; color: #fff; font-size: 12px; flex-shrink: 0; }
.pal-card { display: flex; align-items: center; gap: 8px; padding: 8px 9px; border: 1px solid #e5e7eb; border-radius: 9px; cursor: grab; background: #fff; }
.pal-card:hover { border-color: #c4b5fd; background: #faf9ff; }
.pal-card:active { cursor: grabbing; }
.pal-just { border-color: #7c3aed; box-shadow: 0 0 0 2px #ede9fe; }
.pal-sel { border-color: #7c3aed; background: #f5f3ff; }
.pal-chk { width: 14px; height: 14px; accent-color: #7c3aed; cursor: pointer; }
.pal-grip { color: #cbd5e1; font-size: 11px; user-select: none; }
.pal-info { flex: 1; min-width: 0; }
.pal-num { font-family: ui-monospace, Consolas, monospace; font-size: 12px; color: #111827; font-weight: 600; display: flex; align-items: center; gap: 6px; }
.pal-unc { background: #fdeede; color: #b45309; font-size: 10px; font-weight: 700; border-radius: 5px; padding: 0 5px; }
.pal-name { font-size: 12px; color: #4b5563; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pal-count { flex-shrink: 0; font-size: 10.5px; font-weight: 700; color: #6d28d9; background: #f5f3ff; border-radius: 999px; padding: 2px 8px; }
.pal-count-0 { color: #b6bcc7; background: #f4f5f7; }
.pal-more { margin-top: 4px; padding: 8px; border: 1px dashed #d1d5db; border-radius: 8px; background: #fff; color: #6b7280; font-size: 12px; cursor: pointer; }
.pal-more:hover { background: #f9fafb; }
</style>
