import 'vant/lib/index.css'
import './lotus-fonts.css'
import './lotus-tokens.css'
import {createApp} from 'vue'
import WorkMobile from './WorkMobile.vue'
import './mobile-work-legacy.css'
import './work-mobile.css'
// The daily report reuses the shared form components (UiButton, LineItemsEditor); their Tailwind utilities, no preflight.
import './shadcn.css'
import './register-work-worker'
createApp(WorkMobile).mount('#app')

import './mobile-ui.css'
