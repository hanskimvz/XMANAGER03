import apiClient from './client'

export const pushApi = {
  vapidPublicKey: async (): Promise<string> =>
    (await apiClient.get('/push/vapid-public-key')).data.public_key,
  subscribe: async (subscription: any): Promise<void> => {
    await apiClient.post('/push/subscribe', subscription)
  },
  unsubscribe: async (endpoint: string): Promise<void> => {
    await apiClient.post('/push/unsubscribe', { endpoint })
  },
}

export type PushResult = { ok: true } | { ok: false; reason: string }

function urlB64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const out = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i)
  return out
}

export function pushSupported(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

/** iOS 홈화면 PWA(standalone) 여부 — iOS는 설치 후 홈 아이콘으로 열어야 푸시 가능 */
function isStandalone(): boolean {
  return (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches)
    || (navigator as any).standalone === true
}

/** 사용자 동작(버튼 클릭)에서 호출: 권한 요청 → 구독 → 서버 저장. 실패 시 사유 반환. */
export async function enablePush(): Promise<PushResult> {
  if (!('serviceWorker' in navigator))
    return { ok: false, reason: '이 브라우저는 서비스워커를 지원하지 않습니다.' }
  if (!('Notification' in window))
    return { ok: false, reason: '이 브라우저는 알림을 지원하지 않습니다.' }
  if (!('PushManager' in window)) {
    const ios = /iPhone|iPad|iPod/.test(navigator.userAgent)
    return {
      ok: false,
      reason: ios && !isStandalone()
        ? '아이폰은 Safari 공유 → "홈 화면에 추가"로 설치한 뒤, 그 홈 아이콘으로 열어서 다시 시도하세요. (iOS 16.4+ 필요)'
        : '이 브라우저는 웹푸시(PushManager)를 지원하지 않습니다.',
    }
  }
  let perm: NotificationPermission
  try {
    perm = await Notification.requestPermission()
  } catch (e: any) {
    return { ok: false, reason: '권한 요청 실패: ' + (e?.message || e) }
  }
  if (perm !== 'granted')
    return { ok: false, reason: `알림 권한이 허용되지 않았습니다 (상태: ${perm}).` }
  return subscribeNow()
}

/** 실제 구독 생성 + 서버 저장. 각 단계 실패를 사유로 구분해 반환. */
async function subscribeNow(): Promise<PushResult> {
  let reg: ServiceWorkerRegistration
  try {
    reg = await navigator.serviceWorker.ready
  } catch (e: any) {
    return { ok: false, reason: '서비스워커 준비 실패: ' + (e?.message || e) }
  }
  let publicKey: string
  try {
    publicKey = await pushApi.vapidPublicKey()
  } catch (e: any) {
    return { ok: false, reason: '서버 공개키 조회 실패(' + (e?.response?.status || e?.message || e) + ').' }
  }
  let sub: PushSubscription | null
  try {
    sub = await reg.pushManager.getSubscription()
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlB64ToUint8Array(publicKey) as BufferSource,
      })
    }
  } catch (e: any) {
    return { ok: false, reason: '구독 생성 실패: ' + (e?.name ? e.name + ' — ' : '') + (e?.message || e) }
  }
  try {
    await pushApi.subscribe(sub.toJSON())
  } catch (e: any) {
    return { ok: false, reason: '서버에 구독 저장 실패(' + (e?.response?.status || e?.message || e) + ').' }
  }
  return { ok: true }
}

/** 이미 권한이 있으면 조용히 구독을 보장(앱 로드 시 호출). 실패해도 조용히 무시. */
export async function ensurePushSubscribed(): Promise<boolean> {
  if (!pushSupported() || Notification.permission !== 'granted') return false
  const r = await subscribeNow()
  return r.ok
}

export async function disablePush(): Promise<void> {
  try {
    if (!pushSupported()) return
    const reg = await navigator.serviceWorker.ready
    const sub = await reg.pushManager.getSubscription()
    if (sub) {
      await pushApi.unsubscribe(sub.endpoint).catch(() => {})
      await sub.unsubscribe().catch(() => {})
    }
  } catch { /* ignore */ }
}
