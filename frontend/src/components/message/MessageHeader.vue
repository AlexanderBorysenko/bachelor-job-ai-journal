<script setup lang="ts">
import type { RawMessage } from '../../types/message'
import { formatDate, formatTime } from '../../utils/datetime'

defineProps<{ message: RawMessage; disabled: boolean; open: boolean }>()
defineEmits<{ edit: []; remove: [] }>()

function icon(sourceType: string) {
  return sourceType === 'voice' ? '🎙️' : sourceType === 'media' ? '📎' : '✏️'
}
</script>

<template>
  <div class="flex items-start justify-between">
    <div class="flex items-center gap-2 text-sm text-sand-500 mb-2">
      <span>{{ icon(message.source_type) }}</span>
      <span>{{ formatTime(message.created_at) }}</span>
      <span class="px-2 py-0.5 rounded-full bg-sand-100 text-xs">
        {{ formatDate(message.classified_date) }}
      </span>
    </div>
    <div v-if="!disabled" class="flex gap-1">
      <button
        v-if="!open"
        @click="$emit('edit')"
        class="text-sand-400 hover:text-sand-600 text-sm px-2"
      >
        ✏️
      </button>
      <button
        @click="$emit('remove')"
        class="text-sand-400 hover:text-red-500 text-sm px-2"
      >
        🗑️
      </button>
    </div>
  </div>
</template>
