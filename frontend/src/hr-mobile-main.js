import 'vant/lib/index.css'
import './lotus-fonts.css'
import './lotus-tokens.css'
import {createApp} from 'vue'
import HrMobile from './HrMobile.vue'
import './hr-mobile.css'
import './register-hr-worker.js'
// Shared form components (UiButton, DataTable, ...) are styled by Tailwind utilities.
import './shadcn.css'
import './mobile-ui.css'
createApp(HrMobile).mount('#app')
