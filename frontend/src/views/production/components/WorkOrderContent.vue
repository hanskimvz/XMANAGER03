<template>
  <div class="py-6 px-4 sm:px-6 lg:px-8">
    <!-- 헤더 -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-semibold text-gray-800">작업지시서 관리</h2>
        <p class="text-sm text-gray-500">생산 요청을 처리하고 작업지시서를 관리합니다.</p>
      </div>
      <button
        @click="openCreateModal"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        작업지시서 등록
      </button>
    </div>

    <!-- v0.22.0: 상태별 요약 카드 (요청 현황 통합) -->
    <div class="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
      <!-- 대기 요청 -->
      <div class="bg-white rounded-lg shadow p-3 border-l-4 border-blue-400 cursor-pointer hover:bg-blue-50 transition-colors" @click="scrollToPending">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs font-medium text-gray-500">대기 요청</p>
            <p class="text-xl font-bold text-blue-600">{{ pendingRequests.length }}</p>
          </div>
          <div class="p-2 bg-blue-100 rounded-full">
            <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      <!-- 승인/출고 대기 -->
      <div class="bg-white rounded-lg shadow p-3 border-l-4 border-indigo-400">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs font-medium text-gray-500">승인/출고</p>
            <p class="text-xl font-bold text-indigo-600">{{ (woStatusCounts.RECEIVED ?? 0) + (woStatusCounts.APPROVED ?? 0) }}</p>
          </div>
          <div class="p-2 bg-indigo-100 rounded-full">
            <svg class="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      <!-- 작업 중 -->
      <div class="bg-white rounded-lg shadow p-3 border-l-4 border-yellow-400">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs font-medium text-gray-500">작업 중</p>
            <p class="text-xl font-bold text-yellow-600">{{ (woStatusCounts.ISSUED ?? 0) + (woStatusCounts.IN_PROGRESS ?? 0) }}</p>
          </div>
          <div class="p-2 bg-yellow-100 rounded-full">
            <svg class="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
        </div>
      </div>

      <!-- 검사/포장 -->
      <div class="bg-white rounded-lg shadow p-3 border-l-4 border-green-400">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs font-medium text-gray-500">검사/포장</p>
            <p class="text-xl font-bold text-green-600">{{ (woStatusCounts.INSPECTION ?? 0) + (woStatusCounts.PACKED ?? 0) }}</p>
          </div>
          <div class="p-2 bg-green-100 rounded-full">
            <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      <!-- 출하 완료 -->
      <div class="bg-white rounded-lg shadow p-3 border-l-4 border-gray-400">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs font-medium text-gray-500">출하 완료</p>
            <p class="text-xl font-bold text-gray-600">{{ woStatusCounts.SHIPPED }}</p>
          </div>
          <div class="p-2 bg-gray-100 rounded-full">
            <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>
      </div>

      <!-- v0.23.0: 수정 알림 -->
      <div
        v-if="modifiedWorkOrders.length > 0"
        class="bg-orange-50 rounded-lg shadow p-3 border-l-4 border-orange-400 cursor-pointer hover:bg-orange-100 transition-colors animate-pulse"
        @click="scrollToModified"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs font-medium text-orange-600">수정 알림</p>
            <p class="text-xl font-bold text-orange-600">{{ modifiedWorkOrders.length }}</p>
          </div>
          <div class="p-2 bg-orange-100 rounded-full">
            <svg class="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- 대기 중인 생산요청 (v0.20.0) -->
    <div id="pending-requests-section" v-if="pendingRequests.length > 0" class="bg-yellow-50 border border-yellow-200 rounded-lg shadow p-4 mb-6">
      <div class="flex justify-between items-center mb-3">
        <h2 class="text-lg font-semibold text-yellow-800 flex items-center gap-2">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          대기 중인 생산요청 ({{ pendingRequests.length }}건)
        </h2>
        <button
          @click="showPendingSection = !showPendingSection"
          class="text-yellow-600 hover:text-yellow-800 text-sm"
        >
          {{ showPendingSection ? '접기' : '펼치기' }}
        </button>
      </div>
      <div v-if="showPendingSection" class="overflow-x-auto">
        <table class="min-w-full divide-y divide-yellow-200">
          <thead>
            <tr>
              <th class="px-3 py-2 text-left text-xs font-medium text-yellow-700">요청번호</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-yellow-700">요청일시</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-yellow-700">고객사</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-yellow-700">제품</th>
              <th class="px-3 py-2 text-right text-xs font-medium text-yellow-700">수량</th>
              <th class="px-3 py-2 text-center text-xs font-medium text-yellow-700">납기</th>
              <th class="px-3 py-2 text-center text-xs font-medium text-yellow-700">우선순위</th>
              <th class="px-3 py-2 text-center text-xs font-medium text-yellow-700">작업</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-yellow-100">
            <tr v-for="pr in pendingRequests" :key="pr.id" class="hover:bg-yellow-100">
              <td class="px-3 py-2 text-sm">
                <button @click="openPRDetail(pr.id)" class="text-blue-600 font-medium hover:underline hover:text-blue-800">
                  {{ pr.request_number }}
                </button>
              </td>
              <td class="px-3 py-2 text-sm text-gray-500">{{ formatDateTime(pr.requested_at || pr.created_at || '') }}</td>
              <td class="px-3 py-2 text-sm">{{ pr.customer?.partner_name || '-' }}</td>
              <td class="px-3 py-2 text-sm">{{ getPRProductDisplay(pr) }}</td>
              <td class="px-3 py-2 text-sm text-right">{{ getPRTotalQuantity(pr) }}</td>
              <td class="px-3 py-2 text-sm text-center">{{ pr.due_date ? formatDate(pr.due_date) : '-' }}</td>
              <td class="px-3 py-2 text-center">
                <span :class="['px-2 py-0.5 text-xs rounded-full', prPriorityStyles[pr.priority]]">
                  {{ prPriorityLabels[pr.priority] }}
                </span>
              </td>
              <td class="px-3 py-2 text-center">
                <div class="flex justify-center gap-2">
                  <button
                    @click="handleApprovePR(pr)"
                    class="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                    title="승인 및 작업지시서 생성"
                  >
                    승인
                  </button>
                  <button
                    @click="handleRejectPR(pr.id)"
                    class="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
                    title="반려"
                  >
                    반려
                  </button>
                  <button
                    @click="handleHoldPR(pr.id)"
                    class="px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200"
                    title="보류"
                  >
                    보류
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- v0.23.0: 수정된 작업지시서 알림 -->
    <div id="modified-wo-section" v-if="modifiedWorkOrders.length > 0" class="bg-orange-50 border border-orange-200 rounded-lg shadow p-4 mb-6">
      <div class="flex justify-between items-center mb-3">
        <h2 class="text-lg font-semibold text-orange-800 flex items-center gap-2">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          수정된 작업지시서 ({{ modifiedWorkOrders.length }}건)
          <span class="text-xs font-normal text-orange-600">원본 생산요청이 변경되었습니다</span>
        </h2>
        <button
          @click="showModifiedSection = !showModifiedSection"
          class="text-orange-600 hover:text-orange-800 text-sm"
        >
          {{ showModifiedSection ? '접기' : '펼치기' }}
        </button>
      </div>
      <div v-if="showModifiedSection" class="overflow-x-auto">
        <table class="min-w-full divide-y divide-orange-200">
          <thead>
            <tr>
              <th class="px-3 py-2 text-left text-xs font-medium text-orange-700">지시번호</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-orange-700">제품</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-orange-700">고객사</th>
              <th class="px-3 py-2 text-right text-xs font-medium text-orange-700">수량</th>
              <th class="px-3 py-2 text-center text-xs font-medium text-orange-700">현재상태</th>
              <th class="px-3 py-2 text-center text-xs font-medium text-orange-700">작업</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-orange-100">
            <tr v-for="wo in modifiedWorkOrders" :key="wo.id" class="hover:bg-orange-100">
              <td class="px-3 py-2 text-sm font-medium text-blue-600 cursor-pointer" @click="openDetailModal(wo.id)">
                {{ wo.wo_number }}
              </td>
              <td class="px-3 py-2 text-sm">
                <template v-if="wo.products && wo.products.length > 1">
                  {{ wo.products[0]?.product_part?.part_name || '-' }}
                  <span class="text-xs text-blue-600 ml-1">외 {{ wo.products.length - 1 }}종</span>
                </template>
                <template v-else-if="wo.products && wo.products.length === 1">
                  {{ wo.products[0]?.product_part?.part_name || '-' }}
                </template>
                <template v-else>
                  {{ wo.product_part?.part_name || '-' }}
                </template>
              </td>
              <td class="px-3 py-2 text-sm">{{ wo.customer?.partner_name || '-' }}</td>
              <td class="px-3 py-2 text-sm text-right">
                <template v-if="wo.products && wo.products.length > 0">
                  {{ wo.products.reduce((sum, p) => sum + Number(p.order_quantity || 0), 0) }}
                </template>
                <template v-else>
                  {{ wo.order_quantity }}
                </template>
              </td>
              <td class="px-3 py-2 text-center">
                <span :class="['px-2 py-0.5 text-xs rounded-full', woStatusStyles[wo.status]]">
                  {{ woStatusLabels[wo.status] }}
                </span>
              </td>
              <td class="px-3 py-2 text-center">
                <div class="flex justify-center gap-2">
                  <button
                    @click="openDetailModal(wo.id)"
                    class="px-2 py-1 text-xs bg-orange-600 text-white rounded hover:bg-orange-700"
                    title="상세 확인"
                  >
                    상세
                  </button>
                  <button
                    @click="handleAcknowledgeFromList(wo.id)"
                    class="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                    title="수정 알림 확인 처리"
                  >
                    확인함
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 검색/필터 -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
      <div class="flex flex-wrap gap-3">
        <!-- 키워드 검색 -->
        <div class="min-w-[160px] flex-1">
          <label class="block text-sm font-medium text-gray-700 mb-1">검색</label>
          <input
            v-model="filters.keyword"
            type="text"
            placeholder="지시번호, 고객주문번호"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
            @keyup.enter="loadData"
          />
        </div>

        <!-- 상태 필터 -->
        <div class="min-w-[100px] w-[100px]">
          <label class="block text-sm font-medium text-gray-700 mb-1">상태</label>
          <select
            v-model="filters.status"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
            @change="loadData"
          >
            <option value="">전체</option>
            <option v-for="(label, key) in woStatusLabels" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>

        <!-- 거래처 필터 (콤보박스) -->
        <div class="min-w-[150px] flex-1 max-w-[200px] relative">
          <label class="block text-sm font-medium text-gray-700 mb-1">거래처</label>
          <div class="relative">
            <input
              v-model="customerSearchText"
              type="text"
              placeholder="검색 또는 선택"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm pr-8"
              @focus="showCustomerDropdown = true"
              @input="onCustomerSearch"
            />
            <button
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              @click="toggleCustomerDropdown"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <!-- 드롭다운 목록 -->
            <div
              v-if="showCustomerDropdown"
              class="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto"
            >
              <div
                class="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                @click="selectCustomer(null, '전체')"
              >
                전체
              </div>
              <div
                v-for="c in filteredCustomers"
                :key="c.id"
                class="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm truncate"
                @click="selectCustomer(c.id, c.partner_name)"
              >
                {{ c.partner_name }}
              </div>
              <div v-if="filteredCustomers.length === 0" class="px-3 py-2 text-sm text-gray-400">
                검색 결과 없음
              </div>
            </div>
          </div>
        </div>

        <!-- 우선순위 필터 -->
        <div class="min-w-[90px] w-[90px]">
          <label class="block text-sm font-medium text-gray-700 mb-1">우선순위</label>
          <select
            v-model="filters.priority"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
            @change="loadData"
          >
            <option value="">전체</option>
            <option value="2">긴급</option>
            <option value="1">높음</option>
            <option value="0">보통</option>
          </select>
        </div>

        <!-- 출하예정일 범위 -->
        <div class="min-w-[220px]">
          <label class="block text-sm font-medium text-gray-700 mb-1">출하예정일</label>
          <div class="flex gap-1">
            <input
              v-model="filters.from_date"
              type="date"
              class="flex-1 min-w-0 px-2 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
              @change="loadData"
            />
            <input
              v-model="filters.to_date"
              type="date"
              class="flex-1 min-w-0 px-2 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
              @change="loadData"
            />
          </div>
        </div>
      </div>

      <div class="mt-4 flex justify-end gap-2 border-t pt-4">
        <button
          @click="resetFilters"
          class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 border rounded-lg"
        >
          필터 초기화
        </button>
        <button
          @click="loadData"
          class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          검색
        </button>
      </div>
    </div>

    <!-- 테이블 -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">지시번호</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">완제품</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">고객사</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">지시수량</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">완료수량</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">우선순위</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">상태</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">출하예정</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">작업</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-if="loading">
            <td colspan="9" class="px-4 py-4 text-center text-gray-500">로딩 중...</td>
          </tr>
          <tr v-else-if="workOrders.length === 0">
            <td colspan="9" class="px-4 py-4 text-center text-gray-500">데이터가 없습니다.</td>
          </tr>
          <tr
            v-for="wo in workOrders"
            :key="wo.id"
            class="cursor-pointer"
            :class="wo.source_request_modified ? 'bg-yellow-50 hover:bg-yellow-100' : 'hover:bg-gray-50'"
            @click="openDetailModal(wo.id)"
          >
            <td class="px-4 py-3 whitespace-nowrap">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-blue-600">{{ wo.wo_number }}</span>
                <!-- v0.21.0: 원본 요청서 수정됨 배지 -->
                <span
                  v-if="wo.source_request_modified"
                  class="px-1.5 py-0.5 text-xs bg-yellow-500 text-white rounded animate-pulse"
                  title="원본 생산요청서가 수정되었습니다"
                >
                  수정됨
                </span>
              </div>
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
              <!-- v0.19.0: 다중 제품 표시 -->
              <template v-if="wo.products && wo.products.length > 1">
                <div class="text-sm text-gray-900">
                  {{ wo.products[0]?.product_part?.part_name || '-' }}
                  <span class="text-xs text-blue-600 ml-1">외 {{ wo.products.length - 1 }}종</span>
                </div>
                <div class="text-xs text-gray-500 font-mono">
                  {{ wo.products[0]?.product_part?.part_number_display || wo.products[0]?.product_part?.part_number || '' }}
                </div>
              </template>
              <template v-else-if="wo.products && wo.products.length === 1">
                <div class="text-sm text-gray-900">{{ wo.products[0]?.product_part?.part_name || '-' }}</div>
                <div class="text-xs text-gray-500 font-mono">{{ wo.products[0]?.product_part?.part_number_display || wo.products[0]?.product_part?.part_number || '' }}</div>
              </template>
              <template v-else>
                <div class="text-sm text-gray-900">{{ wo.product_part?.part_name || '-' }}</div>
                <div class="text-xs text-gray-500 font-mono">{{ wo.product_part?.part_number_display || wo.product_part?.part_number || '' }}</div>
              </template>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
              {{ wo.customer?.partner_name || '-' }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
              <!-- v0.19.0: 다중 제품 수량 표시 -->
              <template v-if="wo.products && wo.products.length > 0">
                {{ wo.products.reduce((sum, p) => sum + Number(p.order_quantity || 0), 0) }}
              </template>
              <template v-else>
                {{ wo.order_quantity }}
              </template>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-right">
              <span :class="getCompletedQty(wo) > 0 ? 'text-green-600' : 'text-gray-400'">
                {{ getCompletedQty(wo) }}
              </span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-center">
              <span :class="['px-2 py-1 text-xs rounded-full', priorityStyles[wo.priority as 0|1|2] || priorityStyles[0]]">
                {{ priorityLabels[wo.priority as 0|1|2] || '보통' }}
              </span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-center">
              <span :class="['px-2 py-1 text-xs rounded-full', woStatusStyles[wo.status]]">
                {{ woStatusLabels[wo.status] }}
              </span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500 text-center">
              {{ wo.shipping_scheduled_date ? formatDate(wo.shipping_scheduled_date) : '-' }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-center">
              <div class="flex justify-center gap-1" @click.stop>
                <!-- 상태별 다음 단계 버튼 -->
                <button
                  v-if="wo.status === 'RECEIVED'"
                  @click="handleApprove(wo.id)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100 transition-colors"
                  title="승인하기"
                >
                  승인
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <button
                  v-if="wo.status === 'APPROVED'"
                  @click="openIssueModal(wo.id)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-indigo-700 bg-indigo-50 rounded hover:bg-indigo-100 transition-colors"
                  title="부품 출고하기"
                >
                  출고
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <button
                  v-if="wo.status === 'ISSUED'"
                  @click="handleStartProduction(wo.id)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-yellow-700 bg-yellow-50 rounded hover:bg-yellow-100 transition-colors"
                  title="작업 시작하기"
                >
                  작업
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <button
                  v-if="wo.status === 'IN_PROGRESS'"
                  @click="openProductionCompleteModal(wo.id)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-orange-700 bg-orange-50 rounded hover:bg-orange-100 transition-colors"
                  title="작업 완료하기"
                >
                  완료
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <button
                  v-if="wo.status === 'INSPECTION'"
                  @click="handleCompleteInspection(wo.id)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-green-700 bg-green-50 rounded hover:bg-green-100 transition-colors"
                  title="검사 완료하기"
                >
                  검사
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <button
                  v-if="wo.status === 'PACKED'"
                  @click="handleShip(wo.id)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-purple-700 bg-purple-50 rounded hover:bg-purple-100 transition-colors"
                  title="출하 처리하기"
                >
                  출하
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <!-- 롤백 버튼 (SHIPPED, CANCELLED, RECEIVED 제외) -->
                <button
                  v-if="canRollback(wo.status)"
                  @click="handleRollback(wo.id, wo.status)"
                  class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
                  title="이전 상태로 되돌리기"
                >
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                  </svg>
                  롤백
                </button>
                <!-- 완료 또는 취소된 경우 표시 -->
                <span
                  v-if="wo.status === 'SHIPPED'"
                  class="inline-flex items-center px-2 py-1 text-xs font-medium text-gray-500 bg-gray-100 rounded"
                >
                  완료
                </span>
                <!-- 취소됨: 복원 + 완전삭제 버튼 -->
                <template v-if="wo.status === 'CANCELLED'">
                  <button
                    @click="handleRestore(wo.id)"
                    class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-green-700 bg-green-50 rounded hover:bg-green-100 transition-colors"
                    title="작업지시서 복원하기"
                  >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    복원
                  </button>
                  <button
                    @click="handlePermanentDelete(wo.id)"
                    class="ml-1 p-1 text-red-400 hover:text-red-600 transition-colors"
                    title="완전 삭제"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </template>
                <!-- 취소 버튼 (출하완료, 취소 상태 제외) -->
                <button
                  v-if="wo.status !== 'SHIPPED' && wo.status !== 'CANCELLED'"
                  @click="handleCancel(wo.id)"
                  class="ml-1 p-1 text-gray-400 hover:text-red-600 transition-colors"
                  title="취소"
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
    </div>

    <!-- 페이지네이션 -->
    <div class="mt-4 flex justify-between items-center">
      <div class="text-sm text-gray-500">
        총 {{ pagination.total }}건 중 {{ (pagination.skip || 0) + 1 }} - {{ Math.min((pagination.skip || 0) + workOrders.length, pagination.total) }}건
      </div>
      <div class="flex gap-2">
        <button
          @click="goPage(currentPage - 1)"
          :disabled="currentPage <= 1"
          class="px-3 py-1 border rounded disabled:opacity-50"
        >
          이전
        </button>
        <span class="px-3 py-1">{{ currentPage }} / {{ totalPages }}</span>
        <button
          @click="goPage(currentPage + 1)"
          :disabled="currentPage >= totalPages"
          class="px-3 py-1 border rounded disabled:opacity-50"
        >
          다음
        </button>
      </div>
    </div>

    <!-- 작업지시서 등록/상세 모달 -->
    <WorkOrderFormModal
      v-if="showFormModal"
      :work-order-id="selectedWOId"
      @close="showFormModal = false"
      @saved="handleSaved"
    />

    <!-- 부품 출고 모달 -->
    <WorkOrderIssueModal
      v-if="showIssueModal && issueWOId"
      :work-order-id="issueWOId"
      @close="showIssueModal = false"
      @issued="handleIssued"
    />

    <!-- 작업 완료 모달 -->
    <WorkOrderCompleteModal
      v-if="showCompleteModal && completeWOId"
      :work-order-id="completeWOId"
      @close="showCompleteModal = false"
      @completed="handleCompleted"
    />

    <!-- 생산요청 상세 모달 -->
    <ProductionRequestDetailModal
      v-if="showPRDetailModal && prDetailId"
      :request-id="prDetailId"
      @close="showPRDetailModal = false"
      @edit="handlePRDetailEdit"
      @approve="handlePRDetailApprove"
      @reject="handlePRDetailReject"
      @hold="handlePRDetailHold"
      @release-hold="handlePRDetailReleaseHold"
      @cancel="handlePRDetailCancel"
      @delete="handlePRDetailDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import {
  workOrderApi,
  type WorkOrderListItem,
  type WorkOrderSearchParams,
  woStatusLabels,
  woStatusStyles,
  priorityLabels,
  priorityStyles,
} from '@/api/workOrder'
import { partnerApi } from '@/api/partner'
import {
  productionRequestApi,
  priorityLabels as prPriorityLabels,
  priorityStyles as prPriorityStyles,
  type ProductionRequest
} from '@/api/productionRequest'
import WorkOrderFormModal from '@/views/production/components/WorkOrderFormModal.vue'
import WorkOrderIssueModal from '@/views/production/components/WorkOrderIssueModal.vue'
import WorkOrderCompleteModal from '@/views/production/components/WorkOrderCompleteModal.vue'
import ProductionRequestDetailModal from '@/views/production/components/ProductionRequestDetailModal.vue'

// Emits
const emit = defineEmits<{
  'data-changed': []
}>()

// 상태
const loading = ref(false)
const workOrders = ref<WorkOrderListItem[]>([])
const customers = ref<any[]>([])
const pagination = reactive({ total: 0, skip: 0, limit: 20 })

// 거래처 콤보박스 상태
const showCustomerDropdown = ref(false)
const customerSearchText = ref('')

// 필터링된 거래처 목록
const filteredCustomers = computed(() => {
  if (!customerSearchText.value) return customers.value
  const search = customerSearchText.value.toLowerCase()
  return customers.value.filter(c => c.partner_name?.toLowerCase().includes(search))
})

// 대기 중인 생산요청 (v0.20.0)
const pendingRequests = ref<ProductionRequest[]>([])
const showPendingSection = ref(true)
const showPRDetailModal = ref(false)
const prDetailId = ref<number | null>(null)

// v0.23.0: 수정된 작업지시서
const modifiedWorkOrders = ref<WorkOrderListItem[]>([])
const showModifiedSection = ref(true)

// v0.22.0: 작업지시 상태별 카운트
const woStatusCounts = ref<Record<string, number>>({
  RECEIVED: 0,
  APPROVED: 0,
  ISSUED: 0,
  IN_PROGRESS: 0,
  INSPECTION: 0,
  PACKED: 0,
  SHIPPED: 0,
  CANCELLED: 0,
})

// 필터
const filters = reactive<WorkOrderSearchParams>({
  keyword: '',
  status: undefined,
  customer_id: undefined,
  priority: undefined,
  from_date: '',
  to_date: '',
})

// 모달
const showFormModal = ref(false)
const selectedWOId = ref<number | null>(null)
const showIssueModal = ref(false)
const issueWOId = ref<number | null>(null)
const showCompleteModal = ref(false)
const completeWOId = ref<number | null>(null)

// 계산된 속성
const currentPage = computed(() => Math.floor((pagination.skip || 0) / pagination.limit) + 1)
const totalPages = computed(() => Math.ceil(pagination.total / pagination.limit) || 1)

// 데이터 로드
async function loadData() {
  loading.value = true
  try {
    const params: WorkOrderSearchParams = {
      ...filters,
      skip: pagination.skip,
      limit: pagination.limit,
    }
    // 빈 문자열을 undefined로 변환
    if (!params.keyword) params.keyword = undefined
    if (!params.status) params.status = undefined
    if (!params.customer_id) params.customer_id = undefined
    if (params.priority === undefined || params.priority === null || (params.priority as unknown) === '') {
      params.priority = undefined
    } else {
      params.priority = Number(params.priority)
    }
    if (!params.from_date) params.from_date = undefined
    if (!params.to_date) params.to_date = undefined

    const response = await workOrderApi.getAll(params)
    workOrders.value = response.items
    pagination.total = response.total
  } catch (error) {
    console.error('작업지시서 목록 조회 실패:', error)
    alert('작업지시서 목록을 불러오는데 실패했습니다.')
  } finally {
    loading.value = false
  }
}

// 거래처 목록 로드 (공급사+고객사 통합)
async function loadCustomers() {
  try {
    const response = await partnerApi.getAll({ limit: 1000 })
    customers.value = response.data.items
  } catch (error) {
    console.error('거래처 목록 조회 실패:', error)
  }
}

// 대기 중인 생산요청 로드 (v0.20.0)
// 생산요청 제품 표시 (items 또는 deprecated 필드 또는 PI 정보)
function getPRProductDisplay(pr: any): string {
  if (pr.items && pr.items.length > 0) {
    const first = pr.items[0]
    const name = first.product_part?.part_name || first.product_part?.part_number_display || first.product_part?.part_number || '-'
    return pr.items.length > 1 ? `${name} 외 ${pr.items.length - 1}종` : name
  }
  if (pr.product_part) {
    return pr.product_part.part_name || pr.product_part.part_number || '-'
  }
  return '(제품 미지정)'
}

function getPRTotalQuantity(pr: any): string {
  if (pr.items && pr.items.length > 0) {
    const total = pr.items.reduce((sum: number, item: any) => sum + Number(item.requested_quantity || 0), 0)
    return formatNumber(total)
  }
  return formatNumber(pr.requested_quantity || 0)
}

function formatDateTime(dateStr: string): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

// 생산요청 상세 보기
function openPRDetail(id: number) {
  prDetailId.value = id
  showPRDetailModal.value = true
}

async function handlePRDetailApprove(id: number) {
  showPRDetailModal.value = false
  const pr = pendingRequests.value.find(p => p.id === id)
  if (pr) handleApprovePR(pr)
}

async function handlePRDetailReject(id: number) {
  showPRDetailModal.value = false
  handleRejectPR(id)
}

async function handlePRDetailHold(id: number) {
  showPRDetailModal.value = false
  handleHoldPR(id)
}

async function handlePRDetailReleaseHold(id: number) {
  showPRDetailModal.value = false
  try {
    await productionRequestApi.releaseHold(id)
    loadPendingRequests()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '보류 해제에 실패했습니다.')
  }
}

async function handlePRDetailCancel(id: number) {
  showPRDetailModal.value = false
  const reason = prompt('취소 사유를 입력하세요:')
  if (reason === null) return
  try {
    await productionRequestApi.cancel(id, reason)
    loadPendingRequests()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '취소에 실패했습니다.')
  }
}

async function handlePRDetailDelete(id: number) {
  showPRDetailModal.value = false
  if (!confirm('삭제하시겠습니까?')) return
  try {
    await productionRequestApi.delete(id)
    loadPendingRequests()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '삭제에 실패했습니다.')
  }
}

function handlePRDetailEdit(id: number) {
  showPRDetailModal.value = false
  // 생산요청 수정 페이지로 이동
  window.location.href = `/production?tab=requests`
}

async function loadPendingRequests() {
  try {
    pendingRequests.value = await productionRequestApi.getPending(0, 20)
  } catch (error) {
    console.error('대기 중인 생산요청 조회 실패:', error)
  }
}

// v0.23.0: 수정된 작업지시서 로드
async function loadModifiedWorkOrders() {
  try {
    modifiedWorkOrders.value = await workOrderApi.getModified(0, 20)
  } catch (error) {
    console.error('수정된 작업지시서 조회 실패:', error)
  }
}

// v0.23.0: 수정된 작업지시서 섹션으로 스크롤
function scrollToModified() {
  showModifiedSection.value = true
  const el = document.getElementById('modified-wo-section')
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// v0.23.0: 수정 알림 확인
async function handleAcknowledgeFromList(woId: number) {
  if (!confirm('수정 알림을 확인 처리하시겠습니까?')) return
  try {
    await workOrderApi.acknowledgeModification(woId)
    loadModifiedWorkOrders()
    loadData()
  } catch (error: any) {
    console.error('알림 확인 실패:', error)
    alert(error.response?.data?.detail?.message || '알림 확인에 실패했습니다.')
  }
}

// v0.22.0: 작업지시 상태별 카운트 로드
async function loadStatusCounts() {
  try {
    // 전체 작업지시 조회해서 상태별 카운트
    const response = await workOrderApi.getAll({ limit: 1000 })
    const counts: Record<string, number> = {
      RECEIVED: 0, APPROVED: 0, ISSUED: 0, IN_PROGRESS: 0,
      INSPECTION: 0, PACKED: 0, SHIPPED: 0, CANCELLED: 0,
    }
    for (const wo of response.items) {
      if (counts[wo.status] !== undefined) {
        counts[wo.status] = (counts[wo.status] ?? 0) + 1
      }
    }
    woStatusCounts.value = counts
  } catch (error) {
    console.error('상태별 카운트 조회 실패:', error)
  }
}

// v0.22.0: 대기 요청 섹션으로 스크롤
function scrollToPending() {
  showPendingSection.value = true
  const el = document.getElementById('pending-requests-section')
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// 생산요청 승인 후 작업지시서 생성 (v0.20.0, v0.22.0 개선)
async function handleApprovePR(pr: ProductionRequest) {
  if (!confirm(`[${pr.request_number}] 요청에 대한 작업지시서를 생성하시겠습니까?`)) return
  try {
    // v0.22.0: PR 상세 조회 (다중 제품 + 첨부파일 포함)
    // 승인은 WO 등록 완료 시점에 수행 (모달에서 처리)
    const prDetail = await productionRequestApi.getById(pr.id)

    selectedWOId.value = null
    sessionStorage.setItem('createFromPR', JSON.stringify({
      production_request_id: prDetail.id,
      customer_id: prDetail.customer_id,
      customer_order_no: prDetail.customer_order_no,
      items: prDetail.items || [],
      attachment_files: prDetail.attachment_files || [],
      product_part_id: prDetail.product_part_id,
      order_quantity: prDetail.requested_quantity,
    }))
    showFormModal.value = true
    // 대기 목록은 새로고침하지 않음 (WO 등록 완료 후 갱신)
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '요청 정보 조회에 실패했습니다.')
  }
}

// 생산요청 반려 (v0.20.0)
async function handleRejectPR(id: number) {
  const reason = prompt('반려 사유를 입력하세요:')
  if (!reason) return
  try {
    await productionRequestApi.reject(id, { rejection_reason: reason })
    alert('반려되었습니다.')
    loadPendingRequests()
    emit('data-changed')  // 부모에 알려 탭 뱃지 갱신
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '반려에 실패했습니다.')
  }
}

// 생산요청 보류 (v0.20.0)
async function handleHoldPR(id: number) {
  if (!confirm('보류 처리하시겠습니까?')) return
  try {
    await productionRequestApi.hold(id)
    alert('보류되었습니다.')
    loadPendingRequests()
  } catch (error: any) {
    alert(error.response?.data?.detail?.message || '보류 처리에 실패했습니다.')
  }
}

// 필터 초기화
function resetFilters() {
  filters.keyword = ''
  filters.status = undefined
  filters.customer_id = undefined
  filters.priority = undefined
  filters.from_date = ''
  filters.to_date = ''
  customerSearchText.value = ''
  pagination.skip = 0
  loadData()
}

// 거래처 콤보박스 함수들
function toggleCustomerDropdown() {
  showCustomerDropdown.value = !showCustomerDropdown.value
}

function selectCustomer(id: number | null, name: string) {
  filters.customer_id = id || undefined
  customerSearchText.value = id ? name : ''
  showCustomerDropdown.value = false
  loadData()
}

function onCustomerSearch() {
  showCustomerDropdown.value = true
  // 검색어가 비어있으면 필터 초기화
  if (!customerSearchText.value) {
    filters.customer_id = undefined
  }
}

// 외부 클릭 시 드롭다운 닫기
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.relative')) {
    showCustomerDropdown.value = false
  }
}

// 페이지 이동
function goPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  pagination.skip = (page - 1) * pagination.limit
  loadData()
}

// 모달
function openCreateModal() {
  selectedWOId.value = null
  showFormModal.value = true
}

function openDetailModal(id: number) {
  selectedWOId.value = id
  showFormModal.value = true
}

function openIssueModal(id: number) {
  issueWOId.value = id
  showIssueModal.value = true
}

function openProductionCompleteModal(id: number) {
  completeWOId.value = id
  showCompleteModal.value = true
}

// 액션
async function handleApprove(id: number) {
  if (!confirm('작업지시를 승인하시겠습니까?')) return
  try {
    await workOrderApi.approve(id)
    alert('승인되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('승인 실패:', error)
    alert(error.response?.data?.detail?.message || '승인에 실패했습니다.')
  }
}

async function handleStartProduction(id: number) {
  if (!confirm('작업을 시작하시겠습니까?')) return
  try {
    await workOrderApi.startProduction(id)
    alert('작업이 시작되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('작업 시작 실패:', error)
    alert(error.response?.data?.detail?.message || '작업 시작에 실패했습니다.')
  }
}

async function handleCompleteInspection(id: number) {
  if (!confirm('검사를 완료하시겠습니까?')) return
  try {
    await workOrderApi.completeInspection(id)
    alert('검사가 완료되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('검사 완료 실패:', error)
    alert(error.response?.data?.detail?.message || '검사 완료에 실패했습니다.')
  }
}

async function handleShip(id: number) {
  if (!confirm('출하 처리하시겠습니까?')) return
  try {
    await workOrderApi.ship(id)
    alert('출하가 완료되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('출하 실패:', error)
    alert(error.response?.data?.detail?.message || '출하에 실패했습니다.')
  }
}

// 취소 처리 (휴지통 클릭 시)
async function handleCancel(id: number) {
  if (!confirm('작업지시서를 취소하시겠습니까?\n출고된 부품은 재고로 복구됩니다.')) return

  const reason = prompt('취소 사유를 입력하세요 (선택사항):')
  if (reason === null) return // prompt 취소됨

  try {
    await workOrderApi.cancel(id, reason || undefined)
    alert('작업지시서가 취소되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('취소 실패:', error)
    alert(error.response?.data?.detail?.message || '취소에 실패했습니다.')
  }
}

// 완전 삭제 (취소된 작업지시서만)
async function handlePermanentDelete(id: number) {
  if (!confirm('작업지시서를 완전히 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.')) return
  try {
    await workOrderApi.delete(id)
    alert('삭제되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('삭제 실패:', error)
    alert(error.response?.data?.detail?.message || '삭제에 실패했습니다.')
  }
}

// 롤백 가능 여부 확인
function canRollback(status: string): boolean {
  // SHIPPED, CANCELLED, RECEIVED는 롤백 불가
  return !['SHIPPED', 'CANCELLED', 'RECEIVED'].includes(status)
}

// 상태 롤백 처리
const rollbackLabels: Record<string, string> = {
  'APPROVED': '접수 상태로',
  'ISSUED': '승인 상태로 (재고 복구)',
  'IN_PROGRESS': '출고 상태로',
  'INSPECTION': '작업중 상태로',
  'PACKED': '검사 상태로',
}

async function handleRollback(id: number, currentStatus: string) {
  const label = rollbackLabels[currentStatus] || '이전 상태로'
  if (!confirm(`${label} 롤백하시겠습니까?
출고 상태에서 롤백 시 재고가 복구됩니다.`)) return
  try {
    await workOrderApi.rollback(id)
    alert('롤백이 완료되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('롤백 실패:', error)
    alert(error.response?.data?.detail?.message || '롤백에 실패했습니다.')
  }
}

async function handleRestore(id: number) {
  if (!confirm('취소된 작업지시서를 복원하시겠습니까?\n출고 상태였던 경우 승인 상태로 복원됩니다.')) return
  try {
    await workOrderApi.restore(id)
    alert('작업지시서가 복원되었습니다.')
    loadData()
  } catch (error: any) {
    console.error('복원 실패:', error)
    alert(error.response?.data?.detail?.message || '복원에 실패했습니다.')
  }
}

function handleSaved() {
  showFormModal.value = false
  loadData()
  loadPendingRequests()      // v0.20.0: 생산요청 목록 새로고침
  loadModifiedWorkOrders()   // v0.23.0: 수정된 작업지시서 새로고침
  loadStatusCounts()         // v0.22.0: 상태별 카운트 새로고침
  emit('data-changed')       // 부모에 알려 탭 뱃지 갱신
}

function handleIssued() {
  showIssueModal.value = false
  loadData()
}

function handleCompleted() {
  showCompleteModal.value = false
  loadData()
}

// v0.19.0: 다중 제품 완료수량 합계
function getCompletedQty(wo: WorkOrderListItem): number {
  if (wo.products && wo.products.length > 0) {
    return wo.products.reduce((sum, p) => sum + Number(p.completed_quantity || 0), 0)
  }
  return Number(wo.completed_quantity || 0)
}

// 포맷
function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('ko-KR')
}

// 포맷 (숫자)
function formatNumber(num: number): string {
  return num?.toLocaleString('ko-KR') || '0'
}

// 초기화
onMounted(() => {
  loadCustomers()
  loadPendingRequests()      // v0.20.0: 대기 중인 생산요청 로드
  loadModifiedWorkOrders()   // v0.23.0: 수정된 작업지시서 로드
  loadStatusCounts()         // v0.22.0: 상태별 카운트 로드
  loadData()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

// 부모 컴포넌트에서 호출할 수 있도록 expose
defineExpose({
  loadPendingRequests,
  loadModifiedWorkOrders,
  loadStatusCounts,
  loadData
})
</script>
