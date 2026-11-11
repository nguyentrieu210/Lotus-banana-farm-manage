// The table theme sizes match the --lotus-table-* tokens of each density (spec 004, FR-013), and the theme
// takes its colours from tokens only.
import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {loadRules,modeMap,resolveToken} from './support/css-tokens.mjs'

const source=readFileSync(new URL('../src/grid-theme.js',import.meta.url),'utf8')
const rules=loadRules(new URL('../src/lotus-tokens.css',import.meta.url))
const DENSITY_MAPS={
 compact:modeMap(rules,[':root']),
 comfortable:modeMap(rules,[':root',':root[data-density="comfortable"]']),
}
// Read GRID_DENSITY from the source so the test does not need ag-grid-community.
const densityBlock=source.match(/GRID_DENSITY=Object\.freeze\(\{([\s\S]*?)\n\}\)/)[1]
const sizes=Object.fromEntries([...densityBlock.matchAll(/(\w+):Object\.freeze\(\{([^}]*)\}\)/g)].map(([,name,body])=>[name,Object.fromEntries(body.split(',').map(p=>p.split(':')).map(([k,v])=>[k.trim(),Number(v)]))]))
const px=value=>Number(String(value).replace(/px$/,''))

test('grid sizes match the table tokens of each density',()=>{
 assert.deepEqual(Object.keys(sizes),['compact','comfortable'])
 for(const [density,map] of Object.entries(DENSITY_MAPS)){
  const s=sizes[density]
  assert.equal(s.rowHeight,px(resolveToken(map,'--lotus-table-row')),density+' row')
  assert.equal(s.headerHeight,px(resolveToken(map,'--lotus-table-header-height')),density+' header')
  assert.equal(s.fontSize,px(resolveToken(map,'--lotus-table-font')),density+' font')
  assert.equal(s.headerFontSize,px(resolveToken(map,'--lotus-table-header-font')),density+' header font')
  assert.equal(s.cellHorizontalPadding,px(resolveToken(map,'--lotus-table-cell-x')),density+' cell padding')
 }
})

test('theme colours are token variables, never literal colours',()=>{
 const colours=source.match(/const COLOURS=Object\.freeze\(\{([\s\S]*?)\n\}\)/)[1]
 assert.doesNotMatch(colours,/#[0-9a-f]{3,8}\b|rgb\(/i)
 const vars=[...source.matchAll(/var\((--lotus-[a-z0-9-]+)\)/g)].map(m=>m[1])
 assert.ok(vars.length>10)
 for(const name of vars)assert.ok(DENSITY_MAPS.compact.has(name),name+' is defined in lotus-tokens.css')
})

test('Kho keeps its accepted look as a named variant: vertical lines between columns',()=>{
 assert.match(source,/stock:\{columnBorder:line\(/)
 assert.match(source,/export function lotusGridTheme\(density='compact',variant='default'\)/)
})
