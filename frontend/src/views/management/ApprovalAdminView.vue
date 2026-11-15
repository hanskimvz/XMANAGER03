<template>
  <div class="approval-admin-view">
    <div class="page-header">
      <h1>전자결재</h1>
      <p class="subtitle">전자결재 관리</p>
    </div>
    <!-- 관리 페이지에서 분리한 전자결재 관리 패널 -->
    <ApprovalAdminPanel />
  </div>
</template>

<script setup lang="ts">
import ApprovalAdminPanel from '@/views/management/ApprovalAdminPanel.vue'
</script>

<style scoped>
.approval-admin-view {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 30px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
}

.subtitle {
  margin: 5px 0 0;
  color: #666;
}
</style>
