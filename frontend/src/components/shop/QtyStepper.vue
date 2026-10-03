<script setup>
const qty = defineModel({ type: Number, required: true })
</script>

<template>
  <div class="stepper">
    <button type="button" aria-label="Remove one" @click="qty = qty - 1">−</button>
    <span>{{ qty }}</span>
    <button type="button" aria-label="Add one" @click="qty = qty + 1">+</button>
  </div>
</template>
