<template>
  <div class="bg-white rounded-lg shadow p-4">
    <h3 class="text-sm font-semibold text-gray-900 mb-3">범례</h3>

    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <!-- 발주서 -->
      <div>
        <h4 class="text-xs font-medium text-gray-500 mb-2">발주서</h4>
        <div class="space-y-1.5">
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-blue-100 rounded text-blue-700"></span>
            <span class="text-xs text-gray-600">발주</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-orange-100 rounded text-orange-700"></span>
            <span class="text-xs text-gray-600">납기예정</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-green-100 rounded text-green-700"></span>
            <span class="text-xs text-gray-600">입고</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-purple-100 rounded text-purple-700"></span>
            <span class="text-xs text-gray-600">결제</span>
          </div>
        </div>
      </div>

      <!-- 작업지시서 예정 -->
      <div>
        <h4 class="text-xs font-medium text-gray-500 mb-2">작업지시서 (예정)</h4>
        <div class="space-y-1.5">
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-indigo-50 border-l-2 border-indigo-400 rounded"></span>
            <span class="text-xs text-gray-600">출고예정</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-yellow-50 border-l-2 border-yellow-400 rounded"></span>
            <span class="text-xs text-gray-600">생산예정</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-orange-50 border-l-2 border-orange-400 rounded"></span>
            <span class="text-xs text-gray-600">검사예정</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-teal-50 border-l-2 border-teal-400 rounded"></span>
            <span class="text-xs text-gray-600">포장예정</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-purple-50 border-l-2 border-purple-400 rounded"></span>
            <span class="text-xs text-gray-600">출하예정</span>
          </div>
        </div>
      </div>

      <!-- 작업지시서 완료 -->
      <div>
        <h4 class="text-xs font-medium text-gray-500 mb-2">작업지시서 (완료)</h4>
        <div class="space-y-1.5">
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-indigo-100 rounded"></span>
            <span class="text-xs text-gray-600">출고완료</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-yellow-100 rounded"></span>
            <span class="text-xs text-gray-600">생산시작</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-yellow-200 rounded"></span>
            <span class="text-xs text-gray-600">생산완료</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-orange-100 rounded"></span>
            <span class="text-xs text-gray-600">검사완료</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-teal-100 rounded"></span>
            <span class="text-xs text-gray-600">포장완료</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-purple-100 rounded"></span>
            <span class="text-xs text-gray-600">출하완료</span>
          </div>
        </div>
      </div>

      <!-- 휴가/출장 -->
      <div>
        <h4 class="text-xs font-medium text-gray-500 mb-2">휴가 / 출장</h4>
        <div class="space-y-1.5">
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-emerald-100 rounded text-emerald-700"></span>
            <span class="text-xs text-gray-600">휴가</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-violet-100 rounded text-violet-700"></span>
            <span class="text-xs text-gray-600">출장</span>
          </div>
        </div>
      </div>

      <!-- 등록 일정 (경영관리 > 일정등록) -->
      <div>
        <h4 class="text-xs font-medium text-gray-500 mb-2">등록 일정</h4>
        <div class="space-y-1.5">
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-amber-100 rounded"></span>
            <span class="text-xs text-gray-600">행사</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-teal-100 rounded"></span>
            <span class="text-xs text-gray-600">휴가</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-sky-100 rounded"></span>
            <span class="text-xs text-gray-600">외근</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-purple-100 rounded"></span>
            <span class="text-xs text-gray-600">출장</span>
          </div>
        </div>
      </div>

      <!-- 우선순위 -->
      <div>
        <h4 class="text-xs font-medium text-gray-500 mb-2">우선순위</h4>
        <div class="space-y-1.5">
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-gray-100 rounded"></span>
            <span class="text-xs text-gray-600">보통</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-gray-100 ring-1 ring-yellow-400 rounded"></span>
            <span class="text-xs text-yellow-700">높음</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-4 h-3 bg-gray-100 ring-2 ring-red-500 rounded"></span>
            <span class="text-xs text-red-700 font-medium">긴급</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 범례 컴포넌트 - 정적 UI
</script>
