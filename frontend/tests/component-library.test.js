import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync,existsSync} from 'node:fs'
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8')

test('shared primitives exist and are built on reka-ui',()=>{
 for(const name of ['button','input','select','textarea','form-field','combobox','date-picker','dropdown-menu','tooltip','popover','sheet','pagination','skeleton','toast']){
  assert.ok(existsSync(new URL('../src/components/ui/'+name+'/index.js',import.meta.url)),name)
 }
 for(const file of ['combobox/Combobox.vue','date-picker/DatePicker.vue','date-picker/DateRangePicker.vue','toast/Toaster.vue','sheet/Sheet.vue','pagination/Pagination.vue','tooltip/Tooltip.vue'])
  assert.match(read('src/components/ui/'+file),/from 'reka-ui'/,file)
})

test('one picker implementation: legacy pickers only wrap Combobox',()=>{
 for(const file of ['src/components/SearchSelect.vue','src/components/LinkPicker.vue']){
  const src=read(file)
  assert.match(src,/<Combobox /,file)
  assert.doesNotMatch(src,/getBoundingClientRect|showPopover|addEventListener\('pointerdown'/,file+' must not position its own popup')
 }
})

test('topbar menus use DropdownMenu and icon buttons carry a tooltip',()=>{
 const bar=read('src/components/WorkspaceBar.vue')
 assert.doesNotMatch(bar,/<details/)
 assert.match(bar,/<DropdownMenuContent/)
 assert.match(bar,/<Tooltip /)
 assert.doesNotMatch(read('src/compact.css'),/\.workspace-bar button\[aria-expanded\]/,'menu triggers must not be styled as the sidebar toggle')
})

test('showcase is a dev-only page, never part of the production build',()=>{
 assert.ok(existsSync(new URL('../showcase.html',import.meta.url)))
 assert.doesNotMatch(read('vite.config.js'),/showcase/)
})
