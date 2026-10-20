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
const {sidebarCollapsed}=await loadModule('workspace.js')
const iconSource=readFileSync(new URL('../src/components/LotusIcon.vue',import.meta.url),'utf8')

test('every page sits in exactly one sidebar group with a real icon',()=>{
 const grouped=navGroups.flatMap(group=>group.items.map(([path])=>path))
 assert.deepEqual([...grouped].sort(),pages.map(([path])=>path).sort())
 assert.equal(new Set(grouped).size,grouped.length,'no page listed twice')
 for(const group of navGroups)for(const [path,icon] of group.items)
  assert.match(iconSource,new RegExp(`(^|[\\s{,])'?${icon}'?:\\[`,'m'),`${path} uses missing icon ${icon}`)
})

test('sidebar orders the actual business areas and respects permitted pages',async()=>{
 const session=useSession();Object.assign(session,{user:'lead@lotus',capabilities:{stock:true},commands:{},modules:{}})
 const nav=pages.filter(([path])=>['reports','kho','materials'].includes(path))
 const view=mount(WorkspaceSidebar,{nav,page:'kho'});await tick()
 const parents=[...view.root.querySelectorAll('.nav-parent .nav-label')].map(node=>node.textContent)
 assert.deepEqual(parents,['Tổng quan','Điều hành công việc','Kho & mua hàng'])
 const labels=[...view.root.querySelectorAll('nav button .nav-label')].map(node=>node.textContent)
 assert.deepEqual(labels,parents,'single-item groups do not duplicate their screens')
 assert.equal(view.root.querySelectorAll('.nav-parent svg.lotus-icon').length,3,'each area has an icon')
 assert.equal(view.root.querySelector('nav button.active .nav-label').textContent,'Kho & mua hàng')
 assert.equal(view.root.querySelector('nav button.active').getAttribute('aria-current'),'page')
 assert.equal(view.root.querySelector('.nav-sub-link')?.textContent.trim(),'Mua hàng')
 assert.equal(view.root.querySelector('.nav-sub-link')?.getAttribute('href'),'/buying')
 view.unmount()
})

test('sidebar parent navigates to its existing route; nested pages expand and can be selected',async()=>{
 const session=useSession();Object.assign(session,{user:'u',capabilities:{},commands:{},modules:{}})
 const visited=[]
 const nav=[['reports','Báo cáo'],['alerts','Cảnh báo'],['map','Bản đồ'],['work','Công việc'],['labor','Bố trí nhân công']]
 const view=mount({render:()=>h(WorkspaceSidebar,{nav,page:'work',onGo:path=>visited.push(path)})});await tick()
 const parents=[...view.root.querySelectorAll('.nav-parent .nav-label')].map(node=>node.textContent)
 assert.deepEqual(parents,['Tổng quan','Bản đồ','Điều hành công việc'])
 assert.equal(view.root.querySelector('.nav-group-current .nav-submenu button .nav-label')?.textContent,'Bố trí nhân công')
 view.root.querySelector('.nav-group-current .nav-submenu button').click();await tick()
 assert.deepEqual(visited,['labor'])
 const collapsed=view.root.querySelector('.nav-group-current .nav-toggle')
 collapsed.click();await tick()
 assert.equal(collapsed.getAttribute('aria-expanded'),'false')
 assert.equal(view.root.querySelector('.nav-group-current .nav-submenu').style.display,'none')
 view.root.querySelector('.nav-group-current .nav-parent').click();await tick()
 assert.deepEqual(visited,['labor','work'])
 view.unmount()
})

test('unknown permitted pages remain reachable and group changes do not create routes',async()=>{
 const session=useSession();Object.assign(session,{user:'u',capabilities:{stock:false},commands:{},modules:{}})
 const visited=[]
 const view=mount({render:()=>h(WorkspaceSidebar,{nav:[['work','Công việc'],['future-page','Màn mới']],page:'',onGo:path=>visited.push(path)})});await tick()
 const parents=[...view.root.querySelectorAll('.nav-parent .nav-label')].map(node=>node.textContent)
 assert.deepEqual(parents,['Điều hành công việc','Khác'])
 assert.equal([...view.root.querySelectorAll('.nav-sub-link')].length,0,'no purchasing shortcut without stock permission')
 view.root.querySelector('.nav-parent').click();await tick()
 assert.deepEqual(visited,['work'])
 view.unmount()
})

test('HR exposes all eight destinations in order with a non-interactive setup label',async()=>{
 const session=useSession();Object.assign(session,{user:'manager',capabilities:{hr:true,hr_manage:true,attendance:true},commands:{},modules:{}})
 const visited=[]
 const view=mount(WorkspaceSidebar,{nav:pages.filter(([p])=>['nhan-su','cham-cong'].includes(p)),page:'nhan-su',hrView:'devices',onGo:(...args)=>visited.push(args)})
 await tick()
 assert.deepEqual([...view.root.querySelectorAll('.nav-child .nav-label')].map(n=>n.textContent),['Hồ sơ nhân viên','Tuyển dụng','Tiếp nhận','Chấm công','Kỳ công & bảng lương','Cơ cấu & chức danh','Máy chấm công','Nhập dữ liệu nhân sự'])
 const heading=view.root.querySelector('.nav-subsection');assert.equal(heading.textContent,'Thiết lập nhân sự');assert.equal(heading.tagName,'SPAN')
 assert.equal(view.root.querySelectorAll('[aria-current=page]').length,1)
 assert.equal(view.root.querySelector('[aria-current=page]').getAttribute('aria-label'),'Máy chấm công')
 view.root.querySelector('[aria-label="Tuyển dụng"]').click();await tick()
 assert.deepEqual(visited,[['nhan-su',{hr_view:'candidates'}]])
 view.root.querySelector('.nav-parent').click();await tick()
 assert.equal(view.root.querySelector('.nav-submenu').style.display,'none');assert.equal(visited.length,1)
 sidebarCollapsed.value=true;await tick();view.root.querySelector('.nav-parent').click();await tick()
 assert.equal(sidebarCollapsed.value,false);assert.equal(view.root.querySelector('.nav-submenu').style.display,'')
 assert.equal(visited.length,1)
 view.unmount()
})

test('HR staff, attendance-only and unrelated users get only their permitted HR entries',async()=>{
 for(const [capabilities,expected] of [
  [{hr:true},['Hồ sơ nhân viên','Tuyển dụng','Tiếp nhận','Cơ cấu & chức danh','Máy chấm công','Nhập dữ liệu nhân sự']],
  [{attendance:true},['Chấm công']],
  [{},[]],
 ]){
  Object.assign(useSession(),{capabilities,commands:{},modules:{}})
  const view=mount(WorkspaceSidebar,{nav:pages.filter(([p])=>['nhan-su','cham-cong'].includes(p)),page:capabilities.hr?'nhan-su':'cham-cong'})
  await tick()
  assert.deepEqual([...view.root.querySelectorAll('.nav-child .nav-label')].map(n=>n.textContent),expected)
  view.unmount()
 }
})
