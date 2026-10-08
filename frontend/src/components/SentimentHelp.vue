<template>
  <details class="help">
    <summary>What do the labels mean?</summary>
    <p>Each article gets a tone, judged from the point of view of the people it is about, not from ours:</p>
    <ul>
      <li>
        <span class="dot positive" /> <strong>Positive:</strong> good news for them. A win, growth, a breakthrough, a
        recovery.
      </li>
      <li><span class="dot negative" /> <strong>Negative:</strong> bad news. Losses, harm, conflict, a setback.</li>
      <li><span class="dot neutral" /> <strong>Neutral:</strong> mostly factual, mixed, or routine reporting.</li>
    </ul>
    <p>
      "Strongly" and "slightly" say how clear the tone is, and the small bar in each badge shows the same thing. Every
      article also has a one-line reason under its summary.
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
