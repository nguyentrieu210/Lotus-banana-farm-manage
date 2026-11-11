<script setup>
// So sánh giá trên điện thoại (spec 003, FR-033): mỗi mặt hàng một thẻ, mỗi báo giá một dòng chọn.
// Chọn báo giá không rẻ nhất thì phải ghi lý do ngay trên thẻ.
import LotusMobileInput from '../LotusMobileInput.vue'
import {unitLabel} from '../../units'
import {money,cheapestCost,needsReason} from '../../procurement'

const props=defineProps({rows:{type:Array,default:()=>[]},suppliers:{type:Array,default:()=>[]},choices:{type:Object,default:()=>({})},reasons:{type:Object,default:()=>({})},disabled:Boolean})
const emit=defineEmits(['update:choices','update:reasons'])
const fmt=value=>value==null?'—':Number(value).toLocaleString('vi-VN',{maximumFractionDigits:3})
const label=name=>props.suppliers.find(s=>s.name===name)?.label||name
const offers=row=>[...(row.offers||[])].filter(o=>o.unit_cost!=null).sort((a,b)=>a.unit_cost-b.unit_cost)
function pick(row,offer){if(props.disabled)return;emit('update:choices',{...props.choices,[row.key]:props.choices[row.key]===offer.line?'':offer.line})}
const setReason=(row,value)=>emit('update:reasons',{...props.reasons,[row.key]:value})
</script>

<template>
 <div class="compare-cards">
  <article v-for="row in rows" :key="row.key" class="compare-card" :aria-label="'Báo giá cho '+row.item_name">
   <header><strong>{{row.item_name}}</strong><small>{{[row.request,row.need_qty!=null?'còn cần '+fmt(row.need_qty)+' '+unitLabel(row.stock_uom):'',row.request&&!row.approved?'đề xuất chưa duyệt xong':''].filter(Boolean).join(' · ')}}</small></header>
   <button v-for="offer in offers(row)" :key="offer.line" type="button" class="compare-card__offer" :class="{'is-chosen':choices[row.key]===offer.line}" :disabled="disabled"
     :aria-pressed="choices[row.key]===offer.line" :aria-label="'Chọn '+label(offer.supplier)+' cho '+row.item_name" @click="pick(row,offer)">
    <span class="compare-card__supplier">{{label(offer.supplier)}}<small>{{[offer.unit_cost===cheapestCost(row)&&'rẻ nhất',offer.docstatus===0&&'báo giá nháp'].filter(Boolean).join(' · ')}}</small></span>
    <b>{{money(offer.unit_cost)}}<small> / {{unitLabel(row.stock_uom)}}</small></b>
   </button>
   <p v-if="!offers(row).length" class="compare-card__empty">Chưa có báo giá có đơn giá.</p>
   <LotusMobileInput v-if="choices[row.key]&&needsReason(row,choices[row.key])" :model-value="reasons[row.key]||''" label="Lý do không chọn giá thấp nhất" :aria-label="'Lý do chọn '+row.item_name" :disabled="disabled" @update:model-value="value=>setReason(row,value)"/>
  </article>
 </div>
</template>

<style>
.compare-cards{display:grid;gap:var(--lotus-space-3,12px)}
.compare-card{display:grid;gap:var(--lotus-space-2,8px);padding:var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-lg,12px);background:var(--lotus-surface)}
.compare-card header{display:grid;gap:2px}
.compare-card header small,.compare-card__supplier small,.compare-card__offer b small{display:block;color:var(--lotus-muted);font-size:12px;font-weight:400}
.compare-card__offer b small{display:inline}
.compare-card__offer{display:flex;align-items:center;justify-content:space-between;gap:var(--lotus-space-2,8px);width:100%;min-height:var(--lotus-touch,44px);padding:var(--lotus-space-2,8px) var(--lotus-space-3,12px);border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md,8px);background:var(--lotus-surface);color:var(--lotus-text);font:inherit;text-align:left}
.compare-card__offer.is-chosen{background:var(--lotus-primary-subtle);border-color:var(--lotus-primary);font-weight:600}
.compare-card__supplier{min-width:0;overflow:hidden;text-overflow:ellipsis}
.compare-card__offer b{flex:none;white-space:nowrap}
.compare-card__empty{margin:0;color:var(--lotus-muted)}
</style>
