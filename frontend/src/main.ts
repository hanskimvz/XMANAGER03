import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')

// 배포로 사라진 옛 청크 preload 실패 시(Vite) 최신 번들로 1회 자동 새로고침(라우터 onError 와 동일 플래그 공유)
window.addEventListener('vite:preloadError', () => {
  if (!sessionStorage.getItem('xm:chunk-reload')) {
    sessionStorage.setItem('xm:chunk-reload', '1')
    window.location.reload()
  }
})

// PWA 서비스워커 등록 (보안 컨텍스트=HTTPS/localhost 에서만 활성)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}
