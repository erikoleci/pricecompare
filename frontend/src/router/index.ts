import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
    { path: '/products/:id', name: 'product', component: () => import('@/views/ProductView.vue') },
    { path: '/compare', name: 'compare', component: () => import('@/views/CompareView.vue') },
    { path: '/deals', name: 'deals', component: () => import('@/views/DealsView.vue') },
    { path: '/search', name: 'search', component: () => import('@/views/SearchView.vue') }
  ]
})

export default router
