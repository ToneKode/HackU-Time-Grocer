<script setup>
import { ref } from 'vue'
import contract from '../../contract.json'

defineProps({ busy: Boolean })
const emit = defineEmits(['submit'])

const intent = ref('Buy toilet paper')
const monthlySpent = ref(0)

const demos = [
  { key: 'happy_path', label: 'Normal order' },
  { key: 'halted_monthly', label: 'Monthly cap hit' },
  { key: 'escalation_bulk', label: 'Bulk (needs approval)' },
].map((d) => ({ ...d, request: contract.examples[d.key].request }))

function submit() {
  const text = intent.value.trim()
  if (!text) return
  emit('submit', { intent: text, monthly_spent: Number(monthlySpent.value) || 0 })
}

function runDemo(request) {
  intent.value = request.intent
  monthlySpent.value = request.monthly_spent
  submit()
}
</script>

<template>
  <form class="card intent" @submit.prevent="submit">
    <label class="field grow">
      <span>What should the agent buy?</span>
      <input v-model="intent" type="text" placeholder="Buy toilet paper" :disabled="busy" />
    </label>
    <label class="field">
      <span>Spent this month (HK$)</span>
      <input v-model.number="monthlySpent" type="number" min="0" step="0.01" :disabled="busy" />
    </label>
    <button class="btn primary" type="submit" :disabled="busy">Send to agent</button>

    <div class="demos">
      <span class="muted">Demo:</span>
      <button
        v-for="demo in demos"
        :key="demo.key"
        type="button"
        class="btn ghost small"
        :disabled="busy"
        @click="runDemo(demo.request)"
      >
        {{ demo.label }}
      </button>
    </div>
  </form>
</template>
