<script setup>
import {Field,Icon,CellGroup} from 'vant'
import LotusMobileSelect from './LotusMobileSelect.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import {computed,nextTick,onBeforeUnmount,ref,watch,useId} from 'vue'
import {useMobilePopup} from '../use-mobile-popup'
import {matchesOption} from '../option-search.js'
const props=defineProps({
 modelValue:{type:String,default:''},
 options:{type:Array,default:()=>[]},
 fetchOptions:Function,displayValue:String,hint:String,error:String,
 placeholder:{type:String,default:'Chạm để chọn hoặc gõ tìm…'},
 disabled:Boolean,required:Boolean,label:String,ariaLabel:String,
 searchable:{default:'auto'}
})
const emit=defineEmits(['update:modelValue','select'])
const root=ref(null),input=ref(null),open=ref(false),query=ref(''),typing=ref(false)
const remote=ref([]),loading=ref(false),remoteError=ref(''),selected=ref(null)
let version=0,timer
async function load(text){
 const id=++version;loading.value=true;remoteError.value=''
 try{const rows=await props.fetchOptions(text);if(id===version)remote.value=rows||[]}
 catch(e){if(id===version){remote.value=[];remoteError.value=e.message||'Chưa tải được danh sách.'}}
 finally{if(id===version)loading.value=false}
}
const listId=useId(),active=ref(-1)
const {popup,style,above,close,schedule,pointerStart,pointerMove,canChoose,highlight}=useMobilePopup(root,input,open,()=>{typing.value=false;active.value=-1})
const searchEnabled=computed(()=>props.searchable==='auto'?true:!!props.searchable)
const chosen=computed(()=>props.options.find(r=>r.value===props.modelValue)||(selected.value?.value===props.modelValue?selected.value:null))
const shown=computed(()=>open.value&&typing.value?query.value:props.displayValue||chosen.value?.label||props.modelValue||'')
const filtered=computed(()=>{
 // same accent/space/dash-insensitive search as the desktop Combobox
 const q=query.value.trim()
 return (props.fetchOptions?remote.value:q?props.options.filter(r=>matchesOption(r,q)):props.options).slice(0,60)
})
function reveal(){
 if(props.disabled||open.value)return
 open.value=true;typing.value=false;query.value='';active.value=-1
 nextTick(()=>{input.value?.focus();if(chosen.value)input.value?.select()})
}
function changed(event){
 typing.value=true;query.value=event.target.value
 active.value=-1;open.value=true
 // Search is tentative. Commit a link only when an option is selected.
 schedule()
}
function choose(row,event){
 if(!canChoose(event))return
 emit('update:modelValue',row.value)
 selected.value=row;emit('select',row)
 query.value='';typing.value=false;open.value=false;active.value=-1
 input.value?.blur()
}
function keydown(event){
 if(event.isComposing)return
 if(event.key==='Escape'){open.value=false;typing.value=false;active.value=-1;input.value?.blur()}
 else if(event.key==='ArrowDown'&&open.value){event.preventDefault();active.value=Math.min(filtered.value.length-1,active.value+1)}
 else if(event.key==='ArrowUp'&&open.value){event.preventDefault();active.value=Math.max(0,active.value-1)}
 else if(event.key==='Enter'&&open.value){event.preventDefault();if(!loading.value&&!remoteError.value&&filtered.value.length)choose(filtered.value[active.value<0?0:active.value])}
 if(active.value>=0)highlight(listId+'-option-'+active.value)
}
watch(()=>props.disabled,value=>{if(value)close()})
watch(filtered,()=>{active.value=-1;schedule()})
watch(query,text=>{if(!props.fetchOptions||!open.value)return;clearTimeout(timer);version++;remote.value=[];loading.value=true;timer=setTimeout(()=>load(text),150)})
watch(open,value=>{clearTimeout(timer);if(value&&props.fetchOptions)load(query.value);else if(!value){version++;loading.value=false}})
watch(()=>props.fetchOptions,()=>{version++;remote.value=[];if(open.value&&props.fetchOptions)load(query.value)})
onBeforeUnmount(()=>{clearTimeout(timer);version++})
</script>
<template>
 <div ref="root" class="mobile-link-field" :class="{'lotus-labeled-link':!!label}">
  <div v-if="!searchEnabled" class="mobile-link-native-box">
   <LotusMobileSelect :label="label" :aria-label="ariaLabel||label||placeholder" :model-value="modelValue" :options="options" :placeholder="placeholder" :disabled="disabled" :required="required" @update:modelValue="emit('update:modelValue',$event)"/>
  </div>
  <Field v-else class="mobile-link-box lotus-pwa-field" :id="listId+'-input'" :label="label" label-align="top" :required="required" :disabled="disabled" :border="false" :error="!!error" :error-message="error"><template #input>
   <input ref="input" :id="listId+'-input'" type="search" :value="shown" :placeholder="placeholder" :required="required"
    :disabled="disabled" :aria-label="ariaLabel||label||placeholder" autocomplete="off" autocorrect="off" :spellcheck="false" enterkeyhint="done" role="combobox" aria-autocomplete="list"
    :aria-expanded="open" :aria-controls="listId" :aria-activedescendant="open&&active>=0?listId+'-option-'+active:undefined" @focus="reveal" @click="reveal" @input="changed" @keydown="keydown"/>
   </template><template #button><LotusMobileButton type="button" aria-label="Chọn trong danh sách" :disabled="disabled" @click="open?close():reveal()"><Icon name="arrow-down"/></LotusMobileButton></template>
  </Field>
  <small v-if="hint&&!error" class="lotus-pwa-field-hint">{{hint}}</small>
  <Teleport to="body"><div v-if="open" ref="popup" :style="style" :id="listId" class="mobile-link-options mobile-floating-options" :class="{'mobile-link-up':above}" role="listbox"><CellGroup :border="false">
   <p v-if="loading" role="status">Đang tải…</p><p v-else-if="remoteError" role="alert">{{remoteError}}</p>
   <LotusMobileButton v-for="(r,i) in loading||remoteError?[]:filtered" :id="listId+'-option-'+i" :key="r.value" type="button" role="option" :aria-selected="r.value===modelValue" :class="{'is-highlighted':i===active}" @pointerdown="pointerStart" @pointermove="pointerMove" @click="choose(r,$event)">
    <span>{{r.label}}</span><small v-if="r.value!==r.label">{{r.value}}</small>
   </LotusMobileButton>
   <p v-if="!loading&&!remoteError&&!filtered.length">Không tìm thấy. Thử tên hoặc mã khác.</p>
   <p v-else-if="filtered.length===60">Gõ thêm để thu hẹp danh sách.</p>
  </CellGroup></div></Teleport>
 </div>
</template>
