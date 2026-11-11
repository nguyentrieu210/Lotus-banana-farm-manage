<script setup>
import {useId} from 'vue'
import {SwitchRoot,SwitchThumb} from 'reka-ui'
// On/off setting (spec 004, User Story 3), e.g. "Chế độ ngoài trời". reka-ui gives role=switch and the keyboard.
defineProps({label:String,disabled:Boolean})
const model=defineModel({type:Boolean,default:false})
const id=useId()
</script>
<template>
 <span class="lotus-switch"><SwitchRoot :id="id" v-model="model" class="lotus-switch__root" :disabled="disabled"><SwitchThumb class="lotus-switch__thumb"/></SwitchRoot><label v-if="label||$slots.default" :for="id"><slot>{{label}}</slot></label></span>
</template>

<style>
/* Kit classes (spec 004): unscoped on purpose, the class names are the kit contract. */
.lotus-switch{display:inline-flex;align-items:center;gap:10px;color:var(--lotus-text);font-size:var(--lotus-text-md);cursor:pointer}
.lotus-switch__root{position:relative;flex:none;width:38px;height:22px;padding:0;border:0;border-radius:var(--lotus-radius-full);background:var(--lotus-border-control);cursor:pointer;transition:background var(--lotus-motion) var(--lotus-ease)}
.lotus-switch__root[data-state="checked"]{background:var(--lotus-primary-solid)}
.lotus-switch__root:focus-visible{outline:none;box-shadow:var(--lotus-focus)}
.lotus-switch__root[data-disabled]{opacity:.5;cursor:not-allowed}
.lotus-switch__thumb{display:block;width:18px;height:18px;border-radius:50%;background:#fff;box-shadow:var(--lotus-shadow-sm);transform:translateX(2px);transition:transform var(--lotus-motion) var(--lotus-ease)}
.lotus-switch__root[data-state="checked"] .lotus-switch__thumb{transform:translateX(18px)}
/* style.css (legacy layer) makes every <label> a 12px column; kit labels keep their own layout. */
.lotus-switch label{display:inline;flex-direction:row;gap:0;font-size:inherit;font-weight:inherit;cursor:pointer}
</style>
