import {ref,onMounted,onUnmounted} from 'vue'
const read=(key,fallback)=>{try{return localStorage.getItem(key)||fallback}catch{return fallback}}
const write=(key,value)=>{try{localStorage.setItem(key,value)}catch{}}
export const dark=ref(read('lotus-theme','light')==='dark')
export const sidebarCollapsed=ref(read('lotus-sidebar','open')==='closed')
function applyTheme(){document.documentElement.classList.toggle('dark',dark.value);document.documentElement.dataset.theme=dark.value?'dark':'light';document.documentElement.style.colorScheme=dark.value?'dark':'light'}
applyTheme()
export function useWorkspace(){
 function toggleTheme(){dark.value=!dark.value;write('lotus-theme',dark.value?'dark':'light');applyTheme()}
 function toggleSidebar(){sidebarCollapsed.value=!sidebarCollapsed.value;write('lotus-sidebar',sidebarCollapsed.value?'closed':'open')}
 function storage(event){if(event.key==='lotus-theme'){dark.value=event.newValue==='dark';applyTheme()}if(event.key==='lotus-sidebar')sidebarCollapsed.value=event.newValue==='closed'}
 onMounted(()=>window.addEventListener('storage',storage))
 onUnmounted(()=>window.removeEventListener('storage',storage))
 return {dark,sidebarCollapsed,toggleTheme,toggleSidebar}
}
