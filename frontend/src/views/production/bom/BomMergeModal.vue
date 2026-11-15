<template>
  <Teleport to="body">
    <div class="mm" @click.self="$emit('close')">
      <div class="mm-box">
        <div class="mm-head"><span>🔀 부품 병합</span><button @click="$emit('close')">✕</button></div>
        <div class="mm-src">
          <span class="mm-lab">병합 대상(없어질 부품)</span>
          <div class="mm-srcname">{{ sourceLabel }}</div>
        </div>
        <div class="mm-arrow">▼ 아래 부품으로 합칩니다(BOM 연결 이관) ▼</div>
        <div class="mm-search">
          <input v-model="q" placeholder="남길 부품(타깃) 품번/품명 검색" @input="debouncedSearch" />
        </div>
        <div class="mm-list">
          <div v-if="loading" class="mm-empty">검색 중…</div>
          <div v-else-if="results.length === 0" class="mm-empty">검색 결과 없음</div>
          <button v-for="r in results" :key="r.id" class="mm-item" :class="{ sel: target?.id === r.id }"
            :disabled="r.id === sourcePartId" @click="target = r">
            <span class="mm-num">{{ r.part_number_display || r.part_number }}</span>
            <span class="mm-nm">{{ r.part_name }}</span>
            <span v-if="r.id === sourcePartId" class="mm-self">자기 자신</span>
          </button>
        </div>
        <div class="mm-warn" v-if="target">
          ⚠ <b>{{ sourceLabel }}</b> 의 BOM 연결이 <b>{{ target.part_number_display || target.part_number }}</b> 로 이관되고,
          원본은 비활성화됩니다. (되돌리기 어려움)
        </div>
        <div class="mm-foot">
          <button class="mm-btn" @click="$emit('close')">취소</button>
          <button class="mm-btn mm-btn-danger" :disabled="!target || saving" @click="submit">{{ saving ? '병합 중…' : '병합' }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { partApi, type PartListItem } from '@/api/parts'

const props = defineProps<{ sourcePartId: number; sourceLabel: string }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'merged'): void }>()

const q = ref('')
const results = ref<PartListItem[]>([])
const target = ref<PartListItem | null>(null)
const loading = ref(false)
const saving = ref(false)
let timer: any = null

async function search() {
  if (!q.value.trim()) { results.value = []; return }
  loading.value = true
  try { results.value = (await partApi.getAll({ keyword: q.value.trim(), limit: 20 })).data.items }
  catch { results.value = [] }
  finally { loading.value = false }
}
function debouncedSearch() { clearTimeout(timer); timer = setTimeout(search, 300) }

async function submit() {
  if (!target.value) return
  if (!confirm(`'${props.sourceLabel}' → '${target.value.part_number_display || target.value.part_number}' 로 병합합니다. 진행할까요?`)) return
  saving.value = true
  try { await partApi.merge(props.sourcePartId, target.value.id); emit('merged') }
  catch (e: any) { alert(e?.response?.data?.detail || '병합 실패') }
  finally { saving.value = false }
}
</script>

<style scoped>
.mm { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 76; display: flex; align-items: center; justify-content: center; padding: 20px; }
.mm-box { background: #fff; border-radius: 12px; width: 100%; max-width: 500px; padding: 18px; }
.mm-head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; }
.mm-head button { border: none; background: none; cursor: pointer; font-size: 16px; color: #6b7280; }
.mm-src { margin-top: 12px; background: #fbe7e7; border: 1px solid #f3c6c6; border-radius: 8px; padding: 9px 12px; }
.mm-lab { font-size: 11px; color: #b91c1c; font-weight: 700; }
.mm-srcname { font-family: ui-monospace, Consolas, monospace; font-size: 13px; color: #1f2937; }
.mm-arrow { text-align: center; color: #9ca3af; font-size: 11.5px; margin: 8px 0; }
.mm-search input { width: 100%; border: 1px solid #d1d5db; border-radius: 8px; padding: 8px 10px; font-size: 13px; }
.mm-list { margin-top: 8px; max-height: 220px; overflow: auto; border: 1px solid #eef1f5; border-radius: 8px; }
.mm-empty { text-align: center; color: #9ca3af; padding: 16px; font-size: 12.5px; }
.mm-item { display: flex; align-items: center; gap: 8px; width: 100%; text-align: left; border: none; border-bottom: 1px solid #f3f4f6; background: #fff; padding: 8px 10px; cursor: pointer; }
.mm-item:hover { background: #f7f9fc; } .mm-item.sel { background: #e7f0ff; } .mm-item:disabled { opacity: .5; cursor: not-allowed; }
.mm-num { font-family: ui-monospace, Consolas, monospace; font-size: 12px; font-weight: 600; color: #111827; }
.mm-nm { color: #374151; font-size: 12.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mm-self { margin-left: auto; font-size: 10px; color: #9ca3af; }
.mm-warn { margin-top: 10px; font-size: 12px; color: #92400e; background: #fef3c7; border-radius: 8px; padding: 8px 11px; }
.mm-foot { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
.mm-btn { border: 1px solid #d1d5db; border-radius: 8px; padding: 7px 14px; font-size: 13px; background: #fff; cursor: pointer; }
.mm-btn-danger { border-color: #dc2626; background: #dc2626; color: #fff; }
.mm-btn-danger:disabled { opacity: .5; cursor: not-allowed; }
</style>
