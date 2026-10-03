<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import contract from '../contract.json'
import * as api from './lib/api.js'
import IntentForm from './components/IntentForm.vue'
import StatusBanner from './components/StatusBanner.vue'
import OrderCard from './components/OrderCard.vue'
import ApprovalCard from './components/ApprovalCard.vue'
import TraceList from './components/TraceList.vue'
import BudgetCard from './components/BudgetCard.vue'
import RulesCard from './components/RulesCard.vue'
import ComparisonCard from './components/ComparisonCard.vue'

const plan = ref(null) // latest ActionPlan from the agent
const escalation = ref(null) // live copy, refreshed by polling
const lastRequest = ref(null) // { intent, monthly_spent }, reused on Approve
const loading = ref(false)
const deciding = ref(false)
const error = ref('')

// ---- Polling the escalation every second while it is PENDING ----
const POLL_MS = contract.calls.read_escalation.poll_every_seconds * 1000
let pollTimer = null
let pollToken = 0 // ignores replies that arrive after polling stopped

function startPolling(id) {
  stopPolling()
  const token = ++pollToken
  pollTimer = setInterval(async () => {
    try {
      const esc = await api.getEscalation(id)
      if (token !== pollToken) return
      escalation.value = esc
      if (esc.status !== 'PENDING') stopPolling()
    } catch (e) {
      if (token !== pollToken) return
      error.value = e.message
      stopPolling()
    }
  }, POLL_MS)
}

function stopPolling() {
  clearInterval(pollTimer)
  pollTimer = null
  pollToken++
}
onBeforeUnmount(stopPolling)

// ---- Agent calls ----
async function runAgent(request, escalationId) {
  stopPolling()
  error.value = ''
  loading.value = true
  try {
    const result = await api.sendIntent({ ...request, escalation_id: escalationId })
    plan.value = result
    escalation.value = result.escalation
    if (result.status === 'ESCALATED' && result.escalation?.status === 'PENDING') {
      startPolling(result.escalation.escalation_id)
    }
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function onSubmit(request) {
  lastRequest.value = request
  plan.value = null
  escalation.value = null
  runAgent(request)
}

// Approve -> ask the agent again with the same intent + escalation_id.
// Refuse / expire -> show "Purchase cancelled" and do not call the agent.
async function onDecide(decision) {
  const id = escalation.value.escalation_id
  stopPolling()
  deciding.value = true
  error.value = ''
  try {
    const esc = await api.decide(id, decision)
    escalation.value = esc
    if (esc.status === 'APPROVED') await runAgent(lastRequest.value, id)
    else if (esc.status === 'PENDING') startPolling(id)
  } catch (e) {
    error.value = e.message
  } finally {
    deciding.value = false
  }
}

// ---- What to show ----
const status = computed(() => {
  if (!plan.value) return null
  const escStatus = escalation.value?.status
  if (plan.value.status === 'ESCALATED' && (escStatus === 'REFUSED' || escStatus === 'EXPIRED')) {
    return 'ABORTED'
  }
  return plan.value.status
})

const reason = computed(() => {
  if (!plan.value) return ''
  if (status.value === 'ABORTED') return `Approval ${contract.labels.escalation_status[escalation.value.status].toLowerCase()}`
  if (status.value === 'FAILED') return plan.value.payment?.error ?? ''
  if (status.value === 'COMPLETED' && escalation.value?.status === 'APPROVED') return 'Approved by you'
  return plan.value.policy?.reason ?? ''
})

const monthlyCap = contract.active_rules.find((r) => r.id === 'monthly_cap').amount
const budget = computed(() => {
  const policy = plan.value?.policy
  const spent = policy?.monthly_spent ?? lastRequest.value?.monthly_spent ?? 0
  const cap = policy?.monthly_cap ?? monthlyCap
  return {
    cap,
    spent,
    remaining: policy?.monthly_remaining ?? cap - spent,
    amount: policy?.amount ?? 0,
    status: policy?.status ?? null,
  }
})
</script>

<template>
  <header class="topbar">
    <div>
      <h1>Time-Grocer</h1>
      <p class="muted">Agent checkout with a parent in the loop</p>
    </div>
    <span class="pill" :class="api.useMock ? 'pill-warn' : 'pill-ok'">
      {{ api.useMock ? 'Mock data' : 'Live API' }}
    </span>
  </header>

  <main class="layout">
    <section class="main-col">
      <IntentForm :busy="loading || deciding" @submit="onSubmit" />

      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="loading" class="muted working">Agent is working…</p>

      <template v-if="plan">
        <StatusBanner :status="status" :reason="reason" />
        <OrderCard v-if="status === 'COMPLETED'" :plan="plan" />
        <ApprovalCard
          v-if="plan.status === 'ESCALATED' && escalation"
          :escalation="escalation"
          :busy="deciding || loading"
          @decide="onDecide"
        />
        <TraceList :entries="plan.audit_log" />
      </template>

      <section v-else-if="!loading" class="card empty">
        <h2>No purchase yet</h2>
        <p class="muted">Type what you need, or try one of the demo buttons.</p>
      </section>
    </section>

    <aside class="side-col">
      <BudgetCard :budget="budget" />
      <RulesCard :rules="contract.active_rules" />
      <ComparisonCard :comparison="contract.comparison" />
    </aside>
  </main>
</template>
