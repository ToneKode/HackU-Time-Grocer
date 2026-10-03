<script setup>
import contract from '../../contract.json'

defineProps({ status: String, reason: String })
const labels = contract.labels.plan_status
</script>

<template>
  <div class="status" :class="`status-${status?.toLowerCase()}`">
    <strong>{{ labels[status] ?? status }}</strong>
    <span v-if="reason">{{ reason }}</span>
  </div>
</template>
