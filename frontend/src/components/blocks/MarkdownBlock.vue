<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{ block: any; media?: Record<string, any> }>()

const html = computed(() => {
  const renderer = new marked.Renderer()
  renderer.heading = function ({ tokens, depth }) {
    const text = this.parser.parseInline(tokens)
    const plain = text.replace(/<[^>]*>/g, '')
    const id = plain
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s-]/gu, '')
      .replace(/\s+/g, '-')
    return `<h${depth} id="${id}">${text}</h${depth}>`
  }
  return marked(props.block?.text || '', { renderer }) as string
})
</script>

<template>
  <div v-html="html"></div>
</template>
