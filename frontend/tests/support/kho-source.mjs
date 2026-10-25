import {readFileSync,readdirSync} from 'node:fs'
// The Kho workspace is split into StockApp.vue (shell), components/stock/*.vue (views and forms) and stock-columns.js.
// Source-level tests read all of it as one text so they check the rule, not which file holds it.
const src=new URL('../../src/',import.meta.url)
export const khoFiles=['StockApp.vue','stock-columns.js','stock-navigation.js',...readdirSync(new URL('components/stock/',src)).map(f=>'components/stock/'+f)]
export function khoSource(){return khoFiles.map(f=>'// FILE '+f+'\n'+readFileSync(new URL(f,src),'utf8')).join('\n')}
export function khoFile(name){return readFileSync(new URL(name,src),'utf8')}
