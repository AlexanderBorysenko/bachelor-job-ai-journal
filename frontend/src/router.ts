import { createRouter, createWebHistory } from 'vue-router'

import LoginView from './views/LoginView.vue'
import DiaryView from './views/DiaryView.vue'
import BufferView from './views/BufferView.vue'
import HighlightsView from './views/HighlightsView.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView },
  { path: '/', name: 'diary', component: DiaryView, meta: { requiresAuth: true } },
  { path: '/diary/:date?', name: 'diary-date', component: DiaryView, meta: { requiresAuth: true } },
  { path: '/buffer', name: 'buffer', component: BufferView, meta: { requiresAuth: true } },
  { path: '/highlights', name: 'highlights', component: HighlightsView, meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !localStorage.getItem('access_token')) {
    return { name: 'login' }
  }
})

export default router
