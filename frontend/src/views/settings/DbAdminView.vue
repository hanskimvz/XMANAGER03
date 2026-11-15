<template>
  <div class="db-view">
    <div class="page-header">
      <h1>DB관리자</h1>
      <p class="subtitle">DB와 테이블을 선택해 레코드 원본(raw data)을 조회합니다 · 읽기 전용</p>
    </div>

    <!-- DB 선택 -->
    <div class="db-bar">
      <label for="db-select">데이터베이스</label>
      <select id="db-select" v-model="selectedDb" @change="onDbChange">
        <option value="" disabled>DB 선택</option>
        <option v-for="d in databases" :key="d.name" :value="d.name">
          {{ d.name }} ({{ d.size_display }}){{ d.is_current ? ' · 현재 연결' : '' }}
        </option>
      </select>
      <span v-if="selectedTable" class="current-target">
        {{ selectedDb }} › {{ tableLabel(selectedTable) }}
      </span>
    </div>

    <div class="layout">
      <!-- 테이블 목록 -->
      <aside class="table-panel">
        <div class="panel-title">
          테이블 <span class="count">({{ filteredTables.length }})</span>
        </div>
        <input
          v-model="tableSearch"
          class="table-search"
          type="search"
          placeholder="테이블 검색"
          :disabled="!selectedDb"
        />
        <div v-if="tablesLoading" class="panel-msg">불러오는 중...</div>
        <div v-else-if="!selectedDb" class="panel-msg">DB를 선택하세요.</div>
        <div v-else-if="filteredTables.length === 0" class="panel-msg">테이블이 없습니다.</div>
        <ul v-else class="table-list">
          <li
            v-for="t in filteredTables"
            :key="t.schema_name + '.' + t.name"
            :class="{ active: isSelected(t) }"
            @click="selectTable(t)"
          >
            <span class="t-name" :title="tableLabel(t)">{{ tableLabel(t) }}</span>
            <span v-if="t.kind !== 'table'" class="t-kind">{{ t.kind === 'view' ? '뷰' : 'M뷰' }}</span>
            <span v-else-if="t.estimated_rows !== null" class="t-rows">~{{ t.estimated_rows.toLocaleString() }}</span>
          </li>
        </ul>
      </aside>

      <!-- 조회 영역 -->
      <section class="data-panel">
        <div v-if="!selectedTable" class="empty-state">
          왼쪽에서 테이블을 선택하면 레코드가 표시됩니다.
        </div>

        <template v-else>
          <!-- 조회 조건 -->
          <form class="query-box" @submit.prevent="runQuery(0)">
            <div class="query-row">
              <label class="field">
                <span>제한</span>
                <input v-model.number="limit" type="number" min="1" :max="MAX_LIMIT" class="limit-input" />
              </label>
              <label class="field">
                <span>정렬</span>
                <select v-model="sortColumn">
                  <option value="">기본(PK)</option>
                  <option v-for="c in columns" :key="c.name" :value="c.name">{{ c.name }}</option>
                </select>
              </label>
              <label class="field">
                <span>방향</span>
                <select v-model="sortDirection" :disabled="!sortColumn">
                  <option value="asc">오름차순</option>
                  <option value="desc">내림차순</option>
                </select>
              </label>
              <div class="query-actions">
                <button type="button" class="btn btn-light" @click="addFilter">+ 필터</button>
                <button type="button" class="btn btn-light" @click="resetQuery">초기화</button>
                <button type="submit" class="btn btn-primary" :disabled="rowsLoading">조회</button>
              </div>
            </div>

            <div v-for="(f, i) in filters" :key="f.id" class="filter-row">
              <span class="filter-tag">필터 {{ i + 1 }}</span>
              <select v-model="f.column">
                <option v-for="c in columns" :key="c.name" :value="c.name">{{ c.name }}</option>
              </select>
              <select v-model="f.op">
                <option v-for="o in FILTER_OPS" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
              <input
                v-if="!isNullOp(f.op)"
                v-model="f.value"
                type="text"
                class="filter-value"
                placeholder="값"
              />
              <button type="button" class="btn-remove" title="필터 삭제" @click="removeFilter(i)">&times;</button>
            </div>
          </form>

          <!-- 결과 요약 / 페이지 이동 -->
          <div class="result-bar">
            <span v-if="rowsLoading">조회 중...</span>
            <span v-else-if="errorMsg" class="error-text">{{ errorMsg }}</span>
            <span v-else>
              전체 <strong>{{ total.toLocaleString() }}</strong>건
              <template v-if="rows.length"> 중 {{ (offset + 1).toLocaleString() }}–{{ (offset + rows.length).toLocaleString() }}</template>
            </span>
            <div class="pager">
              <button class="btn btn-light btn-sm" :disabled="rowsLoading || offset === 0" @click="runQuery(offset - appliedLimit)">이전</button>
              <button class="btn btn-light btn-sm" :disabled="rowsLoading || offset + rows.length >= total" @click="runQuery(offset + appliedLimit)">다음</button>
            </div>
          </div>

          <!-- 데이터 -->
          <div class="grid-wrap" :class="{ dim: rowsLoading }">
            <table v-if="columns.length" class="grid">
              <thead>
                <tr>
                  <th class="row-no">#</th>
                  <th v-for="c in columns" :key="c.name" @click="toggleSort(c.name)" :title="'클릭: 정렬'">
                    <div class="th-name">
                      <span v-if="c.is_pk" class="pk" title="Primary Key">PK</span>
                      {{ c.name }}
                      <span v-if="appliedSort?.column === c.name" class="sort-mark">{{ appliedSort.direction === 'asc' ? '▲' : '▼' }}</span>
                    </div>
                    <div class="th-type">{{ c.type }}</div>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, ri) in rows" :key="ri" @click="detailRow = row">
                  <td class="row-no">{{ offset + ri + 1 }}</td>
                  <td v-for="(v, ci) in row" :key="ci" :class="{ 'is-null': v === null }" :title="cellText(v)">{{ cellText(v) }}</td>
                </tr>
                <tr v-if="!rows.length && !rowsLoading">
                  <td :colspan="columns.length + 1" class="no-rows">{{ errorMsg ? '조회에 실패했습니다.' : '조건에 맞는 레코드가 없습니다.' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="hint">행을 클릭하면 전체 값을 볼 수 있습니다. 컬럼 제목을 클릭하면 해당 컬럼으로 정렬합니다.</p>
        </template>
      </section>
    </div>

    <!-- 레코드 상세 -->
    <div v-if="detailRow" class="modal-overlay" @click.self="detailRow = null">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ selectedTable ? tableLabel(selectedTable) : '' }} 레코드</h3>
          <button class="close-btn" @click="detailRow = null">&times;</button>
        </div>
        <div class="modal-body">
          <div v-for="(c, ci) in columns" :key="c.name" class="detail-item">
            <div class="detail-key">{{ c.name }} <span class="th-type">{{ c.type }}</span></div>
            <pre class="detail-val" :class="{ 'is-null': detailRow[ci] === null }">{{ cellText(detailRow[ci], true) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  getDatabases,
  getTables,
  queryRows,
  type ColumnInfo,
  type DatabaseInfo,
  type FilterOp,
  type SortSpec,
  type TableInfo,
} from '@/api/dbAdmin'

const MAX_LIMIT = 1000
const DEFAULT_LIMIT = 100

const FILTER_OPS: { value: FilterOp; label: string }[] = [
  { value: 'contains', label: '포함' },
  { value: 'not_contains', label: '포함 안 함' },
  { value: 'starts', label: '시작' },
  { value: 'ends', label: '끝' },
  { value: 'eq', label: '=' },
  { value: 'ne', label: '≠' },
  { value: 'gt', label: '>' },
  { value: 'gte', label: '≥' },
  { value: 'lt', label: '<' },
  { value: 'lte', label: '≤' },
  { value: 'is_null', label: 'NULL' },
  { value: 'not_null', label: 'NULL 아님' },
]

interface FilterRow {
  id: number
  column: string
  op: FilterOp
  value: string
}

// DB / 테이블
const databases = ref<DatabaseInfo[]>([])
const selectedDb = ref('')
const tables = ref<TableInfo[]>([])
const tablesLoading = ref(false)
const tableSearch = ref('')
const selectedTable = ref<TableInfo | null>(null)

// 조회 조건
const limit = ref(DEFAULT_LIMIT)
const sortColumn = ref('')
const sortDirection = ref<'asc' | 'desc'>('asc')
const filters = ref<FilterRow[]>([])
let filterSeq = 0

// 결과
const columns = ref<ColumnInfo[]>([])
const rows = ref<unknown[][]>([])
const total = ref(0)
const offset = ref(0)
const appliedLimit = ref(DEFAULT_LIMIT)
const appliedSort = ref<SortSpec | null>(null)
const rowsLoading = ref(false)
const errorMsg = ref('')
const detailRow = ref<unknown[] | null>(null)
let querySeq = 0 // 늦게 도착한 이전 응답 무시용

const filteredTables = computed(() => {
  const q = tableSearch.value.trim().toLowerCase()
  return q ? tables.value.filter((t) => tableLabel(t).toLowerCase().includes(q)) : tables.value
})

function tableLabel(t: TableInfo): string {
  return t.schema_name === 'public' ? t.name : `${t.schema_name}.${t.name}`
}

function isSelected(t: TableInfo): boolean {
  return selectedTable.value?.schema_name === t.schema_name && selectedTable.value?.name === t.name
}

function isNullOp(op: FilterOp): boolean {
  return op === 'is_null' || op === 'not_null'
}

function apiError(e: unknown, fallback: string): string {
  const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

// 셀 표시: 원본 그대로(객체/배열은 JSON). full=true 면 상세 보기용으로 들여쓰기.
function cellText(v: unknown, full = false): string {
  if (v === null || v === undefined) return 'NULL'
  if (typeof v === 'object') return JSON.stringify(v, null, full ? 2 : undefined)
  return String(v)
}

function clearResult() {
  querySeq++ // 진행 중인 조회 응답 무시
  columns.value = []
  rows.value = []
  total.value = 0
  offset.value = 0
  errorMsg.value = ''
  rowsLoading.value = false
  detailRow.value = null
}

function resetConditions() {
  limit.value = DEFAULT_LIMIT
  sortColumn.value = ''
  sortDirection.value = 'asc'
  filters.value = []
}

async function onDbChange() {
  selectedTable.value = null
  tables.value = []
  tableSearch.value = ''
  clearResult()
  resetConditions()
  const db = selectedDb.value
  if (!db) return
  tablesLoading.value = true
  try {
    const list = await getTables(db)
    if (db === selectedDb.value) tables.value = list
  } catch (e) {
    if (db === selectedDb.value) alert(apiError(e, '테이블 목록을 불러오지 못했습니다.'))
  } finally {
    if (db === selectedDb.value) tablesLoading.value = false
  }
}

function selectTable(t: TableInfo) {
  selectedTable.value = t
  clearResult()
  resetConditions()
  runQuery(0)
}

function addFilter() {
  filters.value.push({ id: ++filterSeq, column: columns.value[0]?.name ?? '', op: 'contains', value: '' })
}

function removeFilter(i: number) {
  filters.value.splice(i, 1)
}

function resetQuery() {
  resetConditions()
  runQuery(0)
}

// 컬럼 제목 클릭: 오름차순 → 내림차순 → 기본(PK)
function toggleSort(col: string) {
  if (sortColumn.value !== col) {
    sortColumn.value = col
    sortDirection.value = 'asc'
  } else if (sortDirection.value === 'asc') {
    sortDirection.value = 'desc'
  } else {
    sortColumn.value = ''
    sortDirection.value = 'asc'
  }
  runQuery(0)
}

async function runQuery(newOffset: number) {
  const t = selectedTable.value
  if (!t || !selectedDb.value) return

  const lim = Math.min(MAX_LIMIT, Math.max(1, Math.floor(Number(limit.value)) || DEFAULT_LIMIT))
  limit.value = lim
  const sort: SortSpec[] = sortColumn.value ? [{ column: sortColumn.value, direction: sortDirection.value }] : []

  const seq = ++querySeq
  rowsLoading.value = true
  errorMsg.value = ''
  try {
    const res = await queryRows({
      database: selectedDb.value,
      schema_name: t.schema_name,
      table: t.name,
      limit: lim,
      offset: Math.max(0, newOffset),
      sort,
      filters: filters.value
        .filter((f) => f.column)
        .map((f) => ({ column: f.column, op: f.op, value: isNullOp(f.op) ? null : f.value })),
    })
    if (seq !== querySeq) return
    columns.value = res.columns
    rows.value = res.rows
    total.value = res.total
    offset.value = res.offset
    appliedLimit.value = res.limit
    appliedSort.value = sort[0] ?? null
  } catch (e) {
    if (seq !== querySeq) return
    rows.value = []
    total.value = 0
    errorMsg.value = apiError(e, '레코드를 조회하지 못했습니다.')
  } finally {
    if (seq === querySeq) rowsLoading.value = false
  }
}

onMounted(async () => {
  try {
    databases.value = await getDatabases()
    const current = databases.value.find((d) => d.is_current)
    if (current) {
      selectedDb.value = current.name
      await onDbChange()
    }
  } catch (e) {
    alert(apiError(e, 'DB 목록을 불러오지 못했습니다.'))
  }
})
</script>

<style scoped>
.db-view {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
}

.subtitle {
  margin: 5px 0 0;
  color: #666;
}

select,
input[type='text'],
input[type='number'],
input[type='search'] {
  padding: 7px 10px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 13px;
  background: white;
  min-width: 0;
}

/* DB 선택 */
.db-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 15px;
}

.db-bar label {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.db-bar select {
  min-width: 240px;
}

.current-target {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  background: #e3f2fd;
  color: #1565c0;
  padding: 4px 10px;
  border-radius: 6px;
}

.layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 15px;
  align-items: start;
}

/* 테이블 목록 */
.table-panel,
.data-panel {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 15px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
}

.panel-title .count {
  font-weight: normal;
  color: #666;
}

.table-search {
  width: 100%;
  box-sizing: border-box;
  margin-bottom: 10px;
}

.panel-msg {
  color: #666;
  font-size: 13px;
  padding: 10px 0;
}

.table-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: calc(100vh - 320px);
  min-height: 160px;
  overflow-y: auto;
}

.table-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.table-list li:hover {
  background: #f5f5f5;
}

.table-list li.active {
  background: #e3f2fd;
  color: #1565c0;
  font-weight: 600;
}

.t-name {
  font-family: 'Consolas', 'Monaco', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.t-rows,
.t-kind {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: normal;
  color: #888;
}

.t-kind {
  background: #f3e5f5;
  color: #7b1fa2;
  padding: 1px 6px;
  border-radius: 4px;
}

/* 조회 조건 */
.query-box {
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  background: #fafafa;
}

.query-row {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #666;
}

.limit-input {
  width: 90px;
}

.query-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.filter-tag {
  font-size: 12px;
  color: #666;
  width: 48px;
}

.filter-value {
  flex: 1;
  min-width: 140px;
}

.btn-remove {
  background: none;
  border: none;
  font-size: 20px;
  line-height: 1;
  color: #999;
  cursor: pointer;
  padding: 2px 6px;
}

.btn-remove:hover {
  color: #d32f2f;
}

/* 버튼 */
.btn {
  padding: 8px 16px;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #1976d2;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1565c0;
}

.btn-light {
  background: white;
  border-color: #ccc;
  color: #333;
}

.btn-light:hover:not(:disabled) {
  background: #f5f5f5;
}

.btn-sm {
  padding: 5px 12px;
  font-size: 12px;
}

/* 결과 */
.result-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 13px;
  color: #333;
  margin-bottom: 8px;
}

.error-text {
  color: #d32f2f;
}

.pager {
  display: flex;
  gap: 6px;
}

.grid-wrap {
  overflow: auto;
  max-height: calc(100vh - 380px);
  min-height: 200px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
}

.grid-wrap.dim {
  opacity: 0.6;
}

.grid {
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
  font-family: 'Consolas', 'Monaco', monospace;
}

.grid th,
.grid td {
  padding: 6px 10px;
  border-bottom: 1px solid #eee;
  border-right: 1px solid #f0f0f0;
  text-align: left;
  white-space: nowrap;
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.grid th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f5f5f5;
  cursor: pointer;
  user-select: none;
}

.grid th:hover {
  background: #eceff1;
}

.grid tbody tr {
  cursor: pointer;
}

.grid tbody tr:hover td {
  background: #f5faff;
}

.row-no {
  color: #999;
  text-align: right !important;
  background: #fafafa;
}

.grid th.row-no {
  cursor: default;
}

.th-name {
  font-weight: 600;
  color: #333;
}

.th-type {
  font-size: 10px;
  font-weight: normal;
  color: #999;
}

.pk {
  font-size: 9px;
  background: #fff3e0;
  color: #e65100;
  padding: 1px 4px;
  border-radius: 3px;
  margin-right: 3px;
}

.sort-mark {
  color: #1976d2;
  font-size: 10px;
}

.is-null {
  color: #bbb;
  font-style: italic;
}

.no-rows {
  text-align: center !important;
  color: #666;
  padding: 30px !important;
  font-family: inherit;
}

.hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: #888;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

/* 레코드 상세 모달 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 720px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 15px 20px;
  overflow-y: auto;
}

.detail-item {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-key {
  font-size: 12px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.detail-val {
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

@media (max-width: 1023px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .table-list {
    max-height: 220px;
  }

  .query-actions {
    margin-left: 0;
  }
}
</style>
