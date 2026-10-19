import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync,readdirSync} from 'node:fs'
const src=new URL('../src/',import.meta.url)
const read=path=>readFileSync(new URL(path,src),'utf8')
const tokens=read('lotus-tokens.css')
const cssFiles=readdirSync(src).filter(f=>f.endsWith('.css')&&f!=='lotus-tokens.css')
const vueFiles=[...readdirSync(src).filter(f=>f.endsWith('.vue')),...readdirSync(new URL('components/',src)).filter(f=>f.endsWith('.vue')).map(f=>'components/'+f)]
const styleOf=file=>file.endsWith('.vue')?(read(file).match(/<style\b[\s\S]*?<\/style>/g)||[]).join('\n'):read(file)

test('one brand colour shared by desktop and PWA',()=>{
 assert.match(tokens,/--lotus-primary-600:#c43224/)
 assert.match(tokens,/--lotus-primary:var\(--lotus-primary-600\)/)
 assert.match(tokens,/--primary:5 69% 45%/)
 assert.match(tokens,/:root\.dark\{/)
 const theme=read('mobile-ui-theme.js')
 assert.match(theme,/primaryColor:'var\(--lotus-primary\)'/)
 assert.doesNotMatch(theme,/#[0-9a-f]{6}/i)
})

test('every entry loads lotus-tokens.css before its own stylesheets',()=>{
 for(const entry of readdirSync(src).filter(f=>/main\.js$/.test(f))){
  const code=read(entry),css=[...code.matchAll(/import '\.\/([\w-]+\.css)'/g)].map(m=>m[1])
  if(!css.length)continue
  const first=css.find(f=>f!=='lotus-fonts.css')
  assert.equal(first,'lotus-tokens.css',entry+' must import lotus-tokens.css first')
 }
})

test('no stylesheet redefines the global tokens',()=>{
 for(const file of cssFiles){
  for(const [,selector,body] of styleOf(file).matchAll(/([^{}]*)\{([^{}]*)\}/g)){
   const sel=selector.replace(/\/\*[\s\S]*?\*\//g,'').split(';').pop().trim()
   if(!/^(:root|\.dark|:root\.dark|\.lotus-ui|\.dark \.lotus-ui|\.lotus-desktop-page|\.dark\.lotus-desktop-page)$/.test(sel))continue
   assert.doesNotMatch(body,/--(lotus-(page|surface|text|muted|border|accent)|primary|ring|background|foreground):/,`${file} ${sel} redefines a token`)
  }
 }
})

test('colours come from tokens: no opaque hex outside lotus-tokens.css',()=>{
 const found=[]
 for(const file of [...cssFiles,...vueFiles]){
  for(const [body] of styleOf(file).matchAll(/\{[^{}]*\}/g)){
   for(const hex of body.replace(/url\([^)]*\)/g,'').match(/#[0-9a-f]{3,8}\b/gi)||[]){
    const k=hex.toLowerCase()
    // white/black and translucent shadows/overlays are allowed
    if(/^#(fff|ffffff|000|000000)$/.test(k)||k.length===5||k.length===9)continue
    found.push(file+' '+k)
   }
  }
 }
 assert.deepEqual(found,[])
})

test('one font stack',()=>{
 assert.match(tokens,/--lotus-font:InterVar,Inter,/)
 for(const file of [...cssFiles,...vueFiles]){
  for(const [,value] of styleOf(file).matchAll(/font-family:\s*([^;}"]+)/g)){
   assert.ok(/^(var\(--lotus-font\)|inherit|Georgia,serif|var\(--lotus-font-mono\))/.test(value.trim()),`${file} font-family:${value}`)
  }
 }
})

test('PWAs use the shared confirm dialog, never native alert/confirm',()=>{
 for(const file of ['WarehouseMobile.vue','BuyingMobile.vue','WorkMobile.vue','HrMobile.vue']){
  assert.doesNotMatch(read(file),/window\.(alert|confirm)\(/,file)
 }
 assert.doesNotMatch(read('HrMobile.vue'),/VanButton|VanLoading/)
})
