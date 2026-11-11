import {ref,onMounted,onUnmounted} from 'vue'
import {useUiMode} from './ui-mode'
const read=(key,fallback)=>{try{return localStorage.getItem(key)||fallback}catch{return fallback}}
const write=(key,value)=>{try{localStorage.setItem(key,value)}catch{}}
// Light/dark and table density come from ui-mode.js, the one source for desktop and phone (spec 004).
// The desktop never shows the outdoor mode; it keeps the theme the person chose (light by default).
const ui=useUiMode({followSystem:false,allowOutdoor:false})
export const dark=ui.dark
export const density=ui.density
export const sidebarCollapsed=ref(read('lotus-sidebar','open')==='closed')
export function useWorkspace(){
 function toggleSidebar(){sidebarCollapsed.value=!sidebarCollapsed.value;write('lotus-sidebar',sidebarCollapsed.value?'closed':'open')}
 function storage(event){if(event.key==='lotus-sidebar')sidebarCollapsed.value=event.newValue==='closed'}
 onMounted(()=>window.addEventListener('storage',storage))
 onUnmounted(()=>window.removeEventListener('storage',storage))
 return {dark,density,sidebarCollapsed,toggleTheme:ui.toggleTheme,setDensity:ui.setDensity,toggleSidebar}
}
