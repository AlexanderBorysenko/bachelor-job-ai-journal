<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ block: any; media: Record<string, any> }>()

const codes = computed<string[]>(() =>
  (props.block?.images || []).filter((c: string) => {
    const m = props.media?.[c]
    return m && m.status === 'ready' && m.kind === 'photo'
  })
)
</script>

<template>
  <figure v-if="codes.length" class="diary-gallery">
    <div class="diary-gallery__grid">
      <a
        v-for="c in codes"
        :key="c"
        class="diary-gallery__item"
        :href="`/api/media/${c}`"
        target="_blank"
        rel="noopener"
      >
        <img :src="`/api/media/${c}`" loading="lazy" />
      </a>
    </div>
    <figcaption v-if="block.caption" class="diary-gallery__caption">{{ block.caption }}</figcaption>
  </figure>
</template>

<style scoped>
.diary-gallery { margin: 1rem 0; }
.diary-gallery__grid { columns: 3 200px; column-gap: 8px; }
.diary-gallery__item { display: block; break-inside: avoid; margin-bottom: 8px; }
.diary-gallery__item img { width: 100%; height: auto; border-radius: 0.5rem; display: block; }
.diary-gallery__caption {
  text-align: center;
  font-size: 0.85rem;
  color: var(--color-sand-500);
  margin-top: 0.4rem;
}
@media (max-width: 640px) {
  .diary-gallery__grid { columns: 2 140px; }
}
</style>
