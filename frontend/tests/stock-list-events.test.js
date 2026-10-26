import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

// v-on="{…}" prefixes "on" itself: keys written as onX become onOnX and the lists' events (open a document, change warehouse) are lost.
test('Kho lists forward their events by event name',()=>{
 const source=readFileSync(new URL('../src/StockApp.vue',import.meta.url),'utf8')
 const events=source.match(/const listEvents=\{([^}]*)\}/)[1]
 assert.doesNotMatch(events,/['"]?on[A-Z]/)
 assert.match(events,/'open-document':openDocument/)
 assert.match(events,/'update:warehouse':setWarehouse/)
})
