import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // GitHub Pages serves from /Bianca2-google/ — set base accordingly.
  // VITE_BASE_PATH is injected by the GitHub Actions workflow.
  // Falls back to '/' for local dev.
  base: process.env.VITE_BASE_PATH || '/',
})
