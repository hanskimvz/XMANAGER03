<template>
  <div
    v-if="open"
    class="fixed inset-0 z-[60] bg-black/70 flex flex-col"
    @click.self="emit('close')"
  >
    <!-- 헤더 -->
    <div class="flex items-center justify-between px-4 py-2 text-white text-sm gap-3">
      <span class="truncate">{{ name }}</span>
      <div class="flex items-center gap-2 shrink-0">
        <button
          type="button"
          class="px-3 py-1 rounded bg-white/15 hover:bg-white/25 whitespace-nowrap"
          @click="emit('download')"
        >⤓ 다운로드</button>
        <button
          type="button"
          class="px-3 py-1 rounded bg-white/15 hover:bg-white/25 whitespace-nowrap"
          @click="emit('close')"
        >닫기 ✕</button>
      </div>
    </div>

    <!-- 본문 -->
    <div class="flex-1 min-h-0 flex items-center justify-center p-4" @click.self="emit('close')">
      <div v-if="loading" class="text-white/80 text-sm">불러오는 중...</div>
      <img
        v-else-if="kind === 'image'"
        :src="url"
        class="max-w-full max-h-full object-contain rounded shadow-lg bg-white"
        :alt="name"
      />
      <iframe
        v-else-if="kind === 'pdf'"
        :src="url"
        class="w-full h-full bg-white rounded shadow-lg"
        title="첨부 미리보기"
      ></iframe>
      <div v-else class="text-white/80 text-sm text-center">
        이 형식은 미리보기를 지원하지 않습니다.
        <div class="mt-3">
          <button
            type="button"
            class="px-4 py-2 rounded bg-white/20 hover:bg-white/30"
            @click="emit('download')"
          >다운로드로 확인</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'

const props = defineProps<{
  open: boolean
  url: string
  kind: 'image' | 'pdf' | 'other'
  name: string
  loading?: boolean
}>()
const emit = defineEmits<{ close: []; download: [] }>()

const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && props.open) emit('close') }
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>
