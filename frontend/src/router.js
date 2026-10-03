import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/catalog', name: 'catalog', component: () => import('./views/CatalogView.vue') },
    { path: '/product/:id', name: 'product', component: () => import('./views/ProductView.vue') },
    { path: '/cart', name: 'cart', component: () => import('./views/CartView.vue') },
    { path: '/agent', name: 'agent', component: () => import('./views/AgentView.vue') },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
