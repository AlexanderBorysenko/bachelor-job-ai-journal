<script setup lang="ts">
import MarkdownBlock from './MarkdownBlock.vue'
import GalleryBlock from './GalleryBlock.vue'
import FigureBlock from './FigureBlock.vue'

defineProps<{ blocks: any[]; media: Record<string, any> }>()

const REGISTRY: Record<string, any> = {
  markdown: MarkdownBlock,
  gallery: GalleryBlock,
  figure: FigureBlock,
}

function componentFor(type: string) {
  return REGISTRY[type] || null
}
</script>

<template>
  <div class="diary-content">
    <template v-for="(block, i) in blocks || []" :key="i">
      <component
        :is="componentFor(block.type)"
        v-if="componentFor(block.type)"
        :block="block"
        :media="media || {}"
      />
    </template>
  </div>
</template>

<style scoped>
.diary-content :deep(h2) {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-sand-800);
  margin-top: 1.5rem;
  margin-bottom: 0.5rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--color-sand-200);
}
.diary-content :deep(h2:first-child) { margin-top: 0; }
.diary-content :deep(h3) {
  font-size: 1.1rem;
  font-weight: 500;
  color: var(--color-sand-700);
  margin-top: 1rem;
  margin-bottom: 0.375rem;
}
.diary-content :deep(p) {
  margin-bottom: 0.75rem;
  line-height: 1.7;
  color: var(--color-sand-800);
}
.diary-content :deep(strong) { font-weight: 600; }
.diary-content :deep(ul),
.diary-content :deep(ol) { margin-bottom: 0.75rem; padding-left: 1.5rem; }
.diary-content :deep(li) { margin-bottom: 0.25rem; line-height: 1.6; }
.diary-content :deep(hr) {
  border: none;
  border-top: 1px solid var(--color-sand-200);
  margin: 1.25rem 0;
}
/* keep a floated figure contained to its section */
.diary-content :deep(h2),
.diary-content :deep(h3) { clear: both; }
</style>
