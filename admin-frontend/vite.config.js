import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/admin-app/',  // ✅ Set base path for production build
  server: {
    port: 5173, // frontend dev server
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // your FastAPI backend
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
      '/admin-ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
