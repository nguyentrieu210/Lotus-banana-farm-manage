// Uses the same isolated Happy DOM installation as the mobile audit.
import assert from 'node:assert/strict'
import {fileURLToPath,pathToFileURL} from 'node:url'
const {Window}=await import(process.env.MOBILE_UX_HAPPY_DOM||'happy-dom')
const project=fileURLToPath(new URL('../frontend/',import.meta.url))
const window=new Window({url:'http://localhost:8080/lotus/kho',width:1440,height:900})
const media=new window.EventTarget();media.matches=true
window.matchMedia=()=>media
for(const name of ['window','document','navigator','Element','HTMLElement','SVGElement','Node','Event','CustomEvent','localStorage'])Object.defineProperty(globalThis,name,{value:window[name],configurable:true})
const {createApp,h,nextTick}=await import(pathToFileURL(project+'node_modules/vue/dist/vue.runtime.esm-bundler.js'))
const {useDesktopWorkspace}=await import(pathToFileURL(project+'src/use-desktop-workspace.js'))
const mount=()=>{
 let state
 const target=document.createElement('div');document.body.append(target)
 const app=createApp({setup(){state=useDesktopWorkspace();return()=>h('div',['comfortable','compact'].map(value=>h('button',{'aria-pressed':state.density.value===value,onClick:()=>state.setDensity(value)},value)))}})
 app.mount(target)
 return {app,target,get state(){return state}}
}
let harness=mount()
assert.equal(harness.state.gridDensity.value,'comfortable')
assert.ok(document.documentElement.classList.contains('lotus-desktop-page'))
assert.equal(harness.target.querySelectorAll('button[aria-pressed=true]').length,1)
harness.target.querySelectorAll('button')[1].click();await nextTick()
assert.equal(harness.state.gridDensity.value,'compact')
assert.equal(localStorage.getItem('lotus-desktop-density'),'compact')
assert.equal(harness.target.querySelectorAll('button')[1].getAttribute('aria-pressed'),'true')
harness.state.setDensity('invalid');assert.equal(harness.state.density.value,'compact')
media.matches=false;media.dispatchEvent(Object.assign(new window.Event('change'),{matches:false}));await nextTick()
assert.equal(harness.state.gridDensity.value,null)
assert.ok(!document.documentElement.classList.contains('lotus-desktop-page'))
media.matches=true;media.dispatchEvent(Object.assign(new window.Event('change'),{matches:true}));await nextTick()
assert.equal(harness.state.gridDensity.value,'compact')
harness.app.unmount();assert.ok(!document.documentElement.classList.contains('lotus-desktop-page'))
harness=mount();assert.equal(harness.state.density.value,'compact');harness.app.unmount()
localStorage.setItem('lotus-desktop-density','unknown')
harness=mount();assert.equal(harness.state.density.value,'comfortable');harness.app.unmount()
console.log('PASS: density selection, persistence, invalid preference, viewport transition and theme cleanup')
