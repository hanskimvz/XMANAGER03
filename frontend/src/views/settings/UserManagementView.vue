<template>
  <div class="user-mgmt-view">
    <div class="page-header">
      <h1>사용자목록</h1>
      <p class="subtitle">사용자 계정 관리</p>
    </div>
    <!-- 관리 페이지에서 분리한 사용자 관리 패널 -->
    <UserManagementPanel />
  </div>
</template>

<script setup lang="ts">
import UserManagementPanel from '@/views/settings/UserManagementPanel.vue'
</script>

<style scoped>
.user-mgmt-view {
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
