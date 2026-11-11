// Dev-only entry for the component catalogue (not in vite.config build inputs). Same CSS stack as main.js.
import {createApp} from 'vue'
import './lotus-fonts.css'
import './lotus-tokens.css'
// Shared kit classes (spec 004): chips, stat tiles, lot cards, charts… built only on the tokens.
import './lotus-kit.css'
import './lotus-kit-mobile.css'
import './style.css'
import './shadcn.css'
import './attio.css'
import './compact.css'
import './desktop-system.css'
import './desktop-components.css'
import './desktop-shell.css'
import './workspace-experience.css'
import UiShowcase from './components/UiShowcase.vue'
createApp(UiShowcase).mount('#app')
