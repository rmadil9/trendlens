import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  // Mirrors what nginx does in production: /api/* is stripped of its prefix
  // and forwarded to the backend. Without this, the relative fetch("/api/query")
  // in src/api/client.js would hit the Vite dev server itself and 404.
  //
  // The point is dev/prod parity — the client code contains no environment
  // branch, because both environments present the API at the same origin under
  // the same path.
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
