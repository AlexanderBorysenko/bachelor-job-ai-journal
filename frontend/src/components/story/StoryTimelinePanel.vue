<script setup lang="ts">
import { ref, computed } from 'vue'
import StoryTimeline from './StoryTimeline.vue'
import type { TimelineGroup } from '../../composables/useStoryPoints'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ groups: TimelineGroup[]; activeDate: string | null }>()
const emit = defineEmits<{ (e: 'navigate', date: string): void }>()
const { t } = useI18n()

const open = ref(false)
const count = computed(() => props.groups.length)

function onNavigate(date: string) {
  emit('navigate', date)
  open.value = false
}
</script>

<template>
  <div>
    <!-- Toggle -->
    <button
      class="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm border border-sand-200 text-sand-600 hover:bg-sand-100"
      @click="open = !open"
    >
      <span>▥</span>
      <span>{{ t('storyPoints.toggle', { count }) }}</span>
      <span class="text-xs">{{ open ? '▲' : '▼' }}</span>
    </button>

    <!-- Desktop: left flyout overlay -->
    <transition name="sp-fade">
      <div
        v-if="open"
        class="hidden sm:block fixed inset-0 z-40 bg-sand-900/10"
        @click.self="open = false"
      >
        <div class="absolute left-0 top-0 h-full w-96 max-w-[85vw] bg-white border-r border-sand-200 shadow-lg p-4 flex flex-col">
          <div class="flex items-center justify-between mb-3 shrink-0">
            <h2 class="text-sm font-semibold text-sand-700">{{ t('storyPoints.timelineTitle') }}</h2>
            <button class="text-sand-400 hover:text-sand-700" @click="open = false" aria-label="close">✕</button>
          </div>
          <p v-if="!count" class="text-sm text-sand-400">{{ t('storyPoints.empty') }}</p>
          <StoryTimeline v-else class="flex-1 min-h-0" :groups="groups" :active-date="activeDate" @navigate="onNavigate" />
        </div>
      </div>
    </transition>

    <!-- Mobile: inline collapsible, height-capped (rail caps its own height) -->
    <div v-if="open" class="sm:hidden mt-2 border border-sand-200 rounded-lg p-3 flex flex-col max-h-[60vh]">
      <p v-if="!count" class="text-sm text-sand-400">{{ t('storyPoints.empty') }}</p>
      <StoryTimeline v-else class="flex-1 min-h-0" :groups="groups" :active-date="activeDate" @navigate="onNavigate" />
    </div>
  </div>
</template>

<style scoped>
.sp-fade-enter-active,
.sp-fade-leave-active { transition: opacity 0.15s ease; }
.sp-fade-enter-from,
.sp-fade-leave-to { opacity: 0; }
</style>
