<script setup>
import {computed,onMounted,ref,watch} from 'vue'
import {Segmented} from './ui/segmented'
import {Toaster} from './ui/toast'
import LotusIcon from './LotusIcon.vue'
import ShowcaseFoundations from './showcase/ShowcaseFoundations.vue'
import ShowcaseComponents from './showcase/ShowcaseComponents.vue'
import ShowcaseTables from './showcase/ShowcaseTables.vue'
import ShowcaseAgri from './showcase/ShowcaseAgri.vue'
import ShowcasePhone from './showcase/ShowcasePhone.vue'
import ShowcaseScreens from './showcase/ShowcaseScreens.vue'
import {applyUiMode} from '../ui-mode'
import {SAMPLE_NOTE} from './showcase/sample-data.js'
// Trang mẫu (spec 004, User Story 6): the whole kit on sample data, for review by the owner and as the reference for
// whoever builds the next screen. Dev and review only: not a build input of vite.config.js (FR-040).
// URL: ?section=<id>&mode=light|dark|outdoor&density=compact|comfortable — one section alone, for screenshots.
const SECTIONS=[
 {id:'nen',label:'Nền',icon:'layers',component:ShowcaseFoundations},
 {id:'thanh-phan',label:'Thành phần',icon:'grid',component:ShowcaseComponents},
 {id:'bang',label:'Bảng',icon:'list',component:ShowcaseTables},
 {id:'dien-thoai',label:'Điện thoại',icon:'id-card',component:ShowcasePhone},
 {id:'nong-nghiep',label:'Nông nghiệp',icon:'sprout',component:ShowcaseAgri},
 {id:'man-hinh',label:'Mẫu màn hình',icon:'document',component:ShowcaseScreens},
]
const params=typeof location==='undefined'?new URLSearchParams():new URLSearchParams(location.search)
const only=ref(SECTIONS.some(s=>s.id===params.get('section'))?params.get('section'):'')
const mode=ref(['light','dark','outdoor'].includes(params.get('mode'))?params.get('mode'):'light')
const density=ref(params.get('density')==='comfortable'?'comfortable':'compact')
const shown=computed(()=>only.value?SECTIONS.filter(s=>s.id===only.value):SECTIONS)
function paint(){applyUiMode(mode.value,density.value)}
onMounted(paint)
watch([mode,density],paint)
</script>
<template>
 <div class="lotus-ui sc" :class="{'sc--single':only}">
  <header class="sc-top">
   <span class="sc-top__brand"><img :src="'/assets/lotus_farm/images/lotus-agritech-header-v2.png'" alt="Lotus Agritech"></span>
   <div class="sc-top__title"><strong>Bộ giao diện Lotus</strong><small>Đất và lá · spec 004</small></div>
   <span class="lotus-sample sc-top__sample"><LotusIcon name="info"/>{{SAMPLE_NOTE}}: mọi số trên trang này là số mẫu</span>
   <span class="sc-top__spacer"/>
   <Segmented v-model="mode" label="Chế độ hiển thị" :options="[{value:'light',label:'Sáng',icon:'sun'},{value:'dark',label:'Tối',icon:'moon'},{value:'outdoor',label:'Ngoài trời',icon:'eye'}]"/>
   <Segmented v-model="density" label="Mật độ bảng" :options="[{value:'compact',label:'Gọn'},{value:'comfortable',label:'Thoáng'}]"/>
  </header>
  <div class="sc-layout">
   <nav v-if="!only" class="sc-nav" aria-label="Mục lục trang mẫu"><a v-for="s in SECTIONS" :key="s.id" :href="'#'+s.id"><LotusIcon :name="s.icon"/>{{s.label}}</a></nav>
   <main class="sc-main">
    <section v-for="s in shown" :id="s.id" :key="s.id" class="sc-section" :aria-labelledby="s.id+'-title'">
     <h2 :id="s.id+'-title'" class="sc-section__title"><LotusIcon :name="s.icon"/>{{s.label}}</h2>
     <component :is="s.component" :mode="mode"/>
    </section>
   </main>
  </div>
  <Toaster/>
 </div>
</template>
<style>
/* Showcase layout only. Every colour, size and font comes from lotus-tokens.css. */
.sc{min-height:100vh;background:var(--lotus-page);color:var(--lotus-text);font-family:var(--lotus-font);font-size:var(--lotus-text-base);line-height:var(--lotus-leading)}
.sc-top{position:sticky;top:0;z-index:var(--lotus-z-topbar);display:flex;align-items:center;gap:14px;min-height:60px;padding:8px 24px;background:linear-gradient(90deg,var(--lotus-topbar),var(--lotus-topbar-end));color:var(--lotus-on-topbar);box-shadow:var(--lotus-shadow-md);flex-wrap:wrap}
.sc-top__brand{display:grid;place-items:center;height:40px;padding:3px 8px;border-radius:var(--lotus-radius-md);background:#fff}
.sc-top__brand img{display:block;height:32px}
.sc-top__title{display:grid;line-height:var(--lotus-leading-tight)}
.sc-top__title strong{font-size:var(--lotus-text-lg)}
.sc-top__title small{opacity:.85;font-size:var(--lotus-text-xs)}
.sc-top__sample{border-color:currentColor;color:var(--lotus-on-topbar)}
.sc-top__spacer,.sc-app__spacer{flex:1}
.sc-top .lotus-segmented{background:rgb(0 0 0/.18);border-color:rgb(255 255 255/.25)}
.sc-top .lotus-segmented__item{color:var(--lotus-on-topbar)}
.sc-top .lotus-segmented__item[data-state="on"]{background:var(--lotus-surface);color:var(--lotus-text-strong)}
.sc-layout{display:grid;grid-template-columns:200px minmax(0,1fr);gap:24px;max-width:1600px;margin:0 auto;padding:24px}
.sc--single .sc-layout{grid-template-columns:minmax(0,1fr)}
.sc-nav{position:sticky;top:84px;align-self:start;display:grid;gap:2px}
.sc-nav a{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:var(--lotus-radius-md);color:var(--lotus-text-secondary);font-weight:var(--lotus-weight-medium);text-decoration:none}
.sc-nav a:hover{background:var(--lotus-hover);color:var(--lotus-text-strong)}
.sc-main{display:grid;gap:36px;min-width:0}
.sc-section{display:grid;gap:14px;min-width:0;scroll-margin-top:84px}
.sc-section__title{display:flex;align-items:center;gap:10px;margin:0;color:var(--lotus-text-strong);font-size:var(--lotus-text-xl);font-weight:var(--lotus-weight-bold);letter-spacing:var(--lotus-tracking-tight)}
.sc-section__title .lotus-icon{color:var(--lotus-primary)}
.sc-stack{display:grid;gap:16px;min-width:0}
.sc-stack-sm{display:grid;gap:10px;min-width:0}
.sc-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.sc-grid-2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;align-items:start}
.sc-grid-2--wide{grid-template-columns:minmax(0,1.2fr) minmax(0,1fr)}
.sc-grid-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;align-items:start}
.sc-split{display:grid;grid-template-columns:minmax(0,1fr) 230px;gap:20px;align-items:start}
.sc-form{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px 16px;align-items:start}
.sc-field{display:grid;gap:6px;align-content:start}
.sc-label{color:var(--lotus-text-secondary);font-size:var(--lotus-text-sm);font-weight:var(--lotus-weight-medium)}
.sc-check{display:inline-flex;flex-direction:row;align-items:center;gap:8px;font-size:var(--lotus-text-md);font-weight:var(--lotus-weight-regular)}
.sc-note{margin:0;color:var(--lotus-text-secondary);font-size:var(--lotus-text-sm)}
.sc-stat-row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.sc-due-row{display:grid;grid-template-columns:44px minmax(0,1fr);gap:10px;align-items:center}
.sc-due-row__lot{color:var(--lotus-text-strong);font-weight:var(--lotus-weight-bold);font-size:var(--lotus-text-sm)}
/* Nền */
.sc-ramps{display:grid;gap:10px}
.sc-ramp{display:grid;grid-template-columns:150px minmax(0,1fr);gap:12px;align-items:center}
.sc-ramp__name{display:grid;line-height:var(--lotus-leading-tight)}
.sc-ramp__name small{color:var(--lotus-muted);font-size:var(--lotus-text-xs)}
.sc-ramp__steps{display:grid;grid-template-columns:repeat(10,minmax(0,1fr));gap:3px}
.sc-swatch{display:grid;align-content:end;gap:1px;height:52px;padding:5px 6px;border-radius:var(--lotus-radius-sm);color:var(--lotus-neutral-900);font-size:10px;line-height:1.2;box-shadow:inset 0 0 0 1px rgb(0 0 0/.06)}
.sc-swatch--dark{color:#fff}
.sc-swatch b{font-size:11px}
.sc-swatch i{font-style:normal;opacity:.85;font-family:var(--lotus-font-mono)}
.sc-pairs{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px}
.sc-pair{display:grid;gap:2px;padding:10px 12px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md)}
.sc-pair span:first-child{font-weight:var(--lotus-weight-semibold)}
.sc-pair b{font-size:var(--lotus-text-xl)}
.sc-pair__verdict{display:inline-flex;align-items:center;gap:4px;font-size:var(--lotus-text-xs);font-weight:var(--lotus-weight-bold)}
.sc-pair__verdict .lotus-icon{width:14px;height:14px;stroke-width:2.4}
.sc-ribbon{display:inline-flex;align-items:center;gap:8px;min-width:120px;font-size:var(--lotus-text-sm)}
.sc-tile{width:44px!important;aspect-ratio:auto!important;height:36px;min-height:36px}
.sc-zone{display:grid;place-items:center;width:24px;height:24px;border-radius:50%;color:var(--lotus-neutral-900);font-size:11px;font-weight:800;box-shadow:inset 0 0 0 1px rgb(0 0 0/.18)}
.sc-scale{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:3px;height:34px}
.sc-scale i{display:grid;place-items:center;border-radius:var(--lotus-radius-sm);color:#fff;font-style:normal}
.sc-scale--thin{height:18px}
.sc-ends{display:flex;justify-content:space-between;color:var(--lotus-muted);font-size:var(--lotus-text-xs)}
.sc-type{display:grid;gap:6px}
.sc-type__row{display:grid;grid-template-columns:42px minmax(0,1fr) auto;gap:10px;align-items:baseline;min-width:0}
.sc-type__row>span:nth-child(2){overflow:hidden;color:var(--lotus-text-strong);text-overflow:ellipsis;white-space:nowrap}
.sc-type__meta{color:var(--lotus-muted);font-size:var(--lotus-text-xs);font-family:var(--lotus-font-mono)}
.sc-type__row small{color:var(--lotus-muted);font-size:var(--lotus-text-xs)}
.sc-space{display:grid;gap:4px}
.sc-space span{display:flex;align-items:center;gap:8px;color:var(--lotus-muted);font-size:var(--lotus-text-xs)}
.sc-space i{display:block;height:10px;border-radius:2px;background:var(--lotus-primary-300)}
.sc-radius,.sc-shadow{display:grid;place-items:center;width:64px;height:48px;border:1px solid var(--lotus-border);background:var(--lotus-surface);color:var(--lotus-muted);font-size:var(--lotus-text-xs)}
.sc-shadow{border-radius:var(--lotus-radius-md);border-color:transparent}
/* Điện thoại */
.sc-phones{display:flex;flex-wrap:wrap;gap:28px;align-items:flex-start}
.sc-phone-wrap{display:grid;gap:10px;justify-items:center;margin:0}
.sc-phone-wrap figcaption{color:var(--lotus-muted);font-size:var(--lotus-text-sm)}
.sc-phone{height:844px;padding:11px;border-radius:46px;background:var(--lotus-neutral-900);box-shadow:var(--lotus-shadow-xl),inset 0 0 0 2px var(--lotus-neutral-700)}
.sc-phone__screen{position:relative;display:flex;flex-direction:column;height:100%;overflow:hidden;border-radius:36px;background:var(--lotus-page);color:var(--lotus-text)}
.sc-phone__header{display:flex;align-items:center;gap:10px;min-height:58px;padding:22px 14px 8px;background:linear-gradient(90deg,var(--lotus-topbar),var(--lotus-topbar-end));color:var(--lotus-on-topbar)}
.sc-phone__header strong{font-size:17px}
.sc-phone__logo{display:grid;place-items:center;height:34px;padding:2px 6px;border-radius:var(--lotus-radius-md);background:#fff}
.sc-phone__logo img{display:block;height:28px}
.sc-phone__body{display:grid;flex:1;align-content:start;gap:10px;padding:12px;overflow:auto}
.sc-phone__body--dim{opacity:.35;filter:saturate(.6)}
.sc-phone__meta{display:flex;flex-wrap:wrap;gap:6px}
.sc-phone__cta{width:100%}
.sc-phone__setting{padding:10px 12px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-lg);background:var(--lotus-surface)}
.sc-tabbar{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));min-height:64px;padding:4px 4px 16px;border-top:1px solid var(--lotus-border);background:var(--lotus-surface)}
.sc-tabbar button{display:grid;justify-items:center;align-content:center;gap:2px;min-width:0;min-height:var(--lotus-touch);padding:0;border:0;border-radius:var(--lotus-radius-md);background:transparent;color:var(--lotus-muted);font:inherit;font-size:var(--lotus-text-xs);font-weight:var(--lotus-weight-medium)}
.sc-tabbar button span{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sc-tabbar button.is-active{color:var(--lotus-primary-text);font-weight:var(--lotus-weight-bold)}
.sc-tabbar button.is-active .lotus-icon{stroke-width:2.2}
.sc-sheet{position:absolute;inset:auto 0 0 0;display:grid;gap:10px;max-height:78%;padding:8px 14px 18px;overflow:auto;border-radius:var(--lotus-radius-2xl) var(--lotus-radius-2xl) 0 0;background:var(--lotus-surface);box-shadow:var(--lotus-shadow-xl)}
.sc-sheet__handle{justify-self:center;width:40px;height:4px;border-radius:2px;background:var(--lotus-border-strong)}
.sc-sheet__head{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.sc-sheet__head strong{font-size:var(--lotus-text-lg)}
.sc-sheet__works{display:flex;flex-wrap:wrap;gap:6px}
.sc-sheet__foot{display:grid;grid-template-columns:1fr 2fr;gap:8px;padding-top:4px}
/* Mẫu màn hình */
.sc-app{display:grid;grid-template-columns:224px minmax(0,1fr);min-height:620px;overflow:hidden;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-xl);background:var(--lotus-page);box-shadow:var(--lotus-shadow-lg)}
.sc-app__side{display:grid;align-content:start;gap:14px;padding:16px 12px;border-right:1px solid var(--lotus-border);background:var(--lotus-sidebar)}
.sc-app__brand{display:grid;place-items:center start;height:48px;padding:4px 8px;border-radius:var(--lotus-radius-md);background:#fff}
.sc-app__brand img{height:38px}
.sc-app__nav{display:grid;gap:2px}
.sc-app__group{display:grid;gap:1px}
.sc-app__group-head{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:var(--lotus-radius-md);color:var(--lotus-text-secondary);font-size:var(--lotus-text-md);font-weight:var(--lotus-weight-semibold)}
.sc-app__group-head .lotus-icon{width:18px;height:18px;color:var(--lotus-muted)}
.sc-app__group-head.is-current,.sc-app__group-head.is-current .lotus-icon{color:var(--lotus-primary-text)}
.sc-app__chev{margin-left:auto;width:14px!important;height:14px!important}
.sc-app__item{margin-left:28px;padding:6px 10px;border-left:2px solid var(--lotus-border);color:var(--lotus-text-secondary);font-size:var(--lotus-text-md)}
.sc-app__group:not(.is-open) .sc-app__item{display:none}
.sc-app__item.is-active{border-left-color:var(--lotus-primary);border-radius:0 var(--lotus-radius-md) var(--lotus-radius-md) 0;background:var(--lotus-selected);color:var(--lotus-primary-text);font-weight:var(--lotus-weight-semibold)}
.sc-app__main{display:grid;grid-template-rows:auto 1fr;min-width:0}
.sc-app__top{display:flex;align-items:center;gap:14px;min-height:56px;padding:0 18px;background:linear-gradient(90deg,var(--lotus-topbar),var(--lotus-topbar-end));color:var(--lotus-on-topbar);font-size:var(--lotus-text-md)}
.sc-app__top>strong{font-size:var(--lotus-text-base)}
.sc-app__farm{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border:1px solid rgb(255 255 255/.45);border-radius:var(--lotus-radius-md);font-weight:var(--lotus-weight-semibold)}
.sc-app__farm .lotus-icon{width:16px;height:16px}
.sc-app__search{display:inline-flex;align-items:center;gap:8px;min-width:260px;padding:7px 10px;border-radius:var(--lotus-radius-md);background:var(--lotus-surface);color:var(--lotus-muted)}
.sc-app__search kbd{margin-left:auto;padding:1px 6px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-xs);background:var(--lotus-soft);font:inherit;font-size:var(--lotus-text-xs)}
.sc-app__search .lotus-icon{width:16px;height:16px}
.sc-app__user{display:inline-flex;align-items:center;gap:8px;font-weight:var(--lotus-weight-medium)}
.sc-app__content{min-width:0;padding:16px 18px}
.sc-modal-demo{display:grid;place-items:center;padding:24px;border-radius:var(--lotus-radius-xl);background:var(--lotus-overlay)}
.sc-modal{display:grid;width:100%;overflow:hidden;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-xl);background:var(--lotus-surface);box-shadow:var(--lotus-shadow-xl)}
.sc-modal__head{display:flex;align-items:center;gap:10px;padding:14px 18px;border-bottom:1px solid var(--lotus-border-subtle)}
.sc-modal__head h3{margin:0 auto 0 0;color:var(--lotus-text-strong);font-size:var(--lotus-text-lg)}
.sc-modal__body{display:grid;gap:14px;padding:16px 18px}
.sc-modal__foot{display:flex;align-items:center;gap:8px;padding:12px 18px;border-top:1px solid var(--lotus-border-subtle);background:var(--lotus-soft)}
@media (max-width:1100px){.sc-grid-2,.sc-grid-3,.sc-split,.sc-grid-2--wide{grid-template-columns:minmax(0,1fr)}.sc-layout{grid-template-columns:minmax(0,1fr)}.sc-nav{display:none}}
</style>
