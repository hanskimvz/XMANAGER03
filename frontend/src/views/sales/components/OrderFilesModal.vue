<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[60] bg-black/50 flex items-center justify-center p-4" @click.self="$emit('close')">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        <div class="flex items-center justify-between px-5 py-3 border-b">
          <div class="min-w-0">
            <div class="text-sm font-semibold text-gray-800 truncate">🗂 {{ docNumber }} · 파일함</div>
            <div class="text-xs text-gray-400 truncate">{{ customerName || '거래처' }} — Nextcloud 주문 폴더(01~06)</div>
          </div>
          <button class="text-gray-400 hover:text-gray-700 text-lg leading-none px-2" @click="$emit('close')">✕</button>
        </div>
        <div class="p-4 overflow-auto">
          <CloudFileBrowser scope="order" :document-id="docId" :active="true" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import CloudFileBrowser from '@/components/CloudFileBrowser.vue'

interface Props {
  docId: number
  docNumber: string
  customerName?: string | null
}
defineProps<Props>()
defineEmits<{ close: [] }>()
</script>
