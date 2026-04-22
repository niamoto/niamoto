import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const apiPort = process.env.NIAMOTO_DESKTOP_API_PORT ?? '8080'
const apiTarget = `http://127.0.0.1:${apiPort}`

// Read version from tauri.conf.json (single source of truth)
const tauriConf = JSON.parse(readFileSync(path.resolve(__dirname, '../../../../src-tauri/tauri.conf.json'), 'utf-8'))

// https://vite.dev/config/
export default defineConfig({
  define: {
    '__APP_VERSION__': JSON.stringify(tauriConf.version),
  },
  plugins: [react()],
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json-summary', 'lcov'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/**/*.test.{ts,tsx}',
        'src/**/__tests__/**',
        'src/**/*.generated.ts',
        'src/**/*.generated.tsx',
        'src/vite-env.d.ts',
        'src/main.tsx',
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/preview': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 1000, // Augmente la limite à 1MB au lieu de 500KB
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return undefined
          }

          if (
            id.includes('@monaco-editor/react') ||
            id.includes('monaco-editor')
          ) {
            return 'monaco'
          }

          if (
            id.includes('/novel/') ||
            id.includes('/@tiptap/') ||
            id.includes('tiptap-extension-resize-image')
          ) {
            return 'rich-text'
          }

          return undefined
        },
      },
      onwarn(warning, warn) {
        // Ignore les warnings de commentaires PURE de @daybrush/utils
        if (warning.code === 'SOURCEMAP_ERROR' ||
            (warning.message && warning.message.includes('/*#__PURE__*/'))) {
          return
        }
        warn(warning)
      },
    },
  },
})
