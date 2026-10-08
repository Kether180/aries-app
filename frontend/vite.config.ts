import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // Forward API calls to FastAPI in dev, so the frontend can always use relative /api URLs
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
