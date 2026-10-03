<script setup>
import { ref, computed, watch } from 'vue'
import contract from '../../contract.json'
import { verifyChain } from '../lib/hash.js'
import { shortHash } from '../lib/format.js'

const props = defineProps({ entries: { type: Array, default: () => [] } })
const eventLabels = contract.labels.event

const sorted = computed(() => [...props.entries].sort((a, b) => a.index - b.index))

const checks = ref([])
watch(
  sorted,
  async (entries) => {
    const results = await verifyChain(entries)
    if (entries === sorted.value) checks.value = results
  },
  { immediate: true },
)
const verified = computed(
  () => checks.value.length === sorted.value.length && checks.value.every(Boolean),
)
</script>

<template>
  <section class="card">
    <div class="approval-head">
      <h2>Agent trace</h2>
      <span v-if="entries.length" class="pill" :class="verified ? 'pill-ok' : 'pill-bad'">
        {{ verified ? 'Hash chain verified' : 'Hash chain broken' }}
      </span>
    </div>

    <ol class="trace">
      <li v-for="(entry, i) in sorted" :key="entry.index" :class="{ broken: checks[i] === false }">
        <div class="trace-top">
          <span class="trace-event">{{ eventLabels[entry.event] ?? entry.event }}</span>
          <span class="pill small">{{ entry.status }}</span>
          <span class="muted mono">{{ entry.ts }}</span>
        </div>
        <p class="thought">{{ entry.thought }}</p>
        <p class="muted">{{ entry.reason }}</p>
        <p class="hashes mono muted">
          <span :title="entry.prev_hash">prev {{ shortHash(entry.prev_hash) }}</span>
          <span :title="entry.hash">hash {{ shortHash(entry.hash) }}</span>
        </p>
      </li>
    </ol>
  </section>
</template>
