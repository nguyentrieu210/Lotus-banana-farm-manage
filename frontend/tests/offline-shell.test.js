import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {runInNewContext} from 'node:vm'
const code=readFileSync(new URL('../../lotus_farm/public/lotus-worker.js',import.meta.url),'utf8').replace('__LOTUS_ASSETS__','[]').replace('__LOTUS_VERSION__','"test"')
function worker(){const events={};runInNewContext(code,{URL,location:{origin:'http://localhost'},self:{addEventListener:(name,fn)=>events[name]=fn},fetch:()=>Promise.reject(new Error('offline')),caches:{open:async()=>({match:async key=>key})}});return events.fetch}
test('offline navigation keeps the correct app for each entry',async()=>{for(const [route,entry] of [['/lotus/kho','stock'],['/lotus/cham-cong','timekeeping'],['/lotus/giao-viec/','assign'],['/lotus/cong-viec/','farm-work'],['/lotus/today','index']]){let response;worker()({request:{url:'http://localhost'+route,method:'GET',mode:'navigate'},respondWith:value=>response=value});assert.equal(await response,'/assets/lotus_farm/frontend/'+entry+'.html')}})
test('private APIs and native print pages never receive a cached app shell',()=>{for(const route of ['/api/method/test','/lotus/in-phieu','/lotus/in-cong/','/private/files/test.pdf']){let intercepted=false;worker()({request:{url:'http://localhost'+route,method:'GET',mode:'navigate'},respondWith:()=>intercepted=true});assert.equal(intercepted,false)}})
