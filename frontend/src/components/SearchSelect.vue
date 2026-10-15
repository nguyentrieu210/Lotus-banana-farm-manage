<script setup>
import {computed,nextTick,onBeforeUnmount,ref,useId,watch,inject} from 'vue'
const props=defineProps({modelValue:{type:[String,Number],default:''},options:{type:Array,default:()=>[]},placeholder:{type:String,default:'Chọn…'},label:{type:String,required:true},disabled:Boolean})
const emit=defineEmits(['update:modelValue','change'])
const portalTarget=inject('searchSelectTarget','body')
const id=useId(),trigger=ref(null),popup=ref(null),input=ref(null),open=ref(false),query=ref(''),active=ref(0),position=ref({})
const selected=computed(()=>props.options.find(o=>o.value===props.modelValue))
const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').toLowerCase().replace(/[\s-]+/g,'')
const filtered=computed(()=>props.options.filter(o=>normalize([o.label,o.subtitle,o.group].join(' ')).includes(normalize(query.value))))
function place(){
 if(!open.value||!trigger.value)return
 const r=trigger.value.getBoundingClientRect(),v=window.visualViewport
 const top=v?.offsetTop||0,left=v?.offsetLeft||0,w=v?.width||innerWidth,h=v?.height||innerHeight
 const below=top+h-r.bottom-10,above=r.top-top-10,up=below<200&&above>below
 const height=Math.min(330,Math.max(96,up?above:below)),width=Math.min(r.width,w-20)
 position.value={left:Math.max(left+10,Math.min(r.left,left+w-width-10))+'px',top:(up?r.top-height-4:r.bottom+4)+'px',width:width+'px',maxHeight:height+'px'}
}
async function show(initial=''){
 if(props.disabled)return
 open.value=true;query.value=initial;active.value=0;place();await nextTick();input.value?.focus()
}
function close(focus=false){open.value=false;if(focus)trigger.value?.focus()}
function choose(option){emit('update:modelValue',option.value);emit('change',option.value);close(true)}
async function move(step){active.value=Math.max(0,Math.min(filtered.value.length-1,active.value+step));await nextTick();popup.value?.querySelector('[data-active="true"]')?.scrollIntoView({block:'nearest'})}
function key(event){
 if(event.key==='Escape'){event.preventDefault();close(true)}
 else if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();move(event.key==='ArrowDown'?1:-1)}
 else if(event.key==='Enter'){event.preventDefault();if(filtered.value[active.value])choose(filtered.value[active.value])}
 else if(event.key==='Tab')close()
}
function triggerKey(event){
 if(['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();show()}
 else if(event.key.length===1&&!event.ctrlKey&&!event.metaKey&&event.key!==' '){event.preventDefault();show(event.key)}
}
function outside(event){if(!trigger.value?.contains(event.target)&&!popup.value?.contains(event.target))close()}
watch(query,()=>{active.value=0})
watch(()=>props.disabled,v=>{if(v)close()})
watch(open,value=>{
 const method=value?'addEventListener':'removeEventListener'
 document[method]('pointerdown',outside)
 window[method]('resize',place);window[method]('scroll',place,true)
 window.visualViewport?.[method]('resize',place);window.visualViewport?.[method]('scroll',place)
})
onBeforeUnmount(()=>{document.removeEventListener('pointerdown',outside);window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);window.visualViewport?.removeEventListener('resize',place);window.visualViewport?.removeEventListener('scroll',place)})
</script>
<template>
 <div class="search-select">
  <button ref="trigger" type="button" class="search-select-trigger" role="combobox" :aria-label="label" :aria-expanded="open" :aria-controls="id+'-list'" aria-haspopup="listbox" :disabled="disabled" @click="open?close():show()" @keydown="triggerKey">
   <span :class="{placeholder:!selected}">{{selected?.label||placeholder}}</span><span aria-hidden="true">⌄</span>
  </button>
  <Teleport :to="portalTarget">
   <div v-if="open" ref="popup" class="search-select-popup" :style="position" @keydown="key">
    <input ref="input" v-model="query" type="search" class="search-select-input" :placeholder="'Gõ để tìm '+label.toLowerCase()+'…'" :aria-label="'Tìm '+label.toLowerCase()" :aria-controls="id+'-list'" :aria-activedescendant="filtered.length?id+'-option-'+active:undefined" autocomplete="off"/>
    <div :id="id+'-list'" class="search-select-list" role="listbox" :aria-label="label">
     <template v-for="(option,i) in filtered" :key="option.value">
      <div v-if="option.group&&(i===0||filtered[i-1].group!==option.group)" class="search-select-group">{{option.group}}</div>
      <button :id="id+'-option-'+i" type="button" role="option" :aria-selected="modelValue===option.value" :data-active="active===i" class="search-select-option" @pointerdown.prevent @click="choose(option)" @mousemove="active=i">
       <span><strong>{{option.label}}</strong><small v-if="option.subtitle">{{option.subtitle}}</small></span><span v-if="modelValue===option.value" aria-hidden="true">✓</span>
      </button>
     </template>
     <div v-if="!filtered.length" class="search-select-empty" role="status">Không có kết quả phù hợp.</div>
    </div>
    <div class="search-select-count">{{filtered.length}} lựa chọn</div>
   </div>
  </Teleport>
 </div>
</template>
<style scoped>
.search-select{min-width:0;width:100%}
.search-select-trigger{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:37px;width:100%;padding:8px 12px;border:1px solid var(--lotus-border,#dce1e9);border-radius:6px;background:var(--lotus-surface,#fff);color:var(--lotus-text,#293448);font:inherit;font-size:13px;text-align:left;cursor:pointer}
.search-select-trigger>span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.placeholder{color:var(--lotus-muted,#748092)}
.search-select-trigger:focus-visible{outline:2px solid #a6b8f4;outline-offset:1px}.search-select-trigger:disabled{opacity:.55;cursor:default}
.search-select-popup{position:fixed;z-index:1000;display:flex;flex-direction:column;overflow:hidden;box-sizing:border-box;padding:6px;background:var(--lotus-surface,#fff);color:var(--lotus-text,#293448);border:1px solid var(--lotus-border,#dce1e9);border-radius:8px;box-shadow:0 8px 28px #14223926;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;font-size:13px}
.search-select-input{box-sizing:border-box;width:100%;height:36px;min-height:36px;flex-shrink:0;margin:0 0 5px;padding:7px 9px;border:1px solid var(--lotus-border,#dce1e9);border-radius:5px;background:var(--lotus-surface,#fff);color:inherit;font:inherit;font-size:16px;outline-offset:-1px}
.search-select-list{overflow-y:auto;overscroll-behavior:contain;min-height:0;flex:1;scroll-padding:5px}
.search-select-group{padding:7px 8px 4px;font-size:11px;font-weight:700;color:var(--lotus-muted,#748092)}
.search-select-option{display:flex;justify-content:space-between;gap:8px;width:100%;padding:8px;border:0;border-radius:4px;background:transparent;color:inherit;text-align:left;cursor:pointer;font:inherit;min-height:35px;white-space:normal}
.search-select-option[data-active=true]{background:var(--lotus-soft,#eef2fb)}.search-select-option[aria-selected=true]{color:var(--lotus-accent,#4058a8)}
.search-select-option strong{font-size:13px;font-weight:500}.search-select-option small{display:block;margin-top:2px;font-size:11px;color:var(--lotus-muted,#748092)}
.search-select-empty{padding:18px 8px;color:var(--lotus-muted,#748092)}.search-select-count{flex-shrink:0;border-top:1px solid var(--lotus-border,#dce1e9);padding:5px 8px 0;font-size:11px;color:var(--lotus-muted,#748092)}
</style>
