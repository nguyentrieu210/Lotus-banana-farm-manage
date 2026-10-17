<script setup>
import {NoticeBar,Loading} from 'vant'
const props=defineProps({kind:{type:String,default:'info'}})
const tones={error:['#9c2e2e','#fff0ed'],warning:['#875c20','#fff6e8'],success:['#246c47','#edf8f1'],info:['#48675b','#edf3ef']}
</script>
<template><div class="lotus-pwa-feedback mobile-message" :class="{danger:kind==='error',success:kind==='success'}" :role="kind==='error'?'alert':'status'">
 <Loading v-if="kind==='loading'" size="18px"><slot/></Loading>
 <NoticeBar v-else wrapable :scrollable="false" :color="(tones[kind]||tones.info)[0]" :background="(tones[kind]||tones.info)[1]"><slot/></NoticeBar>
</div></template>
