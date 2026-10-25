<script setup>
import {CheckboxRoot,CheckboxIndicator} from 'reka-ui'
import LotusIcon from '../../LotusIcon.vue'
// Accessible checkbox (button role="checkbox"); v-model is a boolean.
defineOptions({inheritAttrs:false})
defineProps({modelValue:{type:Boolean,default:false},disabled:Boolean,required:Boolean,id:String})
const emit=defineEmits(['update:modelValue'])
</script>
<template>
 <CheckboxRoot v-bind="$attrs" :id="id" class="lotus-checkbox" :model-value="modelValue" :disabled="disabled" :required="required" @update:model-value="value=>emit('update:modelValue',value===true)">
  <CheckboxIndicator class="lotus-checkbox__indicator"><LotusIcon name="tick"/></CheckboxIndicator>
 </CheckboxRoot>
</template>
<style>
.lotus-checkbox{display:inline-flex;align-items:center;justify-content:center;flex:none;width:18px;height:18px;padding:0;border:1px solid var(--lotus-border-strong);border-radius:4px;background:var(--lotus-surface);color:var(--lotus-on-primary);cursor:pointer}
.lotus-checkbox:focus-visible{outline:2px solid var(--lotus-primary);outline-offset:2px}
.lotus-checkbox[data-state=checked]{border-color:var(--lotus-primary);background:var(--lotus-primary)}
.lotus-checkbox:disabled{opacity:.5;cursor:not-allowed}
.lotus-checkbox__indicator .lotus-icon{width:14px;height:14px}
</style>
