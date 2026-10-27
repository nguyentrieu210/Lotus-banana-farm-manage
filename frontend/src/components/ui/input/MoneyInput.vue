<script setup>
import {cn} from '@/lib/utils'
import {formatMoneyInput,reformatMoneyInput} from '../../../money-format.js'
// Money field: shows 1.250.000 while typing, emits the plain number ('' when empty).
defineOptions({inheritAttrs:false})
const props=defineProps({modelValue:{type:[String,Number],default:''},disabled:{type:Boolean,default:false}})
const emit=defineEmits(['update:modelValue'])
function onInput(event){emit('update:modelValue',reformatMoneyInput(event.target))}
</script>
<template>
  <input
    v-bind="$attrs"
    type="text"
    inputmode="decimal"
    autocomplete="off"
    :value="formatMoneyInput(modelValue)"
    :disabled="disabled"
    :class="cn('flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm text-right tabular-nums shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring aria-[invalid=true]:border-destructive aria-[invalid=true]:focus-visible:ring-destructive disabled:cursor-not-allowed disabled:opacity-50',$attrs.class)"
    @input="onInput"
  />
</template>
