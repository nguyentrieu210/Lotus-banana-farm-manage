<script setup>
import {ref,computed} from 'vue'
import {cn} from '@/lib/utils'
import {formatMoneyInput,reformatMoneyInput} from '../../../money-format.js'
// Number field (money, quantities): accepts "," or "." for decimals and pasted "26,571,428.571"; emits the plain number ('' when empty).
// While focused the text stays as typed; on blur it shows the Vietnamese form 26.571.428,571.
defineOptions({inheritAttrs:false})
const props=defineProps({modelValue:{type:[String,Number],default:''},disabled:{type:Boolean,default:false}})
const emit=defineEmits(['update:modelValue','blur','focus'])
const typing=ref(null)
const shown=computed(()=>typing.value??formatMoneyInput(props.modelValue))
function onFocus(event){typing.value=event.target.value;emit('focus',event)}
function onInput(event){const value=reformatMoneyInput(event.target);typing.value=event.target.value;emit('update:modelValue',value)}
function onBlur(event){typing.value=null;emit('blur',event)}
</script>
<template>
  <input
    v-bind="$attrs"
    type="text"
    inputmode="decimal"
    autocomplete="off"
    :value="shown"
    :disabled="disabled"
    :class="cn('flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm text-right tabular-nums shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring aria-[invalid=true]:border-destructive aria-[invalid=true]:focus-visible:ring-destructive disabled:cursor-not-allowed disabled:opacity-50',$attrs.class)"
    @focus="onFocus"
    @input="onInput"
    @blur="onBlur"
  />
</template>
