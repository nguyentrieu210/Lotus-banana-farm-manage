import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8')

test('AG Grid dependencies are pinned and consistent with npm ci lockfile',()=>{
  const pkg=JSON.parse(read('package.json'))
  const lock=JSON.parse(read('package-lock.json'))
  for(const name of ['ag-grid-community','ag-grid-vue3']){
    assert.equal(pkg.dependencies[name],'36.2.0')
    assert.equal(lock.packages[''].dependencies[name],pkg.dependencies[name])
    assert.equal(lock.packages['node_modules/'+name].version,pkg.dependencies[name])
    assert.ok(lock.packages['node_modules/'+name].integrity.startsWith('sha512-'))
  }
  for(const name of ['ag-stack','ag-charts-types']){
    assert.ok(lock.packages['node_modules/'+name]?.integrity)
  }
})
test('shared list uses AG Grid but preserves open-row event and mobile view',()=>{
  const source=read('src/components/OpsList.vue')
  assert.match(source,/from 'ag-grid-vue3'/)
  assert.match(source,/AllCommunityModule/)
  assert.match(source,/@row-clicked="onRowClicked"/)
  assert.match(source,/emit\('open',event\.data\)/)
  assert.match(source,/lotus-mobile-records/)
})
test('Attio-inspired theme and shadcn-style Vue button are wired to both entries',()=>{
  assert.match(read('src/main.js'),/import '\.\/attio\.css'/)
  assert.match(read('src/assign-main.js'),/import '\.\/assign-attio\.css'/)
  assert.match(read('src/App.vue'),/import UiButton from '\.\/components\/ui\/Button\.vue'/)
  assert.match(read('src/App.vue'),/<FrappeUIProvider>/)
  assert.match(read('src/AssignApp.vue'),/<UiButton/)
  assert.match(read('src/attio.css'),/\.lotus-button--outline/)
})
