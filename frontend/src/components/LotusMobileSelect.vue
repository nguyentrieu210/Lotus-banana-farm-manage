<script setup>
import {computed,useId} from 'vue'
import {Field,Icon} from 'vant'
defineOptions({inheritAttrs:false})
const props=defineProps({modelValue:{type:[String,Number],default:''},label:String,options:Array,placeholder:String,disabled:Boolean,required:Boolean,hint:String,error:String})
const emit=defineEmits(['update:modelValue'])
const value=computed({get:()=>props.modelValue,set:v=>emit('update:modelValue',v)})
const id=useId()
</script>
<template>
 <Field class="lotus-pwa-field lotus-pwa-select" :id="id" :label="label" label-align="top" :required="required" :disabled="disabled" :border="false" :error="!!error" :error-message="error||undefined">
  <template #input>
   <select v-bind="$attrs" :id="id" v-model="value" class="van-field__control" :disabled="disabled" :required="required" :aria-label="$attrs['aria-label']||label||placeholder" :aria-invalid="!!error" :aria-describedby="hint&&!error?id+'-hint':undefined">
    <template v-if="options"><option v-if="placeholder&&!options.some(r=>r.value==='')" value="" disabled>{{placeholder}}</option><option v-for="r in options" :key="r.value??r" :value="r.value??r">{{r.label??r}}</option></template><slot v-else/>
   </select>
   <Icon class="lotus-pwa-select-arrow" name="arrow-down" aria-hidden="true"/>
  </template>
 </Field>
 <small v-if="hint&&!error" :id="id+'-hint'" class="lotus-pwa-field-hint">{{hint}}</small>
</template>