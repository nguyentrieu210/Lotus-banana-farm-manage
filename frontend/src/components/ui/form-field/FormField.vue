<script setup>
import {computed,useId} from 'vue'
// Desktop field wrapper: label, required mark, hint and error wired to the control by id.
// <FormField label="Họ tên" required :error="errors.employee_name" v-slot="field"><UiInput v-bind="field" v-model="form.employee_name"/></FormField>
const props=defineProps({label:String,hint:String,error:String,required:Boolean,id:String})
const generated=useId()
const fieldId=computed(()=>props.id||generated)
const field=computed(()=>({id:fieldId.value,required:props.required||undefined,'aria-invalid':props.error?'true':undefined,'aria-describedby':props.error?fieldId.value+'-error':props.hint?fieldId.value+'-hint':undefined}))
</script>
<template>
 <div class="lotus-field" :class="{'lotus-field--invalid':!!error}">
  <label v-if="label" :for="fieldId" class="lotus-field__label">{{label}}<span v-if="required" class="lotus-field__required" aria-hidden="true">*</span></label>
  <slot v-bind="field"/>
  <p v-if="error" :id="fieldId+'-error'" class="lotus-field__error">{{error}}</p>
  <p v-else-if="hint" :id="fieldId+'-hint'" class="lotus-field__hint">{{hint}}</p>
 </div>
</template>
<style>
.lotus-field{display:grid;gap:6px;min-width:0}
:root:root .lotus-field__label{display:block;font-size:var(--lotus-text-sm);font-weight:550;color:var(--lotus-text)}
.lotus-field__required{margin-left:2px;color:var(--lotus-danger)}
.lotus-field__hint,.lotus-field__error{margin:0;font-size:var(--lotus-text-sm);line-height:1.45}
.lotus-field__hint{color:var(--lotus-muted)}
.lotus-field__error{color:var(--lotus-danger)}
</style>
