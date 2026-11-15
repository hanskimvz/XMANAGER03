<template>
  <Teleport to="body">
    <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" @click.self="$emit('close')">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[92vh] flex flex-col">
        <div class="flex justify-between items-center px-6 py-4 border-b">
          <h2 class="text-lg font-bold text-gray-800">일괄 발주 <span class="text-sm font-normal text-gray-400">(선택 {{ rows.length }}건)</span></h2>
          <button class="text-gray-400 hover:text-gray-700 text-2xl leading-none" @click="$emit('close')">&times;</button>
        </div>

        <div class="p-6 space-y-4 overflow-y-auto">
          <!-- 발주 헤더 -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">공급업체 <span class="text-red-500">*</span></label>
              <SearchableSelect v-model="supplierId" :options="supplierOptions" placeholder="공급업체 검색/선택" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">발주일</label>
              <input v-model="orderDate" type="date" class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">예상 납기일</label>
              <input v-model="expectedDate" type="date" class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">통화</label>
              <input v-model="currency" type="text" class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>

          <!-- 품목 -->
          <div class="border rounded-lg overflow-x-auto">
            <table class="min-w-full text-sm">
              <thead class="bg-gray-50 text-gray-500">
                <tr>
                  <th class="px-3 py-2 text-left font-medium">품번</th>
                  <th class="px-3 py-2 text-left font-medium">품명</th>
                  <th class="px-3 py-2 text-right font-medium">재고</th>
                  <th class="px-3 py-2 text-right font-medium w-28">발주수량</th>
                  <th class="px-3 py-2 text-right font-medium w-28">단가</th>
                  <th class="px-3 py-2 text-right font-medium">금액</th>
                  <th class="px-2 py-2 w-8"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="(r, i) in rows" :key="r.part_id">
                  <td class="px-3 py-2 font-mono">{{ r.part_number }}</td>
                  <td class="px-3 py-2 text-gray-700 max-w-[160px] truncate">{{ r.part_name }}</td>
                  <td class="px-3 py-2 text-right text-gray-400">{{ formatNum(r.on_hand) }}</td>
                  <td class="px-3 py-2 text-right">
                    <input v-model.number="r.qty" type="number" min="1" step="1"
                      class="w-24 px-2 py-1 border border-gray-300 rounded text-right text-sm focus:ring-2 focus:ring-blue-500" />
                  </td>
                  <td class="px-3 py-2 text-right">
                    <input v-model.number="r.price" type="number" min="0" step="0.01"
                      class="w-24 px-2 py-1 border border-gray-300 rounded text-right text-sm focus:ring-2 focus:ring-blue-500" />
                  </td>
                  <td class="px-3 py-2 text-right font-medium">{{ formatNum((r.qty || 0) * (r.price || 0)) }}</td>
                  <td class="px-2 py-2 text-center">
                    <button class="text-red-400 hover:text-red-600" title="제외" @click="rows.splice(i, 1)">✕</button>
                  </td>
                </tr>
                <tr v-if="rows.length === 0">
                  <td colspan="7" class="px-3 py-6 text-center text-gray-400">품목이 없습니다.</td>
                </tr>
              </tbody>
              <tfoot v-if="rows.length" class="bg-gray-50 font-semibold">
                <tr>
                  <td colspan="5" class="px-3 py-2 text-right">합계</td>
                  <td class="px-3 py-2 text-right">{{ currency }} {{ formatNum(totalAmount) }}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>

          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">비고</label>
            <textarea v-model="remarks" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500"
              placeholder="발주 비고 (선택)"></textarea>
          </div>
          <p class="text-xs text-gray-400">* 발주서는 <b>임시저장(DRAFT)</b>으로 생성됩니다. 한 발주서는 공급업체 1곳 기준입니다 — 여러 업체 품목은 나눠서 발주하세요.</p>
        </div>

        <div class="px-6 py-3 border-t flex justify-end gap-2">
          <button class="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50" @click="$emit('close')">취소</button>
          <button class="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            :disabled="saving || !supplierId || rows.length === 0" @click="submit">
            {{ saving ? '생성 중...' : '발주서 생성' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import SearchableSelect from '@/components/SearchableSelect.vue'
import { partnerApi } from '@/api/partner'
import { purchaseOrderApi } from '@/api/purchaseOrder'
import { useToast } from '@/composables/useToast'

interface SelectedInvItem {
  part_id: number
  part_number: string
  part_name: string
  on_hand: number
  reorder_point?: number
  unit_cost?: number
}

const props = defineProps<{ items: SelectedInvItem[] }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'created', poId: number): void }>()
const { showToast } = useToast()

const supplierId = ref<number | undefined>(undefined)
const supplierOptions = ref<{ id: number; code: string; name_ko: string }[]>([])
const orderDate = ref(new Date().toISOString().slice(0, 10))
const expectedDate = ref('')
const currency = ref('KRW')
const remarks = ref('')
const saving = ref(false)

const rows = ref(
  props.items.map(it => ({
    part_id: it.part_id,
    part_number: it.part_number,
    part_name: it.part_name,
    on_hand: it.on_hand,
    qty: it.reorder_point && it.reorder_point > 0 ? Math.ceil(it.reorder_point) : 1,
    price: it.unit_cost || 0,
  })),
)

const totalAmount = computed(() => rows.value.reduce((s, r) => s + (r.qty || 0) * (r.price || 0), 0))

function formatNum(n: number): string {
  return (Number(n) || 0).toLocaleString('ko-KR', { maximumFractionDigits: 2 })
}

async function loadSuppliers() {
  try {
    const res = await partnerApi.getAll({ is_supplier: true, limit: 300 })
    supplierOptions.value = (res.data.items || []).map((p: any) => ({
      id: p.id,
      code: p.partner_code || p.short_code || '',
      name_ko: p.partner_name,
    }))
  } catch { supplierOptions.value = [] }
}

async function submit() {
  if (!supplierId.value || rows.value.length === 0) return
  for (const r of rows.value) {
    if (!r.qty || r.qty <= 0) { showToast('발주수량을 확인하세요', 'error'); return }
  }
  saving.value = true
  try {
    const po = await purchaseOrderApi.create({
      supplier_id: supplierId.value,
      order_date: orderDate.value,
      expected_delivery_date: expectedDate.value || undefined,
      currency: currency.value || undefined,
      remarks: remarks.value || undefined,
      items: rows.value.map((r, idx) => ({
        part_id: r.part_id,
        ordered_quantity: r.qty,
        unit_price: r.price || 0,
        sort_order: idx,
      })),
    })
    showToast(`발주서 ${po.po_number || ''} 임시저장 생성됨`, 'success')
    emit('created', po.id)
  } catch (e: any) {
    showToast(e?.response?.data?.detail?.message || e?.response?.data?.detail || '발주서 생성에 실패했습니다', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(loadSuppliers)
</script>
