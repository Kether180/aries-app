<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

const box = ref<HTMLDetailsElement | null>(null)

// Badges anywhere on the page dispatch this event; open the note and bring it into view
function open() {
  if (!box.value) return
  box.value.open = true
  box.value.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
}

onMounted(() => window.addEventListener('sentiment-help', open))
onUnmounted(() => window.removeEventListener('sentiment-help', open))
</script>

<template>
  <details ref="box" class="help">
    <summary>What do the labels mean?</summary>
    <p>
      Each label answers one question: is this good or bad news for the people and organisations the article is about?
    </p>
    <ul>
      <li>
        <span class="dot positive" /><strong>Positive:</strong> good news for them. Jobs created, a recovery, a win,
        charges dropped.
      </li>
      <li>
        <span class="dot negative" /><strong>Negative:</strong> bad news for them. Job losses, rising costs, harm,
        conflict, a setback.
      </li>
      <li>
        <span class="dot neutral" /><strong>Neutral:</strong> nothing clearly good or bad happened: an announcement, an
        explainer, a routine update, or good and bad that balance out.
      </li>
    </ul>
    <p>
      It is about what happened, not how the article is written. "Strongly" or "slightly" says how clear it is, and the
      small bar in each badge shows the same. Every article also has a one-line reason under its summary. Tap any badge
      to come back here.
    </p>
  </details>
</template>

<style scoped>
.help {
  margin-top: 12px;
  font-size: 0.86rem;
  color: var(--muted);
}
summary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-weight: 500;
  color: var(--accent);
  list-style: none;
}
summary::-webkit-details-marker {
  display: none;
}
summary::before {
  content: '?';
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--accent-text);
  background: var(--accent);
}
.help[open] summary {
  margin-bottom: 6px;
}
p {
  margin: 0 0 6px;
}
ul {
  margin: 0 0 8px;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
li {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
strong {
  color: var(--text);
  margin-right: 2px;
}
.dot {
  flex: none;
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  position: relative;
  top: -1px;
}
.positive {
  background: var(--positive);
}
.neutral {
  background: var(--neutral);
}
.negative {
  background: var(--negative);
}
</style>
