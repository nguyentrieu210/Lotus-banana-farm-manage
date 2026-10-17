import {nextTick,onMounted,onUnmounted,ref,watch} from 'vue'
import {popupLayout} from './mobile-popup-layout'

export function useMobilePopup(root,input,opened,onClose){
 const popup=ref(null),style=ref({visibility:'hidden'}),above=ref(false)
 let frame=0,observer,gesture=null
 const close=()=>{opened.value=false;onClose?.()}
 function position(){
  frame=0
  if(!opened.value||!root.value)return
  const box=root.value.getBoundingClientRect(),vv=window.visualViewport
  const header=document.querySelector('.lotus-pwa-header,.mobile-head')?.getBoundingClientRect().bottom||0
  const nav=document.querySelector('.lotus-pwa-bottom .van-tabbar,.mobile-bottom')?.getBoundingClientRect()
  const bottom=(vv?.offsetTop||0)+(vv?.height||window.innerHeight)
  const footer=nav&&nav.height>0&&nav.top<bottom?Math.max(0,bottom-nav.top):0
  if(box.bottom<header||box.top>bottom){close();return}
  const p=popupLayout(box,{left:vv?.offsetLeft||0,top:vv?.offsetTop||0,width:vv?.width||window.innerWidth,height:vv?.height||window.innerHeight},{header,footer})
  above.value=p.up
  style.value={position:'fixed',left:p.left+'px',top:(p.up?box.top-6:p.top)+'px',transform:p.up?'translateY(-100%)':'none',width:p.width+'px',maxHeight:p.maxHeight+'px',visibility:p.maxHeight>0?'visible':'hidden'}
 }
 function schedule(){if(opened.value&&!frame)frame=requestAnimationFrame(position)}
 function outside(e){if(!root.value?.contains(e.target)&&!popup.value?.contains(e.target))close()}
 function focusOutside(e){if(opened.value)outside(e)}
 function dismiss(){close();input.value?.blur()}
 function exclusive(e){if(e.detail!==root.value)close()}
 function pointerStart(e){
  gesture={x:e.clientX,y:e.clientY,moved:false}
  // Preserve mouse focus without cancelling native touch scrolling.
  if(e.pointerType==='mouse')e.preventDefault()
 }
 function pointerMove(e){if(gesture&&Math.hypot(e.clientX-gesture.x,e.clientY-gesture.y)>8)gesture.moved=true}
 function canChoose(event){const ok=!event||event.detail===0||!gesture?.moved;gesture=null;return ok}
 function highlight(id){nextTick(()=>document.getElementById(id)?.scrollIntoView({block:'nearest'}))}
 watch(opened,async value=>{
  if(!value){cancelAnimationFrame(frame);frame=0;style.value={visibility:'hidden'};return}
  document.dispatchEvent(new CustomEvent('warehouse-picker-open',{detail:root.value}))
  await nextTick();position()
 })
 onMounted(()=>{
  document.addEventListener('pointerdown',outside)
  document.addEventListener('focusin',focusOutside)
  document.addEventListener('warehouse-picker-open',exclusive)
  document.addEventListener('warehouse-dismiss-picker',dismiss)
  window.addEventListener('scroll',schedule,{passive:true,capture:true})
  window.addEventListener('resize',schedule,{passive:true})
  window.visualViewport?.addEventListener('resize',schedule,{passive:true})
  window.visualViewport?.addEventListener('scroll',schedule,{passive:true})
  observer=new ResizeObserver(schedule);if(root.value)observer.observe(root.value)
 })
 onUnmounted(()=>{
  cancelAnimationFrame(frame);observer?.disconnect()
  document.removeEventListener('pointerdown',outside)
  document.removeEventListener('focusin',focusOutside)
  document.removeEventListener('warehouse-picker-open',exclusive)
  document.removeEventListener('warehouse-dismiss-picker',dismiss)
  window.removeEventListener('scroll',schedule,true)
  window.removeEventListener('resize',schedule)
  window.visualViewport?.removeEventListener('resize',schedule)
  window.visualViewport?.removeEventListener('scroll',schedule)
 })
 return {popup,style,above,close,schedule,pointerStart,pointerMove,canChoose,highlight}
}
