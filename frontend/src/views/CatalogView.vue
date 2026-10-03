<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { products, categories, categoryById } from '../data/catalog.js'
import { bestOffer, discountPct } from '../lib/pricing.js'
import ProductCard from '../components/shop/ProductCard.vue'
import MerchantChips from '../components/shop/MerchantChips.vue'

const route = useRoute()
const router = useRouter()

const merchant = ref(null)
const sort = ref('popular')

const category = computed(() => route.query.category ?? null)
const q = computed(() => (route.query.q ?? '').toString().trim().toLowerCase())

const countByCategory = Object.fromEntries(
  categories.map((c) => [c.id, products.filter((p) => p.category === c.id).length]),
)

function setCategory(id) {
  router.replace({ query: { ...route.query, category: id ?? undefined } })
}

function clearSearch() {
  router.replace({ query: { ...route.query, q: undefined } })
}

const results = computed(() => {
  const allowed = merchant.value ? [merchant.value] : null
  const list = products.filter(
    (p) =>
      (!category.value || p.category === category.value) &&
      (!q.value || p.name.toLowerCase().includes(q.value)) &&
      bestOffer(p, allowed),
  )
  const price = (p) => bestOffer(p, allowed).price
  if (sort.value === 'cheap') list.sort((a, b) => price(a) - price(b))
  if (sort.value === 'expensive') list.sort((a, b) => price(b) - price(a))
  if (sort.value === 'discount') list.sort((a, b) => discountPct(bestOffer(b, allowed)) - discountPct(bestOffer(a, allowed)))
  return list
})

const title = computed(() => categoryById[category.value]?.label ?? 'All products')
</script>

<template>
  <main class="page catalog">
    <aside class="sidebar">
      <h2 class="sidebar-title">Categories</h2>
      <button type="button" class="side-item" :class="{ on: !category }" @click="setCategory(null)">
        <span>🛍️ All products</span><span class="muted">{{ products.length }}</span>
      </button>
      <button
        v-for="c in categories"
        :key="c.id"
        type="button"
        class="side-item"
        :class="{ on: category === c.id }"
        @click="setCategory(c.id)"
      >
        <span>{{ c.emoji }} {{ c.label }}</span><span class="muted">{{ countByCategory[c.id] }}</span>
      </button>
    </aside>

    <section class="catalog-main">
      <MerchantChips v-model="merchant" />

      <div class="section-head">
        <h2>{{ title }} <span class="muted">({{ results.length }})</span></h2>
        <select v-model="sort" class="sort" aria-label="Sort products">
          <option value="popular">Popular</option>
          <option value="cheap">Cheapest first</option>
          <option value="expensive">Most expensive first</option>
          <option value="discount">Biggest discount</option>
        </select>
      </div>

      <p v-if="q" class="search-note">
        Results for “{{ route.query.q }}”
        <button type="button" class="link-btn" @click="clearSearch">Clear</button>
      </p>

      <div class="product-grid">
        <ProductCard v-for="p in results" :key="p.id" :product="p" :merchant="merchant" />
      </div>

      <div v-if="!results.length" class="empty-box">
        <div class="empty-icon">🔍</div>
        <h3>Nothing found</h3>
        <p class="muted">Try another category, store or search word.</p>
      </div>
    </section>
  </main>
</template>
