// Behaviour of the spec 004 kit components (constitution IV: a component with behaviour has a mount test).
import test from 'node:test'
import assert from 'node:assert/strict'
import {load,loadModule,mount,tick,h,ref,window} from './support/mount.mjs'

const {StatusChip}=await loadModule('components/ui/status-chip/index.js')
const {Banner}=await loadModule('components/ui/banner/index.js')
const {StatTile}=await loadModule('components/ui/stat-tile/index.js')
const {NumberStepper}=await loadModule('components/ui/number-stepper/index.js')
const {Segmented}=await loadModule('components/ui/segmented/index.js')
const {Switch}=await loadModule('components/ui/switch/index.js')
const {Steps}=await loadModule('components/ui/steps/index.js')
const {Progress}=await loadModule('components/ui/progress/index.js')
const LotusMobileNetBar=await load('components/LotusMobileNetBar.vue')

const click=el=>el.dispatchEvent(new window.MouseEvent('click',{bubbles:true}))
const input=(el,value)=>{el.value=value;el.dispatchEvent(new window.Event('input',{bubbles:true}))}

test('StatusChip: one raw state, one chip — label, tone, icon from the shared vocabulary',async()=>{
 const view=mount({setup:()=>()=>[h(StatusChip,{status:'Overdue'}),h(StatusChip,{status:'Sent',label:'Đã gửi, chờ xác nhận'}),h(StatusChip,{status:'Cancelled'}),h(StatusChip,{status:'Một mã lạ'})]})
 await tick()
 const [overdue,sent,cancelled,unknown]=view.root.querySelectorAll('.lotus-chip')
 assert.ok(overdue.classList.contains('lotus-chip--danger'));assert.equal(overdue.textContent.trim(),'Quá hạn');assert.ok(overdue.querySelector('svg.lotus-icon'),'state is never colour alone')
 assert.equal(sent.textContent.trim(),'Đã gửi, chờ xác nhận');assert.ok(sent.classList.contains('lotus-chip--info'))
 assert.equal(cancelled.dataset.kind,'cancelled')
 assert.ok(unknown.classList.contains('lotus-chip--neutral'));assert.ok(unknown.classList.contains('lotus-chip--bare'));assert.equal(unknown.querySelector('svg'),null)
 view.unmount()
})

test('Banner: danger is announced at once, others politely; it can be dismissed',async()=>{
 const dismissed=[]
 const view=mount({setup:()=>()=>[h(Banner,{tone:'danger',title:'Lô C1 đang cách ly'},()=>'Không ghi được thu hoạch.'),h(Banner,{tone:'warning',dismissible:true,onDismiss:()=>dismissed.push(1)},()=>'Thiếu ảnh.')]})
 await tick()
 const [danger,warning]=view.root.querySelectorAll('.lotus-banner')
 assert.equal(danger.getAttribute('role'),'alert');assert.equal(warning.getAttribute('role'),'status')
 click(warning.querySelector('.lotus-banner__close'));await tick()
 assert.equal(view.root.querySelectorAll('.lotus-banner').length,1);assert.equal(dismissed.length,1)
 view.unmount()
})

test('StatTile: a missing figure shows a dash and the reason, never 0; a change reads as good or bad',async()=>{
 const view=mount({setup:()=>()=>[h(StatTile,{label:'Dự thu',value:null,missing:'Chưa có bản chốt'}),h(StatTile,{label:'Lô quá hạn',value:9,unit:'lô',delta:3,goodWhen:'down'}),h(StatTile,{label:'Thu',value:6640,unit:'buồng',delta:120})]})
 await tick()
 const [missing,overdue,harvest]=view.root.querySelectorAll('.lotus-stat')
 assert.ok(missing.classList.contains('lotus-stat--missing'));assert.equal(missing.querySelector('.lotus-stat__value').textContent.trim(),'—');assert.match(missing.textContent,/Chưa có bản chốt/)
 assert.ok(overdue.querySelector('.lotus-stat__delta--bad'),'more overdue lots is bad')
 assert.match(harvest.querySelector('.lotus-stat__value').textContent.trim(),/^6\.640\s*buồng$/,'Vietnamese grouping and the unit')
 assert.ok(harvest.querySelector('.lotus-stat__delta--good'))
 view.unmount()
})

test('NumberStepper: − and +, clamped to min/max, empty stays empty, comma decimals accepted',async()=>{
 const value=ref(null)
 const view=mount({setup:()=>()=>h(NumberStepper,{label:'Số buồng',unit:'buồng',min:0,max:3,modelValue:value.value,'onUpdate:modelValue':v=>value.value=v})})
 await tick()
 const [minus,plus]=view.root.querySelectorAll('button'),field=view.root.querySelector('input')
 assert.equal(field.value,'','nothing entered is not 0')
 assert.equal(field.getAttribute('aria-label'),'Số buồng (buồng)')
 click(plus);await tick();assert.equal(value.value,1,'the first + from empty is one buồng, not 0')
 for(let i=0;i<4;i++){click(plus);await tick()}
 assert.equal(value.value,3,'never above max')
 assert.ok(plus.disabled)
 click(minus);await tick();assert.equal(value.value,2)
 input(field,'');await tick();assert.equal(value.value,null)
 view.unmount()
 const kg=ref(1)
 const decimal=mount({setup:()=>()=>h(NumberStepper,{label:'Khối lượng',decimals:1,step:0.5,modelValue:kg.value,'onUpdate:modelValue':v=>kg.value=v})})
 await tick()
 input(decimal.root.querySelector('input'),'12,5');await tick();assert.equal(kg.value,12.5)
 assert.equal(decimal.root.querySelector('input').value,'12,5')
 decimal.unmount()
})

test('Segmented: one choice, labelled group, cannot be cleared',async()=>{
 const value=ref('week')
 const view=mount({setup:()=>()=>h(Segmented,{label:'Kỳ',options:[{value:'day',label:'Sáng nay'},{value:'week',label:'Tuần'}],modelValue:value.value,'onUpdate:modelValue':v=>value.value=v})})
 await tick()
 const group=view.root.querySelector('.lotus-segmented')
 assert.equal(group.getAttribute('aria-label'),'Kỳ')
 const items=view.root.querySelectorAll('.lotus-segmented__item')
 assert.equal(items[1].dataset.state,'on')
 click(items[0]);await tick();assert.equal(value.value,'day')
 click(view.root.querySelectorAll('.lotus-segmented__item')[0]);await tick();assert.equal(value.value,'day','clicking the chosen item keeps it')
 view.unmount()
})

test('Switch: role switch, label tied to it, toggles',async()=>{
 const on=ref(false)
 const view=mount({setup:()=>()=>h(Switch,{label:'Chế độ ngoài trời',modelValue:on.value,'onUpdate:modelValue':v=>on.value=v})})
 await tick()
 const button=view.root.querySelector('[role="switch"]'),label=view.root.querySelector('label')
 assert.ok(button);assert.equal(label.getAttribute('for'),button.id)
 click(button);await tick();assert.equal(on.value,true)
 view.unmount()
})

test('Steps: the current step is marked for screen readers; a returned step says so',async()=>{
 const view=mount({setup:()=>()=>h(Steps,{steps:[{label:'Lập',state:'done'},{label:'Thủ kho',state:'returned'},{label:'Kế toán',state:'current'},{label:'Giám đốc'}]})})
 await tick()
 const items=view.root.querySelectorAll('.lotus-steps__item')
 assert.equal(items.length,4);assert.equal(items[2].getAttribute('aria-current'),'step')
 assert.match(items[1].textContent,/trả lại/);assert.equal(items[3].dataset.state,'waiting')
 view.unmount()
})

test('Progress: value is clamped and exposed to assistive technology',async()=>{
 const view=mount({setup:()=>()=>h(Progress,{value:80,max:64,label:'Lô đã báo cáo',valueText:'80 / 64 lô'})})
 await tick()
 const bar=view.root.querySelector('[role="progressbar"]')
 assert.equal(bar.getAttribute('aria-valuenow'),'100');assert.equal(bar.getAttribute('aria-valuetext'),'80 / 64 lô')
 view.unmount()
})

test('LotusMobileNetBar: shows offline with the queue, then a short "back online"',async()=>{
 const online=ref(false)
 const view=mount({setup:()=>()=>h(LotusMobileNetBar,{online:online.value,queued:3})})
 await tick()
 assert.match(view.root.textContent,/Đang ngoại tuyến/);assert.match(view.root.textContent,/3 chờ gửi/)
 online.value=true;await tick()
 assert.doesNotMatch(view.root.textContent,/Đang ngoại tuyến/)
 view.unmount()
})
