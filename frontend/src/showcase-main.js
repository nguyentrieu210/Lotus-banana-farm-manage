// Dev-only entry for the component catalogue (not in vite.config build inputs). Same CSS stack as main.js.
import {createApp} from 'vue'
import './lotus-fonts.css'
import './lotus-tokens.css'
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
