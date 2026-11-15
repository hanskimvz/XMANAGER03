<template>
  <div class="container mx-auto px-4 py-8">
    <div class="max-w-4xl mx-auto bg-white shadow-lg rounded-lg overflow-hidden">
      <!-- 헤더 -->
      <div class="bg-gradient-to-r from-blue-500 to-blue-600 p-8 text-white">
        <!-- 회사 로고 -->
        <div class="mb-4">
          <img
            src="/xbeamtech-logo.png"
            alt="XbeamTech Logo"
            class="h-12 brightness-0 invert"
          />
        </div>
        <h1 class="text-4xl font-bold mb-2">X-Manager</h1>
        <p class="text-blue-100 text-lg">부품 관리 통합 시스템</p>
      </div>

      <!-- 본문 -->
      <div class="p-8">
        <!-- 시스템 정보 -->
        <section class="mb-8">
          <h2 class="text-2xl font-semibold mb-4 text-gray-800">시스템 정보</h2>
          <div class="grid grid-cols-2 gap-4">
            <div class="flex items-center">
              <span class="font-medium text-gray-700 w-32">버전:</span>
              <span class="text-gray-600">v0.19.0</span>
            </div>
            <div class="flex items-center">
              <span class="font-medium text-gray-700 w-32">개발사:</span>
              <span class="text-gray-600">엑스빔테크</span>
            </div>
            <div class="flex items-center">
              <span class="font-medium text-gray-700 w-32">개발일:</span>
              <span class="text-gray-600">2026년 1월</span>
            </div>
            <div class="flex items-center">
              <span class="font-medium text-gray-700 w-32">라이선스:</span>
              <span class="text-gray-600">Proprietary</span>
            </div>
          </div>
        </section>

        <!-- 주요 기능 -->
        <section class="mb-8">
          <h2 class="text-2xl font-semibold mb-4 text-gray-800">주요 기능</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              <h3 class="font-semibold text-blue-600 mb-2">코드 마스터 관리</h3>
              <p class="text-gray-600 text-sm">
                대분류/소분류, 개발구분, 부품유형, 재질, 후처리, 레벨 등 코드 마스터 관리
              </p>
            </div>
            <div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              <h3 class="font-semibold text-blue-600 mb-2">부품 마스터 관리</h3>
              <p class="text-gray-600 text-sm">
                부품 등록, 품번 자동생성 (v1.1), BOM 관리, 파일 첨부, 2단계 삭제 지원
              </p>
            </div>
            <div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              <h3 class="font-semibold text-blue-600 mb-2">거래처 관리</h3>
              <p class="text-gray-600 text-sm">
                공급업체/고객사 통합 관리, 연락처, 거래 조건, 문서 첨부
              </p>
            </div>
            <div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              <h3 class="font-semibold text-blue-600 mb-2">발주 관리</h3>
              <p class="text-gray-600 text-sm">
                발주서 작성, 입고 처리, 결제 관리, 상태 롤백, 파일 첨부
              </p>
            </div>
            <div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              <h3 class="font-semibold text-blue-600 mb-2">작업지시서 관리</h3>
              <p class="text-gray-600 text-sm">
                7단계 상태 전이, BOM 자동 전개, FIFO 출고, 취소/복원/롤백 기능
              </p>
            </div>
            <div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              <h3 class="font-semibold text-blue-600 mb-2">재고 관리</h3>
              <p class="text-gray-600 text-sm">
                로트 관리, 입출고 이력, FIFO 자동 선택, 생산 가용수량 체크
              </p>
            </div>
          </div>
        </section>

        <!-- 기술 스택 -->
        <section class="mb-8">
          <h2 class="text-2xl font-semibold mb-4 text-gray-800">기술 스택</h2>
          <div class="bg-gray-50 rounded-lg p-6">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <h3 class="font-semibold text-gray-700 mb-3">Frontend</h3>
                <ul class="space-y-2 text-gray-600 text-sm">
                  <li>• Vue.js 3.4+</li>
                  <li>• TypeScript</li>
                  <li>• Tailwind CSS 3.4</li>
                  <li>• Vite 7.3</li>
                  <li>• Vue Router 4</li>
                  <li>• Pinia 2.1+</li>
                  <li>• Axios</li>
                </ul>
              </div>
              <div>
                <h3 class="font-semibold text-gray-700 mb-3">Backend</h3>
                <ul class="space-y-2 text-gray-600 text-sm">
                  <li>• FastAPI 0.110.0</li>
                  <li>• Python 3.12</li>
                  <li>• SQLAlchemy 2.0.27</li>
                  <li>• Pydantic 2.6</li>
                  <li>• Alembic 1.13</li>
                  <li>• Uvicorn 0.27</li>
                </ul>
              </div>
              <div>
                <h3 class="font-semibold text-gray-700 mb-3">Database</h3>
                <ul class="space-y-2 text-gray-600 text-sm">
                  <li>• PostgreSQL 17.7</li>
                  <li>• 30+ 테이블</li>
                  <li>• 외래키 제약조건</li>
                  <li>• 트랜잭션 지원</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        <!-- 개발 진행률 -->
        <section class="mb-8">
          <h2 class="text-2xl font-semibold mb-4 text-gray-800">개발 진행률</h2>
          <div class="space-y-3">
            <div>
              <div class="flex justify-between mb-1">
                <span class="text-sm font-medium text-gray-700">코드 마스터 관리</span>
                <span class="text-sm font-medium text-green-600">100%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-green-500 h-2 rounded-full" style="width: 100%"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between mb-1">
                <span class="text-sm font-medium text-gray-700">부품/BOM 관리</span>
                <span class="text-sm font-medium text-green-600">100%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-green-500 h-2 rounded-full" style="width: 100%"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between mb-1">
                <span class="text-sm font-medium text-gray-700">거래처 관리</span>
                <span class="text-sm font-medium text-green-600">100%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-green-500 h-2 rounded-full" style="width: 100%"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between mb-1">
                <span class="text-sm font-medium text-gray-700">발주/재고 관리</span>
                <span class="text-sm font-medium text-green-600">100%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-green-500 h-2 rounded-full" style="width: 100%"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between mb-1">
                <span class="text-sm font-medium text-gray-700">작업지시서 관리</span>
                <span class="text-sm font-medium text-green-600">100%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-green-500 h-2 rounded-full" style="width: 100%"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between mb-1">
                <span class="text-sm font-medium text-gray-700">전체 진행률 (1단계)</span>
                <span class="text-sm font-medium text-blue-600">95%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-blue-500 h-2 rounded-full" style="width: 95%"></div>
              </div>
            </div>
          </div>
        </section>

        <!-- 연락처 -->
        <section>
          <h2 class="text-2xl font-semibold mb-4 text-gray-800">연락처</h2>
          <div class="bg-blue-50 rounded-lg p-6">
            <div class="space-y-2 text-gray-700">
              <p><span class="font-medium">회사:</span> 엑스빔테크 (XbeamTech)</p>
              <p><span class="font-medium">이메일:</span> support@xbeamtech.com</p>
              <p><span class="font-medium">GitHub:</span> <a href="https://github.com/xbeamtech" class="text-blue-600 hover:underline">github.com/xbeamtech</a></p>
            </div>
          </div>
        </section>
      </div>

      <!-- 푸터 -->
      <div class="bg-gray-50 p-6 text-center text-gray-600 text-sm border-t">
        <p>© 2026 XbeamTech. All rights reserved.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// About 페이지 로직 (필요시 추가)
</script>
