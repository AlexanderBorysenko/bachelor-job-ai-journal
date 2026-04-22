<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppNav from './components/AppNav.vue'

const route = useRoute()
</script>

<template>
  <div class="min-h-screen bg-sand-50">
    <AppNav v-if="route.name !== 'login'" />
    <main class="max-w-3xl mx-auto px-4 py-8">
      <router-view />
    </main>
  </div>
</template>
