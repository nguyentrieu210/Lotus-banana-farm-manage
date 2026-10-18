<script setup>
import {ConfigProvider} from 'vant'
import LotusMobileHeader from './LotusMobileHeader.vue'
import LotusMobileBottomNav from './LotusMobileBottomNav.vue'
import LotusMobileNotifications from './LotusMobileNotifications.vue'
import LotusMobileOnboarding from './LotusMobileOnboarding.vue'
import {mobileTheme} from '../mobile-ui-theme'
defineProps({app:{type:String,default:'warehouse'},title:{type:String,default:'Lotus'},tabs:{type:Array,required:true},activeTab:{type:String,required:true},back:Boolean,keyboardOpen:Boolean,disabled:Boolean,notifications:{type:Boolean,default:true},onboarding:{type:Boolean,default:true}})
const emit=defineEmits(['navigate','back'])
</script>
<template>
 <ConfigProvider class="lotus-pwa-shell" :class="{'lotus-pwa-keyboard':keyboardOpen}" :theme-vars="mobileTheme" theme-vars-scope="global">
  <LotusMobileHeader :title="title" :back="back" :disabled="disabled" @back="emit('back')"><template #right><LotusMobileNotifications v-if="notifications" :app="app"/><slot name="header-right"/></template></LotusMobileHeader>
  <slot/>
  <LotusMobileOnboarding v-if="onboarding" :app="app" :title="title"/>
  <LotusMobileBottomNav :items="tabs" :active="activeTab" :hidden="keyboardOpen" :disabled="disabled" @navigate="emit('navigate',$event)"/>
 </ConfigProvider>
</template>
