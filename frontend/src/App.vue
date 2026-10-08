<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header class="header">
    <div class="container header-inner">
      <RouterLink to="/" class="brand">News<span>Pulse</span></RouterLink>
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
  background: color-mix(in srgb, var(--bg) 85%, transparent);
  backdrop-filter: blur(8px);
}
.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
}
.brand {
  font-weight: 800;
  font-size: 1.1rem;
  color: var(--text);
  text-decoration: none;
}
.brand span {
  color: var(--accent);
}
nav {
  display: flex;
  gap: 4px;
}
nav a {
  padding: 6px 12px;
  border-radius: 8px;
  color: var(--muted);
  text-decoration: none;
  font-weight: 500;
}
nav a:hover {
  color: var(--text);
}
nav a.router-link-exact-active {
  color: var(--text);
  background: var(--surface-2);
}
</style>
