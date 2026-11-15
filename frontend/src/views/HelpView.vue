<template>
  <div class="container mx-auto px-4 py-8 max-w-6xl">
    <!-- 헤더 -->
    <div class="mb-8 flex items-center gap-6">
      <!-- 회사 로고 -->
      <img
        src="/xbeamtech-logo.png"
        alt="XbeamTech Logo"
        class="h-12"
      />
      <div>
        <h1 class="text-3xl font-bold text-gray-900 mb-2">X-Manager 사용 설명서</h1>
        <p class="text-gray-600">부품 관리 시스템 사용 가이드 v1.0</p>
      </div>
    </div>

    <!-- 목차 & 컨텐츠 레이아웃 -->
    <div class="flex gap-6">
      <!-- 좌측 목차 (Sticky) -->
      <aside class="hidden lg:block w-64 flex-shrink-0">
        <nav class="sticky top-4 bg-white rounded-lg shadow p-4 max-h-[calc(100vh-2rem)] overflow-y-auto">
          <h2 class="text-lg font-semibold text-gray-900 mb-3">목차</h2>
          <ul class="space-y-1 text-sm">
            <li v-for="section in sections" :key="section.id">
              <a
                :href="`#${section.id}`"
                class="block px-2 py-1.5 rounded hover:bg-gray-100 transition-colors"
                :class="{ 'bg-blue-50 text-blue-700 font-medium': activeSection === section.id }"
                @click="activeSection = section.id"
              >
                {{ section.title }}
              </a>
              <ul v-if="section.children" class="ml-3 mt-1 space-y-1">
                <li v-for="child in section.children" :key="child.id">
                  <a
                    :href="`#${child.id}`"
                    class="block px-2 py-1 text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded"
                  >
                    {{ child.title }}
                  </a>
                </li>
              </ul>
            </li>
          </ul>
        </nav>
      </aside>

      <!-- 우측 컨텐츠 -->
      <main class="flex-1 min-w-0">
        <!-- 1. 시스템 개요 -->
        <section id="overview" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-2xl font-bold text-gray-900 mb-4 flex items-center">
            <span class="bg-blue-100 text-blue-800 rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">1</span>
            시스템 개요
          </h2>

          <div class="prose max-w-none">
            <h3 id="what-is" class="text-lg font-semibold text-gray-800 mt-4 mb-2">X-Manager란?</h3>
            <p class="text-gray-600 mb-4">
              X-Manager는 제조업체를 위한 <strong>부품 관리 시스템(PLM)</strong>입니다.
              부품 마스터 관리부터 BOM 구성, 원가 계산, 재고 관리까지 통합적으로 지원합니다.
            </p>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 my-6">
              <div class="bg-blue-50 rounded-lg p-4">
                <h4 class="font-semibold text-blue-800 mb-2">핵심 기능</h4>
                <ul class="text-sm text-blue-700 space-y-1">
                  <li>- 부품 마스터 관리 (자동 품번 생성)</li>
                  <li>- BOM(Bill of Materials) 구성</li>
                  <li>- 원가 계산 (BOM 기반, 이동평균법)</li>
                  <li>- 거래처 관리 (공급업체/고객사)</li>
                </ul>
              </div>
              <div class="bg-green-50 rounded-lg p-4">
                <h4 class="font-semibold text-green-800 mb-2">확장 기능</h4>
                <ul class="text-sm text-green-700 space-y-1">
                  <li>- 발주 및 입고 관리</li>
                  <li>- 작업지시서 관리</li>
                  <li>- 재고 관리 (로트 추적, FIFO)</li>
                  <li>- 파일 첨부 (도면, 사진, 문서)</li>
                </ul>
              </div>
            </div>

            <h3 id="requirements" class="text-lg font-semibold text-gray-800 mt-6 mb-2">시스템 요구사항</h3>
            <div class="bg-gray-50 rounded-lg p-4">
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p class="font-medium text-gray-700">권장 브라우저</p>
                  <p class="text-gray-600">Chrome 90+, Edge 90+, Firefox 88+</p>
                </div>
                <div>
                  <p class="font-medium text-gray-700">화면 해상도</p>
                  <p class="text-gray-600">최소 1280x720, 권장 1920x1080</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 2. 화면 구성 -->
        <section id="ui" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-2xl font-bold text-gray-900 mb-4 flex items-center">
            <span class="bg-blue-100 text-blue-800 rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">2</span>
            화면 구성
          </h2>

          <h3 id="menu" class="text-lg font-semibold text-gray-800 mt-4 mb-3">메뉴 구성</h3>
          <div class="overflow-x-auto">
            <table class="min-w-full text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-2 text-left font-semibold">메뉴</th>
                  <th class="px-4 py-2 text-left font-semibold">설명</th>
                  <th class="px-4 py-2 text-left font-semibold">경로</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr v-for="menu in menuList" :key="menu.path" class="hover:bg-gray-50">
                  <td class="px-4 py-2 font-medium">{{ menu.name }}</td>
                  <td class="px-4 py-2 text-gray-600">{{ menu.desc }}</td>
                  <td class="px-4 py-2">
                    <code class="bg-gray-100 px-2 py-0.5 rounded text-xs">{{ menu.path }}</code>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <h3 id="common-ui" class="text-lg font-semibold text-gray-800 mt-6 mb-3">공통 UI 요소</h3>

          <!-- 검색 영역 설명 -->
          <div class="bg-gray-50 rounded-lg p-4 mb-4">
            <h4 class="font-medium text-gray-800 mb-2">검색 영역</h4>
            <div class="flex flex-wrap gap-2 mb-2">
              <input type="text" placeholder="검색어 입력" class="border rounded px-3 py-1.5 text-sm w-40" disabled>
              <select class="border rounded px-3 py-1.5 text-sm" disabled>
                <option>대분류</option>
              </select>
              <select class="border rounded px-3 py-1.5 text-sm" disabled>
                <option>상태</option>
              </select>
              <button class="bg-blue-600 text-white px-4 py-1.5 rounded text-sm" disabled>검색</button>
            </div>
            <p class="text-xs text-gray-500">Enter 키로 검색 실행 가능</p>
          </div>

          <!-- 작업 버튼 설명 -->
          <div class="bg-gray-50 rounded-lg p-4 mb-4">
            <h4 class="font-medium text-gray-800 mb-2">작업 버튼</h4>
            <div class="flex gap-4 text-sm">
              <span class="flex items-center gap-1">
                <button class="p-1.5 rounded bg-blue-100 text-blue-600">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                </button>
                상세보기
              </span>
              <span class="flex items-center gap-1">
                <button class="p-1.5 rounded bg-yellow-100 text-yellow-600">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                </button>
                수정
              </span>
              <span class="flex items-center gap-1">
                <button class="p-1.5 rounded bg-red-100 text-red-600">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                </button>
                삭제
              </span>
            </div>
          </div>

          <!-- 토스트 알림 -->
          <div class="bg-gray-50 rounded-lg p-4">
            <h4 class="font-medium text-gray-800 mb-2">토스트 알림</h4>
            <div class="flex flex-wrap gap-2">
              <span class="px-3 py-1 rounded text-sm bg-green-100 text-green-800">성공</span>
              <span class="px-3 py-1 rounded text-sm bg-red-100 text-red-800">오류</span>
              <span class="px-3 py-1 rounded text-sm bg-yellow-100 text-yellow-800">경고</span>
              <span class="px-3 py-1 rounded text-sm bg-blue-100 text-blue-800">정보</span>
            </div>
          </div>
        </section>

        <!-- 3. 코드 마스터 -->
        <section id="code-master" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-2xl font-bold text-gray-900 mb-4 flex items-center">
            <span class="bg-blue-100 text-blue-800 rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">3</span>
            코드 마스터 관리
          </h2>

          <p class="text-gray-600 mb-4">
            코드 마스터는 부품 품번 생성 및 분류에 사용되는 기준 코드를 관리합니다.
            <router-link to="/codes" class="text-blue-600 hover:underline ml-1">바로가기 ></router-link>
          </p>

          <h3 class="text-lg font-semibold text-gray-800 mt-4 mb-3">품번 구성요소</h3>
          <div class="overflow-x-auto mb-4">
            <table class="min-w-full text-sm">
              <thead class="bg-blue-50">
                <tr>
                  <th class="px-4 py-2 text-left font-semibold">코드</th>
                  <th class="px-4 py-2 text-left font-semibold">자릿수</th>
                  <th class="px-4 py-2 text-left font-semibold">설명</th>
                  <th class="px-4 py-2 text-left font-semibold">예시</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr class="hover:bg-gray-50">
                  <td class="px-4 py-2 font-medium">대분류 (ProductLine)</td>
                  <td class="px-4 py-2">4자리</td>
                  <td class="px-4 py-2 text-gray-600">제품 라인 구분</td>
                  <td class="px-4 py-2"><code class="bg-gray-100 px-1 rounded">HB01, BI03, TF01</code></td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="px-4 py-2 font-medium">소분류 (PartGroup)</td>
                  <td class="px-4 py-2">3자리</td>
                  <td class="px-4 py-2 text-gray-600">품목군 구분</td>
                  <td class="px-4 py-2"><code class="bg-gray-100 px-1 rounded">DCP, PLP, OCP</code></td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="px-4 py-2 font-medium">재질 (Material)</td>
                  <td class="px-4 py-2">2자리</td>
                  <td class="px-4 py-2 text-gray-600">소재 구분</td>
                  <td class="px-4 py-2"><code class="bg-gray-100 px-1 rounded">A6, S4, XX</code></td>
                </tr>
                <tr class="hover:bg-gray-50">
                  <td class="px-4 py-2 font-medium">후처리 (Treatment)</td>
                  <td class="px-4 py-2">2자리</td>
                  <td class="px-4 py-2 text-gray-600">표면처리 구분</td>
                  <td class="px-4 py-2"><code class="bg-gray-100 px-1 rounded">NK, NN, WA</code></td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 품번 구조 시각화 -->
          <div class="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 mt-4">
            <h4 class="font-medium text-gray-800 mb-3">품번 구조 (v1.1)</h4>
            <div class="flex flex-wrap items-center gap-1 text-sm font-mono">
              <span class="bg-blue-200 px-2 py-1 rounded">HB01</span>
              <span class="text-gray-400">-</span>
              <span class="bg-green-200 px-2 py-1 rounded">DCP</span>
              <span class="text-gray-400">-</span>
              <span class="bg-yellow-200 px-2 py-1 rounded">00001</span>
              <span class="text-gray-400">-</span>
              <span class="bg-orange-200 px-2 py-1 rounded">A6</span>
              <span class="text-gray-400">-</span>
              <span class="bg-red-200 px-2 py-1 rounded">NK</span>
            </div>
            <div class="flex flex-wrap items-center gap-1 text-xs text-gray-500 mt-2">
              <span class="w-12 text-center">대분류</span>
              <span class="w-2"></span>
              <span class="w-10 text-center">소분류</span>
              <span class="w-2"></span>
              <span class="w-14 text-center">품목코드</span>
              <span class="w-2"></span>
              <span class="w-8 text-center">재질</span>
              <span class="w-2"></span>
              <span class="w-10 text-center">후처리</span>
            </div>
          </div>
        </section>

        <!-- 4. 부품 마스터 -->
        <section id="parts" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-2xl font-bold text-gray-900 mb-4 flex items-center">
            <span class="bg-blue-100 text-blue-800 rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">4</span>
            부품 마스터 관리
          </h2>

          <p class="text-gray-600 mb-4">
            부품의 기본 정보, 분류, 가격 정보 등을 관리합니다.
            <router-link to="/parts" class="text-blue-600 hover:underline ml-1">바로가기 ></router-link>
          </p>

          <h3 class="text-lg font-semibold text-gray-800 mt-4 mb-3">부품 등록 절차</h3>
          <ol class="list-decimal list-inside space-y-2 text-gray-600 mb-4">
            <li><strong>[+ 부품 등록]</strong> 버튼 클릭</li>
            <li>부품명, 대분류, 소분류, 품목코드 입력 (필수)</li>
            <li>재질, 후처리, 레벨 등 선택 (선택)</li>
            <li>미리보기 품번 확인 후 <strong>[저장]</strong></li>
          </ol>

          <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
            <h4 class="font-medium text-yellow-800 mb-1">품목코드 입력 안내</h4>
            <p class="text-sm text-yellow-700">
              품목코드는 앞 3자리만 입력하면 뒤 2자리(일련번호)가 자동 생성됩니다.
              예: <code class="bg-yellow-100 px-1 rounded">001</code> 입력 시 → <code class="bg-yellow-100 px-1 rounded">00101</code>, <code class="bg-yellow-100 px-1 rounded">00102</code> 자동 증가
            </p>
          </div>

          <h3 class="text-lg font-semibold text-gray-800 mt-6 mb-3">2단계 삭제 정책</h3>
          <div class="grid md:grid-cols-2 gap-4">
            <div class="bg-orange-50 rounded-lg p-4">
              <h4 class="font-medium text-orange-800 mb-2">1단계: 단종 처리</h4>
              <p class="text-sm text-orange-700">
                ACTIVE/INACTIVE 상태 삭제 시 → OBSOLETE(단종)으로 변경<br>
                데이터는 보존됨
              </p>
            </div>
            <div class="bg-red-50 rounded-lg p-4">
              <h4 class="font-medium text-red-800 mb-2">2단계: 완전 삭제</h4>
              <p class="text-sm text-red-700">
                OBSOLETE 상태 삭제 시 → DB에서 완전 삭제<br>
                복구 불가
              </p>
            </div>
          </div>
        </section>

        <!-- 5. BOM 관리 -->
        <section id="bom" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-2xl font-bold text-gray-900 mb-4 flex items-center">
            <span class="bg-blue-100 text-blue-800 rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">5</span>
            BOM 관리
          </h2>

          <p class="text-gray-600 mb-4">
            BOM(Bill of Materials)은 제품을 구성하는 부품의 계층 구조를 관리합니다.
            <router-link to="/bom" class="text-blue-600 hover:underline ml-1">바로가기 ></router-link>
          </p>

          <h3 class="text-lg font-semibold text-gray-800 mt-4 mb-3">BOM 레벨 체계</h3>
          <div class="overflow-x-auto mb-4">
            <table class="min-w-full text-sm">
              <thead class="bg-purple-50">
                <tr>
                  <th class="px-4 py-2 text-left font-semibold">레벨</th>
                  <th class="px-4 py-2 text-left font-semibold">코드</th>
                  <th class="px-4 py-2 text-left font-semibold">설명</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr class="hover:bg-gray-50"><td class="px-4 py-2">완제품</td><td class="px-4 py-2 font-mono">F</td><td class="px-4 py-2 text-gray-600">Finished Goods - 최종 제품</td></tr>
                <tr class="hover:bg-gray-50"><td class="px-4 py-2">패키지</td><td class="px-4 py-2 font-mono">P</td><td class="px-4 py-2 text-gray-600">Package - 포장 단위</td></tr>
                <tr class="hover:bg-gray-50"><td class="px-4 py-2">키트</td><td class="px-4 py-2 font-mono">K</td><td class="px-4 py-2 text-gray-600">Kit - 키트 구성품</td></tr>
                <tr class="hover:bg-gray-50"><td class="px-4 py-2">서브어셈블리</td><td class="px-4 py-2 font-mono">S</td><td class="px-4 py-2 text-gray-600">Sub-Assembly - 반제품</td></tr>
                <tr class="hover:bg-gray-50"><td class="px-4 py-2">단품</td><td class="px-4 py-2 font-mono">R</td><td class="px-4 py-2 text-gray-600">Raw Material/Part - 원자재/단품</td></tr>
              </tbody>
            </table>
          </div>

          <!-- BOM 트리 예시 -->
          <div class="bg-gray-50 rounded-lg p-4 font-mono text-sm">
            <h4 class="font-medium text-gray-800 mb-2 font-sans">BOM 트리 예시</h4>
            <div class="text-gray-700 whitespace-pre">HB01-DCP-00001 (하우징 어셈블리)
├── HB01-DCP-00010 (하우징 본체) × 1
│   ├── HB01-DCP-00011 (내부 프레임) × 1
│   └── HB01-DCP-00012 (실링 가스켓) × 2
├── HB01-DCP-00020 (커버) × 1
└── HB01-DCP-00030 (볼트 M4) × 4</div>
          </div>

          <div class="bg-red-50 border-l-4 border-red-400 p-4 mt-4">
            <h4 class="font-medium text-red-800 mb-1">순환 참조 방지</h4>
            <p class="text-sm text-red-700">
              시스템은 순환 참조(A→B→C→A)를 자동으로 감지하고 방지합니다.
              순환 참조 발생 시 오류 메시지가 표시됩니다.
            </p>
          </div>
        </section>

        <!-- 6. 원가 관리 -->
        <section id="cost" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-2xl font-bold text-gray-900 mb-4 flex items-center">
            <span class="bg-blue-100 text-blue-800 rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">6</span>
            원가 관리
          </h2>

          <p class="text-gray-600 mb-4">
            부품의 다양한 원가 정보를 관리하고 BOM 기반 원가를 자동 계산합니다.
          </p>

          <h3 class="text-lg font-semibold text-gray-800 mt-4 mb-3">단가 종류</h3>
          <div class="overflow-x-auto mb-4">
            <table class="min-w-full text-sm">
              <thead class="bg-green-50">
                <tr>
                  <th class="px-4 py-2 text-left font-semibold">단가 유형</th>
                  <th class="px-4 py-2 text-left font-semibold">설명</th>
                  <th class="px-4 py-2 text-left font-semibold">산출 방식</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr class="hover:bg-gray-50"><td class="px-4 py-2 font-medium">기준단가</td><td class="px-4 py-2 text-gray-600">목표/표준 단가</td><td class="px-4 py-2">수동 입력</td></tr>
                <tr class="hover:bg-gray-50"><td class="px-4 py-2 font-medium">재고단가</td><td class="px-4 py-2 text-gray-600">재고 평가 단가</td><td class="px-4 py-2">이동평균법 자동계산</td></tr>
                <tr class="hover:bg-gray-50"><td class="px-4 py-2 font-medium">최근단가</td><td class="px-4 py-2 text-gray-600">마지막 입고 단가</td><td class="px-4 py-2">입고 시 자동 갱신</td></tr>
                <tr class="hover:bg-gray-50"><td class="px-4 py-2 font-medium">평균단가</td><td class="px-4 py-2 text-gray-600">30일/90일/5건/10건</td><td class="px-4 py-2">자동 계산</td></tr>
              </tbody>
            </table>
          </div>

          <h3 class="text-lg font-semibold text-gray-800 mt-6 mb-3">BOM 원가 계산 공식</h3>
          <div class="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-4">
            <div class="font-mono text-sm space-y-2">
              <p><strong>총원가</strong> = 재료비 + 가공비 + 경비</p>
              <p><strong>재료비</strong> = Σ(하위부품 단가 × 수량)</p>
            </div>
            <hr class="my-3 border-gray-200">
            <p class="text-sm text-gray-600">
              <strong>단가 우선순위:</strong> 기준단가 > 최근단가 > 재고단가
            </p>
          </div>

          <h3 class="text-lg font-semibold text-gray-800 mt-6 mb-3">이동평균법 (재고단가)</h3>
          <div class="bg-gray-50 rounded-lg p-4 font-mono text-sm">
            <p class="mb-2">신규 재고단가 = (기존재고금액 + 신규입고금액) / 총수량</p>
            <hr class="my-2 border-gray-300">
            <p class="text-gray-600">예시:</p>
            <p class="text-gray-600">기존: 100개 × 1,000원 = 100,000원</p>
            <p class="text-gray-600">신규: 50개 × 1,200원 = 60,000원</p>
            <p class="text-green-700 font-semibold">→ 신규 재고단가 = 160,000 / 150 = 1,066.67원</p>
          </div>
        </section>

        <!-- 7. 발주/재고/작업지시서 (간략) -->
        <section id="operations" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-2xl font-bold text-gray-900 mb-4 flex items-center">
            <span class="bg-blue-100 text-blue-800 rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">7</span>
            운영 관리
          </h2>

          <div class="grid md:grid-cols-3 gap-4">
            <!-- 발주 -->
            <div class="border rounded-lg p-4">
              <h3 class="font-semibold text-orange-800 mb-2 flex items-center">
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                발주 관리
              </h3>
              <p class="text-sm text-gray-600 mb-2">
                DRAFT → CONFIRMED → ORDERED → RECEIVED
              </p>
              <router-link to="/purchase-orders" class="text-sm text-blue-600 hover:underline">바로가기 ></router-link>
            </div>

            <!-- 재고 -->
            <div class="border rounded-lg p-4">
              <h3 class="font-semibold text-teal-800 mb-2 flex items-center">
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
                재고 관리
              </h3>
              <p class="text-sm text-gray-600 mb-2">
                로트 추적, FIFO 출고, 재고 조정
              </p>
              <router-link to="/inventory" class="text-sm text-blue-600 hover:underline">바로가기 ></router-link>
            </div>

            <!-- 작업지시서 -->
            <div class="border rounded-lg p-4">
              <h3 class="font-semibold text-indigo-800 mb-2 flex items-center">
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/></svg>
                작업지시서
              </h3>
              <p class="text-sm text-gray-600 mb-2">
                7단계 상태, BOM 자동전개, 취소/복원
              </p>
              <router-link to="/work-orders" class="text-sm text-blue-600 hover:underline">바로가기 ></router-link>
            </div>
          </div>
        </section>

        <!-- 8. FAQ -->
        <section id="faq" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-2xl font-bold text-gray-900 mb-4 flex items-center">
            <span class="bg-blue-100 text-blue-800 rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">8</span>
            자주 묻는 질문 (FAQ)
          </h2>

          <div class="space-y-4">
            <div
              v-for="(faq, index) in faqs"
              :key="index"
              class="border rounded-lg overflow-hidden"
            >
              <button
                class="w-full px-4 py-3 text-left font-medium bg-gray-50 hover:bg-gray-100 flex justify-between items-center"
                @click="toggleFaq(index)"
              >
                <span>Q{{ index + 1 }}. {{ faq.question }}</span>
                <svg
                  class="w-5 h-5 transition-transform"
                  :class="{ 'rotate-180': openFaqs.includes(index) }"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                </svg>
              </button>
              <div v-show="openFaqs.includes(index)" class="px-4 py-3 text-gray-600 text-sm">
                <p v-html="faq.answer"></p>
              </div>
            </div>
          </div>
        </section>

        <!-- 9. 단축키 & 용어 -->
        <section id="appendix" class="bg-white rounded-lg shadow p-6 mb-6">
          <h2 class="text-2xl font-bold text-gray-900 mb-4 flex items-center">
            <span class="bg-blue-100 text-blue-800 rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">9</span>
            부록
          </h2>

          <div class="grid md:grid-cols-2 gap-6">
            <!-- 단축키 -->
            <div>
              <h3 class="text-lg font-semibold text-gray-800 mb-3">단축키</h3>
              <table class="min-w-full text-sm">
                <tbody class="divide-y divide-gray-200">
                  <tr><td class="py-2"><kbd class="bg-gray-100 px-2 py-0.5 rounded">Enter</kbd></td><td class="py-2 text-gray-600">검색 실행</td></tr>
                  <tr><td class="py-2"><kbd class="bg-gray-100 px-2 py-0.5 rounded">Esc</kbd></td><td class="py-2 text-gray-600">모달 닫기</td></tr>
                  <tr><td class="py-2"><kbd class="bg-gray-100 px-2 py-0.5 rounded">Ctrl</kbd> + <kbd class="bg-gray-100 px-2 py-0.5 rounded">S</kbd></td><td class="py-2 text-gray-600">저장 (모달에서)</td></tr>
                </tbody>
              </table>
            </div>

            <!-- 용어 -->
            <div>
              <h3 class="text-lg font-semibold text-gray-800 mb-3">용어 정의</h3>
              <dl class="text-sm space-y-2">
                <div><dt class="font-medium text-gray-800">품번</dt><dd class="text-gray-600">부품을 식별하는 고유 코드</dd></div>
                <div><dt class="font-medium text-gray-800">BOM</dt><dd class="text-gray-600">Bill of Materials, 부품 구성표</dd></div>
                <div><dt class="font-medium text-gray-800">기준단가</dt><dd class="text-gray-600">사용자가 설정한 표준 단가</dd></div>
                <div><dt class="font-medium text-gray-800">FIFO</dt><dd class="text-gray-600">First In First Out, 선입선출</dd></div>
                <div><dt class="font-medium text-gray-800">로트</dt><dd class="text-gray-600">동일 조건으로 입고된 물량 단위</dd></div>
              </dl>
            </div>
          </div>
        </section>

        <!-- 하단 -->
        <div class="text-center text-gray-500 text-sm py-4">
          X-Manager 사용 설명서 v1.0 | 최종 업데이트: 2026-01-20
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// 목차 데이터
const sections = [
  { id: 'overview', title: '1. 시스템 개요', children: [
    { id: 'what-is', title: 'X-Manager란?' },
    { id: 'requirements', title: '시스템 요구사항' }
  ]},
  { id: 'ui', title: '2. 화면 구성', children: [
    { id: 'menu', title: '메뉴 구성' },
    { id: 'common-ui', title: '공통 UI 요소' }
  ]},
  { id: 'code-master', title: '3. 코드 마스터' },
  { id: 'parts', title: '4. 부품 마스터' },
  { id: 'bom', title: '5. BOM 관리' },
  { id: 'cost', title: '6. 원가 관리' },
  { id: 'operations', title: '7. 운영 관리' },
  { id: 'faq', title: '8. FAQ' },
  { id: 'appendix', title: '9. 부록' }
]

// 메뉴 목록
const menuList = [
  { name: '코드 마스터', desc: '분류, 재질, 후처리 등 코드 관리', path: '/codes' },
  { name: '부품 마스터', desc: '부품 등록, 품번 자동생성', path: '/parts' },
  { name: 'BOM 관리', desc: 'BOM 트리, 원가 계산', path: '/bom' },
  { name: '거래처', desc: '공급업체/고객사 관리', path: '/partners' },
  { name: '발주서', desc: '발주 생성, 입고 처리', path: '/purchase-orders' },
  { name: '작업지시서', desc: '생산 작업 관리', path: '/work-orders' },
  { name: '재고', desc: '재고 현황, 로트 관리', path: '/inventory' }
]

// FAQ 데이터
const faqs = [
  {
    question: '품번이 중복되었다고 나옵니다.',
    answer: '품번은 시스템 전체에서 고유해야 합니다. 동일한 대분류 + 소분류 + 품목코드 조합이 있는지 확인하고, 품목코드 앞 3자리를 다른 값으로 변경해주세요.'
  },
  {
    question: 'BOM에서 부품을 추가할 수 없습니다.',
    answer: '다음 경우 BOM 추가가 제한됩니다: <br>- 순환 참조가 발생하는 경우 (A→B→C→A)<br>- 이미 동일한 하위부품이 등록된 경우<br>- 상위부품과 하위부품이 동일한 경우'
  },
  {
    question: '재고단가가 자동으로 바뀌었습니다.',
    answer: '재고단가는 이동평균법으로 자동 계산됩니다. 발주 입고 시 재계산되며, 수동 단가를 사용하려면 기준단가를 입력하세요.'
  },
  {
    question: '삭제한 부품을 복구하고 싶습니다.',
    answer: '1단계 삭제(단종)된 부품은 상태 필터에서 "단종" 선택 후 상태 변경이 가능합니다. 2단계 완전 삭제된 부품은 복구할 수 없습니다.'
  },
  {
    question: '발주서 입고처리를 취소하고 싶습니다.',
    answer: '발주서 상세에서 <strong>[롤백]</strong> 버튼을 사용하세요. RECEIVED → ORDERED 상태로 변경되며, 입고된 재고가 자동으로 차감됩니다.'
  },
  {
    question: '원가 계산 결과가 0원입니다.',
    answer: '하위 부품에 단가 정보가 없으면 0원으로 계산됩니다. 각 하위 부품의 기준단가 또는 최근단가를 입력하거나, 해당 부품의 발주 입고 이력이 필요합니다.'
  },
  {
    question: '파일 업로드가 실패합니다.',
    answer: '다음을 확인하세요:<br>- 파일 크기가 제한을 초과하지 않는지<br>- 허용된 확장자인지 (도면: PDF/DWG/STEP, 사진: JPG/PNG, 문서: PDF/DOC/XLS)<br>- 파일명에 특수문자가 없는지'
  }
]

const activeSection = ref('overview')
const openFaqs = ref<number[]>([])

const toggleFaq = (index: number) => {
  const i = openFaqs.value.indexOf(index)
  if (i === -1) {
    openFaqs.value.push(index)
  } else {
    openFaqs.value.splice(i, 1)
  }
}
</script>

<style scoped>
/* 스크롤 시 부드러운 이동 */
html {
  scroll-behavior: smooth;
}
</style>
