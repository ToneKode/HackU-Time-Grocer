<script setup>
import { ref, computed } from 'vue'
import { products, categories, merchants } from '../data/catalog.js'
import { bestOffer, discountPct } from '../lib/pricing.js'
import ProductCard from '../components/shop/ProductCard.vue'
import MerchantChips from '../components/shop/MerchantChips.vue'

const merchant = ref(null)

// Deals = products whose best price (for the chosen store) is discounted, biggest first.
const deals = computed(() => {
  const allowed = merchant.value ? [merchant.value] : null
  return products
    .map((product) => ({ product, pct: discountPct(bestOffer(product, allowed)) }))
    .filter((d) => d.pct > 0)
    .sort((a, b) => b.pct - a.pct)
    .map((d) => d.product)
})
</script>

<template>
  <main class="page">
    <section class="hero">
      <div class="hero-text">
        <h1>Compare the whole basket <span class="accent">and let the agent check out</span></h1>
        <p>
          Build your list once. Time-Grocer finds the cheapest store for every item across
          {{ merchants.map((m) => m.name).join(', ') }}.
        </p>
        <div class="hero-actions">
          <RouterLink to="/catalog" class="btn-primary">Browse catalog</RouterLink>
          <RouterLink to="/cart" class="btn-soft">Open my cart</RouterLink>
        </div>
      </div>
      <div class="hero-art" aria-hidden="true">
        <span v-for="e in ['🥦', '🥛', '🍞', '🍎', '🧻', '🥚']" :key="e">{{ e }}</span>
      </div>
    </section>

    <nav class="category-row" aria-label="Categories">
      <RouterLink
        v-for="c in categories"
        :key="c.id"
        :to="{ name: 'catalog', query: { category: c.id } }"
        class="category-pill"
        :style="{ background: c.tint }"
      >
        <span class="category-emoji">{{ c.emoji }}</span>{{ c.label }}
      </RouterLink>
    </nav>

    <section>
      <div class="section-head">
        <h2>⚡ Mega deals <span class="muted">({{ deals.length }})</span></h2>
      </div>
      <MerchantChips v-model="merchant" />
      <div class="product-grid">
        <ProductCard v-for="p in deals" :key="p.id" :product="p" :merchant="merchant" />
      </div>
      <p v-if="!deals.length" class="empty-note">No deals at this store right now.</p>
    </section>
  </main>
</template>
