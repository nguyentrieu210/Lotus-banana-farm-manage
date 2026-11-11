// Behaviour of the agritech pack (spec 004, User Story 5): lot grid, lot card, week strip, ribbons, due, quarantine, charts.
import test from 'node:test'
import assert from 'node:assert/strict'
import {loadModule,mount,tick,h,ref,window} from './support/mount.mjs'

const agri=await loadModule('components/agri/index.js')
const {LotGrid,LotCard,WeekStrip,RibbonChip,RibbonPicker,DueMeter,QuarantineBadge,ForecastWeekChart,AgeHistogram,RibbonBatchCard}=agri
const click=el=>el.dispatchEvent(new window.MouseEvent('click',{bubbles:true}))
const TODAY='2026-11-10'

test('LotGrid: lots grouped by khu, every tile a labelled button with an icon for its state, legend with counts',async()=>{
 const picked=ref(''),selected=[]
 const lots=[{code:'A10',state:'overdue'},{code:'A2',state:'ok'},{code:'B1',state:'due'},{code:'B3',state:'quarantine'},{code:'A1',state:'ok'}]
 const view=mount({setup:()=>()=>h(LotGrid,{lots,states:['ok','due','overdue','quarantine'],modelValue:picked.value,'onUpdate:modelValue':v=>picked.value=v,onSelect:l=>selected.push(l.code)})})
 await tick()
 const zones=view.root.querySelectorAll('.lotus-lotgrid__zone')
 assert.equal(zones.length,2)
 assert.deepEqual([...zones[0].querySelectorAll('.lotus-lot-tile')].map(t=>t.textContent.trim()),['A1','A2','A10'],'natural order: A2 before A10')
 const overdue=view.root.querySelector('.lotus-lot-tile[data-state="overdue"]')
 assert.equal(overdue.tagName,'BUTTON');assert.equal(overdue.getAttribute('aria-label'),'Lô A10: Quá hạn');assert.ok(overdue.querySelector('svg'),'icon, not colour alone')
 click(overdue);await tick()
 assert.equal(picked.value,'A10');assert.deepEqual(selected,['A10'])
 assert.equal(view.root.querySelector('.lotus-lot-tile[aria-pressed="true"]').textContent.trim(),'A10')
 const legend=[...view.root.querySelectorAll('.lotus-lotgrid__legend li')].map(li=>li.textContent.replace(/\s+/g,' ').trim())
 assert.deepEqual(legend,['Chưa đến hạn 2','Đến hạn 1','Quá hạn 1','Đang cách ly 1'])
 view.unmount()
})

test('LotCard: a button that opens the lot; state chip, ribbons with counts, quarantine countdown',async()=>{
 const opened=[]
 const lot={code:'B9',zone:'B',state:'empty',todo:'Chưa nhập hôm nay',ribbons:[{code:'TIM',week:39,count:31},{code:'CAM',week:40,count:18},{code:'DEN',week:41,count:2},{code:'DO',week:43,count:1},{code:'TRANG',week:44,count:6}],quarantineUntil:'2026-11-14'}
 const view=mount({setup:()=>()=>h(LotCard,{lot,today:TODAY,onOpen:l=>opened.push(l.code)})})
 await tick()
 const card=view.root.querySelector('.lotus-lotcard')
 assert.equal(card.tagName,'BUTTON');assert.equal(card.dataset.state,'empty');assert.match(card.getAttribute('aria-label'),/Lô B9 khu B: Chưa nhập/)
 assert.equal(view.root.querySelectorAll('.lotus-ribbon-chip').length,4,'at most four ribbons, then +n');assert.match(view.root.textContent,/\+1/)
 assert.match(view.root.querySelector('.lotus-quarantine').textContent,/Cách ly còn 4 ngày, đến 14\/11/)
 click(card);await tick();assert.deepEqual(opened,['B9'])
 view.unmount()
})

test('QuarantineBadge and DueMeter read days against today',async()=>{
 const view=mount({setup:()=>()=>[h(QuarantineBadge,{until:'2026-11-09',today:TODAY}),h(QuarantineBadge,{until:'2026-11-10',today:TODAY}),h(DueMeter,{due:'2026-11-07',today:TODAY,cycle:21,label:'Cắt lá'}),h(DueMeter,{due:'2026-11-20',today:TODAY,cycle:30})]})
 await tick()
 const badges=view.root.querySelectorAll('.lotus-quarantine')
 assert.equal(badges.length,1,'an ended quarantine shows nothing');assert.match(badges[0].textContent,/hết hôm nay/)
 const [overdue,later]=view.root.querySelectorAll('.lotus-due')
 assert.equal(overdue.dataset.state,'overdue');assert.match(overdue.textContent,/Cắt lá: Quá 3 ngày/);assert.equal(overdue.querySelector('.lotus-due__fill').style.width,'100%')
 assert.equal(later.dataset.state,'upcoming');assert.match(later.textContent,/Còn 10 ngày/)
 view.unmount()
})

test('WeekStrip: ISO weeks around today, this week marked, harvest weeks marked, v-model picks a week',async()=>{
 const week=ref('')
 const view=mount({setup:()=>()=>h(WeekStrip,{today:TODAY,before:1,after:2,harvest:['2026-W47'],values:{'2026-W47':7350},unit:'buồng',modelValue:week.value,'onUpdate:modelValue':v=>week.value=v})})
 await tick()
 const cells=view.root.querySelectorAll('.lotus-weekstrip__cell')
 assert.deepEqual([...cells].map(c=>c.querySelector('.lotus-weekstrip__num').textContent),['T45','T46','T47','T48'])
 assert.equal(cells[1].getAttribute('aria-current'),'date');assert.ok(cells[2].classList.contains('lotus-weekstrip__cell--harvest'))
 assert.match(cells[2].getAttribute('aria-label'),/7\.350 buồng/)
 click(cells[2]);await tick();assert.equal(week.value,'2026-W47')
 view.unmount()
})

test('Ribbons: chip names two-colour ribbons; the picker is a radio group driven by arrows',async()=>{
 const code=ref('CAM')
 const view=mount({setup:()=>()=>[h(RibbonChip,{code:'XANH_LA_DO',week:37,count:233}),h(RibbonPicker,{label:'Màu dây',options:[{code:'CAM',week:46},{code:'DEN',week:45},{code:'TRANG',week:44}],modelValue:code.value,'onUpdate:modelValue':v=>code.value=v})]})
 await tick()
 assert.match(view.root.querySelector('.lotus-ribbon-chip').getAttribute('aria-label'),/Màu dây Xanh lá – Đỏ, tuần 37, còn 233 buồng/)
 const radios=view.root.querySelectorAll('[role="radio"]')
 assert.equal(view.root.querySelector('[role="radiogroup"]').getAttribute('aria-label'),'Màu dây')
 assert.equal(radios[0].getAttribute('aria-checked'),'true')
 radios[0].dispatchEvent(new window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));await tick()
 assert.equal(code.value,'DEN')
 click(view.root.querySelectorAll('[role="radio"]')[2]);await tick();assert.equal(code.value,'TRANG')
 view.unmount()
})

test('Charts draw only the numbers given: no bar for a week without an actual, a summary for screen readers',async()=>{
 const weeks=[{year:2026,week:45,forecast:6900,actual:6640,low:6300,high:7400},{year:2026,week:46,forecast:7120,actual:null,low:6550,high:7600},{year:2026,week:47,forecast:7350,actual:null}]
 const view=mount({setup:()=>()=>[h(ForecastWeekChart,{weeks,today:TODAY}),h(AgeHistogram,{bins:[{age:8,count:238},{age:9,count:354,ripe:true},{age:10,count:31,ripe:true}]})]})
 await tick()
 const [forecast,histogram]=view.root.querySelectorAll('figure.lotus-chart')
 assert.equal(forecast.querySelectorAll('.lotus-chart__bar').length,1,'one actual, one bar')
 assert.match(forecast.querySelector('svg').getAttribute('aria-label'),/3 tuần, 3 tuần có dự thu, 1 tuần có thực tế/)
 const cols=forecast.querySelectorAll('.lotus-chart__col')
 assert.match(cols[0].getAttribute('aria-label'),/thực tế 6\.640 buồng, lệch −260/)
 assert.equal(histogram.querySelectorAll('.lotus-chart__bar--ripe').length,2)
 assert.match(histogram.textContent,/Đến tuổi thu\s*385/)
 view.unmount()
})

test('RibbonBatchCard: counts, harvest progress and the harvest window',async()=>{
 const view=mount({setup:()=>()=>h(RibbonBatchCard,{batch:{code:'XANH_LA',week:36,age:9,cut:248,bagged:244,harvested:120,left:121,ripe:true},today:TODAY})})
 await tick()
 const card=view.root.querySelector('.lotus-batch')
 assert.equal(card.dataset.ripe,'true');assert.match(card.textContent,/Đến tuổi thu/)
 assert.equal(card.querySelector('[role="progressbar"]').getAttribute('aria-valuetext'),'120 / 248')
 view.unmount()
})
