<template>
  <div class="perm-view">
    <div class="page-header">
      <h1>권한 관리</h1>
      <p class="subtitle">역할·권한 매트릭스, 사용자 역할 배정, 권한 적용</p>
    </div>

    <!-- 상위 탭 -->
    <div class="perm-tabs">
      <button
        class="perm-tab"
        :class="{ active: activeTab === 'matrix' }"
        @click="activeTab = 'matrix'"
      >역할·권한 매트릭스</button>
      <button
        class="perm-tab"
        :class="{ active: activeTab === 'assign' }"
        @click="activeTab = 'assign'"
      >사용자역할배정</button>
      <button
        class="perm-tab"
        :class="{ active: activeTab === 'policy' }"
        @click="activeTab = 'policy'"
      >권한적용</button>
    </div>

    <!-- 역할·권한 매트릭스 / 사용자역할배정 — 단일 RolePermissionPanel 인스턴스를 유지하고 서브탭만 전환 -->
    <div v-show="activeTab !== 'policy'">
      <RolePermissionPanel
        :hide-tabs="true"
        :tab="activeTab === 'assign' ? 'assign' : 'roles'"
      />
    </div>

    <!-- 권한적용 -->
    <ModulePolicyPanel v-if="activeTab === 'policy'" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import RolePermissionPanel from '@/views/settings/RolePermissionPanel.vue'
import ModulePolicyPanel from '@/views/settings/ModulePolicyPanel.vue'

// 관리 페이지의 '권한 관리' + '권한 적용' 탭을 하나로 통합
const activeTab = ref<'matrix' | 'assign' | 'policy'>('matrix')
</script>

<style scoped>
.perm-view {
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

/* 상위 탭 */
.perm-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 2px solid #e0e0e0;
  margin-bottom: 24px;
}

.perm-tab {
  padding: 10px 20px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
  color: #666;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
}

.perm-tab:hover {
  color: #1976d2;
}

.perm-tab.active {
  color: #1976d2;
  border-bottom-color: #1976d2;
}
</style>
