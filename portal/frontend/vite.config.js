import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        // Полный стек в Docker: UI на :8010 (nginx). Разработка только Vite: backend на :8011
        target: process.env.VITE_API_PROXY || 'http://localhost:8011',
        changeOrigin: true,
      },
    },
  },
})
