import {computed,onMounted,onUnmounted,ref,watch} from 'vue'

// This preference changes presentation only; data, sorting and permissions stay in the apps.
export function useDesktopWorkspace(){
 const viewport=window.matchMedia('(min-width: 901px)')
 const desktop=ref(viewport.matches)
 let stored='comfortable'
 try{stored=localStorage.getItem('lotus-desktop-density')||stored}catch{}
 const density=ref(stored==='compact'?'compact':'comfortable')
 const gridDensity=computed(()=>desktop.value?density.value:null)
 const resized=event=>desktop.value=event.matches
 const apply=()=>document.documentElement.classList.toggle('lotus-desktop-page',desktop.value)
 watch(desktop,apply)
 function setDensity(value){
  if(!['compact','comfortable'].includes(value))return
  density.value=value
  try{localStorage.setItem('lotus-desktop-density',value)}catch{}
 }
 onMounted(()=>{viewport.addEventListener('change',resized);apply()})
 onUnmounted(()=>{viewport.removeEventListener('change',resized);document.documentElement.classList.remove('lotus-desktop-page')})
 return {desktop,density,gridDensity,setDensity}
}
