<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
      <!-- 헤더 -->
      <div class="px-6 py-4 border-b flex justify-between items-center shrink-0">
        <div>
          <h2 class="text-lg font-bold text-gray-800">📦 {{ editMode ? '패킹 정보 수정' : '출고 처리' }} — Packing List</h2>
          <p class="text-xs text-gray-500 mt-0.5">
            <template v-if="editMode">
              {{ requestNumber }} · 실제 포장이 바뀐 경우 여기서 정정합니다. 출고 상태·출고일시는 그대로 유지됩니다.
            </template>
            <template v-else>
              {{ requestNumber }} · 어떤 박스로 몇 개, 무게·치수를 입력하면 영업 CI 발행에 그대로 반영됩니다.
            </template>
          </p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
      </div>

      <!-- 본문 -->
      <div class="flex-1 overflow-y-auto min-h-0 p-6">
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="text-xs text-gray-500 border-b">
                <th class="px-2 py-2 text-left w-8">#</th>
                <th class="px-2 py-2 text-left min-w-[140px]">박스 종류</th>
                <th class="px-2 py-2 text-center w-16">개수</th>
                <th class="px-2 py-2 text-center w-20">Gross(kg)</th>
                <th class="px-2 py-2 text-center w-20">Net(kg)</th>
                <th class="px-2 py-2 text-center w-16">L(cm)</th>
                <th class="px-2 py-2 text-center w-16">W(cm)</th>
                <th class="px-2 py-2 text-center w-16">H(cm)</th>
                <th class="px-2 py-2 text-left min-w-[120px]">내용물/비고</th>
                <th class="px-2 py-2 w-8"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(box, i) in boxes" :key="i" class="border-b">
                <td class="px-2 py-1.5 text-gray-400">{{ i + 1 }}</td>
                <td class="px-2 py-1.5">
                  <input v-model="box.box_type" list="pkgBoxTypes" @change="onBoxTypeSelect(box)"
                    type="text" placeholder="박스 선택 또는 직접 입력"
                    class="w-full border rounded px-2 py-1 text-sm" />
                </td>
                <td class="px-2 py-1.5">
                  <input v-model.number="box.quantity" type="number" min="1"
                    class="w-full border rounded px-2 py-1 text-sm text-center" />
                </td>
                <td class="px-2 py-1.5">
                  <input v-model.number="box.gross_weight" type="number" step="0.01" min="0"
                    class="w-full border rounded px-2 py-1 text-sm text-center" />
                </td>
                <td class="px-2 py-1.5">
                  <input v-model.number="box.net_weight" type="number" step="0.01" min="0"
                    class="w-full border rounded px-2 py-1 text-sm text-center" />
                </td>
                <td class="px-2 py-1.5">
                  <input v-model.number="box.length" type="number" step="0.1" min="0"
                    class="w-full border rounded px-2 py-1 text-sm text-center" />
                </td>
                <td class="px-2 py-1.5">
                  <input v-model.number="box.width" type="number" step="0.1" min="0"
                    class="w-full border rounded px-2 py-1 text-sm text-center" />
                </td>
                <td class="px-2 py-1.5">
                  <input v-model.number="box.height" type="number" step="0.1" min="0"
                    class="w-full border rounded px-2 py-1 text-sm text-center" />
                </td>
                <td class="px-2 py-1.5">
                  <input v-model="box.remarks" type="text" placeholder="예: 품번/수량"
                    class="w-full border rounded px-2 py-1 text-sm" />
                </td>
                <td class="px-2 py-1.5 text-center">
                  <button @click="removeBox(i)" class="text-red-400 hover:text-red-600" title="삭제">✕</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 박스 프리셋(선택 시 L·W·H 자동입력, 목록 외 박스는 직접 입력) -->
        <datalist id="pkgBoxTypes">
          <option v-for="p in BOX_PRESETS" :key="p.name" :value="p.name">{{ p.l }}×{{ p.w }}×{{ p.h }} cm</option>
        </datalist>

        <div class="mt-3 flex items-center gap-3">
          <button @click="addBox" type="button"
            class="px-3 py-1.5 text-sm text-blue-600 border border-blue-200 rounded hover:bg-blue-50">
            + 박스 추가
          </button>
          <span class="text-xs text-gray-400">박스 종류를 선택하면 가로·세로·높이가 자동 입력됩니다. 무게는 직접 입력하세요.</span>
        </div>

        <!-- 합계 미리보기 -->
        <div class="mt-4 flex flex-wrap gap-4 text-sm bg-gray-50 rounded-lg px-4 py-2">
          <span class="text-gray-600">총 박스: <strong class="text-gray-900">{{ totalBoxes }}</strong></span>
          <span class="text-gray-600">총 Gross: <strong class="text-gray-900">{{ totalGross.toFixed(1) }} kg</strong></span>
          <span class="text-gray-600">총 Net: <strong class="text-gray-900">{{ totalNet.toFixed(1) }} kg</strong></span>
        </div>

        <!-- 출고 포장사진 (출고 처리 중에도 바로 업로드) -->
        <div v-if="requestId" class="mt-5 border-t pt-4">
          <h3 class="text-sm font-medium text-gray-700 mb-2">📷 출고 포장사진</h3>
          <PackingPhotos :request-id="requestId" />
        </div>

        <!-- 측정자료 (손실값측정 엑셀 등) -->
        <div v-if="requestId" class="mt-5 border-t pt-4">
          <h3 class="text-sm font-medium text-gray-700 mb-2">📊 측정자료 <span class="text-xs text-gray-400 font-normal">(손실값측정 엑셀 등)</span></h3>
          <MeasurementFiles :request-id="requestId" />
        </div>
      </div>

      <!-- 푸터 -->
      <div class="px-6 py-4 border-t flex justify-between items-center shrink-0 bg-gray-50">
        <span class="text-xs text-gray-400">
          {{ editMode
            ? '상태 변경 없이 패킹 정보만 갱신합니다. 이미 발행된 CI에는 자동 반영되지 않습니다.'
            : "출고 완료 시 상태가 '생산 출고'로 전환됩니다." }}
        </span>
        <div class="flex gap-2">
          <button @click="$emit('close')" class="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-100">취소</button>
          <button @click="confirm" :disabled="submitting"
            class="px-4 py-2 text-sm text-white rounded-lg disabled:opacity-50"
            :class="editMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-green-600 hover:bg-green-700'">
            {{ submitting ? '처리 중…' : (editMode ? '💾 패킹 정보 저장' : '📦 출고 완료 처리') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { PackingBox } from '@/api/productionRequest'
import { BOX_PRESETS, findBoxPreset } from '@/constants/packingBoxes'
import PackingPhotos from '@/views/production/components/PackingPhotos.vue'
import MeasurementFiles from '@/views/production/components/MeasurementFiles.vue'

interface BoxRow {
  box_type: string
  quantity: number | null
  gross_weight: number | null
  net_weight: number | null
  length: number | null
  width: number | null
  height: number | null
  remarks: string
}

const props = defineProps<{
  requestId?: number | null
  requestNumber: string
  initial?: PackingBox[] | null
  /** 출고 후 패킹 정보 정정 모드 — 상태 전이 없이 packing list 만 저장 */
  editMode?: boolean
}>()

const emit = defineEmits<{ (e: 'close'): void; (e: 'confirm', packingList: PackingBox[]): void }>()

const submitting = ref(false)

// 박스 종류 선택 시 프리셋이면 L·W·H 자동입력(무게는 수기 유지). 커스텀은 그대로 둠.
function onBoxTypeSelect(box: BoxRow) {
  const p = findBoxPreset(box.box_type)
  if (p) { box.length = p.l; box.width = p.w; box.height = p.h }
}

function emptyRow(): BoxRow {
  return { box_type: '', quantity: 1, gross_weight: null, net_weight: null, length: null, width: null, height: null, remarks: '' }
}

const boxes = ref<BoxRow[]>(
  props.initial && props.initial.length
    ? props.initial.map(b => ({
        box_type: b.box_type || '',
        quantity: b.quantity ?? 1,
        gross_weight: b.gross_weight ?? null,
        net_weight: b.net_weight ?? null,
        length: b.length ?? null,
        width: b.width ?? null,
        height: b.height ?? null,
        remarks: b.remarks || '',
      }))
    : [emptyRow()]
)

function addBox() { boxes.value.push(emptyRow()) }
function removeBox(i: number) {
  boxes.value.splice(i, 1)
  if (boxes.value.length === 0) boxes.value.push(emptyRow())
}

// 값이 하나라도 있는 행만 유효
function isFilled(b: BoxRow): boolean {
  return !!(b.box_type || b.gross_weight || b.net_weight || b.length || b.width || b.height || b.remarks)
}

const filledBoxes = computed(() => boxes.value.filter(isFilled))
const totalBoxes = computed(() => filledBoxes.value.reduce((s, b) => s + (Number(b.quantity) || 0), 0))
const totalGross = computed(() => filledBoxes.value.reduce((s, b) => s + (Number(b.gross_weight) || 0) * (Number(b.quantity) || 0), 0))
const totalNet = computed(() => filledBoxes.value.reduce((s, b) => s + (Number(b.net_weight) || 0) * (Number(b.quantity) || 0), 0))

function confirm() {
  const list: PackingBox[] = filledBoxes.value.map(b => ({
    box_type: b.box_type?.trim() || null,
    quantity: Number(b.quantity) || 1,
    gross_weight: b.gross_weight ?? null,
    net_weight: b.net_weight ?? null,
    length: b.length ?? null,
    width: b.width ?? null,
    height: b.height ?? null,
    remarks: b.remarks?.trim() || null,
  }))
  if (list.length === 0 && !confirm2()) return
  submitting.value = true
  emit('confirm', list)
}

// 포장 정보 없이 출고 확인 / 정정 모드에서는 기존 패킹 정보 삭제 확인
function confirm2(): boolean {
  return window.confirm(
    props.editMode
      ? '입력된 박스가 없습니다. 기존 패킹 정보를 모두 지울까요?'
      : '포장(Packing List) 정보 없이 출고 완료 처리할까요?',
  )
}
</script>
