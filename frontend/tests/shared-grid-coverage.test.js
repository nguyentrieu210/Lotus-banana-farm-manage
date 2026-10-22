import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync,readdirSync} from 'node:fs'
import {join,relative} from 'node:path'
import {fileURLToPath} from 'node:url'

const source=fileURLToPath(new URL('../src/',import.meta.url))
function vueFiles(directory){
 return readdirSync(directory,{withFileTypes:true}).flatMap(entry=>{
  const path=join(directory,entry.name)
  return entry.isDirectory()?vueFiles(path):entry.name.endsWith('.vue')?[path]:[]
 })
}
test('desktop Lotus screens use the shared AG Grid instead of native HTML tables',()=>{
 const nativeTables=vueFiles(source).filter(file=>/<table(?:\s|>)/i.test(readFileSync(file,'utf8')))
 assert.deepEqual(nativeTables.map(file=>relative(source,file)),[],'convert native desktop tables to DataTable, preserving editors and commands')
 const dataTable=readFileSync(join(source,'components','DataTable.vue'),'utf8')
 assert.match(dataTable,/AgGridVue/)
})