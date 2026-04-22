<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getBuffer, updateMessage, deleteMessage, bake } from '../api'

interface RawMsg {
  _id: string
  source_type: string
  content: string
  classified_date: string
  created_at: string
}

interface AudioJob {
  _id: string
  duration: number
  status: string
}

const messages = ref<RawMsg[]>([])
const processingAudio = ref<AudioJob[]>([])
const canBake = ref(false)
const loading = ref(true)
const baking = ref(false)
const bakeResult = ref<any>(null)
const editingId = ref<string | null>(null)
const editContent = ref('')

async function loadBuffer() {
  loading.value = true
  try {
    const { data } = await getBuffer()
    messages.value = data.messages
    processingAudio.value = data.processing_audio
    canBake.value = data.can_bake
  } catch {
    messages.value = []
  } finally {
    loading.value = false
  }
}

function startEdit(msg: RawMsg) {
  editingId.value = msg._id
  editContent.value = msg.content
}

async function saveEdit(id: string) {
  try {
    await updateMessage(id, { content: editContent.value })
    editingId.value = null
    await loadBuffer()
  } catch {}
}

function cancelEdit() {
  editingId.value = null
}

async function remove(id: string) {
  if (!confirm('Видалити повідомлення?')) return
  try {
    await deleteMessage(id)
    await loadBuffer()
  } catch {}
}

async function doBake() {
  baking.value = true
  bakeResult.value = null
  try {
    const { data } = await bake()
    bakeResult.value = data
    await loadBuffer()
  } catch (err: any) {
    if (err.response?.status === 409) {
      alert(err.response.data.detail)
    } else if (err.response?.status === 422) {
      alert(err.response.data.detail)
    }
  } finally {
    baking.value = false
  }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('uk-UA', { day: 'numeric', month: 'short' })
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' })
}

onMounted(loadBuffer)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-medium text-sand-800">Буфер повідомлень</h1>
      <button
        @click="doBake"
        :disabled="!canBake || messages.length === 0 || baking"
        class="px-4 py-2 rounded-lg text-sm font-medium text-white bg-accent disabled:opacity-40"
        :class="{ 'bg-accent-hover:hover': canBake && messages.length > 0 }"
      >
        {{ baking ? 'Запікаю...' : `🔥 Запікти (${messages.length})` }}
      </button>
    </div>

    <!-- Processing audio warning -->
    <div v-if="processingAudio.length > 0" class="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
      <div class="flex items-center gap-2">
        <div class="w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-sm text-amber-800">
          {{ processingAudio.length }} голосових повідомлень в процесі транскрибації.
          Запікання заблоковано до завершення.
        </p>
      </div>
    </div>

    <!-- Bake result -->
    <div v-if="bakeResult" class="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
      <p class="text-sm text-green-800">
        ✅ Створено {{ bakeResult.entries_created }} запис(ів)!
        <router-link
          v-if="bakeResult.entries?.[0]"
          :to="`/diary/${bakeResult.entries[0].date}`"
          class="text-accent hover:underline ml-1"
        >
          Переглянути →
        </router-link>
      </p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block w-6 h-6 border-2 border-sand-300 border-t-accent rounded-full animate-spin"></div>
    </div>

    <!-- Empty buffer -->
    <div v-else-if="messages.length === 0 && processingAudio.length === 0" class="text-center py-12">
      <p class="text-sand-500">Буфер порожній</p>
      <p class="text-sand-400 text-sm mt-1">Надсилай повідомлення в Telegram-бот</p>
    </div>

    <!-- Messages list -->
    <div v-else class="space-y-3">
      <div
        v-for="msg in messages"
        :key="msg._id"
        class="bg-white rounded-xl border border-sand-200 p-4"
      >
        <div class="flex items-start justify-between">
          <div class="flex items-center gap-2 text-sm text-sand-500 mb-2">
            <span>{{ msg.source_type === 'voice' ? '🎙️' : '✏️' }}</span>
            <span>{{ formatTime(msg.created_at) }}</span>
            <span class="px-2 py-0.5 rounded-full bg-sand-100 text-xs">
              {{ formatDate(msg.classified_date) }}
            </span>
          </div>
          <div class="flex gap-1">
            <button
              v-if="editingId !== msg._id"
              @click="startEdit(msg)"
              class="text-sand-400 hover:text-sand-600 text-sm px-2"
            >
              ✏️
            </button>
            <button
              @click="remove(msg._id)"
              class="text-sand-400 hover:text-red-500 text-sm px-2"
            >
              🗑️
            </button>
          </div>
        </div>

        <!-- Edit mode -->
        <div v-if="editingId === msg._id">
          <textarea
            v-model="editContent"
            class="w-full border border-sand-200 rounded-lg p-3 text-sm text-sand-800 resize-none focus:outline-none focus:ring-2 focus:ring-accent/30"
            rows="3"
          ></textarea>
          <div class="flex gap-2 mt-2">
            <button
              @click="saveEdit(msg._id)"
              class="px-3 py-1 text-sm bg-accent text-white rounded-md"
            >
              Зберегти
            </button>
            <button
              @click="cancelEdit"
              class="px-3 py-1 text-sm text-sand-600 border border-sand-200 rounded-md"
            >
              Скасувати
            </button>
          </div>
        </div>

        <!-- Display mode -->
        <p v-else class="text-sand-800 text-sm">{{ msg.content }}</p>
      </div>
    </div>
  </div>
</template>
