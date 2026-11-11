import {computed,ref} from 'vue'
// Display mode and density, shared by desktop and phone (spec 004, FR-003, FR-013, FR-025, FR-047).
// Saved keys stay as before so nobody loses a choice: 'lotus-theme' ('light'|'dark') and 'lotus-desktop-density'
// ('compact'|'comfortable'). New: 'lotus-outdoor' ('1'|'0'), the high-contrast light mode for phones in the sun.
// <html> gets .dark or .lotus-outdoor (never both), data-theme, data-mode and data-density; lotus-tokens.css does the rest.
export const UI_KEYS=Object.freeze({theme:'lotus-theme',outdoor:'lotus-outdoor',density:'lotus-desktop-density'})
export const DENSITIES=Object.freeze(['compact','comfortable'])
export const MODES=Object.freeze(['light','dark','outdoor'])

const browserStorage=()=>{try{return typeof localStorage==='undefined'?null:localStorage}catch{return null}}
const get=(storage,key)=>{try{return storage?.getItem(key)??null}catch{return null}}
export function writeUiPref(storage,key,value){try{storage?.setItem(key,value)}catch{}}

// theme is null when the person never chose one (phones then follow the system).
export function readUiPrefs(storage=browserStorage()){
 const theme=get(storage,UI_KEYS.theme)
 return {
  theme:theme==='dark'||theme==='light'?theme:null,
  outdoor:get(storage,UI_KEYS.outdoor)==='1',
  density:get(storage,UI_KEYS.density)==='comfortable'?'comfortable':'compact',
 }
}

// Outdoor wins over dark. Desktop uses the saved theme (light by default); phones follow the system theme
// unless outdoor is on, as they did before.
export function resolveUiMode(prefs,{followSystem=false,systemDark=false,allowOutdoor=true}={}){
 if(allowOutdoor&&prefs.outdoor)return 'outdoor'
 if(followSystem)return systemDark?'dark':'light'
 return prefs.theme==='dark'?'dark':'light'
}

export function applyUiMode(mode,density,root=typeof document==='undefined'?null:document.documentElement){
 if(!root)return
 const m=MODES.includes(mode)?mode:'light'
 root.classList.toggle('dark',m==='dark')
 root.classList.toggle('lotus-outdoor',m==='outdoor')
 root.dataset.theme=m==='dark'?'dark':'light'
 root.dataset.mode=m
 if(density)root.dataset.density=DENSITIES.includes(density)?density:'compact'
 root.style.colorScheme=m==='dark'?'dark':'light'
}

// One shared state per page. Each app calls useUiMode once with its context; later calls reuse the state.
const prefs=ref(readUiPrefs())
const context=ref({followSystem:false,allowOutdoor:false})
const systemDark=ref(false)
const mode=computed(()=>resolveUiMode(prefs.value,{...context.value,systemDark:systemDark.value}))
const density=computed(()=>prefs.value.density)
// Read-only views for components that follow the choice without owning it (DataTable, charts).
export {mode as uiMode,density as uiDensity}
let started=false
function paint(){applyUiMode(mode.value,density.value)}
function start(){
 if(started||typeof window==='undefined')return
 started=true
 const scheme=window.matchMedia?.('(prefers-color-scheme: dark)')
 systemDark.value=!!scheme?.matches
 scheme?.addEventListener?.('change',event=>{systemDark.value=event.matches;paint()})
 // Another tab changed a choice.
 window.addEventListener('storage',event=>{if(Object.values(UI_KEYS).includes(event.key)){prefs.value=readUiPrefs();paint()}})
}

export function useUiMode({followSystem,allowOutdoor}={}){
 if(followSystem!==undefined||allowOutdoor!==undefined)context.value={followSystem:!!followSystem,allowOutdoor:!!allowOutdoor}
 start()
 paint()
 const store=browserStorage()
 function setTheme(value){
  const theme=value==='dark'?'dark':'light'
  prefs.value={...prefs.value,theme,outdoor:false}
  writeUiPref(store,UI_KEYS.theme,theme);writeUiPref(store,UI_KEYS.outdoor,'0');paint()
 }
 function toggleTheme(){setTheme(mode.value==='dark'?'light':'dark')}
 function setOutdoor(on){prefs.value={...prefs.value,outdoor:!!on};writeUiPref(store,UI_KEYS.outdoor,on?'1':'0');paint()}
 function setDensity(value){
  if(!DENSITIES.includes(value))return
  prefs.value={...prefs.value,density:value};writeUiPref(store,UI_KEYS.density,value);paint()
 }
 return {mode,density,dark:computed(()=>mode.value==='dark'),outdoor:computed(()=>mode.value==='outdoor'),setTheme,toggleTheme,setOutdoor,setDensity}
}
