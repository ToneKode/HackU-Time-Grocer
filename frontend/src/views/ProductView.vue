<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productById, products, categoryById, merchantByName } from '../data/catalog.js'
import { sortedOffers, bestOffer, discountPct } from '../lib/pricing.js'
import { productHistory, daysSinceChange, PERIODS } from '../lib/priceHistory.js'
import { money } from '../lib/format.js'
import { qtyOf, setQty, addToCart, favourites, toggleFavourite } from '../stores/shop.js'
import ProductCard from '../components/shop/ProductCard.vue'
import MerchantLogo from '../components/shop/MerchantLogo.vue'
import QtyStepper from '../components/shop/QtyStepper.vue'
import PriceChart from '../components/shop/PriceChart.vue'
import Icon from '../components/shop/Icon.vue'
import {
  ArrowLeft01Icon, Share08Icon, FavouriteIcon, PlusSignIcon, ArrowDown01Icon, ArrowUp01Icon,
  CheckmarkCircle02Icon, AlertCircleIcon, InformationCircleIcon, ChartLineData02Icon, Table01Icon,
} from '@hugeicons/core-free-icons'

const route = useRoute()
const router = useRouter()

const product = computed(() => productById[route.params.id])
const category = computed(() => categoryById[product.value?.category])
const offers = computed(() => sortedOffers(product.value))
const best = computed(() => bestOffer(product.value))
const discount = computed(() => discountPct(best.value))
const qty = computed({
  get: () => qtyOf(product.value.id),
  set: (value) => setQty(product.value.id, value),
})

// ---- Store list ----
const openStore = ref(null)
function toggleStore(name) {
  openStore.value = openStore.value === name ? null : name
}

// ---- Price history ----
const days = ref(30)
const mode = ref('min') // 'min' | 'stores'
const showTable = ref(false)
const history = computed(() => productHistory(product.value, days.value))
const stats = computed(() => history.value.stats)
const fmtDate = (t) => new Date(t).toLocaleDateString('en-HK', { day: 'numeric', month: 'short' })

const chartSeries = computed(() =>
  mode.value === 'min'
    ? [{ key: 'min', label: 'Lowest price', color: 'var(--primary)', points: history.value.minPoints }]
    : history.value.stores.map((s) => ({ key: s.merchant, label: s.merchant, color: merchantByName[s.merchant].color, points: s.points })),
)

// Verdict on today's price, with an icon + label (never colour alone).
const verdict = computed(() => {
  const s = stats.value
  if (s.current <= s.low * 1.02) return { tone: 'good', icon: CheckmarkCircle02Icon, text: `Great time to buy: today's price is at the ${days.value}-day low.` }
  if (s.current > s.avg * 1.02) return { tone: 'warn', icon: AlertCircleIcon, text: `Above the ${days.value}-day average. Waiting for a promo may be cheaper.` }
  return { tone: 'neutral', icon: InformationCircleIcon, text: `A typical price for the last ${days.value} days.` }
})

const pct = (n) => (n > 0 ? `+${n}%` : `${n}%`)

// ---- Similar products ----
const similar = computed(() =>
  products.filter((p) => p.category === product.value.category && p.id !== product.value.id).slice(0, 8),
)

// ---- Header actions ----
const shareNote = ref('')
async function share() {
  const url = window.location.href
  try {
    if (navigator.share) await navigator.share({ title: product.value.name, url })
    else {
      await navigator.clipboard.writeText(url)
      shareNote.value = 'Link copied'
      setTimeout(() => (shareNote.value = ''), 2000)
    }
  } catch {
    // Share sheet closed or clipboard blocked: nothing to do.
  }
}
function goBack() {
  if (window.history.state?.back) router.back()
  else router.push('/')
}
</script>

<template>
  <main v-if="product" class="page product-page">
    <div class="top-actions">
      <button type="button" class="link-btn plain" @click="goBack">
        <Icon :icon="ArrowLeft01Icon" :size="18" /> Back
      </button>
      <button type="button" class="link-btn plain" @click="share">
        <Icon :icon="Share08Icon" :size="18" /> {{ shareNote || 'Share' }}
      </button>
    </div>

    <!-- ---------- Main card ---------- -->
    <section class="pd-main">
      <div class="product-image pd-image" :style="{ background: category?.tint }">
        <span v-if="discount" class="discount">-{{ discount }}%</span>
        <button
          type="button"
          class="fav"
          :class="{ on: favourites.ids[product.id] }"
          :aria-label="favourites.ids[product.id] ? 'Remove from favourites' : 'Add to favourites'"
          @click="toggleFavourite(product.id)"
        >
          <Icon :icon="FavouriteIcon" :size="18" />
        </button>
        <span class="product-emoji pd-emoji" aria-hidden="true">{{ product.emoji }}</span>
        <span class="size">{{ product.size }}</span>
      </div>

      <div class="pd-info">
        <RouterLink v-if="category" :to="{ name: 'catalog', query: { category: category.id } }" class="pd-crumb">
          <Icon :icon="category.icon" :size="16" /> {{ category.label }}
        </RouterLink>
        <h1 class="pd-title">{{ product.name }}</h1>
        <p v-if="best" class="muted small">
          Cheapest at <strong>{{ best.merchant }}</strong> · {{ stats.storeCount }} {{ stats.storeCount === 1 ? 'store has' : 'stores have' }} it in stock
        </p>

        <div class="pd-price">
          <template v-if="best">
            <s v-if="best.oldPrice" class="old-price">{{ money(best.oldPrice) }}</s>
            <span class="price pd-price-big">{{ money(best.price) }}</span>
          </template>
          <span v-else class="muted">Not available right now</span>
        </div>

        <QtyStepper v-if="qty" v-model="qty" class="pd-action" />
        <button v-else type="button" class="add-btn pd-action" :disabled="!best" @click="addToCart(product.id)">
          <Icon :icon="PlusSignIcon" :size="16" :stroke-width="2.2" /> Add to cart
        </button>
      </div>
    </section>

    <!-- ---------- Prices by store ---------- -->
    <section class="pd-card">
      <h2 class="pd-h2">Prices by store</h2>
      <ul class="store-rows">
        <li v-for="offer in offers" :key="offer.merchant" :class="{ out: offer.inStock === false }">
          <button
            type="button"
            class="store-row"
            :aria-expanded="openStore === offer.merchant"
            @click="toggleStore(offer.merchant)"
          >
            <MerchantLogo :name="offer.merchant" :size="26" />
            <span class="store-row-name">{{ offer.merchant }}</span>
            <span v-if="offer.inStock === false" class="out-tag">Out of stock</span>
            <span v-else-if="best && offer.merchant === best.merchant" class="best-tag">Best price</span>
            <span class="store-row-price">
              <s v-if="offer.oldPrice" class="old-price">{{ money(offer.oldPrice) }}</s>
              {{ money(offer.price) }}
            </span>
            <Icon :icon="openStore === offer.merchant ? ArrowUp01Icon : ArrowDown01Icon" :size="16" class="muted" />
          </button>
          <dl v-if="openStore === offer.merchant" class="store-detail">
            <div>
              <dt>Discount</dt>
              <dd>{{ discountPct(offer) ? `-${discountPct(offer)}% off ${money(offer.oldPrice)}` : 'None' }}</dd>
            </div>
            <div>
              <dt>vs cheapest</dt>
              <dd>{{ best && offer.price > best.price ? '+' + money(offer.price - best.price) : 'Cheapest' }}</dd>
            </div>
            <div>
              <dt>Price unchanged for</dt>
              <dd>{{ daysSinceChange(product, offer) }} days</dd>
            </div>
            <div>
              <dt>{{ days }}-day low here</dt>
              <dd>{{ money(history.stores.find((s) => s.merchant === offer.merchant).low) }}</dd>
            </div>
          </dl>
        </li>
      </ul>
    </section>

    <!-- ---------- Price stats + history ---------- -->
    <section class="pd-card">
      <div class="pd-history-head">
        <div>
          <h2 class="pd-h2">Price history</h2>
          <p class="muted small">{{ fmtDate(history.start) }} – {{ fmtDate(history.end) }} · demo data</p>
        </div>
        <div class="segmented" role="group" aria-label="Period">
          <button
            v-for="d in PERIODS"
            :key="d"
            type="button"
            :class="{ on: days === d }"
            :aria-pressed="days === d"
            @click="days = d"
          >{{ d }} days</button>
        </div>
      </div>

      <div class="stat-tiles">
        <div class="stat-tile">
          <span class="stat-label">Today's best</span>
          <strong class="stat-value">{{ money(stats.current) }}</strong>
          <span class="stat-sub">{{ pct(stats.vsAvgPct) }} vs average</span>
        </div>
        <div class="stat-tile">
          <span class="stat-label">{{ days }}-day low</span>
          <strong class="stat-value">{{ money(stats.low) }}</strong>
        </div>
        <div class="stat-tile">
          <span class="stat-label">{{ days }}-day high</span>
          <strong class="stat-value">{{ money(stats.high) }}</strong>
        </div>
        <div class="stat-tile">
          <span class="stat-label">Average</span>
          <strong class="stat-value">{{ money(stats.avg) }}</strong>
        </div>
        <div class="stat-tile">
          <span class="stat-label">Store price gap</span>
          <strong class="stat-value">{{ money(stats.spread) }}</strong>
          <span class="stat-sub">cheapest vs priciest today</span>
        </div>
      </div>

      <p class="verdict" :class="`verdict-${verdict.tone}`">
        <Icon :icon="verdict.icon" :size="18" /> {{ verdict.text }}
      </p>

      <div class="pd-chart-controls">
        <div class="segmented" role="group" aria-label="Chart mode">
          <button type="button" :class="{ on: mode === 'min' }" :aria-pressed="mode === 'min'" @click="mode = 'min'">Lowest price</button>
          <button type="button" :class="{ on: mode === 'stores' }" :aria-pressed="mode === 'stores'" @click="mode = 'stores'">By store</button>
        </div>
        <button type="button" class="link-btn" @click="showTable = !showTable">
          <Icon :icon="showTable ? ChartLineData02Icon : Table01Icon" :size="16" />
          {{ showTable ? 'Show chart' : 'Show table' }}
        </button>
      </div>

      <template v-if="!showTable">
        <PriceChart :series="chartSeries" :annotate="mode === 'min'" />
        <ul v-if="mode === 'stores'" class="chart-legend">
          <li v-for="s in history.stores" :key="s.merchant">
            <span class="legend-key" :style="{ background: merchantByName[s.merchant].color }" />
            {{ s.merchant }}
            <strong>{{ money(s.current) }}</strong>
            <span :class="s.changePct < 0 ? 'down' : s.changePct > 0 ? 'up' : 'muted'">{{ pct(s.changePct) }}</span>
          </li>
        </ul>
      </template>

      <div v-else class="table-scroll">
        <table class="price-table">
          <thead>
            <tr><th>Store</th><th>Today</th><th>Low</th><th>High</th><th>Average</th><th>Change</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in history.stores" :key="s.merchant">
              <td><span class="legend-key" :style="{ background: merchantByName[s.merchant].color }" /> {{ s.merchant }}</td>
              <td>{{ money(s.current) }}</td>
              <td>{{ money(s.low) }}</td>
              <td>{{ money(s.high) }}</td>
              <td>{{ money(s.avg) }}</td>
              <td>{{ pct(s.changePct) }}</td>
            </tr>
            <tr class="table-total">
              <td>Lowest across stores</td>
              <td>{{ money(stats.current) }}</td>
              <td>{{ money(stats.low) }}</td>
              <td>{{ money(stats.high) }}</td>
              <td>{{ money(stats.avg) }}</td>
              <td>{{ pct(stats.changePct) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ---------- Similar products ---------- -->
    <section v-if="similar.length">
      <div class="section-head">
        <h2>Similar products</h2>
        <span class="muted small">{{ similar.length }} {{ similar.length === 1 ? 'item' : 'items' }}</span>
      </div>
      <div class="product-grid">
        <ProductCard v-for="p in similar" :key="p.id" :product="p" />
      </div>
    </section>
  </main>

  <main v-else class="page">
    <div class="empty-box">
      <h3>Product not found</h3>
      <RouterLink to="/catalog" class="btn-primary">Back to catalog</RouterLink>
    </div>
  </main>
</template>
