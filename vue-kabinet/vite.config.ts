import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // Relative paths so the build works from any folder, e.g. GitHub Pages
  base: './',
  build: { outDir: 'demo', emptyOutDir: true },
  test: { environment: 'jsdom' },
})
