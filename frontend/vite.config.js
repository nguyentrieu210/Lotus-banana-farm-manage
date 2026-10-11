import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({plugins:[vue()],base:'/assets/lotus_farm/frontend/',build:{outDir:'../lotus_farm/public/frontend',emptyOutDir:true,manifest:true,rollupOptions:{input:['index.html','assign.html','mobile.html']}},server:{proxy:{'/api':'http://localhost:8000','/private':'http://localhost:8000','/files':'http://localhost:8000'}}})
