// Display mode and density (spec 004, FR-003, FR-013, FR-025, FR-047): saved choices survive, outdoor and dark
// never combine, phones keep following the system theme.
import test from 'node:test'
import assert from 'node:assert/strict'
import {readUiPrefs,resolveUiMode,applyUiMode,UI_KEYS} from '../src/ui-mode.js'

const memory=(entries={})=>{const data=new Map(Object.entries(entries));return {getItem:k=>data.has(k)?data.get(k):null,setItem:(k,v)=>data.set(k,String(v)),data}}
const fakeRoot=()=>{const classes=new Set();return {classList:{toggle:(name,on)=>on?classes.add(name):classes.delete(name),contains:n=>classes.has(n)},dataset:{},style:{},classes}}

test('saved choices from before spec 004 are read with the same keys',()=>{
 assert.deepEqual(UI_KEYS,{theme:'lotus-theme',outdoor:'lotus-outdoor',density:'lotus-desktop-density'})
 assert.deepEqual(readUiPrefs(memory({'lotus-theme':'dark','lotus-desktop-density':'comfortable'})),{theme:'dark',outdoor:false,density:'comfortable'})
 assert.deepEqual(readUiPrefs(memory()),{theme:null,outdoor:false,density:'compact'})
 assert.deepEqual(readUiPrefs(memory({'lotus-theme':'purple','lotus-desktop-density':'huge','lotus-outdoor':'1'})),{theme:null,outdoor:true,density:'compact'})
})

test('storage that throws (private mode) falls back to defaults',()=>{
 const broken={getItem(){throw new Error('denied')}}
 assert.deepEqual(readUiPrefs(broken),{theme:null,outdoor:false,density:'compact'})
})

test('outdoor wins over dark; phones follow the system; desktop ignores outdoor',()=>{
 assert.equal(resolveUiMode({theme:'dark',outdoor:true},{allowOutdoor:true}),'outdoor')
 assert.equal(resolveUiMode({theme:'dark',outdoor:true},{allowOutdoor:false}),'dark')
 assert.equal(resolveUiMode({theme:null,outdoor:false},{followSystem:true,systemDark:true}),'dark')
 assert.equal(resolveUiMode({theme:'dark',outdoor:false},{followSystem:true,systemDark:false}),'light')
 assert.equal(resolveUiMode({theme:null,outdoor:false}),'light')
})

test('the page never carries .dark and .lotus-outdoor together',()=>{
 const root=fakeRoot()
 applyUiMode('dark','comfortable',root)
 assert.ok(root.classes.has('dark'));assert.ok(!root.classes.has('lotus-outdoor'))
 assert.equal(root.dataset.theme,'dark');assert.equal(root.dataset.density,'comfortable');assert.equal(root.style.colorScheme,'dark')
 applyUiMode('outdoor','compact',root)
 assert.ok(!root.classes.has('dark'));assert.ok(root.classes.has('lotus-outdoor'))
 assert.equal(root.dataset.theme,'light');assert.equal(root.dataset.mode,'outdoor');assert.equal(root.dataset.density,'compact')
 applyUiMode('weird','tiny',root)
 assert.equal(root.dataset.mode,'light');assert.equal(root.dataset.density,'compact')
})
