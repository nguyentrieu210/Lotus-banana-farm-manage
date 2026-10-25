<script setup>
import ModalForm from './ModalForm.vue'
import LotusMobileButton from '../LotusMobileButton.vue'
// A form used by both desktop and the phone PWAs: desktop opens the standard ModalForm, `mobile` renders the same body inline
// with a title, "Đóng" and a full-width submit. Same props/slots as ModalForm (#secondary, #actions).
const props=defineProps({modelValue:Boolean,mobile:Boolean,title:{type:String,required:true},busy:Boolean,width:{type:String,default:'960px'},error:String,description:String,submitLabel:{type:String,default:'Lưu'},busyLabel:{type:String,default:'Đang lưu…'},cancelLabel:{type:String,default:'Hủy'},submitDisabled:Boolean,readonly:Boolean})
const emit=defineEmits(['update:modelValue','submit','cancel'])
function submit(){if(!props.busy&&!props.readonly&&!props.submitDisabled)emit('submit')}
</script>
<template>
 <ModalForm v-if="!mobile" :model-value="modelValue" v-bind="{title,busy,width,error,description,submitLabel,busyLabel,cancelLabel,submitDisabled,readonly}" @update:model-value="emit('update:modelValue',$event)" @submit="emit('submit')" @cancel="emit('cancel',$event)">
  <slot/>
  <template v-if="$slots.secondary" #secondary><slot name="secondary"/></template>
  <template v-if="$slots.actions" #actions><slot name="actions"/></template>
 </ModalForm>
 <section v-else-if="modelValue" class="lotus-mobile-form" :aria-label="title">
  <header class="lotus-mobile-form__header"><h3>{{title}}</h3><LotusMobileButton type="button" :disabled="busy" @click="emit('update:modelValue',false)">{{readonly?'Đóng':cancelLabel}}</LotusMobileButton></header>
  <p v-if="description" class="lotus-form-note">{{description}}</p>
  <p v-if="error" class="lotus-modal-form__error" role="alert">{{error}}</p>
  <form class="lotus-mobile-form__body" @submit.prevent="submit"><fieldset :disabled="busy">
   <slot/>
   <div class="lotus-mobile-form__actions"><slot name="secondary"/><slot name="actions"/><LotusMobileButton v-if="!readonly" type="submit" :disabled="busy||submitDisabled">{{busy?busyLabel:submitLabel}}</LotusMobileButton></div>
  </fieldset></form>
 </section>
</template>
<style>
.lotus-mobile-form{display:grid;gap:12px;min-width:0}
.lotus-mobile-form__header{display:flex;align-items:center;justify-content:space-between;gap:12px}
.lotus-mobile-form__header h3{margin:0;font-size:var(--lotus-text-md)}
.lotus-mobile-form__body>fieldset{display:grid;gap:12px;border:0;margin:0;padding:0;min-width:0}
.lotus-mobile-form__actions{display:grid;gap:8px}
</style>
