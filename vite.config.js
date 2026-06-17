import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: resolve(__dirname, 'qatrack/qatrack_core/static/dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        faults: resolve(__dirname, 'qatrack/faults/static/faults/src/main.js')
      },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: '[name].js',
        assetFileNames: '[name].[ext]'
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'qatrack/faults/static/faults/src')
    }
  }
});
