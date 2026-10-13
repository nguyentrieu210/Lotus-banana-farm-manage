import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync,existsSync} from 'node:fs'

const file=path=>new URL('../'+path,import.meta.url)
const read=path=>readFileSync(file(path),'utf8')

test('AG Grid packages are pinned consistently with npm lock',()=>{
  const pkg=JSON.parse(read('package.json'))
  const lock=JSON.parse(read('package-lock.json'))
  for(const name of ['ag-grid-community','ag-grid-vue3']){
    assert.equal(pkg.dependencies[name],'36.2.0')
    assert.equal(lock.packages[''].dependencies[name],pkg.dependencies[name])
    assert.equal(lock.packages['node_modules/'+name].version,pkg.dependencies[name])
    assert.ok(lock.packages['node_modules/'+name].integrity.startsWith('sha512-'))
  }
})
test('shadcn-vue registry configuration uses JS, Tailwind v3, and matching dependencies',()=>{
  const cfg=JSON.parse(read('components.json'))
  const pkg=JSON.parse(read('package.json'))
  const lock=JSON.parse(read('package-lock.json'))
  assert.equal(cfg.typescript,false)
  assert.equal(cfg.style,'new-york')
  assert.equal(cfg.tailwind.css,'src/shadcn.css')
  assert.equal(cfg.tailwind.config,'tailwind.config.js')
  assert.equal(cfg.aliases.ui,'@/components/ui')
  assert.match(pkg.scripts['ui:add'],/shadcn-vue@1\.0\.3 add/)
  for(const name of ['class-variance-authority','clsx','tailwind-merge','reka-ui']){
    assert.equal(pkg.dependencies[name],lock.packages[''].dependencies[name])
    assert.equal(lock.packages['node_modules/'+name].version,pkg.dependencies[name])
    assert.match(lock.packages['node_modules/'+name].integrity,/^sha512-/)
  }
  assert.equal(pkg.devDependencies['tailwindcss-animate'],lock.packages[''].devDependencies['tailwindcss-animate'])
  assert.match(read('tailwind.config.js'),/tailwindcss-animate/)
  assert.match(read('vite.config.js'),/fileURLToPath/)
  assert.match(read('src/shadcn.css'),/@tailwind utilities/)
  for(const folder of ['button','input','textarea','card','badge','skeleton','separator']){
    assert.ok(existsSync(file('src/components/ui/'+folder+'/index.js')),folder+' registry component should be available')
  }
  assert.ok(!existsSync(file('src/components/ui/Button.vue')),'remove the bespoke Button')
})
test('main pages use shadcn-vue Button and still keep Frappe API provider',()=>{
  const main=read('src/App.vue')
  const quick=read('src/AssignApp.vue')
  const form=read('src/components/SchemaForm.vue')
  for(const source of [main,quick,form]){
    assert.match(source,/import \{Button as UiButton\}/)
    assert.equal((source.match(/<UiButton\b/g)||[]).length,(source.match(/<\/UiButton>/g)||[]).length)
  }
  assert.match(main,/<FrappeUIProvider>/)
  assert.match(read('src/main.js'),/import '\.\/shadcn\.css'/)
  assert.match(read('src/assign-main.js'),/import '\.\/shadcn\.css'/)
})
test('shared grid keeps open-row event and mobile record view',()=>{
  const source=read('src/components/OpsList.vue')
  assert.match(source,/from 'ag-grid-vue3'/)
  assert.match(source,/AllCommunityModule/)
  assert.match(source,/@row-clicked="onRowClicked"/)
  assert.match(source,/emit\('open',event\.data\)/)
  assert.match(source,/lotus-mobile-records/)
})
