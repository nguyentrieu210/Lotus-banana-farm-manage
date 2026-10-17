export function swipeStep({dx,dy,elapsed,startX,width}){
 if(startX<24||startX>width-24||elapsed>650||Math.abs(dx)<72||Math.abs(dx)<Math.abs(dy)*2)return 0
 return dx<0?1:-1
}
