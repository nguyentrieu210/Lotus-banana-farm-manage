import 'vant/lib/index.css'
import './lotus-fonts.css'
import './lotus-tokens.css'
// Shared kit classes (spec 004): chips, stat tiles, lot cards, charts… built only on the tokens.
import './lotus-kit.css'
import './lotus-kit-mobile.css'
import {createApp} from 'vue'
import BuyingMobile from './BuyingMobile.vue'
createApp(BuyingMobile).mount('#app')

// Shared form components (UiButton, DataTable, ...) are styled by Tailwind utilities.
import './shadcn.css'
import './mobile-ui.css'
