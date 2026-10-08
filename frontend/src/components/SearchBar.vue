<script setup lang="ts">
import { ref, watch } from 'vue'

import { COUNTRIES, TOPICS, countryName } from '@/constants'

const props = defineProps<{
  query: string // the search currently shown (chips set it from the parent)
  country: string // '' means worldwide
  activeQuery: string | null // what the results on the page are for
  loading: boolean
}>()

const emit = defineEmits<{ search: [query: string, country: string] }>()

// The box is editable locally; the parent only sees a value when the user submits
const text = ref(props.query)
watch(
  () => props.query,
  (q) => (text.value = q),
)

function changeCountry(event: Event) {
  emit('search', text.value, (event.target as HTMLSelectElement).value)
}
</script>

<template>
  <div>
    <form class="search" role="search" @submit.prevent="emit('search', text, country)">
      <input v-model="text" type="search" placeholder="Search a topic, company or person…" aria-label="Search news" />
      <select :value="country" aria-label="Country" class="country" @change="changeCountry">
        <option v-for="[code, name] in COUNTRIES" :key="code" :value="code">{{ name }}</option>
      </select>
      <button class="primary" type="submit" :disabled="loading">Search</button>
    </form>
    <p v-if="country" class="muted country-hint">
      Showing the {{ countryName(country) }} press in its own language, summarised in English.
    </p>

    <div class="chips">
      <button class="chip" :class="{ active: !activeQuery }" @click="emit('search', '', country)">Top headlines</button>
      <button
        v-for="topic in TOPICS"
        :key="topic"
        class="chip"
        :class="{ active: activeQuery?.toLowerCase() === topic.toLowerCase() }"
        @click="emit('search', topic, country)"
      >
        {{ topic }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.search {
  display: flex;
  gap: 8px;
  margin-top: 18px;
}
.search input {
  flex: 1;
  min-width: 0;
}
.country {
  height: 44px;
  max-width: 180px;
  padding: 0 32px 0 12px;
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  background: var(--surface);
  color: var(--text);
  font: inherit;
  font-size: 0.92rem;
  box-shadow: var(--shadow);
  appearance: none;
  background-image:
    linear-gradient(45deg, transparent 50%, var(--muted) 50%),
    linear-gradient(135deg, var(--muted) 50%, transparent 50%);
  background-position:
    calc(100% - 18px) 19px,
    calc(100% - 13px) 19px;
  background-size:
    5px 5px,
    5px 5px;
  background-repeat: no-repeat;
}
.country:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 18%, transparent);
}
.country-hint {
  margin: 8px 0 0;
  font-size: 0.85rem;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
@media (max-width: 600px) {
  .search {
    flex-wrap: wrap;
  }
  .search input {
    flex-basis: 100%;
  }
  .country {
    flex: 1;
    max-width: none;
  }
}
</style>
