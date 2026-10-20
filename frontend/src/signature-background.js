// Paper background removal for signature photos, mirrored by lotus_farm/signature_image.py so the phone
// preview matches the stored PNG. The paper level is estimated locally (closing: max then min filter,
// then blur) so shadows and tinted light are not mistaken for ink; opacity follows how much darker a
// pixel is than the paper around it.
export const DEFAULT_STRENGTH=50
const TRANSPARENT_SHARE=0.02
const PAD=0.04

export function thresholds(strength=DEFAULT_STRENGTH){
 const value=Math.max(0,Math.min(100,Math.round(strength)))
 const low=140-value
 return [low,low+180]
}

function slide(src,w,h,radius,pick){
 // Separable running max/min over a square window.
 const tmp=new Float32Array(w*h),out=new Float32Array(w*h)
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){let v=src[y*w+x];for(let k=Math.max(0,x-radius);k<=Math.min(w-1,x+radius);k++)v=pick(v,src[y*w+k]);tmp[y*w+x]=v}
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){let v=tmp[y*w+x];for(let k=Math.max(0,y-radius);k<=Math.min(h-1,y+radius);k++)v=pick(v,tmp[k*w+x]);out[y*w+x]=v}
 return out
}

function blur(src,w,h,radius){
 let a=src
 for(let pass=0;pass<2;pass++){
  const tmp=new Float32Array(w*h),out=new Float32Array(w*h)
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){let s=0,n=0;for(let k=Math.max(0,x-radius);k<=Math.min(w-1,x+radius);k++){s+=a[y*w+k];n++}tmp[y*w+x]=s/n}
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){let s=0,n=0;for(let k=Math.max(0,y-radius);k<=Math.min(h-1,y+radius);k++){s+=tmp[k*w+x];n++}out[y*w+x]=s/n}
  a=out
 }
 return a
}

export function paperLevel(gray,w,h){
 const step=Math.max(1,Math.floor(Math.min(w,h)/200))
 const sw=Math.max(1,Math.floor(w/step)),sh=Math.max(1,Math.floor(h/step))
 const small=new Float32Array(sw*sh)
 for(let y=0;y<sh;y++)for(let x=0;x<sw;x++){let s=0,n=0;for(let j=y*step;j<Math.min(h,(y+1)*step);j++)for(let i=x*step;i<Math.min(w,(x+1)*step);i++){s+=gray[j*w+i];n++}small[y*sw+x]=n?s/n:255}
 const size=Math.max(3,Math.min(31,Math.floor(Math.min(sw,sh)/10)|1)),radius=(size-1)/2
 const closed=slide(slide(small,sw,sh,radius,Math.max),sw,sh,radius,Math.min)
 const smooth=blur(closed,sw,sh,Math.max(1,Math.round(size/6)))
 const level=new Float32Array(w*h)
 for(let y=0;y<h;y++){const fy=Math.min(sh-1,Math.max(0,(y+0.5)/step-0.5)),y0=Math.floor(fy),y1=Math.min(sh-1,y0+1),ty=fy-y0
  for(let x=0;x<w;x++){const fx=Math.min(sw-1,Math.max(0,(x+0.5)/step-0.5)),x0=Math.floor(fx),x1=Math.min(sw-1,x0+1),tx=fx-x0
   const top=smooth[y0*sw+x0]*(1-tx)+smooth[y0*sw+x1]*tx,bottom=smooth[y1*sw+x0]*(1-tx)+smooth[y1*sw+x1]*tx
   level[y*w+x]=top*(1-ty)+bottom*ty}}
 return level
}

// Mutates imageData (RGBA) and returns the stroke box {x,y,width,height}, or null when no ink is found.
export function removeBackground(imageData,strength=DEFAULT_STRENGTH){
 const {data,width:w,height:h}=imageData,count=w*h
 let clear=0
 for(let i=3;i<data.length;i+=4)if(data[i]<250)clear++
 if(clear<=TRANSPARENT_SHARE*count){
  const gray=new Float32Array(count)
  for(let p=0,i=0;p<count;p++,i+=4)gray[p]=0.299*data[i]+0.587*data[i+1]+0.114*data[i+2]
  const level=paperLevel(gray,w,h),[low,high]=thresholds(strength)
  for(let p=0,i=3;p<count;p++,i+=4){
   const darkness=(level[p]-gray[p])*1000/(level[p]+1)
   const alpha=Math.max(0,Math.min(255,(darkness-low)*255/(high-low)))
   data[i]=Math.min(data[i],Math.round(alpha))
  }
 }
 let x0=w,y0=h,x1=-1,y1=-1
 for(let y=0;y<h;y++)for(let x=0;x<w;x++)if(data[(y*w+x)*4+3]>40){if(x<x0)x0=x;if(x>x1)x1=x;if(y<y0)y0=y;if(y>y1)y1=y}
 if(x1<0)return null
 const pad=Math.max(2,Math.round(Math.max(x1-x0,y1-y0)*PAD))
 const x=Math.max(0,x0-pad),y=Math.max(0,y0-pad)
 return {x,y,width:Math.min(w,x1+pad+1)-x,height:Math.min(h,y1+pad+1)-y}
}
