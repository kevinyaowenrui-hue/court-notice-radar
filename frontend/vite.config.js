import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5220,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5225',
        changeOrigin: true
      }
    }
  }
})
