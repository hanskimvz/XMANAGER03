<template>
  <div class="admin-view">
    <div class="page-header">
      <h1>견적설정</h1>
      <p class="subtitle">견적 자동산출 설정 및 회사 계좌 관리</p>
    </div>

    <!-- 탭 (시스템 관리 → '설정', 전자결재 → '경영관리', 사용자 관리 → '설정 > 사용자목록'으로 분리됨) -->
    <div class="admin-tabs">
      <button
        v-if="isAdmin"
        class="admin-tab"
        :class="{ active: activeTab === 'quote-settings' }"
        @click="activeTab = 'quote-settings'"
      >견적 설정</button>
      <button
        v-if="isAdmin"
        class="admin-tab"
        :class="{ active: activeTab === 'bank-accounts' }"
        @click="activeTab = 'bank-accounts'"
      >회사 계좌</button>
    </div>

    <!-- 견적 자동산출 설정 탭 (관리자 전용) -->
    <QuoteSettingsPanel v-if="activeTab === 'quote-settings' && isAdmin" />

    <!-- 회사 은행 계좌(통화별) 탭 (관리자 전용) -->
    <CompanyBankAccountsPanel v-else-if="activeTab === 'bank-accounts' && isAdmin" />

  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import QuoteSettingsPanel from '@/views/sales/QuoteSettingsPanel.vue'
import CompanyBankAccountsPanel from '@/views/sales/CompanyBankAccountsPanel.vue'
import { useAuth } from '@/stores/auth'

// 탭 (시스템 관리 → '설정', 전자결재 → '경영관리', 사용자 관리·권한 관리·권한 적용 → '설정'으로 분리됨)
const activeTab = ref<'quote-settings' | 'bank-accounts'>('quote-settings')

// 인증 (관리자 여부)
const { isAdmin } = useAuth()
</script>

<style scoped>
.admin-view {
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

/* 탭 */
.admin-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 2px solid #e0e0e0;
  margin-bottom: 24px;
}

.admin-tab {
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

.admin-tab:hover {
  color: #1976d2;
}

.admin-tab.active {
  color: #1976d2;
  border-bottom-color: #1976d2;
}
</style>
