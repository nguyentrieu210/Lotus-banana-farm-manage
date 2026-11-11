import {computed,onMounted,onUnmounted,ref,watch} from 'vue'
import {uiDensity,useUiMode} from './ui-mode'

// This preference changes presentation only; data, sorting and permissions stay in the apps.
// Density is the one shared choice from the account menu (ui-mode.js, spec 004); narrow screens leave it to DataTable.
export function useDesktopWorkspace({embedded=false}={}){
 const viewport=window.matchMedia('(min-width: 901px)')
 const desktop=ref(!embedded&&viewport.matches)
 const {setDensity}=useUiMode()
 const density=computed(()=>uiDensity.value)
 const gridDensity=computed(()=>desktop.value?density.value:null)
 const resized=event=>desktop.value=!embedded&&event.matches
 const apply=()=>{if(!embedded)document.documentElement.classList.toggle('lotus-desktop-page',desktop.value)}
 watch(desktop,apply)
 onMounted(()=>{viewport.addEventListener('change',resized);apply()})
 onUnmounted(()=>{viewport.removeEventListener('change',resized);if(!embedded)document.documentElement.classList.remove('lotus-desktop-page')})
 return {desktop,density,gridDensity,setDensity}
}
