<script setup lang="ts">
// 조직도 노드(재귀) — 카드 1개 + 하위 조직 목록. 연결선은 아래 .org-tree CSS 가 그린다.
import { orgTypeBadge, orgTypeLabel, type Department } from '@/api/department'

export interface OrgTreeNode {
  dept: Department
  children: OrgTreeNode[]
}

defineProps<{ node: OrgTreeNode; selectedId: number | null }>()
const emit = defineEmits<{ (e: 'select', id: number): void }>()
</script>

<template>
  <li>
    <button
      type="button"
      class="org-card"
      :class="{ 'org-card-selected': node.dept.id === selectedId, 'org-card-inactive': !node.dept.is_active }"
      @click="emit('select', node.dept.id)"
    >
      <span class="org-badge" :class="orgTypeBadge(node.dept.org_type)">{{ orgTypeLabel(node.dept.org_type) }}</span>
      <span class="org-name">{{ node.dept.name }}</span>
      <span v-if="node.dept.manager_name" class="org-manager">{{ node.dept.manager_name }}</span>
      <span class="org-count">{{ node.dept.member_count }}명<template v-if="!node.dept.is_active"> · 비활성</template></span>
    </button>
    <ul v-if="node.children.length">
      <OrgChartNode
        v-for="child in node.children"
        :key="child.dept.id"
        :node="child"
        :selected-id="selectedId"
        @select="(id) => emit('select', id)"
      />
    </ul>
  </li>
</template>

<!-- 재귀 컴포넌트 전체에 걸치는 트리 연결선이라 scoped 를 쓰지 않고 .org-tree 로 범위를 한정한다 -->
<style>
.org-tree ul {
  display: flex;
  justify-content: center;
  position: relative;
  margin: 0;
  padding: 24px 0 0;
  list-style: none;
}

.org-tree li {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  padding: 24px 8px 0;
}

/* 형제를 잇는 가로선(::before 왼쪽 절반, ::after 오른쪽 절반)과 카드로 내려오는 세로선 */
.org-tree li::before,
.org-tree li::after {
  content: '';
  position: absolute;
  top: 0;
  right: 50%;
  width: 50%;
  height: 24px;
  border-top: 2px solid #d1d5db;
}

.org-tree li::after {
  right: auto;
  left: 50%;
  border-left: 2px solid #d1d5db;
}

.org-tree li:first-child::before,
.org-tree li:last-child::after {
  border-top: 0 none;
}

/* 외동이면 가로선 없이 세로선만 */
.org-tree li:only-child::before {
  display: none;
}

/* 상위 카드에서 내려오는 세로선 */
.org-tree ul ul::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  height: 24px;
  border-left: 2px solid #d1d5db;
}

/* 최상위 줄: 위로 이어질 조직이 없으므로 연결선을 그리지 않는다 */
.org-tree > ul {
  padding-top: 0;
}

.org-tree > ul > li {
  padding-top: 0;
}

.org-tree > ul > li::before,
.org-tree > ul > li::after {
  display: none;
}

.org-tree .org-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 152px;
  padding: 14px 10px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.org-tree .org-card:hover {
  border-color: #93c5fd;
}

.org-tree .org-card-selected {
  border-color: #2563eb;
  box-shadow: 0 1px 6px rgba(37, 99, 235, 0.2);
}

.org-tree .org-card-inactive {
  opacity: 0.55;
}

.org-tree .org-badge {
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.org-tree .org-name {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  text-align: center;
  word-break: keep-all;
}

.org-tree .org-manager {
  font-size: 12px;
  color: #4b5563;
}

.org-tree .org-count {
  font-size: 12px;
  color: #9ca3af;
}
</style>
