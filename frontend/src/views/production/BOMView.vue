<template>
  <div class="p-4">
    <h1 class="text-2xl font-bold mb-4">BOM 관리 (Bill of Materials)</h1>

    <!-- 상위 부품 선택 -->
    <div class="bg-white rounded-lg shadow p-4 mb-4">
      <div class="flex justify-between items-center mb-3">
        <h2 class="text-lg font-semibold">상위 부품 선택</h2>
        <div class="flex gap-2">
          <button
            @click="showStartWizard = true"
            class="px-3 py-1 text-sm bg-violet-600 text-white rounded hover:bg-violet-700 flex items-center gap-1 font-medium"
            title="신규 제품 BOM을 처음부터 등록 (권장)"
          >
            ✨ 신규 제품 시작
          </button>
          <button
            @click="showUploadModal = true"
            class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center gap-1"
            title="엑셀 파일로 BOM 업로드"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            엑셀 업로드
          </button>
          <button
            @click="toggleParentPartList"
            :class="[
              'px-3 py-1 text-sm rounded',
              showParentPartList
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            ]"
          >
            {{ showParentPartList ? '목록 닫기' : '부품 목록' }}
          </button>
          <button
            @click="handleBOMRegisterClick"
            class="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
            title="새 BOM(조립품)을 등록하고 상위 부품으로 선택"
          >
            + BOM 등록
          </button>
        </div>
      </div>

      <!-- 선택된 부품 표시 (항상 표시) -->
      <div v-if="selectedParentPart" class="bg-blue-50 border border-blue-200 rounded-md p-3 mb-3">
        <div class="flex justify-between items-start">
          <div>
            <div class="text-sm text-blue-700">
              <span class="font-medium">선택된 부품:</span>
              <span v-if="selectedParentPart.is_classified !== false" class="font-mono ml-2">{{ selectedParentPart.part_number_display || selectedParentPart.part_number }}</span>
              <span v-else class="ml-2 text-xs font-semibold text-amber-600">미분류</span>
            </div>
            <div class="text-sm text-blue-600">{{ selectedParentPart.part_name }}</div>
            <div v-if="selectedParentPart.specification" class="text-xs text-blue-500 mt-1">{{ selectedParentPart.specification }}</div>
          </div>
          <button @click="clearSelection" class="text-xs text-red-500 hover:underline">선택 해제</button>
        </div>
      </div>

      <!-- 부품 목록 (토글) -->
      <div v-if="showParentPartList" class="border rounded-lg p-3 bg-gray-50">
        <!-- v0.12.0: 상세 필터 패널 -->
        <PartFilterPanel
          ref="parentFilterPanelRef"
          mode="bom"
          v-model="parentFilterValues"
          @search="handleParentFilterSearch"
          @reset="handleParentFilterReset"
        />

        <!-- 부품 목록 테이블 -->
        <div v-if="parentPartListLoading" class="text-center py-4 text-gray-500 text-sm">
          로딩 중...
        </div>
        <div v-else-if="parentPartList.length === 0" class="text-center py-4 text-gray-500 text-sm">
          검색 결과가 없습니다.
        </div>
        <div v-else class="max-h-64 overflow-y-auto">
          <table class="min-w-full divide-y divide-gray-200 text-sm">
            <thead class="bg-gray-100 sticky top-0">
              <tr>
                <th class="px-2 py-1.5 text-left text-xs font-medium text-gray-500 uppercase">품번</th>
                <th class="px-2 py-1.5 text-left text-xs font-medium text-gray-500 uppercase">품명</th>
                <th class="px-2 py-1.5 text-left text-xs font-medium text-gray-500 uppercase">설명</th>
                <th class="px-2 py-1.5 text-center text-xs font-medium text-gray-500 uppercase">대분류</th>
                <th class="px-2 py-1.5 text-center text-xs font-medium text-gray-500 uppercase">레벨</th>
                <th class="px-2 py-1.5 text-center text-xs font-medium text-gray-500 uppercase">BOM</th>
                <th class="px-2 py-1.5 text-center text-xs font-medium text-gray-500 uppercase w-24">작업</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr
                v-for="part in parentPartList"
                :key="part.id"
                :class="[
                  'hover:bg-blue-50 cursor-pointer',
                  selectedParentPart?.id === part.id ? 'bg-blue-100' : ''
                ]"
                @click="selectParentPart(part)"
              >
                <td class="px-2 py-1.5">
                  <span
                    class="font-mono text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                    @click.stop="openPartDetail(part.id)"
                    title="클릭하여 상세 보기"
                  ><template v-if="part.is_classified !== false">{{ part.part_number_display || part.part_number }}</template><template v-else><span class="text-amber-600 font-semibold not-italic">미분류</span></template></span>
                </td>
                <td class="px-2 py-1.5">{{ part.part_name }}</td>
                <td class="px-2 py-1.5 text-xs text-gray-500 break-words max-w-[300px]" :title="part.description">{{ part.description || '-' }}</td>
                <td class="px-2 py-1.5 text-center">
                  <span v-if="part.product_line" class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-blue-100 text-blue-700">
                    {{ part.product_line.code }}
                  </span>
                </td>
                <td class="px-2 py-1.5 text-center">
                  <span v-if="part.level" :class="['inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium', getLevelColorClass(part.level.code)]">
                    {{ part.level.code }}
                  </span>
                </td>
                <td class="px-2 py-1.5 text-center">
                  <span
                    v-if="(bomChildrenCounts[part.id] ?? 0) > 0"
                    class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700"
                    :title="`하위 부품 ${bomChildrenCounts[part.id]}건`"
                  >
                    <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M2 6a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1H8a3 3 0 00-3 3v1.5a1.5 1.5 0 01-3 0V6z" clip-rule="evenodd" /><path d="M6 12a2 2 0 012-2h8a2 2 0 012 2v2a2 2 0 01-2 2H2h2a2 2 0 002-2v-2z" /></svg>
                    {{ bomChildrenCounts[part.id] }}
                  </span>
                  <span
                    v-else
                    class="inline-flex items-center px-1.5 py-0.5 rounded text-xs text-gray-400"
                    title="하위 부품 없음"
                  >
                    -
                  </span>
                </td>
                <td class="px-2 py-1.5 text-center">
                  <div class="flex justify-center gap-1">
                    <button
                      @click.stop="selectParentPart(part)"
                      :class="[
                        'px-2 py-0.5 text-xs rounded',
                        selectedParentPart?.id === part.id
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      ]"
                    >
                      {{ selectedParentPart?.id === part.id ? '선택됨' : '선택' }}
                    </button>
                    <button
                      @click.stop="duplicatePart(part)"
                      class="px-2 py-0.5 text-xs rounded bg-purple-100 text-purple-700 hover:bg-purple-200"
                      title="부품 복제"
                    >
                      복제
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 페이지네이션 -->
        <div v-if="parentPartTotal > 0" class="flex justify-between items-center mt-2 text-xs text-gray-500">
          <span>총 {{ parentPartTotal }}건</span>
          <div class="flex gap-1">
            <button
              @click="parentPartPage > 1 && changeParentPartPage(parentPartPage - 1)"
              :disabled="parentPartPage <= 1"
              class="px-2 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
            >
              이전
            </button>
            <span class="px-2 py-1">{{ parentPartPage }} / {{ Math.ceil(parentPartTotal / parentPartPageSize) }}</span>
            <button
              @click="parentPartPage < Math.ceil(parentPartTotal / parentPartPageSize) && changeParentPartPage(parentPartPage + 1)"
              :disabled="parentPartPage >= Math.ceil(parentPartTotal / parentPartPageSize)"
              class="px-2 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
            >
              다음
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 완결성 체크 패널 (BOM 개편 2026-09) -->
    <div v-if="selectedParentPart && bomTree.length > 0" class="mb-3">
      <BomCompleteness :tree="bomTree" :price-map="treePriceMap" @view-detail="openPartDetail" />
    </div>

    <!-- BOM 관리 영역 (리사이즈 가능) -->
    <div v-if="selectedParentPart" class="flex gap-1 h-[calc(100vh-280px)] min-h-[500px]">
      <!-- 왼쪽: BOM 구성 + 원가 정보 -->
      <div
        class="bg-white rounded-lg shadow p-4 flex flex-col"
        :style="{ width: leftPanelWidth + '%', minWidth: '400px' }"
      >
        <div class="flex justify-between items-center mb-3 flex-shrink-0">
          <h2 class="text-lg font-semibold">BOM 구성</h2>
          <div class="flex gap-2">
            <button
              @click="toggleQuickAddMode"
              :class="[
                'px-3 py-1 text-sm rounded',
                quickAddMode
                  ? 'bg-yellow-500 text-white hover:bg-yellow-600'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              ]"
            >
              {{ quickAddMode ? '빠른추가 ON' : '빠른추가' }}
            </button>
            <button
              @click="openAddChildModal"
              class="px-3 py-1 bg-green-500 text-white text-sm rounded hover:bg-green-600"
            >
              + 기존부품 추가
            </button>
            <button
              @click="openNewPartModal"
              class="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
              title="새 부품을 등록하고 BOM에 추가"
            >
              + 새부품
            </button>
            <button
              @click="recalculateBOMCost"
              class="px-3 py-1 bg-orange-500 text-white text-sm rounded hover:bg-orange-600"
              title="BOM 원가를 재계산합니다"
              :disabled="isRecalculating"
            >
              {{ isRecalculating ? '계산중...' : '원가 재계산' }}
            </button>
            <button
              @click="goEditor"
              class="px-3 py-1 text-sm rounded bg-violet-600 text-white hover:bg-violet-700"
              title="전용 편집 화면에서 부품을 끌어다 BOM 구조를 조립"
            >
              ✎ BOM 편집
            </button>
            <button
              @click="treeEditMode = !treeEditMode"
              :class="['px-3 py-1 text-sm rounded', treeEditMode ? 'bg-violet-100 text-violet-700 ring-1 ring-violet-400' : 'bg-gray-100 text-gray-600 hover:bg-gray-200']"
              title="이 화면에서 간단히 편집(드래그 이동·수량·첨부)"
            >
              🧩 간편 편집{{ treeEditMode ? ' ON' : '' }}
            </button>
          </div>
        </div>

        <!-- BOM 트리 편집기 (드래그·인라인·첨부·분류) -->
        <div v-if="treeEditMode && selectedParentPart" class="mb-4">
          <BomTreeEditor
            :root-part-id="selectedParentPart.id"
            :root-label="selectedParentPart.is_classified === false ? (selectedParentPart.part_name || '미분류 부품') : (selectedParentPart.part_number_display || selectedParentPart.part_number)"
            :key="'bte-' + selectedParentPart.id"
          />
        </div>

        <!-- 빠른 추가 모드 -->
        <div v-if="quickAddMode" class="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4 flex-shrink-0">
          <div class="text-sm text-yellow-700 mb-2">
            <strong>빠른 추가 모드:</strong> 품번/품명 검색 후 Enter로 추가, Tab으로 수량 이동
          </div>
          <div class="flex gap-2 items-end">
            <div class="flex-1">
              <label class="block text-xs text-gray-600 mb-1">부품 검색</label>
              <input
                ref="quickSearchInput"
                v-model="quickAddSearch"
                type="text"
                placeholder="품번 또는 품명..."
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-yellow-500 focus:border-yellow-500"
                @input="searchQuickAdd"
                @keydown.enter.prevent="addQuickPart"
                @keydown.tab.prevent="focusQuickQty"
              />
              <!-- 검색 결과 -->
              <div v-if="quickAddResults.length > 0 || (quickAddSearch.length > 0 && quickSearchDone)" class="relative">
                <div class="absolute z-20 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-40 overflow-y-auto mt-1">
                  <div
                    v-for="(part, idx) in quickAddResults"
                    :key="part.id"
                    :class="['px-3 py-2 cursor-pointer', idx === quickAddSelectedIdx ? 'bg-yellow-100' : 'hover:bg-gray-100']"
                    @click="selectQuickAddPart(part)"
                  >
                    <span class="font-medium">{{ part.part_number }}</span>
                    <span class="text-gray-500 ml-2">{{ part.part_name }}</span>
                  </div>
                  <!-- 검색 결과 없음 - 새 부품 등록 유도 -->
                  <div
                    v-if="quickAddResults.length === 0 && quickSearchDone"
                    class="px-3 py-2 text-gray-500 text-sm"
                  >
                    <div class="mb-2">검색 결과가 없습니다.</div>
                    <button
                      @click="openNewPartModal"
                      class="text-blue-600 hover:text-blue-800 underline"
                    >
                      + 새 부품 등록하기
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div class="w-24">
              <label class="block text-xs text-gray-600 mb-1">수량</label>
              <input
                ref="quickQtyInput"
                v-model.number="quickAddQty"
                type="number"
                min="1"
                step="1"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-yellow-500 focus:border-yellow-500"
                @keydown.enter.prevent="addQuickPart"
              />
            </div>
            <button
              @click="addQuickPart"
              :disabled="!quickAddSelectedPart"
              class="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600 disabled:opacity-50"
            >
              추가
            </button>
          </div>
          <div v-if="quickAddSelectedPart" class="mt-2 text-sm text-yellow-700">
            선택: <span class="font-medium">{{ quickAddSelectedPart.part_number }}</span> - {{ quickAddSelectedPart.part_name }}
          </div>
        </div>

        <!-- BOM 목록 영역 (flex-1로 남은 공간 차지, 스크롤 가능) -->
        <div class="flex-1 overflow-hidden flex flex-col min-h-0">
          <!-- 로딩 -->
          <div v-if="loadingTree" class="flex justify-center py-8">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>

          <!-- 빈 상태 -->
          <div v-else-if="bomChildren.length === 0" class="text-center py-8 text-gray-500">
            <svg class="mx-auto h-12 w-12 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <p>등록된 하위 부품이 없습니다.</p>
            <p class="text-sm">위의 "빠른추가" 또는 "+ 부품 추가" 버튼을 사용해주세요.</p>
          </div>

          <!-- BOM 목록 테이블 -->
          <div v-else class="overflow-auto flex-1">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase w-10">#</th>
                  <th class="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase">품번</th>
                  <th class="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase">품명</th>
                  <th class="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase">설명</th>
                  <th class="px-2 py-2 text-center text-xs font-medium text-gray-500 uppercase w-20">수량</th>
                  <th class="px-2 py-2 text-right text-xs font-medium text-gray-500 uppercase w-24">단가</th>
                  <th class="px-2 py-2 text-right text-xs font-medium text-gray-500 uppercase w-24">금액</th>
                  <th class="px-2 py-2 text-center text-xs font-medium text-gray-500 uppercase w-16">작업</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr
                  v-for="(bom, index) in bomChildren"
                  :key="bom.id"
                  class="hover:bg-gray-50 group"
                  draggable="true"
                  @dragstart="onDragStart($event, index)"
                  @dragover.prevent="onDragOver($event, index)"
                  @drop="onDrop($event, index)"
                  @dragend="onDragEnd"
                  :class="{ 'bg-blue-50': dragOverIndex === index }"
                >
                <td class="px-2 py-2 text-sm text-gray-400 cursor-move">
                  <span class="group-hover:hidden">{{ index + 1 }}</span>
                  <svg class="w-4 h-4 hidden group-hover:block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16" />
                  </svg>
                </td>
                <td class="px-2 py-2 text-sm">
                  <span
                    class="font-medium font-mono text-xs text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                    @click="openPartDetail(bom.child_part_id)"
                    title="클릭하여 상세 보기"
                  ><template v-if="bom.child_part?.is_classified !== false">{{ bom.child_part?.part_number_display || bom.child_part?.part_number }}</template><template v-else><span class="text-amber-600">미분류</span></template></span>
                </td>
                <td class="px-2 py-2 text-sm">
                  <div class="text-xs">{{ bom.child_part?.part_name }}</div>
                </td>
                <td class="px-2 py-2 text-sm">
                  <div class="text-xs text-gray-500 break-words" :title="bom.child_part?.description">{{ bom.child_part?.description || '-' }}</div>
                </td>
                <td class="px-2 py-2 text-sm text-center">
                  <!-- 인라인 수량 편집 -->
                  <div v-if="editingQtyId === bom.id" class="flex items-center justify-center gap-1">
                    <input
                      ref="qtyInput"
                      v-model.number="editingQtyValue"
                      type="number"
                      min="1"
                      step="1"
                      class="w-14 px-1 py-1 text-center text-xs border rounded focus:ring-blue-500 focus:border-blue-500"
                      @keydown.enter="saveInlineQty(bom.id)"
                      @keydown.escape="cancelInlineQty"
                      @blur="saveInlineQty(bom.id)"
                    />
                  </div>
                  <div
                    v-else
                    class="cursor-pointer hover:bg-blue-100 rounded px-1 py-0.5 inline-block text-xs"
                    @click="startInlineQtyEdit(bom)"
                    title="클릭하여 수량 수정"
                  >
                    <span class="font-medium">{{ bom.quantity }}</span>
                  </div>
                </td>
                <td class="px-2 py-2 text-sm text-right">
                  <span class="text-xs text-gray-600">
                    {{ formatPrice(bomPriceMap[bom.child_part_id]?.unit_price) }}
                  </span>
                </td>
                <td class="px-2 py-2 text-sm text-right">
                  <span class="text-xs font-medium text-blue-600">
                    {{ formatPrice(getLineTotal(bom)) }}
                  </span>
                </td>
                <td class="px-2 py-2 text-center">
                  <div class="flex justify-center gap-0.5">
                    <button
                      @click="openPartDetail(bom.child_part_id)"
                      class="text-gray-600 hover:text-gray-800 p-0.5"
                      title="상세 보기"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </button>
                    <button
                      @click="openEditModal(bom)"
                      class="text-blue-600 hover:text-blue-800 p-0.5"
                      title="수정"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                    <button
                      @click="deleteBOM(bom.id)"
                      class="text-red-600 hover:text-red-800 p-0.5"
                      title="삭제"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
            </table>

            <!-- 총 개수 및 합계 -->
            <div class="mt-3 flex justify-between items-center text-sm text-gray-500 border-t pt-2">
              <span>총 <span class="font-medium">{{ bomChildren.length }}</span>개 부품</span>
              <span class="font-medium text-blue-700">
                합계: {{ formatPrice(bomTotalCost) }}
              </span>
            </div>
          </div>
        </div>

        <!-- 원가 정보 (BOM 구성 하단) -->
        <div class="mt-3 pt-3 border-t flex-shrink-0 max-h-[200px] overflow-auto">
          <PartPriceInfoCard
            v-if="selectedParentPart"
            :part-id="selectedParentPart.id"
            @updated="onPriceUpdated"
          />
        </div>
      </div>

      <!-- 리사이즈 핸들 -->
      <div
        class="w-2 bg-gray-200 hover:bg-blue-400 cursor-col-resize flex-shrink-0 rounded transition-colors flex items-center justify-center"
        @mousedown="startResize"
      >
        <div class="w-0.5 h-8 bg-gray-400 rounded"></div>
      </div>

      <!-- 오른쪽: BOM 트리 뷰 -->
      <div
        class="bg-white rounded-lg shadow p-4 flex flex-col overflow-hidden"
        :style="{ width: (100 - leftPanelWidth) + '%' }"
      >
        <div class="flex justify-between items-center mb-3 flex-shrink-0">
          <h2 class="text-lg font-semibold">BOM 트리</h2>
          <div class="flex gap-2">
            <button
              v-if="bomChildren.length > 0"
              @click="exportBOMExcel"
              :disabled="isExporting"
              class="px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50 flex items-center gap-1"
              title="BOM을 엑셀로 내보내기"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {{ isExporting ? '내보내기...' : '엑셀' }}
            </button>
            <button
              @click="showUploadModal = true"
              class="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center gap-1"
              title="엑셀 파일로 BOM 업로드"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              엑셀 업로드
            </button>
            <button
              v-if="bomChildren.length > 0"
              @click="openCopyModal"
              class="px-2 py-1 text-xs bg-purple-500 text-white rounded hover:bg-purple-600"
              title="다른 부품으로 BOM 복사"
            >
              BOM 복사
            </button>
          </div>
        </div>

        <!-- 로딩 -->
        <div v-if="loadingTree" class="flex justify-center py-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>

        <!-- 빈 상태 -->
        <div v-else-if="bomTree.length === 0" class="text-center py-8 text-gray-500">
          <p>BOM 트리가 없습니다.</p>
        </div>

        <!-- 트리 뷰 -->
        <div v-else class="border rounded-md p-3 text-sm flex-1 overflow-y-auto">
          <!-- 최상위 부품 (선택된 부품) -->
          <div class="flex items-center mb-2 font-medium text-blue-700">
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <span>{{ selectedParentPart?.part_number }}</span>
          </div>
          <!-- 재귀적 트리 노드 -->
          <BOMTreeNodeComponent
            v-for="node in bomTree"
            :key="node.id"
            :node="node"
            :level="1"
            :price-map="treePriceMap"
            @view-detail="openPartDetail"
          />
        </div>
      </div>
    </div>

    <!-- 선택되지 않은 상태 -->
    <div v-else class="bg-white rounded-lg shadow p-8">
      <div class="max-w-2xl mx-auto">
        <!-- 신규 제품 시작 (권장 표준 경로) -->
        <div class="rounded-xl border-2 border-violet-200 bg-violet-50/60 p-6 text-center">
          <div class="text-4xl mb-2">🧩</div>
          <p class="text-lg font-semibold text-gray-800">신규 제품 BOM을 등록하시나요?</p>
          <p class="text-sm text-gray-600 mt-1">제품 이름만 정하면 바로 트리에서 구조를 짤 수 있습니다. 품번·레벨은 나중에 부여해도 됩니다.</p>
          <!-- 표준 흐름 -->
          <div class="flex items-center justify-center flex-wrap gap-x-2 gap-y-1 mt-4 text-xs text-violet-700">
            <span class="px-2 py-1 bg-white rounded-full border border-violet-200 font-medium">① 제품 이름</span>
            <span class="text-violet-300">→</span>
            <span class="px-2 py-1 bg-white rounded-full border border-violet-200">② 하위 부품(이름만)</span>
            <span class="text-violet-300">→</span>
            <span class="px-2 py-1 bg-white rounded-full border border-violet-200">③ 도면 첨부</span>
            <span class="text-violet-300">→</span>
            <span class="px-2 py-1 bg-white rounded-full border border-violet-200">④ 코드 부여</span>
          </div>
          <button
            @click="showStartWizard = true"
            class="mt-5 px-6 py-2.5 bg-violet-600 text-white rounded-lg hover:bg-violet-700 font-medium shadow-sm"
          >
            ✨ 신규 제품 시작하기
          </button>
        </div>

        <!-- 대안 경로 -->
        <div class="grid grid-cols-2 gap-3 mt-4">
          <button
            @click="showUploadModal = true"
            class="rounded-lg border border-gray-200 bg-white p-4 text-left hover:border-blue-300 hover:bg-blue-50/40 transition"
          >
            <div class="text-sm font-semibold text-gray-800 flex items-center gap-1.5">📊 엑셀로 일괄 등록</div>
            <div class="text-xs text-gray-500 mt-1">부품·수량이 이미 표로 정리돼 있을 때 (대량)</div>
          </button>
          <button
            @click="toggleParentPartList(); scrollTop()"
            class="rounded-lg border border-gray-200 bg-white p-4 text-left hover:border-gray-300 hover:bg-gray-50 transition"
          >
            <div class="text-sm font-semibold text-gray-800 flex items-center gap-1.5">🔍 기존 제품 선택</div>
            <div class="text-xs text-gray-500 mt-1">이미 등록된 제품의 BOM을 이어서 편집</div>
          </button>
        </div>
      </div>
    </div>

    <!-- 하위 부품 추가/수정 모달 -->
    <BOMFormModal
      :show="showFormModal"
      :mode="formMode"
      :parent-part="selectedParentPart"
      :bom-data="editingBOM"
      @close="closeFormModal"
      @saved="onBOMSaved"
    />

    <!-- 부품 등록/수정 모달 (BOM에서 직접 부품 생성/수정) -->
    <PartFormModal
      :show="showNewPartModal"
      :is-edit="isEditingPart"
      :initial-data="editingPartData"
      mode="bom"
      @close="closeNewPartModal"
      @submit="handlePartFormSubmit"
    />

    <!-- 부품 다중 선택 모달 (BOM 추가용) -->
    <PartSearchModal
      :show="showPartSearchModal"
      :multi-select="true"
      :exclude-part-ids="excludedPartIds"
      @close="closePartSearchModal"
      @select-multiple="handleMultiplePartsSelected"
    />

    <!-- 새 부품 등록 후 BOM 추가 확인 모달 -->
    <div
      v-if="showAddToBomConfirm"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-[70]"
      
    >
      <div class="relative top-1/4 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">BOM에 추가</h3>
          <button @click="cancelAddToBom" class="text-gray-400 hover:text-gray-600">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="bg-green-50 border border-green-200 rounded-md p-3 mb-4">
          <div class="text-sm text-green-700">
            <strong>{{ newlyCreatedPart?.part_number }}</strong> 부품이 등록되었습니다.<br/>
            이 부품을 현재 BOM에 추가하시겠습니까?
          </div>
        </div>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">수량</label>
          <input
            v-model.number="newPartQty"
            type="number"
            min="1"
            step="1"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div class="flex justify-end gap-2">
          <button
            @click="cancelAddToBom"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            나중에
          </button>
          <button
            @click="confirmAddToBom"
            :disabled="isAddingToBom"
            class="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
          >
            {{ isAddingToBom ? '추가 중...' : 'BOM에 추가' }}
          </button>
        </div>
      </div>
    </div>

    <!-- BOM 복사 모달 -->
    <div
      v-if="showCopyModal"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
      
    >
      <div class="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">BOM 복사</h3>
          <button @click="closeCopyModal" class="text-gray-400 hover:text-gray-600">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="bg-blue-50 border border-blue-200 rounded-md p-3 mb-4">
          <div class="text-sm text-blue-700">
            <strong>{{ selectedParentPart?.part_number }}</strong>의 BOM을<br/>
            다른 부품으로 복사합니다.
          </div>
        </div>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">복사할 대상 부품</label>
          <input
            v-model="copyTargetSearch"
            type="text"
            placeholder="품번 또는 품명으로 검색..."
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            @input="searchCopyTarget"
          />
          <!-- 검색 결과 -->
          <div v-if="copyTargetResults.length > 0" class="mt-1 border rounded-md max-h-40 overflow-y-auto">
            <div
              v-for="part in copyTargetResults"
              :key="part.id"
              class="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
              @click="selectCopyTarget(part)"
            >
              <span class="font-medium">{{ part.part_number }}</span>
              <span class="text-gray-500 ml-2">{{ part.part_name }}</span>
            </div>
          </div>
          <!-- 선택된 대상 -->
          <div v-if="copyTargetPart" class="mt-2 bg-green-50 border border-green-200 rounded-md p-2">
            <div class="flex justify-between items-center text-sm">
              <div>
                <span class="font-medium text-green-700">{{ copyTargetPart.part_number }}</span>
                <span class="text-green-600 ml-2">{{ copyTargetPart.part_name }}</span>
              </div>
              <button @click="copyTargetPart = null" class="text-red-500">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-2">
          <button
            @click="closeCopyModal"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            취소
          </button>
          <button
            @click="executeCopyBOM"
            :disabled="!copyTargetPart || isCopying"
            class="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-50"
          >
            {{ isCopying ? '복사 중...' : '복사 실행' }}
          </button>
        </div>
      </div>
    </div>

    <!-- BOM 엑셀 업로드 모달 (v0.23.0) -->
    <BOMUploadModal
      :show="showUploadModal"
      :parent-part-id="selectedParentPart?.id"
      :parent-part-number="selectedParentPart?.part_number_display || selectedParentPart?.part_number"
      @close="showUploadModal = false"
      @uploaded="onBOMUploaded"
    />


    <!-- 부품 상세 보기 모달 -->
    <PartDetailModal
      :show="showDetailModal"
      :part-id="detailPartId"
      @close="closePartDetail"
      @edit="handlePartEdit"
    />

    <!-- 신규 제품 BOM 시작 위저드 (BOM 개편 2026-09) -->
    <BomStartWizard
      :show="showStartWizard"
      @close="showStartWizard = false"
      @started="onWizardStarted"
      @use-existing="onWizardUseExisting"
      @excel="onWizardExcel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { partApi, type Part, type PartListItem, type PartCreate, type PartSearchParams } from '@/api/parts'
import { bomApi, type BOMDetailResponse, type BOMTreeNode, type BOMItemCreate } from '@/api/bom'
import { levelApi, productLineApi, type CodeMaster, type LevelCodeMaster } from '@/api/codeMaster'
import { priceApi, type PartPriceInfo } from '@/api/price'
import BOMTreeNodeComponent from '@/views/production/components/BOMTreeNode.vue'
import BOMFormModal from '@/views/production/components/BOMFormModal.vue'
import PartFormModal from '@/views/production/components/PartFormModal.vue'
import PartSearchModal from '@/views/production/components/PartSearchModal.vue'
import PartPriceInfoCard from '@/views/production/components/PartPriceInfoCard.vue'
import PartFilterPanel, { type FilterValues } from '@/views/production/components/PartFilterPanel.vue'
import PartDetailModal from '@/views/production/components/PartDetailModal.vue'
import BOMUploadModal from '@/views/production/components/BOMUploadModal.vue'
import BomTreeEditor from '@/views/production/bom/BomTreeEditor.vue'
import BomStartWizard from '@/views/production/bom/BomStartWizard.vue'
import BomCompleteness from '@/views/production/bom/BomCompleteness.vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'

const router = useRouter()
// 전용 BOM 편집 화면으로 이동(선택된 상위 부품 기준)
function goEditor() {
  if (!selectedParentPart.value) { toast.warning('상위 부품을 먼저 선택해주세요.'); return }
  router.push({ name: 'bom-editor', params: { partId: selectedParentPart.value.id } })
}

// BOM 개편: 트리 편집 모드
const treeEditMode = ref(false)

// BOM 개편 2026-09: 신규 제품 시작 위저드
const showStartWizard = ref(false)

// 위저드에서 새 제품 생성 완료 → 전용 편집 화면으로 이동
function onWizardStarted(part: PartListItem) {
  showStartWizard.value = false
  router.push({ name: 'bom-editor', params: { partId: part.id } })
}

// 위저드에서 유사 기존 제품 선택 → 전용 편집 화면으로 이동
function onWizardUseExisting(part: PartListItem) {
  showStartWizard.value = false
  router.push({ name: 'bom-editor', params: { partId: part.id } })
}

// 위저드에서 엑셀 경로 선택
function onWizardExcel() {
  showStartWizard.value = false
  showUploadModal.value = true
}

// 빈 화면에서 '기존 제품 선택' → 상단으로 스크롤
function scrollTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
import { handleApiError } from '@/utils/errorHandler'

// 토스트 알림
const toast = useToast()

// 코드 마스터 데이터
const levels = ref<LevelCodeMaster[]>([])
const productLines = ref<CodeMaster[]>([])

// v0.12.0: BOM 관리 페이지용 조립품 레벨만 표시 (is_assembly=true: C, S, P, K, F)
const assemblyLevels = computed(() => levels.value.filter(l => l.is_assembly))

// v0.21.0: 레벨별 색상 구분 함수
function getLevelColorClass(levelCode: string): string {
  const colorMap: Record<string, string> = {
    'M': 'bg-yellow-100 text-yellow-800',      // 내부공정
    'O': 'bg-orange-100 text-orange-800',      // 외주공정
    'R': 'bg-green-100 text-green-800',        // 원자재 (단품)
    'C': 'bg-blue-100 text-blue-800',          // 조합부품
    'S': 'bg-indigo-100 text-indigo-800',      // 서브어셈블리
    'P': 'bg-pink-100 text-pink-800',          // 패키지
    'K': 'bg-cyan-100 text-cyan-800',          // 키트
    'F': 'bg-red-100 text-red-800',            // 최종품 (완제품)
  }
  return colorMap[levelCode] || 'bg-purple-100 text-purple-700'
}

// 부품 검색 (기존 - 레거시 유지)
const partSearchKeyword = ref('')
const searchedParts = ref<PartListItem[]>([])
const showPartDropdown = ref(false)
const selectedParentPart = ref<PartListItem | null>(null)

// 상위 부품 목록 (새로운 UI)
const showParentPartList = ref(false)
const parentPartList = ref<PartListItem[]>([])
const parentPartListLoading = ref(false)
const parentPartTotal = ref(0)
const parentPartPage = ref(1)
const parentPartPageSize = ref(10)
const bomChildrenCounts = ref<Record<number, number>>({})
const parentPartSearch = ref<{
  keyword: string
  product_line_id: number | undefined
  level_id: number | undefined
}>({
  keyword: '',
  product_line_id: undefined,
  level_id: undefined
})

// v0.12.0: 상세 필터
const parentFilterPanelRef = ref<InstanceType<typeof PartFilterPanel> | null>(null)
const parentFilterValues = ref<FilterValues>({})
const currentParentFilters = ref<FilterValues>({})

// BOM 데이터
const bomChildren = ref<BOMDetailResponse[]>([])
const bomTree = ref<BOMTreeNode[]>([])
const loadingTree = ref(false)

// 패널 리사이즈
const leftPanelWidth = ref(60) // 초기값 60% (6:4 비율)
const isResizing = ref(false)

function startResize(e: MouseEvent) {
  isResizing.value = true
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function onResize(e: MouseEvent) {
  if (!isResizing.value) return
  const container = document.querySelector('.flex.gap-1.h-\\[calc\\(100vh-280px\\)\\]') as HTMLElement
  if (!container) return

  const containerRect = container.getBoundingClientRect()
  const newWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100

  // 최소 30%, 최대 70%로 제한
  leftPanelWidth.value = Math.min(70, Math.max(30, newWidth))
}

function stopResize() {
  isResizing.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

// 부품별 가격 정보 맵 (목록용)
const bomPriceMap = ref<Record<number, { unit_price: number; currency: string }>>({})

// 트리 전체 가격 정보 맵 (트리용 - 모든 하위 부품 포함)
const treePriceMap = ref<Record<number, { unit_price: number; currency: string }>>({})

// BOM 총 원가 계산
const bomTotalCost = computed(() => {
  let total = 0
  bomChildren.value.forEach(bom => {
    const priceInfo = bomPriceMap.value[bom.child_part_id]
    if (priceInfo?.unit_price) {
      total += priceInfo.unit_price * bom.quantity
    }
  })
  return total
})

// 라인별 금액 계산
function getLineTotal(bom: BOMDetailResponse): number {
  const priceInfo = bomPriceMap.value[bom.child_part_id]
  if (priceInfo?.unit_price) {
    return priceInfo.unit_price * bom.quantity
  }
  return 0
}

// 가격 포맷팅 (소수점 없이 표시)
function formatPrice(amount: number | undefined): string {
  if (amount === undefined || amount === null || amount === 0) return '-'
  return '₩' + Math.round(amount).toLocaleString('ko-KR')
}

// 모달
const showFormModal = ref(false)
const formMode = ref<'add' | 'edit'>('add')
const editingBOM = ref<BOMDetailResponse | null>(null)

// 새 부품 등록/수정 모달
const showNewPartModal = ref(false)
const isEditingPart = ref(false)
const editingPartData = ref<Part | null>(null)
const showAddToBomConfirm = ref(false)
const newlyCreatedPart = ref<{ id: number; part_number: string; part_name: string } | null>(null)
const newPartQty = ref(1)
const isAddingToBom = ref(false)
const isCreatingParentPart = ref(false) // 상위 부품 등록 여부

// 부품 다중 선택 모달
const showPartSearchModal = ref(false)
const excludedPartIds = computed(() => {
  const ids = new Set<number>()
  if (selectedParentPart.value) {
    ids.add(selectedParentPart.value.id)
  }
  bomChildren.value.forEach(b => ids.add(b.child_part_id))
  return Array.from(ids)
})

// 빠른 추가 모드
const quickAddMode = ref(false)
const quickAddSearch = ref('')
const quickAddResults = ref<PartListItem[]>([])
const quickAddSelectedPart = ref<PartListItem | null>(null)
const quickAddSelectedIdx = ref(0)
const quickAddQty = ref(1)
const quickSearchDone = ref(false) // 검색 완료 여부
const quickSearchInput = ref<HTMLInputElement | null>(null)
const quickQtyInput = ref<HTMLInputElement | null>(null)

// 인라인 수량 편집
const editingQtyId = ref<number | null>(null)
const editingQtyValue = ref(1)
const qtyInput = ref<HTMLInputElement | null>(null)

// 원가 재계산
const isRecalculating = ref(false)

// 드래그앤드롭
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

// BOM 엑셀 업로드 (v0.23.0)
const showUploadModal = ref(false)

// BOM 복사
const showCopyModal = ref(false)
const copyTargetSearch = ref('')
const copyTargetResults = ref<PartListItem[]>([])
const copyTargetPart = ref<PartListItem | null>(null)
const isCopying = ref(false)

// BOM 엑셀 내보내기
const isExporting = ref(false)

// 부품 상세 보기 모달
const showDetailModal = ref(false)
const detailPartId = ref<number | null>(null)

// 부품 검색
let searchTimeout: ReturnType<typeof setTimeout> | null = null
const searchParts = () => {
  if (searchTimeout) clearTimeout(searchTimeout)

  searchTimeout = setTimeout(async () => {
    if (!partSearchKeyword.value.trim()) {
      searchedParts.value = []
      showPartDropdown.value = false
      return
    }

    try {
      // 단종 부품도 검색 가능하도록 is_active 필터 제거
      const response = await partApi.getAll({
        keyword: partSearchKeyword.value,
        limit: 20
      })
      searchedParts.value = response.data.items
      showPartDropdown.value = true
    } catch (error) {
      console.error('부품 검색 실패:', error)
    }
  }, 300)
}

// 첫 번째 검색 결과 선택
const selectFirstPart = () => {
  const firstPart = searchedParts.value[0]
  if (firstPart) {
    selectParentPart(firstPart)
  }
}

// 상위 부품 선택
const selectParentPart = (part: PartListItem) => {
  selectedParentPart.value = part
  partSearchKeyword.value = ''
  searchedParts.value = []
  showPartDropdown.value = false
  loadBOMData()
}

// 선택 해제
const clearSelection = () => {
  selectedParentPart.value = null
  bomChildren.value = []
  bomTree.value = []
  quickAddMode.value = false
}

// 코드 마스터 로드
const loadCodeMasters = async () => {
  try {
    const [levelsRes, productLinesRes] = await Promise.all([
      levelApi.getAll(),
      productLineApi.getAll()
    ])
    levels.value = levelsRes.data
    productLines.value = productLinesRes.data
  } catch (error) {
    console.error('코드 마스터 로드 실패:', error)
  }
}

// 상위 부품 목록 토글
const toggleParentPartList = () => {
  showParentPartList.value = !showParentPartList.value
  // 토글 시 필터 패널이 초기화되고 자동으로 검색 트리거됨
}

// v0.12.0: 필터 검색 핸들러
const handleParentFilterSearch = (filters: FilterValues) => {
  currentParentFilters.value = { ...filters }
  parentPartPage.value = 1
  searchParentParts()
}

// v0.12.0: 필터 초기화 핸들러
const handleParentFilterReset = () => {
  currentParentFilters.value = {}
  parentFilterValues.value = {}
  parentPartPage.value = 1
  searchParentParts()
}

// 상위 부품 검색
const searchParentParts = async () => {
  parentPartListLoading.value = true
  try {
    // level_ids 배열을 콤마 구분 문자열로 변환
    const levelIdsParam = currentParentFilters.value.level_ids && currentParentFilters.value.level_ids.length > 0
      ? currentParentFilters.value.level_ids.join(',')
      : undefined

    // development_type_ids 배열을 콤마 구분 문자열로 변환
    const devTypeIdsParam = currentParentFilters.value.development_type_ids && currentParentFilters.value.development_type_ids.length > 0
      ? currentParentFilters.value.development_type_ids.join(',')
      : undefined

    // 단종 부품도 검색 가능하도록 is_active 필터 제거
    const params: PartSearchParams = {
      keyword: currentParentFilters.value.keyword || undefined,
      level_ids: levelIdsParam,
      product_line_id: currentParentFilters.value.product_line_id,
      part_group_id: currentParentFilters.value.part_group_id,
      development_type_ids: devTypeIdsParam,
      material_id: currentParentFilters.value.material_id,
      treatment_id: currentParentFilters.value.treatment_id,
      drawing_type_id: currentParentFilters.value.drawing_type_id,
      procurement_type_id: currentParentFilters.value.procurement_type_id,
      unit_id: currentParentFilters.value.unit_id,
      status: currentParentFilters.value.status,
      classified: currentParentFilters.value.classified,
      skip: (parentPartPage.value - 1) * parentPartPageSize.value,
      limit: parentPartPageSize.value,
      order_by: 'created_at',
      order_desc: true
    }

    const response = await partApi.getAll(params)
    parentPartList.value = response.data.items
    parentPartTotal.value = response.data.total

    // 하위 BOM 개수 조회
    const partIds = response.data.items.map((p: PartListItem) => p.id)
    if (partIds.length > 0) {
      try {
        const countRes = await bomApi.getChildrenCountBatch(partIds)
        bomChildrenCounts.value = countRes.data
      } catch {
        bomChildrenCounts.value = {}
      }
    }
  } catch (error) {
    console.error('상위 부품 검색 실패:', error)
    parentPartList.value = []
    parentPartTotal.value = 0
  } finally {
    parentPartListLoading.value = false
  }
}

// 상위 부품 페이지 변경
const changeParentPartPage = async (page: number) => {
  parentPartPage.value = page
  await searchParentParts()
}

// BOM 데이터 로드
const loadBOMData = async () => {
  if (!selectedParentPart.value) return

  loadingTree.value = true
  try {
    // 하위 부품 목록 조회
    const childrenResponse = await bomApi.getChildren(selectedParentPart.value.id)
    bomChildren.value = childrenResponse.data

    // 트리 구조 조회
    const treeResponse = await bomApi.getTree(selectedParentPart.value.id)
    bomTree.value = treeResponse.data

    // 부품별 가격 정보 로드
    await loadBOMPrices()
  } catch (error) {
    console.error('BOM 데이터 로드 실패:', error)
  } finally {
    loadingTree.value = false
  }
}

// 트리에서 모든 part_id 추출 (재귀)
function collectPartIdsFromTree(nodes: BOMTreeNode[]): number[] {
  const ids: number[] = []
  function traverse(nodeList: BOMTreeNode[]) {
    for (const node of nodeList) {
      if (node.part_id) {
        ids.push(node.part_id)
      }
      if (node.children && node.children.length > 0) {
        traverse(node.children)
      }
    }
  }
  traverse(nodes)
  return ids
}

// BOM 부품들의 가격 정보 로드
const loadBOMPrices = async () => {
  // 목록용 part_id
  const listPartIds = bomChildren.value.map(b => b.child_part_id)
  // 트리용 part_id (트리의 모든 노드)
  const treePartIds = collectPartIdsFromTree(bomTree.value)
  // 중복 제거한 전체 part_id
  const allPartIds = [...new Set([...listPartIds, ...treePartIds])]

  if (allPartIds.length === 0) {
    bomPriceMap.value = {}
    treePriceMap.value = {}
    return
  }

  // 각 부품의 가격 정보를 병렬로 조회
  const pricePromises = allPartIds.map(async (partId) => {
    try {
      const priceInfo = await priceApi.getPartPriceInfo(partId)

      // v0.12.0: BOM 원가 계산 방식 개선
      // cost_type에 따라 단가 결정:
      // - BOM 타입: calculated_cost (하위 BOM 합산 원가) 사용
      // - MANUAL 타입: 기준단가 > 재고단가 > 최근단가 우선순위
      let unitPrice = 0

      if (priceInfo.cost_type === 'BOM' && priceInfo.calculated_cost > 0) {
        // BOM 기반 원가가 계산되어 있으면 사용
        unitPrice = priceInfo.calculated_cost
      } else {
        // 단품(MANUAL): 우선순위 - 기준단가 > 재고단가 > 최근단가
        unitPrice = priceInfo.standard_price > 0
          ? priceInfo.standard_price
          : priceInfo.inventory_avg_price > 0
            ? priceInfo.inventory_avg_price
            : priceInfo.latest_price > 0
              ? priceInfo.latest_price
              : 0
      }

      return {
        partId,
        unit_price: unitPrice,
        currency: priceInfo.calculated_cost_currency || priceInfo.standard_price_currency || 'KRW'
      }
    } catch (error) {
      console.warn(`부품 ${partId} 가격 조회 실패:`, error)
      // 에러는 무시하고 0으로 처리
      return { partId, unit_price: 0, currency: 'KRW' }
    }
  })

  const results = await Promise.all(pricePromises)
  const newPriceMap: Record<number, { unit_price: number; currency: string }> = {}
  results.forEach(result => {
    newPriceMap[result.partId] = {
      unit_price: result.unit_price,
      currency: result.currency
    }
  })

  // 목록용과 트리용 모두에 동일한 맵 사용
  bomPriceMap.value = newPriceMap
  treePriceMap.value = newPriceMap
}

// 빠른 추가 모드 토글
const toggleQuickAddMode = () => {
  quickAddMode.value = !quickAddMode.value
  if (quickAddMode.value) {
    nextTick(() => quickSearchInput.value?.focus())
  }
}

// 빠른 추가 검색
let quickSearchTimeout: ReturnType<typeof setTimeout> | null = null
const searchQuickAdd = () => {
  if (quickSearchTimeout) clearTimeout(quickSearchTimeout)
  quickSearchDone.value = false

  quickSearchTimeout = setTimeout(async () => {
    if (!quickAddSearch.value.trim()) {
      quickAddResults.value = []
      quickAddSelectedPart.value = null
      quickSearchDone.value = false
      return
    }

    try {
      // 단종 부품도 검색 가능하도록 is_active 필터 제거
      const response = await partApi.getAll({
        keyword: quickAddSearch.value,
        limit: 10
      })
      // 상위 부품과 이미 추가된 부품 제외
      const existingIds = new Set(bomChildren.value.map(b => b.child_part_id))
      quickAddResults.value = response.data.items.filter(
        p => p.id !== selectedParentPart.value?.id && !existingIds.has(p.id)
      )
      quickAddSelectedIdx.value = 0
      const firstResult = quickAddResults.value[0]
      if (firstResult) {
        quickAddSelectedPart.value = firstResult
      } else {
        quickAddSelectedPart.value = null
      }
      quickSearchDone.value = true
    } catch (error) {
      console.error('빠른 추가 검색 실패:', error)
      quickSearchDone.value = true
    }
  }, 200)
}

// 빠른 추가 부품 선택
const selectQuickAddPart = (part: PartListItem) => {
  quickAddSelectedPart.value = part
  quickAddResults.value = []
  quickAddSearch.value = part.part_number
}

// 수량 입력으로 포커스
const focusQuickQty = () => {
  quickQtyInput.value?.focus()
  quickQtyInput.value?.select()
}

// 빠른 추가 실행
const addQuickPart = async () => {
  if (!quickAddSelectedPart.value || !selectedParentPart.value) return

  try {
    await bomApi.create({
      parent_part_id: selectedParentPart.value.id,
      child_part_id: quickAddSelectedPart.value.id,
      quantity: quickAddQty.value,
      sort_order: bomChildren.value.length
    })

    // 초기화 및 새로고침
    quickAddSearch.value = ''
    quickAddSelectedPart.value = null
    quickAddResults.value = []
    quickAddQty.value = 1
    quickSearchInput.value?.focus()

    loadBOMData()
    toast.success('부품이 BOM에 추가되었습니다.')
  } catch (error: any) {
    toast.error(handleApiError(error))
  }
}

// 인라인 수량 편집 시작
const startInlineQtyEdit = (bom: BOMDetailResponse) => {
  editingQtyId.value = bom.id
  editingQtyValue.value = bom.quantity
  nextTick(() => {
    qtyInput.value?.focus()
    qtyInput.value?.select()
  })
}

// 인라인 수량 저장
const saveInlineQty = async (bomId: number) => {
  if (editingQtyId.value !== bomId) return

  const bom = bomChildren.value.find(b => b.id === bomId)
  // 수량을 자연수(1 이상 정수)로 강제 변환
  let qty = Math.floor(editingQtyValue.value)
  if (qty < 1) qty = 1
  editingQtyValue.value = qty

  if (!bom || bom.quantity === qty) {
    editingQtyId.value = null
    return
  }

  try {
    await bomApi.update(bomId, { quantity: qty })
    bom.quantity = qty
    toast.success('수량이 수정되었습니다.')
  } catch (error: any) {
    toast.error(handleApiError(error))
  } finally {
    editingQtyId.value = null
  }
}

// 인라인 수량 편집 취소
const cancelInlineQty = () => {
  editingQtyId.value = null
}

// 드래그 시작
const onDragStart = (event: DragEvent, index: number) => {
  dragIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

// 드래그 오버
const onDragOver = (event: DragEvent, index: number) => {
  dragOverIndex.value = index
}

// 드롭
const onDrop = async (event: DragEvent, dropIndex: number) => {
  const currentDragIndex = dragIndex.value
  if (currentDragIndex === null || currentDragIndex === dropIndex) {
    dragOverIndex.value = null
    return
  }

  const items = [...bomChildren.value]
  const draggedItem = items.splice(currentDragIndex, 1)[0]
  if (!draggedItem) {
    dragOverIndex.value = null
    return
  }
  items.splice(dropIndex, 0, draggedItem)

  // UI 업데이트
  bomChildren.value = items
  dragOverIndex.value = null

  // 서버에 순서 업데이트
  try {
    const orders = items.map((item, idx) => ({
      id: item.id,
      sort_order: idx
    }))
    await bomApi.updateSortOrders(selectedParentPart.value!.id, orders)
  } catch (error) {
    console.error('순서 업데이트 실패:', error)
    loadBOMData() // 실패 시 다시 로드
  }
}

// 드래그 종료
const onDragEnd = () => {
  dragIndex.value = null
  dragOverIndex.value = null
}

// 하위 부품 추가 모달 열기 (다중 선택)
const openAddChildModal = () => {
  showPartSearchModal.value = true
}

// 부품 다중 선택 모달 닫기
const closePartSearchModal = () => {
  showPartSearchModal.value = false
}

// 다중 부품 선택 완료 처리
const handleMultiplePartsSelected = async (parts: PartListItem[]) => {
  if (!selectedParentPart.value || parts.length === 0) return

  try {
    // 일괄 BOM 추가
    const items = parts.map((part, idx) => ({
      child_part_id: part.id,
      quantity: 1,
      sort_order: bomChildren.value.length + idx
    }))

    await bomApi.createBulk({
      parent_part_id: selectedParentPart.value.id,
      items
    })

    // BOM 데이터 새로고침
    await loadBOMData()
    toast.success(`${parts.length}개 부품이 BOM에 추가되었습니다.`)
  } catch (error: any) {
    toast.error(handleApiError(error))
  }
}

// 수정 모달 열기
const openEditModal = (bom: BOMDetailResponse) => {
  formMode.value = 'edit'
  editingBOM.value = bom
  showFormModal.value = true
}

// 모달 닫기
const closeFormModal = () => {
  showFormModal.value = false
  editingBOM.value = null
}

// BOM 저장 완료
const onBOMSaved = () => {
  closeFormModal()
  loadBOMData()
}

// BOM 삭제
const deleteBOM = async (bomId: number) => {
  if (!confirm('정말 삭제하시겠습니까?')) return

  try {
    await bomApi.delete(bomId)
    loadBOMData()
    toast.success('BOM 항목이 삭제되었습니다.')
  } catch (error: any) {
    toast.error(handleApiError(error))
  }
}

// BOM 복사 모달
// BOM 엑셀 업로드 완료 처리 (v0.23.0)
const onBOMUploaded = async (parentPartId?: number) => {
  showUploadModal.value = false
  // 상위 부품이 반환된 경우 해당 부품으로 자동 선택
  if (parentPartId && (!selectedParentPart.value || selectedParentPart.value.id !== parentPartId)) {
    try {
      const res = await partApi.getById(parentPartId)
      const part = res.data as unknown as PartListItem
      selectParentPart(part)
    } catch {
      // 부품 조회 실패 시 기존 선택 유지하고 데이터만 리로드
      loadBOMData()
    }
  } else {
    loadBOMData()
  }
  toast.success('BOM 엑셀 업로드가 완료되었습니다.')
}

const openCopyModal = () => {
  showCopyModal.value = true
  copyTargetSearch.value = ''
  copyTargetResults.value = []
  copyTargetPart.value = null
}

const closeCopyModal = () => {
  showCopyModal.value = false
}

// 복사 대상 검색
let copySearchTimeout: ReturnType<typeof setTimeout> | null = null
const searchCopyTarget = () => {
  if (copySearchTimeout) clearTimeout(copySearchTimeout)

  copySearchTimeout = setTimeout(async () => {
    if (!copyTargetSearch.value.trim()) {
      copyTargetResults.value = []
      return
    }

    try {
      // 단종 부품도 검색 가능하도록 is_active 필터 제거
      const response = await partApi.getAll({
        keyword: copyTargetSearch.value,
        limit: 10
      })
      // 현재 선택된 부품 제외
      copyTargetResults.value = response.data.items.filter(
        p => p.id !== selectedParentPart.value?.id
      )
    } catch (error) {
      console.error('복사 대상 검색 실패:', error)
    }
  }, 300)
}

// 복사 대상 선택
const selectCopyTarget = (part: PartListItem) => {
  copyTargetPart.value = part
  copyTargetSearch.value = ''
  copyTargetResults.value = []
}

// BOM 복사 실행
const executeCopyBOM = async () => {
  if (!copyTargetPart.value || !selectedParentPart.value) return

  try {
    isCopying.value = true

    const items: BOMItemCreate[] = bomChildren.value.map((bom, idx) => ({
      child_part_id: bom.child_part_id,
      quantity: bom.quantity,
      unit_id: bom.unit_id,
      sort_order: idx,
      remark: bom.remark
    }))

    await bomApi.createBulk({
      parent_part_id: copyTargetPart.value.id,
      items
    })

    toast.success(`${copyTargetPart.value.part_number}로 BOM이 복사되었습니다.`)
    closeCopyModal()
  } catch (error: any) {
    toast.error(handleApiError(error))
  } finally {
    isCopying.value = false
  }
}

// ==================== BOM 엑셀 내보내기 ====================

const exportBOMExcel = async () => {
  if (!selectedParentPart.value) {
    toast.warning('상위 부품을 먼저 선택해주세요.')
    return
  }

  isExporting.value = true
  try {
    await bomApi.exportExcel(selectedParentPart.value.id, true)
    toast.success('BOM 엑셀 파일이 다운로드되었습니다.')
  } catch (error: any) {
    console.error('BOM 엑셀 내보내기 실패:', error)
    toast.error('엑셀 내보내기에 실패했습니다.')
  } finally {
    isExporting.value = false
  }
}

// 드롭다운 외부 클릭 시 닫기
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (!target.closest('.relative')) {
    showPartDropdown.value = false
  }
}

// ==================== 새 부품 등록 관련 ====================

// 새 부품 등록 모달 열기 (하위 부품용)
const openNewPartModal = () => {
  isEditingPart.value = false
  editingPartData.value = null
  isCreatingParentPart.value = false
  showNewPartModal.value = true
}

// 새 상위 부품 등록 모달 열기
const openNewParentPartModal = () => {
  isEditingPart.value = false
  editingPartData.value = null
  isCreatingParentPart.value = true
  showNewPartModal.value = true
}

// BOM 등록 버튼 클릭 핸들러
// BOM 등록 버튼: 항상 새로운 상위 부품(BOM)을 생성
// 하위 부품 추가는 BOM 구성에서 별도로 진행
const handleBOMRegisterClick = () => {
  // 항상 상위 부품으로 등록
  openNewParentPartModal()
}

// 새 부품 등록 모달 닫기
const closeNewPartModal = () => {
  showNewPartModal.value = false
  isCreatingParentPart.value = false
  isEditingPart.value = false
  editingPartData.value = null
}

// 부품 등록/수정 완료 처리
const handlePartFormSubmit = async (data: PartCreate) => {
  try {
    if (isEditingPart.value && editingPartData.value) {
      // 부품 수정
      const response = await partApi.update(editingPartData.value.id, data)
      const updatedPart = response.data

      closeNewPartModal()

      // 현재 선택된 상위 부품이 수정된 부품인 경우 정보 갱신
      if (selectedParentPart.value?.id === updatedPart.id) {
        selectedParentPart.value = {
          ...selectedParentPart.value,
          part_number: updatedPart.part_number,
          part_number_display: updatedPart.part_number_display,
          part_name: updatedPart.part_name,
          specification: updatedPart.specification
        }
      }

      // BOM 데이터 새로고침
      await loadBOMData()
      // 부품 목록도 새로고침 (상위 부품 목록)
      if (showParentPartList.value) {
        await searchParentParts()
      }
      toast.success('부품이 수정되었습니다.')
      return
    }

    // 부품 생성 API 호출
    const response = await partApi.create(data)
    const createdPart = response.data

    // 새 부품 모달 닫기
    closeNewPartModal()

    // 상위 부품 등록인 경우: 바로 상위 부품으로 선택
    if (isCreatingParentPart.value) {
      selectedParentPart.value = {
        id: createdPart.id,
        part_number: createdPart.part_number,
        part_number_display: createdPart.part_number_display,
        part_name: createdPart.part_name,
        specification: createdPart.specification,
        is_active: true,
        created_at: new Date().toISOString()
      } as PartListItem
      partSearchKeyword.value = ''
      searchedParts.value = []
      showPartDropdown.value = false
      loadBOMData()
      toast.success(`부품 "${createdPart.part_number_display}"가 등록되고 선택되었습니다.`)
      return
    }

    // 하위 부품 등록인 경우: BOM 추가 확인 모달 열기
    newlyCreatedPart.value = {
      id: createdPart.id,
      part_number: createdPart.part_number_display || createdPart.part_number,
      part_name: createdPart.part_name
    }
    newPartQty.value = 1
    showAddToBomConfirm.value = true
    toast.success('부품이 등록되었습니다.')
  } catch (error: any) {
    toast.error(handleApiError(error))
  }
}

// BOM 추가 확인
const confirmAddToBom = async () => {
  if (!newlyCreatedPart.value || !selectedParentPart.value) return

  try {
    isAddingToBom.value = true

    await bomApi.create({
      parent_part_id: selectedParentPart.value.id,
      child_part_id: newlyCreatedPart.value.id,
      quantity: newPartQty.value,
      sort_order: bomChildren.value.length
    })

    // BOM 데이터 새로고침
    await loadBOMData()

    // 모달 닫기
    showAddToBomConfirm.value = false
    newlyCreatedPart.value = null
    toast.success('BOM에 추가되었습니다.')
  } catch (error: any) {
    toast.error(handleApiError(error))
  } finally {
    isAddingToBom.value = false
  }
}

// BOM 추가 취소
const cancelAddToBom = () => {
  showAddToBomConfirm.value = false
  newlyCreatedPart.value = null
}

// ==================== 부품 상세 보기 관련 ====================

// 부품 상세 보기 모달 열기
const openPartDetail = (partId: number) => {
  detailPartId.value = partId
  showDetailModal.value = true
}

// 부품 상세 보기 모달 닫기
const closePartDetail = () => {
  showDetailModal.value = false
  detailPartId.value = null
}

// 부품 수정 (상세 모달에서 수정 버튼 클릭 시)
const handlePartEdit = (part: Part) => {
  closePartDetail()
  // 부품 수정 모달 열기
  isEditingPart.value = true
  editingPartData.value = part
  showNewPartModal.value = true
}

// 부품 복제 (기존 데이터를 새 등록 폼에 pre-fill)
const duplicatePart = async (part: PartListItem) => {
  try {
    const response = await partApi.getById(part.id)
    const partData = response.data

    // 복제 데이터 생성 (id, part_uid, created_at, updated_at 등 고유값 제외)
    // part_number는 비워두어 품번규칙 A 모드에서 새로 생성하도록 함
    const duplicateData: any = {
      // part_number는 의도적으로 비움 - 새 품번을 생성하도록
      part_name: partData.part_name + ' (복제)',  // 복제임을 표시
      part_name_en: partData.part_name_en,
      specification: partData.specification,
      description: partData.description,
      product_line_id: partData.product_line_id,
      part_group_id: partData.part_group_id,
      item_code: partData.item_code,  // 품목코드 (prefix 추출용)
      material_id: partData.material_id,
      treatment_id: partData.treatment_id,
      unit_id: partData.unit_id,
      level_id: partData.level_id,
      drawing_type_id: partData.drawing_type_id,
      procurement_type_id: partData.procurement_type_id,
      development_type_id: partData.development_type_id,
      supplier_id: partData.supplier_id,
      standard_price: partData.standard_price,
      status: 'ACTIVE',  // 새 부품은 기본적으로 활성 상태
    }

    isEditingPart.value = false  // 신규 등록 모드
    editingPartData.value = duplicateData
    isCreatingParentPart.value = false
    showNewPartModal.value = true

    toast.success('부품 데이터가 복제되었습니다. 재질/후처리 등을 변경 후 등록하세요.')
  } catch (error: any) {
    toast.error(handleApiError(error))
  }
}

// 원가 정보 업데이트 핸들러 (v0.20.0)
function onPriceUpdated() {
  // 필요 시 BOM 데이터 새로고침
  toast.success('원가 정보가 업데이트되었습니다.')
}

// BOM 원가 재계산 (모든 하위 BOM 포함)
const recalculateBOMCost = async () => {
  if (!selectedParentPart.value) {
    toast.warning('상위 부품을 먼저 선택해주세요.')
    return
  }

  isRecalculating.value = true
  try {
    // 상위 부품 및 모든 하위 BOM의 원가를 재귀적으로 재계산
    const result = await priceApi.saveAllBOMCosts(selectedParentPart.value.id)

    // 가격 정보 다시 로드
    await loadBOMPrices()

    toast.success(result.message)
  } catch (error) {
    console.error('원가 재계산 실패:', error)
    toast.error('원가 재계산에 실패했습니다.')
  } finally {
    isRecalculating.value = false
  }
}

// 마운트 시 이벤트 리스너 및 초기 데이터 로드
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  loadCodeMasters()
  // 초기 진입 시 상위 부품 목록 자동 표시
  showParentPartList.value = true
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  // 리사이즈 이벤트 정리
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
})
</script>
