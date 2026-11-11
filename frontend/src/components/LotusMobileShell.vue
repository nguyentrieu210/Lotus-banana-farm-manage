<script setup>
import {computed,ref} from 'vue'
import {ConfigProvider,PullRefresh} from 'vant'
import LotusMobileHeader from './LotusMobileHeader.vue'
import LotusMobileBottomNav from './LotusMobileBottomNav.vue'
import LotusMobileNotifications from './LotusMobileNotifications.vue'
import LotusMobileSignInbox from './LotusMobileSignInbox.vue'
import LotusMobileOnboarding from './LotusMobileOnboarding.vue'
import LotusMobileAiChat from './LotusMobileAiChat.vue'
import {mobileTheme} from '../mobile-ui-theme'
import LotusIcon from './LotusIcon.vue'
import LotusMobileNetBar from './LotusMobileNetBar.vue'
import {useUiMode} from '../ui-mode'
const props=defineProps({app:{type:String,default:'warehouse'},user:{type:String,default:''},title:{type:String,default:'Lotus'},tabs:{type:Array,required:true},activeTab:{type:String,required:true},back:Boolean,keyboardOpen:Boolean,disabled:Boolean,notifications:{type:Boolean,default:true},onboarding:{type:Boolean,default:true},refresh:Function,refreshable:Boolean})
const emit=defineEmits(['navigate','back'])
// Pull down to reload the current list. Apps enable it only on root screens so forms in progress are never reloaded.
const pulling=ref(false)
async function pull(){try{await props.refresh?.()}finally{pulling.value=false}}
// Follow the phone's light/dark setting, unless the person turned on the outdoor mode (spec 004, FR-025): a
// high-contrast light mode for the sun, kept on this phone. ui-mode.js switches the Lotus tokens; Vant follows them.
const {mode,outdoor,setOutdoor}=useUiMode({followSystem:true,allowOutdoor:true})
const dark=computed(()=>mode.value==='dark')
</script>
<template>
 <ConfigProvider class="lotus-pwa-shell" :class="{'lotus-pwa-keyboard':keyboardOpen}" :theme="dark?'dark':'light'" :theme-vars="mobileTheme" theme-vars-scope="global">
  <LotusMobileHeader :title="title" :back="back" :disabled="disabled" @back="emit('back')"><template #right><button type="button" class="lotus-pwa-outdoor" :aria-pressed="outdoor" :aria-label="outdoor?'Tắt chế độ ngoài trời':'Bật chế độ ngoài trời'" :title="outdoor?'Tắt chế độ ngoài trời':'Chế độ ngoài trời: chữ to, tương phản cao'" @click="setOutdoor(!outdoor)"><LotusIcon name="sun"/></button><LotusMobileSignInbox v-if="notifications"/><LotusMobileNotifications v-if="notifications" :app="app"/><slot name="header-right"/></template></LotusMobileHeader>
  <LotusMobileNetBar/>
  <PullRefresh v-model="pulling" class="lotus-pwa-pull" :disabled="!refresh||!refreshable||keyboardOpen||disabled" pulling-text="Kéo xuống để tải lại" loosing-text="Thả ra để tải lại" loading-text="Đang tải lại…" success-text="Đã cập nhật" :success-duration="700" @refresh="pull"><slot/></PullRefresh>
  <LotusMobileOnboarding v-if="onboarding" :app="app" :title="title"/>
  <LotusMobileBottomNav :items="tabs" :active="activeTab" :hidden="keyboardOpen" :disabled="disabled" @navigate="emit('navigate',$event)"/>
  <LotusMobileAiChat :user="user" :push-app="app" :keyboard-open="keyboardOpen" :disabled="disabled"/>
 </ConfigProvider>
</template>
