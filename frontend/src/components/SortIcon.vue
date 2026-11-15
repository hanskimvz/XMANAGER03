<template>
  <span class="inline-flex flex-col ml-1">
    <!-- 오름차순 화살표 -->
    <svg
      :class="[
        'w-3 h-3 -mb-1',
        active && !desc ? 'text-blue-600' : 'text-gray-300'
      ]"
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path fill-rule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L10 6.414l-3.293 3.293a1 1 0 01-1.414 0z" clip-rule="evenodd" />
    </svg>
    <!-- 내림차순 화살표 -->
    <svg
      :class="[
        'w-3 h-3',
        active && desc ? 'text-blue-600' : 'text-gray-300'
      ]"
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path fill-rule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L10 13.586l3.293-3.293a1 1 0 011.414 0z" clip-rule="evenodd" />
    </svg>
  </span>
</template>

<script setup lang="ts">
defineProps<{
  active: boolean
  desc: boolean
}>()
</script>
