import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
// mount.mjs must run before anything pulls in Vue, so runtime-dom sees the Happy DOM document.
import {load,mount,tick,h,ref,document} from './support/mount.mjs'

const LotusMobileDialog=await load('components/LotusMobileDialog.vue')

// Found in the browser walk-through on the live-site copy (10/11/2026): the signing confirmation opened from the
// Chờ tôi ký sheet stayed under the sheet on a phone, so tapping "Ký" did nothing visible.
test('phone confirmations are rendered at the top of the page, above any open sheet',()=>{
 const dialog=readFileSync(new URL('../src/components/LotusMobileDialog.vue',import.meta.url),'utf8')
 assert.match(dialog,/<Dialog [^>]*teleport="body"/)
})

// Its review: outside .lotus-pwa-shell the dialog lost the shell's form rules (14px inputs make an iPhone zoom on focus).
test('a teleported phone dialog keeps the shell form rules: 16px inputs, border-box, focus ring',()=>{
 const dialog=readFileSync(new URL('../src/components/LotusMobileDialog.vue',import.meta.url),'utf8')
 const css=readFileSync(new URL('../src/mobile-ui.css',import.meta.url),'utf8')
 assert.match(dialog,/<Dialog [^>]*:class="\['lotus-pwa-dialog',host\]"/)
 assert.match(css,/:is\(\.lotus-pwa-shell,\.lotus-pwa-dialog\) \.lotus-pwa-field :is\(input,textarea,select\)\{[^}]*font-size:16px/)
 assert.match(css,/:is\(\.lotus-pwa-shell,\.lotus-pwa-dialog\) \*\{box-sizing:border-box\}/)
 assert.match(css,/:is\(\.lotus-pwa-shell,\.lotus-pwa-dialog\) :is\(button,a,input,select,textarea,\[role="option"\]\):focus-visible/)
 assert.doesNotMatch(css,/(^|[},])\s*\.lotus-pwa-shell [^{]*\{/m,'every descendant rule of the shell also reaches the dialog')
})

// Second review: the purchasing screen's phone rules (wrapping action rows, one-column fields) stopped reaching the
// receiving dialog once it was teleported. The dialog takes the screen's modifier with it, and only that screen's.
test('a dialog opened from the phone purchasing screen keeps that screen\'s phone rules, other dialogs do not',async()=>{
 for(const [host,expected] of [['procurement-workspace procurement-workspace--mobile',true],['hr-sheet',false]]){
  const dialog=ref(null)
  const view=mount({render:()=>h('section',{class:host},[h(LotusMobileDialog,{ref:dialog},{default:()=>h('h2','Nhận hàng')})])})
  await tick();await dialog.value.showModal();await tick()
  const shown=[...document.body.querySelectorAll('.lotus-pwa-dialog')].at(-1)
  assert.ok(shown,'the dialog is in the page')
  assert.equal(shown.classList.contains('procurement-workspace--mobile'),expected,host)
  dialog.value.close();await tick();view.unmount()
 }
})
