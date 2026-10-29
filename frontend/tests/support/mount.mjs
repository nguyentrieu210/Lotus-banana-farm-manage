// Mount real .vue components in Node for tests: Happy DOM window + SFC compiled on the fly (no Vite).
// Same approach as tools/verify_warehouse_mobile_dom.mjs, shared so `npm test` can exercise behaviour, not just source text.
import fs from 'node:fs'
import path from 'node:path'
import {pathToFileURL,fileURLToPath} from 'node:url'
import {Window} from 'happy-dom'

const project=fileURLToPath(new URL('../../',import.meta.url))
// Test files run in separate Node processes. Do not let concurrent SFC compilation truncate a shared module.
const runtime=path.join(project,'node_modules/.lotus-mount',String(process.pid))
fs.mkdirSync(runtime,{recursive:true})

export const window=new Window({url:'http://localhost:8080/lotus',width:1440,height:900})
for(const name of ['window','document','Document','ShadowRoot','navigator','location','Element','HTMLElement','HTMLInputElement','HTMLTextAreaElement','HTMLButtonElement','HTMLSelectElement','HTMLDialogElement','SVGElement','Node','NodeFilter','Event','CustomEvent','KeyboardEvent','MouseEvent','getComputedStyle','requestAnimationFrame','cancelAnimationFrame','localStorage','ResizeObserver','MutationObserver','IntersectionObserver','PointerEvent','FocusEvent'])
 Object.defineProperty(globalThis,name,{value:typeof window[name]==='function'&&['getComputedStyle','requestAnimationFrame','cancelAnimationFrame'].includes(name)?window[name].bind(window):window[name],configurable:true})
window.HTMLElement.prototype.scrollIntoView=function(){}
globalThis.history??=window.history

const {parse,compileScript}=await import(pathToFileURL(path.join(project,'node_modules/@vue/compiler-sfc/dist/compiler-sfc.esm-browser.js')))
// One Vue instance for the compiled components and for libraries such as reka-ui (both resolve the bare 'vue').
const vue=await import('vue')
const generated=new Map()

// Compile a .vue/.js file and its relative imports into runtime/, rewriting imports to absolute file URLs.
export function compile(filename){
 const absolute=path.resolve(filename)
 if(generated.has(absolute))return generated.get(absolute)
 const out=path.join(runtime,path.relative(project,absolute).replace(/[\\/]/g,'__').replace(/\.vue$/,'.mjs').replace(/\.js$/,'.mjs'))
 generated.set(absolute,out)
 let code=fs.readFileSync(absolute,'utf8')
 code=code.replace(/^import ['"][^'"]*\.css['"];?\s*$/gm,'')
 if(absolute.endsWith('.vue')){const {descriptor}=parse(code);code=descriptor.scriptSetup||descriptor.script?compileScript(descriptor,{id:path.basename(absolute),inlineTemplate:true}).content:'export default {}'}
 // Vite-only build flags have no meaning outside Vite; tests run as a production build.
 code=code.replace(/import\.meta\.env/g,'({DEV:false,PROD:true,MODE:"test"})')
 // Both `import x from './y'` and side-effect `import './y.js'` must resolve to compiled files.
 code=code.replace(/(from\s+|^import\s+)(['"])(\.[^'"]+|@\/[^'"]+)\2/gm,(match,keyword,quote,spec)=>{
  let target=spec.startsWith('@/')?path.join(project,'src',spec.slice(2)):path.resolve(path.dirname(absolute),spec)
  if(!path.extname(target))target=fs.existsSync(target+'.js')?target+'.js':path.join(target,'index.js')
  if(target.endsWith('.css'))return keyword+'"data:text/javascript,"'
  return keyword+JSON.stringify(pathToFileURL(compile(target)).href)
 })
 fs.writeFileSync(out,code)
 return out
}
// Whole module, same instance the compiled components import (e.g. shared state in use-toast.js).
export async function loadModule(relativeToSrc){return import(pathToFileURL(compile(path.join(project,'src',relativeToSrc))))}
export async function load(relativeToSrc){return (await loadModule(relativeToSrc)).default}
export const {createApp,h,nextTick,ref}=vue
export const document=window.document
export async function tick(){await nextTick();await new Promise(resolve=>setTimeout(resolve,20));await nextTick()}
export function mount(component,props={},slots){
 const root=document.createElement('div');document.body.append(root)
 const app=createApp({render:()=>h(component,props,slots)});const vm=app.mount(root)
 return {root,app,vm,unmount:()=>{app.unmount();root.remove()}}
}
