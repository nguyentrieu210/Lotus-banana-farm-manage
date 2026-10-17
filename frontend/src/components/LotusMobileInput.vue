<script setup>
import {computed,useId} from 'vue'
import {Field} from 'vant'
defineOptions({inheritAttrs:false})
const props=defineProps({modelValue:{type:[String,Number],default:''},label:{type:String,default:''},type:{type:String,default:'text'},placeholder:String,required:Boolean,disabled:Boolean,rows:{type:[String,Number],default:2},inputmode:String,min:[String,Number],max:[String,Number],step:[String,Number],maxlength:[String,Number],name:String})
const emit=defineEmits(['update:modelValue'])
const value=computed({get:()=>props.modelValue,set:v=>emit('update:modelValue',v)})
const id=useId()
</script>
<template>
 <Field class="lotus-pwa-field" :label="label||undefined" :required="required" :disabled="disabled" :border="false" label-align="top" :id="id">
  <template #input>
   <textarea v-if="type==='textarea'" v-bind="$attrs" :id="id" :aria-label="$attrs['aria-label']||label||placeholder" v-model="value" class="van-field__control" :placeholder="placeholder" :required="required" :disabled="disabled" :rows="rows" :maxlength="maxlength" :name="name"/>
   <input v-else v-bind="$attrs" :id="id" :aria-label="$attrs['aria-label']||label||placeholder" v-model="value" class="van-field__control" :type="type" :placeholder="placeholder" :required="required" :disabled="disabled" :inputmode="inputmode" :min="min" :max="max" :step="step" :maxlength="maxlength" :name="name"/>
  </template>
 </Field>
</template>
