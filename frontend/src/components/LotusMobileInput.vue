<script setup>
import {computed,ref,useId} from 'vue'
import {Field} from 'vant'
import {formatMoneyInput,reformatMoneyInput} from '../money-format.js'
defineOptions({inheritAttrs:false})
const props=defineProps({modelValue:{type:[String,Number],default:''},label:{type:String,default:''},type:{type:String,default:'text'},placeholder:String,required:Boolean,disabled:Boolean,rows:{type:[String,Number],default:2},inputmode:String,min:[String,Number],max:[String,Number],step:[String,Number],maxlength:[String,Number],name:String,hint:String,error:String})
const emit=defineEmits(['update:modelValue'])
const value=computed({get:()=>props.modelValue,set:v=>emit('update:modelValue',v)})
const id=useId()
// Money: the text stays as typed while focused (so "," / "." decimals are not re-read halfway), grouped again on blur.
const typing=ref(null)
const moneyText=computed(()=>typing.value??formatMoneyInput(props.modelValue))
function moneyInput(event){const v=reformatMoneyInput(event.target);typing.value=event.target.value;emit('update:modelValue',v)}
</script>
<template>
 <Field class="lotus-pwa-field" :label="label||undefined" :required="required" :disabled="disabled" :border="false" label-align="top" :id="id" :error="!!error" :error-message="error||undefined">
  <template #input>
   <textarea v-if="type==='textarea'" v-bind="$attrs" :id="id" :aria-label="$attrs['aria-label']||label||placeholder" :aria-invalid="!!error" :aria-describedby="hint&&!error?id+'-hint':undefined" v-model="value" class="van-field__control" :placeholder="placeholder" :required="required" :disabled="disabled" :rows="rows" :maxlength="maxlength" :name="name"/>
   <input v-else-if="type==='money'" v-bind="$attrs" :id="id" :aria-label="$attrs['aria-label']||label||placeholder" :aria-invalid="!!error" :aria-describedby="hint&&!error?id+'-hint':undefined" :value="moneyText" class="van-field__control lotus-pwa-money" type="text" inputmode="decimal" autocomplete="off" :placeholder="placeholder" :required="required" :disabled="disabled" :name="name" @focus="typing=$event.target.value" @input="moneyInput" @blur="typing=null"/>
   <input v-else v-bind="$attrs" :id="id" :aria-label="$attrs['aria-label']||label||placeholder" :aria-invalid="!!error" :aria-describedby="hint&&!error?id+'-hint':undefined" v-model="value" class="van-field__control" :type="type" :placeholder="placeholder" :required="required" :disabled="disabled" :inputmode="inputmode" :min="min" :max="max" :step="step" :maxlength="maxlength" :name="name"/>
  </template>
 </Field>
 <small v-if="hint&&!error" :id="id+'-hint'" class="lotus-pwa-field-hint">{{hint}}</small>
</template>