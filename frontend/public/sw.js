/*
 * X-Manager PWA 서비스워커 (최소 구성)
 * - 설치 가능(installable) 요건 충족용 fetch 핸들러
 * - API(/api) 와 비-GET 요청은 절대 캐시하지 않음(항상 네트워크 → 데이터 최신성 보장)
 * - 동일 출처 정적 자원만 "네트워크 우선, 실패 시 캐시" 로 처리
 * 참고: 서비스워커는 보안 컨텍스트(HTTPS 또는 localhost)에서만 활성화됨.
 */
const CACHE = 'xmanager-shell-v3'  // bump 시 activate 에서 옛 캐시 전부 삭제 → 아이콘/자원 강제 갱신

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  const url = new URL(req.url)

  // API · 비-GET · 타 출처 → 개입하지 않음(항상 네트워크)
  if (req.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api')) {
    return
  }

  // 정적 GET 요청: 네트워크 우선, 실패 시 캐시(오프라인 대비)
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.status === 200 && res.type === 'basic') {
          const copy = res.clone()
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {})
        }
        return res
      })
      .catch(() => caches.match(req))
  )
})

// ── 웹푸시 (v0.59.0): 앱이 닫혀 있어도 OS 알림 표시 ──
self.addEventListener('push', (event) => {
  let data = { title: 'X-Manager', body: '새 알림', url: '/' }
  try { if (event.data) data = Object.assign(data, event.data.json()) } catch (e) { /* ignore */ }
  // tag 미지정 시 각 알림이 독립적으로 쌓임(여러 건 동시 도착해도 모두 표시).
  // 과거 고정 tag('xmanager-notif') 는 알림을 하나로 병합해 이전 알림이 사라지는 버그였음.
  const opts = {
    body: data.body,
    icon: '/icon-192-v3.png',        // 알림 본문 큰 아이콘(풀컬러)
    badge: '/badge-x.png',           // 상태바 작은 아이콘: 투명배경+흰 X(안드로이드 실루엣). 불투명 사각형이면 흰 네모로 뜸
    data: { url: data.url || '/' },
  }
  if (data.tag) opts.tag = data.tag  // 서버가 의도적으로 그룹핑을 원할 때만 사용
  event.waitUntil(self.registration.showNotification(data.title, opts))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = (event.notification.data && event.notification.data.url) || '/'
  const targetPath = (function () { try { return new URL(target, self.location.origin).pathname } catch (e) { return target } })()
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      // 1) 이미 target 경로를 열고 있는 창이 있으면 그 창을 포커스(불필요한 이동/리로드 없음)
      for (const c of clients) {
        try { if (new URL(c.url).pathname === targetPath && 'focus' in c) return c.focus() } catch (e) { /* ignore */ }
      }
      // 2) 없으면 아무 앱 창을 포커스 후 target 으로 이동
      for (const c of clients) {
        if ('focus' in c) {
          if ('navigate' in c) { try { c.navigate(target) } catch (e) { /* ignore */ } }
          return c.focus()
        }
      }
      // 3) 열린 창이 없으면 새 창
      if (self.clients.openWindow) return self.clients.openWindow(target)
    })
  )
})
