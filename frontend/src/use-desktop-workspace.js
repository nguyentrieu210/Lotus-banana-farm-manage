import {computed,onMounted,onUnmounted,ref,watch} from 'vue'

// This preference changes presentation only; data, sorting and permissions stay in the apps.
export function useDesktopWorkspace({embedded=false}={}){
 const viewport=window.matchMedia('(min-width: 901px)')
 const desktop=ref(!embedded&&viewport.matches)
 let stored='comfortable'
 try{stored=localStorage.getItem('lotus-desktop-density')||stored}catch{}
 const density=ref(stored==='compact'?'compact':'comfortable')
 const gridDensity=computed(()=>desktop.value?density.value:null)
 const resized=event=>desktop.value=!embedded&&event.matches
 const apply=()=>{if(!embedded)document.documentElement.classList.toggle('lotus-desktop-page',desktop.value)}
 watch(desktop,apply)
 function setDensity(value){
  if(!['compact','comfortable'].includes(value))return
  density.value=value
  try{localStorage.setItem('lotus-desktop-density',value)}catch{}
 }
 onMounted(()=>{viewport.addEventListener('change',resized);apply()})
 onUnmounted(()=>{viewport.removeEventListener('change',resized);if(!embedded)document.documentElement.classList.remove('lotus-desktop-page')})
 return {desktop,density,gridDensity,setDensity}
}
