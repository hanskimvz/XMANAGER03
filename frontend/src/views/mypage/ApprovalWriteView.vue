<template>
  <div class="aw-root">
    <!-- ===== TOP BAR ===== -->
    <header class="aw-topbar">
      <div class="aw-topbar-left">
        <div class="aw-brand">
          <span class="aw-logo">결</span>
          <span class="aw-sysname">전자결재</span>
        </div>
        <span class="aw-divider"></span>
        <nav class="aw-crumb">
          <RouterLink to="/approvals" class="aw-crumb-link">기안 문서</RouterLink>
          <span class="aw-crumb-sep">/</span>
          <span class="aw-crumb-current">{{ isEdit ? '기안 수정' : '기안서 작성' }}</span>
        </nav>
      </div>
      <div class="aw-topbar-right">
        <button type="button" class="aw-btn aw-btn-ghost" :disabled="saving" @click="previewDocument" title="저장 후 인쇄 미리보기">미리보기</button>
        <template v-if="adminMode">
          <button type="button" class="aw-btn aw-btn-primary" @click="adminFullSave" :disabled="saving" title="상태·결재선은 그대로 두고 문서 내용 전체를 정정합니다(정정 이력 기록)">
            {{ saving ? '저장 중...' : '관리자 정정 저장' }}
          </button>
        </template>
        <template v-else-if="isSubmittedEdit">
          <button type="button" class="aw-btn aw-btn-primary" @click="saveEdit" :disabled="saving">
            {{ saving ? '저장 중...' : '저장' }}
          </button>
        </template>
        <template v-else-if="isRejectedEdit">
          <button type="button" class="aw-btn aw-btn-primary" @click="resubmitEdit" :disabled="saving">
            {{ saving ? '재상신 중...' : '수정 후 재상신' }}
          </button>
        </template>
        <template v-else>
          <button type="button" class="aw-btn aw-btn-secondary" @click="saveDraft" :disabled="saving">
            {{ saving ? '저장 중...' : '임시저장' }}
          </button>
          <button type="button" class="aw-btn aw-btn-primary" @click="submitDocument" :disabled="saving">
            결재 요청
          </button>
        </template>
      </div>
    </header>

    <div v-if="loading" class="aw-loading">로딩 중...</div>

    <!-- ===== BODY ===== -->
    <div v-else class="aw-body">
      <!-- ===== MAIN ===== -->
      <main class="aw-main">
        <!-- status row -->
        <div class="aw-status-row">
          <div class="aw-status-left">
            <span class="aw-status-chip">
              <span class="aw-status-dot"></span>{{ isSubmittedEdit ? '수정 중 (승인 전)' : isRejectedEdit ? '반려 문서 수정 중' : '작성 중' }}
            </span>
          </div>
          <span class="aw-docno">문서번호 · {{ docId ? `편집-${docId}` : '신규' }}</span>
        </div>
        <div v-if="adminMode" style="margin:8px 0;padding:8px 12px;border:1px solid #93c5fd;background:#eff6ff;border-radius:8px;color:#1e40af;font-size:13px;">
          🛠 <b>관리자 정정 모드</b> — 상태·결재선(승인/도장)은 <b>그대로 두고</b> 문서 내용 전체를 수정합니다. 저장 시 정정 이력에 기록되며 <b>재상신되지 않습니다</b>.
        </div>
        <div v-if="isSubmittedEdit && !adminMode" style="margin:8px 0;padding:8px 12px;border:1px solid #f0c36d;background:#fdf6e7;border-radius:8px;color:#8a6d1a;font-size:13px;">
          ⚠ 결재 진행 중인 문서입니다. 저장하면 결재선 1차부터 다시 결재됩니다.
        </div>
        <div v-if="isRejectedEdit && !adminMode" style="margin:8px 0;padding:8px 12px;border:1px solid #f0c36d;background:#fdf6e7;border-radius:8px;color:#8a6d1a;font-size:13px;">
          ⚠ 반려된 문서입니다. 내용·첨부를 수정한 뒤 <b>수정 후 재상신</b>하면 결재선 1차부터 다시 결재됩니다.
        </div>

        <!-- PAPER -->
        <div class="aw-paper">
          <!-- doc header + approval grid -->
          <div class="aw-paper-header">
            <div class="aw-stamp-grid">
              <div class="aw-stamp-label"><span>결</span><span>재</span></div>
              <div v-for="(col, ci) in stampColumns" :key="ci" class="aw-stamp-col">
                <div class="aw-stamp-col-label">{{ col.label }}</div>
                <div class="aw-stamp-box">
                  <div v-if="col.done" class="aw-stamp-mark">{{ col.name }}</div>
                  <span v-else class="aw-stamp-wait">대기</span>
                </div>
                <div class="aw-stamp-foot" :class="{ 'aw-stamp-foot-wait': !col.done }">
                  {{ col.done ? (col.date || '').slice(5).replace('-', '.') : col.name }}
                </div>
              </div>
            </div>

            <div class="aw-paper-title-wrap">
              <h1 class="aw-paper-title">{{ paperTitle }}</h1>
              <div class="aw-paper-subtitle">DRAFT FOR APPROVAL</div>
            </div>
          </div>

          <!-- meta table -->
          <div class="aw-meta-wrap">
            <div class="aw-meta-grid">
              <div class="aw-meta-label">문서번호</div>
              <div class="aw-meta-value">{{ docId ? `편집-${docId}` : '신규(저장 시 채번)' }}</div>
              <div class="aw-meta-label">기안일자</div>
              <div class="aw-meta-value">{{ draftDateStr }}</div>

              <div class="aw-meta-label">기안부서</div>
              <div class="aw-meta-value">{{ drafterDepartment || '-' }}</div>
              <div class="aw-meta-label">기안자</div>
              <div class="aw-meta-value">
                {{ drafterName }}
                <span v-if="drafterPosition" class="aw-meta-sub">{{ drafterPosition }}</span>
              </div>

              <!-- 휴가 신청서에는 프로젝트 선택 미표시 -->
              <template v-if="!isLeaveForm">
                <div class="aw-meta-label">프로젝트</div>
                <div class="aw-meta-value aw-meta-value-input">
                  <select v-model="projectId" class="aw-inline-select">
                    <option :value="null">선택 안 함</option>
                    <option v-for="p in projects" :key="p.id" :value="p.id">[{{ p.code }}] {{ p.name }}</option>
                  </select>
                </div>
              </template>
              <div class="aw-meta-label">양식</div>
              <div class="aw-meta-value" :style="isLeaveForm ? 'grid-column: 2 / -1;' : undefined">{{ selectedForm ? selectedForm.name : '일반 기안' }}</div>

              <!-- 프로젝트 즉석추가 -->
              <template v-if="projectAddOpen">
                <div class="aw-meta-label">새 프로젝트</div>
                <div class="aw-meta-value aw-meta-value-input" style="grid-column: 2 / -1;">
                  <div class="aw-proj-add">
                    <input
                      v-model="newProjectName"
                      type="text"
                      placeholder="새 프로젝트 이름"
                      class="aw-inline-input"
                      @keyup.enter="createNewProject"
                    />
                    <button
                      type="button"
                      class="aw-mini-btn aw-mini-btn-primary"
                      :disabled="projectCreating || !newProjectName.trim()"
                      @click="createNewProject"
                    >{{ projectCreating ? '추가 중...' : '추가' }}</button>
                    <button type="button" class="aw-mini-btn" @click="projectAddOpen = false">취소</button>
                  </div>
                </div>
              </template>

              <!-- 제목 (full width). 휴가는 자동 생성("유형 기안자")이라 입력 생략 -->
              <div class="aw-meta-label" style="grid-column: 1;">제목 <span v-if="!isLeaveForm" class="aw-req">*</span></div>
              <div class="aw-meta-value aw-meta-value-input" style="grid-column: 2 / -1;">
                <input
                  v-if="!isLeaveForm"
                  v-model="title"
                  type="text"
                  maxlength="200"
                  placeholder="문서 제목을 입력하세요"
                  class="aw-inline-input aw-title-input"
                />
                <span v-else class="aw-title-auto">{{ title || '휴가 ' + drafterName }} <span class="aw-title-auto-hint">(자동)</span></span>
              </div>
            </div>

            <button v-if="!isLeaveForm" type="button" class="aw-add-proj-link" @click="openProjectAdd">＋ 새 프로젝트</button>
          </div>

          <!-- 양식 동적 필드 -->
          <div v-if="selectedForm" class="aw-section">
            <div class="aw-section-label">{{ selectedForm.name }} 항목</div>

            <!-- 휴가: 잔여 연차 안내 -->
            <div v-if="isLeaveForm && leaveBalance" class="aw-leave-note">
              올해({{ leaveBalance.year }}) 연차 {{ leaveBalance.entitlement }}일 중
              {{ leaveBalance.used }}일 사용, 잔여 {{ leaveBalance.remaining }}일
              <span v-if="leaveOverflow" class="aw-leave-over">
                ⚠ 신청 일수({{ formData.days }}일)가 잔여 연차를 초과합니다.
              </span>
            </div>

            <!-- 사후(POST) 양식: 선행문서 선택 -->
            <div v-if="isPostForm" class="aw-field">
              <label class="aw-field-label">{{ predecessorLabel }}</label>
              <div v-if="predecessorsLoaded && linkablePredecessors.length === 0" class="aw-empty-hint">
                연결 가능한 선행 문서가 없습니다
              </div>
              <template v-else>
                <SearchableSelect
                  :model-value="addRelatedId"
                  :options="tripOptions"
                  :preserve-order="true"
                  placeholder="선행 문서 검색/선택 후 추가 (여러 개 가능)"
                  @update:model-value="onAddRelated"
                />
                <!-- 선택된 관련 문서 목록(칩) -->
                <div v-if="selectedRelatedDocs.length" class="aw-rel-chips">
                  <span v-for="rd in selectedRelatedDocs" :key="rd.id" class="aw-rel-chip">
                    <span class="aw-rel-chip-txt">{{ rd.doc_number }} · {{ rd.title }}</span>
                    <button type="button" class="aw-rel-chip-x" @click="removeRelated(rd.id)" aria-label="제거">×</button>
                  </span>
                </div>
                <p v-if="selectedTrip && isExpenseForm" class="aw-field-help">
                  예상경비:
                  <span class="aw-strong">
                    {{ selectedTrip.expense != null ? selectedTrip.expense.toLocaleString() + '원' : '미입력' }}
                  </span>
                  <span v-if="selectedTrip.start_date"> · 기간 {{ selectedTrip.start_date }} ~ {{ selectedTrip.end_date || '' }}</span>
                </p>
              </template>
            </div>

            <!-- 구매 구분(구매기안서/지출결의서): 과제를 고르면 품목 아래 RCMS 항목·세부항목이 나타난다 -->
            <div v-if="isPurchaseForm" class="aw-field">
              <label class="aw-field-label">구매 구분 <span v-if="isPurchaseDraft" class="aw-req">*</span></label>
              <div class="aw-items-mode aw-cat-mode">
                <button
                  v-for="c in PURCHASE_CATEGORIES"
                  :key="c"
                  type="button"
                  class="aw-mode-btn"
                  :class="{ 'aw-mode-on': purchaseCategory === c }"
                  @click="purchaseCategory = purchaseCategory === c ? '' : c"
                >{{ c }}</button>
              </div>
              <p v-if="isPurchaseDraft" class="aw-field-help">과제를 고르면 품목 아래에 RCMS 항목·세부항목 선택란이 나타납니다.</p>
            </div>

            <template v-for="field in selectedForm.fields_schema" :key="field.key">
            <div v-if="!(isLeaveForm && (field.key === 'end_date' || field.key === 'substitute'))" class="aw-field">
              <label class="aw-field-label">
                {{ isLeaveForm && field.key === 'start_date' ? '휴가 날짜' : field.label }}
                <span v-if="field.required" class="aw-req">*</span>
              </label>

              <!-- 참석자: 구조화 입력 -->
              <div v-if="field.key === 'attendees'" class="aw-attendees">
                <div v-for="(row, ridx) in attendeeRows" :key="ridx" class="aw-attendee-row">
                  <input v-model="row.org" type="text" placeholder="소속" class="aw-input" />
                  <input v-model="row.name" type="text" placeholder="이름" class="aw-input" />
                  <input v-model="row.title" type="text" placeholder="직책" class="aw-input" />
                  <button type="button" class="aw-icon-btn aw-icon-del" title="삭제" @click="removeAttendeeRow(ridx)">✕</button>
                </div>
                <div class="aw-attendee-actions">
                  <button type="button" class="aw-mini-btn" @click="addAttendeeRow">+ 참석자 추가</button>
                  <button type="button" class="aw-mini-btn aw-mini-btn-dark" @click="onPrintAttendanceSheet">참석자 서명부 인쇄</button>
                </div>
              </div>

              <!-- 품목: 품목표(상세단가/BOM) 또는 자유형식(일괄·간단) 중 선택 -->
              <div v-else-if="field.key === 'items'" class="aw-items">
                <div class="aw-items-mode">
                  <button type="button" class="aw-mode-btn" :class="{ 'aw-mode-on': itemsMode === 'TABLE' }" @click="itemsMode = 'TABLE'">품목표 (상세단가·BOM)</button>
                  <button type="button" class="aw-mode-btn" :class="{ 'aw-mode-on': itemsMode === 'FREE' }" @click="itemsMode = 'FREE'">자유형식 (일괄·간단)</button>
                </div>

                <!-- 부가세 포함/별도 표시 (품목표·자유형식 공통) -->
                <div class="aw-vat">
                  <label class="aw-vat-check">
                    <input type="checkbox" v-model="vatIncluded" />
                    <span>부가세 포함 금액</span>
                  </label>
                  <span class="aw-vat-tag" :class="vatIncluded ? 'aw-vat-inc' : 'aw-vat-exc'">
                    {{ vatIncluded ? '부가세 포함' : '부가세 별도' }}
                  </span>
                  <span v-if="vatBreakdown" class="aw-vat-break">
                    공급가 {{ formatMoney(vatBreakdown.supply) }} · 부가세 {{ formatMoney(vatBreakdown.vat) }} · 합계 <b>{{ formatMoney(vatBreakdown.total) }}</b> {{ currencySuffix }}
                  </span>
                </div>

                <template v-if="itemsMode === 'TABLE'">
                  <div class="aw-items-row aw-items-head">
                    <span>품목</span><span>수량</span><span>단가</span><span>비고</span><span>금액</span><span></span>
                  </div>
                  <div v-for="(row, ridx) in itemRows" :key="ridx" class="aw-items-row">
                    <input v-model="row.name" type="text" placeholder="품목명" class="aw-input" />
                    <input v-model.number="row.qty" type="number" min="0" placeholder="수량" class="aw-input" />
                    <MoneyInput v-model="row.unit_price" :currency="currency" :fraction-digits="UNIT_PRICE_DIGITS" placeholder="단가" class="aw-input" />
                    <input v-model="row.note" type="text" placeholder="비고" class="aw-input" />
                    <span class="aw-item-amount">{{ formatMoney(lineAmount(row)) }}</span>
                    <button type="button" class="aw-icon-btn aw-icon-del" title="삭제" @click="removeItemRow(ridx)">✕</button>
                  </div>
                  <div class="aw-attendee-actions">
                    <button type="button" class="aw-mini-btn" @click="addItemRow">+ 품목 추가</button>
                    <button type="button" class="aw-mini-btn aw-mini-btn-primary" @click="showPartPicker = true">📦 BOM에서 선택</button>
                    <button type="button" class="aw-mini-btn" :disabled="itemsUploading" @click="itemsFileInput?.click()">
                      {{ itemsUploading ? '업로드 중...' : '📥 엑셀 업로드' }}
                    </button>
                    <button type="button" class="aw-mini-btn" @click="downloadItemsTemplate">양식</button>
                    <input ref="itemsFileInput" type="file" accept=".xlsx,.xls" class="hidden" @change="onItemsFile" />
                    <span class="aw-items-total">합계 {{ formatMoney(itemsTotal) }} {{ currencySuffix }}</span>
                  </div>
                </template>

                <template v-else>
                  <textarea v-model="itemsFree" rows="4" class="aw-input aw-textarea"
                    placeholder="예) OO상사 3월분 잔금 일괄 지불 / 소모품 커넥터 외 6종 일괄 구매 등 자유롭게 작성"></textarea>
                  <p class="aw-field-help">금액은 아래 <b>청구 금액</b>에 직접 입력하세요.</p>
                </template>

                <!-- 발주서 자동 생성 (구매기안서 + 품목표 모드 전용) — 품목 바로 아래에 눈에 띄게 배치 -->
                <div v-if="isPurchaseDraft && itemsMode === 'TABLE'" class="aw-po-box" :class="{ 'aw-po-box-on': autoPo }">
                  <label class="aw-po-toggle">
                    <input type="checkbox" v-model="autoPo" @change="autoPo && loadSuppliers()" />
                    <span class="aw-po-toggle-txt">📦 승인되면 이 <b>품목표</b>로 <b>발주서(임시저장)를 자동 생성</b></span>
                  </label>
                  <div v-if="autoPo" class="aw-po-body">
                    <label class="aw-po-sup-label">공급업체(발주처) <span class="aw-req">*</span></label>
                    <SearchableSelect v-model="poSupplierId" :options="supplierOptions" placeholder="거래처(공급업체) 검색 또는 선택" />
                    <p class="aw-po-hint">BOM 품목은 부품 연결, 자유입력 품목은 품명으로 발주서에 담깁니다.</p>
                  </div>
                </div>
              </div>

              <textarea
                v-else-if="field.type === 'textarea'"
                v-model="formData[field.key]"
                rows="3"
                :placeholder="field.placeholder || ''"
                class="aw-input aw-textarea"
              ></textarea>

              <!-- 휴가 유형: 반차를 오전/오후로 세분 -->
              <select
                v-else-if="isLeaveForm && field.key === 'leave_type'"
                v-model="formData[field.key]"
                class="aw-input"
              >
                <option value="">선택하세요</option>
                <option v-for="opt in leaveTypeOptions" :key="opt" :value="opt">{{ opt }}</option>
              </select>

              <select
                v-else-if="field.type === 'select'"
                v-model="formData[field.key]"
                class="aw-input"
              >
                <option value="">선택하세요</option>
                <option v-for="opt in field.options || []" :key="opt" :value="opt">{{ opt }}</option>
              </select>

              <!-- 청구 금액 + 통화 선택 (구매기안서/지출결의서) — 자유형식·품목표 공통 -->
              <div v-else-if="isPurchaseForm && field.key === 'amount'" class="aw-amount-row">
                <MoneyInput
                  v-model="formData[field.key]"
                  :currency="currency"
                  :fraction-digits="hasItemsField && itemsMode === 'TABLE' ? UNIT_PRICE_DIGITS : undefined"
                  :placeholder="itemsMode === 'FREE' ? '총액 직접 입력' : (field.placeholder || '')"
                  :readonly="hasItemsField && itemsMode === 'TABLE'"
                  class="aw-input"
                  :class="{ 'aw-input-readonly': hasItemsField && itemsMode === 'TABLE' }"
                />
                <select v-model="currency" class="aw-input aw-cur-select" title="통화 선택">
                  <option value="KRW">₩ KRW</option>
                  <option value="USD">$ USD</option>
                  <option value="JPY">¥ JPY</option>
                  <option value="CNY">¥ CNY</option>
                  <option value="EUR">€ EUR</option>
                </select>
              </div>

              <MoneyInput
                v-else-if="field.type === 'number'"
                v-model="formData[field.key]"
                :fraction-digits="hasItemsField && field.key === 'amount' && itemsMode === 'TABLE' ? UNIT_PRICE_DIGITS : undefined"
                :placeholder="field.key === 'amount' && itemsMode === 'FREE' ? '총액 직접 입력' : (field.placeholder || '')"
                :readonly="(isLeaveForm && field.key === 'days') || (isSettlementForm && field.key === 'total_cost') || (hasItemsField && field.key === 'amount' && itemsMode === 'TABLE')"
                class="aw-input"
                :class="{ 'aw-input-readonly': (isLeaveForm && field.key === 'days') || (isSettlementForm && field.key === 'total_cost') || (hasItemsField && field.key === 'amount' && itemsMode === 'TABLE') }"
              />

              <!-- 휴가: 날짜 선택 달력 (개별/기간, 주말 자동 제외 / 반차는 하루만) -->
              <LeaveDateSelector
                v-else-if="isLeaveForm && field.key === 'start_date'"
                v-model="leaveDates"
                :single="isHalfDay(formData['leave_type'])"
              />

              <input
                v-else-if="field.type === 'date'"
                v-model="formData[field.key]"
                type="date"
                class="aw-input"
                @change="onLeaveDateChange"
              />

              <input
                v-else
                v-model="formData[field.key]"
                type="text"
                :placeholder="field.placeholder || ''"
                class="aw-input"
              />

              <!-- 정산서 합계: 차액 표시 -->
              <p
                v-if="isSettlementForm && field.key === 'total_cost' && expenseDiff !== null"
                class="aw-field-help"
                :class="expenseDiff > 0 ? 'aw-text-red' : 'aw-text-green'"
              >
                예상경비 {{ selectedTrip?.expense?.toLocaleString() }}원 대비
                {{ expenseDiff > 0 ? '+' : '' }}{{ expenseDiff.toLocaleString() }}원
                ({{ expenseDiff > 0 ? '초과' : '이하' }})
              </p>

              <p v-if="field.help" class="aw-field-help">{{ field.help }}</p>
            </div>

            <!-- 과제 구매기안서: 품목 바로 아래 RCMS 항목·세부항목 (비목은 항목에서 자동) -->
            <template v-if="field.key === 'items' && showBudgetFields">
              <div class="aw-field aw-budget">
                <label class="aw-field-label">항목 <span class="aw-req">*</span></label>
                <div class="aw-budget-row">
                  <span v-if="budgetCategory" class="aw-budget-badge">{{ budgetCategory }}</span>
                  <select v-model="budgetItem" class="aw-input aw-budget-select">
                    <option value="">선택하세요</option>
                    <option v-for="it in RCMS_BUDGET_ITEMS" :key="it.name" :value="it.name">{{ it.name }}</option>
                  </select>
                  <span class="aw-budget-note">필수 · 비목은 자동 표시</span>
                </div>
              </div>
              <div class="aw-field aw-budget">
                <label class="aw-field-label">세부항목 <span class="aw-req">*</span></label>
                <div class="aw-budget-row">
                  <select v-model="budgetDetail" class="aw-input aw-budget-select" :disabled="!budgetItem">
                    <option value="">{{ budgetItem ? '선택하세요' : '항목을 먼저 선택하세요' }}</option>
                    <option v-for="d in budgetDetailOptions" :key="d" :value="d">{{ d }}</option>
                  </select>
                  <span class="aw-budget-note">필수 · RCMS 세부항목과 동일</span>
                </div>
              </div>
            </template>
            </template>

            <!-- 출장정산서: 개인카드 경비 환급 (체크 시 항목 입력 → 승인 시 지출결의서 자동 생성) -->
            <div v-if="isSettlementForm" class="aw-field aw-personal">
              <label class="aw-personal-toggle">
                <input type="checkbox" :checked="hasPersonal" @change="togglePersonal" />
                <span>개인카드 경비 환급 신청 (개인 계좌로 환급)</span>
              </label>
              <p class="aw-field-help">체크하면 개인 사용 항목을 입력할 수 있고, 이 출장정산서가 승인되면 <b>지출결의서 초안이 자동 생성</b>됩니다.</p>

              <div v-if="hasPersonal" class="aw-personal-body">
                <div class="aw-items-row aw-items-head aw-personal-row"><span>사용 내역</span><span>금액</span><span></span></div>
                <div v-for="(row, ridx) in personalRows" :key="ridx" class="aw-items-row aw-personal-row">
                  <input v-model="row.name" type="text" placeholder="예: KTX 왕복" class="aw-input" />
                  <MoneyInput v-model="row.amount" :currency="currency" placeholder="금액" class="aw-input" />
                  <button type="button" class="aw-icon-btn aw-icon-del" title="삭제" @click="removePersonalRow(ridx)">✕</button>
                </div>
                <div class="aw-attendee-actions">
                  <button type="button" class="aw-mini-btn" @click="addPersonalRow">+ 항목 추가</button>
                  <span class="aw-items-total">환급 합계 {{ formatMoney(personalTotal) }} 원</span>
                </div>
                <div class="aw-personal-grid">
                  <div>
                    <label class="aw-field-label">결제방법</label>
                    <select v-model="personalPayment" class="aw-input">
                      <option>카드결제</option><option>현금-선결제</option><option>익월결제</option>
                    </select>
                  </div>
                  <div>
                    <label class="aw-field-label">입금 계좌 <span class="aw-req">*</span></label>
                    <input v-model="personalAccount" type="text" placeholder="은행 / 계좌번호 / 예금주" class="aw-input" />
                  </div>
                </div>
                <div>
                  <label class="aw-field-label">환급 사유 / 비고</label>
                  <textarea v-model="personalNote" rows="2" class="aw-input aw-textarea" placeholder="개인카드로 선지출한 사유"></textarea>
                </div>
              </div>
            </div>
          </div>

          <!-- 본문 -->
          <div class="aw-section">
            <div class="aw-section-label">본문</div>
            <div class="aw-content-box">
              <MarkupEditor v-model="content" multiline images min-height="260px" />
            </div>
          </div>

          <!-- 첨부파일 -->
          <div class="aw-section aw-section-last">
            <div class="aw-section-label">첨부파일</div>

            <ul v-if="attachments.length || pendingFiles.length" class="aw-attach-list">
              <li v-for="att in attachments" :key="'a' + att.id" class="aw-attach-item">
                <div class="aw-attach-badge">FILE</div>
                <div class="aw-attach-info">
                  <button type="button" class="aw-attach-name aw-attach-link" :title="`${att.original_name} 미리보기`" @click="openPreview(att)">{{ att.original_name }}</button>
                  <div class="aw-attach-size">{{ formatFileSize(att.file_size) }}</div>
                </div>
                <button class="aw-icon-btn" title="미리보기" @click="openPreview(att)">👁</button>
                <button class="aw-icon-btn" title="새 탭에서 열기" @click="openAttachment(att)">↗</button>
                <button class="aw-icon-btn" title="삭제" @click="removeAttachment(att.id)">✕</button>
              </li>
              <!-- 저장 전 첨부(저장 시 업로드) -->
              <li v-for="(f, i) in pendingFiles" :key="'p' + i" class="aw-attach-item">
                <div class="aw-attach-badge" style="background:#fde68a;color:#92400e">대기</div>
                <div class="aw-attach-info">
                  <span class="aw-attach-name">{{ f.name }}</span>
                  <div class="aw-attach-size">{{ formatFileSize(f.size) }} · 저장 시 업로드</div>
                </div>
                <button class="aw-icon-btn" title="제거" @click="pendingFiles.splice(i, 1)">✕</button>
              </li>
            </ul>

            <input ref="fileInput" type="file" multiple class="aw-hidden" @change="onFileSelected" />
            <div
              class="aw-dropzone"
              role="button"
              tabindex="0"
              :style="dropOver ? 'border-color:#2563eb;background:#eff6ff' : ''"
              @click="fileInput?.click()"
              @keydown.enter="fileInput?.click()"
              @dragover.prevent="dropOver = true"
              @dragleave.prevent="dropOver = false"
              @drop.prevent="onDropFiles"
            >{{ uploading ? '업로드 중...' : '파일을 여기로 끌어다 놓거나 클릭하여 첨부 · 여러 개 가능 (최대 200MB)' }}</div>
            <p v-if="!docId && !pendingFiles.length" class="aw-empty-hint">저장(임시저장/결재요청) 시 함께 업로드됩니다 — 먼저 저장하지 않아도 됩니다.</p>
          </div>
        </div>
      </main>

      <!-- ===== SIDEBAR ===== -->
      <aside class="aw-sidebar">
        <!-- 양식 선택 카드 -->
        <div class="aw-card">
          <div class="aw-card-title">양식</div>
          <!-- 양식 칩: 관련 양식끼리 한 줄로 그룹화(일반 / 구매 / 휴가 / 출장쌍 / 회의묶음) v0.44.0 -->
          <div class="aw-form-chips">
            <div v-for="(row, ri) in formRows" :key="ri" class="aw-form-row">
              <button
                v-for="f in row"
                :key="f.id"
                type="button"
                class="aw-form-chip"
                :class="{ 'aw-form-chip-on': selectedFormId === f.id }"
                @click="selectForm(f.id)"
              >{{ f.name }}</button>
            </div>
          </div>
        </div>

        <!-- 결재선 카드 -->
        <div class="aw-card">
          <div class="aw-card-head">
            <span class="aw-card-title">결재선 <span class="aw-req">*</span></span>
            <span class="aw-card-hint">위→아래 순서로 결재</span>
          </div>

          <!-- 결재자 추가 -->
          <div class="aw-add-row">
            <div class="aw-add-select">
              <SearchableSelect
                v-model="selectedApproverId"
                :options="approverOptions"
                placeholder="결재자 검색 또는 선택"
              />
            </div>
            <button class="aw-mini-btn aw-mini-btn-dark" :disabled="!selectedApproverId" @click="addApprover">+ 추가</button>
          </div>

          <!-- id 직접입력 fallback -->
          <div v-if="approverOptions.length === 0" class="aw-add-row">
            <input
              v-model.number="manualApproverId"
              type="number"
              placeholder="결재자 ID 직접 입력"
              class="aw-input"
            />
            <button class="aw-mini-btn aw-mini-btn-dark" :disabled="!manualApproverId" @click="addManualApprover">추가</button>
          </div>

          <!-- 결재선 목록 -->
          <div v-if="lines.length === 0" class="aw-empty-hint aw-empty-hint-center">
            지정된 결재자가 없습니다
          </div>
          <ul v-else class="aw-line-list">
            <li
              v-for="(line, idx) in lines"
              :key="line.approver_id"
              draggable="true"
              class="aw-line-item"
              :class="{ 'aw-line-over': dragOverIndex === idx, 'aw-line-dragging': dragIndex === idx }"
              @dragstart="onDragStart(idx)"
              @dragover.prevent="onDragOver(idx)"
              @drop.prevent="onDrop(idx)"
              @dragend="onDragEnd"
            >
              <span class="aw-line-handle" title="드래그하여 이동">⠿</span>
              <div class="aw-avatar">{{ initials(approverLabel(line.approver_id)) }}</div>
              <div class="aw-line-info">
                <div class="aw-line-name">{{ approverLabel(line.approver_id) }}</div>
                <div class="aw-line-role">{{ lineRole(idx) }}</div>
              </div>
              <span
                class="aw-step-pill"
                :class="idx === lines.length - 1 ? 'aw-step-final' : 'aw-step-mid'"
              >{{ idx === lines.length - 1 ? '최종' : (idx + 1) + '단' }}</span>
              <div class="aw-line-ctrls">
                <button class="aw-icon-btn" :disabled="idx === 0" title="위로" @click="moveUp(idx)">▲</button>
                <button class="aw-icon-btn" :disabled="idx === lines.length - 1" title="아래로" @click="moveDown(idx)">▼</button>
                <button class="aw-icon-btn aw-icon-del" title="삭제" @click="removeApprover(idx)">✕</button>
              </div>
            </li>
          </ul>
        </div>

        <!-- 공유 및 옵션 카드 -->
        <div class="aw-card">
          <div class="aw-card-title">공유 및 옵션</div>

          <div class="aw-share-label">참조자</div>
          <div class="aw-add-row aw-add-row-tight">
            <div class="aw-add-select">
              <SearchableSelect
                v-model="selectedReferenceId"
                :options="approverOptions"
                placeholder="참조자 검색 또는 선택"
              />
            </div>
            <button class="aw-mini-btn aw-mini-btn-dark" :disabled="!selectedReferenceId" @click="addReference">+ 추가</button>
          </div>

          <div v-if="referenceIds.length === 0" class="aw-ref-empty">지정된 참조자가 없습니다</div>
          <div v-else class="aw-ref-chips">
            <span v-for="rid in referenceIds" :key="rid" class="aw-ref-chip">
              {{ approverLabel(rid) }}
              <button class="aw-ref-chip-x" title="삭제" @click="removeReference(rid)">✕</button>
            </span>
          </div>

          <!-- 시행자(지출결의서 전용). 구매 구분은 본문(품목 위)으로 이동 -->
          <template v-if="isPurchaseForm">
            <!-- 시행자: 지출결의서에서만 지정(구매기안서는 시행자 없음) -->
            <template v-if="isDisbursementForm">
              <div class="aw-share-label" style="margin-top:12px">시행자 <span class="aw-req">*</span> <span class="aw-title-auto-hint">(승인 후 집행 담당 · 필수)</span></div>
              <div class="aw-add-row aw-add-row-tight">
                <div class="aw-add-select">
                  <SearchableSelect v-model="executorId" :options="approverOptions" placeholder="시행자 검색 또는 선택" />
                </div>
              </div>
              <div v-if="executorId" class="aw-ref-chips">
                <span class="aw-ref-chip">{{ approverLabel(executorId) }}
                  <button class="aw-ref-chip-x" title="해제" @click="executorId = undefined">✕</button>
                </span>
              </div>
            </template>

          </template>
        </div>

        <div class="aw-footnote">결재 요청 시 첫 번째 결재자에게<br>알림이 전송됩니다.</div>
      </aside>
    </div>

    <!-- BOM(부품) 선택 모달 -->
    <PartPickerModal v-if="showPartPicker" @close="showPartPicker = false" @select="onPartsPicked" />

    <!-- 첨부 미리보기 모달 -->
    <AttachmentPreviewModal
      :open="previewOpen"
      :url="previewUrl"
      :kind="previewKind"
      :name="previewName"
      :loading="previewLoading"
      @close="closePreview"
      @download="previewDownload"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import MarkupEditor from '@/components/common/MarkupEditor.vue'
import MoneyInput from '@/components/common/MoneyInput.vue'
import AttachmentPreviewModal from '@/views/mypage/approval/AttachmentPreviewModal.vue'
import SearchableSelect from '@/components/SearchableSelect.vue'
import { partnerApi } from '@/api/partner'
import LeaveDateSelector from '@/views/mypage/LeaveDateSelector.vue'
import PartPickerModal, { type PickedItem } from '@/views/mypage/approval/PartPickerModal.vue'
import { useToast } from '@/composables/useToast'
import { downloadAuthedUrl } from '@/utils/download'
import { settingsApi } from '@/api/settings'
import { useAuth } from '@/stores/auth'
import { printAttendanceSheet } from '@/utils/attendanceSheet'
import { departmentLabel } from '@/api/department'
import { RCMS_BUDGET_ITEMS, findRcmsItem } from '@/constants/rcmsBudget'
import {
  approvalApi,
  type ApproverCandidate,
  type ApprovalLineInput,
  type ApprovalForm,
  type ApprovalAttachment,
  type LeaveBalance,
  type LinkablePredecessor,
  type ApprovalProject,
} from '@/api/approval'

const route = useRoute()
const router = useRouter()
const { success, error, warning } = useToast()
const auth = useAuth()

const docId = ref<number | null>(route.params.id ? Number(route.params.id) : null)
const isEdit = computed(() => docId.value !== null)
// 수정 대상 문서의 상태(로드 시 세팅). IN_PROGRESS = 상신 후 승인 전 수정
const editingStatus = ref<string | null>(null)
const isSubmittedEdit = computed(() => editingStatus.value === 'IN_PROGRESS')
const isRejectedEdit = computed(() => editingStatus.value === 'REJECTED')
// 관리자 전체수정 모드: /approvals/:id/edit?admin=1 → 상태 무관 전체 편집(결재선/상태 보존, 정정 저장).
// 쿼리 플래그만으로 판정(백엔드 require_admin이 보안 강제) — client isAdmin 상태와 무관하게 항상 정정 저장 경로 사용.
const adminMode = computed(() => isEdit.value && route.query.admin === '1')

const title = ref('')
const content = ref('')
const lines = ref<ApprovalLineInput[]>([])
const selectedApproverId = ref<number | undefined>(undefined)
const manualApproverId = ref<number | null>(null)
const candidates = ref<ApproverCandidate[]>([])
const loading = ref(false)
const saving = ref(false)

// 프로젝트 (공통, 선택)
const projects = ref<ApprovalProject[]>([])
const projectId = ref<number | null>(null)

// 프로젝트 즉석추가 (인라인)
const projectAddOpen = ref(false)
const newProjectName = ref('')
const projectCreating = ref(false)

const openProjectAdd = () => {
  newProjectName.value = ''
  projectAddOpen.value = true
}

const createNewProject = async () => {
  const name = newProjectName.value.trim()
  if (!name) return
  projectCreating.value = true
  try {
    const res = await approvalApi.createProject({ name })
    await loadProjects()
    projectId.value = res.data.id
    projectAddOpen.value = false
    newProjectName.value = ''
    success('프로젝트가 추가되었습니다')
  } catch {
    error('프로젝트 추가에 실패했습니다')
  } finally {
    projectCreating.value = false
  }
}

// ── 참석자 구조화 입력 (회의 양식: key === 'attendees') ──
interface AttendeeRow { org: string; name: string; title: string }
const attendeeRows = ref<AttendeeRow[]>([])

const addAttendeeRow = () => attendeeRows.value.push({ org: '', name: '', title: '' })
const removeAttendeeRow = (idx: number) => attendeeRows.value.splice(idx, 1)

// 참석자 서명부 인쇄 (현재 편집 중인 참석자 행 사용)
const onPrintAttendanceSheet = () => {
  const dateStr =
    formData.value['meeting_at'] ||
    formData.value['meeting_date'] ||
    formData.value['date'] ||
    ''
  try {
    printAttendanceSheet({
      title: title.value.trim() || (selectedForm.value?.name ?? '회의'),
      dateStr: dateStr ? String(dateStr) : undefined,
      attendees: attendeeRows.value,
    })
  } catch {
    error('팝업이 차단되었습니다. 팝업을 허용해주세요')
  }
}

// formData[attendees] 값을 행으로 복원 (배열=구조화, 문자열=레거시 관대처리)
const hydrateAttendees = (raw: unknown) => {
  if (Array.isArray(raw)) {
    attendeeRows.value = raw.map((r) => {
      const o = (r ?? {}) as Record<string, unknown>
      return {
        org: o.org != null ? String(o.org) : '',
        name: o.name != null ? String(o.name) : '',
        title: o.title != null ? String(o.title) : '',
      }
    })
  } else if (typeof raw === 'string' && raw.trim()) {
    attendeeRows.value = [{ org: '', name: raw.trim(), title: '' }]
  } else {
    attendeeRows.value = []
  }
}

// 현재 양식에 attendees 필드가 있는지
const hasAttendeesField = computed(
  () => !!selectedForm.value?.fields_schema.some((f) => f.key === 'attendees'),
)

// ── 품목 입력 (구매/지출결의: key === 'items') ──
// TABLE=품목표(상세단가/BOM) / FREE=자유형식(일괄·간단, 총액 직접 입력)
const itemsMode = ref<'TABLE' | 'FREE'>('TABLE')
const itemsFree = ref('')
// 부가세 포함 여부(품목 섹션 전체 적용) — 미체크 = 부가세 별도(기본)
const vatIncluded = ref(false)
interface ItemRow { name: string; qty: number | null; unit_price: number | null; note: string; part_id: number | null }
const itemRows = ref<ItemRow[]>([])
const newItemRow = (): ItemRow => ({ name: '', qty: null, unit_price: null, note: '', part_id: null })
const addItemRow = () => itemRows.value.push(newItemRow())
const removeItemRow = (idx: number) => itemRows.value.splice(idx, 1)
// BOM(부품) 선택 모달 → 선택 품목을 품목 행으로 추가 (part_id 보존 → 발주서 자동생성용)
const showPartPicker = ref(false)
const onPartsPicked = (items: PickedItem[]) => {
  for (const it of items) itemRows.value.push({ ...newItemRow(), part_id: it.part_id, name: it.name, qty: 1, unit_price: it.unit_price })
  showPartPicker.value = false
}
// ── 엑셀 업로드(품목명/수량/단가/거래처/비고): 비어있으면 채우고, 있으면 추가 ──
const itemsFileInput = ref<HTMLInputElement | null>(null)
const itemsUploading = ref(false)
function downloadItemsTemplate() {
  downloadAuthedUrl('/approvals/items-template.xlsx', '구매품목_양식.xlsx')
}
async function onItemsFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''  // 같은 파일 재선택 허용
  if (!file) return
  itemsUploading.value = true
  try {
    const rows = await approvalApi.parseItems(file)
    const parsed: ItemRow[] = (rows || []).map((r: any) => ({
      name: r.name != null ? String(r.name) : '',
      qty: r.qty != null && r.qty !== '' ? Number(r.qty) : null,
      unit_price: r.unit_price != null && r.unit_price !== '' ? Number(r.unit_price) : null,
      note: r.note != null ? String(r.note) : '',
      part_id: null,  // 엑셀 업로드 품목은 BOM 링크 없음
    }))
    if (!parsed.length) { warning('엑셀에서 읽은 품목이 없습니다'); return }
    const hasContent = itemRows.value.some((r) => (r.name || '').trim() || r.qty || r.unit_price)
    if (hasContent) itemRows.value.push(...parsed)  // 있으면 뒤에 추가
    else itemRows.value = parsed                    // 비어있으면 채우기
    success(`품목 ${parsed.length}건을 불러왔습니다`)
  } catch (err: any) {
    error(err?.response?.data?.detail || '엑셀 업로드에 실패했습니다')
  } finally {
    itemsUploading.value = false
  }
}
// 단가는 통화와 무관하게 소수 2자리까지(원화 0.5원 단위 부품 등) — 발주서 단가 Numeric(15,2)와 동일
const UNIT_PRICE_DIGITS = 2
const round2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100  // 0.1×3=0.30000000000000004 같은 오차 정리
const lineAmount = (r: ItemRow) => round2((Number(r.qty) || 0) * (Number(r.unit_price) || 0))
const itemsTotal = computed(() => round2(itemRows.value.reduce((s, r) => s + lineAmount(r), 0)))
const formatMoney = (n: number) => (Number(n) || 0).toLocaleString('ko-KR')
const hasItemsField = computed(
  () => !!selectedForm.value?.fields_schema.some((f) => f.key === 'items'),
)
const hydrateItems = (raw: unknown) => {
  if (Array.isArray(raw)) {
    itemRows.value = raw.map((r) => {
      const o = (r ?? {}) as Record<string, unknown>
      return {
        name: o.name != null ? String(o.name) : '',
        qty: o.qty != null && o.qty !== '' ? Number(o.qty) : null,
        unit_price: o.unit_price != null && o.unit_price !== '' ? Number(o.unit_price) : null,
        note: o.note != null ? String(o.note) : '',
        part_id: o.part_id != null && o.part_id !== '' ? Number(o.part_id) : null,
      }
    })
  } else {
    itemRows.value = []
  }
}
// 품목 합계를 금액(amount) 필드에 자동 반영
watch(itemsTotal, (v) => { if (hasItemsField.value && itemsMode.value === 'TABLE') formData.value['amount'] = v })

// ── 출장정산서 개인경비(개인카드) 환급 섹션 (v0.57.0) ──
// 체크 시에만 항목 입력. 승인되면 이 값으로 지출결의서 초안이 자동 생성된다.
type PersonalRow = { name: string; amount: number | null }
const hasPersonal = ref(false)
const personalRows = ref<PersonalRow[]>([])
const addPersonalRow = () => personalRows.value.push({ name: '', amount: null })
const removePersonalRow = (idx: number) => personalRows.value.splice(idx, 1)
const personalTotal = computed(() => personalRows.value.reduce((s, r) => s + (Number(r.amount) || 0), 0))
const personalPayment = ref('카드결제')
const personalAccount = ref('')
const personalNote = ref('')
function togglePersonal() {
  hasPersonal.value = !hasPersonal.value
  if (hasPersonal.value && personalRows.value.length === 0) addPersonalRow()
}

// 양식
const forms = ref<ApprovalForm[]>([])
const selectedFormId = ref<number | null>(null)
const formData = ref<Record<string, any>>({})
const selectedForm = computed(() => forms.value.find((f) => f.id === selectedFormId.value) || null)
const isLeaveForm = computed(() => selectedForm.value?.code === 'LEAVE')
// 구매기안서/지출결의서 → 구매 구분·시행자 노출
const isPurchaseForm = computed(() => ['PURCHASE', 'DISBURSEMENT'].includes(selectedForm.value?.code || ''))
const isPurchaseDraft = computed(() => selectedForm.value?.code === 'PURCHASE')  // 발주서 자동생성=구매기안서만
const isDisbursementForm = computed(() => selectedForm.value?.code === 'DISBURSEMENT')  // 시행자=지출결의서만
const purchaseCategory = ref<string>('')
const PURCHASE_CATEGORIES = ['일반', '과제', '개발']

// 과제 구매기안서 — RCMS 항목·세부항목 (비목은 항목에서 자동). 저장: form_data.budget_category/item/detail
const showBudgetFields = computed(() => isPurchaseDraft.value && purchaseCategory.value === '과제')
const budgetItem = ref<string>('')
const budgetDetail = ref<string>('')
const budgetCategory = computed(() => findRcmsItem(budgetItem.value)?.category || '')
const budgetDetailOptions = computed(() => findRcmsItem(budgetItem.value)?.details || [])
// 항목을 바꾸면 그 항목에 없는 세부항목은 비운다
watch(budgetItem, () => {
  if (budgetDetail.value && !budgetDetailOptions.value.includes(budgetDetail.value)) {
    budgetDetail.value = ''
  }
})
// 실무에서는 구매 구분을 비워 두고 제목에만 "[과제/코드]"를 적는 경우가 많다(과제 문서 71건 중 17건).
// 구분이 비어 있고 제목이 "[과제"로 시작하면 '과제'로 채운다. 사용자가 직접 고른 구분은 건드리지 않는다.
watch([title, isPurchaseDraft], () => {
  if (isPurchaseDraft.value && !purchaseCategory.value && /^\s*\[과제/.test(title.value || '')) {
    purchaseCategory.value = '과제'
  }
})

const executorId = ref<number | undefined>(undefined)
// 통화(구매기안서/지출결의서 금액 표기 단위) — 저장은 form_data.currency
const currency = ref<string>('KRW')
const CURRENCY_SUFFIX: Record<string, string> = { KRW: '원', USD: 'USD', JPY: 'JPY', CNY: 'CNY', EUR: 'EUR' }
const currencySuffix = computed(() => CURRENCY_SUFFIX[currency.value] || currency.value)
// 부가세 10% 분해(원화 국내거래 기준) — 체크 시 포함가 역산, 미체크 시 별도 가산
const vatBreakdown = computed(() => {
  if (currency.value !== 'KRW') return null
  const total = itemsMode.value === 'TABLE' ? itemsTotal.value : (Number(formData.value['amount']) || 0)
  if (!total) return null
  if (vatIncluded.value) {
    const supply = Math.round(total / 1.1)
    return { supply, vat: total - supply, total }
  }
  const vat = Math.round(total * 0.1)
  return { supply: total, vat, total: total + vat }
})
// 발주서 자동 생성(구매기안서): 승인 시 BOM 품목으로 발주서(DRAFT) 생성
const autoPo = ref(false)
const poSupplierId = ref<number | undefined>(undefined)
const supplierOptions = ref<{ id: number; code: string; name_ko: string }[]>([])
const loadSuppliers = async () => {
  if (supplierOptions.value.length) return
  try {
    const res = await partnerApi.getAll({ is_supplier: true, is_active: true, limit: 500 })
    supplierOptions.value = (res.data.items || []).map((p) => ({
      id: p.id, code: p.partner_code || '', name_ko: p.partner_name,
    }))
  } catch { supplierOptions.value = [] }
}
// 휴가 유형: '반차'를 오전/오후로 세분(프론트 표시용 — 저장값은 문자열 그대로, 백엔드는 '반차' 포함이면 0.5일 차감)
const leaveTypeOptions = ['연차', '오전 반차', '오후 반차', '병가', '경조', '기타']

// 양식 칩 배치(줄 단위 그룹). 관련 양식(사전/사후)을 같은 줄로. 정의 외 신규 양식은 마지막 줄.
const FORM_LAYOUT: string[][] = [
  ['FREE'],                                  // 일반 기안서
  ['PURCHASE', 'DISBURSEMENT'],             // 구매기안서 / 지출결의서(집행)
  ['LEAVE'],                                 // 휴가 신청서
  ['TRIP', 'EXPENSE'],                       // 출장 신청서 / 출장 정산서
  ['MEETING_PLAN', 'MEETING', 'MEETING_EXPENSE'], // 회의 안건서 / 회의록 / 회의비 정산서
]
const formRows = computed(() => {
  const placed = new Set<string>()
  const rows = FORM_LAYOUT
    .map((codes) => codes.map((c) => forms.value.find((f) => f.code === c)).filter((f): f is NonNullable<typeof f> => !!f))
    .filter((r) => r.length > 0)
  rows.forEach((r) => r.forEach((f) => placed.add(f.code)))
  const rest = forms.value.filter((f) => !placed.has(f.code)) // 레이아웃에 없는 신규 양식
  if (rest.length) rows.push(rest)
  return rows
})

// ── 사후(POST) 양식: 선행문서 연결 (일반화) ──
const isExpenseForm = computed(() => selectedForm.value?.code === 'EXPENSE')
// 정산형: total_cost 필드가 있으면 정산형으로 본다 (EXPENSE / MEETING_EXPENSE)
const isSettlementForm = computed(
  () => !!selectedForm.value?.fields_schema.some((f) => f.key === 'total_cost'),
)
const isPostForm = computed(() => selectedForm.value?.phase === 'POST')
const linkablePredecessors = ref<LinkablePredecessor[]>([])
const relatedDocumentIds = ref<number[]>([])   // 다중 관련 문서(v0.55.0)
const addRelatedId = ref<number | undefined>(undefined)  // picker 임시 선택값
const predecessorsLoaded = ref(false)
const predecessorsLoadedFor = ref<string | null>(null)

// 선행문서 picker 라벨: linked_form_code 로 forms 에서 양식명 찾기
const predecessorLabel = computed(() => {
  const code = selectedForm.value?.linked_form_code
  if (!code) return '관련 문서'
  const f = forms.value.find((x) => x.code === code)
  return f ? `관련 ${f.name}` : '관련 문서'
})

// 선택된 관련 문서 목록(칩 표시용, 입력 순서 보존)
const selectedRelatedDocs = computed(() =>
  relatedDocumentIds.value
    .map((id) => linkablePredecessors.value.find((t) => t.id === id))
    .filter((t): t is LinkablePredecessor => !!t),
)
// 경비 힌트용 — 첫 선택 문서
const selectedTrip = computed(() => selectedRelatedDocs.value[0] || null)

// SearchableSelect 옵션 (이미 선택된 것은 제외)
const tripOptions = computed(() =>
  linkablePredecessors.value
    .filter((t) => !relatedDocumentIds.value.includes(t.id))
    .map((t) => ({ id: t.id, code: t.doc_number, name_ko: t.title })),
)

function onAddRelated(v: number | undefined) {
  if (v != null && !relatedDocumentIds.value.includes(v)) {
    relatedDocumentIds.value.push(v)
  }
  addRelatedId.value = undefined  // picker 초기화(연속 추가)
}
function removeRelated(id: number) {
  relatedDocumentIds.value = relatedDocumentIds.value.filter((x) => x !== id)
}

const toNum = (v: unknown): number => {
  const n = Number(v)
  return isNaN(n) ? 0 : n
}

// 정산형 합계 = 키가 `_cost`로 끝나는 number 필드(단, total_cost 제외)의 합 (일반화)
const costFieldKeys = computed(() => {
  if (!selectedForm.value) return []
  return selectedForm.value.fields_schema
    .filter((f) => f.type === 'number' && f.key.endsWith('_cost') && f.key !== 'total_cost')
    .map((f) => f.key)
})

const expenseTotal = computed(() =>
  costFieldKeys.value.reduce((sum, key) => sum + toNum(formData.value[key]), 0),
)

// 예상경비 대비 차액 (선택된 선행문서 expense 기준 — 출장정산만 해당)
const expenseDiff = computed(() => {
  if (!selectedTrip.value || selectedTrip.value.expense == null) return null
  return expenseTotal.value - selectedTrip.value.expense
})

// 정산형 양식에서 합계 자동 반영
watch(
  expenseTotal,
  (v) => {
    if (isSettlementForm.value) formData.value['total_cost'] = v
  },
)

const loadLinkablePredecessors = async (formCode: string) => {
  if (predecessorsLoaded.value && predecessorsLoadedFor.value === formCode) return
  try {
    const res = await approvalApi.getLinkablePredecessors(formCode)
    linkablePredecessors.value = res.data
  } catch {
    linkablePredecessors.value = []
  } finally {
    predecessorsLoaded.value = true
    predecessorsLoadedFor.value = formCode
  }
}

// 참조자
const selectedReferenceId = ref<number | undefined>(undefined)
const referenceIds = ref<number[]>([])

// 첨부파일
const fileInput = ref<HTMLInputElement | null>(null)
const attachments = ref<ApprovalAttachment[]>([])
const uploading = ref(false)
const pendingFiles = ref<File[]>([])   // 저장 전 첨부(문서 저장 시 업로드)
const dropOver = ref(false)

// 연차 잔여
const leaveBalance = ref<LeaveBalance | null>(null)

const approverOptions = computed(() =>
  candidates.value.map((c) => ({
    id: c.id,
    code: c.position || c.department || '',
    name_ko: c.name,
  })),
)

const candidateMap = computed(() => {
  const m = new Map<number, ApproverCandidate>()
  candidates.value.forEach((c) => m.set(c.id, c))
  return m
})

const approverLabel = (id: number) => {
  const c = candidateMap.value.get(id)
  if (!c) return `ID ${id}`
  const extra = [c.position, c.department].filter(Boolean).join(' / ')
  return extra ? `${c.name} (${extra})` : c.name
}

const formatFileSize = (bytes: number): string => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

// ── 디자인용 표시 헬퍼 (기능 변경 없음, 표시 전용) ──
const todayStr = new Date().toISOString().slice(0, 10)
// 기존 문서를 편집(특히 관리자 정정)할 때는 '현재 로그인 사용자/오늘'이 아니라
// 문서의 실제 기안자·기안일자·결재 도장 상태를 그대로 보여준다(오해 방지).
const docDrafter = ref<{ name: string; position: string; department: string } | null>(null)
const docDraftedAt = ref<string | null>(null)
const docLineStates = ref<{ step_order: number; approver_id: number; approver_name?: string | null; status?: string | null; acted_at?: string | null }[]>([])

const drafterName = computed(() => docDrafter.value?.name || auth.userName.value || '기안자')
const drafterPosition = computed(() => docDrafter.value ? (docDrafter.value.position || '') : (auth.userPosition.value || ''))
const drafterDepartment = computed(() =>
  docDrafter.value
    ? (docDrafter.value.department ? departmentLabel(docDrafter.value.department) : '')
    : (auth.userDepartment.value || ''),
)
// 기안일자: 기존 문서면 그 문서의 기안일, 신규면 오늘
const draftDateStr = computed(() => (docDraftedAt.value ? String(docDraftedAt.value).slice(0, 10) : todayStr))
const initials = (name: string) => (name ? name.slice(-2) : '··')

// 큰 제목: 선택 양식명을 자간 벌려 표시 (없으면 "기 안 서")
const paperTitle = computed(() => {
  const base = selectedForm.value?.name || '기안서'
  return base.split('').join(' ')
})

// 결재란 그리드 셀: 기안 + 결재선
const stampColumns = computed(() => {
  const cols: { label: string; name: string; done: boolean; date: string }[] = [
    { label: '기안', name: drafterName.value, done: true, date: draftDateStr.value },
  ]
  lines.value.forEach((l, i) => {
    // 기존 문서 편집이면 실제 결재 상태/처리일을 반영(승인된 칸이 '대기'로 보이지 않게)
    const st = docLineStates.value.find(
      (s) => s.step_order === l.step_order || s.approver_id === l.approver_id,
    )
    const done = !!st && (st.status === 'APPROVED' || st.status === 'REJECTED')
    cols.push({
      label: i === lines.value.length - 1 ? '승인' : '검토',
      name: candidateMap.value.get(l.approver_id)?.name || st?.approver_name || `ID ${l.approver_id}`,
      done,
      date: done && st?.acted_at ? String(st.acted_at).slice(0, 10) : '',
    })
  })
  return cols
})

// 결재선 사이드바 행 역할 라벨
const lineRole = (idx: number) =>
  idx === lines.value.length - 1 ? '승인' : (lines.value.length === 1 ? '승인' : '검토')

// ── 양식 선택 ──
const selectForm = (id: number | null, keepRelated = false) => {
  selectedFormId.value = id
  // 새 양식의 기본 키로 formData 초기화 (기존 값 보존 X — 양식 전환 시)
  const obj: Record<string, any> = {}
  const f = forms.value.find((x) => x.id === id)
  if (f) f.fields_schema.forEach((field) => { obj[field.key] = '' })
  formData.value = obj
  leaveDates.value = []  // 휴가 달력 초기화(양식 전환)
  // 양식 전환 시 참석자/품목 행 초기화
  attendeeRows.value = []
  itemRows.value = []
  itemsMode.value = 'TABLE'
  itemsFree.value = ''
  vatIncluded.value = false
  autoPo.value = false
  poSupplierId.value = undefined
  currency.value = 'KRW'
  budgetItem.value = ''
  budgetDetail.value = ''
  // 품목 표 양식이면 빈 행 1개로 시작(입력 편의)
  if (f && f.fields_schema.some((field) => field.key === 'items')) addItemRow()
  if (isLeaveForm.value) loadLeaveBalance()
  if (isPostForm.value && f) {
    loadLinkablePredecessors(f.code)
  } else if (!keepRelated) {
    relatedDocumentIds.value = []
    addRelatedId.value = undefined
  }
}

// ── 휴가 일수 자동계산 ──
const isHalfDay = (leaveType: unknown) =>
  typeof leaveType === 'string' && leaveType.includes('반차')

const computeBusinessDays = (start: string, end: string): number => {
  const s = new Date(start)
  const e = new Date(end)
  if (isNaN(s.getTime()) || isNaN(e.getTime()) || e < s) return 0
  let count = 0
  const cur = new Date(s)
  while (cur <= e) {
    const day = cur.getDay()
    if (day !== 0 && day !== 6) count++
    cur.setDate(cur.getDate() + 1)
  }
  return count
}

const recomputeLeaveDays = () => {
  if (!isLeaveForm.value) return
  const start = formData.value['start_date']
  const end = formData.value['end_date']
  if (!start || !end) return
  let days = computeBusinessDays(String(start), String(end))
  if (isHalfDay(formData.value['leave_type'])) days = 0.5
  formData.value['days'] = days
}

const onLeaveDateChange = () => recomputeLeaveDays()

// 휴가 날짜 다중선택(달력) — 선택 → form_data(dates/start/end/days) 동기화
const leaveDates = ref<string[]>([])
const _leaveDays = () => {
  if (isHalfDay(formData.value['leave_type'])) return leaveDates.value.length ? 0.5 : 0
  return leaveDates.value.length
}
watch(leaveDates, (ds) => {
  if (!isLeaveForm.value) return
  const sorted = [...ds].sort()
  formData.value['dates'] = sorted
  formData.value['start_date'] = sorted[0] || ''
  formData.value['end_date'] = sorted[sorted.length - 1] || ''
  formData.value['days'] = _leaveDays()
}, { deep: true })

// 기존 휴가 문서 로드 시 달력 초기화(dates 우선, 없으면 start~end 주중)
const initLeaveDates = () => {
  if (!isLeaveForm.value) { leaveDates.value = []; return }
  const d = formData.value['dates']
  if (Array.isArray(d) && d.length) { leaveDates.value = [...d].map(String).sort(); return }
  const s = formData.value['start_date']; const e = formData.value['end_date'] || s
  if (!s) { leaveDates.value = []; return }
  const out: string[] = []
  const cur = new Date(String(s) + 'T00:00:00'); const end = new Date(String(e) + 'T00:00:00')
  while (cur <= end) {
    const dow = cur.getDay()
    if (dow !== 0 && dow !== 6) out.push(`${cur.getFullYear()}-${String(cur.getMonth() + 1).padStart(2, '0')}-${String(cur.getDate()).padStart(2, '0')}`)
    cur.setDate(cur.getDate() + 1)
  }
  leaveDates.value = out
}

// leave_type 변경 시: 반차면 하루만 유지 + 일수 재계산
watch(
  () => formData.value['leave_type'],
  () => {
    if (!isLeaveForm.value) return
    if (isHalfDay(formData.value['leave_type']) && leaveDates.value.length > 1) {
      leaveDates.value = leaveDates.value.slice(0, 1)  // 반차: 첫 날짜만
    }
    formData.value['days'] = _leaveDays()
  },
)

// 휴가 제목 자동 생성("{휴가유형} {기안자}") — 제목 입력 없이 간편 신청
const autoLeaveTitle = () => {
  const lt = (formData.value['leave_type'] as string) || '휴가'
  return `${lt} ${drafterName.value}`.trim()
}
watch(
  [() => formData.value['leave_type'], isLeaveForm],
  (newv, oldv) => {
    const isLeave = newv[1]
    const wasLeave = oldv ? oldv[1] : false
    if (isLeave) {
      title.value = autoLeaveTitle()
    } else if (wasLeave) {
      // 휴가 → 다른 양식으로 전환: 자동 채워진 제목을 비워 사용자가 직접 입력하게 함
      title.value = ''
    }
  },
  { immediate: true },
)

const leaveOverflow = computed(() => {
  if (!isLeaveForm.value || !leaveBalance.value) return false
  const d = Number(formData.value['days'])
  return !isNaN(d) && d > leaveBalance.value.remaining
})

const loadLeaveBalance = async () => {
  try {
    const res = await approvalApi.getLeaveBalance()
    leaveBalance.value = res.data
  } catch {
    leaveBalance.value = null
  }
}

// ── 결재선 ──
const renumber = () => {
  lines.value = lines.value.map((l, i) => ({ ...l, step_order: i + 1 }))
}

const addApprover = () => {
  if (!selectedApproverId.value) return
  if (lines.value.some((l) => l.approver_id === selectedApproverId.value)) {
    warning('이미 추가된 결재자입니다')
    return
  }
  lines.value.push({ step_order: lines.value.length + 1, approver_id: selectedApproverId.value })
  selectedApproverId.value = undefined
  renumber()
}

const addManualApprover = () => {
  if (!manualApproverId.value) return
  if (lines.value.some((l) => l.approver_id === manualApproverId.value)) {
    warning('이미 추가된 결재자입니다')
    return
  }
  lines.value.push({ step_order: lines.value.length + 1, approver_id: manualApproverId.value })
  manualApproverId.value = null
  renumber()
}

const removeApprover = (idx: number) => {
  lines.value.splice(idx, 1)
  renumber()
}
const swap = (a: number, b: number) => {
  const arr = lines.value
  const tmp = arr[a]
  const other = arr[b]
  if (tmp === undefined || other === undefined) return
  arr[a] = other
  arr[b] = tmp
}
const moveUp = (idx: number) => {
  if (idx === 0) return
  swap(idx, idx - 1)
  renumber()
}
const moveDown = (idx: number) => {
  if (idx === lines.value.length - 1) return
  swap(idx, idx + 1)
  renumber()
}

// ── 결재선 드래그앤드롭 정렬 ──
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

const onDragStart = (idx: number) => {
  dragIndex.value = idx
}
const onDragOver = (idx: number) => {
  dragOverIndex.value = idx
}
const onDrop = (idx: number) => {
  const from = dragIndex.value
  if (from === null || from === idx) {
    dragIndex.value = null
    dragOverIndex.value = null
    return
  }
  const arr = lines.value.slice()
  const moved = arr.splice(from, 1)[0]
  if (moved) arr.splice(idx, 0, moved)
  lines.value = arr
  dragIndex.value = null
  dragOverIndex.value = null
  renumber()
}
const onDragEnd = () => {
  dragIndex.value = null
  dragOverIndex.value = null
}

// ── 참조자 ──
const addReference = () => {
  if (!selectedReferenceId.value) return
  if (referenceIds.value.includes(selectedReferenceId.value)) {
    warning('이미 추가된 참조자입니다')
    return
  }
  referenceIds.value.push(selectedReferenceId.value)
  selectedReferenceId.value = undefined
}
const removeReference = (id: number) => {
  referenceIds.value = referenceIds.value.filter((r) => r !== id)
}

// ── 검증 ──
const validate = (requireLines: boolean): boolean => {
  if (!title.value.trim()) {
    warning('제목을 입력하세요')
    return false
  }
  if (requireLines && lines.value.length === 0) {
    warning('결재자를 1명 이상 지정하세요')
    return false
  }
  if (requireLines && isDisbursementForm.value && !executorId.value) {
    warning('지출결의서는 시행자를 반드시 지정해야 합니다')
    return false
  }
  if (requireLines && isPurchaseDraft.value && autoPo.value) {
    if (!poSupplierId.value) {
      warning('발주서 자동 생성을 선택했으면 공급업체(발주처)를 지정하세요')
      return false
    }
    if (!itemRows.value.some((r) => r.part_id)) {
      warning('발주서 자동 생성은 BOM에서 추가한 품목이 1개 이상 필요합니다')
      return false
    }
  }
  if (requireLines && selectedForm.value) {
    for (const field of selectedForm.value.fields_schema) {
      if (field.required) {
        if (field.key === 'attendees') {
          const filled = attendeeRows.value.some(
            (r) => r.org.trim() || r.name.trim() || r.title.trim(),
          )
          if (!filled) {
            warning(`${field.label} 항목을 입력하세요`)
            return false
          }
          continue
        }
        if (field.key === 'items') {
          if (itemsMode.value === 'FREE') {
            if (!itemsFree.value.trim()) {
              warning(`${field.label}(자유형식) 내용을 입력하세요`)
              return false
            }
          } else if (!itemRows.value.some((r) => r.name.trim())) {
            warning(`${field.label}을(를) 1개 이상 입력하세요`)
            return false
          }
          continue
        }
        const v = formData.value[field.key]
        if (v === undefined || v === null || String(v).trim() === '') {
          warning(`${field.label} 항목을 입력하세요`)
          return false
        }
      }
    }
  }
  // 구매기안서: 구매 구분 필수(상신 시) — 과제 여부에 따라 RCMS 항목·세부항목 필수 여부가 갈림
  if (requireLines && isPurchaseDraft.value && !purchaseCategory.value) {
    warning('구매 구분(일반/과제/개발)을 선택하세요')
    return false
  }
  // 과제 구매기안서: RCMS 항목·세부항목 필수(상신 시)
  if (requireLines && showBudgetFields.value) {
    if (!budgetItem.value) { warning('과제 구매기안서는 항목을 선택하세요'); return false }
    if (!budgetDetail.value) { warning('과제 구매기안서는 세부항목을 선택하세요'); return false }
  }
  // 출장정산서 개인경비 환급: 체크했으면 항목 1개 이상 + 입금계좌 필수(상신 시)
  if (requireLines && isSettlementForm.value && hasPersonal.value) {
    if (!personalRows.value.some((r) => r.name.trim() && (Number(r.amount) || 0) > 0)) {
      warning('개인경비 항목(내역/금액)을 1개 이상 입력하세요')
      return false
    }
    if (!personalAccount.value.trim()) {
      warning('환급받을 입금 계좌를 입력하세요')
      return false
    }
  }
  return true
}

// ── 저장 ──
// 양식에 attendees 필드가 있으면 구조화 행을 객체 배열로 직렬화
const buildFormData = (): Record<string, any> | null => {
  if (!selectedFormId.value) return null
  const data = { ...formData.value }
  if (hasAttendeesField.value) {
    data['attendees'] = attendeeRows.value
      .filter((r) => r.org.trim() || r.name.trim() || r.title.trim())
      .map((r) => ({ org: r.org.trim(), name: r.name.trim(), title: r.title.trim() }))
  }
  if (hasItemsField.value) {
    data['items_mode'] = itemsMode.value
    data['vat_included'] = vatIncluded.value   // 부가세 포함(true)/별도(false)
    if (itemsMode.value === 'FREE') {
      data['items_free'] = itemsFree.value.trim()
      data['items'] = []
      data['amount'] = Number(formData.value['amount']) || 0  // 자유형식: 총액 직접 입력값
    } else {
      data['items_free'] = ''
      data['items'] = itemRows.value
        .filter((r) => r.name.trim() || r.qty || r.unit_price || (r.note || '').trim())
        .map((r) => ({ name: r.name.trim(), qty: Number(r.qty) || 0, unit_price: Number(r.unit_price) || 0, note: (r.note || '').trim(), part_id: r.part_id ?? null, amount: lineAmount(r) }))
      data['amount'] = itemsTotal.value
    }
  }
  // 구매기안서: 발주서 자동 생성 여부 + 공급업체(승인 시 백엔드가 BOM 품목으로 발주서 생성)
  // 자유형식(FREE)은 part_id가 없어 발주서 생성 불가 → 강제 off
  if (isPurchaseDraft.value) {
    const effAutoPo = itemsMode.value === 'TABLE' && autoPo.value
    data['auto_po'] = effAutoPo
    data['po_supplier_id'] = effAutoPo ? (poSupplierId.value ?? null) : null
  }
  // 통화(구매기안서/지출결의서) — 금액 표기 단위 저장
  if (isPurchaseForm.value) data['currency'] = currency.value
  // 과제 구매기안서 RCMS 항목 — 과제가 아니면 남아 있던 값을 지운다(구분을 바꾼 경우)
  if (showBudgetFields.value) {
    data['budget_category'] = budgetCategory.value || null
    data['budget_item'] = budgetItem.value || null
    data['budget_detail'] = budgetDetail.value || null
  } else {
    delete data['budget_category']
    delete data['budget_item']
    delete data['budget_detail']
  }
  // 출장정산서 개인카드 환급(v0.57.0) — 승인 시 지출결의서 자동생성 재료
  if (isSettlementForm.value) {
    if (hasPersonal.value) {
      data['has_personal'] = true
      data['personal_expenses'] = personalRows.value
        .filter((r) => r.name.trim() || r.amount)
        .map((r) => ({ name: r.name.trim(), amount: Number(r.amount) || 0 }))
      data['personal_total'] = personalTotal.value
      data['personal_payment_method'] = personalPayment.value
      data['personal_account'] = personalAccount.value.trim()
      data['personal_note'] = personalNote.value.trim()
    } else {
      data['has_personal'] = false
    }
  }
  return data
}

const buildPayload = () => ({
  title: title.value.trim(),
  content: content.value,
  lines: lines.value,
  form_id: selectedFormId.value,
  form_data: buildFormData(),
  reference_ids: referenceIds.value,
  related_document_ids: isPostForm.value ? relatedDocumentIds.value : null,
  project_id: isLeaveForm.value ? null : (projectId.value ?? null),
  purchase_category: isPurchaseForm.value ? (purchaseCategory.value || null) : null,
  executor_id: isDisbursementForm.value ? (executorId.value ?? null) : null,
})

const persist = async (): Promise<number | null> => {
  const payload = buildPayload()
  let id: number
  if (isEdit.value && docId.value) {
    await approvalApi.update(docId.value, payload)
    id = docId.value
  } else {
    const res = await approvalApi.create(payload)
    id = res.data.id
  }
  await uploadPendingFiles(id)   // 저장 전 첨부한 파일 업로드
  return id
}

const saveDraft = async () => {
  if (!validate(false)) return
  saving.value = true
  try {
    const wasNew = !docId.value
    const id = await persist()
    success('임시저장되었습니다')
    if (id) {
      // 신규였다면 첨부 가능하도록 편집 모드로 전환 (라우트 + 상태)
      docId.value = id
      if (wasNew) router.replace(`/approvals/${id}/edit`)
      await loadAttachments()
    }
  } catch {
    error('저장에 실패했습니다')
  } finally {
    saving.value = false
  }
}

const submitDocument = async () => {
  if (!validate(true)) return
  saving.value = true
  try {
    const id = await persist()
    if (!id) throw new Error('no id')
    // 상신 실패 시 재시도가 create 를 또 호출해 유령 DRAFT 를 만들지 않도록 id 를 기억
    // (route 이동은 하지 않음 — 성공 시 곧바로 상세로 이동하므로 불필요한 이중 내비게이션 방지)
    docId.value = id
    await approvalApi.submit(id)
    success('상신되었습니다')
    router.push(`/approvals/${id}`)
  } catch {
    error('상신에 실패했습니다')
  } finally {
    saving.value = false
  }
}

// 상신 후(진행중·미승인) 문서 수정 저장 — 상태 유지(1차부터 다시 결재), 상세로 복귀
const saveEdit = async () => {
  if (!validate(true)) return
  saving.value = true
  try {
    const id = await persist()
    if (!id) throw new Error('no id')
    success('수정되었습니다')
    router.push(`/approvals/${id}`)
  } catch {
    error('수정에 실패했습니다')
  } finally {
    saving.value = false
  }
}

// [관리자] 전체 정정 저장 — 상태·결재선(승인/도장) 보존, 문서 내용 전체 교체 + 정정 이력 기록
const adminFullSave = async () => {
  if (!validate(false)) return
  if (!docId.value) return
  const reason = window.prompt('정정 사유를 입력하세요 (필수)')
  if (reason === null) return
  if (!reason.trim()) { warning('정정 사유는 필수입니다'); return }
  saving.value = true
  try {
    await approvalApi.adminFullEdit(docId.value, { ...buildPayload(), reason: reason.trim() })
    await uploadPendingFiles(docId.value)
    success('정정 저장되었습니다')
    router.push(`/approvals/${docId.value}`)
  } catch {
    error('정정 저장에 실패했습니다')
  } finally {
    saving.value = false
  }
}

// 인쇄 미리보기 — 현재 편집 내용을 저장한 뒤 인쇄용 HTML을 새 창에서 표시
const previewDocument = async () => {
  if (!validate(false)) return
  saving.value = true
  try {
    if (!docId.value) {
      const id = await persist()   // 신규 → 초안 저장
      if (id) docId.value = id
    } else if (!isRejectedEdit.value) {
      await persist()              // 편집 저장(반려는 update 불가 → 마지막 저장본으로 미리보기)
    }
  } catch {
    /* 저장 실패해도 마지막 저장본으로 미리보기 시도 */
  } finally {
    saving.value = false
  }
  if (!docId.value) {
    warning('미리보기하려면 제목 등 필수 항목 입력 후 저장이 필요합니다')
    return
  }
  try {
    const res = await approvalApi.getPrintHtml(docId.value)
    const html = res.data as unknown as string
    const win = window.open('', '_blank')
    if (!win) { warning('팝업이 차단되었습니다. 팝업을 허용해주세요'); return }
    win.document.open(); win.document.write(html); win.document.close(); win.focus()
  } catch {
    error('미리보기에 실패했습니다')
  }
}

// 반려 문서 수정 후 재상신 — 편집 내용을 담아 resubmit(1차부터 새 결재 사이클)
const resubmitEdit = async () => {
  if (!validate(true)) return
  if (!docId.value) return
  saving.value = true
  try {
    await approvalApi.resubmit(docId.value, buildPayload())
    success('재상신되었습니다')
    router.push(`/approvals/${docId.value}`)
  } catch {
    error('재상신에 실패했습니다')
  } finally {
    saving.value = false
  }
}

// ── 첨부 ──
const loadAttachments = async () => {
  if (!docId.value) return
  try {
    const res = await approvalApi.listAttachments(docId.value)
    attachments.value = res.data
  } catch {
    attachments.value = []
  }
}

// 파일 처리: 저장된 문서면 즉시 업로드, 아직 저장 전이면 대기목록에 담아 저장 시 업로드
const handleFiles = async (files: FileList | File[] | null) => {
  const list = files ? Array.from(files) : []
  if (!list.length) return
  if (docId.value) {
    uploading.value = true
    try {
      for (const f of list) await approvalApi.uploadAttachment(docId.value, f)
      success(`파일 ${list.length}개가 첨부되었습니다`)
      await loadAttachments()
    } catch {
      error('첨부에 실패했습니다')
    } finally {
      uploading.value = false
    }
  } else {
    pendingFiles.value.push(...list)   // 저장 전 → 대기(저장 시 업로드)
  }
}
const onFileSelected = async (e: Event) => {
  const input = e.target as HTMLInputElement
  await handleFiles(input.files)
  if (fileInput.value) fileInput.value.value = ''  // 같은 파일 재선택 허용
}
const onDropFiles = async (e: DragEvent) => {
  dropOver.value = false
  await handleFiles(e.dataTransfer?.files ?? null)
}
// 문서 저장 후 대기 첨부 일괄 업로드
const uploadPendingFiles = async (id: number) => {
  if (!pendingFiles.value.length) return
  const files = pendingFiles.value.splice(0)
  for (const f of files) {
    try { await approvalApi.uploadAttachment(id, f) } catch { /* best-effort */ }
  }
}

// 첨부 열어보기 (새 탭 — Bearer 인증 유지 blob 방식)
const openAttachment = async (att: { id: number; original_name: string; content_type?: string | null }) => {
  if (!docId.value) return
  try {
    const res = await approvalApi.downloadAttachment(docId.value, att.id)
    const blob = new Blob([res.data as BlobPart], att.content_type ? { type: att.content_type } : undefined)
    const url = window.URL.createObjectURL(blob)
    window.open(url, '_blank')
    setTimeout(() => window.URL.revokeObjectURL(url), 60_000)
  } catch {
    error('파일을 열지 못했습니다')
  }
}

// ── 앱 내 미리보기 모달 ──
type AttLike = { id: number; original_name: string; content_type?: string | null }
const attKind = (att: AttLike): 'image' | 'pdf' | 'other' => {
  const ct = (att.content_type || '').toLowerCase()
  const ext = (att.original_name.split('.').pop() || '').toLowerCase()
  if (ct.startsWith('image/') || ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'].includes(ext)) return 'image'
  if (ct === 'application/pdf' || ext === 'pdf') return 'pdf'
  return 'other'
}
const previewOpen = ref(false)
const previewUrl = ref('')
const previewKind = ref<'image' | 'pdf' | 'other'>('other')
const previewName = ref('')
const previewLoading = ref(false)
let previewAtt: AttLike | null = null

const openPreview = async (att: AttLike) => {
  if (!docId.value) return
  previewAtt = att
  previewName.value = att.original_name
  previewKind.value = attKind(att)
  previewLoading.value = true
  previewOpen.value = true
  try {
    const res = await approvalApi.downloadAttachment(docId.value, att.id)
    const blob = new Blob([res.data as BlobPart], att.content_type ? { type: att.content_type } : undefined)
    if (previewUrl.value) window.URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = window.URL.createObjectURL(blob)
  } catch {
    error('미리보기를 불러오지 못했습니다')
    previewOpen.value = false
  } finally {
    previewLoading.value = false
  }
}
const closePreview = () => {
  previewOpen.value = false
  if (previewUrl.value) { window.URL.revokeObjectURL(previewUrl.value); previewUrl.value = '' }
}
const previewDownload = () => { if (previewAtt) openAttachment(previewAtt) }

const removeAttachment = async (aid: number) => {
  if (!docId.value) return
  if (!confirm('첨부파일을 삭제하시겠습니까?')) return
  try {
    await approvalApi.deleteAttachment(docId.value, aid)
    await loadAttachments()
  } catch (err: any) {
    error(err?.response?.data?.detail?.message || '삭제에 실패했습니다')
  }
}

// ── 로드 ──
const loadForms = async () => {
  try {
    const res = await approvalApi.getForms()
    forms.value = [...res.data].sort((a, b) => a.sort_order - b.sort_order)
  } catch {
    forms.value = []
  }
}

const loadProjects = async () => {
  try {
    const res = await approvalApi.getProjects()
    projects.value = res.data
  } catch {
    projects.value = []
  }
}

const loadCandidates = async () => {
  try {
    const res = await approvalApi.getApprovers()
    candidates.value = res.data
  } catch {
    candidates.value = []
  }
}

const loadExisting = async () => {
  if (!docId.value) return
  loading.value = true
  try {
    const res = await approvalApi.getById(docId.value)
    const doc = res.data
    const anyApproved = (doc.lines || []).some((l: any) => l.status === 'APPROVED')
    const editable = doc.status === 'DRAFT'
      || doc.status === 'REJECTED'
      || (doc.status === 'IN_PROGRESS' && !anyApproved)
    // 관리자 전체수정 모드는 상태와 무관하게 편집 허용(승인·완료 포함)
    if (!editable && !adminMode.value) {
      warning('임시저장·반려·진행중(미승인) 문서만 수정할 수 있습니다')
      router.replace(`/approvals/${doc.id}`)
      return
    }
    editingStatus.value = doc.status
    // 표시용: 문서의 실제 기안자·기안일자·결재 도장 상태(현재 로그인 사용자로 덮어쓰지 않음)
    docDrafter.value = {
      name: doc.drafter_name || '',
      position: doc.drafter_position || '',
      department: doc.drafter_department || '',
    }
    docDraftedAt.value = doc.drafted_at || doc.created_at || null
    docLineStates.value = (doc.lines || []).map((l: any) => ({
      step_order: l.step_order,
      approver_id: l.approver_id,
      approver_name: l.approver_name,
      status: l.status,
      acted_at: l.acted_at,
    }))
    purchaseCategory.value = doc.purchase_category || ''
    executorId.value = doc.executor_id ?? undefined
    title.value = doc.title
    content.value = doc.content || ''
    lines.value = doc.lines
      .slice()
      .sort((a, b) => a.step_order - b.step_order)
      .map((l, i) => ({ step_order: i + 1, approver_id: l.approver_id }))
    referenceIds.value = (doc.references || []).map((r) => r.user_id)
    projectId.value = doc.project_id ?? null
    selectedFormId.value = doc.form_id ?? null
    if (doc.form_id) {
      // 양식 키 초기화 후 기존 값 주입
      const f = forms.value.find((x) => x.id === doc.form_id)
      const obj: Record<string, any> = {}
      if (f) f.fields_schema.forEach((field) => { obj[field.key] = '' })
      if (doc.form_data) Object.assign(obj, doc.form_data)
      formData.value = obj
      currency.value = String((doc.form_data as any)?.['currency'] || 'KRW')
      initLeaveDates()  // 휴가: 달력 선택 복원(dates 또는 start~end)
      // 참석자 필드 복원 (배열=구조화 / 문자열=레거시)
      if (f && f.fields_schema.some((field) => field.key === 'attendees')) {
        hydrateAttendees(doc.form_data ? doc.form_data['attendees'] : null)
      } else {
        attendeeRows.value = []
      }
      // 품목 복원 (모드 + 표/자유형식)
      if (f && f.fields_schema.some((field) => field.key === 'items')) {
        const fd = doc.form_data || {}
        itemsMode.value = fd['items_mode'] === 'FREE' ? 'FREE' : 'TABLE'
        itemsFree.value = String(fd['items_free'] || '')
        vatIncluded.value = !!fd['vat_included']
        hydrateItems(fd['items'])
        // 발주서 자동생성 설정 복원(구매기안서)
        autoPo.value = !!fd['auto_po']
        poSupplierId.value = fd['po_supplier_id'] != null ? Number(fd['po_supplier_id']) : undefined
        if (autoPo.value) loadSuppliers()
        // 과제 구매기안서 RCMS 항목·세부항목 복원
        budgetItem.value = String(fd['budget_item'] || '')
        budgetDetail.value = String(fd['budget_detail'] || '')
      } else {
        itemRows.value = []
        itemsMode.value = 'TABLE'
        itemsFree.value = ''
        vatIncluded.value = false
      }
      // 출장정산서 개인경비 복원(v0.57.0)
      if (f && f.code === 'EXPENSE') {
        const fd = doc.form_data || {}
        hasPersonal.value = !!fd['has_personal']
        const pe = fd['personal_expenses']
        personalRows.value = Array.isArray(pe)
          ? pe.map((r: any) => ({ name: r?.name ?? '', amount: r?.amount != null ? Number(r.amount) : null }))
          : []
        personalPayment.value = String(fd['personal_payment_method'] ?? '') || '카드결제'
        personalAccount.value = String(fd['personal_account'] ?? '')
        personalNote.value = String(fd['personal_note'] ?? '')
      }
      if (isLeaveForm.value) loadLeaveBalance()
      if (isPostForm.value && f) {
        await loadLinkablePredecessors(f.code)
        const rd = (doc as any).related_documents
        relatedDocumentIds.value = Array.isArray(rd) && rd.length
          ? rd.map((d: any) => d.id)
          : (doc.related_document_id ? [doc.related_document_id] : [])
      }
    }
    await loadAttachments()
  } catch {
    error('문서를 불러오지 못했습니다')
    router.replace('/approvals')
  } finally {
    loading.value = false
  }
}

// ── 쿼리 프리필 (사전문서의 [후속 작성] 버튼에서 진입) ──
const applyQueryPrefill = async () => {
  if (isEdit.value) return
  const formCode = typeof route.query.form === 'string' ? route.query.form : null
  const relatedRaw = typeof route.query.related === 'string' ? route.query.related : null
  if (!formCode) return
  const f = forms.value.find((x) => x.code === formCode)
  if (!f) return
  // related 를 먼저 설정해 selectForm(POST) 에서 보존되도록 함
  const relatedId = relatedRaw ? Number(relatedRaw) : NaN
  if (!isNaN(relatedId)) relatedDocumentIds.value = [relatedId]
  selectForm(f.id, true)
  // picker 후보 로드 (selectForm 에서 이미 트리거되지만 await 보장)
  if (isPostForm.value) await loadLinkablePredecessors(f.code)
  // 후속 작성: 선행(이전 안건) 문서 내용을 기본값으로 불러오기
  if (!isNaN(relatedId)) await prefillFromPredecessor(relatedId)
}

// 후속 문서 작성 시, 연결된 선행 문서의 내용을 현재 양식에 맞춰 기본값으로 채움
const prefillFromPredecessor = async (relatedId: number) => {
  try {
    const res = await approvalApi.getById(relatedId)
    const pred: any = res.data
    if (!pred) return
    if (!title.value.trim()) title.value = pred.title || ''
    if (projectId.value == null && pred.project_id != null) projectId.value = pred.project_id
    if (!content.value && pred.content) content.value = pred.content
    // 결재선 복사: 현재 결재선이 비어있을 때만 선행문서의 결재자들을 복사.
    // (지출결의서는 선행 구매기안의 결재선(대표)을 쓰지 않고 '집행 담당'을 자동 채움 → §seedDisbursementApprovers)
    if (selectedForm.value?.code !== 'DISBURSEMENT'
        && lines.value.length === 0 && Array.isArray(pred.lines) && pred.lines.length) {
      lines.value = [...pred.lines]
        .sort((a: any, b: any) => a.step_order - b.step_order)
        .map((l: any, i: number) => ({ step_order: i + 1, approver_id: l.approver_id }))
    }
    const predData = (pred.form_data || {}) as Record<string, unknown>
    if (selectedForm.value) {
      for (const field of selectedForm.value.fields_schema) {
        const cur = formData.value[field.key]
        if (predData[field.key] !== undefined && (cur === undefined || cur === '' || cur === null)) {
          formData.value[field.key] = predData[field.key]
        }
      }
      if (predData['attendees'] !== undefined) hydrateAttendees(predData['attendees'])
      if (predData['items'] !== undefined || predData['items_mode'] !== undefined) {
        itemsMode.value = predData['items_mode'] === 'FREE' ? 'FREE' : 'TABLE'
        itemsFree.value = String(predData['items_free'] || '')
        if (predData['vat_included'] !== undefined) vatIncluded.value = !!predData['vat_included']
        hydrateItems(predData['items'])
      }
      if (predData['currency'] !== undefined) currency.value = String(predData['currency']) || 'KRW'
    }
  } catch {
    /* 선행 문서 로드 실패 시 빈 양식 유지 */
  }
}

// 새 기안: 기안자의 디폴트 결재자(1차→2차)를 결재선에 자동 추가 (v0.42.0)
// 수정/후속(선행 복사)으로 이미 결재선이 있으면 건드리지 않음.
const seedDefaultApprovers = () => {
  if (isEdit.value || lines.value.length > 0) return
  const u = auth.user.value
  const ids = [u?.approver_id, u?.approver2_id].filter(
    (v): v is number => typeof v === 'number' && v > 0,
  )
  const uniq = [...new Set(ids)]
  if (uniq.length === 0) return
  lines.value = uniq.map((id, i) => ({ step_order: i + 1, approver_id: id }))
}

// 새 기안 기본 양식: FREE('일반 기안서'). 양식 미선택('일반 기안')을 FREE로 통합(v0.44.0).
const seedDefaultForm = () => {
  if (isEdit.value || selectedFormId.value !== null) return  // 수정/쿼리프리필로 이미 선택된 경우 제외
  const free = forms.value.find((f) => f.code === 'FREE')
  if (free) selectForm(free.id)
}

// 휴가(LEAVE): 기안자에게 지정된 휴가 전용 결재선/참조자를 자동 채움 (v0.51.0)
// 결재선이 비어있을 때만 채우며, 미지정이면 그대로 두어 이후 seedDefaultApprovers 가 기본 결재자로 폴백.
const seedLeaveApprovers = () => {
  if (isEdit.value) return
  if (selectedForm.value?.code !== 'LEAVE') return
  const u = auth.user.value
  if (lines.value.length === 0) {
    const ids = (u?.leave_approver_ids ?? []).filter(
      (v): v is number => typeof v === 'number' && v > 0,
    )
    const uniq = [...new Set(ids)]
    if (uniq.length > 0) lines.value = uniq.map((id, i) => ({ step_order: i + 1, approver_id: id }))
  }
  if (referenceIds.value.length === 0) {
    const refs = (u?.leave_reference_ids ?? []).filter(
      (v): v is number => typeof v === 'number' && v > 0,
    )
    if (refs.length > 0) referenceIds.value = [...new Set(refs)]
  }
}

// 지출결의서: 관리자가 지정한 '집행 담당'을 결재선에 자동 채움 (v0.49.0)
const seedDisbursementApprovers = async () => {
  if (isEdit.value) return
  if (selectedForm.value?.code !== 'DISBURSEMENT') return
  if (lines.value.length > 0) return  // 이미 채워졌으면(사용자/복사) 건드리지 않음
  try {
    const aps = await settingsApi.getDisbursementApprovers()
    if (aps.length) lines.value = aps.map((a, i) => ({ step_order: i + 1, approver_id: a.id }))
  } catch { /* 미지정 시 기본 결재자 폴백 */ }
}

onMounted(async () => {
  await Promise.all([loadForms(), loadCandidates(), loadProjects()])
  await loadExisting()
  await applyQueryPrefill()
  seedDefaultForm()
  await seedDisbursementApprovers()
  seedLeaveApprovers()
  seedDefaultApprovers()
})
</script>

<style scoped>
/* Pretendard는 이 화면 루트에만 적용 (앱 전역 폰트 미변경) */
.aw-root {
  --accent: #2f6fed;
  --accent-soft: #eaf1fe;
  font-family: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  min-height: 100vh;
  background: #f4f5f7;
  color: #1a1d24;
  -webkit-font-smoothing: antialiased;
}
.aw-root *,
.aw-root *::before,
.aw-root *::after { box-sizing: border-box; }
.aw-root ::placeholder { color: #aeb3bd; }

/* ===== TOP BAR ===== */
.aw-topbar {
  position: sticky; top: 0; z-index: 30;
  display: flex; align-items: center; justify-content: space-between;
  height: 60px; padding: 0 28px;
  background: #fff; border-bottom: 1px solid #e7e9ee;
}
.aw-topbar-left { display: flex; align-items: center; gap: 18px; }
.aw-brand { display: flex; align-items: center; gap: 10px; }
.aw-logo {
  width: 26px; height: 26px; border-radius: 7px; background: var(--accent);
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 13px; font-weight: 800;
}
.aw-sysname { font-weight: 700; font-size: 15px; color: #15181e; letter-spacing: -0.02em; }
.aw-divider { width: 1px; height: 18px; background: #e7e9ee; }
.aw-crumb { display: flex; align-items: center; gap: 9px; font-size: 13px; color: #9298a3; }
.aw-crumb-link { color: #9298a3; text-decoration: none; }
.aw-crumb-link:hover { color: #5b616b; }
.aw-crumb-sep { color: #cfd3da; }
.aw-crumb-current { color: #15181e; font-weight: 600; }

.aw-topbar-right { display: flex; align-items: center; gap: 8px; }
.aw-btn {
  height: 36px; border-radius: 8px; cursor: pointer; font-size: 13.5px;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background 0.12s, border-color 0.12s, filter 0.12s;
}
.aw-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.aw-btn-ghost { padding: 0 14px; border: none; background: transparent; color: #5b616b; font-weight: 600; }
.aw-btn-ghost:hover:not(:disabled) { background: #f2f3f5; }
.aw-btn-secondary { padding: 0 16px; border: 1px solid #d8dbe1; background: #fff; color: #2b2f37; font-weight: 600; }
.aw-btn-secondary:hover:not(:disabled) { background: #f7f8fa; border-color: #c8ccd3; }
.aw-btn-primary {
  padding: 0 18px; border: none; background: var(--accent); color: #fff; font-weight: 700;
  box-shadow: 0 1px 2px rgba(16,24,40,0.14);
}
.aw-btn-primary:hover:not(:disabled) { filter: brightness(0.95); }

.aw-loading { padding: 40px; text-align: center; color: #9aa0ab; }

/* ===== BODY ===== */
.aw-body {
  display: flex; gap: 24px; align-items: flex-start;
  max-width: 1340px; margin: 0 auto; padding: 26px 28px 64px;
}
.aw-main { flex: 1; min-width: 0; }

/* status row */
.aw-status-row {
  display: flex; align-items: center; justify-content: space-between;
  margin: 0 2px 14px;
}
.aw-status-left { display: flex; align-items: center; gap: 9px; }
.aw-status-chip {
  display: inline-flex; align-items: center; gap: 7px;
  height: 26px; padding: 0 11px; border-radius: 7px;
  background: #fff6e5; color: #b06b00; font-size: 12.5px; font-weight: 700;
}
.aw-status-dot { width: 6px; height: 6px; border-radius: 50%; background: #b06b00; }
.aw-docno { font-size: 12.5px; color: #9aa0ab; letter-spacing: -0.01em; }

/* ===== PAPER ===== */
.aw-paper {
  background: #fff; border: 1px solid #e7e9ee; border-radius: 14px;
  box-shadow: 0 1px 3px rgba(16,24,40,0.05); overflow: hidden;
}
.aw-paper-header {
  padding: 30px 48px 26px; border-bottom: 1px solid #eef0f3;
  display: flex; flex-direction: column;
}

/* approval stamp grid */
.aw-stamp-grid {
  align-self: flex-end; display: flex; margin-bottom: 20px;
  border: 1px solid #d9dde3; border-radius: 8px; overflow: hidden;
}
.aw-stamp-label {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;
  width: 26px; background: #f6f7f9; border-right: 1px solid #e2e6eb;
  font-size: 11px; font-weight: 700; color: #6b717b; letter-spacing: 0.04em;
}
.aw-stamp-col { display: flex; flex-direction: column; width: 78px; border-right: 1px solid #e9ecf0; }
.aw-stamp-col:last-child { border-right: none; }
.aw-stamp-col-label {
  height: 24px; display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; color: #6b717b;
  background: #f6f7f9; border-bottom: 1px solid #e9ecf0;
}
.aw-stamp-box { height: 62px; display: flex; align-items: center; justify-content: center; }
.aw-stamp-mark {
  min-width: 40px; max-width: 60px; height: 40px; padding: 0 4px;
  border-radius: 50%; border: 1.6px solid var(--accent);
  display: flex; align-items: center; justify-content: center;
  color: var(--accent); font-size: 12px; font-weight: 800;
  transform: rotate(-9deg); letter-spacing: -0.03em; white-space: nowrap; overflow: hidden;
}
.aw-stamp-wait { color: #c2c7cf; font-size: 11px; font-weight: 600; }
.aw-stamp-foot {
  height: 22px; display: flex; align-items: center; justify-content: center;
  font-size: 10.5px; color: #9aa0ab; border-top: 1px solid #f0f2f4;
  padding: 0 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.aw-stamp-foot-wait { color: #bcc1c9; }

.aw-paper-title-wrap { text-align: center; padding-top: 2px; }
.aw-paper-title {
  margin: 0; font-size: 30px; font-weight: 800;
  letter-spacing: 0.42em; text-indent: 0.42em; color: #13161c; white-space: nowrap;
}
.aw-paper-subtitle {
  margin-top: 11px; font-size: 11.5px; color: #a7adb6;
  letter-spacing: 0.16em; font-weight: 600;
}

/* meta table */
.aw-meta-wrap { padding: 26px 48px 4px; }
.aw-meta-grid {
  display: grid; grid-template-columns: 106px 1fr 106px 1fr;
  border-top: 1px solid #ebedf0; border-left: 1px solid #ebedf0;
  border-radius: 9px; overflow: hidden;
}
.aw-meta-label {
  padding: 11px 14px; background: #fafbfc;
  border-right: 1px solid #ebedf0; border-bottom: 1px solid #ebedf0;
  font-size: 12.5px; font-weight: 600; color: #5b616b;
  display: flex; align-items: center;
}
.aw-meta-value {
  padding: 11px 14px; border-right: 1px solid #ebedf0; border-bottom: 1px solid #ebedf0;
  font-size: 13px; color: #2b2f37; display: flex; align-items: center; min-width: 0;
}
.aw-meta-value-input { padding: 5px 8px; }
.aw-meta-sub { color: #9aa0ab; margin-left: 6px; font-size: 12px; }
.aw-req { color: #cf3b2f; }

.aw-inline-input, .aw-inline-select {
  width: 100%; border: 1px solid transparent; background: transparent;
  padding: 6px 8px; font-size: 13px; color: #2b2f37; border-radius: 7px; outline: none;
  font-family: inherit;
}
.aw-inline-input:hover, .aw-inline-select:hover { background: #f6f7f9; }
.aw-inline-input:focus, .aw-inline-select:focus { border-color: var(--accent); background: #fff; }
.aw-title-input { font-size: 15px; font-weight: 600; color: #15181e; padding: 8px; }

.aw-proj-add { display: flex; gap: 6px; width: 100%; align-items: center; }
.aw-add-proj-link {
  margin-top: 8px; border: none; background: transparent; cursor: pointer;
  color: var(--accent); font-size: 12.5px; font-weight: 600; padding: 2px 4px;
}

/* sections inside paper */
.aw-section { padding: 0 48px; }
.aw-section-last { padding-bottom: 40px; }
.aw-section-label {
  font-size: 12.5px; font-weight: 700; color: #5b616b; margin: 24px 0 12px;
}
.aw-content-box {
  border: 1px solid #ebedf0; border-radius: 11px; padding: 14px 16px; min-height: 300px;
}

.aw-field { margin-bottom: 14px; }
.aw-field-label { display: block; font-size: 12.5px; font-weight: 600; color: #5b616b; margin-bottom: 6px; }
.aw-field-help { margin-top: 6px; font-size: 11.5px; color: #9aa0ab; }
.aw-rel-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.aw-rel-chip { display: inline-flex; align-items: center; gap: 6px; max-width: 100%;
  padding: 4px 8px; font-size: 12px; background: #eef2ff; color: #3730a3;
  border: 1px solid #c7d2fe; border-radius: 9999px; }
.aw-rel-chip-txt { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 320px; }
.aw-rel-chip-x { border: none; background: transparent; color: #6366f1; cursor: pointer;
  font-size: 15px; line-height: 1; padding: 0; }
.aw-rel-chip-x:hover { color: #3730a3; }
.aw-personal { border: 1px dashed #cbd5e1; border-radius: 8px; padding: 12px; background: #f8fafc; }
.aw-personal-toggle { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: #334155; cursor: pointer; }
.aw-personal-toggle input { width: 16px; height: 16px; }
.aw-personal-body { margin-top: 10px; display: flex; flex-direction: column; gap: 10px; }
.aw-personal-row { grid-template-columns: 1fr 140px 32px; }
.aw-personal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
@media (max-width: 640px) { .aw-personal-grid { grid-template-columns: 1fr; } }
.aw-strong { font-weight: 600; color: #5b616b; }
.aw-text-red { color: #cf3b2f; }
.aw-text-green { color: #1f9d6b; }

.aw-input {
  width: 100%; padding: 9px 12px; border: 1px solid #d8dbe1; border-radius: 9px;
  font-size: 13.5px; color: #2b2f37; background: #fff; outline: none; font-family: inherit;
  transition: border-color 0.12s;
}
.aw-input:focus { border-color: var(--accent); }
.aw-input-readonly { background: #f6f7f9; color: #5b616b; }
/* 숫자 입력(수량/단가) 증감 화살표(스피너) 숨김 */
.aw-input[type="number"]::-webkit-outer-spin-button,
.aw-input[type="number"]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.aw-input[type="number"] { -moz-appearance: textfield; appearance: textfield; }
.aw-textarea { resize: vertical; line-height: 1.6; }

/* 청구 금액 + 통화 선택 (구매기안서/지출결의서) */
.aw-amount-row { display: flex; gap: 8px; align-items: center; }
.aw-amount-row .aw-input:first-child { flex: 1; }
.aw-cur-select { width: 108px; flex: 0 0 auto; padding-left: 10px; padding-right: 8px; font-weight: 600; }

.aw-attendees { display: flex; flex-direction: column; gap: 8px; }
.aw-attendee-row { display: flex; gap: 8px; align-items: center; }
.aw-attendee-actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }

/* 품목 표 */
.aw-items { display: flex; flex-direction: column; gap: 6px; }
.aw-items-mode { display: inline-flex; border: 1px solid #d7dbe2; border-radius: 8px; overflow: hidden; align-self: flex-start; margin-bottom: 2px; }
.aw-mode-btn { padding: 5px 12px; font-size: 12px; color: #5b616b; background: #fff; border: none; cursor: pointer; }
.aw-mode-btn + .aw-mode-btn { border-left: 1px solid #d7dbe2; }
.aw-mode-btn.aw-mode-on { background: var(--accent, #2f6fed); color: #fff; font-weight: 600; }
.aw-items-row { display: grid; grid-template-columns: 1.4fr 60px 96px 1fr 104px 24px; gap: 6px; align-items: center; }
.aw-items-head { font-size: 11.5px; color: #9298a3; font-weight: 600; padding: 0 2px; }
.aw-items-head span { text-align: left; }
.aw-item-amount { text-align: right; font-variant-numeric: tabular-nums; color: #3a3f49; font-size: 12.5px; padding-right: 2px; }
.aw-items-total { margin-left: auto; font-weight: 700; color: #15181e; }
/* 부가세 포함/별도 */
.aw-vat { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 12px; margin: 2px 0 4px; }
.aw-vat-check { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: #3a3f49; cursor: pointer; user-select: none; }
.aw-vat-check input { width: 15px; height: 15px; accent-color: var(--accent, #2f6fed); cursor: pointer; }
.aw-vat-tag { font-size: 11px; font-weight: 700; border-radius: 999px; padding: 2px 9px; }
.aw-vat-inc { background: #e7eefd; color: #1b4fc0; }
.aw-vat-exc { background: #fbeedd; color: #b45309; }
.aw-vat-break { font-size: 11.5px; color: #6b7280; font-variant-numeric: tabular-nums; }

/* 과제 구매기안서 — RCMS 항목·세부항목 */
.aw-budget-row { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 10px; }
.aw-budget-select { flex: 0 1 280px; min-width: 200px; }
.aw-budget-badge { font-size: 11.5px; font-weight: 700; border-radius: 999px; padding: 3px 10px; background: #1f2a44; color: #fff; white-space: nowrap; }
.aw-budget-note { font-size: 11.5px; color: #9aa0ab; white-space: nowrap; }
.aw-vat-break b { color: #15181e; }
/* 발주서 자동 생성 박스 (품목 아래, 눈에 띄게) */
.aw-po-box { margin-top: 14px; border: 1.5px solid #cdddfb; background: #f4f8ff; border-radius: 10px; padding: 12px 14px; }
.aw-po-box-on { border-color: var(--accent, #2f6fed); background: #eaf1ff; }
.aw-po-toggle { display: flex; align-items: center; gap: 9px; cursor: pointer; user-select: none; }
.aw-po-toggle input { width: 17px; height: 17px; accent-color: var(--accent, #2f6fed); cursor: pointer; flex-shrink: 0; }
.aw-po-toggle-txt { font-size: 13.5px; color: #1f2a44; }
.aw-po-toggle-txt b { color: #1b4fc0; }
.aw-po-body { margin-top: 11px; padding-top: 11px; border-top: 1px dashed #c2d3f2; }
.aw-po-sup-label { display: block; font-size: 12px; font-weight: 600; color: #3a4250; margin-bottom: 5px; }
.aw-po-hint { font-size: 11.5px; color: #6b7280; margin-top: 6px; }

/* 휴가 자동 제목 */
.aw-title-auto { font-weight: 700; color: #15181e; }
.aw-title-auto-hint { font-weight: 400; font-size: 12px; color: #9298a3; }

.aw-leave-note {
  border: 1px solid var(--accent-soft); background: var(--accent-soft);
  border-radius: 9px; padding: 10px 12px; font-size: 12.5px; color: #1f4fb0; margin-bottom: 14px;
}
.aw-leave-over { display: block; margin-top: 4px; color: #cf3b2f; }

.aw-empty-hint {
  font-size: 12.5px; color: #9aa0ab; padding: 11px 14px;
  border: 1.5px dashed #d4d8df; border-radius: 10px; background: #fafbfc;
}
.aw-empty-hint-center { text-align: center; }

/* attachments */
.aw-attach-list { list-style: none; margin: 0 0 10px; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.aw-attach-item {
  display: flex; align-items: center; gap: 10px; padding: 11px 14px;
  border: 1px solid #e9ebef; border-radius: 10px;
}
.aw-attach-badge {
  width: 30px; height: 30px; flex: none; border-radius: 7px;
  background: #fdecec; color: #cf3b2f;
  display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: 800;
}
.aw-attach-info { flex: 1; min-width: 0; }
.aw-attach-name { font-size: 13px; font-weight: 600; color: #2b2f37; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.aw-attach-link { display: block; max-width: 100%; padding: 0; background: none; border: none; text-align: left; cursor: pointer; font-family: inherit; }
.aw-attach-link:hover { color: #2563eb; text-decoration: underline; }
.aw-attach-size { font-size: 11.5px; color: #9aa0ab; }
.aw-dropzone {
  width: 100%; height: 48px; border: 1.5px dashed #d4d8df; background: #fafbfc;
  border-radius: 10px; color: #8b909a; font-size: 13px; font-weight: 600; cursor: pointer;
  font-family: inherit; transition: border-color 0.12s, color 0.12s, background 0.12s;
}
.aw-dropzone:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); background: var(--accent-soft); }
.aw-dropzone:disabled { opacity: 0.6; cursor: not-allowed; }
.aw-hidden { display: none; }

/* ===== SIDEBAR ===== */
.aw-sidebar {
  width: 320px; flex: none; position: sticky; top: 86px;
  display: flex; flex-direction: column; gap: 16px;
}
.aw-card {
  background: #fff; border: 1px solid #e7e9ee; border-radius: 13px; padding: 18px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.03);
}
.aw-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; gap: 8px; }
.aw-card-title { font-size: 13.5px; font-weight: 700; color: #15181e; }
.aw-card-hint { font-size: 11px; color: #9aa0ab; }

.aw-form-chips { display: flex; flex-direction: column; gap: 6px; margin-top: 12px; }
.aw-form-row { display: flex; flex-wrap: wrap; gap: 6px; }
.aw-form-chip {
  padding: 6px 11px; border: 1px solid #d8dbe1; background: #fff; color: #3a3f49;
  font-size: 12.5px; font-weight: 600; border-radius: 8px; cursor: pointer; font-family: inherit;
  transition: background 0.12s, border-color 0.12s, color 0.12s;
}
.aw-form-chip:hover { background: #f7f8fa; }
.aw-form-chip-on { background: var(--accent); border-color: var(--accent); color: #fff; }

.aw-add-row { display: flex; gap: 8px; margin: 12px 0; align-items: center; }
.aw-add-row-tight { margin: 8px 0 0; }
.aw-add-select { flex: 1; min-width: 0; }

.aw-mini-btn {
  height: 38px; padding: 0 14px; border: 1px solid #d8dbe1; background: #fff; color: #2b2f37;
  font-size: 12.5px; font-weight: 600; border-radius: 8px; cursor: pointer; white-space: nowrap;
  font-family: inherit; transition: background 0.12s, filter 0.12s;
}
.aw-mini-btn:hover:not(:disabled) { background: #f7f8fa; }
.aw-mini-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.aw-mini-btn-dark { background: #2b2f37; border-color: #2b2f37; color: #fff; }
.aw-mini-btn-dark:hover:not(:disabled) { background: #1f242c; }
.aw-mini-btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
.aw-mini-btn-primary:hover:not(:disabled) { filter: brightness(0.95); }

/* approval line list */
.aw-line-list { list-style: none; margin: 4px 0 0; padding: 0; display: flex; flex-direction: column; }
.aw-line-item {
  display: flex; align-items: center; gap: 8px; padding: 9px 4px;
  border-bottom: 1px solid #f0f2f4; cursor: move; transition: background 0.12s;
}
.aw-line-item:last-child { border-bottom: none; }
.aw-line-over { background: var(--accent-soft); }
.aw-line-dragging { opacity: 0.5; }
.aw-line-handle { color: #cfd3da; user-select: none; font-size: 13px; }
.aw-avatar {
  width: 34px; height: 34px; flex: none; border-radius: 50%;
  background: #f1f3f5; color: #8b909a;
  display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700;
}
.aw-line-item:first-child .aw-avatar { background: var(--accent-soft); color: var(--accent); }
.aw-line-info { flex: 1; min-width: 0; }
.aw-line-name {
  font-size: 13px; font-weight: 600; color: #1f242c;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.aw-line-role { font-size: 11.5px; color: #9aa0ab; }
.aw-step-pill {
  height: 22px; padding: 0 9px; border-radius: 6px; font-size: 11.5px; font-weight: 700;
  display: inline-flex; align-items: center; flex: none; color: #fff;
}
.aw-step-mid { background: var(--accent); }
.aw-step-final { background: #cf3b2f; }
.aw-line-ctrls { display: flex; align-items: center; gap: 2px; flex: none; }

.aw-icon-btn {
  width: 24px; height: 24px; border: none; background: transparent; color: #aeb3bd;
  border-radius: 6px; cursor: pointer; font-size: 11px;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background 0.12s, color 0.12s;
}
.aw-icon-btn:hover:not(:disabled) { background: #f2f3f5; color: #5b616b; }
.aw-icon-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.aw-icon-del:hover:not(:disabled) { background: #fdecec; color: #cf3b2f; }

/* share / options */
.aw-share-label { font-size: 11.5px; font-weight: 600; color: #8b909a; margin-bottom: 8px; }
.aw-po-check { display: flex; align-items: flex-start; gap: 7px; font-size: 12.5px; color: #3a3f49; cursor: pointer; line-height: 1.5; }
.aw-po-check input { margin-top: 2px; }
.aw-ref-empty { font-size: 12px; color: #9aa0ab; padding: 8px 0; }
.aw-ref-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.aw-ref-chip {
  display: inline-flex; align-items: center; gap: 6px; height: 26px; padding: 0 11px;
  border-radius: 7px; background: #f4f5f7; color: #3a3f49; font-size: 12px; font-weight: 600;
}
.aw-ref-chip-x {
  border: none; background: transparent; color: #aeb3bd; cursor: pointer; font-size: 11px; padding: 0;
}
.aw-ref-chip-x:hover { color: #cf3b2f; }

.aw-footnote {
  font-size: 11.5px; color: #aeb3bd; text-align: center; line-height: 1.6; padding: 0 8px;
}

/* ===== RESPONSIVE ===== */
@media (max-width: 980px) {
  .aw-body { flex-direction: column; }
  .aw-sidebar { width: 100%; position: static; }
  .aw-paper-header { padding: 24px 18px 20px; }
  .aw-meta-wrap { padding: 18px 18px 4px; }
  .aw-section { padding: 0 18px; }
  .aw-section-last { padding-bottom: 28px; }
  .aw-meta-grid { grid-template-columns: 92px 1fr; }
  .aw-meta-value-input[style] { grid-column: auto !important; }
}
@media (max-width: 560px) {
  .aw-topbar { padding: 0 14px; }
  .aw-crumb { display: none; }
  .aw-attendee-row { flex-wrap: wrap; }
  .aw-paper-title { font-size: 24px; }
}
</style>
