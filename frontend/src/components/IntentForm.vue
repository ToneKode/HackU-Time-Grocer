<script setup>
import { ref } from 'vue'

defineProps({ busy: Boolean })
const emit = defineEmits(['submit'])

const intent = ref('Buy toilet paper')
const monthlySpent = ref(0)

const suggestions = ['Buy toilet paper', 'Buy bulk toilet paper']

function submit() {
  const text = intent.value.trim()
  if (!text) return
  emit('submit', { intent: text, monthly_spent: Number(monthlySpent.value) || 0 })
}

function useSuggestion(text) {
  intent.value = text
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

    <div class="suggestions">
      <span class="muted">Try:</span>
      <button
        v-for="text in suggestions"
        :key="text"
        type="button"
        class="btn ghost small"
        :disabled="busy"
        @click="useSuggestion(text)"
      >
        {{ text }}
      </button>
    </div>
  </form>
</template>
