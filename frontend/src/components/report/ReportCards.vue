<script setup>
import {computed,ref} from 'vue'
import ModalForm from '../form/ModalForm.vue'
import DataTable from '../DataTable.vue'
import {formatDate} from '../../format'
// The cards of a report (lotus_farm.field_reports): one figure each; a card opens its detail rows in a dialog, where the
// table can be filtered and exported to Excel. The server says which columns to show and how to read them.
const props=defineProps({cards:{type:Array,default:()=>[]},mobile:Boolean,storageKey:{type:String,default:'field-report'}})
const opened=ref(null)
const number=v=>v==null||v===''?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:2})
const figure=c=>c.value==null?'—':number(c.value)+(c.unit&&c.unit!=='%'?'':c.unit==='%'?'%':'')
const columns=computed(()=>(opened.value?.columns||[]).map(c=>({field:c.field,headerName:c.label,minWidth:c.kind==='number'?100:120,
 sum:c.kind==='number'&&!/\/|%|Tỷ lệ|Lệch/.test(c.label),
 valueFormatter:c.kind==='date'?p=>p.value?formatDate(p.value):'':c.kind==='number'?p=>p.value==null||p.value===''?'':number(p.value):undefined})))
const rows=computed(()=>(opened.value?.rows||[]).map((r,i)=>({__key:i,...r})))
</script>

<template>
 <div class="report-cards" :class="{'report-cards--mobile':mobile}">
  <button v-for="c in cards" :key="c.key" type="button" class="report-card" :class="'is-'+c.tone" @click="opened=c">
   <span class="report-card__title">{{c.title}}</span>
   <strong class="report-card__value">{{figure(c)}}<small v-if="c.unit&&c.unit!=='%'"> {{c.unit}}</small></strong>
   <span v-if="c.note" class="report-card__note">{{c.note}}</span>
   <span class="report-card__more">{{c.rows.length?'Xem '+c.rows.length+' dòng':'Không có dòng nào'}}</span>
  </button>
  <ModalForm :model-value="!!opened" :title="opened?.title||''" width="1000px" readonly @update:model-value="v=>!v&&(opened=null)">
   <template v-if="opened">
    <p v-if="opened.note" class="lotus-form-note">{{opened.note}}</p>
    <DataTable :rows="rows" :columns="columns" row-key="__key" :storage-key="storageKey+'-'+opened.key" :selection-enabled="false" :export-title="opened.title"
     empty="Không có dòng nào."/>
   </template>
  </ModalForm>
 </div>
</template>

<style>
.report-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px}
.report-cards--mobile{grid-template-columns:1fr 1fr}
.report-card{display:grid;gap:4px;align-content:start;padding:10px 12px;text-align:left;font:inherit;color:inherit;border:1px solid var(--lotus-border);border-top:4px solid var(--lotus-info);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);cursor:pointer;min-width:0}
.report-card.is-good{border-top-color:var(--lotus-success)}
.report-card.is-warn{border-top-color:var(--lotus-warning)}
.report-card.is-bad{border-top-color:var(--lotus-danger)}
.report-card__title{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.report-card__value{font-size:var(--lotus-text-xl);color:var(--lotus-text-strong)}
.report-card__value small{margin-left:4px;font-size:var(--lotus-text-sm);font-weight:normal;color:var(--lotus-muted)}
.report-card.is-bad .report-card__value{color:var(--lotus-danger)}
.report-card__note{font-size:var(--lotus-text-sm);color:var(--lotus-text)}
.report-card__more{font-size:var(--lotus-text-xs);color:var(--lotus-muted)}
</style>
