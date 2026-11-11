// Builds the component catalogue (showcase.html) as a static site for review.
// It is never part of the production build: vite.config.js does not list this page,
// and the output goes to frontend/dist-showcase (git-ignored), not to lotus_farm/public.
//   npm run showcase:build            → frontend/dist-showcase/showcase.html
//   LOTUS_SHOWCASE_OUT=/some/dir LOTUS_SHOWCASE_BASE=/catalogue/ npm run showcase:build
import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'
import {fileURLToPath,URL} from 'node:url'

export default defineConfig({
  plugins:[vue()],
  resolve:{alias:{'@':fileURLToPath(new URL('./src',import.meta.url))}},
  base:process.env.LOTUS_SHOWCASE_BASE||'./',
  build:{
    outDir:process.env.LOTUS_SHOWCASE_OUT||'dist-showcase',
    emptyOutDir:true,
    chunkSizeWarningLimit:2500,
    rollupOptions:{input:['showcase.html']},
  },
})
