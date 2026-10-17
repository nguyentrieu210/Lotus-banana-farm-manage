<script setup>
import {Field,Icon,CellGroup} from 'vant'
import LotusMobileButton from './LotusMobileButton.vue'
import {computed,nextTick,ref,useId,watch} from 'vue'
import {useMobilePopup} from '../use-mobile-popup'
import {foldVietnamese} from '../warehouse-mobile-helpers'

const props=defineProps({
 modelValue:{type:String,default:''},
 options:{type:Array,default:()=>[]},
 placeholder:{type:String,default:'Gõ tên hoặc mã…'},
 loading:Boolean,
 disabled:Boolean
})
const emit=defineEmits(['update:modelValue','select'])
const root=ref(null),input=ref(null),opened=ref(false),active=ref(-1)
const id=useId()
const {popup,style,above:up,close,schedule,pointerStart,pointerMove,canChoose,highlight}=useMobilePopup(root,input,opened,()=>{active.value=-1})
const matches=computed(()=>{
 const q=foldVietnamese(props.modelValue.trim())
 const rows=q?props.options.filter(r=>foldVietnamese([r.label,r.value,r.description].join(' ')).includes(q)):props.options
 return rows.slice(0,12)
})
function open(){
 if(props.disabled)return
 opened.value=true;active.value=-1
 nextTick(()=>input.value?.focus())
}
function typed(event){
 emit('update:modelValue',event.target.value)
 opened.value=true
 active.value=-1
}
function choose(row,event){
 if(!canChoose(event))return
 emit('select',row)
 opened.value=false;active.value=-1
 input.value?.blur()
}
function keydown(event){
 if(event.isComposing)return
 if(event.key==='Escape'){opened.value=false;active.value=-1;input.value?.blur()}
 if(event.key==='ArrowDown'&&opened.value){event.preventDefault();active.value=Math.min(matches.value.length-1,active.value+1)}
 if(event.key==='ArrowUp'&&opened.value){event.preventDefault();active.value=Math.max(0,active.value-1)}
 if(event.key==='Enter'){
  event.preventDefault()
  if(opened.value&&matches.value.length)choose(matches.value[active.value<0?0:active.value])
  else input.value?.blur()
 }
}
watch(matches,()=>{active.value=-1;schedule()})
watch(()=>props.disabled,value=>{if(value)close()})
watch(active,value=>{if(value>=0)highlight(id+'-result-'+value)})
</script>

<template>
 <div ref="root" class="mobile-live-search">
  <Field class="mobile-live-box lotus-pwa-field" :border="false"><template #left-icon><Icon name="search"/></template><template #input>
   <input ref="input" type="search" :value="modelValue" :placeholder="placeholder" :disabled="disabled"
    :aria-label="placeholder" autocomplete="off" enterkeyhint="search" role="combobox" aria-autocomplete="list" :aria-expanded="opened"
    :aria-controls="id" :aria-activedescendant="opened&&active>=0?id+'-result-'+active:undefined"
    @focus="open" @click="open" @input="typed" @keydown="keydown"/>
   </template><template #button><LotusMobileButton v-if="modelValue" type="button" class="mobile-live-clear" aria-label="Xóa tìm kiếm"
    @click="emit('update:modelValue','');open()">×</LotusMobileButton>
   <span v-else-if="loading" class="mobile-live-wait" aria-label="Đang lọc">◌</span></template>
  </Field>
  <Teleport to="body"><div v-if="opened" ref="popup" :style="style" :id="id" class="mobile-link-options mobile-live-results mobile-floating-options" :class="{'mobile-link-up':up}" role="listbox"><CellGroup :border="false">
   <LotusMobileButton v-for="(row,i) in matches" :id="id+'-result-'+i" :key="row.value" type="button"
    role="option" :aria-selected="i===active" :class="{'is-highlighted':i===active}"
    @pointerdown="pointerStart" @pointermove="pointerMove" @click="choose(row,$event)">
    <span>{{row.label}}</span><small v-if="row.description">{{row.description}}</small>
   </LotusMobileButton>
   <p v-if="!matches.length&&loading" role="status">Đang tìm kết quả…</p>
   <p v-else-if="!matches.length">Chưa có kết quả. Gõ thêm để tìm trên hệ thống.</p>
   <p v-else-if="matches.length===12">Gõ thêm để lọc danh sách.</p>
  </CellGroup></div></Teleport>
 </div>
</template>
