<script setup>
import {NoticeBar,Loading} from 'vant'
const props=defineProps({kind:{type:String,default:'info'}})
// Tones follow lotus-tokens.css so feedback matches desktop.
const tones={error:['var(--lotus-danger)','var(--lotus-danger-soft)'],warning:['var(--lotus-warning-700)','var(--lotus-warning-soft)'],success:['var(--lotus-success-700)','var(--lotus-success-soft)'],info:['var(--lotus-info-700)','var(--lotus-info-soft)']}
</script>
<template><div class="lotus-pwa-feedback mobile-message" :class="{danger:kind==='error',success:kind==='success'}" :role="kind==='error'?'alert':'status'">
 <Loading v-if="kind==='loading'" size="18px"><slot/></Loading>
 <NoticeBar v-else wrapable :scrollable="false" :color="(tones[kind]||tones.info)[0]" :background="(tones[kind]||tones.info)[1]"><slot/></NoticeBar>
</div></template>
