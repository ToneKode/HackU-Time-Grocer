<script setup>
import { money } from '../lib/format.js'

defineProps({ plan: { type: Object, required: true } })
</script>

<template>
  <section class="card">
    <h2>Order details</h2>
    <!-- Product names are untrusted plain text: always {{ }}, never v-html. -->
    <p class="product-name">{{ plan.product.name }}</p>
    <dl class="rows">
      <dt>Merchant</dt><dd>{{ plan.product.merchant }}</dd>
      <dt>Order ID</dt><dd class="mono">{{ plan.payment.order_id }}</dd>
      <dt>Subtotal</dt><dd>{{ money(plan.quote?.subtotal) }}</dd>
      <dt>Shipping</dt><dd>{{ money(plan.quote?.shipping_fee) }}</dd>
      <dt class="total">Charged</dt><dd class="total">{{ money(plan.payment.charged) }}</dd>
    </dl>
  </section>
</template>
