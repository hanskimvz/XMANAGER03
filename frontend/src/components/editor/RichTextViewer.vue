<template>
  <div class="rich-text-viewer" v-html="safeHtml"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import { VIEWER_ALLOWED_ATTR, VIEWER_ALLOWED_TAGS } from './editorConfig'

const props = withDefaults(defineProps<{ html?: string | null }>(), {
  html: '',
})

const safeHtml = computed(() => {
  if (!props.html) return ''
  return DOMPurify.sanitize(props.html, {
    ALLOWED_TAGS: VIEWER_ALLOWED_TAGS,
    ALLOWED_ATTR: VIEWER_ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
  })
})
</script>

<style scoped>
.rich-text-viewer {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.95rem;
  line-height: 1.7;
  color: #111827;
}

.rich-text-viewer :deep(p) {
  margin: 0 0 0.75rem;
}

.rich-text-viewer :deep(p:last-child) {
  margin-bottom: 0;
}

.rich-text-viewer :deep(mark) {
  padding: 0 2px;
  border-radius: 2px;
  color: inherit;
}

.rich-text-viewer :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  margin: 0.5rem 0;
}
</style>
