<script setup>
import {computed} from 'vue'
import {FormField} from './ui/form-field'
import {Input} from './ui/input'
import {Textarea} from './ui/textarea'
import {Combobox} from './ui/combobox'
import Select from './ui/select/Select.vue'
import {DatePicker} from './ui/date-picker'
import LotusMobileInput from './LotusMobileInput.vue'
import LotusMobileSelect from './LotusMobileSelect.vue'
import MobileLinkField from './MobileLinkField.vue'
defineOptions({inheritAttrs:false})
const props=defineProps({mobile:Boolean,modelValue:{type:[String,Number],default:''},label:String,type:{type:String,default:'text'},options:Array,fetchOptions:Function,displayValue:String,searchable:{type:Boolean,default:true},required:Boolean,disabled:Boolean,hint:String,error:String})
const emit=defineEmits(['update:modelValue','select'])
const linked=computed(()=>!!props.options||!!props.fetchOptions)
const control=computed(()=>linked.value?(props.searchable?MobileLinkField:LotusMobileSelect):LotusMobileInput)
</script>
<template>
 <component v-if="mobile" :is="control" v-bind="$attrs" :model-value="modelValue" :label="label" :options="options" :fetch-options="fetchOptions" :display-value="displayValue" :searchable="searchable" :type="linked?undefined:type" :required="required" :disabled="disabled" :hint="hint" :error="error" @update:model-value="emit('update:modelValue',$event)" @select="emit('select',$event)"/>
 <FormField v-else :label="label" :required="required" :hint="hint" :error="error" v-slot="field">
  <Combobox v-if="linked&&searchable" v-bind="{...field,...$attrs}" :model-value="modelValue" :options="options" :fetch-options="fetchOptions" :display-value="displayValue" :disabled="disabled" @update:model-value="emit('update:modelValue',$event)" @select="emit('select',$event)"/>
  <Select v-else-if="options" v-bind="{...field,...$attrs}" :model-value="modelValue" :disabled="disabled" @update:model-value="emit('update:modelValue',$event)"><option v-if="!options.some(r=>r.value==='')" value="">Chọn…</option><option v-for="r in options" :key="r.value" :value="r.value">{{r.label}}</option></Select>
  <DatePicker v-else-if="type==='date'" v-bind="{...field,...$attrs}" :model-value="modelValue" :disabled="disabled" @update:model-value="emit('update:modelValue',$event)"/>
  <component v-else :is="type==='textarea'?Textarea:Input" v-bind="{...field,...$attrs}" :model-value="modelValue" :type="type" :disabled="disabled" @update:model-value="emit('update:modelValue',$event)"/>
 </FormField>
</template>
