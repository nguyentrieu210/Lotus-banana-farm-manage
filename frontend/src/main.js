import {createApp} from 'vue'
import {createPinia} from 'pinia'
import {createLotusRouter} from './router'
import {setCSRF} from './api'
import App from './App.vue'
import './style.css'
import './attio.css'
window.addEventListener('lotus-csrf',event=>setCSRF(event.detail))
createApp(App).use(createPinia()).use(createLotusRouter()).mount('#app')
if('serviceWorker' in navigator)navigator.serviceWorker.register('/api/method/lotus_farm.web.service_worker',{scope:'/lotus/'}).catch(()=>{})
