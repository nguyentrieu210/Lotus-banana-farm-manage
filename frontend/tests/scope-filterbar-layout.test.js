import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

const scope=readFileSync(new URL('../src/components/WorkspaceScopeBar.vue',import.meta.url),'utf8')
const style=readFileSync(new URL('../src/workspace-experience.css',import.meta.url),'utf8')

test('shared scope filters reserve a separate width for the two-date control',()=>{
 assert.match(scope, /class="scope-date-range" label="Từ ngày – đến ngày"/)
 assert.match(style, />\.scope-picker>\.lotus-field\{\s*flex:0 0 170px/)
 assert.match(style, />\.scope-picker>\.scope-date-range\{\s*flex-basis:320px/)
 assert.match(style, />\.scope-picker>\.scope-date-range \.lotus-date__field\{\s*width:100%;min-width:0/)
})

test('scope filters stay on one horizontally scrollable row and never shrink the refresh button',()=>{
 assert.match(style, />\.scope-picker\{\s*display:flex;flex-wrap:nowrap;align-items:flex-end;gap:8px;\s*max-width:100%;min-width:0;overflow-x:auto/)
 assert.match(style, />\.scope-picker>button\{flex:0 0 auto;align-self:flex-end\}/)
 assert.doesNotMatch(style, />\.scope-picker>label/)
})
