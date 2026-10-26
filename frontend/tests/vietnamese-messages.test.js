import test from 'node:test'
import assert from 'node:assert/strict'
import {readdirSync,readFileSync,statSync} from 'node:fs'
import {join} from 'node:path'

// Server messages reach users verbatim (frappe.throw / msgprint, rule errors). They must be Vietnamese.
const root=new URL('../../lotus_farm/',import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,'$1')
const files=[]
;(function walk(dir){for(const name of readdirSync(dir)){const path=join(dir,name);if(statSync(path).isDirectory()){if(!['tests','__pycache__','public','node_modules'].includes(name))walk(path)}else if(name.endsWith('.py')&&!name.startsWith('test_')&&!/seed/.test(name))files.push(path)}})(root)
const call=/(frappe\.(?:throw|msgprint)|raise (?:RuleError|ForecastInputError|MapBundleError))\(\s*(?:_\()?f?(["'])((?:\\.|(?!\2).)*)\2/g
const vietnamese=/[À-ỹĐđ]/
test('server messages shown to users are written in Vietnamese',()=>{
 assert.ok(files.length>50,'scanned '+files.length+' server files')
 const english=[]
 for(const file of files){
  const source=readFileSync(file,'utf8')
  for(const match of source.matchAll(call)){
   const text=match[3]
   if(!vietnamese.test(text)&&/[A-Za-z]{3,} [A-Za-z]{3,}/.test(text))english.push(file.slice(root.length)+': '+text.slice(0,80))
  }
 }
 assert.deepEqual(english,[])
})
