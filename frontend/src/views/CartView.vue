<script setup>
import { ref, computed } from 'vue'
import { merchants } from '../data/catalog.js'
import { optimalMix, singleStoreTotals, mixSavings, sortedOffers } from '../lib/pricing.js'
import { money } from '../lib/format.js'
import { cartLines, cartCount, setQty, clearCart } from '../stores/shop.js'
import MerchantChips from '../components/shop/MerchantChips.vue'
import MerchantLogo from '../components/shop/MerchantLogo.vue'
import QtyStepper from '../components/shop/QtyStepper.vue'

const allowed = ref(merchants.map((m) => m.name))
const mode = ref('mix') // 'mix' | 'single'
const openStore = ref(null)

const mix = computed(() => optimalMix(cartLines.value, allowed.value))
const stores = computed(() => singleStoreTotals(cartLines.value, allowed.value))
const savings = computed(() => mixSavings(mix.value, stores.value))
</script>

<template>
  <main class="page cart">
    <RouterLink to="/" class="back-link">← Back to home</RouterLink>

    <div class="cart-head">
      <h1>My cart <span v-if="cartCount" class="cart-total-pill">{{ money(mix.total) }}</span></h1>
      <button v-if="cartCount" type="button" class="link-btn danger-text" @click="clearCart">Clear cart</button>
    </div>

    <div v-if="!cartCount" class="empty-box">
      <div class="empty-icon">🛒</div>
      <h3>Build a basket without overpaying</h3>
      <p class="muted">Add products and Grocer will show where each one is cheapest.</p>
      <RouterLink to="/catalog" class="btn-primary">Check prices</RouterLink>
    </div>

    <template v-else>
      <section class="panel">
        <p class="muted small">Choose the stores you want to buy from. The optimal mix only uses these.</p>
        <MerchantChips v-model="allowed" multiple />
      </section>

      <div class="tabs" role="tablist">
        <button type="button" role="tab" :aria-selected="mode === 'mix'" :class="{ on: mode === 'mix' }" @click="mode = 'mix'">
          ⚡ Optimal mix
        </button>
        <button type="button" role="tab" :aria-selected="mode === 'single'" :class="{ on: mode === 'single' }" @click="mode = 'single'">
          🏪 One store
        </button>
      </div>

      <!-- ---------- Optimal mix ---------- -->
      <template v-if="mode === 'mix'">
        <section class="summary">
          <h2>⚡ Optimal mix: {{ money(mix.total) }}</h2>
          <p class="muted small">Each item is bought at the cheapest of your selected stores.</p>
          <p v-if="savings && savings.amount > 0" class="savings">
            ↘ You save {{ money(savings.amount) }} compared with {{ savings.merchant }}
          </p>
        </section>

        <section v-for="group in mix.groups" :key="group.merchant" class="store-group">
          <header class="store-group-head">
            <MerchantLogo :name="group.merchant" :size="26" />
            <strong>{{ group.merchant }}</strong>
            <span class="muted small">{{ group.items.length }} {{ group.items.length === 1 ? 'item' : 'items' }}</span>
            <span class="store-subtotal">{{ money(group.subtotal) }}</span>
          </header>

          <div v-for="item in group.items" :key="item.product.id" class="cart-item">
            <span class="cart-emoji" aria-hidden="true">{{ item.product.emoji }}</span>
            <div class="cart-item-body">
              <div class="cart-item-top">
                <span class="cart-item-name">{{ item.product.name }}</span>
                <button type="button" class="icon-btn" aria-label="Remove item" @click="setQty(item.product.id, 0)">🗑</button>
              </div>
              <div class="cart-item-bottom">
                <QtyStepper :model-value="item.qty" @update:model-value="setQty(item.product.id, $event)" />
                <div class="price-pills">
                  <span
                    v-for="offer in sortedOffers(item.product, allowed)"
                    :key="offer.merchant"
                    class="price-pill"
                    :class="{ chosen: offer.merchant === item.offer.merchant, out: offer.inStock === false }"
                  >
                    <MerchantLogo :name="offer.merchant" :size="16" />
                    {{ offer.inStock === false ? 'n/a' : money(offer.price * item.qty) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section v-if="mix.unavailable.length" class="store-group">
          <header class="store-group-head"><strong>Not available at your selected stores</strong></header>
          <div v-for="line in mix.unavailable" :key="line.product.id" class="cart-item muted">
            <span class="cart-emoji" aria-hidden="true">{{ line.product.emoji }}</span>
            <div class="cart-item-body">
              <div class="cart-item-top">
                <span class="cart-item-name">{{ line.product.name }}</span>
                <button type="button" class="icon-btn" aria-label="Remove item" @click="setQty(line.product.id, 0)">🗑</button>
              </div>
            </div>
          </div>
        </section>
      </template>

      <!-- ---------- One store ---------- -->
      <template v-else>
        <section class="summary">
          <h2>🏪 Compare by store</h2>
          <p class="muted small">What the whole cart costs if you buy everything in one store.</p>
        </section>

        <section v-for="store in stores" :key="store.merchant" class="store-group">
          <header class="store-group-head">
            <MerchantLogo :name="store.merchant" :size="26" />
            <div class="store-meta">
              <strong>{{ store.merchant }}</strong>
              <span class="muted small">
                {{ store.available }} of {{ cartLines.length }} items<template v-if="store.missing"> · {{ store.missing }} unavailable</template>
              </span>
            </div>
            <div class="store-right">
              <span class="store-subtotal">{{ money(store.total) }}</span>
              <span v-if="!store.missing && store.total > mix.total" class="diff">+{{ money(store.total - mix.total) }} vs mix</span>
              <span v-else-if="!store.missing" class="diff good">Best price</span>
            </div>
          </header>
          <button type="button" class="link-btn" @click="openStore = openStore === store.merchant ? null : store.merchant">
            {{ openStore === store.merchant ? '▴ Hide items' : '▾ Show items' }}
          </button>
          <ul v-if="openStore === store.merchant" class="store-items">
            <li v-for="item in store.items" :key="item.product.id" :class="{ muted: !item.offer }">
              <span>{{ item.product.emoji }} {{ item.product.name }} × {{ item.qty }}</span>
              <span>{{ item.offer ? money(item.lineTotal) : 'Unavailable' }}</span>
            </li>
          </ul>
        </section>
      </template>

      <!-- ---------- Checkout (automated later) ---------- -->
      <section class="checkout-bar">
        <div>
          <span class="muted small">Total ({{ cartCount }} items)</span>
          <strong class="checkout-total">{{ money(mix.total) }}</strong>
        </div>
        <button type="button" class="btn-primary" disabled title="Coming soon">
          ✦ Checkout with agent <span class="soon">Soon</span>
        </button>
      </section>
    </template>
  </main>
</template>
