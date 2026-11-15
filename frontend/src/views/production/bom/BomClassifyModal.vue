<template>
  <Teleport to="body">
    <div class="cm" @click.self="$emit('close')">
      <div class="cm-box">
        <div class="cm-head">
          <span>🏷 분류/채번 — <b>{{ partLabel }}</b></span>
          <button @click="$emit('close')">✕</button>
        </div>
        <p class="cm-desc">코드·레벨을 지정하면 정식 품번이 생성됩니다. 고유 ID와 BOM 연결은 그대로 유지됩니다.</p>
        <div class="cm-grid">
          <label>대분류(제품라인) <span class="req">*</span>
            <select v-model="form.product_line_id"><option :value="undefined">선택</option>
              <option v-for="o in productLines" :key="o.id" :value="o.id">{{ o.code }} · {{ o.name_ko }}</option></select>
          </label>
          <label>소분류(품목군) <span class="req">*</span>
            <select v-model="form.part_group_id"><option :value="undefined">선택</option>
              <option v-for="o in partGroups" :key="o.id" :value="o.id">{{ o.code }} · {{ o.name_ko }}</option></select>
          </label>
          <label>품목코드 앞3자리 <span class="req">*</span>
            <input v-model="form.item_code_prefix" maxlength="3" placeholder="001" />
          </label>
          <label>레벨 <span class="req">*</span>
            <select v-model="form.level_id"><option :value="undefined">선택</option>
              <option v-for="o in levels" :key="o.id" :value="o.id">{{ o.code }} · {{ o.name_ko }}</option></select>
          </label>
          <label>재질
            <select v-model="form.material_id"><option :value="undefined">선택</option>
              <option v-for="o in materials" :key="o.id" :value="o.id">{{ o.code }} · {{ o.name_ko }}</option></select>
          </label>
          <label>후처리
            <select v-model="form.treatment_id"><option :value="undefined">선택</option>
              <option v-for="o in treatments" :key="o.id" :value="o.id">{{ o.code }} · {{ o.name_ko }}</option></select>
          </label>
        </div>
        <div class="cm-foot">
          <button class="cm-btn" @click="$emit('close')">취소</button>
          <button class="cm-btn cm-btn-p" :disabled="!canSubmit || saving" @click="submit">{{ saving ? '처리 중…' : '분류·채번' }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { partApi } from '@/api/parts'
import { productLineApi, partGroupApi, levelApi, materialApi, treatmentApi, type CodeMaster } from '@/api/codeMaster'

const props = defineProps<{ partId: number; partLabel: string }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'classified'): void }>()

const productLines = ref<CodeMaster[]>([]); const partGroups = ref<CodeMaster[]>([])
const levels = ref<CodeMaster[]>([]); const materials = ref<CodeMaster[]>([]); const treatments = ref<CodeMaster[]>([])
const saving = ref(false)
const form = ref<any>({ product_line_id: undefined, part_group_id: undefined, item_code_prefix: '', level_id: undefined, material_id: undefined, treatment_id: undefined })

const canSubmit = computed(() => form.value.product_line_id && form.value.part_group_id && (form.value.item_code_prefix || '').length === 3 && form.value.level_id)

onMounted(async () => {
  try {
    const [pl, pg, lv, mt, tr] = await Promise.all([
      productLineApi.getAll(), partGroupApi.getAll(), levelApi.getAll(), materialApi.getAll(), treatmentApi.getAll(),
    ])
    productLines.value = pl.data; partGroups.value = pg.data; levels.value = lv.data; materials.value = mt.data; treatments.value = tr.data
  } catch { /* 무시 */ }
})

async function submit() {
  if (!canSubmit.value) return
  saving.value = true
  try {
    await partApi.classify(props.partId, {
      product_line_id: form.value.product_line_id, part_group_id: form.value.part_group_id,
      item_code_prefix: form.value.item_code_prefix, level_id: form.value.level_id,
      material_id: form.value.material_id || null, treatment_id: form.value.treatment_id || null,
    })
    emit('classified')
  } catch (e: any) { alert(e?.response?.data?.detail || '분류 실패') }
  finally { saving.value = false }
}
</script>

<style scoped>
.cm { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 75; display: flex; align-items: center; justify-content: center; padding: 20px; }
.cm-box { background: #fff; border-radius: 12px; width: 100%; max-width: 520px; padding: 18px; }
.cm-head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; }
.cm-head button { border: none; background: none; cursor: pointer; font-size: 16px; color: #6b7280; }
.cm-desc { font-size: 12.5px; color: #6b7280; margin: 8px 0 14px; }
.cm-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 11px; }
.cm-grid label { font-size: 12px; color: #374151; display: flex; flex-direction: column; gap: 4px; }
.cm-grid select, .cm-grid input { border: 1px solid #d1d5db; border-radius: 7px; padding: 6px 8px; font-size: 13px; }
.req { color: #dc2626; }
.cm-foot { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.cm-btn { border: 1px solid #d1d5db; border-radius: 8px; padding: 7px 14px; font-size: 13px; background: #fff; cursor: pointer; }
.cm-btn-p { border-color: #2563eb; background: #2563eb; color: #fff; }
.cm-btn-p:disabled { opacity: .5; cursor: not-allowed; }
</style>
