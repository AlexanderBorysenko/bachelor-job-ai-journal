<script setup lang="ts">
defineProps<{
  src: string | null
  kind: string
}>()
</script>

<template>
  <img v-if="src" :src="src" class="w-full h-full object-cover" />
  <span v-else class="text-2xl">{{ kind === 'photo' ? '🖼️' : '🎬' }}</span>
</template>
