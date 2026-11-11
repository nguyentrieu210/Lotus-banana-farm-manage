<script setup>
import {nextTick,onMounted,ref,watch} from 'vue'
import {contrastRatio} from '../../color-contrast.js'
import {RIBBON_COLOURS} from '../../ribbon-colors.js'
import {LOT_STATES} from '../../lot-states.js'
import LotusIcon from '../LotusIcon.vue'
import RibbonDot from '../agri/RibbonDot.vue'
// Nền: ramps, semantic pairs with their live contrast, farm colours, chart palettes, type, space, radius, elevation.
const props=defineProps({mode:String})
const FAMILIES=[['primary','Đỏ Lotus','hành động duy nhất'],['neutral','Đá ấm','nền, chữ, viền'],['success','Lá','đạt, đã xong'],['warning','Chuối','đến hạn, đang chờ'],['danger','Đỏ thẫm','nguy, quá hạn, cách ly'],['info','Nước','thông tin, dự thu'],['earth','Đất','dữ liệu phụ']]
const STEPS=[50,100,200,300,400,500,600,700,800,900]
const PAIRS=[
 ['--lotus-text','--lotus-surface','Chữ chính'],['--lotus-text-secondary','--lotus-surface','Chữ phụ'],['--lotus-muted','--lotus-page','Chữ mờ trên nền trang'],
 ['--lotus-subtle','--lotus-surface','Chữ gợi ý'],['--lotus-on-primary-solid','--lotus-primary-solid','Chữ trên nút chính'],['--lotus-on-topbar','--lotus-topbar','Chữ trên thanh trên'],
 ['--lotus-tone-success-text','--lotus-tone-success-soft','Đạt'],['--lotus-tone-warning-text','--lotus-tone-warning-soft','Cảnh báo'],['--lotus-tone-danger-text','--lotus-tone-danger-soft','Nguy'],
 ['--lotus-tone-info-text','--lotus-tone-info-soft','Thông tin'],['--lotus-primary-text','--lotus-primary-subtle','Đỏ trên đỏ nhạt'],['--lotus-border-control','--lotus-surface','Viền ô nhập'],
]
const CHARTS=[1,2,3,4,5,6,7,8]
const SEQ=[1,2,3,4,5,6,7]
const TYPE=[['4xl','Số lớn KPI'],['3xl','Số liệu ô KPI'],['2xl','Tiêu đề hộp thoại'],['xl','Tiêu đề phần'],['lg','Tiêu đề thẻ'],['base','Chữ thường'],['md','Chữ bảng'],['sm','Chữ phụ'],['xs','Nhãn nhỏ']]
const SPACE=['1','2','3','4','5','6','8','10','12']
const RADIUS=['xs','sm','md','lg','xl','2xl','full']
const SHADOW=['xs','sm','md','lg','xl']
const values=ref({})
function read(){
 if(typeof document==='undefined')return
 const cs=getComputedStyle(document.documentElement),out={}
 const names=[...FAMILIES.flatMap(([f])=>STEPS.map(s=>`--lotus-${f}-${s}`)),...PAIRS.flatMap(([a,b])=>[a,b])]
 for(const n of names)out[n]=cs.getPropertyValue(n).trim()
 values.value=out
}
onMounted(read)
watch(()=>props.mode,()=>nextTick(read))
const ratio=(a,b)=>contrastRatio(values.value[a],values.value[b])
const need=a=>a==='--lotus-border-control'?3:props.mode==='outdoor'&&/text|muted|on-/.test(a)?7:4.5
</script>
<template>
 <div class="sc-stack">
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Bảng màu gốc</h3><span class="lotus-sample">Giá trị đọc trực tiếp từ token</span></header>
   <div class="lotus-card__body sc-ramps">
    <div v-for="[family,name,use] in FAMILIES" :key="family" class="sc-ramp"><div class="sc-ramp__name"><strong>{{name}}</strong><small>{{use}}</small></div><div class="sc-ramp__steps"><span v-for="s in STEPS" :key="s" class="sc-swatch" :style="{background:`var(--lotus-${family}-${s})`}" :class="{'sc-swatch--dark':s>=500}" :title="`--lotus-${family}-${s}`"><b>{{s}}</b><i>{{values[`--lotus-${family}-${s}`]}}</i></span></div></div>
   </div>
  </article>
  <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Cặp chữ và nền, tỉ lệ tương phản</h3><span class="lotus-caps">Chữ ≥ 4,5 · viền ≥ 3 · ngoài trời ≥ 7</span></header>
   <div class="lotus-card__body sc-pairs">
    <div v-for="[fg,bg,label] in PAIRS" :key="fg+bg" class="sc-pair" :style="{background:`var(${bg})`,color:`var(${fg})`,borderColor:fg==='--lotus-border-control'?`var(${fg})`:undefined}">
     <span>{{label}}</span><b class="lotus-num">{{ratio(fg,bg)?ratio(fg,bg).toFixed(2).replace('.',',')+':1':'…'}}</b>
     <span class="sc-pair__verdict" :class="ratio(fg,bg)>=need(fg)?'is-pass':'is-fail'"><LotusIcon :name="ratio(fg,bg)>=need(fg)?'tick':'x'"/>{{ratio(fg,bg)>=need(fg)?'Đạt':'Không đạt'}} ≥ {{need(fg)}}</span>
    </div>
   </div>
  </article>
  <div class="sc-grid-2">
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Màu dây (giống dây thật, mọi chế độ)</h3></header>
    <div class="lotus-card__body sc-row"><span v-for="(meta,code) in RIBBON_COLOURS" :key="code" class="sc-ribbon"><RibbonDot :code="code" size="lg" decorative/>{{meta.label}}</span><span class="sc-ribbon"><RibbonDot code="XANH_LA_DO" size="lg" decorative/>Xanh lá – Đỏ</span></div>
   </article>
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Trạng thái lô</h3></header>
    <div class="lotus-card__body sc-row"><span v-for="(meta,state) in LOT_STATES" :key="state" class="sc-ribbon"><span class="lotus-lot-tile sc-tile" :data-state="state" aria-hidden="true"><LotusIcon v-if="meta.icon" :name="meta.icon"/>A5</span>{{meta.label}}</span></div>
   </article>
  </div>
  <div class="sc-grid-2">
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Biểu đồ: 8 màu phân loại, thang liên tục, thang hai chiều</h3></header>
    <div class="lotus-card__body sc-stack-sm">
     <div class="sc-scale"><i v-for="i in CHARTS" :key="i" :style="{background:`var(--lotus-chart-${i})`}"><b>{{i}}</b></i></div>
     <div class="sc-scale sc-scale--thin"><i v-for="i in SEQ" :key="i" :style="{background:`var(--lotus-seq-${i})`}"/></div>
     <div class="sc-scale sc-scale--thin"><i v-for="i in SEQ" :key="i" :style="{background:`var(--lotus-div-${i})`}"/></div>
     <div class="sc-ends"><span>Thấp hơn kế hoạch</span><span>Bằng</span><span>Cao hơn</span></div>
    </div>
   </article>
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Màu khu trên bản đồ</h3></header>
    <div class="lotus-card__body sc-row"><span v-for="z in ['a','b','c','d','e','f']" :key="z" class="sc-ribbon"><span class="sc-zone" :style="{background:`var(--lotus-map-zone-${z})`}">{{z.toUpperCase()}}</span>Khu {{z.toUpperCase()}}</span></div>
   </article>
  </div>
  <div class="sc-grid-2">
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Chữ: Inter, số đều cột</h3></header>
    <div class="lotus-card__body sc-type"><div v-for="[size,use] in TYPE" :key="size" class="sc-type__row"><span class="sc-type__meta">{{size}}</span><span :style="{fontSize:`var(--lotus-text-${size})`,fontWeight:size.includes('xl')?700:500}">{{size==='4xl'||size==='3xl'?'7.350 buồng':'Báo cáo ngày theo lô · Ước tính tuần 46'}}</span><small>{{use}}</small></div></div>
   </article>
   <article class="lotus-card"><header class="lotus-card__head"><h3 class="lotus-card__title">Khoảng cách, bo góc, đổ bóng</h3></header>
    <div class="lotus-card__body sc-stack-sm">
     <div class="sc-space"><span v-for="s in SPACE" :key="s"><i :style="{width:`var(--lotus-space-${s})`}"/>{{s}}</span></div>
     <div class="sc-row"><span v-for="r in RADIUS" :key="r" class="sc-radius" :style="{borderRadius:`var(--lotus-radius-${r})`}">{{r}}</span></div>
     <div class="sc-row"><span v-for="s in SHADOW" :key="s" class="sc-shadow" :style="{boxShadow:`var(--lotus-shadow-${s})`}">{{s}}</span></div>
    </div>
   </article>
  </div>
 </div>
</template>
