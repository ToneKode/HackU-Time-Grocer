<script setup>
defineProps({ comparison: { type: Object, required: true } })
</script>

<template>
  <section class="card">
    <h2>Why an agent?</h2>
    <div class="compare">
      <div v-for="side in [comparison.manual, comparison.agent]" :key="side.label" class="compare-col">
        <span class="muted">{{ side.label }}</span>
        <strong>{{ side.duration_display }}</strong>
        <span>{{ side.steps }} {{ side.steps === 1 ? 'step' : 'steps' }}</span>
      </div>
    </div>
  </section>
</template>
