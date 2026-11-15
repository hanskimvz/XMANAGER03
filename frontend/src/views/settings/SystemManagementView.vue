<template>
  <div class="system-view">
    <div class="page-header">
      <h1>시스템 관리</h1>
      <p class="subtitle">DB 백업 · 동기화 및 서버 연결 정보</p>
    </div>

    <!-- 시스템 정보 -->
    <div class="info-cards">
      <div class="info-card">
        <div class="info-icon">
          <i class="fas fa-server"></i>
        </div>
        <div class="info-content">
          <span class="info-label">환경</span>
          <span class="info-value" :class="systemInfo.environment">
            {{ environmentLabel }}
          </span>
        </div>
      </div>
      <div class="info-card">
        <div class="info-icon">
          <i class="fas fa-database"></i>
        </div>
        <div class="info-content">
          <span class="info-label">데이터베이스</span>
          <span class="info-value">{{ systemInfo.database }}</span>
        </div>
      </div>
      <div class="info-card">
        <div class="info-icon">
          <i class="fas fa-archive"></i>
        </div>
        <div class="info-content">
          <span class="info-label">백업 수</span>
          <span class="info-value">{{ systemInfo.backup_count }}개</span>
        </div>
      </div>
      <div class="info-card">
        <div class="info-icon">
          <i class="fas fa-hdd"></i>
        </div>
        <div class="info-content">
          <span class="info-label">백업 용량</span>
          <span class="info-value">{{ systemInfo.total_backup_size }}</span>
        </div>
      </div>
    </div>

    <!-- 서버 정보 (v0.12.0) -->
    <div class="server-section">
      <h2>서버 연결 정보</h2>

      <!-- API 서버 연결 정보 -->
      <div class="connection-info-box">
        <div class="connection-header">
          <i class="fas fa-plug"></i>
          <span>현재 연결 정보</span>
        </div>
        <div class="connection-grid">
          <div class="connection-item">
            <span class="conn-label">API 서버</span>
            <span class="conn-value highlight">{{ apiServerUrl }}</span>
          </div>
          <div class="connection-item">
            <span class="conn-label">DB 서버</span>
            <span class="conn-value">{{ systemInfo.backend_host }}:{{ systemInfo.backend_port }}</span>
          </div>
          <div class="connection-item">
            <span class="conn-label">현재 DB</span>
            <span class="conn-value db-badge" :class="systemInfo.environment">{{ systemInfo.database }}</span>
          </div>
          <div class="connection-item">
            <span class="conn-label">API 버전</span>
            <span class="conn-value">v{{ systemInfo.api_version }}</span>
          </div>
        </div>
      </div>

      <!-- 운영/개발 서버 카드 -->
      <div class="server-cards">
        <div
          v-for="server in systemInfo.servers"
          :key="server.database_name"
          class="server-card"
          :class="{ 'active': server.is_current }"
        >
          <div class="server-header">
            <span class="server-name">{{ server.name }}</span>
            <span v-if="server.is_current" class="current-badge">현재 연결</span>
          </div>
          <div class="server-details">
            <div class="detail-row">
              <span class="detail-label">환경:</span>
              <span class="detail-value" :class="server.environment">
                {{ server.environment === 'production' ? '운영' : '개발' }}
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">DB 이름:</span>
              <span class="detail-value db-name">{{ server.database_name }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">DB IP:</span>
              <span class="detail-value ip-value">{{ server.host }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">DB 포트:</span>
              <span class="detail-value port-value">{{ server.port }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 작업 버튼 -->
    <div class="action-section">
      <h2>DB 작업</h2>
      <div class="action-buttons">
        <button class="btn btn-primary" @click="showBackupModal = true" :disabled="isLoading">
          <i class="fas fa-download"></i>
          백업 생성
        </button>
        <button class="btn btn-warning" @click="showSyncModal = true" :disabled="isLoading">
          <i class="fas fa-sync"></i>
          DB 동기화
        </button>
        <button class="btn btn-secondary" @click="loadData" :disabled="isLoading">
          <i class="fas fa-refresh"></i>
          새로고침
        </button>
      </div>
    </div>

    <!-- 백업 목록 -->
    <div class="backup-section">
      <h2>백업 목록 <span class="count">({{ backupList.total_count }}개)</span></h2>

      <div v-if="isLoading" class="loading">
        <i class="fas fa-spinner fa-spin"></i> 로딩 중...
      </div>

      <table v-else-if="backupList.backups.length > 0" class="backup-table">
        <thead>
          <tr>
            <th>파일명</th>
            <th>크기</th>
            <th>생성일시</th>
            <th>유형</th>
            <th>작업</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="backup in backupList.backups" :key="backup.filename">
            <td class="filename">{{ backup.filename }}</td>
            <td>{{ backup.size_display }}</td>
            <td>{{ backup.created_at }}</td>
            <td>
              <span class="badge" :class="backup.is_daily ? 'badge-daily' : 'badge-hourly'">
                {{ backup.is_daily ? '일별' : '시간별' }}
              </span>
            </td>
            <td class="actions">
              <button
                class="btn btn-sm btn-success"
                @click="openRestoreModal(backup)"
                title="복원"
              >
                <i class="fas fa-upload"></i>
              </button>
              <button
                class="btn btn-sm btn-danger"
                @click="handleDelete(backup)"
                title="삭제"
              >
                <i class="fas fa-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-else class="empty-state">
        <i class="fas fa-archive"></i>
        <p>백업 파일이 없습니다.</p>
      </div>
    </div>

    <!-- 백업 모달 -->
    <div v-if="showBackupModal" class="modal-overlay">
      <div class="modal">
        <div class="modal-header">
          <h3>DB 백업 생성</h3>
          <button class="close-btn" @click="showBackupModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p class="info-text">
            <i class="fas fa-info-circle"></i>
            백업할 데이터베이스를 선택하세요.
          </p>
          <div class="backup-options">
            <label class="backup-option">
              <input type="radio" v-model="backupSource" value="production">
              <div class="option-content">
                <strong>운영 DB 백업</strong>
                <span>xmanager (실제 데이터)</span>
              </div>
            </label>
            <label class="backup-option">
              <input type="radio" v-model="backupSource" value="development">
              <div class="option-content">
                <strong>개발 DB 백업</strong>
                <span>xmanager_dev (테스트 데이터)</span>
              </div>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showBackupModal = false">취소</button>
          <button class="btn btn-primary" @click="handleBackup" :disabled="isLoading">
            <i class="fas fa-download"></i> 백업 실행
          </button>
        </div>
      </div>
    </div>

    <!-- 동기화 모달 -->
    <div v-if="showSyncModal" class="modal-overlay">
      <div class="modal">
        <div class="modal-header">
          <h3>DB 동기화</h3>
          <button class="close-btn" @click="showSyncModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p class="warning-text">
            <i class="fas fa-exclamation-triangle"></i>
            동기화하면 대상 DB의 기존 데이터가 덮어씌워집니다!
          </p>
          <div class="sync-options">
            <label class="sync-option">
              <input type="radio" v-model="syncDirection" value="prod_to_dev">
              <div class="option-content">
                <strong>운영 → 개발</strong>
                <span>운영 데이터를 개발 환경으로 복사 (안전)</span>
              </div>
            </label>
            <label class="sync-option">
              <input type="radio" v-model="syncDirection" value="dev_to_prod">
              <div class="option-content">
                <strong>개발 → 운영</strong>
                <span>개발 데이터를 운영 환경으로 복사 (주의!)</span>
              </div>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showSyncModal = false">취소</button>
          <button class="btn btn-warning" @click="handleSync" :disabled="isLoading">
            <i class="fas fa-sync"></i> 동기화 실행
          </button>
        </div>
      </div>
    </div>

    <!-- 복원 모달 -->
    <div v-if="showRestoreModal" class="modal-overlay">
      <div class="modal">
        <div class="modal-header">
          <h3>백업 복원</h3>
          <button class="close-btn" @click="showRestoreModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p><strong>파일:</strong> {{ selectedBackup?.filename }}</p>
          <p class="warning-text">
            <i class="fas fa-exclamation-triangle"></i>
            복원하면 선택한 DB의 기존 데이터가 덮어씌워집니다!
          </p>
          <div class="restore-options">
            <label class="restore-option">
              <input type="radio" v-model="restoreTarget" value="development">
              <div class="option-content">
                <strong>개발 DB로 복원</strong>
                <span>xmanager_dev에 복원 (안전)</span>
              </div>
            </label>
            <label class="restore-option">
              <input type="radio" v-model="restoreTarget" value="production">
              <div class="option-content">
                <strong>운영 DB로 복원</strong>
                <span>xmanager에 복원 (주의!)</span>
              </div>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showRestoreModal = false">취소</button>
          <button class="btn btn-primary" @click="handleRestore" :disabled="isLoading">
            <i class="fas fa-upload"></i> 복원 실행
          </button>
        </div>
      </div>
    </div>

    <!-- 토스트 메시지 -->
    <div v-if="toast.show" class="toast" :class="toast.type">
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import apiClient from '@/api/client'
import {
  getSystemInfo,
  getBackups,
  createBackup,
  restoreBackup,
  syncDatabases,
  deleteBackup,
  type BackupInfo,
  type BackupListResponse,
  type SystemInfoResponse
} from '@/api/admin'

// 상태
const isLoading = ref(false)
const systemInfo = ref<SystemInfoResponse>({
  environment: '',
  database: '',
  storage_path: '',
  backup_count: 0,
  total_backup_size: '0 B',
  servers: [],
  api_version: '',
  backend_host: '',
  backend_port: 0
})
const backupList = ref<BackupListResponse>({
  backups: [],
  total_count: 0,
  total_size: '0 B'
})

// 모달 상태
const showBackupModal = ref(false)
const showSyncModal = ref(false)
const showRestoreModal = ref(false)
const backupSource = ref<'production' | 'development'>('production')
const syncDirection = ref<'prod_to_dev' | 'dev_to_prod'>('prod_to_dev')
const restoreTarget = ref<'production' | 'development'>('development')
const selectedBackup = ref<BackupInfo | null>(null)

// 토스트
const toast = ref({
  show: false,
  message: '',
  type: 'success'
})

// 환경 라벨
const environmentLabel = computed(() => {
  switch (systemInfo.value.environment) {
    case 'production': return '운영'
    case 'development': return '개발'
    default: return '기본'
  }
})

// API 서버 URL (프론트엔드가 연결 중인 백엔드 서버)
const apiServerUrl = computed(() => {
  // apiClient 의 baseURL 기준. 상대 경로(/api/v1)면 현재 접속한 origin 을 거쳐 프록시된다.
  const base = apiClient.defaults.baseURL || '/api/v1'
  return /^https?:\/\//.test(base) ? new URL(base).host : `${window.location.host}${base}`
})

// 데이터 로드
const loadData = async () => {
  isLoading.value = true
  try {
    const [sysInfo, backups] = await Promise.all([
      getSystemInfo(),
      getBackups()
    ])
    systemInfo.value = sysInfo
    backupList.value = backups
  } catch (error) {
    showToast('데이터 로드 실패', 'error')
  } finally {
    isLoading.value = false
  }
}

// 백업 생성
const handleBackup = async () => {
  const sourceLabel = backupSource.value === 'production' ? '운영' : '개발'
  if (!confirm(`${sourceLabel} DB를 백업하시겠습니까?`)) return

  isLoading.value = true
  showBackupModal.value = false
  try {
    const result = await createBackup({ source_db: backupSource.value })
    showToast(result.message, 'success')
    await loadData()
  } catch (error) {
    showToast('백업 실패', 'error')
  } finally {
    isLoading.value = false
  }
}

// 복원 모달 열기
const openRestoreModal = (backup: BackupInfo) => {
  selectedBackup.value = backup
  restoreTarget.value = 'development'
  showRestoreModal.value = true
}

// 복원 실행
const handleRestore = async () => {
  if (!selectedBackup.value) return

  const targetLabel = restoreTarget.value === 'production' ? '운영' : '개발'
  if (!confirm(`정말로 ${targetLabel} DB에 복원하시겠습니까?\n기존 데이터가 모두 삭제됩니다!`)) return

  isLoading.value = true
  showRestoreModal.value = false
  try {
    const result = await restoreBackup({
      filename: selectedBackup.value.filename,
      target_db: restoreTarget.value
    })
    showToast(result.message, 'success')
    await loadData()
  } catch (error) {
    showToast('복원 실패', 'error')
  } finally {
    isLoading.value = false
  }
}

// 동기화 실행
const handleSync = async () => {
  const directionLabel = syncDirection.value === 'prod_to_dev' ? '운영 → 개발' : '개발 → 운영'
  if (!confirm(`정말로 DB를 동기화하시겠습니까?\n(${directionLabel})\n대상 DB의 데이터가 모두 덮어씌워집니다!`)) return

  isLoading.value = true
  showSyncModal.value = false
  try {
    const result = await syncDatabases({ direction: syncDirection.value })
    showToast(result.message, 'success')
    await loadData()
  } catch (error) {
    showToast('동기화 실패', 'error')
  } finally {
    isLoading.value = false
  }
}

// 백업 삭제
const handleDelete = async (backup: BackupInfo) => {
  if (!confirm(`'${backup.filename}' 백업을 삭제하시겠습니까?`)) return

  isLoading.value = true
  try {
    const result = await deleteBackup(backup.filename)
    showToast(result.message, 'success')
    await loadData()
  } catch (error) {
    showToast('삭제 실패', 'error')
  } finally {
    isLoading.value = false
  }
}

// 토스트 표시
const showToast = (message: string, type: 'success' | 'error') => {
  toast.value = { show: true, message, type }
  setTimeout(() => {
    toast.value.show = false
  }, 3000)
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.system-view {
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

/* 정보 카드 */
.info-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.info-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.info-icon {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: #e3f2fd;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1976d2;
  font-size: 20px;
}

.info-content {
  display: flex;
  flex-direction: column;
}

.info-label {
  font-size: 12px;
  color: #666;
}

.info-value {
  font-size: 18px;
  font-weight: 600;
}

.info-value.production {
  color: #d32f2f;
}

.info-value.development {
  color: #388e3c;
}

/* 서버 정보 섹션 (v0.12.0) */
.server-section {
  margin-bottom: 30px;
}

.server-section h2 {
  font-size: 18px;
  margin-bottom: 15px;
}

/* 연결 정보 박스 */
.connection-info-box {
  background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  color: white;
}

.connection-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 15px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.2);
}

.connection-header i {
  font-size: 16px;
}

.connection-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 15px;
}

.connection-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conn-label {
  font-size: 11px;
  opacity: 0.8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.conn-value {
  font-size: 15px;
  font-weight: 600;
  font-family: 'Consolas', 'Monaco', monospace;
}

.conn-value.highlight {
  background: rgba(255,255,255,0.2);
  padding: 4px 10px;
  border-radius: 6px;
  display: inline-block;
}

.conn-value.db-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
}

.conn-value.db-badge.production {
  background: #ffcdd2;
  color: #c62828;
}

.conn-value.db-badge.development {
  background: #c8e6c9;
  color: #2e7d32;
}

.server-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 15px;
}

.server-card {
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  border: 2px solid transparent;
  transition: all 0.2s;
}

.server-card.active {
  border-color: #1976d2;
  background: linear-gradient(to right, #e3f2fd, white);
}

.server-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.server-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.current-badge {
  background: #1976d2;
  color: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.server-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-label {
  font-size: 13px;
  color: #666;
}

.detail-value {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.detail-value.production {
  color: #d32f2f;
  font-weight: 600;
}

.detail-value.development {
  color: #388e3c;
  font-weight: 600;
}

.detail-value.db-name {
  font-family: monospace;
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 4px;
}

.detail-value.ip-value,
.detail-value.port-value {
  font-family: 'Consolas', 'Monaco', monospace;
  background: #e3f2fd;
  color: #1565c0;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

/* 작업 섹션 */
.action-section {
  margin-bottom: 30px;
}

.action-section h2 {
  font-size: 18px;
  margin-bottom: 15px;
}

.action-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

/* 버튼 */
.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #1976d2;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1565c0;
}

.btn-secondary {
  background: #757575;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #616161;
}

.btn-warning {
  background: #f57c00;
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: #ef6c00;
}

.btn-success {
  background: #388e3c;
  color: white;
}

.btn-danger {
  background: #d32f2f;
  color: white;
}

.btn-sm {
  padding: 6px 10px;
  font-size: 12px;
}

/* 백업 테이블 */
.backup-section h2 {
  font-size: 18px;
  margin-bottom: 15px;
}

.backup-section h2 .count {
  font-weight: normal;
  color: #666;
  font-size: 14px;
}

.backup-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.backup-table th,
.backup-table td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.backup-table th {
  background: #f5f5f5;
  font-weight: 600;
  font-size: 13px;
  color: #333;
}

.backup-table td {
  font-size: 13px;
}

.backup-table .filename {
  font-family: monospace;
  font-size: 12px;
}

.backup-table .actions {
  display: flex;
  gap: 5px;
}

.badge {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.badge-daily {
  background: #e3f2fd;
  color: #1976d2;
}

.badge-hourly {
  background: #f3e5f5;
  color: #7b1fa2;
}

/* 로딩 & 빈 상태 */
.loading, .empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

.empty-state i {
  font-size: 48px;
  margin-bottom: 15px;
  opacity: 0.5;
}

/* 모달 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  padding: 15px 20px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.info-text {
  background: #e3f2fd;
  color: #1565c0;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.info-text i {
  margin-right: 8px;
}

.warning-text {
  background: #fff3e0;
  color: #e65100;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.warning-text i {
  margin-right: 8px;
}

.backup-options, .sync-options, .restore-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.backup-option, .sync-option, .restore-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 15px;
  border: 2px solid #eee;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.backup-option:hover, .sync-option:hover, .restore-option:hover {
  border-color: #1976d2;
}

.backup-option input:checked + .option-content,
.sync-option input:checked + .option-content,
.restore-option input:checked + .option-content {
  color: #1976d2;
}

.option-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.option-content strong {
  font-size: 14px;
}

.option-content span {
  font-size: 12px;
  color: #666;
}

/* 토스트 */
.toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  padding: 15px 25px;
  border-radius: 8px;
  color: white;
  font-weight: 500;
  z-index: 2000;
  animation: slideIn 0.3s ease;
}

.toast.success {
  background: #388e3c;
}

.toast.error {
  background: #d32f2f;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
