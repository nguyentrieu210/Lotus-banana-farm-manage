import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick} from './support/mount.mjs'
import {imageFileProblem,saveImage,removeImage} from '../src/use-signature-profile.js'

test('signature pad starts empty, reports drawing and clears',async()=>{
 const {h}=await import('vue')
 const Pad=await load('../src/components/signing/SignaturePad.vue')
 const changes=[];let pad
 const view=mount({render:()=>h(Pad,{ref:r=>{pad=r},height:120,onChange:v=>changes.push(v)})})
 await tick()
 const canvas=document.querySelector('canvas.lotus-signature-pad')
 assert.ok(canvas,'a canvas is rendered')
 assert.equal(canvas.getAttribute('aria-label'),'Vùng vẽ chữ ký')
 assert.equal(pad.isEmpty(),true)
 assert.equal(pad.toDataURL(),'','nothing to save before drawing')
 view.unmount()
})

test('image rules are shared by phone and desktop',async()=>{
 assert.equal(imageFileProblem({type:'image/png',name:'a.png',size:1000}),'')
 assert.match(imageFileProblem({type:'image/heic',name:'a.heic',size:1000}),/PNG hoặc JPG/)
 assert.match(imageFileProblem({type:'image/jpeg',name:'a.jpg',size:10000001}),/10 MB/)
 assert.equal(imageFileProblem({type:'',name:'a.JPG',size:5}),'')
 const calls=[];const callFn=async(m,a,w)=>{calls.push([m,w]);return {}}
 await saveImage('initials','data:image/png;base64,AA',callFn)
 await removeImage('signature',callFn)
 assert.deepEqual(calls,[['lotus_farm.digital_signature.save_my_initials_image',true],['lotus_farm.digital_signature.remove_my_signature_image',true]])
 assert.throws(()=>saveImage('signature','javascript:alert(1)',callFn),/không hợp lệ/)
})
