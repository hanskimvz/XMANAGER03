import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    host: '0.0.0.0',  // 모든 네트워크 인터페이스에서 접속 허용
    port: 5073,
    // 개발 서버: /api/* 를 백엔드(backend/config.json 의 server.port)로 프록시
    proxy: {
      '/api': {
        target: 'http://localhost:5198',
        changeOrigin: true,
      },
    },
  },
})
