<script setup>
import {computed,nextTick,onMounted,onUnmounted,ref,useId,watch} from 'vue'
defineOptions({inheritAttrs:false})
const props=defineProps({modelValue:{type:String,default:''},displayValue:{type:String,default:''},options:{type:Array,default:()=>[]},fetchOptions:Function,hideValues:Boolean,disabled:Boolean,readonly:Boolean,required:Boolean,placeholder:{type:String,default:'Chọn hoặc tìm…'}})
const emit=defineEmits(['update:modelValue','select','change'])
const root=ref(null),input=ref(null),popup=ref(null),position=ref({}),isOpen=ref(false),query=ref(''),remote=ref([]),loading=ref(false),error=ref(''),selected=ref(0),id=useId()
let version=0,timer
const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').toLowerCase()
const rows=computed(()=>props.fetchOptions?remote.value:props.options.filter(row=>normalize(row.value+' '+row.label).includes(normalize(query.value))))
async function load(text){const request=++version;selected.value=0;error.value='';if(!props.fetchOptions)return;loading.value=true;try{const result=await props.fetchOptions(text);if(request===version)remote.value=result}catch(e){if(request===version){remote.value=[];error.value=e.message||'Chưa tải được danh sách.'}}finally{if(request===version)loading.value=false}}
function reposition(){if(!isOpen.value||!input.value)return;const rect=input.value.getBoundingClientRect();const above=window.innerHeight-rect.bottom<180&&rect.top>window.innerHeight-rect.bottom;position.value={left:Math.max(8,Math.min(rect.left,window.innerWidth-Math.max(rect.width,300)-8))+'px',width:Math.min(Math.max(rect.width,300),window.innerWidth-16)+'px',top:above?'auto':(rect.bottom+4)+'px',bottom:above?(window.innerHeight-rect.top+4)+'px':'auto',maxHeight:Math.min(280,Math.max(120,above?rect.top-12:window.innerHeight-rect.bottom-12))+'px'}}
async function show(){reposition();await nextTick();if(popup.value&&!popup.value.matches(':popover-open'))popup.value.showPopover?.()}
async function open(){if(props.disabled||props.readonly||isOpen.value)return;isOpen.value=true;query.value='';load('');await show();input.value.focus();input.value.select()}
function close(){isOpen.value=false;clearTimeout(timer);version++;loading.value=false}
function type(event){const text=event.target.value;query.value=text;emit('update:modelValue',text);isOpen.value=true;show();clearTimeout(timer);timer=setTimeout(()=>load(text),150)}
function choose(row){emit('update:modelValue',row.value);emit('select',row);emit('change',row.value);close()}
function outside(event){if(root.value&&!root.value.contains(event.target))close()}
function keys(event){if(event.key==='Escape'){event.stopPropagation();event.preventDefault();close()}else if(event.key==='Tab')close();else if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();if(!isOpen.value)open();else selected.value=(selected.value+(event.key==='ArrowDown'?1:-1)+rows.value.length)%Math.max(rows.value.length,1)}else if(event.key==='Enter'&&isOpen.value){event.preventDefault();if(rows.value[selected.value])choose(rows.value[selected.value])}}
watch(()=>props.disabled,value=>{if(value)close()})
onMounted(()=>{document.addEventListener('pointerdown',outside);window.addEventListener('resize',reposition);window.addEventListener('scroll',reposition,true)})
onUnmounted(()=>{document.removeEventListener('pointerdown',outside);window.removeEventListener('resize',reposition);window.removeEventListener('scroll',reposition,true);clearTimeout(timer);version++})
</script>
<template>
 <div ref="root" class="link-picker"><div class="link-picker-input"><input ref="input" v-bind="$attrs" :value="isOpen?query:(displayValue||modelValue)" :disabled="disabled" :readonly="readonly" :required="required" :placeholder="placeholder" role="combobox" aria-autocomplete="list" :aria-expanded="isOpen" :aria-controls="id+'-options'" :aria-activedescendant="isOpen&&rows[selected]?id+'-'+selected:undefined" autocomplete="off" @focus="open" @click="open" @input="type" @keydown="keys"><button type="button" tabindex="-1" aria-label="Mở danh sách lựa chọn" :disabled="disabled||readonly" @pointerdown.prevent @click="isOpen?close():open()">⌄</button></div>
  <div v-if="isOpen" ref="popup" popover="manual" :style="position" :id="id+'-options'" class="link-picker-options" role="listbox"><div v-if="loading" role="status">Đang tải…</div><div v-else-if="error" role="alert">{{error}}</div><template v-else><button v-for="(row,index) in rows" :id="id+'-'+index" :key="row.value" type="button" role="option" :aria-selected="index===selected" :class="{selected:index===selected}" @pointerdown.prevent @click="choose(row)"><strong>{{row.label||row.value}}</strong><small v-if="!hideValues">{{row.value}}</small></button><div v-if="!rows.length" role="status">Không tìm thấy lựa chọn.</div></template></div>
 </div>
</template>
