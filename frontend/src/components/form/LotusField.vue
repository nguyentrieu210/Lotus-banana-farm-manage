<script setup>
import {computed,useId} from 'vue'
import {FormField} from '../ui/form-field'
import {Input} from '../ui/input'
import {Textarea} from '../ui/textarea'
import {Combobox} from '../ui/combobox'
import Select from '../ui/select/Select.vue'
import {DatePicker} from '../ui/date-picker'
import {Checkbox} from '../ui/checkbox'
import {FileInput} from '../ui/file-input'
import MonthPicker from '../MonthPicker.vue'
import LotusMobileInput from '../LotusMobileInput.vue'
import LotusMobileSelect from '../LotusMobileSelect.vue'
import LotusMobileCheck from '../LotusMobileCheck.vue'
import LotusMobileFile from '../LotusMobileFile.vue'
import MobileLinkField from '../MobileLinkField.vue'
// The one data-entry field for every screen. Desktop: FormField (label, *, hint, error) + a ui control; `mobile`: LotusMobile* controls.
// type: text | number | money | date | month | select | combobox | textarea | checkbox | file (email/tel/password render as inputs).
// `options` ([{value,label}] or strings) give a searchable Combobox, or a Select with :searchable="false"; `fetchOptions` searches the server.
// <LotusField v-model="form.posting_date" label="Ngày" type="date" required/>
defineOptions({inheritAttrs:false})
const props=defineProps({
 modelValue:{type:[String,Number,Boolean,Array,Object],default:''},label:String,type:{type:String,default:'text'},
 options:Array,searchable:{type:Boolean,default:undefined},fetchOptions:Function,displayValue:String,
 required:Boolean,disabled:Boolean,readonly:Boolean,hint:String,error:String,placeholder:String,
 emptyOption:{type:String,default:'Chọn…'},currency:{type:String,default:'VND'},wide:Boolean,mobile:Boolean
})
const emit=defineEmits(['update:modelValue','select','change'])
const id=useId()
const choices=computed(()=>(props.options||[]).map(o=>o!==null&&typeof o==='object'?o:{value:o,label:String(o)}))
const kind=computed(()=>{
 if(['checkbox','file','date','month','textarea','money','select'].includes(props.type))return props.type
 if(props.fetchOptions||props.type==='combobox')return 'combobox'
 if(props.options)return props.searchable===false?'select':'combobox'
 return 'input'
})
const numeric=computed(()=>kind.value==='money'||props.type==='number')
const moneyHint=computed(()=>kind.value==='money'&&props.modelValue!==''&&props.modelValue!=null&&!Number.isNaN(Number(props.modelValue))?Number(props.modelValue).toLocaleString('vi-VN',{style:'currency',currency:props.currency}):'')
const hintText=computed(()=>props.hint||moneyHint.value||undefined)
const mobileControl=computed(()=>kind.value==='combobox'?MobileLinkField:kind.value==='select'?LotusMobileSelect:LotusMobileInput)
const mobileType=computed(()=>numeric.value?'number':['date','month','textarea'].includes(kind.value)?kind.value:props.type==='combobox'?'text':props.type)
function set(value){emit('update:modelValue',value);emit('change',value)}
</script>

<template>
 <LotusMobileCheck v-if="mobile&&kind==='checkbox'" v-bind="$attrs" class="lotus-mobile-check-field" :model-value="!!modelValue" :disabled="disabled||readonly" @update:model-value="set">{{label}}</LotusMobileCheck>
 <div v-else-if="mobile&&kind==='file'" class="lotus-mobile-file-field"><span class="lotus-mobile-file-field__label">{{label}}<span v-if="required" class="lotus-field__required" aria-hidden="true">*</span></span><LotusMobileFile v-bind="$attrs" :aria-label="label" :required="required" :disabled="disabled" @change="event=>set(event.target.files?.[0]||null)"/><small v-if="error||hint" class="lotus-pwa-field-hint">{{error||hint}}</small></div>
 <component v-else-if="mobile&&!fetchOptions" :is="mobileControl" v-bind="$attrs" :model-value="modelValue" :label="label" :options="kind==='combobox'||kind==='select'?choices:undefined" :type="mobileControl===LotusMobileInput?mobileType:undefined" :placeholder="placeholder" :required="required" :disabled="disabled||readonly" :hint="hintText" :error="error" @update:model-value="value=>set(numeric&&value!==''?Number(value):value)"/>
 <div v-else-if="kind==='checkbox'" class="lotus-field lotus-field--check" :class="{'lotus-field--invalid':!!error,'lotus-field--wide':wide}">
  <div class="lotus-field--check__row"><Checkbox v-bind="$attrs" :id="id" :model-value="!!modelValue" :disabled="disabled||readonly" :required="required" :aria-invalid="error?'true':undefined" :aria-describedby="error?id+'-error':hint?id+'-hint':undefined" @update:model-value="set"/><label :for="id" class="lotus-field__label">{{label}}<span v-if="required" class="lotus-field__required" aria-hidden="true">*</span></label></div>
  <p v-if="error" :id="id+'-error'" class="lotus-field__error">{{error}}</p>
  <p v-else-if="hint" :id="id+'-hint'" class="lotus-field__hint">{{hint}}</p>
 </div>
 <FormField v-else :label="label" :required="required" :hint="hintText" :error="error" :class="{'lotus-field--wide':wide}" v-slot="field">
  <Combobox v-if="kind==='combobox'" v-bind="{...field,...$attrs}" :model-value="modelValue" :options="choices" :fetch-options="fetchOptions" :display-value="displayValue" :placeholder="placeholder" :disabled="disabled" :readonly="readonly" :required="required" :label="label" @update:model-value="set" @select="emit('select',$event)"/>
  <Select v-else-if="kind==='select'" v-bind="{...field,...$attrs}" :model-value="modelValue" :disabled="disabled||readonly" @update:model-value="set"><option v-if="emptyOption!==null" value="">{{emptyOption}}</option><option v-for="o in choices" :key="o.value" :value="o.value" :disabled="o.disabled">{{o.label}}</option></Select>
  <DatePicker v-else-if="kind==='date'" v-bind="{...field,...$attrs}" :model-value="modelValue" :disabled="disabled" :readonly="readonly" :required="required" :label="label" @update:model-value="set"/>
  <MonthPicker v-else-if="kind==='month'" v-bind="{...field,...$attrs}" :model-value="modelValue" :disabled="disabled||readonly" :label="label" @update:model-value="set"/>
  <Textarea v-else-if="kind==='textarea'" v-bind="{...field,...$attrs}" :model-value="modelValue" :placeholder="placeholder" :disabled="disabled" :readonly="readonly" @update:model-value="set"/>
  <FileInput v-else-if="kind==='file'" v-bind="{...field,...$attrs}" :disabled="disabled||readonly" :required="required" @update:model-value="set" @change="emit('change',$event)"/>
  <Input v-else v-bind="{...field,...$attrs}" :model-value="modelValue" :type="numeric?'number':type" :model-modifiers="numeric?{number:true}:{}" :step="numeric?($attrs.step??'any'):$attrs.step" :placeholder="placeholder" :disabled="disabled" :readonly="readonly" @update:model-value="set"/>
 </FormField>
</template>

<style>
.lotus-field--wide{grid-column:1/-1}
.lotus-field--check{align-content:start}
.lotus-field--check__row{display:flex;align-items:center;gap:8px;min-height:36px}
.lotus-field--check__row .lotus-field__label{font-weight:500;cursor:pointer}
.lotus-mobile-file-field{display:grid;gap:4px;padding:0 var(--lotus-space-4)}
.lotus-mobile-file-field__label{font-size:var(--lotus-text-sm);font-weight:550;color:var(--lotus-text)}
</style>
