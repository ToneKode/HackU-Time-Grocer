<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { cartCount } from '../../stores/shop.js'
import {
  Home01Icon, GridViewIcon, ShoppingCart01Icon, AiMagicIcon, Search01Icon, Location01Icon, ShoppingBasket01Icon,
} from '@hugeicons/core-free-icons'
import Icon from './Icon.vue'

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
  { to: '/', label: 'Home', icon: Home01Icon },
  { to: '/catalog', label: 'Catalog', icon: GridViewIcon },
  { to: '/cart', label: 'Cart', icon: ShoppingCart01Icon, badge: true },
  { to: '/agent', label: 'Agent', icon: AiMagicIcon },
]
</script>

<template>
  <header class="site-header">
    <div class="site-header-inner">
      <RouterLink to="/" class="logo">
        <span class="logo-mark"><Icon :icon="ShoppingBasket01Icon" :size="24" :stroke-width="2" /></span>
        <span>grocer</span>
      </RouterLink>

      <form class="search" role="search" @submit.prevent="search">
        <span class="search-icon"><Icon :icon="Search01Icon" :size="18" /></span>
        <input v-model="query" type="search" placeholder="Search for low prices…" aria-label="Search products" />
      </form>

      <nav class="nav">
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="nav-link">
          <span class="nav-icon">
            <Icon :icon="item.icon" />
            <span v-if="item.badge && cartCount" class="nav-badge">{{ cartCount }}</span>
          </span>
          <span class="nav-label">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <span class="location"><Icon :icon="Location01Icon" :size="16" /> Hong Kong</span>
    </div>
  </header>
</template>
