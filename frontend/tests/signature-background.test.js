import test from 'node:test'
import assert from 'node:assert/strict'
import {removeBackground,thresholds} from '../src/signature-background.js'

// Tinted, shadowed paper (150 on the left .. 230 on the right) with a dark blue horizontal stroke.
function photo(w=300,h=150,{alpha=255,paper=true}={}){
 const data=new Uint8ClampedArray(w*h*4)
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){const i=(y*w+x)*4,shade=Math.round(150+80*x/w),ink=y>=70&&y<78&&x>=40&&x<260
  data[i]=ink?30:paper?shade+12:0;data[i+1]=ink?40:paper?shade+6:0;data[i+2]=ink?120:paper?shade-10:0;data[i+3]=ink?255:alpha}
 return {data,width:w,height:h}
}
const alphaAt=(img,x,y)=>img.data[(y*img.width+x)*4+3]

test('shadowed tinted paper turns transparent while the stroke stays opaque',()=>{
 const img=photo(),box=removeBackground(img)
 assert.equal(alphaAt(img,5,5),0,'shadowed corner')
 assert.equal(alphaAt(img,295,140),0,'lit corner')
 assert.equal(alphaAt(img,150,74),255,'pen stroke')
 assert.ok(box.width<300&&box.height<40,'box hugs the stroke')
})

test('an already transparent drawing is only trimmed, and blank paper has no box',()=>{
 const drawn=photo(300,150,{alpha:0,paper:false}),box=removeBackground(drawn)
 assert.equal(alphaAt(drawn,150,74),255)
 assert.ok(box.height<40)
 const blank={data:new Uint8ClampedArray(200*100*4).map((_,i)=>i%4===3?255:220),width:200,height:100}
 assert.equal(removeBackground(blank),null)
})

test('thresholds match the server constants',()=>{
 assert.deepEqual(thresholds(50),[90,270])
 assert.ok(thresholds(100)[0]<thresholds(0)[0])
})
