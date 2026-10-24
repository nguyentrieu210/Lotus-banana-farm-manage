<script setup>
import {computed,onBeforeUnmount,ref,watch} from 'vue'
import {ComboboxRoot,ComboboxAnchor,ComboboxInput,ComboboxTrigger,ComboboxPortal,ComboboxContent,ComboboxViewport,ComboboxItem,ComboboxItemIndicator} from 'reka-ui'
import LotusIcon from '../../LotusIcon.vue'
import {filterOptions} from '../../../option-search'
import {useDialogPortal} from '../portal-target'
// One desktop picker on reka-ui Combobox. Static `options` are filtered locally (accent-insensitive);
// `fetchOptions(search)` loads from the server instead. Options: {value,label,subtitle?,group?}.
// `allowCustom` keeps typed text as the value (Frappe Link fields validate on the server).
defineOptions({inheritAttrs:false})
const props=defineProps({modelValue:{type:[String,Number],default:''},options:{type:Array,default:()=>[]},fetchOptions:Function,displayValue:String,label:String,placeholder:{type:String,default:'Chọn hoặc gõ để tìm…'},hideValues:Boolean,disabled:Boolean,readonly:Boolean,required:Boolean,allowCustom:Boolean})
const emit=defineEmits(['update:modelValue','change','select'])
const search=ref(''),open=ref(false),remote=ref([]),loading=ref(false),error=ref(''),chosen=ref(null),anchor=ref(null),portalTo=ref('body')
// Inside a modal <dialog> everything outside is inert, so the list must render in that dialog (top layer).
const portalTarget=useDialogPortal()
function setOpen(value){if(value)portalTo.value=portalTarget(anchor.value?.$el);open.value=value}
let version=0,timer
// The input shows the chosen label; only text the user typed counts as a search (opening shows every option).
const selectedLabel=()=>props.displayValue||current.value?.label||''
const query=computed(()=>selectedLabel()&&search.value===selectedLabel()?'':search.value)
const rows=computed(()=>props.fetchOptions?remote.value:filterOptions(props.options,query.value))
const current=computed(()=>props.options.find(o=>o.value===props.modelValue)||(chosen.value?.value===props.modelValue?chosen.value:null))
const shown=()=>props.displayValue||current.value?.label||String(props.modelValue??'')
async function load(text){
 const request=++version;error.value='';loading.value=true
 try{const result=await props.fetchOptions(text);if(request===version)remote.value=result||[]}
 catch(e){if(request===version){remote.value=[];error.value=e?.message||'Chưa tải được danh sách.'}}
 finally{if(request===version)loading.value=false}
}
watch(search,text=>{
 if(props.allowCustom&&open.value)emit('update:modelValue',text)
 if(!props.fetchOptions||!open.value)return
 clearTimeout(timer);version++;remote.value=[];loading.value=true;timer=setTimeout(()=>load(query.value),150)
})
watch(open,value=>{if(value&&props.fetchOptions)load(query.value);if(!value){clearTimeout(timer);version++;loading.value=false}})
watch(()=>props.fetchOptions,()=>{clearTimeout(timer);version++;remote.value=[];if(open.value&&props.fetchOptions)load(query.value)})
onBeforeUnmount(()=>{clearTimeout(timer);version++})
function select(value){
 if(value==null)return
 const row=rows.value.find(o=>o.value===value)||props.options.find(o=>o.value===value)||{value,label:String(value)}
 chosen.value=row;emit('update:modelValue',value);emit('select',row);emit('change',value)
}
const groupStart=index=>rows.value[index].group&&(index===0||rows.value[index-1].group!==rows.value[index].group)
</script>
<template>
 <ComboboxRoot class="lotus-combobox" :model-value="modelValue" :open="open" ignore-filter open-on-click :reset-search-term-on-blur="!allowCustom" :disabled="disabled||readonly" @update:open="setOpen" @update:model-value="select">
  <ComboboxAnchor ref="anchor" class="lotus-combobox__anchor">
   <ComboboxInput v-model="search" v-bind="$attrs" class="lotus-combobox__input" :display-value="shown" :placeholder="placeholder" :required="required" :readonly="readonly" :aria-label="$attrs['aria-label']||label" autocomplete="off"/>
   <ComboboxTrigger class="lotus-combobox__trigger" aria-label="Mở danh sách lựa chọn" tabindex="-1"><LotusIcon name="chevron-down"/></ComboboxTrigger>
  </ComboboxAnchor>
  <ComboboxPortal :to="portalTo">
   <ComboboxContent class="lotus-combobox__content" position="popper" :side-offset="4" :collision-padding="8">
    <ComboboxViewport class="lotus-combobox__viewport">
     <div v-if="loading" class="lotus-combobox__state" role="status">Đang tải…</div>
     <div v-else-if="error" class="lotus-combobox__state lotus-combobox__state--error" role="alert">{{error}}</div>
     <div v-else-if="!rows.length" class="lotus-combobox__state" role="status">Không tìm thấy lựa chọn.</div>
     <template v-for="(row,index) in loading||error?[]:rows" :key="row.value">
      <div v-if="groupStart(index)" class="lotus-combobox__group" role="presentation">{{row.group}}</div>
      <ComboboxItem :value="row.value" class="lotus-combobox__item">
       <span class="lotus-combobox__text"><strong>{{row.label||row.value}}</strong><small v-if="row.subtitle||(!hideValues&&row.label&&row.label!==row.value)">{{row.subtitle||row.value}}</small></span>
       <ComboboxItemIndicator class="lotus-combobox__check"><LotusIcon name="tick"/></ComboboxItemIndicator>
      </ComboboxItem>
     </template>
    </ComboboxViewport>
   </ComboboxContent>
  </ComboboxPortal>
 </ComboboxRoot>
</template>
<style>
.lotus-combobox{min-width:0;width:100%}
.lotus-combobox__anchor{position:relative;display:flex;align-items:center;width:100%}
.lotus-combobox__input{box-sizing:border-box;width:100%;min-height:var(--lotus-control-height);padding:6px 34px 6px 12px;border:1px solid var(--lotus-border-strong);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);color:var(--lotus-text);font:inherit;font-size:var(--lotus-text-base);text-overflow:ellipsis}
.lotus-combobox__input:focus-visible{outline:none;border-color:var(--lotus-primary);box-shadow:var(--lotus-focus)}
.lotus-combobox__input[aria-invalid=true]{border-color:var(--lotus-danger)}
.lotus-combobox__input:disabled{opacity:.55;cursor:not-allowed}
.lotus-combobox__trigger{position:absolute;right:4px;display:grid;place-items:center;width:28px;height:28px;border:0;border-radius:var(--lotus-radius-sm);background:transparent;color:var(--lotus-muted);cursor:pointer}
.lotus-combobox__trigger .lotus-icon{width:16px;height:16px}
.lotus-combobox__content{z-index:2147482000;width:max(var(--reka-combobox-trigger-width),280px);max-width:calc(100vw - 16px);overflow:hidden;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-lg);background:var(--lotus-surface);color:var(--lotus-text);box-shadow:var(--lotus-shadow-lg);font-family:var(--lotus-font);font-size:var(--lotus-text-md)}
.lotus-combobox__viewport{max-height:min(320px,var(--reka-combobox-content-available-height));overflow-y:auto;overscroll-behavior:contain;padding:6px}
.lotus-combobox__group{padding:8px 8px 4px;font-size:var(--lotus-text-xs);font-weight:700;color:var(--lotus-muted)}
.lotus-combobox__item{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:36px;padding:6px 8px;border-radius:var(--lotus-radius-md);cursor:pointer;outline:none}
.lotus-combobox__item[data-highlighted]{background:var(--lotus-hover)}
.lotus-combobox__item[data-state=checked] strong{color:var(--lotus-primary-text)}
.lotus-combobox__text{min-width:0}
.lotus-combobox__text strong{display:block;font-weight:500}
.lotus-combobox__text small{display:block;margin-top:1px;font-size:var(--lotus-text-xs);color:var(--lotus-muted)}
.lotus-combobox__check{color:var(--lotus-primary-text)}.lotus-combobox__check .lotus-icon{width:16px;height:16px}
.lotus-combobox__state{padding:16px 8px;color:var(--lotus-muted);text-align:center}
.lotus-combobox__state--error{color:var(--lotus-danger)}
</style>
