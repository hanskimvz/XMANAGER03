<template>
  <div class="print-container" ref="printContainer">
    <!-- 헤더: 결재란 포함 -->
    <div class="print-header">
      <div class="title-section">
        <h1 class="main-title">발 주 서</h1>
      </div>
      <div class="approval-box">
        <table class="approval-table">
          <thead>
            <tr>
              <th>작성</th>
              <th>검토</th>
              <th>승인</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="approval-cell"></td>
              <td class="approval-cell"></td>
              <td class="approval-cell"></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 문서 정보 -->
    <div class="doc-info-section">
      <table class="doc-info-table">
        <tbody>
          <tr>
            <th>문서번호</th>
            <td>{{ purchaseOrder?.po_number }}</td>
            <th>TEL</th>
            <td>{{ companyInfo.tel }}</td>
            <th>발주일자</th>
            <td>{{ formatDate(purchaseOrder?.order_date) }}</td>
          </tr>
          <tr>
            <th>구매담당자</th>
            <td>{{ companyInfo.purchaseManager }}</td>
            <th>FAX</th>
            <td>{{ companyInfo.fax }}</td>
            <th>발주근거</th>
            <td>{{ purchaseOrder?.remarks || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 공급업체 정보 -->
    <div class="supplier-section">
      <table class="supplier-table">
        <tbody>
          <tr>
            <th rowspan="3" class="supplier-header">공<br/>급<br/>업<br/>체</th>
            <th>상 호</th>
            <td colspan="3">{{ purchaseOrder?.supplier?.partner_name || '-' }}</td>
          </tr>
          <tr>
            <th>대표자</th>
            <td>{{ purchaseOrder?.supplier?.representative || '-' }}</td>
            <th>담당자</th>
            <td>{{ purchaseOrder?.supplier?.manager_name || '-' }}</td>
          </tr>
          <tr>
            <th>주 소</th>
            <td>{{ purchaseOrder?.supplier?.address || '-' }}</td>
            <th>TEL/FAX</th>
            <td>{{ supplierContact }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 발주 항목 테이블 -->
    <div class="items-section">
      <table class="items-table">
        <thead>
          <tr>
            <th class="col-no">NO.</th>
            <th class="col-name">품명</th>
            <th class="col-unit">단위</th>
            <th class="col-qty">수량</th>
            <th class="col-price">단가</th>
            <th class="col-amount">금액</th>
            <th class="col-remarks">비고</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in purchaseOrder?.items || []" :key="item.id">
            <td class="text-center">{{ idx + 1 }}</td>
            <td>{{ item.part?.part_name || item.custom_product_name || item.custom_product_code || '-' }}</td>
            <td class="text-center">{{ item.unit || 'EA' }}</td>
            <td class="text-right">{{ formatNumber(item.ordered_quantity) }}</td>
            <td class="text-right">{{ formatNumber(item.unit_price) }}</td>
            <td class="text-right">{{ formatNumber(item.line_total) }}</td>
            <td>{{ item.line_remarks || '' }}</td>
          </tr>
          <!-- 빈 행 채우기 (최소 10행) -->
          <tr v-for="i in emptyRowCount" :key="'empty-' + i">
            <td>&nbsp;</td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 총액 -->
    <div class="total-section">
      <table class="total-table">
        <tbody>
          <tr>
            <th>총액</th>
            <td class="currency-label">화폐단위(원)</td>
            <td class="amount-value">{{ formatNumber(purchaseOrder?.total_amount || 0) }}</td>
            <td class="vat-label">VAT별도 (최종가액)</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 특이사항 -->
    <div class="remarks-section">
      <h4>&lt; 특이사항 &gt;</h4>
      <ol>
        <li>대금지불조건: {{ purchaseOrder?.payment_terms || '세금계산서 발행일로부터 익월 말 이내' }}</li>
        <li>납품장소: {{ purchaseOrder?.delivery_terms || companyInfo.address }}</li>
        <li>위 주문에 대한 납기 준수를 필히 부탁드립니다.</li>
        <li>물품 입고 시 거래명세서를 첨부하여 주십시오.</li>
        <li>폐사에 공급되는 자재는 품질 검사 규정에 의거 검사가 진행됩니다.</li>
        <li>본 발주서에 따른 납품 시 수량은 발주수량과 일치하여야 합니다.</li>
        <li>불량으로 인해 발생되는 대내외적인 손해 발생 시 공급업체에서 변상책임을 부담합니다.</li>
        <li>납품 전 무역전쟁, 환율변화 등의 이유로 가격 변경이 필요시 협의하여 진행합니다.</li>
        <li>물품 공급 후 3개월간 A/S를 보증하는 것으로 하며, 단, 소모품 등은 별도 규정에 따릅니다.</li>
        <li>물품 입고 시 반드시 거래명세서와 성적서(또는 규격 확인용 인증서 등)를 첨부하여 주십시오.</li>
        <li>불량 발생 시 귀사로 반품처리, 대체품 배송요청합니다.</li>
        <li>본 발주서에 발행은 귀사의 견적서를 토대로 발급되며 제반조건은 동일 적용합니다.</li>
        <li>제품 공급 시 견적가와 다른 부분이 확인되면 협의 후 정산합니다.</li>
        <li>위 주문에 대한 주문 확인서(확약서/주문서류)를 발송 하여 주십시오.</li>
        <li>위 주문에 대한 다른 조건이 있으신 경우 회신 바랍니다.</li>
        <li>당사의 관련 지적 재산권은 엑스빔테크(주)에 귀속됩니다.</li>
        <li>ITAR 관련 자재 및 수출 통제 품목은 관련 법규에 따릅니다.</li>
      </ol>
    </div>

    <!-- 회사 서명 -->
    <div class="company-signature">
      <p class="company-name">{{ companyInfo.name }}</p>
      <p class="representative">대표이사 <strong>{{ companyInfo.representative }}</strong></p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PurchaseOrder } from '@/api/purchaseOrder'

const props = defineProps<{
  purchaseOrder: PurchaseOrder | null
}>()

// 회사 정보 (하드코딩 또는 설정에서 가져오기)
const companyInfo = {
  name: '엑스빔테크(주)',
  nameEn: 'XbeamTech Co., Ltd.',
  representative: '김행정',
  businessNumber: '123-45-67890',
  address: '경기도 김포시 양촌읍 흥신로 239번길 29',
  tel: '02-864-7280',
  fax: '02-864-7281',
  email: 'info@xbeamtech.com',
  purchaseManager: '박창현',
}

// 공급업체 연락처
const supplierContact = computed(() => {
  const supplier = props.purchaseOrder?.supplier
  if (!supplier) return '-'
  const parts = []
  if (supplier.tel) parts.push(supplier.tel)
  if (supplier.fax) parts.push(supplier.fax)
  return parts.join(' / ') || '-'
})

// 빈 행 개수 (최소 10행, 최대 15행)
const emptyRowCount = computed(() => {
  const itemCount = props.purchaseOrder?.items?.length || 0
  const minRows = 10
  const maxRows = 15
  const remaining = Math.max(0, minRows - itemCount)
  return Math.min(remaining, maxRows)
})

// 날짜 포맷
function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return `${date.getFullYear()}년 ${date.getMonth() + 1}월 ${date.getDate()}일`
}

// 숫자 포맷 (소수점 2자리까지)
function formatNumber(num?: number): string {
  if (num === undefined || num === null) return '0'
  return new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(num)
}
</script>

<style scoped>
.print-container {
  width: 210mm;
  min-height: 297mm;
  padding: 10mm 15mm;
  margin: 0 auto;
  background: white;
  font-family: '맑은 고딕', 'Malgun Gothic', sans-serif;
  font-size: 10pt;
  color: #000;
  box-sizing: border-box;
}

/* 헤더 */
.print-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10mm;
}

.title-section {
  flex: 1;
}

.main-title {
  font-size: 24pt;
  font-weight: bold;
  letter-spacing: 8px;
  margin: 0;
}

.approval-box {
  width: 90mm;
}

.approval-table {
  width: 100%;
  border-collapse: collapse;
}

.approval-table th,
.approval-table td {
  border: 1px solid #000;
  padding: 2mm;
  text-align: center;
  font-size: 9pt;
}

.approval-table th {
  background-color: #f0f0f0;
  font-weight: normal;
  height: 6mm;
}

.approval-cell {
  height: 15mm;
}

/* 문서 정보 */
.doc-info-section {
  margin-bottom: 5mm;
}

.doc-info-table {
  width: 100%;
  border-collapse: collapse;
}

.doc-info-table th,
.doc-info-table td {
  border: 1px solid #000;
  padding: 2mm 3mm;
  font-size: 9pt;
}

.doc-info-table th {
  background-color: #f0f0f0;
  font-weight: normal;
  width: 15%;
  text-align: center;
}

.doc-info-table td {
  width: 18%;
}

/* 공급업체 정보 */
.supplier-section {
  margin-bottom: 5mm;
}

.supplier-table {
  width: 100%;
  border-collapse: collapse;
}

.supplier-table th,
.supplier-table td {
  border: 1px solid #000;
  padding: 2mm 3mm;
  font-size: 9pt;
}

.supplier-table th {
  background-color: #f0f0f0;
  font-weight: normal;
  text-align: center;
}

.supplier-header {
  width: 8%;
  writing-mode: vertical-rl;
  text-orientation: upright;
  letter-spacing: 2px;
}

.supplier-table td {
  text-align: left;
}

/* 발주 항목 테이블 */
.items-section {
  margin-bottom: 3mm;
}

.items-table {
  width: 100%;
  border-collapse: collapse;
}

.items-table th,
.items-table td {
  border: 1px solid #000;
  padding: 2mm 3mm;
  font-size: 9pt;
}

.items-table th {
  background-color: #f0f0f0;
  font-weight: normal;
  text-align: center;
}

.items-table td {
  height: 6mm;
}

.col-no { width: 6%; }
.col-name { width: 30%; }
.col-unit { width: 8%; }
.col-qty { width: 10%; }
.col-price { width: 15%; }
.col-amount { width: 15%; }
.col-remarks { width: 16%; }

.text-center { text-align: center; }
.text-right { text-align: right; }

/* 총액 */
.total-section {
  margin-bottom: 5mm;
}

.total-table {
  width: 100%;
  border-collapse: collapse;
}

.total-table th,
.total-table td {
  border: 1px solid #000;
  padding: 3mm;
  font-size: 10pt;
}

.total-table th {
  background-color: #f0f0f0;
  font-weight: bold;
  width: 10%;
  text-align: center;
}

.currency-label {
  width: 15%;
  text-align: center;
  font-size: 9pt;
}

.amount-value {
  width: 25%;
  text-align: right;
  font-weight: bold;
  font-size: 12pt;
}

.vat-label {
  text-align: left;
  font-size: 9pt;
  color: #666;
}

/* 특이사항 */
.remarks-section {
  margin-bottom: 5mm;
  border: 1px solid #000;
  padding: 3mm;
}

.remarks-section h4 {
  margin: 0 0 2mm 0;
  font-size: 10pt;
  font-weight: bold;
}

.remarks-section ol {
  margin: 0;
  padding-left: 5mm;
  font-size: 8pt;
  line-height: 1.4;
}

.remarks-section li {
  margin-bottom: 1mm;
}

/* 회사 서명 */
.company-signature {
  text-align: right;
  margin-top: 10mm;
  padding-right: 20mm;
}

.company-name {
  font-size: 12pt;
  font-weight: bold;
  margin: 0;
}

.representative {
  font-size: 11pt;
  margin: 2mm 0 0 0;
}

.representative strong {
  font-size: 14pt;
  margin-left: 5mm;
}

/* 인쇄 스타일 */
@media print {
  @page {
    size: A4;
    margin: 0;
  }

  body {
    margin: 0;
    padding: 0;
  }

  .print-container {
    width: 210mm;
    min-height: 297mm;
    padding: 10mm 15mm;
    margin: 0;
    box-shadow: none;
  }

  /* 페이지 넘김 방지 */
  .items-table,
  .remarks-section {
    page-break-inside: avoid;
  }
}

/* 화면에서 미리보기용 스타일 */
@media screen {
  .print-container {
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
    margin: 20px auto;
  }
}
</style>
