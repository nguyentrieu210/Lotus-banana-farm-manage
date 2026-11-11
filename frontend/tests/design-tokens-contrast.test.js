// Contrast of the token pairs the kit actually paints (spec 004, FR-004, SC-001), in light, dark and outdoor.
// Text ≥ 4.5:1; large text, icons, control borders and chart marks ≥ 3:1; outdoor body text ≥ 7:1.
import test from 'node:test'
import assert from 'node:assert/strict'
import {loadRules,modeMap,resolveToken,contrast,toRgba} from './support/css-tokens.mjs'

const rules=loadRules(new URL('../src/lotus-tokens.css',import.meta.url))
const MODES={
 light:modeMap(rules,[':root']),
 dark:modeMap(rules,[':root',':root.dark']),
 outdoor:modeMap(rules,[':root',':root.lotus-outdoor']),
}
const TONES=['neutral','primary','success','warning','danger','info']
const LOT_STATES=['empty','entered','sent','confirmed','ok','due','overdue','quarantine']

const TEXT=[
 ['--lotus-text','--lotus-surface'],['--lotus-text','--lotus-page'],['--lotus-text','--lotus-sunken'],
 ['--lotus-text-strong','--lotus-surface'],['--lotus-text-secondary','--lotus-surface'],
 ['--lotus-muted','--lotus-surface'],['--lotus-muted','--lotus-page'],['--lotus-muted','--lotus-soft'],['--lotus-muted','--lotus-sidebar'],
 ['--lotus-subtle','--lotus-surface'],['--lotus-subtle','--lotus-page'],
 ['--lotus-primary-text','--lotus-surface'],['--lotus-primary-text','--lotus-primary-subtle'],['--lotus-primary','--lotus-surface'],
 ['--lotus-link','--lotus-surface'],
 ['--lotus-on-primary-solid','--lotus-primary-solid'],['--lotus-on-topbar','--lotus-topbar'],['--lotus-on-topbar','--lotus-topbar-end'],
 ['--lotus-table-heading','--lotus-table-header'],
 ['--lotus-text','--lotus-table-zebra'],['--lotus-text','--lotus-table-hover'],['--lotus-text','--lotus-table-selected'],['--lotus-text','--lotus-table-total'],
 ['--lotus-success','--lotus-success-soft'],['--lotus-warning','--lotus-warning-soft'],['--lotus-danger','--lotus-danger-soft'],['--lotus-info','--lotus-info-soft'],
 ['--lotus-success','--lotus-surface'],['--lotus-warning','--lotus-surface'],['--lotus-danger','--lotus-surface'],['--lotus-info','--lotus-surface'],
 ...TONES.flatMap(t=>[[`--lotus-tone-${t}-text`,`--lotus-tone-${t}-soft`],[`--lotus-tone-${t}-on`,`--lotus-tone-${t}-solid`],[`--lotus-tone-${t}-text`,'--lotus-surface']]),
 ...LOT_STATES.map(s=>[`--lotus-lot-${s}-on`,`--lotus-lot-${s}`]),
]
const GRAPHIC=[
 ['--lotus-border-control','--lotus-surface'],['--lotus-border-control','--lotus-page'],
 ['--lotus-focus-ring','--lotus-surface'],['--lotus-focus-ring','--lotus-page'],
 ['--lotus-ribbon-outline','--lotus-surface'],
 ...[1,2,3,4,5,6,7,8].map(i=>[`--lotus-chart-${i}`,'--lotus-surface']),
 ['--lotus-chart-forecast','--lotus-surface'],['--lotus-chart-actual','--lotus-surface'],['--lotus-chart-axis','--lotus-surface'],
]
// Outdoor: the text people read in the sun.
const OUTDOOR_MAIN=[
 ['--lotus-text','--lotus-surface'],['--lotus-text-secondary','--lotus-surface'],['--lotus-muted','--lotus-surface'],['--lotus-muted','--lotus-soft'],
 ['--lotus-primary-text','--lotus-surface'],['--lotus-link','--lotus-surface'],['--lotus-on-primary-solid','--lotus-primary-solid'],
 ['--lotus-table-heading','--lotus-table-header'],
 ...TONES.map(t=>[`--lotus-tone-${t}-text`,`--lotus-tone-${t}-soft`]),
]

function measure(mode,fg,bg){
 const map=MODES[mode],a=resolveToken(map,fg),b=resolveToken(map,bg)
 assert.ok(toRgba(a),`${mode}: ${fg} resolves to a colour (${a})`)
 assert.ok(toRgba(b),`${mode}: ${bg} resolves to a colour (${b})`)
 return {a,b,ratio:contrast(a,b)}
}
function check(mode,pairs,minimum){
 const failures=[]
 for(const [fg,bg] of pairs){
  const {a,b,ratio}=measure(mode,fg,bg)
  if(ratio<minimum)failures.push(`${fg} ${a} on ${bg} ${b} = ${ratio.toFixed(2)}:1 < ${minimum}`)
 }
 assert.deepEqual(failures,[],mode)
}

for(const mode of Object.keys(MODES)){
 test(`${mode}: text pairs reach 4.5:1`,()=>check(mode,TEXT,4.5))
 test(`${mode}: control borders, focus ring, ribbon outline and chart marks reach 3:1`,()=>check(mode,GRAPHIC,3))
}
test('outdoor: main text reaches 7:1',()=>check('outdoor',OUTDOOR_MAIN,7))

test('every colour token is plain hex, rgb() or a reference (old Android WebViews)',()=>{
 const bad=[]
 for(const rule of rules)for(const [name,value] of rule.decls){
  if(!name.startsWith('--lotus-')||!/(color|colour|-\d{2,3}$|text|surface|page|border|tone|lot-|chart|seq-|div-|ribbon|map-zone|primary|success|warning|danger|info|neutral|earth|topbar|sidebar|soft|hover|selected|zebra|total)/.test(name))continue
  if(/oklch|oklab|lab\(|lch\(|color\(/.test(value))bad.push(`${rule.selector} ${name}: ${value}`)
 }
 assert.deepEqual(bad,[])
})

test('modes and densities override only tokens that exist in the light base',()=>{
 const base=MODES.light,extra=[]
 for(const rule of rules){
  if(rule.selector===':root'&&!rule.at.length)continue
  for(const name of rule.decls.keys())if(!base.has(name))extra.push(`${rule.selector} ${name}`)
 }
 assert.deepEqual(extra,[])
})

test('brand red stays the single primary colour',()=>{
 assert.equal(resolveToken(MODES.light,'--lotus-primary'),'#c43224')
 assert.equal(resolveToken(MODES.light,'--lotus-primary-solid'),'#c43224')
 assert.equal(resolveToken(MODES.dark,'--lotus-primary-solid'),'#c43224')
 // danger is a different hue from the brand red, so a red button never reads as an error
 assert.notEqual(resolveToken(MODES.light,'--lotus-danger'),resolveToken(MODES.light,'--lotus-primary'))
})
