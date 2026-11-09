import 'vant/lib/index.css'
import './lotus-fonts.css'
import './lotus-tokens.css'
import {createApp} from 'vue'
import WarehouseMobile from './WarehouseMobile.vue'
import './warehouse-mobile.css'
import './register-warehouse-worker'
createApp(WarehouseMobile).mount('#app')

// Shared form components (UiButton, DataTable, ...) are styled by Tailwind utilities.
import './shadcn.css'
import './mobile-ui.css'
