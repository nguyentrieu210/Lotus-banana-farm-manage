import {onMounted,onUnmounted,ref} from 'vue'

export function useMobileViewport(){
 const keyboard=ref(false)
 let baseline=0,frame=0
 function update(){
  frame=0
  const vv=window.visualViewport
  const height=vv?.height||window.innerHeight
  const focused=document.activeElement
  const editing=focused?.matches('input:not([type="checkbox"]):not([type="file"]),textarea,[contenteditable="true"]')
  if(!editing)baseline=window.innerHeight
  keyboard.value=!!editing&&Math.max(baseline,window.innerHeight)-height>140
  document.documentElement.style.setProperty('--warehouse-visible-height',height+'px')
 }
 function schedule(){if(!frame)frame=requestAnimationFrame(update)}
 function orientation(){baseline=window.innerHeight;schedule()}
 onMounted(()=>{
  baseline=window.innerHeight;update()
  window.visualViewport?.addEventListener('resize',schedule,{passive:true})
  window.visualViewport?.addEventListener('scroll',schedule,{passive:true})
  window.addEventListener('resize',schedule,{passive:true})
  window.addEventListener('orientationchange',orientation)
  document.addEventListener('focusin',schedule)
  document.addEventListener('focusout',schedule)
 })
 onUnmounted(()=>{
  cancelAnimationFrame(frame)
  window.visualViewport?.removeEventListener('resize',schedule)
  window.visualViewport?.removeEventListener('scroll',schedule)
  window.removeEventListener('resize',schedule)
  window.removeEventListener('orientationchange',orientation)
  document.removeEventListener('focusin',schedule)
  document.removeEventListener('focusout',schedule)
  document.documentElement.style.removeProperty('--warehouse-visible-height')
 })
 return {keyboard}
}
