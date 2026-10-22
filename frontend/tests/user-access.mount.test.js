import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,ref,h} from './support/mount.mjs'
import {filterRoles,scopeWarnings} from '../src/user-access.js'
import {hrCatalogLabel} from '../src/hr-catalog-labels.js'
const Picker=await load('components/UserRolePicker.vue')
const Audit=await load('components/UserPermissionAudit.vue')
const roles=[
 {name:'Lotus Purchase Approver',label:'Người duyệt mua hàng Lotus',group:'Lotus',assignable:true},
 {name:'Accounts Manager',label:'Quản lý kế toán',group:'ERPNext',assignable:true},
 {name:'Disabled',label:'Vai trò cũ',group:'ERPNext',assignable:false,disabled:true},
 {name:'All',label:'Tất cả người dùng',group:'ERPNext',assignable:false,automatic:true},
]
test('all backend roles appear, search accepts Vietnamese without accents, assignment survives filtering',async()=>{
 const selected=ref(['Disabled'])
 const view=mount({setup:()=>()=>h(Picker,{roles,modelValue:selected.value,effectiveRoles:['All'],'onUpdate:modelValue':v=>selected.value=v})})
 assert.equal(view.root.querySelectorAll('.user-choice').length,4)
 const boxes=view.root.querySelectorAll('.user-choice input')
 assert.ok(boxes[2].disabled&&boxes[2].checked)
 assert.ok(boxes[3].disabled&&boxes[3].checked)
 const search=view.root.querySelector('input[type=search]');search.value='duyet mua';search.dispatchEvent(new Event('input'));await tick()
 assert.equal(view.root.querySelectorAll('.user-choice').length,1)
 view.root.querySelector('.user-choice input').click();await tick()
 assert.deepEqual(selected.value,['Disabled','Lotus Purchase Approver'])
 search.value='';search.dispatchEvent(new Event('input'));await tick()
 assert.equal(view.root.querySelectorAll('.user-choice').length,4)
 const group=view.root.querySelector('select');group.value='ERPNext';group.dispatchEvent(new Event('change'));await tick()
 assert.equal(view.root.querySelectorAll('.user-choice').length,3)
 view.unmount()
 assert.equal(filterRoles(roles,'ke toan').length,1)
})
test('role profiles prevent changes and farm/team warnings follow scoped business roles',async()=>{
 const view=mount(Picker,{roles,modelValue:['Accounts Manager'],disabled:true})
 assert.ok([...view.root.querySelectorAll('.user-choice input')].every(x=>x.disabled));view.unmount()
 assert.equal(scopeWarnings({roles:['Lotus Farm Manager'],farms:[]}).length,1)
 assert.equal(scopeWarnings({roles:['Lotus Team Leader'],farms:['A'],teams:[]}).length,1)
 assert.equal(scopeWarnings({roles:['Lotus Farm Manager'],farms:['A']}).length,0)
 assert.equal(hrCatalogLabel('Human Resources - LT'),'Nhân sự - LT')
 assert.equal(hrCatalogLabel('Chief Financial Officer'),'Giám đốc tài chính')
 assert.equal(hrCatalogLabel('Phòng mới'),'Phòng mới')
})

test('saved permission audit distinguishes role rights, denied farm scope and signing readiness',async()=>{
 const view=mount(Audit,{audit:{enabled:true,active_employee:'',
  permissions:[{label:'Vườn',doctype:'Farm',read:true,create:false,write:false,submittable:false}],
  farms:[{name:'A',label:'Vườn A',read:false}],
  signing:[{chain:'purchase_order',chain_label:'Đơn mua hàng',step:'APPROVE',title:'Người duyệt mua',ready:false,role_eligible:false,roles:['Người duyệt mua hàng Lotus']}]}})
 await tick()
 assert.match(view.root.textContent,/Bị chặn/)
 assert.match(view.root.textContent,/Chưa gắn nhân sự/)
 assert.match(view.root.textContent,/Thiếu role: Người duyệt mua hàng Lotus/)
 const record=view.root.querySelector('.lotus-mobile-record')
 assert.match(record.textContent,/Có/)
 assert.match(record.textContent,/Không/)
 assert.match(record.textContent,/Ghi sổ—/)
 view.unmount()
})
