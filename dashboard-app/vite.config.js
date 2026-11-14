import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base './' -> the built site works from any sub-path (GitHub Pages, Netlify, Vercel) and from a plain folder
export default defineConfig({
  base: './',
  plugins: [react()],
  build: { outDir: 'dist', chunkSizeWarningLimit: 2500, sourcemap: false },
});
