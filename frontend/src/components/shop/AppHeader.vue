<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { cartCount } from '../../stores/shop.js'

const route = useRoute()
const router = useRouter()
const query = ref('')

// Keep the box in sync when the catalog URL changes (?q=...)
watch(() => route.query.q, (q) => { query.value = q ?? '' }, { immediate: true })

function search() {
  const q = query.value.trim()
  router.push({ name: 'catalog', query: q ? { q } : {} })
}

const nav = [
  { to: '/', label: 'Home', icon: '⌂' },
  { to: '/catalog', label: 'Catalog', icon: '▦' },
  { to: '/cart', label: 'Cart', icon: '🛒', badge: true },
  { to: '/agent', label: 'Agent', icon: '✦' },
]
</script>

<template>
  <header class="site-header">
    <div class="site-header-inner">
      <RouterLink to="/" class="logo">
        <span class="logo-mark">🛒</span>
        <span>time-grocer</span>
      </RouterLink>

      <form class="search" role="search" @submit.prevent="search">
        <span class="search-icon" aria-hidden="true">⌕</span>
        <input v-model="query" type="search" placeholder="Search for low prices…" aria-label="Search products" />
      </form>

      <nav class="nav">
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="nav-link">
          <span class="nav-icon" aria-hidden="true">
            {{ item.icon }}
            <span v-if="item.badge && cartCount" class="nav-badge">{{ cartCount }}</span>
          </span>
          <span class="nav-label">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <span class="location">📍 Hong Kong</span>
    </div>
  </header>
</template>
