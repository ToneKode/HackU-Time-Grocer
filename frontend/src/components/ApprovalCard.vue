<script setup>
import { computed } from 'vue'
import contract from '../../contract.json'
import { money, clock } from '../lib/format.js'

const props = defineProps({
  escalation: { type: Object, required: true },
  busy: Boolean,
})
const emit = defineEmits(['decide'])

const screen = contract.screens.approval
const labels = contract.labels.escalation_status
const canDecide = computed(
  () => props.escalation.status === 'PENDING' && props.escalation.remaining_seconds > 0 && !props.busy,
)
const progress = computed(() => (props.escalation.remaining_seconds / props.escalation.ttl_seconds) * 100)
</script>

<template>
  <section class="card approval" :class="{ closed: escalation.status !== 'PENDING' }">
    <div class="approval-head">
      <h2>Approval needed</h2>
      <span class="pill">{{ labels[escalation.status] }}</span>
    </div>

    <div class="timer" :class="{ low: escalation.remaining_seconds <= 60 }">
      {{ clock(escalation.remaining_seconds) }}
    </div>
    <div class="timer-bar"><div :style="{ width: progress + '%' }" /></div>

    <dl class="rows">
      <dt>Amount</dt><dd class="total">{{ money(escalation.amount) }}</dd>
      <dt>Merchant</dt><dd>{{ escalation.merchant }}</dd>
      <dt>Reason</dt><dd>{{ escalation.reason }}</dd>
    </dl>

    <div class="actions">
      <button
        v-for="button in screen.buttons"
        :key="button.decision"
        class="btn"
        :class="button.decision === 'APPROVE' ? 'primary' : 'danger'"
        :disabled="!canDecide"
        @click="emit('decide', button.decision)"
      >
        {{ button.label }}
      </button>
    </div>
  </section>
</template>
