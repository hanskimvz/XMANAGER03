// NavBar / SideBar / MobileTabBar 가 공유하는 전역(모듈 싱글톤) 상태.
//  - sidebarCollapsed: 네비바 햄버거로 토글, 사이드바가 읽음
//  - pendingCount / announceUnread: NavBar가 갱신, App의 MobileTabBar가 읽음
import { ref } from 'vue'

const sidebarCollapsed = ref(false)
const pendingCount = ref(0)
const announceUnread = ref(0)

export function useNavState() {
  return { sidebarCollapsed, pendingCount, announceUnread }
}
