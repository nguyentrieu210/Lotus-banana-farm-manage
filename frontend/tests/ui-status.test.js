// One status vocabulary (spec 004, FR-005, SC-002) and ribbon colours (FR-031).
import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {STATUS_KINDS,TONES,statusKind,statusMeta,dueState,daysBetween} from '../src/ui-status.js'
import {ribbonParts,ribbonLabel,ribbonBackground,RIBBON_COLOURS} from '../src/ribbon-colors.js'

const icons=readFileSync(new URL('../src/icon-paths.js',import.meta.url),'utf8')
const tokens=readFileSync(new URL('../src/lotus-tokens.css',import.meta.url),'utf8')

test('every kind has a Vietnamese label, a known tone and an icon that LotusIcon draws',()=>{
 for(const [kind,meta] of Object.entries(STATUS_KINDS)){
  assert.ok(meta.label&&/[a-zà-ỹđ]/i.test(meta.label),kind)
  assert.ok(TONES.includes(meta.tone),kind+' tone')
  assert.match(icons,new RegExp(`(^|[\\s,{])'?${meta.icon}'?:\\[`),kind+' icon '+meta.icon)
 }
})

test('the spec vocabulary is complete: nháp … cách ly',()=>{
 for(const kind of ['draft','pending','to_sign','approved','done','returned','reopened','cancelled','due','overdue','quarantine'])assert.ok(STATUS_KINDS[kind],kind)
})

test('the same raw state gives the same chip in every module',()=>{
 assert.equal(statusKind('Draft'),'draft');assert.equal(statusKind(0),'draft');assert.equal(statusKind('0'),'draft')
 assert.equal(statusKind(1),'approved');assert.equal(statusKind('Submitted'),'approved')
 assert.equal(statusKind(2),'cancelled');assert.equal(statusKind('Cancelled'),'cancelled');assert.equal(statusKind('Voided'),'cancelled')
 assert.equal(statusKind('Rework'),'returned');assert.equal(statusKind('Returned'),'returned')
 assert.equal(statusKind('Overdue'),'overdue');assert.equal(statusKind('overdue'),'overdue')
 assert.equal(statusKind('Something new'),null);assert.equal(statusKind(''),null);assert.equal(statusKind(null),null)
})

test('labels: the caller caption wins, then the kind label, then the code; unknown codes are neutral',()=>{
 assert.deepEqual(statusMeta('Sent','Đã gửi, chờ xác nhận'),{code:'Sent',kind:'sent',label:'Đã gửi, chờ xác nhận',tone:'info',icon:'send'})
 assert.equal(statusMeta('Draft').label,'Nháp')
 assert.equal(statusMeta('Draft','Draft').label,'Nháp')
 assert.deepEqual(statusMeta('Weird code'),{code:'Weird code',kind:null,label:'Weird code',tone:'neutral',icon:''})
})

test('due dates read as days left or days over, by calendar day',()=>{
 assert.equal(daysBetween('2026-11-10','2026-11-14'),4)
 assert.equal(daysBetween(new Date(2026,10,10,23,59),'2026-11-11'),1)
 assert.deepEqual(dueState('2026-11-14','2026-11-10'),{kind:'upcoming',days:4,label:'Còn 4 ngày',tone:'neutral',icon:'calendar'})
 assert.equal(dueState('2026-11-12','2026-11-10',{soon:3}).kind,'due')
 assert.equal(dueState('2026-11-10','2026-11-10').label,'Đến hạn hôm nay')
 assert.deepEqual(dueState('2026-11-07','2026-11-10'),{kind:'overdue',days:-3,label:'Quá 3 ngày',tone:'danger',icon:'alert'})
 assert.equal(dueState('','2026-11-10'),null)
})

test('ribbon codes, Vietnamese names and two-colour ribbons resolve to token colours',()=>{
 for(const meta of Object.values(RIBBON_COLOURS))assert.match(tokens,new RegExp(meta.token+':#[0-9a-f]{6}'),meta.token)
 assert.deepEqual(ribbonParts('DO'),[{key:'DO',label:'Đỏ',colour:'var(--lotus-ribbon-do)'}])
 assert.deepEqual(ribbonParts('xanh_la_do').map(p=>p.key),['XANH_LA','DO'])
 assert.deepEqual(ribbonParts('Xanh dương').map(p=>p.key),['XANH_DUONG'])
 assert.deepEqual(ribbonParts('Đen').map(p=>p.key),['DEN'])
 assert.equal(ribbonLabel('XANH_LA_DO'),'Xanh lá – Đỏ')
 assert.equal(ribbonBackground('TRANG'),'var(--lotus-ribbon-trang)')
 assert.equal(ribbonBackground('XANH_LA_DO'),'linear-gradient(90deg,var(--lotus-ribbon-xanh-la) 0% 50%,var(--lotus-ribbon-do) 50% 100%)')
 assert.equal(ribbonBackground('#123456'),'#123456')
 assert.equal(ribbonBackground('VANG'),'transparent');assert.equal(ribbonBackground(''),'transparent')
})
