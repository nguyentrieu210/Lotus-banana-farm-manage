import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,ref} from './support/mount.mjs'

const DataTable=await load('components/DataTable.vue')
const cols=[{field:'name',headerName:'Nhân viên'}]
const settle=async()=>{await tick();await tick()}

test('AG Grid may be rebuilt rapidly without calling destroyed API #26',async()=>{
 const changing=ref([{name:'A'},{name:'B'},{name:'C'}])
 const Wrapper={setup(){return ()=>h(DataTable,{rows:changing.value,columns:cols,rowKey:'name',pageSize:2,storageKey:'ag-lifecycle-26'})}}
 const errors=[]
 const originalError=console.error,originalWarn=console.warn
 const capture=(...args)=>{const text=args.map(String).join(' ');if(/AG Grid.*#26|grid has been destroyed|cannot be called as the grid has been destroyed/i.test(text))errors.push(text)}
 let view
 console.error=(...args)=>{capture(...args);originalError(...args)}
 console.warn=(...args)=>{capture(...args);originalWarn(...args)}
 try{
  view=mount(Wrapper)
  await settle()
  changing.value=[{name:'D'},{name:'E'},{name:'F'}]
  await settle()
  changing.value=[]
  await settle()
  changing.value=[{name:'G'},{name:'H'},{name:'I'}]
  await settle()
  view.unmount();view=null
  await settle()
  assert.deepEqual(errors,[])
 }finally{view?.unmount();console.error=originalError;console.warn=originalWarn}
})
