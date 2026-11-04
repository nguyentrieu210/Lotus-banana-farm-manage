import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync,readdirSync,statSync} from 'node:fs'
import {join,relative} from 'node:path'
import {fileURLToPath} from 'node:url'
import {parse} from '@babel/parser'
import {parse as parseSfc} from '@vue/compiler-sfc'
import {GRID_APP_KEYS} from '../src/grid-app-keys.js'

const root=fileURLToPath(new URL('..',import.meta.url))
const types=join(root,'node_modules/ag-grid-community/dist/types/src')
// ColDef = AbstractColDef + ColDef (entities/colDef.d.ts) + IFilterDef (interfaces/iFilter.d.ts).
const declared=file=>[...readFileSync(join(types,file),'utf8').matchAll(/^\s{4}(\w+)\??:/gm)].map(m=>m[1])
const agKeys=new Set([...declared('entities/colDef.d.ts'),...declared('interfaces/iFilter.d.ts')])
// DataTable reads these itself and passes AG Grid the equivalent (tooltip / headerTooltip).
const dataTableKeys=new Set(['tooltipValueGetter','tooltipField','headerTooltipValueGetter'])

function sources(dir,out=[]){for(const f of readdirSync(dir)){const p=join(dir,f);if(statSync(p).isDirectory())sources(p,out);else if(/\.(vue|js)$/.test(f))out.push(p)}return out}
function scriptOf(file){
 const code=readFileSync(file,'utf8')
 if(!file.endsWith('.vue'))return code
 const {descriptor}=parseSfc(code)
 return (descriptor.scriptSetup?.content||'')+'\n'+(descriptor.script?.content||'')
}
// A column literal: an object with headerName, or a field plus a display option.
const isColumn=keys=>keys.includes('headerName')||(keys.includes('field')&&['valueFormatter','minWidth','flex','cellRenderer'].some(k=>keys.includes(k)))

test('every column literal uses AG Grid colDef keys or a stripped app flag (no #307 warnings)',()=>{
 const unknown=[]
 for(const file of sources(join(root,'src'))){
  const code=scriptOf(file)
  const ast=parse(code,{sourceType:'module',errorRecovery:true})
  const visit=node=>{
   if(!node||typeof node.type!=='string')return
   if(node.type==='ObjectExpression'){
    const keys=node.properties.filter(p=>p.type==='ObjectProperty'&&!p.computed).map(p=>p.key.name??p.key.value)
    if(isColumn(keys))for(const k of keys)if(k&&!agKeys.has(k)&&!GRID_APP_KEYS.includes(k)&&!dataTableKeys.has(k))unknown.push(relative(root,file).replace(/\\/g,'/')+':'+code.slice(0,node.start).split('\n').length+' '+k)
   }
   for(const v of Object.values(node)){if(Array.isArray(v))v.forEach(visit);else if(v&&typeof v.type==='string')visit(v)}
  }
  visit(ast.program)
 }
 assert.deepEqual(unknown,[],'Add app-only flags to src/grid-app-keys.js, or use an AG Grid colDef key')
})

test('DataTable strips the shared app flag list before AG Grid',()=>{
 const table=readFileSync(join(root,'src/components/DataTable.vue'),'utf8')
 assert.match(table,/import \{GRID_APP_KEYS\} from '\.\.\/grid-app-keys'/)
 assert.match(table,/for\(const k of GRID_APP_KEYS\)delete column\[k\]/)
 assert.ok(GRID_APP_KEYS.includes('sum'),'grid-totals reads col.sum')
})
