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
