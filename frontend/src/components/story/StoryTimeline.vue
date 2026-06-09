<script setup lang="ts">
import { ref } from 'vue'
import type { TimelineGroup } from '../../composables/useStoryPoints'
import { useI18n } from 'vue-i18n'
import { bcp47, type Language } from '../../i18n'

defineProps<{ groups: TimelineGroup[]; activeDate: string | null }>()
const emit = defineEmits<{ (e: 'navigate', date: string): void }>()
const { locale } = useI18n()

const scroller = ref<HTMLElement | null>(null)
function scrollRail(delta: number) {
  scroller.value?.scrollBy({ top: delta, behavior: 'smooth' })
}
function fmt(date: string) {
  return new Date(date + 'T00:00:00').toLocaleDateString(bcp47(locale.value as Language), {
    day: 'numeric',
    month: 'short',
  })
}
</script>

<template>
  <div class="flex flex-col">
    <div ref="scroller" class="overflow-y-auto max-h-[60vh] pr-1">
      <ul class="relative border-l border-sand-200 ml-2">
        <li v-for="g in groups" :key="g.date" class="mb-4 ml-4">
          <button
            class="absolute -left-[5px] w-2.5 h-2.5 rounded-full"
            :class="g.date === activeDate ? 'bg-accent' : 'bg-sand-300'"
            @click="emit('navigate', g.date)"
            :aria-label="fmt(g.date)"
          ></button>
          <button
            class="block text-left text-sm font-medium hover:text-accent transition-colors"
            :class="g.date === activeDate ? 'text-accent' : 'text-sand-700'"
            @click="emit('navigate', g.date)"
          >
            {{ fmt(g.date) }}
          </button>
          <ul class="mt-1 space-y-0.5">
            <li v-for="p in g.points" :key="p.id" class="text-xs text-sand-500 truncate">
              {{ p.title }}
            </li>
          </ul>
        </li>
      </ul>
    </div>
    <div class="flex justify-center gap-2 mt-2">
      <button class="px-2 py-1 text-sand-500 hover:text-accent" @click="scrollRail(-120)" aria-label="up">▲</button>
      <button class="px-2 py-1 text-sand-500 hover:text-accent" @click="scrollRail(120)" aria-label="down">▼</button>
    </div>
  </div>
</template>
