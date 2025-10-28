import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/admin-app/',  // ✅ Set base path for production build
  server: {
    host: '0.0.0.0', // Bind to all network interfaces for devcontainer access
    port: 5173, // frontend dev server
    proxy: {
      // Proxy all /api routes (including /api/v1/auth/login)
      '/api': {
        target: 'http://127.0.0.1:8000', // your FastAPI backend
        changeOrigin: true,
        secure: false,
      },
      // Proxy admin-specific API routes
      '/admin/api': {
        target: 'http://127.0.0.1:8000', // admin API endpoints
        changeOrigin: true,
        secure: false,
      },
      '/handoff': {
        target: 'http://127.0.0.1:8000', // handoff endpoints
        changeOrigin: true,
        secure: false,
      },
      '/admin-app/handoff': {
        target: 'http://127.0.0.1:8000', // handoff endpoints (from admin-app base)
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/admin-app/, ''),
      },
      '/followup': {
        target: 'http://127.0.0.1:8000', // followup submissions
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
        rewriteWsOrigin: true,
      },
      '/admin-ws': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
        rewriteWsOrigin: true,
      },
    },
  },
})
