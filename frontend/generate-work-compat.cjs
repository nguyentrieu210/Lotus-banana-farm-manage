/* One-time split of legacy mobile layout rules required by the Work PWA.
   Run from frontend. Does not rewrite warehouse-mobile.css. */
const fs=require('fs'),postcss=require('postcss');
const files=['src/WorkMobile.vue','src/work-mobile.css','src/components/MobileLinkField.vue','src/components/MobileLiveSearch.vue','src/components/LotusMobileAction.vue','src/components/LotusMobileFile.vue','src/components/LotusMobileCheck.vue','src/components/LotusMobileDialog.vue'];
const source=files.map(f=>fs.readFileSync(f,'utf8')).join('\n');
const used=new Set([...source.matchAll(/\b(?:lotus|mobile)-[A-Za-z0-9_-]+\b/g)].map(m=>m[0]));
used.add('lotus-mobile');used.add('mobile-container');
const input=fs.readFileSync('src/warehouse-mobile.css','utf8');
const ast=postcss.parse(input,{from:'warehouse-mobile.css'}),out=postcss.root();
const globals=/^(?::root|\*|html|body|#app|h1|h2|button|input|select|textarea)(?:[,:\s{]|$)/;
let kept=0;
function copy(parent,dest){
 parent.each(n=>{
  if(n.type==='rule'){
   const classes=[...n.selector.matchAll(/\.([A-Za-z_][\w-]*)/g)].map(m=>m[1]);
   if(classes.some(x=>used.has(x))||globals.test(n.selector.trim())){dest.append(n.clone());kept++;}
  }else if(n.type==='atrule'){
   if(/keyframes/i.test(n.name))dest.append(n.clone());
   else {const next=n.clone({nodes:[]});if(n.nodes){copy(n,next);if(next.nodes.length)dest.append(next);}else dest.append(next);}
  }
 });
}
copy(ast,out);
const result='/* Shared legacy mobile primitives consumed by Work. Extracted in source order from warehouse-mobile.css;\n   do not add app-specific rules here. New components go in mobile-ui.css (Vant 4). */\n'+out.toString();
fs.writeFileSync('src/mobile-work-legacy.css',result,'utf8');
console.log('Work style classes:',used.size,'rules:',kept,'bytes:',result.length,'original bytes:',input.length);
