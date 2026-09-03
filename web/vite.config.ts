import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: false,
  },
  server: {
    host: '127.0.0.1',
    port: 43123,
    proxy: {
      '/v1': 'http://127.0.0.1:43124',
      '/health': 'http://127.0.0.1:43124',
    },
  },
})
