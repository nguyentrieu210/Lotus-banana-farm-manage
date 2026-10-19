import test from 'node:test'
import assert from 'node:assert/strict'
import {loadColumnWidths,saveColumnWidths} from '../src/grid-state.js'

test('column widths persist per table and ignore junk',()=>{
 const store=new Map()
 globalThis.localStorage={getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,String(v))}
 saveColumnWidths('stock',[{colId:'item',width:241.6,sort:'asc'},{colId:'qty',width:0},{width:90}])
 assert.deepEqual(loadColumnWidths('stock'),[{colId:'item',width:242,flex:null}])
 assert.deepEqual(loadColumnWidths('other'),[])
 store.set('lotus-grid-widths:broken','{not json')
 assert.deepEqual(loadColumnWidths('broken'),[])
 delete globalThis.localStorage
 assert.deepEqual(loadColumnWidths('stock'),[],'private mode without storage still works')
})

test('named table views are saved per table, replaced by name and removable',async()=>{
 const {loadViews,saveView,deleteView}=await import('../src/grid-state.js')
 const store=new Map()
 globalThis.localStorage={getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,String(v))}
 saveView('stock',{name:'Kho A',filters:{warehouse:['Kho A']},sort:[]})
 saveView('stock',{name:'Kho A',filters:{warehouse:['Kho A','Kho B']},sort:[{colId:'qty',sort:'desc'}]})
 assert.equal(loadViews('stock').length,1,'same name replaces')
 assert.deepEqual(loadViews('stock')[0].filters.warehouse,['Kho A','Kho B'])
 assert.deepEqual(loadViews('other'),[])
 assert.deepEqual(deleteView('stock','Kho A'),[])
 delete globalThis.localStorage
})
