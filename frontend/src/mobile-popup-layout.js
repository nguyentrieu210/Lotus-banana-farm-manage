// Coordinates use the layout viewport; visualViewport accounts for mobile keyboards.
export function popupLayout(anchor, viewport, {header=0, footer=0, maxHeight=300}={}){
 const gap=6, edge=8
 const leftEdge=viewport.left||0, topEdge=Math.max(viewport.top||0,header)+edge
 const bottom=(viewport.top||0)+viewport.height-footer-edge
 const below=Math.max(0,bottom-anchor.bottom-gap)
 const above=Math.max(0,anchor.top-gap-topEdge)
 const up=below<Math.min(180,maxHeight)&&above>below
 const height=Math.max(0,Math.min(maxHeight,up?above:below))
 const width=Math.min(anchor.width,viewport.width-edge*2)
 const left=Math.max(leftEdge+edge,Math.min(anchor.left,leftEdge+viewport.width-width-edge))
 return {up,left,width,maxHeight:height,top:up?anchor.top-gap-height:anchor.bottom+gap}
}
