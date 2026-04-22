<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getEntryByDate, getEntries, getEntryRaw } from '../api'

const route = useRoute()
const router = useRouter()

const entry = ref<any>(null)
const prevDate = ref<string | null>(null)
const nextDate = ref<string | null>(null)
const rawMessages = ref<any[]>([])
const showRaw = ref(false)
const loading = ref(true)
const availableDates = ref<string[]>([])
const noEntry = ref(false)

async function loadEntry(date: string) {
  loading.value = true
  noEntry.value = false
  showRaw.value = false
  rawMessages.value = []

  try {
    const { data } = await getEntryByDate(date)
    entry.value = data.entry
    prevDate.value = data.prev_date
    nextDate.value = data.next_date
  } catch (err: any) {
    if (err.response?.status === 404) {
      entry.value = null
      noEntry.value = true
    }
  } finally {
    loading.value = false
  }
}

async function loadLatest() {
  loading.value = true
  try {
    const { data } = await getEntries({ page: 1, per_page: 1 })
    availableDates.value = data.available_dates || []
    if (data.items.length > 0) {
      await loadEntry(data.items[0].date)
    } else {
      entry.value = null
      noEntry.value = true
      loading.value = false
    }
  } catch {
    loading.value = false
    noEntry.value = true
  }
}

async function toggleRaw() {
  if (!showRaw.value && entry.value) {
    try {
      const { data } = await getEntryRaw(entry.value.id)
      rawMessages.value = data
    } catch {
      rawMessages.value = []
    }
  }
  showRaw.value = !showRaw.value
}

function goTo(date: string | null) {
  if (date) router.push(`/diary/${date}`)
}

function formatDate(isoDate: string) {
  const d = new Date(isoDate + 'T00:00:00')
  return d.toLocaleDateString('uk-UA', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

onMounted(() => {
  const dateParam = route.params.date as string
  if (dateParam) {
    loadEntry(dateParam)
  } else {
    loadLatest()
  }
})

watch(() => route.params.date, (newDate) => {
  if (newDate) loadEntry(newDate as string)
})
</script>

<template>
  <div>
    <!-- Loading -->
    <div v-if="loading" class="text-center py-16">
      <div class="inline-block w-6 h-6 border-2 border-sand-300 border-t-accent rounded-full animate-spin"></div>
      <p class="text-sand-500 mt-3">Завантаження...</p>
    </div>

    <!-- No entries -->
    <div v-else-if="noEntry && !entry" class="text-center py-16">
      <p class="text-sand-500 text-lg mb-2">Записів поки немає</p>
      <p class="text-sand-400">
        Надсилай повідомлення в Telegram-бот і натискай /bake
      </p>
      <router-link to="/buffer" class="inline-block mt-4 text-accent hover:underline">
        Перейти до буфера →
      </router-link>
    </div>

    <!-- Entry -->
    <div v-else-if="entry">
      <!-- Navigation -->
      <div class="flex items-center justify-between mb-6">
        <button
          @click="goTo(prevDate)"
          :disabled="!prevDate"
          class="px-3 py-1.5 rounded-md text-sm border border-sand-200 disabled:opacity-30"
          :class="prevDate ? 'text-sand-700 hover:bg-sand-100 cursor-pointer' : 'text-sand-400'"
        >
          ← Попередній
        </button>
        <h1 class="text-xl font-medium text-sand-800">
          {{ formatDate(entry.date) }}
        </h1>
        <button
          @click="goTo(nextDate)"
          :disabled="!nextDate"
          class="px-3 py-1.5 rounded-md text-sm border border-sand-200 disabled:opacity-30"
          :class="nextDate ? 'text-sand-700 hover:bg-sand-100 cursor-pointer' : 'text-sand-400'"
        >
          Наступний →
        </button>
      </div>

      <!-- Entry content -->
      <div class="bg-white rounded-xl border border-sand-200 p-6 mb-4">
        <div class="prose" v-html="renderMarkdown(entry.content)"></div>
      </div>

      <!-- Highlights -->
      <div v-if="entry.highlights?.length" class="mb-4">
        <h3 class="text-sm font-medium text-sand-600 mb-2">Хайлайти</h3>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="h in entry.highlights"
            :key="h.id"
            class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm bg-sand-100 text-sand-700"
          >
            <span v-if="h.category === 'idea'">💡</span>
            <span v-else-if="h.category === 'story'">📖</span>
            <span v-else-if="h.category === 'mood'">🧠</span>
            <span v-else-if="h.category === 'insight'">⚡</span>
            {{ h.title }}
          </span>
        </div>
      </div>

      <!-- Raw messages toggle -->
      <button
        @click="toggleRaw"
        class="text-sm text-sand-500 hover:text-sand-700"
      >
        {{ showRaw ? 'Сховати оригінали' : `Показати оригінали (${entry.source_messages_count})` }}
      </button>

      <div v-if="showRaw && rawMessages.length" class="mt-3 space-y-2">
        <div
          v-for="msg in rawMessages"
          :key="msg.id"
          class="bg-sand-100 rounded-lg p-3 text-sm"
        >
          <div class="flex items-center gap-2 text-sand-500 mb-1">
            <span>{{ msg.source_type === 'voice' ? '🎙️' : '✏️' }}</span>
            <span>{{ new Date(msg.created_at).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' }) }}</span>
          </div>
          <p class="text-sand-800">{{ msg.content }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
// Simple markdown to HTML (paragraphs and bold)
function renderMarkdown(md: string): string {
  if (!md) return ''
  return md
    .split('\n\n')
    .map(p => p.trim())
    .filter(p => p)
    .map(p => `<p>${p.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</p>`)
    .join('')
}

export default {
  methods: { renderMarkdown },
}
</script>
