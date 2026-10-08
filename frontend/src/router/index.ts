import { createRouter, createWebHistory } from 'vue-router'
import DiscoverView from '@/views/DiscoverView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'discover', component: DiscoverView },
    { path: '/library', name: 'library', component: () => import('@/views/LibraryView.vue') },
    { path: '/research', name: 'research', component: () => import('@/views/ResearchView.vue') },
  ],
})

export default router
