<template>
  <div class="min-h-screen bg-gray-50">
    <div class="max-w-screen-2xl mx-auto">
      <!-- 영업대응 페이지에서 분리한 '데이터 집계' → 영업현황 -->
      <SalesAnalyticsContent />
    </div>
  </div>
</template>

<script setup lang="ts">
import SalesAnalyticsContent from '@/views/sales/components/SalesAnalyticsContent.vue'
</script>
