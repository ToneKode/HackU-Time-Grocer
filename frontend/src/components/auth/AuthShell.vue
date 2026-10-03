<script setup>
// Two-column auth layout: form on the left, food illustration on the right
// (on phones the illustration becomes a banner above the form).
import AuthArt from './AuthArt.vue'

defineProps({
  variant: { type: String, default: 'login' },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>

<template>
  <main class="auth-page">
    <section class="auth-form-side">
      <div class="auth-form-wrap">
        <h1 class="auth-title">{{ title }}</h1>
        <p v-if="subtitle" class="auth-subtitle">{{ subtitle }}</p>
        <slot />
      </div>
    </section>
    <aside class="auth-art-side" :class="`auth-art-${variant}`">
      <AuthArt :variant="variant" />
    </aside>
  </main>
</template>
