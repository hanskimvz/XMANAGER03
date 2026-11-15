<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import ToastContainer from '@/components/ToastContainer.vue'
import MobileTabBar from '@/components/MobileTabBar.vue'
import NavBar from '@/components/NavBar.vue'
import SideBar from '@/components/SideBar.vue'
import { useAuth } from '@/stores/auth'
import { loadDepartments } from '@/api/department'
import { useNavState } from '@/composables/useNavState'

const route = useRoute()
const { isLoggedIn, fetchMe } = useAuth()
const isLoginPage = computed(() => route.name === 'login')

// MobileTabBar가 표시할 배지(결재 대기·공지 미열람) — NavBar가 갱신, 여기서는 읽기만
const { pendingCount, announceUnread } = useNavState()

// 로그인 상태면 최신 사용자 정보(직급/부서 등)·부서 마스터 동기화 — 재로그인 없이 반영
if (isLoggedIn.value) { fetchMe(); loadDepartments() }
</script>

<template>
  <div class="min-h-screen bg-gray-100">
    <!-- Toast 알림 컨테이너 -->
    <ToastContainer />

    <!-- 네비바 (로그인 페이지에서는 숨김) -->
    <NavBar v-if="!isLoginPage && isLoggedIn" />

    <!-- 본문 영역: 활성 그룹이 있으면 좌측 사이드바 + 본문, 없으면 본문만 -->
    <div class="flex">
      <!-- 사이드바는 활성 그룹이 없거나 접힌 경우 스스로 렌더링하지 않음 -->
      <SideBar />
      <!-- Main Content (모바일은 하단 탭바 높이만큼 여백 확보) -->
      <main class="flex-1 min-w-0" :class="{ 'pb-16 lg:pb-0': !isLoginPage && isLoggedIn }">
        <RouterView />
      </main>
    </div>

    <!-- 모바일 하단 탭바 (lg 미만 전용) -->
    <MobileTabBar v-if="!isLoginPage && isLoggedIn" :pending="pendingCount" :announce-unread="announceUnread" />
  </div>
</template>
