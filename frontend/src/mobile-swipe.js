export function swipeStep({dx,dy,elapsed,startX,width}){
 if(startX<24||startX>width-24||elapsed>650||Math.abs(dx)<72||Math.abs(dx)<Math.abs(dy)*2)return 0
 return dx<0?1:-1
}

/* Edge-swipe between root tabs, shared by the PWAs. Returns touch handlers for the shell element. */
export function createTabSwipe({enabled,ignore,tabs,current,go}){
 let swipe=null
 function start(event){
  swipe=null
  if(!enabled()||event.touches.length!==1||event.target.closest(ignore))return
  const t=event.touches[0]
  if(t.clientX<24||t.clientX>window.innerWidth-24)return
  swipe={x:t.clientX,y:t.clientY,time:performance.now(),screen:current()}
 }
 function move(event){
  if(!swipe||event.touches.length!==1){swipe=null;return}
  const t=event.touches[0],dx=t.clientX-swipe.x,dy=t.clientY-swipe.y
  if(Math.abs(dy)>16&&Math.abs(dy)>Math.abs(dx)){swipe=null;return}
  if(Math.abs(dx)>16&&Math.abs(dx)>Math.abs(dy)*2&&event.cancelable)event.preventDefault()
 }
 function end(event){
  const from=swipe;swipe=null
  if(!from||from.screen!==current()||!event.changedTouches?.length)return
  const t=event.changedTouches[0],list=tabs()
  const step=swipeStep({dx:t.clientX-from.x,dy:t.clientY-from.y,elapsed:performance.now()-from.time,startX:from.x,width:window.innerWidth})
  const target=list[list.indexOf(current())+step]
  if(step&&target)go(target)
 }
 return {start,move,end,cancel(){swipe=null}}
}
