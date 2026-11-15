<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useAuth } from '@/stores/auth'
import { type MenuGroup } from '@/router/menu'
import { approvalApi } from '@/api/approval'
import { announcementApi } from '@/api/announcement'
import { notificationApi, type NotificationItem } from '@/api/notification'
import { pushSupported, enablePush, ensurePushSubscribed } from '@/api/push'
import { useToast } from '@/composables/useToast'
import { downloadAuthedUrl } from '@/utils/download'
import { useMenu } from '@/composables/useMenu'
import { useNavState } from '@/composables/useNavState'

const toast = useToast()
const route = useRoute()
const router = useRouter()
const { isLoggedIn, isAdmin, userName, userPosition, userDepartment, logout } = useAuth()

// 메뉴(그룹/가시성) + 공유 상태(사이드바 접힘, 배지)
const { visibleItems, visibleSub, visibleGroups, activeGroup, firstLeafPath } = useMenu()
const { sidebarCollapsed, pendingCount, announceUnread } = useNavState()

const mobileMenuOpen = ref(false)

// 사용자 매뉴얼 다운로드 (docs/manual 의 최신 파일)
const downloadManual = async () => {
  try {
    await downloadAuthedUrl('/manual/download', 'X-Manager_사용자매뉴얼.pptx')
  } catch {
    toast.error('매뉴얼을 불러오지 못했습니다. 관리자에게 문의하세요.')
  }
}

// 그룹 버튼 클릭: 사이드바 펼친 상태로 + 보이는 첫 메뉴로 이동
function openGroup(g: MenuGroup) {
  sidebarCollapsed.value = false
  const first = firstLeafPath(g.children)
  if (first) router.push(first)
}

// 네비바 햄버거: 데스크톱(lg↑)은 좌측 사이드바 토글, 모바일은 상단 드롭다운 메뉴 토글
function onHamburger() {
  if (window.matchMedia('(max-width: 1023px)').matches) {
    mobileMenuOpen.value = !mobileMenuOpen.value
  } else {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }
}

// 결재 대기 건수 배지 (로그인 시 + 라우트 이동 시 갱신) — MobileTabBar와 공유(useNavState)
async function loadPendingCount() {
  if (!isLoggedIn.value) {
    pendingCount.value = 0
    return
  }
  try {
    const res = await approvalApi.pendingCount()
    pendingCount.value = res.data.count
  } catch { /* ignore */ }
}

// 공지 미열람 건수 배지
async function loadAnnounceUnread() {
  if (!isLoggedIn.value) {
    announceUnread.value = 0
    return
  }
  try {
    announceUnread.value = await announcementApi.unreadCount()
  } catch { /* ignore */ }
}

// ===== 인앱 알림(종 아이콘) =====
const notifUnread = ref(0)
const showNotif = ref(false)
const notifItems = ref<NotificationItem[]>([])
const notifLoading = ref(false)

async function loadNotifUnread() {
  if (!isLoggedIn.value) {
    notifUnread.value = 0
    return
  }
  try {
    notifUnread.value = await notificationApi.unreadCount()
  } catch { /* ignore */ }
}

async function loadNotifList(withSpinner = false) {
  if (withSpinner) notifLoading.value = true
  try {
    const res = await notificationApi.list({ limit: 20 })
    notifItems.value = res.items
    notifUnread.value = res.unread
  } catch {
    if (withSpinner) toast.error('알림을 불러오지 못했습니다')
  } finally {
    if (withSpinner) notifLoading.value = false
  }
}

async function toggleNotif() {
  showNotif.value = !showNotif.value
  if (showNotif.value) await loadNotifList(true)
}

async function onNotifClick(item: NotificationItem) {
  showNotif.value = false
  if (!item.is_read) {
    try {
      await notificationApi.markRead(item.id)
      item.is_read = true
      notifUnread.value = Math.max(0, notifUnread.value - 1)
    } catch { /* ignore */ }
  }
  if (item.link) router.push(item.link)
}

async function markAllNotif() {
  try {
    await notificationApi.markAllRead()
    notifItems.value.forEach(n => { n.is_read = true })
    notifUnread.value = 0
  } catch {
    toast.error('모두 읽음 처리에 실패했습니다')
  }
}

// 알림 유형별 아이콘
function notifIcon(type: string): string {
  if (type === 'APPROVAL_APPROVED') return '✅'
  if (type === 'APPROVAL_REJECTED') return '⛔'
  if (type === 'APPROVAL_RECALLED') return '↩️'
  if (type === 'APPROVAL_EXECUTION') return '📦'
  if (type === 'APPROVAL_EXECUTED') return '✅'
  if (type === 'APPROVAL_REFERENCE') return '👀'
  if (type === 'APPROVAL_COMMENT') return '💬'
  if (type === 'ANNOUNCEMENT') return '📢'
  return '📄'  // APPROVAL_REQUEST 등 결재 요청
}

// ===== 웹푸시(브라우저/OS 알림) =====
// 'unsupported' | 'default'(미결정) | 'granted' | 'denied'
const pushPerm = ref<'unsupported' | 'default' | 'granted' | 'denied'>('unsupported')
const isIos = /iPhone|iPad|iPod/.test(navigator.userAgent)
const pushNeedsSetup = ref(false)  // 권한은 있는데 구독 저장 실패 → 재설정 필요 안내
function refreshPushPerm() {
  pushPerm.value = pushSupported() ? (Notification.permission as any) : 'unsupported'
}
const pushBusy = ref(false)
async function enablePushNotif() {
  if (pushBusy.value) return
  pushBusy.value = true
  try {
    const r = await enablePush()
    refreshPushPerm()
    if (r.ok) {
      pushNeedsSetup.value = false
      showNotif.value = false
      alert('✅ 알림이 켜졌습니다. 이제 앱을 닫아도 새 알림이 폰으로 옵니다.')
    } else {
      alert('알림 켜기 실패\n\n' + r.reason)
    }
  } finally {
    pushBusy.value = false
  }
}

// 상대 시간 표기 (방금 / N분 전 / N시간 전 / M.DD)
function notifTime(iso: string): string {
  const t = new Date(iso).getTime()
  if (isNaN(t)) return ''
  const diff = Date.now() - t
  const min = Math.floor(diff / 60000)
  if (min < 1) return '방금'
  if (min < 60) return `${min}분 전`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}시간 전`
  const d = new Date(t)
  return `${d.getMonth() + 1}.${String(d.getDate()).padStart(2, '0')}`
}

// 라우트 변경 시 모바일 메뉴 닫기 + 배지 갱신 + 알림 패널 닫기
watch(() => route.path, () => {
  mobileMenuOpen.value = false
  showNotif.value = false
  loadPendingCount()
  loadAnnounceUnread()
  loadNotifUnread()
}, { immediate: true })

// 배지 즉시 갱신 이벤트 — 하위 화면(공지 열람/삭제 등)이 새로고침 없이 배지를 갱신하도록
function onAnnounceRefresh() {
  loadAnnounceUnread()
  if (showNotif.value) loadNotifList()
  else loadNotifUnread()
}

// 알림 배지 주기적 갱신(60초) — 화면 이동 없이도 새 알림 감지
let notifTimer: number | undefined
onMounted(async () => {
  refreshPushPerm()
  // 이미 권한을 준 사용자는 로그인 시 조용히 구독 갱신(기기 재구독·키 만료 대비).
  if (isLoggedIn.value && pushPerm.value === 'granted') {
    const ok = await ensurePushSubscribed()
    pushNeedsSetup.value = !ok
  }
  window.addEventListener('xm:announce-refresh', onAnnounceRefresh)
  notifTimer = window.setInterval(() => {
    if (showNotif.value) loadNotifList()  // 열려있으면 목록+카운트, 아니면 카운트만
    else loadNotifUnread()
    loadPendingCount()
  }, 60000)
})
onUnmounted(() => {
  if (notifTimer) clearInterval(notifTimer)
  window.removeEventListener('xm:announce-refresh', onAnnounceRefresh)
})

function handleLogout() {
  logout()
  window.location.href = '/login'
}
</script>

<template>
  <!-- Navigation Header — 화면 맨 위에 full-width로 고정 -->
  <nav class="bg-white shadow-lg sticky top-0 z-30">
    <!-- full-width: 햄버거/로고를 화면 맨 왼쪽에 붙임 -->
    <div class="w-full px-3 sm:px-4 lg:px-4">
      <div class="flex items-center justify-between h-14">
        <!-- 좌: 햄버거(맨 왼쪽) + 로고 -->
        <div class="flex-shrink-0 flex items-center gap-1">
          <button
            @click="onHamburger"
            class="p-2 rounded-md text-gray-600 hover:bg-gray-100"
            aria-label="메뉴 열기/닫기"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <RouterLink to="/" class="flex items-center gap-2">
            <img src="/xbeamtech-logo.png" alt="XbeamTech" class="h-7" />
          </RouterLink>
        </div>

        <!-- 중앙: PC 메뉴 그룹 버튼 (lg 이상에서만 표시) -->
        <div class="hidden lg:flex items-center space-x-1">
          <button
            v-for="g in visibleGroups"
            :key="g.key"
            type="button"
            class="nav-link"
            :class="{ 'nav-link-active': activeGroup?.key === g.key }"
            @click="openGroup(g)"
          >
            <span v-if="g.icon" class="mr-1" aria-hidden="true">{{ g.icon }}</span>{{ g.label }}
          </button>
        </div>

        <!-- 우: 알림 종 + 사용자 정보 -->
        <div class="flex items-center gap-3">
          <!-- 종 아이콘 (인앱 알림 수신함) -->
          <div class="relative">
            <button @click="toggleNotif" class="relative p-2 rounded-md text-gray-600 hover:bg-gray-100" aria-label="알림">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              <span v-if="notifUnread > 0"
                class="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 flex items-center justify-center text-[10px] font-bold rounded-full bg-red-500 text-white">
                {{ notifUnread > 99 ? '99+' : notifUnread }}
              </span>
            </button>

            <!-- 드롭다운 패널 -->
            <template v-if="showNotif">
              <div class="fixed inset-0 z-40" @click="showNotif = false"></div>
              <div class="absolute right-0 mt-2 w-80 max-w-[calc(100vw-1.5rem)] bg-white rounded-lg shadow-xl border z-50 overflow-hidden">
                <div class="flex items-center justify-between px-4 py-2.5 border-b">
                  <span class="text-sm font-semibold text-gray-800">알림</span>
                  <button v-if="notifItems.some(n => !n.is_read)" @click="markAllNotif" class="text-xs text-blue-600 hover:underline">모두 읽음</button>
                </div>
                <!-- 권한 있으나 구독 저장 실패 → 재설정 유도 -->
                <div v-if="pushPerm === 'granted' && pushNeedsSetup" class="px-4 py-2 bg-amber-50 border-b text-[11px] text-amber-700">
                  알림 구독이 활성화되지 않았습니다 — 아래 버튼으로 다시 설정해 주세요
                </div>
                <!-- 브라우저/OS 알림 켜기 — 미설정일 때만 노출 -->
                <button
                  v-if="pushPerm === 'default' || (pushPerm === 'granted' && pushNeedsSetup)"
                  :disabled="pushBusy"
                  @click="enablePushNotif"
                  class="w-full flex items-center gap-2 px-4 py-2.5 bg-blue-50 hover:bg-blue-100 text-left border-b disabled:opacity-60"
                >
                  <span class="text-base leading-none">🔔</span>
                  <span class="min-w-0 flex-1">
                    <span class="block text-xs font-medium text-blue-800">
                      {{ pushBusy ? '설정 중…' : (pushNeedsSetup ? '휴대폰·PC 알림 다시 켜기' : '휴대폰·PC 알림 켜기') }}
                    </span>
                    <span class="block text-[11px] text-blue-600">앱을 닫아도 새 알림을 받아볼 수 있어요</span>
                  </span>
                </button>
                <!-- 구독 완료 상태: 버튼 대신 조용한 확인 표시 -->
                <div v-else-if="pushPerm === 'granted'" class="px-4 py-2 border-b text-[11px] text-gray-400 flex items-center gap-1.5">
                  <span class="text-green-500 text-sm leading-none">✓</span> 휴대폰·PC 알림이 켜져 있습니다
                </div>
                <div v-else-if="pushPerm === 'denied'" class="px-4 py-2 bg-amber-50 border-b text-[11px] text-amber-700">
                  브라우저 알림이 차단됨 — 주소창 자물쇠 → 알림 허용
                </div>
                <!-- 아이폰 사파리(미설치): PushManager 미지원 → 홈 화면 추가 안내 -->
                <div v-else-if="pushPerm === 'unsupported' && isIos" class="px-4 py-2.5 bg-blue-50 border-b text-[11px] text-blue-700 leading-relaxed">
                  📱 아이폰은 <b>공유 → 홈 화면에 추가</b>로 앱을 설치한 뒤,<br>그 앱 아이콘으로 열어서 알림을 켤 수 있어요 <span class="text-blue-400">(iOS 16.4+)</span>
                </div>
                <div class="max-h-96 overflow-y-auto">
                  <div v-if="notifLoading" class="p-6 text-center text-sm text-gray-400">불러오는 중...</div>
                  <div v-else-if="notifItems.length === 0" class="p-8 text-center text-sm text-gray-400">
                    <div class="text-2xl mb-1">🔔</div>
                    받은 알림이 없습니다
                  </div>
                  <button
                    v-for="item in notifItems" :key="item.id"
                    @click="onNotifClick(item)"
                    class="w-full text-left px-4 py-3 border-b last:border-b-0 hover:bg-gray-50 flex gap-2"
                    :class="item.is_read ? 'bg-white' : 'bg-blue-50/60'"
                  >
                    <span class="mt-0.5 text-base leading-none">{{ notifIcon(item.type) }}</span>
                    <span class="min-w-0 flex-1">
                      <span class="block text-sm font-medium text-gray-900 truncate">{{ item.title }}</span>
                      <span v-if="item.message" class="block text-xs text-gray-500 truncate">{{ item.message }}</span>
                      <span class="block text-[11px] text-gray-400 mt-0.5">{{ notifTime(item.created_at) }}</span>
                    </span>
                    <span v-if="!item.is_read" class="mt-1 w-2 h-2 rounded-full bg-blue-500 shrink-0"></span>
                  </button>
                </div>
              </div>
            </template>
          </div>

          <span class="text-sm text-gray-600 whitespace-nowrap hidden sm:inline">
            <span class="font-medium">{{ userName }}</span>
            <span v-if="userPosition" class="ml-1 text-gray-500">{{ userPosition }}</span>
            <span v-if="userDepartment" class="ml-1 text-xs text-gray-400">· {{ userDepartment }}</span>
            <span v-if="isAdmin" class="ml-1 px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">관리자</span>
          </span>
          <!-- <button @click="downloadManual" title="사용자 매뉴얼 다운로드" class="text-sm text-gray-400 hover:text-blue-600 whitespace-nowrap hidden sm:inline">📖 매뉴얼</button> -->
          <button @click="handleLogout" class="text-sm text-gray-400 hover:text-gray-600 whitespace-nowrap hidden sm:inline">로그아웃</button>
        </div>
      </div>
    </div>

    <!-- 모바일 메뉴 (드롭다운) -->
    <div v-if="mobileMenuOpen" class="lg:hidden border-t bg-white">
      <div class="px-4 py-3 space-y-1">
        <RouterLink to="/menu" class="mobile-nav-link flex items-center gap-2" active-class="mobile-nav-link-active" @click="mobileMenuOpen = false">
          <span aria-hidden="true">🏠</span><span>모바일 홈</span>
        </RouterLink>
        <button @click="downloadManual(); mobileMenuOpen = false" class="mobile-nav-link text-left w-full">📖 매뉴얼 다운로드</button>
        <!-- 메뉴 그룹 — 모바일은 그룹별로 펼쳐서 표시 -->
        <div v-for="g in visibleGroups" :key="g.key" class="pt-2 mt-2 border-t">
          <div class="px-3 py-1 text-xs font-bold text-gray-400">
            <span v-if="g.icon" class="mr-1" aria-hidden="true">{{ g.icon }}</span>{{ g.label }}
          </div>
          <template v-for="item in visibleItems(g.children)" :key="item.path || item.label">
            <!-- 2단 부모: 라벨(path 있으면 이동 링크) + 하위 메뉴(더 깊게 들여쓰기) -->
            <template v-if="visibleSub(item).length">
              <RouterLink
                v-if="item.path"
                :to="item.path"
                class="mobile-nav-link pl-6 font-semibold"
                active-class="mobile-nav-link-active"
                @click="mobileMenuOpen = false"
              >{{ item.label }}</RouterLink>
              <div v-else class="px-3 pt-1 text-[11px] font-semibold text-gray-400 pl-6">{{ item.label }}</div>
              <RouterLink
                v-for="sub in visibleSub(item)"
                :key="sub.path"
                :to="sub.path!"
                class="mobile-nav-link pl-9"
                active-class="mobile-nav-link-active"
                @click="mobileMenuOpen = false"
              >{{ sub.label }}</RouterLink>
            </template>
            <!-- 리프 -->
            <RouterLink
              v-else
              :to="item.path!"
              class="mobile-nav-link pl-6"
              active-class="mobile-nav-link-active"
              @click="mobileMenuOpen = false"
            >{{ item.label }}</RouterLink>
          </template>
        </div>
        <!-- 모바일에서 사용자 정보 + 로그아웃 -->
        <div class="pt-2 mt-2 border-t flex items-center justify-between">
          <span class="text-sm text-gray-600">
            <span class="font-medium">{{ userName }}</span>
            <span v-if="userPosition" class="ml-1 text-gray-500">{{ userPosition }}</span>
            <span v-if="userDepartment" class="ml-1 text-xs text-gray-400">· {{ userDepartment }}</span>
            <span v-if="isAdmin" class="ml-1 px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">관리자</span>
          </span>
          <div class="flex items-center gap-3">
            <button @click="handleLogout(); mobileMenuOpen = false" class="text-sm text-red-500 hover:text-red-700">로그아웃</button>
          </div>
        </div>
      </div>
    </div>
  </nav>
</template>

<style scoped>
/* PC 메뉴 그룹 버튼 */
.nav-link {
  @apply inline-flex items-center px-2.5 py-1.5 rounded-md text-sm font-bold text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors whitespace-nowrap;
}
.nav-link-active {
  @apply bg-blue-600 text-white hover:bg-blue-700 hover:text-white;
}
/* 모바일 메뉴 */
.mobile-nav-link {
  @apply block px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100 hover:text-gray-900 transition-colors;
}
.mobile-nav-link-active {
  @apply bg-blue-50 text-blue-700 font-bold;
}
</style>
