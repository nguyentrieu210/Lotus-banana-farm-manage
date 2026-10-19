import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
// mount.mjs must run before pinia pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,loadModule,mount,tick,h} from './support/mount.mjs'
import {createPinia,setActivePinia} from 'pinia'
import {pages,navGroups} from '../src/domain.js'

setActivePinia(createPinia())
const WorkspaceSidebar=await load('components/WorkspaceSidebar.vue')
const {useSession}=await loadModule('store.js')
const iconSource=readFileSync(new URL('../src/components/LotusIcon.vue',import.meta.url),'utf8')

test('every page sits in exactly one sidebar group with a real icon',()=>{
 const grouped=navGroups.flatMap(group=>group.items.map(([path])=>path))
 assert.deepEqual([...grouped].sort(),pages.map(([path])=>path).sort())
 assert.equal(new Set(grouped).size,grouped.length,'no page listed twice')
 for(const group of navGroups)for(const [path,icon] of group.items)
  assert.match(iconSource,new RegExp(`(^|[\\s{,])'?${icon}'?:\\[`,'m'),`${path} uses missing icon ${icon}`)
})

test('sidebar shows only permitted pages, grouped, without the duplicate stock link',async()=>{
 const session=useSession();Object.assign(session,{user:'lead@lotus',capabilities:{stock:true},commands:{},modules:{}})
 const nav=pages.filter(([path])=>['reports','kho','materials'].includes(path))
 const view=mount(WorkspaceSidebar,{nav,page:'kho'});await tick()
 const titles=[...view.root.querySelectorAll('.nav-group-title')].map(node=>node.textContent)
 assert.deepEqual(titles,['Tổng quan','Công việc hằng ngày','Kho & mua hàng'],'groups without permitted pages are hidden')
 const labels=[...view.root.querySelectorAll('nav button .nav-label')].map(node=>node.textContent)
 assert.deepEqual(labels,['Tổng quan','Vật tư theo việc','Quản lý kho'])
 assert.equal(view.root.querySelectorAll('nav button svg.lotus-icon').length,3,'each item has an icon, not a letter')
 assert.equal(view.root.querySelector('nav button.active .nav-label').textContent,'Quản lý kho')
 assert.equal(view.root.querySelector('nav button.active').getAttribute('aria-current'),'page')
 assert.equal([...view.root.querySelectorAll('.field-link')].some(link=>link.textContent.includes('Quản lý kho')),false)
 view.unmount()
})

test('clicking an item asks the shell to navigate; unknown pages still appear',async()=>{
 const session=useSession();Object.assign(session,{user:'u',capabilities:{},commands:{},modules:{}})
 const visited=[]
 const view=mount({render:()=>h(WorkspaceSidebar,{nav:[['work','Công việc'],['future-page','Màn mới']],page:'',onGo:path=>visited.push(path)})});await tick()
 const buttons=[...view.root.querySelectorAll('nav button')]
 assert.deepEqual(buttons.map(button=>button.querySelector('.nav-label').textContent),['Tiến độ công việc','Màn mới'])
 assert.equal(view.root.querySelector('.nav-group:last-child .nav-group-title').textContent,'Khác')
 buttons[0].click();await tick()
 assert.deepEqual(visited,['work'])
 view.unmount()
})
