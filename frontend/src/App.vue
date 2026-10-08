<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header class="header">
    <div class="container header-inner">
      <RouterLink to="/" class="brand">
        <svg class="mark" viewBox="0 0 32 32" aria-hidden="true">
          <rect width="32" height="32" rx="8" fill="url(#brand-gradient)" />
          <!-- Aries glyph: a stem with two horns curling outward -->
          <path
            d="M16 27V13M16 13C16 5.5 6.5 5 6.5 12.5M16 13C16 5.5 25.5 5 25.5 12.5"
            fill="none"
            stroke="#fff"
            stroke-width="2.6"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <defs>
            <linearGradient id="brand-gradient" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#5b5bd6" />
              <stop offset="1" stop-color="#8b5cf6" />
            </linearGradient>
          </defs>
        </svg>
        <span>Aries<em>News</em></span>
      </RouterLink>
      <nav>
        <RouterLink to="/">Discover</RouterLink>
        <RouterLink to="/research">Research</RouterLink>
        <RouterLink to="/library">Library</RouterLink>
      </nav>
    </div>
  </header>

  <main class="container">
    <RouterView />
  </main>
</template>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 1px solid var(--border);
  background: color-mix(in srgb, var(--bg) 82%, transparent);
  backdrop-filter: blur(10px);
}
.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  font-weight: 800;
  font-size: 1.12rem;
  letter-spacing: -0.02em;
  color: var(--text);
  text-decoration: none;
}
.brand em {
  font-style: normal;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  box-shadow: 0 4px 10px -4px color-mix(in srgb, var(--accent) 70%, transparent);
}
nav {
  display: flex;
  gap: 2px;
  padding: 3px;
  border-radius: 12px;
  background: var(--surface-2);
}
nav a {
  padding: 6px 13px;
  border-radius: 9px;
  color: var(--muted);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.92rem;
  transition:
    color 0.15s ease,
    background 0.15s ease;
}
nav a:hover {
  color: var(--text);
}
nav a.router-link-exact-active {
  color: var(--text);
  background: var(--surface);
  box-shadow: var(--shadow);
  font-weight: 600;
}
@media (max-width: 480px) {
  .brand span {
    display: none;
  }
}
</style>
