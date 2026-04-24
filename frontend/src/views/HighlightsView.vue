<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getHighlights,
  getHighlightCategories,
  deleteHighlight,
  createCategory,
  updateCategory,
  deleteCategory,
} from '../api'
import { useEvents } from '../composables/useEvents'

const router = useRouter()

interface HighlightItem {
  id: string
  title: string
  category: string
  content: string
  source_date?: string
  created_at: string
}

interface Category {
  name: string
  description: string
  prompt: string
  icon: string
  is_system: boolean
  enabled: boolean
}

const highlights = ref<HighlightItem[]>([])
const categories = ref<Category[]>([])
const selectedCategory = ref<string | null>(null)
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const perPage = 20

const showSettings = ref(false)
const editingCategory = ref<string | null>(null)
const editForm = ref({ description: '', prompt: '', icon: '' })
const showNewForm = ref(false)
const newForm = ref({ name: '', description: '', prompt: '', icon: '' })
const savingCategory = ref(false)

const totalPages = computed(() => Math.ceil(total.value / perPage))

const categoryIcons = computed(() => {
  const map: Record<string, string> = {}
  for (const cat of categories.value) {
    map[cat.name] = cat.icon
  }
  return map
})

async function loadHighlights() {
  loading.value = true
  try {
    const params: any = { page: page.value, per_page: perPage }
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
  return categoryIcons.value[category] || '🏷️'
}

function formatDate(iso: string) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('uk-UA', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

function goToEntry(date: string) {
  router.push({ name: 'diary-date', params: { date } })
}

async function removeHighlight(id: string) {
  try {
    await deleteHighlight(id)
    highlights.value = highlights.value.filter(h => h.id !== id)
    total.value--
  } catch {}
}

function goPage(p: number) {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  loadHighlights()
}

function startEditCategory(cat: Category) {
  editingCategory.value = cat.name
  editForm.value = {
    description: cat.description,
    prompt: cat.prompt || '',
    icon: cat.icon,
  }
}

function cancelEdit() {
  editingCategory.value = null
}

async function saveEditCategory(cat: Category) {
  savingCategory.value = true
  try {
    const body: any = { prompt: editForm.value.prompt }
    if (!cat.is_system) {
      body.description = editForm.value.description
      body.icon = editForm.value.icon
    }
    await updateCategory(cat.name, body)
    await loadCategories()
    editingCategory.value = null
  } catch {}
  finally {
    savingCategory.value = false
  }
}

async function toggleCategory(cat: Category) {
  try {
    await updateCategory(cat.name, { enabled: !cat.enabled })
    await loadCategories()
  } catch {}
}

function openNewForm() {
  newForm.value = { name: '', description: '', prompt: '', icon: '' }
  showNewForm.value = true
}

async function saveNewCategory() {
  if (!newForm.value.name || !newForm.value.description) return
  savingCategory.value = true
  try {
    await createCategory({
      name: newForm.value.name,
      description: newForm.value.description,
      prompt: newForm.value.prompt,
      icon: newForm.value.icon || undefined,
    })
    await loadCategories()
    showNewForm.value = false
  } catch {}
  finally {
    savingCategory.value = false
  }
}

async function removeCategory(name: string) {
  if (!confirm('Видалити цю категорію?')) return
  try {
    await deleteCategory(name)
    await loadCategories()
    if (selectedCategory.value === name) {
      selectedCategory.value = null
      loadHighlights()
    }
  } catch {}
}

useEvents({
  'bake:complete': () => {
    loadCategories()
    loadHighlights()
  },
})

onMounted(async () => {
  await Promise.all([loadCategories(), loadHighlights()])
})
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-medium text-sand-800">Хайлайти</h1>
      <button
        @click="showSettings = !showSettings"
        class="px-3 py-1.5 rounded-md text-sm border border-sand-200 text-sand-600 hover:bg-sand-100 transition-colors"
      >
        <span class="hidden sm:inline">⚙️ Налаштування</span>
        <span class="sm:hidden">⚙️</span>
      </button>
    </div>

    <!-- Category Settings Panel -->
    <div v-if="showSettings" class="bg-white rounded-xl border border-sand-200 p-4 sm:p-6 mb-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-base font-medium text-sand-800">Категорії хайлайтів</h2>
        <button
          @click="openNewForm"
          class="px-3 py-1.5 rounded-md text-sm bg-accent text-white hover:bg-accent-hover transition-colors"
        >
          + Нова категорія
        </button>
      </div>
      <p class="text-sm text-sand-500 mb-4">
        Налаштуйте, які хайлайти витягувати з ваших записів. Промпт описує AI, що шукати.
      </p>

      <!-- New category form -->
      <div v-if="showNewForm" class="border border-accent/30 rounded-lg p-4 mb-4 bg-sand-50">
        <div class="grid gap-3">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              v-model="newForm.name"
              placeholder="Назва (англ., напр. health)"
              class="w-full px-3 py-2 text-sm border border-sand-200 rounded-md focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
            <input
              v-model="newForm.icon"
              placeholder="Іконка (емодзі, напр. 🏥)"
              class="w-full px-3 py-2 text-sm border border-sand-200 rounded-md focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
          </div>
          <input
            v-model="newForm.description"
            placeholder="Опис категорії"
            class="w-full px-3 py-2 text-sm border border-sand-200 rounded-md focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
          <textarea
            v-model="newForm.prompt"
            placeholder="Промпт для AI — що шукати у записах (напр. спостереження про здоров'я, спорт, самопочуття, фізичні відчуття)"
            rows="2"
            class="w-full px-3 py-2 text-sm border border-sand-200 rounded-md resize-y focus:outline-none focus:ring-2 focus:ring-accent/30"
          ></textarea>
          <div class="flex gap-2">
            <button
              @click="saveNewCategory"
              :disabled="savingCategory || !newForm.name || !newForm.description"
              class="px-4 py-2 text-sm bg-accent text-white rounded-md hover:bg-accent-hover disabled:opacity-40 transition-colors"
            >
              Створити
            </button>
            <button
              @click="showNewForm = false"
              class="px-4 py-2 text-sm text-sand-600 border border-sand-200 rounded-md hover:bg-sand-100 transition-colors"
            >
              Скасувати
            </button>
          </div>
        </div>
      </div>

      <!-- Category list -->
      <div class="space-y-3">
        <div
          v-for="cat in categories"
          :key="cat.name"
          class="border border-sand-200 rounded-lg p-3 sm:p-4 transition-colors"
          :class="cat.enabled ? 'bg-white' : 'bg-sand-50 opacity-60'"
        >
          <!-- View mode -->
          <div v-if="editingCategory !== cat.name">
            <div class="flex items-start justify-between gap-2">
              <div class="flex items-center gap-2 min-w-0">
                <span class="text-lg">{{ cat.icon }}</span>
                <div>
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-medium text-sm text-sand-800">{{ cat.name }}</span>
                    <span v-if="cat.is_system" class="text-xs px-1.5 py-0.5 rounded bg-sand-100 text-sand-400">системна</span>
                  </div>
                  <p class="text-xs text-sand-500 mt-0.5">{{ cat.description }}</p>
                </div>
              </div>
              <div class="flex items-center gap-1 shrink-0">
                <button
                  @click="toggleCategory(cat)"
                  class="w-8 h-8 rounded-md text-sm flex items-center justify-center transition-colors"
                  :class="cat.enabled ? 'text-green-600 hover:bg-green-50' : 'text-sand-300 hover:bg-sand-100'"
                  :title="cat.enabled ? 'Увімкнено' : 'Вимкнено'"
                >
                  {{ cat.enabled ? '✓' : '○' }}
                </button>
                <button
                  @click="startEditCategory(cat)"
                  class="w-8 h-8 rounded-md text-sm text-sand-400 hover:text-sand-600 hover:bg-sand-100 flex items-center justify-center transition-colors"
                >
                  ✏️
                </button>
                <button
                  v-if="!cat.is_system"
                  @click="removeCategory(cat.name)"
                  class="w-8 h-8 rounded-md text-sm text-sand-300 hover:text-red-400 hover:bg-red-50 flex items-center justify-center transition-colors"
                >
                  🗑️
                </button>
              </div>
            </div>
            <p v-if="cat.prompt" class="text-xs text-sand-400 mt-2 pl-8 italic">
              Промпт: {{ cat.prompt }}
            </p>
          </div>

          <!-- Edit mode -->
          <div v-else class="space-y-3">
            <div class="flex items-center gap-2">
              <span class="text-lg">{{ cat.icon }}</span>
              <span class="font-medium text-sm text-sand-800">{{ cat.name }}</span>
              <span v-if="cat.is_system" class="text-xs px-1.5 py-0.5 rounded bg-sand-100 text-sand-400">системна</span>
            </div>
            <div v-if="!cat.is_system" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input
                v-model="editForm.description"
                placeholder="Опис"
                class="w-full px-3 py-2 text-sm border border-sand-200 rounded-md focus:outline-none focus:ring-2 focus:ring-accent/30"
              />
              <input
                v-model="editForm.icon"
                placeholder="Іконка"
                class="w-full px-3 py-2 text-sm border border-sand-200 rounded-md focus:outline-none focus:ring-2 focus:ring-accent/30"
              />
            </div>
            <textarea
              v-model="editForm.prompt"
              placeholder="Промпт для AI — що шукати у записах"
              rows="2"
              class="w-full px-3 py-2 text-sm border border-sand-200 rounded-md resize-y focus:outline-none focus:ring-2 focus:ring-accent/30"
            ></textarea>
            <div class="flex gap-2">
              <button
                @click="saveEditCategory(cat)"
                :disabled="savingCategory"
                class="px-4 py-1.5 text-sm bg-accent text-white rounded-md hover:bg-accent-hover disabled:opacity-40 transition-colors"
              >
                Зберегти
              </button>
              <button
                @click="cancelEdit"
                class="px-4 py-1.5 text-sm text-sand-600 border border-sand-200 rounded-md hover:bg-sand-100 transition-colors"
              >
                Скасувати
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

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
        v-for="cat in categories.filter(c => c.enabled)"
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

    <!-- Highlights list -->
    <div v-else class="space-y-3">
      <div
        v-for="h in highlights"
        :key="h.id"
        class="bg-white rounded-xl border border-sand-200 p-3 sm:p-5"
      >
        <div class="flex items-start gap-3">
          <span class="text-xl mt-0.5">{{ getIcon(h.category) }}</span>
          <div class="flex-1 min-w-0">
            <div class="flex items-start sm:items-center gap-1.5 sm:gap-2 mb-1 flex-wrap">
              <h3 class="font-medium text-sand-800 text-sm sm:text-base">{{ h.title }}</h3>
              <span class="text-xs px-2 py-0.5 rounded-full bg-sand-100 text-sand-500">
                {{ h.category }}
              </span>
            </div>
            <p class="text-sm text-sand-600">{{ h.content }}</p>
            <div class="flex items-center justify-between mt-2 sm:mt-3 gap-2">
              <button
                v-if="h.source_date"
                @click="goToEntry(h.source_date)"
                class="text-xs text-sand-400 hover:text-accent transition-colors"
              >
                з запису від {{ formatDate(h.source_date) }}
              </button>
              <span v-else></span>
              <button
                @click="removeHighlight(h.id)"
                class="text-xs text-sand-300 hover:text-red-400 transition-colors"
              >
                Видалити
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 mt-6">
      <button
        @click="goPage(page - 1)"
        :disabled="page <= 1"
        class="px-3 py-1.5 rounded-md text-sm border border-sand-200 disabled:opacity-30 transition-colors"
        :class="page > 1 ? 'text-sand-700 hover:bg-sand-100' : 'text-sand-400'"
      >
        ←
      </button>
      <span class="text-sm text-sand-600 px-2">
        {{ page }} / {{ totalPages }}
      </span>
      <button
        @click="goPage(page + 1)"
        :disabled="page >= totalPages"
        class="px-3 py-1.5 rounded-md text-sm border border-sand-200 disabled:opacity-30 transition-colors"
        :class="page < totalPages ? 'text-sand-700 hover:bg-sand-100' : 'text-sand-400'"
      >
        →
      </button>
    </div>
  </div>
</template>
