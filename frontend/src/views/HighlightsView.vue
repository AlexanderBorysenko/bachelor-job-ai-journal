<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getHighlights, getHighlightCategories } from '../api'

interface HighlightItem {
  id: string
  title: string
  category: string
  content: string
  created_at: string
}

interface Category {
  name: string
  description: string
  icon: string
  is_system: boolean
}

const highlights = ref<HighlightItem[]>([])
const categories = ref<Category[]>([])
const selectedCategory = ref<string | null>(null)
const loading = ref(true)
const total = ref(0)
const page = ref(1)

const categoryIcons: Record<string, string> = {
  idea: '💡',
  story: '📖',
  mood: '🧠',
  insight: '⚡',
}

async function loadHighlights() {
  loading.value = true
  try {
    const params: any = { page: page.value, per_page: 20 }
    if (selectedCategory.value) params.category = selectedCategory.value
    const { data } = await getHighlights(params)
    highlights.value = data.items
    total.value = data.total
  } catch {
    highlights.value = []
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  try {
    const { data } = await getHighlightCategories()
    categories.value = data
  } catch {}
}

function selectCategory(name: string | null) {
  selectedCategory.value = selectedCategory.value === name ? null : name
  page.value = 1
  loadHighlights()
}

function getIcon(category: string) {
  return categoryIcons[category] || '🏷️'
}

onMounted(async () => {
  await Promise.all([loadCategories(), loadHighlights()])
})
</script>

<template>
  <div>
    <h1 class="text-xl font-medium text-sand-800 mb-6">Хайлайти</h1>

    <!-- Category filters -->
    <div class="flex flex-wrap gap-2 mb-6">
      <button
        @click="selectCategory(null)"
        class="px-3 py-1.5 rounded-full text-sm border transition-colors"
        :class="!selectedCategory
          ? 'bg-accent text-sand-50 border-accent'
          : 'text-sand-600 border-sand-200 hover:border-sand-300'"
      >
        Всі
      </button>
      <button
        v-for="cat in categories"
        :key="cat.name"
        @click="selectCategory(cat.name)"
        class="px-3 py-1.5 rounded-full text-sm border transition-colors"
        :class="selectedCategory === cat.name
          ? 'bg-accent text-sand-50 border-accent'
          : 'text-sand-600 border-sand-200 hover:border-sand-300'"
      >
        {{ cat.icon }} {{ cat.name }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block w-6 h-6 border-2 border-sand-300 border-t-accent rounded-full animate-spin"></div>
    </div>

    <!-- Empty -->
    <div v-else-if="highlights.length === 0" class="text-center py-12">
      <p class="text-sand-500">Хайлайтів поки немає</p>
      <p class="text-sand-400 text-sm mt-1">Вони з'являться автоматично після запікання записів</p>
    </div>

    <!-- Highlights grid -->
    <div v-else class="space-y-3">
      <div
        v-for="h in highlights"
        :key="h.id"
        class="bg-white rounded-xl border border-sand-200 p-5"
      >
        <div class="flex items-start gap-3">
          <span class="text-xl mt-0.5">{{ getIcon(h.category) }}</span>
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <h3 class="font-medium text-sand-800">{{ h.title }}</h3>
              <span class="text-xs px-2 py-0.5 rounded-full bg-sand-100 text-sand-500">
                {{ h.category }}
              </span>
            </div>
            <p class="text-sm text-sand-600">{{ h.content }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="total > 20" class="flex justify-center gap-2 mt-6">
      <button
        v-for="p in Math.ceil(total / 20)"
        :key="p"
        @click="page = p; loadHighlights()"
        class="w-8 h-8 rounded-md text-sm"
        :class="page === p ? 'bg-sand-800 text-white' : 'text-sand-600 hover:bg-sand-100'"
      >
        {{ p }}
      </button>
    </div>
  </div>
</template>
