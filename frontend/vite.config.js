import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import {fileURLToPath,URL} from 'node:url'
export default defineConfig({plugins:[vue()],resolve:{alias:{'@':fileURLToPath(new URL('./src',import.meta.url))}},base:'/assets/lotus_farm/frontend/',build:{outDir:'../lotus_farm/public/frontend',emptyOutDir:true,manifest:true,rollupOptions:{input:['index.html','assign.html','stock.html','timekeeping.html','farm-work.html','hr.html','warehouse.html','work-mobile.html','buying.html','hr-mobile.html']}},server:{proxy:{'/api':'http://localhost:8000','/private':'http://localhost:8000','/files':'http://localhost:8000'}}})
