<template>
  <div class="temp-page">
    <div class="container">
      <h1 class="page-title">임시 페이지1</h1>
      <div class="route-info">
        <h2>현재 Route 정보</h2>
        <div class="info-grid">
          <div class="info-item">
            <label>Path:</label>
            <span>{{ route.path }}</span>
          </div>
          <div class="info-item">
            <label>Name:</label>
            <span>{{ route.name }}</span>
          </div>
          <div class="info-item">
            <label>Full Path:</label>
            <span>{{ route.fullPath }}</span>
          </div>
          <div class="info-item">
            <label>Hash:</label>
            <span>{{ route.hash || 'none' }}</span>
          </div>
          <div class="info-item">
            <label>Params:</label>
            <pre>{{ JSON.stringify(route.params, null, 2) }}</pre>
          </div>
          <div class="info-item">
            <label>Query:</label>
            <pre>{{ JSON.stringify(route.query, null, 2) }}</pre>
          </div>
          <div class="info-item">
            <label>Meta:</label>
            <pre>{{ JSON.stringify(route.meta, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<style scoped>
.temp-page {
  padding: 2rem;
  min-height: 100vh;
  background-color: #f8f9fa;
}

.container {
  max-width: 800px;
  margin: 0 auto;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 2rem;
}

.page-title {
  color: #495057;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e9ecef;
}

.route-info h2 {
  color: #007bff;
  margin-bottom: 1.5rem;
}

.info-grid {
  display: grid;
  gap: 1rem;
}

.info-item {
  display: grid;
  grid-template-columns: 120px 1fr;
  align-items: start;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #007bff;
}

.info-item label {
  font-weight: 600;
  color: #495057;
}

.info-item span {
  color: #6c757d;
  word-break: break-all;
}

.info-item pre {
  background: #e9ecef;
  padding: 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 768px) {
  .temp-page {
    padding: 1rem;
  }
  
  .info-item {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }
}
</style> 