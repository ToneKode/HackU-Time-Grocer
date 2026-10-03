<script setup>
defineProps({ rules: { type: Array, required: true } })
</script>

<template>
  <section class="card">
    <h2>Active rules</h2>
    <dl class="rows">
      <template v-for="rule in rules" :key="rule.id">
        <dt>{{ rule.label }}</dt>
        <dd v-if="rule.merchants" class="chips">
          <span v-for="m in rule.merchants" :key="m" class="chip" :class="{ 'chip-bad': rule.id === 'blacklist' }">{{ m }}</span>
        </dd>
        <dd v-else>{{ rule.display }}</dd>
      </template>
    </dl>
  </section>
</template>
