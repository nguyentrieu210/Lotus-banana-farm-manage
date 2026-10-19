<script setup>
import {ref,onMounted,onUnmounted} from 'vue'
import {ConfigProvider,PullRefresh} from 'vant'
import LotusMobileHeader from './LotusMobileHeader.vue'
import LotusMobileBottomNav from './LotusMobileBottomNav.vue'
import LotusMobileNotifications from './LotusMobileNotifications.vue'
import LotusMobileOnboarding from './LotusMobileOnboarding.vue'
import {mobileTheme} from '../mobile-ui-theme'
const props=defineProps({app:{type:String,default:'warehouse'},title:{type:String,default:'Lotus'},tabs:{type:Array,required:true},activeTab:{type:String,required:true},back:Boolean,keyboardOpen:Boolean,disabled:Boolean,notifications:{type:Boolean,default:true},onboarding:{type:Boolean,default:true},refresh:Function,refreshable:Boolean})
const emit=defineEmits(['navigate','back'])
// Pull down to reload the current list. Apps enable it only on root screens so forms in progress are never reloaded.
const pulling=ref(false)
async function pull(){try{await props.refresh?.()}finally{pulling.value=false}}
// Follow the phone's light/dark setting: .dark switches the Lotus tokens, Vant gets its dark theme.
const dark=ref(false)
const scheme=typeof window!=='undefined'&&window.matchMedia?window.matchMedia('(prefers-color-scheme: dark)'):null
function applyScheme(){dark.value=!!scheme?.matches;document.documentElement.classList.toggle('dark',dark.value);document.documentElement.style.colorScheme=dark.value?'dark':'light'}
onMounted(()=>{applyScheme();scheme?.addEventListener?.('change',applyScheme)})
onUnmounted(()=>scheme?.removeEventListener?.('change',applyScheme))
</script>
<template>
 <ConfigProvider class="lotus-pwa-shell" :class="{'lotus-pwa-keyboard':keyboardOpen}" :theme="dark?'dark':'light'" :theme-vars="mobileTheme" theme-vars-scope="global">
  <LotusMobileHeader :title="title" :back="back" :disabled="disabled" @back="emit('back')"><template #right><LotusMobileNotifications v-if="notifications" :app="app"/><slot name="header-right"/></template></LotusMobileHeader>
  <PullRefresh v-model="pulling" class="lotus-pwa-pull" :disabled="!refresh||!refreshable||keyboardOpen||disabled" pulling-text="Kéo xuống để tải lại" loosing-text="Thả ra để tải lại" loading-text="Đang tải lại…" success-text="Đã cập nhật" :success-duration="700" @refresh="pull"><slot/></PullRefresh>
  <LotusMobileOnboarding v-if="onboarding" :app="app" :title="title"/>
  <LotusMobileBottomNav :items="tabs" :active="activeTab" :hidden="keyboardOpen" :disabled="disabled" @navigate="emit('navigate',$event)"/>
 </ConfigProvider>
</template>
