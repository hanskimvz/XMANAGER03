<template>
  <div
    v-if="show"
    ref="modalOverlay"
    class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
    tabindex="-1"
    @keydown.escape="closeModal"
  >
    <div class="relative top-20 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white" @click.stop>
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold">{{ isEdit ? '부품 수정' : (mode === 'bom' ? 'BOM 등록' : '부품 등록') }}</h3>
        <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <!-- 로딩 상태 -->
      <div v-if="isLoadingCodes" class="text-center py-12">
        <div class="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-500 mx-auto"></div>
        <p class="text-gray-600 mt-4 font-medium">코드 정보를 불러오는 중...</p>
      </div>

      <form v-else @submit.prevent="submitForm" class="space-y-4">
        <!-- 기본 정보 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">기본 정보</h4>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >부품명 <span class="text-red-500">*</span></label
              >
              <input
                v-model="formData.part_name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">영문 부품명</label>
              <input
                v-model="formData.part_name_en"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <div class="mt-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">설명</label>
            <textarea
              v-model="formData.description"
              rows="3"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        <!-- 품번 구성 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">품번 구성</h4>

          <!-- Part UID (수정 모드에서만 표시) -->
          <div v-if="isEdit" class="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  고유ID (Part UID)
                  <span class="text-xs text-gray-400 ml-1">변경불가</span>
                </label>
                <div class="flex items-center">
                  <input
                    :value="formData.part_uid || '-'"
                    type="text"
                    readonly
                    class="w-48 px-3 py-2 border border-gray-200 rounded-md bg-gray-100 font-mono text-sm cursor-not-allowed"
                    title="바코드/QR용 고유 ID (시스템 생성, 변경 불가)"
                  />
                  <button
                    v-if="formData.part_uid"
                    type="button"
                    @click="copyToClipboard(formData.part_uid)"
                    class="ml-2 px-2 py-2 text-gray-500 hover:text-blue-600 transition-colors"
                    title="복사"
                  >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </button>
                </div>
              </div>
              <div class="ml-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">현재 품번</label>
                <div class="font-mono text-sm bg-white px-3 py-2 border rounded-md">
                  {{ originalPartNumber || '-' }}
                </div>
              </div>
            </div>
          </div>

          <!-- 품번 입력 방식 선택 (수정 모드 및 신규 등록 모두) -->
          <div class="mb-4">
            <div class="flex items-center space-x-4 mb-3">
              <span class="text-sm font-medium text-gray-700">품번 입력 방식:</span>
              <label class="inline-flex items-center cursor-pointer">
                <input
                  type="radio"
                  v-model="partNumberEditMode"
                  value="rule_a"
                  class="form-radio text-blue-600"
                />
                <span class="ml-2 text-sm">품번규칙 A</span>
              </label>
              <label class="inline-flex items-center cursor-pointer">
                <input
                  type="radio"
                  v-model="partNumberEditMode"
                  value="direct"
                  class="form-radio text-orange-600"
                />
                <span class="ml-2 text-sm">직접 입력</span>
              </label>
            </div>

            <!-- 직접 입력 모드 -->
            <div v-if="partNumberEditMode === 'direct'" class="bg-orange-50 border border-orange-200 rounded-lg p-3">
              <label class="block text-sm font-medium text-gray-700 mb-1">
                품번 직접 입력
                <span class="text-xs text-orange-500 ml-1">하이픈(-) 포함 형식으로 입력</span>
              </label>
              <div class="flex items-center gap-2">
                <div class="relative flex-1">
                  <input
                    v-model="formData.part_number"
                    type="text"
                    maxlength="30"
                    :class="[
                      'w-full px-3 py-2 border rounded-md focus:outline-none font-mono text-sm',
                      duplicateCheckResult?.exists
                        ? 'border-red-500 focus:ring-red-500 focus:border-red-500 bg-red-50'
                        : 'border-orange-300 focus:ring-orange-500 focus:border-orange-500'
                    ]"
                    :placeholder="partNumberWithHyphens"
                    @input="debouncedCheckDuplicate(formData.part_number || '')"
                  />
                  <!-- 중복 체크 로딩 -->
                  <div v-if="isCheckingDuplicate" class="absolute right-3 top-2.5">
                    <svg class="animate-spin h-5 w-5 text-orange-500" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                </div>
                <!-- 직접 입력 모드에서도 레벨 선택 가능 -->
                <select
                  v-model="formData.level_id"
                  class="w-32 px-2 py-2 border border-orange-300 rounded-md focus:outline-none focus:ring-orange-500 focus:border-orange-500 text-sm"
                >
                  <option :value="undefined">레벨 선택</option>
                  <option v-for="item in levels" :key="item.id" :value="item.id">
                    {{ item.code }} - {{ item.name_ko }}
                  </option>
                </select>
              </div>
              <!-- 미리보기: 직접 입력 품번 + 레벨 -->
              <div v-if="formData.part_number || selectedLevel" class="mt-2 font-mono text-sm">
                <span class="text-gray-500">미리보기: </span>
                <span class="text-orange-700">{{ formData.part_number || 'XXXX-XXX-XXX-XX-XX-XX' }}</span>
                <span v-if="selectedLevel" class="text-pink-700 ml-1">[{{ selectedLevel.code }}]</span>
              </div>
              <!-- 중복 경고 -->
              <div v-if="duplicateCheckResult?.exists" class="mt-2 p-2 bg-red-100 border border-red-300 rounded text-sm text-red-700">
                <span class="font-medium">⚠️ 중복된 품번입니다!</span>
                <div class="text-xs mt-1">
                  기존 부품: {{ duplicateCheckResult.part?.part_number_display }} - {{ duplicateCheckResult.part?.part_name }}
                </div>
              </div>
              <p class="text-xs text-orange-600 mt-1">예: COTS-SO-S31-06-NB-NN (하이픈 포함), 레벨은 별도 선택</p>
            </div>

            <!-- 품번규칙 A 모드: 미리보기 -->
            <div v-else class="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div class="text-sm text-blue-600 font-medium mb-1">품번규칙 A - 미리보기</div>
              <div class="font-mono text-lg">
                <span class="text-blue-700">{{ selectedProductLine?.code || '____' }}</span>
                <span class="text-gray-400">-</span>
                <span class="text-green-700">{{ selectedPartGroup?.code || '___' }}</span>
                <span class="text-gray-400">-</span>
                <span class="text-purple-700">{{ formData.item_code_prefix || '___' }}</span>
                <span class="text-gray-400">-</span>
                <span class="text-purple-500">{{ itemCodeSuffixInput || (isEdit ? itemCodeSuffix : '##') }}</span>
                <span class="text-gray-400">-</span>
                <span class="text-orange-700">{{ selectedMaterial?.code || 'XX' }}</span>
                <span class="text-gray-400">-</span>
                <span class="text-red-700">{{ selectedTreatment?.code || 'NN' }}</span>
                <span class="text-pink-700 ml-1">[{{ selectedLevel?.code || '_' }}]</span>
              </div>
              <div class="text-xs text-gray-500 mt-1">
                제품라인(4)-품목군(3)-품목코드(3+2)-재질(2)-후처리(2) [레벨]
                <span v-if="!itemCodeSuffixInput && !isEdit" class="text-blue-500 ml-2">* 뒤 2자리는 자동생성</span>
              </div>
            </div>
          </div>

          <!-- 구성요소 선택 (직접입력 모드가 아닐 때만 활성화) -->
          <div :class="{ 'opacity-50 pointer-events-none': partNumberEditMode === 'direct' }">
            <!-- 첫 번째 줄: 제품라인, 품목군 -->
            <div class="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1"
                  >제품라인 <span v-if="partNumberEditMode === 'rule_a'" class="text-red-500">*</span></label
                >
                <div class="flex space-x-2">
                  <SearchableSelect
                    v-model="formData.product_line_id"
                    :options="productLines"
                    placeholder="검색 또는 선택"
                    :disabled="partNumberEditMode === 'direct'"
                    class="flex-1"
                  />
                  <button
                    type="button"
                    @click="openCodeMasterModal('product_line')"
                    :disabled="partNumberEditMode === 'direct'"
                    class="px-2 py-2 bg-green-500 text-white text-xs rounded hover:bg-green-600 whitespace-nowrap disabled:bg-gray-300"
                    title="제품라인 간편등록"
                  >
                    +
                  </button>
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1"
                  >품목군 <span v-if="partNumberEditMode === 'rule_a'" class="text-red-500">*</span></label
                >
                <div class="flex space-x-2">
                  <SearchableSelect
                    v-model="formData.part_group_id"
                    :options="partGroups"
                    placeholder="검색 또는 선택"
                    :disabled="partNumberEditMode === 'direct'"
                    class="flex-1"
                  />
                  <button
                    type="button"
                    @click="openCodeMasterModal('part_group')"
                    :disabled="partNumberEditMode === 'direct'"
                    class="px-2 py-2 bg-green-500 text-white text-xs rounded hover:bg-green-600 whitespace-nowrap disabled:bg-gray-300"
                    title="품목군 간편등록"
                  >
                    +
                  </button>
                </div>
              </div>
            </div>
            <!-- 두 번째 줄: 품목코드, 레벨 -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1"
                  >품목코드 (5자리) <span v-if="partNumberEditMode === 'rule_a'" class="text-red-500">*</span></label
                >
                <div class="flex items-center gap-2">
                  <input
                    v-model="formData.item_code_prefix"
                    type="text"
                    :required="partNumberEditMode === 'rule_a'"
                    :disabled="partNumberEditMode === 'direct'"
                    maxlength="3"
                    placeholder="PLP"
                    class="w-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono disabled:bg-gray-100 text-center"
                  />
                  <span class="text-gray-400 font-bold">-</span>
                  <input
                    v-model="itemCodeSuffixInput"
                    type="text"
                    :disabled="partNumberEditMode === 'direct'"
                    maxlength="2"
                    :placeholder="isEdit ? itemCodeSuffix : '01'"
                    class="w-14 px-2 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono disabled:bg-gray-100 text-center"
                    :class="{ 'bg-green-50 border-green-300': itemCodeSuffixInput }"
                  />
                  <button
                    type="button"
                    @click="suggestItemCodeSuffix"
                    :disabled="partNumberEditMode === 'direct' || !formData.product_line_id || !formData.part_group_id || !formData.item_code_prefix"
                    class="px-3 py-2 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 whitespace-nowrap disabled:bg-gray-300 disabled:cursor-not-allowed"
                    title="비어있는 번호 자동 추천"
                  >
                    추천
                  </button>
                </div>
                <p class="text-xs text-gray-500 mt-1">
                  <span v-if="isEdit">기존: {{ itemCodeSuffix }}</span>
                  <span v-else-if="itemCodeSuffixInput">입력값: {{ itemCodeSuffixInput }}</span>
                  <span v-else class="text-blue-500">비워두면 자동생성</span>
                </p>
                <!-- 유사 품목코드 표시 (중복 방지) -->
                <div v-if="similarItemCodes.length > 0" class="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
                  <div class="font-medium text-yellow-700 mb-1">동일 조합의 기존 품목코드:</div>
                  <div class="flex flex-wrap gap-1">
                    <span
                      v-for="code in similarItemCodes"
                      :key="code.suffix"
                      class="px-2 py-0.5 bg-yellow-100 rounded"
                      :class="{ 'bg-red-200 text-red-700': code.suffix === itemCodeSuffixInput }"
                    >
                      {{ code.suffix }} ({{ code.part_name }})
                    </span>
                  </div>
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1"
                  >레벨 <span v-if="partNumberEditMode === 'rule_a'" class="text-red-500">*</span></label
                >
                <select
                  v-model="formData.level_id"
                  :required="partNumberEditMode === 'rule_a'"
                  :disabled="partNumberEditMode === 'direct'"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                >
                  <option :value="undefined">선택</option>
                  <option v-for="item in levels" :key="item.id" :value="item.id">
                    {{ item.code }} - {{ item.name_ko }}
                  </option>
                </select>
                <p class="text-xs text-gray-500 mt-1">품번 마지막 [{{ selectedLevel?.code || '_' }}]</p>
              </div>
            </div>
          </div>

          <!-- 분류 속성 -->
          <div class="mt-4">
            <div class="text-sm font-medium text-gray-700 mb-2">분류 속성</div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-600 mb-1">개발구분</label>
                <select
                  v-model="formData.development_type_id"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option :value="undefined">선택</option>
                  <option v-for="item in developmentTypes" :key="item.id" :value="item.id">
                    {{ item.code }} - {{ item.name_ko }}
                  </option>
                </select>
              </div>
              <div>
                <label class="block text-sm text-gray-600 mb-1">도면여부</label>
                <select
                  v-model="formData.drawing_type_id"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option :value="undefined">선택</option>
                  <option v-for="item in drawingTypes" :key="item.id" :value="item.id">
                    {{ item.code }} - {{ item.name_ko }}
                  </option>
                </select>
              </div>
            </div>
          </div>

          <!-- 부품유형 (다중선택) -->
          <div class="mt-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">부품유형 (다중선택 가능)</label>
            <div class="grid grid-cols-4 gap-2 p-3 border border-gray-200 rounded-md bg-gray-50">
              <template v-if="partTypes.length > 0">
                <label
                  v-for="item in partTypes"
                  :key="item.id"
                  class="flex items-center space-x-2 cursor-pointer hover:bg-white p-1 rounded"
                >
                  <input
                    type="checkbox"
                    :value="item.id"
                    v-model="formData.part_type_ids"
                    class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span class="text-sm">{{ item.code }} - {{ item.name_ko }}</span>
                </label>
              </template>
              <span v-else class="text-gray-400 text-sm col-span-4">부품유형 데이터가 없습니다.</span>
            </div>
          </div>
        </div>

        <!-- 재질 및 후처리 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">재질 및 후처리</h4>
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">재질</label>
              <div class="flex space-x-2">
                <select
                  v-model="formData.material_id"
                  class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option :value="undefined">선택</option>
                  <option v-for="item in materials" :key="item.id" :value="item.id">
                    {{ item.code }} - {{ item.name_ko }}
                  </option>
                </select>
                <button
                  type="button"
                  @click="openCodeMasterModal('material')"
                  class="px-2 py-2 bg-green-500 text-white text-xs rounded hover:bg-green-600 whitespace-nowrap"
                  title="재질 간편등록"
                >
                  +
                </button>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">후처리</label>
              <div class="flex space-x-2">
                <select
                  v-model="formData.treatment_id"
                  class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option :value="undefined">선택</option>
                  <option v-for="item in treatments" :key="item.id" :value="item.id">
                    {{ item.code }} - {{ item.name_ko }}
                  </option>
                </select>
                <button
                  type="button"
                  @click="openCodeMasterModal('treatment')"
                  class="px-2 py-2 bg-green-500 text-white text-xs rounded hover:bg-green-600 whitespace-nowrap"
                  title="후처리 간편등록"
                >
                  +
                </button>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">규격</label>
              <input
                v-model="formData.specification"
                type="text"
                placeholder="예: AN016, SER-20"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        <!-- 조달 정보 섹션 -->
        <div class="border-b pb-4">
          <h4 class="font-semibold mb-3">조달 정보</h4>
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">조달구분</label>
              <select
                v-model="formData.procurement_type_id"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option :value="undefined">선택</option>
                <option v-for="item in procurementTypes" :key="item.id" :value="item.id">
                  {{ item.code }} - {{ item.name_ko }}
                </option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">공급업체</label>
              <div class="flex gap-2">
                <input
                  type="text"
                  :value="selectedSupplierName"
                  readonly
                  placeholder="공급업체를 선택하세요"
                  class="flex-1 min-w-0 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 cursor-pointer focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  @click="showSupplierSearchModal = true"
                />
                <button
                  type="button"
                  @click="showSupplierSearchModal = true"
                  class="flex-shrink-0 px-3 py-2 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200"
                  title="공급업체 검색"
                >
                  <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </button>
                <button
                  v-if="formData.supplier_id"
                  type="button"
                  @click="clearSupplier"
                  class="flex-shrink-0 px-2 py-2 bg-gray-200 text-gray-600 rounded-md hover:bg-gray-300"
                  title="선택 해제"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">단위</label>
              <select
                v-model="formData.unit_id"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option :value="undefined">선택</option>
                <option v-for="item in units" :key="item.id" :value="item.id">
                  {{ item.code }} - {{ item.name_ko }}
                </option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-4 mt-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">최소 주문 수량</label>
              <input
                v-model.number="formData.min_order_qty"
                type="number"
                min="1"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">기준단가</label>
              <!-- BOM 모드: 계산 원가 적용 체크박스 -->
              <div v-if="mode === 'bom' && !isEdit" class="space-y-2">
                <label class="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    v-model="useCalculatedCost"
                    class="mr-2 rounded border-gray-300 text-blue-600 focus:ring-blue-500 w-4 h-4"
                  />
                  <span class="text-sm text-gray-700">하위 부품 합산 원가 적용</span>
                </label>
                <!-- 체크 해제 시 가격 입력 필드 표시 -->
                <div v-if="!useCalculatedCost" class="flex gap-2">
                  <input
                    v-model.number="formData.standard_price"
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="0"
                    class="flex-1 min-w-0 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                  <select
                    v-model="formData.standard_price_currency"
                    class="flex-shrink-0 w-24 px-2 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                  >
                    <option value="KRW">₩ KRW</option>
                    <option value="USD">$ USD</option>
                    <option value="EUR">€ EUR</option>
                    <option value="JPY">¥ JPY</option>
                    <option value="CNY">¥ CNY</option>
                    <option value="GBP">£ GBP</option>
                  </select>
                </div>
                <p v-else class="text-xs text-blue-600">
                  BOM 구성 후 하위 부품 단가의 합계로 자동 계산됩니다.
                </p>
              </div>
              <!-- 부품 모드 또는 수정 모드: 기존 가격 입력 -->
              <div v-else class="flex gap-2">
                <input
                  v-model.number="formData.standard_price"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0"
                  class="flex-1 min-w-0 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
                <select
                  v-model="formData.standard_price_currency"
                  class="flex-shrink-0 w-24 px-2 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                >
                  <option value="KRW">₩ KRW</option>
                  <option value="USD">$ USD</option>
                  <option value="EUR">€ EUR</option>
                  <option value="JPY">¥ JPY</option>
                  <option value="CNY">¥ CNY</option>
                  <option value="GBP">£ GBP</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- 전속(독점) 공급 계약 (v0.79.0) — 관리자만 -->
        <div v-if="isAdmin" class="border-b pb-4">
          <h4 class="font-semibold mb-3 flex items-center gap-2">
            🔒 전속(독점) 공급 계약
            <span class="text-xs font-normal text-gray-400">특정 고객 전용 — 다른 고객 생산요청 차단</span>
          </h4>
          <label class="flex items-center gap-2 mb-3 cursor-pointer">
            <input type="checkbox" v-model="formData.is_protected" class="w-4 h-4 rounded accent-red-600" />
            <span class="text-sm font-medium text-gray-700">이 부품은 전속 계약 품목입니다</span>
          </label>
          <div v-if="formData.is_protected" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">전속 고객 <span class="text-red-500">*</span></label>
              <select v-model.number="formData.protected_customer_id"
                class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500">
                <option :value="undefined">고객 선택…</option>
                <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.partner_name }}</option>
              </select>
              <p class="text-xs text-gray-400 mt-1">이 고객 외에는 견적/생산요청 시 경고·차단됩니다.</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">계약 비고</label>
              <input v-model="formData.protection_note" type="text" placeholder="예: 2026 독점공급계약 (만료 2027-12)"
                class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500" />
            </div>
          </div>
        </div>

        <!-- 첨부파일 섹션 (수정 모드에서만 표시) -->
        <div v-if="isEdit && partId" class="border-b pb-4">
          <h4 class="font-semibold mb-3">첨부파일</h4>
          <div class="grid grid-cols-3 gap-4">
            <!-- 도면 업로드 -->
            <div class="border rounded-lg p-3">
              <h5 class="text-sm font-medium text-gray-700 mb-2">도면</h5>
              <FileUpload
                :part-id="partId"
                file-type="drawing"
                @uploaded="handleFileUploaded"
                @error="handleUploadError"
              />
            </div>

            <!-- 사진 업로드 -->
            <div class="border rounded-lg p-3">
              <h5 class="text-sm font-medium text-gray-700 mb-2">사진</h5>
              <FileUpload
                :part-id="partId"
                file-type="photo"
                @uploaded="handleFileUploaded"
                @error="handleUploadError"
              />
            </div>

            <!-- 문서 업로드 -->
            <div class="border rounded-lg p-3">
              <h5 class="text-sm font-medium text-gray-700 mb-2">문서</h5>
              <FileUpload
                :part-id="partId"
                file-type="document"
                @uploaded="handleFileUploaded"
                @error="handleUploadError"
              />
            </div>
          </div>
          <!-- 첨부된 파일 목록 -->
          <div class="mt-4">
            <FileList
              ref="fileListRef"
              :part-id="partId"
              @deleted="handleFileDeleted"
            />
          </div>
        </div>

        <!-- 신규 등록 시 안내 메시지 -->
        <div v-else-if="!isEdit" class="border-b pb-4">
          <h4 class="font-semibold mb-3">첨부파일</h4>
          <div class="bg-gray-50 rounded-lg p-4 text-center text-gray-500">
            <svg class="mx-auto h-8 w-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-sm">부품 등록 후 상세 화면에서 파일을 첨부할 수 있습니다.</p>
          </div>
        </div>

        <!-- 유효성 검사 에러 표시 -->
        <div v-if="validationErrors.length > 0" class="bg-red-50 border border-red-200 rounded-lg p-3">
          <div class="flex items-start">
            <svg class="w-5 h-5 text-red-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
            <div>
              <p class="text-sm font-medium text-red-800">입력 오류가 있습니다</p>
              <ul class="mt-1 text-sm text-red-700 list-disc list-inside">
                <li v-for="(error, idx) in validationErrors" :key="idx">{{ error }}</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- 버튼 -->
        <div class="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            @click="closeModal"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            취소
          </button>
          <button
            type="submit"
            class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            {{ isEdit ? '수정' : '등록' }}
          </button>
        </div>
      </form>

      <!-- 공급업체 검색 모달 -->
      <SupplierSearchModal
        :show="showSupplierSearchModal"
        partner-type="supplier"
        @close="showSupplierSearchModal = false"
        @select="handleSupplierSelect"
      />

      <!-- 코드 마스터 간편등록 모달 -->
      <CodeMasterQuickAddModal
        :show="showCodeMasterModal"
        :code-type="codeMasterType"
        @close="closeCodeMasterModal"
        @added="handleCodeMasterAdded"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { partApi, type PartCreate } from '@/api/parts'

// 수정 모드에서 사용할 확장된 폼 데이터 타입
interface PartFormData extends PartCreate {
  part_uid?: string  // v0.12.0: 고유 ID (읽기 전용)
  part_number?: string  // v0.12.0: 품번 (수정 가능)
  part_number_display?: string  // 표시용 품번
  item_code?: string  // 품목코드 5자리 (앞3+뒤2)
}
import {
  productLineApi,
  partGroupApi,
  developmentTypeApi,
  partTypeApi,
  drawingTypeApi,
  materialApi,
  treatmentApi,
  levelApi,
  procurementTypeApi,
  unitApi,
  type CodeMaster,
} from '@/api/codeMaster'
import { partnerApi, type BusinessPartnerListItem, type Partner } from '@/api/partner'
import { useAuth } from '@/stores/auth'
import FileUpload from '@/components/FileUpload.vue'
import FileList from '@/components/FileList.vue'
import SupplierSearchModal from './SupplierSearchModal.vue'
import CodeMasterQuickAddModal from './CodeMasterQuickAddModal.vue'
import SearchableSelect from '@/components/SearchableSelect.vue'

interface Props {
  show: boolean
  isEdit: boolean
  initialData?: (Partial<PartCreate> & { id?: number }) | null
  mode?: 'parts' | 'bom'  // 부품관리 모드 vs BOM 모드
}

const props = withDefaults(defineProps<Props>(), {
  mode: 'parts'
})
const emit = defineEmits<{
  close: []
  submit: [data: PartCreate]
}>()

// 부품 ID (수정 모드에서 파일 업로드에 사용)
const partId = computed(() => props.initialData?.id)

// 파일 목록 ref
const fileListRef = ref<InstanceType<typeof FileList> | null>(null)

// 로딩 상태
const isLoadingCodes = ref(false)

// 코드 마스터 데이터
const productLines = ref<CodeMaster[]>([])
const partGroups = ref<CodeMaster[]>([])
const developmentTypes = ref<CodeMaster[]>([])
const partTypes = ref<CodeMaster[]>([])
const drawingTypes = ref<CodeMaster[]>([])
const materials = ref<CodeMaster[]>([])
const treatments = ref<CodeMaster[]>([])
const levels = ref<CodeMaster[]>([])
const procurementTypes = ref<CodeMaster[]>([])
const units = ref<CodeMaster[]>([])
const suppliers = ref<BusinessPartnerListItem[]>([])
const customers = ref<BusinessPartnerListItem[]>([])  // v0.79.0: 전속 고객 선택용
const { isAdmin } = useAuth()  // 전속 계약 지정은 관리자만

// 선택된 코드 마스터 정보 (품번 미리보기용)
const selectedProductLine = computed(() =>
  productLines.value.find(item => item.id === formData.value.product_line_id)
)
const selectedPartGroup = computed(() =>
  partGroups.value.find(item => item.id === formData.value.part_group_id)
)
const selectedMaterial = computed(() =>
  materials.value.find(item => item.id === formData.value.material_id)
)
const selectedTreatment = computed(() =>
  treatments.value.find(item => item.id === formData.value.treatment_id)
)
const selectedLevel = computed(() =>
  levels.value.find(item => item.id === formData.value.level_id)
)

// 품번 입력 모드 ('rule_a' = 품번규칙 A, 'direct' = 직접 입력)
// 신규 등록과 수정 모두에서 사용
// localStorage에서 이전 선택값 복원
const PART_NUMBER_MODE_KEY = 'partNumberEditMode'
const savedMode = localStorage.getItem(PART_NUMBER_MODE_KEY)
const partNumberEditMode = ref<'rule_a' | 'direct'>(
  savedMode === 'direct' ? 'direct' : 'rule_a'
)

// 원본 품번 (수정 모드에서 표시용)
const originalPartNumber = ref<string>('')

// 품번 중복 체크 관련
const isCheckingDuplicate = ref(false)
const duplicateCheckResult = ref<{
  exists: boolean
  part: { id: number; part_number: string; part_number_display: string; part_name: string } | null
} | null>(null)
let duplicateCheckTimeout: ReturnType<typeof setTimeout> | null = null

// 품목코드 뒤 2자리 직접 입력
const itemCodeSuffixInput = ref('')

// 품목코드 뒤 2자리 (수정 모드에서 기존 값 유지)
const itemCodeSuffix = computed(() => {
  // item_code가 있으면 뒤 2자리 추출, 없으면 기본값
  const itemCode = formData.value.item_code || ''
  if (itemCode.length >= 5) {
    return itemCode.slice(3, 5)
  } else if (itemCode.length > 3) {
    return itemCode.slice(3)
  }
  return '01'
})

// 유사 품목코드 목록 (중복 방지용)
const similarItemCodes = ref<Array<{ suffix: string; part_name: string; part_id: number }>>([])
let similarCodesTimeout: ReturnType<typeof setTimeout> | null = null

// 유사 품목코드 조회 (제품라인 + 품목군 + 품목코드 앞3자리가 같은 데이터)
const loadSimilarItemCodes = async () => {
  if (!formData.value.product_line_id || !formData.value.part_group_id || !formData.value.item_code_prefix) {
    similarItemCodes.value = []
    return
  }

  try {
    // 같은 조합의 부품 검색
    const response = await partApi.getAll({
      product_line_id: formData.value.product_line_id,
      part_group_id: formData.value.part_group_id,
      limit: 100
    })

    // 품목코드 앞 3자리가 같은 것만 필터링
    const prefix = formData.value.item_code_prefix.toUpperCase()
    const currentPartId = props.initialData?.id

    similarItemCodes.value = response.data.items
      .filter(part => {
        // 현재 수정 중인 부품은 제외
        if (currentPartId && part.id === currentPartId) return false
        // 품목코드 앞 3자리가 같은지 확인
        const partPrefix = part.item_code?.slice(0, 3)?.toUpperCase()
        return partPrefix === prefix
      })
      .map(part => ({
        suffix: part.item_code?.slice(3, 5) || '??',
        part_name: part.part_name,
        part_id: part.id
      }))
      .sort((a, b) => a.suffix.localeCompare(b.suffix))
  } catch (error) {
    console.error('유사 품목코드 조회 실패:', error)
    similarItemCodes.value = []
  }
}

// 디바운스된 유사 품목코드 조회
const debouncedLoadSimilarCodes = () => {
  if (similarCodesTimeout) {
    clearTimeout(similarCodesTimeout)
  }
  similarCodesTimeout = setTimeout(() => {
    loadSimilarItemCodes()
  }, 300)
}

// 품목코드 뒤 2자리 추천 (비어있는 가장 작은 번호)
const suggestItemCodeSuffix = async () => {
  if (!formData.value.product_line_id || !formData.value.part_group_id || !formData.value.item_code_prefix) {
    alert('제품라인, 품목군, 품목코드 앞 3자리를 먼저 선택/입력해주세요.')
    return
  }

  await loadSimilarItemCodes()

  // 사용 중인 suffix 목록
  const usedSuffixes = new Set(similarItemCodes.value.map(c => c.suffix))

  // 01부터 99까지 비어있는 가장 작은 번호 찾기
  for (let i = 1; i <= 99; i++) {
    const suffix = i.toString().padStart(2, '0')
    if (!usedSuffixes.has(suffix)) {
      itemCodeSuffixInput.value = suffix
      return
    }
  }

  alert('사용 가능한 번호가 없습니다. (01~99 모두 사용 중)')
}

// 공급업체 검색 모달
const showSupplierSearchModal = ref(false)
const selectedSupplier = ref<Partner | null>(null)

// 선택된 공급업체 이름 표시
const selectedSupplierName = computed(() => {
  if (selectedSupplier.value) {
    return `${selectedSupplier.value.partner_code} - ${selectedSupplier.value.partner_name}`
  }
  // 수정 모드에서 기존 공급업체 정보 표시
  if (formData.value.supplier_id) {
    const supplier = suppliers.value.find(s => s.id === formData.value.supplier_id)
    if (supplier) {
      return `${supplier.partner_code} - ${supplier.partner_name}`
    }
  }
  return ''
})

// 코드 마스터 간편등록 모달
const showCodeMasterModal = ref(false)
const codeMasterType = ref<'product_line' | 'part_group' | 'material' | 'treatment'>('product_line')

// BOM 모드: 계산 원가 적용 체크박스 (기본 체크)
const useCalculatedCost = ref(true)

// 하이픈 포함 품번 미리보기 (직접 입력용 placeholder)
const partNumberWithHyphens = computed(() => {
  // 예: COTS-SO-S31-06-NB-NN 형식
  return 'XXXX-XXX-XXX-XX-XX-XX'
})

// 품번 중복 체크 함수
const checkPartNumberDuplicate = async (partNumber: string) => {
  if (!partNumber || partNumber.length < 5) {
    duplicateCheckResult.value = null
    return
  }

  isCheckingDuplicate.value = true
  try {
    const excludeId = props.isEdit ? props.initialData?.id : undefined
    const response = await partApi.checkDuplicate(partNumber, excludeId)
    duplicateCheckResult.value = response.data
  } catch (error) {
    console.error('품번 중복 체크 실패:', error)
    duplicateCheckResult.value = null
  } finally {
    isCheckingDuplicate.value = false
  }
}

// 디바운스된 품번 중복 체크
const debouncedCheckDuplicate = (partNumber: string) => {
  if (duplicateCheckTimeout) {
    clearTimeout(duplicateCheckTimeout)
  }
  duplicateCheckTimeout = setTimeout(() => {
    checkPartNumberDuplicate(partNumber)
  }, 500)
}

// 폼 데이터 (v0.12.0: part_uid, part_number 추가)
const formData = ref<PartFormData>({
  part_name: '',
  part_name_en: '',
  description: '',
  product_line_id: undefined,
  part_group_id: undefined,
  item_code_prefix: '',  // 품목코드 앞 3자리 (사용자 입력)
  development_type_id: undefined,
  drawing_type_id: undefined,
  part_type_ids: [],
  material_id: undefined,
  treatment_id: undefined,
  level_id: undefined,
  procurement_type_id: undefined,
  specification: '',
  unit_id: undefined,
  min_order_qty: 1,
  supplier_id: undefined,
  is_protected: false,
  protected_customer_id: undefined,
  protection_note: '',
  standard_price: 0,
  standard_price_currency: 'KRW',
  // v0.12.0 추가 필드
  part_uid: undefined,
  part_number: undefined,
  part_number_display: undefined,
})

// 클립보드 복사 함수 (v0.12.0)
const copyToClipboard = async (text: string | undefined) => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    alert('클립보드에 복사되었습니다: ' + text)
  } catch (err) {
    console.error('클립보드 복사 실패:', err)
  }
}

// 폼 리셋
const resetForm = () => {
  formData.value = {
    part_name: '',
    part_name_en: '',
    description: '',
    product_line_id: undefined,
    part_group_id: undefined,
    item_code_prefix: '',  // 품목코드 앞 3자리 (사용자 입력)
    development_type_id: undefined,
    drawing_type_id: undefined,
    part_type_ids: [],
    material_id: undefined,
    treatment_id: undefined,
    level_id: undefined,
    procurement_type_id: undefined,
    specification: '',
    unit_id: undefined,
    min_order_qty: 1,
    supplier_id: undefined,
    is_protected: false,
    protected_customer_id: undefined,
    protection_note: '',
    standard_price: 0,
    standard_price_currency: 'KRW',
    // v0.12.0 추가 필드
    part_uid: undefined,
    part_number: undefined,
    part_number_display: undefined,
  }
  // BOM 모드 체크박스 초기화
  useCalculatedCost.value = true
  // 품번 입력 모드: localStorage에서 이전 선택값 복원
  const savedMode = localStorage.getItem(PART_NUMBER_MODE_KEY)
  partNumberEditMode.value = savedMode === 'direct' ? 'direct' : 'rule_a'
  itemCodeSuffixInput.value = ''
  duplicateCheckResult.value = null
  isCheckingDuplicate.value = false
}

// 코드 마스터 데이터 로드
const loadCodeMasters = async () => {
  try {
    isLoadingCodes.value = true
    console.log('코드 마스터 데이터 로드 시작...')

    const results = await Promise.allSettled([
      productLineApi.getAll(),
      partGroupApi.getAll(),
      developmentTypeApi.getAll(),
      partTypeApi.getAll(),
      drawingTypeApi.getAll(),
      materialApi.getAll(),
      treatmentApi.getAll(),
      levelApi.getAll(),
      procurementTypeApi.getAll(),
      unitApi.getAll(),
      partnerApi.getAll({ is_supplier: true, is_active: true, limit: 500 }),
    ])

    // 각 결과 처리
    if (results[0].status === 'fulfilled') productLines.value = results[0].value.data
    else console.error('productLineApi 실패:', results[0].reason)

    if (results[1].status === 'fulfilled') partGroups.value = results[1].value.data
    else console.error('partGroupApi 실패:', results[1].reason)

    if (results[2].status === 'fulfilled') developmentTypes.value = results[2].value.data
    else console.error('developmentTypeApi 실패:', results[2].reason)

    if (results[3].status === 'fulfilled') partTypes.value = results[3].value.data
    else console.error('partTypeApi 실패:', results[3].reason)

    if (results[4].status === 'fulfilled') drawingTypes.value = results[4].value.data
    else console.error('drawingTypeApi 실패:', results[4].reason)

    if (results[5].status === 'fulfilled') materials.value = results[5].value.data
    else console.error('materialApi 실패:', results[5].reason)

    if (results[6].status === 'fulfilled') treatments.value = results[6].value.data
    else console.error('treatmentApi 실패:', results[6].reason)

    if (results[7].status === 'fulfilled') levels.value = results[7].value.data
    else console.error('levelApi 실패:', results[7].reason)

    if (results[8].status === 'fulfilled') procurementTypes.value = results[8].value.data
    else console.error('procurementTypeApi 실패:', results[8].reason)

    if (results[9].status === 'fulfilled') units.value = results[9].value.data
    else console.error('unitApi 실패:', results[9].reason)

    if (results[10].status === 'fulfilled') suppliers.value = results[10].value.data.items
    else console.error('partnerApi 실패:', results[10].reason)

    // v0.79.0: 전속 고객 목록(고객사) 로드
    partnerApi.getAll({ is_customer: true, is_active: true, limit: 500 })
      .then(r => { customers.value = r.data.items || [] })
      .catch(() => { customers.value = [] })

    console.log('코드 마스터 데이터 로드 완료:', {
      productLines: productLines.value.length,
      partGroups: partGroups.value.length,
      developmentTypes: developmentTypes.value.length,
      partTypes: partTypes.value.length,
      drawingTypes: drawingTypes.value.length,
      materials: materials.value.length,
      treatments: treatments.value.length,
      levels: levels.value.length,
      procurementTypes: procurementTypes.value.length,
      units: units.value.length,
      suppliers: suppliers.value.length,
    })
  } catch (error) {
    console.error('코드 마스터 로드 실패:', error)
  } finally {
    isLoadingCodes.value = false
  }
}

// 모달 닫기
const closeModal = () => {
  emit('close')
}

// 폼 유효성 검사 에러
const validationErrors = ref<string[]>([])

// 폼 유효성 검사
const validateForm = (): boolean => {
  validationErrors.value = []

  // 필수 필드 검증
  if (!formData.value.part_name?.trim()) {
    validationErrors.value.push('부품명은 필수입니다.')
  }

  // 직접 입력 모드: 품번 필수, 레벨 선택
  if (partNumberEditMode.value === 'direct') {
    if (!formData.value.part_number?.trim()) {
      validationErrors.value.push('품번을 입력해주세요.')
    }
    // 직접 입력 모드에서도 레벨은 선택 사항 (없어도 저장 가능)
  } else {
    // 신규 등록 또는 품번규칙 A 모드: 구성요소 필수
    if (!formData.value.product_line_id) {
      validationErrors.value.push('제품라인을 선택해주세요.')
    }

    if (!formData.value.part_group_id) {
      validationErrors.value.push('품목군을 선택해주세요.')
    }

    if (!formData.value.item_code_prefix?.trim()) {
      validationErrors.value.push('품목코드(앞 3자리)를 입력해주세요.')
    } else if (!/^[A-Za-z0-9]{3}$/.test(formData.value.item_code_prefix)) {
      validationErrors.value.push('품목코드는 영문/숫자 3자리여야 합니다.')
    }

    // 레벨 필수 (v0.20.0)
    if (!formData.value.level_id) {
      validationErrors.value.push('레벨을 선택해주세요.')
    }

    // 품목코드 대문자 변환
    if (formData.value.item_code_prefix) {
      formData.value.item_code_prefix = formData.value.item_code_prefix.toUpperCase()
    }
  }

  return validationErrors.value.length === 0
}

// 폼 제출
const submitForm = () => {
  if (!validateForm()) {
    return
  }

  // 중복 체크 결과 확인 (직접 입력 모드일 때)
  if (partNumberEditMode.value === 'direct' && duplicateCheckResult.value?.exists) {
    alert('중복된 품번입니다. 다른 품번을 입력해주세요.')
    return
  }

  // 직접 입력 모드 처리
  if (partNumberEditMode.value === 'direct') {
    // 직접 입력 모드: part_number와 part_number_display 동기화
    if (formData.value.part_number) {
      // 하이픈 있는 값을 display로, 하이픈 제거한 값을 내부값으로
      formData.value.part_number_display = formData.value.part_number
      // 내부 저장용 품번에서 하이픈 제거 (백엔드에서 처리할 수도 있음)
    }
    // 직접 입력 모드에서는 품번규칙 A 관련 필드 제거 (min_length 검증 에러 방지)
    formData.value.item_code_prefix = undefined
    ;(formData.value as any).item_code_suffix = undefined
    formData.value.product_line_id = undefined
    formData.value.part_group_id = undefined
  } else {
    // 품번규칙 A 모드
    // 품목코드 뒤 2자리 값 적용 (입력값이 있으면 사용, 없으면 수정모드에서 기존값 사용)
    if (itemCodeSuffixInput.value && itemCodeSuffixInput.value.length === 2) {
      ;(formData.value as any).item_code_suffix = itemCodeSuffixInput.value
    } else if (props.isEdit && formData.value.item_code) {
      // 수정 모드: 기존 품목코드 뒤 2자리 유지
      ;(formData.value as any).item_code_suffix = formData.value.item_code.slice(3, 5)
    }

    if (props.isEdit) {
      // 수정 모드: 품번은 백엔드에서 재생성
      delete formData.value.part_number
      delete formData.value.part_number_display
      // 백엔드에 품번 재생성 요청 플래그 추가
      ;(formData.value as any).regenerate_part_number = true
    } else {
      // 신규 등록 모드: part_number 필드 제거
      delete formData.value.part_number
      delete formData.value.part_number_display
    }
  }

  // 빈 숫자 필드 정리 (Pydantic 빈 문자열 거부 방지)
  const _payload: any = formData.value
  for (const f of ['min_order_qty', 'standard_price', 'latest_price', 'inventory_avg_price',
                   'material_cost', 'labor_cost', 'overhead_cost', 'calculated_cost',
                   'lead_time_days', 'safety_stock']) {
    const v = _payload[f]
    if (v === '' || v === undefined || (typeof v === 'number' && Number.isNaN(v))) _payload[f] = null
  }

  // v0.79.0: 전속 해제 시 고객/비고 정리, 지정 시 null 명시 전송
  if (!_payload.is_protected) {
    _payload.protected_customer_id = null
    _payload.protection_note = null
  } else if (_payload.protected_customer_id === undefined) {
    _payload.protected_customer_id = null
  }

  emit('submit', _payload)
}

// 파일 업로드 완료
const handleFileUploaded = () => {
  fileListRef.value?.refresh()
}

// 파일 업로드 에러
const handleUploadError = (error: string) => {
  alert(error)
}

// 파일 삭제 완료
const handleFileDeleted = () => {
  // 필요시 추가 처리
}

// 공급업체 선택 처리
const handleSupplierSelect = (supplier: Partner) => {
  selectedSupplier.value = supplier
  formData.value.supplier_id = supplier.id
  showSupplierSearchModal.value = false
}

// 공급업체 선택 해제
const clearSupplier = () => {
  selectedSupplier.value = null
  formData.value.supplier_id = undefined
}

// 코드 마스터 간편등록 모달 열기
const openCodeMasterModal = (type: 'product_line' | 'part_group' | 'material' | 'treatment') => {
  codeMasterType.value = type
  showCodeMasterModal.value = true
}

// 코드 마스터 간편등록 모달 닫기
const closeCodeMasterModal = () => {
  showCodeMasterModal.value = false
}

// 제품라인 목록 새로고침
const refreshProductLines = async () => {
  try {
    const response = await productLineApi.getAll()
    productLines.value = response.data
  } catch (error) {
    console.error('제품라인 목록 새로고침 실패:', error)
  }
}

// 품목군 목록 새로고침
const refreshPartGroups = async () => {
  try {
    const response = await partGroupApi.getAll()
    partGroups.value = response.data
  } catch (error) {
    console.error('품목군 목록 새로고침 실패:', error)
  }
}

// 재질 목록 새로고침
const refreshMaterials = async () => {
  try {
    const response = await materialApi.getAll()
    materials.value = response.data
  } catch (error) {
    console.error('재질 목록 새로고침 실패:', error)
  }
}

// 후처리 목록 새로고침
const refreshTreatments = async () => {
  try {
    const response = await treatmentApi.getAll()
    treatments.value = response.data
  } catch (error) {
    console.error('후처리 목록 새로고침 실패:', error)
  }
}

// 코드 마스터 간편등록 완료
const handleCodeMasterAdded = async (id: number) => {
  if (codeMasterType.value === 'product_line') {
    await refreshProductLines()
    formData.value.product_line_id = id
  } else if (codeMasterType.value === 'part_group') {
    await refreshPartGroups()
    formData.value.part_group_id = id
  } else if (codeMasterType.value === 'material') {
    await refreshMaterials()
    formData.value.material_id = id
  } else if (codeMasterType.value === 'treatment') {
    await refreshTreatments()
    formData.value.treatment_id = id
  }
  closeCodeMasterModal()
}

// props 변경 감지
watch(
  () => props.initialData,
  (newData) => {
    if (newData) {
      formData.value = { ...formData.value, ...newData }
      // part_type_ids가 없으면 빈 배열로 초기화
      if (!formData.value.part_type_ids) {
        formData.value.part_type_ids = []
      }

      // 품목코드에서 prefix/suffix 추출 (수정 모드 또는 복제 모드)
      if (formData.value.item_code && !formData.value.item_code_prefix) {
        formData.value.item_code_prefix = formData.value.item_code.slice(0, 3)
      }

      // 수정 모드: 품목코드 뒤 2자리 기존값으로 초기화
      if (props.isEdit && formData.value.item_code) {
        const suffix = formData.value.item_code.slice(3, 5)
        if (suffix) {
          itemCodeSuffixInput.value = suffix
        }
      }

      // 수정 모드: 원본 품번 저장
      if (props.isEdit) {
        originalPartNumber.value = (newData as any).part_number_display || (newData as any).part_number || ''
        // 품번 수정 모드: localStorage에서 이전 선택값 복원
        const savedMode = localStorage.getItem(PART_NUMBER_MODE_KEY)
        partNumberEditMode.value = savedMode === 'direct' ? 'direct' : 'rule_a'
      }

      // 복제 모드: 신규 등록 + item_code 있음 (part_number 없음)
      // 품번규칙 A 모드 유지하여 새 품번 자동 생성
      if (!props.isEdit && formData.value.item_code && !formData.value.part_number) {
        // 품번규칙 A 모드 유지 (새 품번 생성)
        partNumberEditMode.value = 'rule_a'
        // suffix는 자동 생성하도록 비워둠
        itemCodeSuffixInput.value = ''
      }
      // 복제 모드: 신규 등록이지만 품번이 있는 경우 (구버전 호환)
      else if (!props.isEdit && formData.value.part_number) {
        partNumberEditMode.value = 'direct'
        // 중복 체크 수행 (복제된 품번은 당연히 중복이므로 경고 표시됨)
        debouncedCheckDuplicate(formData.value.part_number)
      }
    } else {
      resetForm()
      originalPartNumber.value = ''
      // 신규 등록: localStorage에서 이전 선택값 복원
      const savedMode = localStorage.getItem(PART_NUMBER_MODE_KEY)
      partNumberEditMode.value = savedMode === 'direct' ? 'direct' : 'rule_a'
    }
  },
  { immediate: true }
)

// 품목코드 관련 필드 변경 시 유사 코드 조회
watch(
  () => [formData.value.product_line_id, formData.value.part_group_id, formData.value.item_code_prefix],
  () => {
    if (partNumberEditMode.value === 'rule_a') {
      debouncedLoadSimilarCodes()
    }
  }
)

// 품번 입력 방식 변경 시 localStorage에 저장
watch(
  () => partNumberEditMode.value,
  (newMode) => {
    localStorage.setItem(PART_NUMBER_MODE_KEY, newMode)
  }
)

// 마운트 시 코드 마스터 로드
onMounted(() => {
  loadCodeMasters()
})
</script>
