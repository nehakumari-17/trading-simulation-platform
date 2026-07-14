import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// proxy all /api and /ws calls to the FastAPI backend
// so we don't have to type localhost:8000 everywhere in the code
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
