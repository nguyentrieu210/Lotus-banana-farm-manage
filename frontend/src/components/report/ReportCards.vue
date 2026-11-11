<script setup>
import {computed,ref} from 'vue'
import ModalForm from '../form/ModalForm.vue'
import DataTable from '../DataTable.vue'
import {StatTile} from '../ui/stat-tile'
import {formatDate} from '../../format'
// The cards of a report (lotus_farm.field_reports): one figure each; a card opens its detail rows in a dialog, where the
// table can be filtered and exported to Excel. The server says which columns to show and how to read them.
// Spec 004: each card is a kit stat tile (button), its tone from the server: good, warn, bad, info.
const props=defineProps({cards:{type:Array,default:()=>[]},mobile:Boolean,storageKey:{type:String,default:'field-report'}})
const opened=ref(null)
const TONES={good:'success',warn:'warning',bad:'danger',info:'info'}
const number=v=>v==null||v===''?'—':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:2})
const columns=computed(()=>(opened.value?.columns||[]).map(c=>({field:c.field,headerName:c.label,minWidth:c.kind==='number'?100:120,
 sum:c.kind==='number'&&!/\/|%|Tỷ lệ|Lệch/.test(c.label),
 valueFormatter:c.kind==='date'?p=>p.value?formatDate(p.value):'':c.kind==='number'?p=>p.value==null||p.value===''?'':number(p.value):undefined})))
const rows=computed(()=>(opened.value?.rows||[]).map((r,i)=>({__key:i,...r})))
</script>

<template>
 <div class="report-cards" :class="{'report-cards--mobile':mobile}">
  <StatTile v-for="c in cards" :key="c.key" as="button" class="report-card" :class="'is-'+c.tone" :tone="TONES[c.tone]||'neutral'"
   :label="c.title" :value="c.value" :digits="2" :unit="c.unit" :hint="c.note||undefined" :missing="c.note||undefined" @click="opened=c">
   <template #foot><span class="report-card__more" :class="{'is-empty':!c.rows.length}">{{c.rows.length?'Xem '+c.rows.length+' dòng':'Không có dòng nào'}}</span></template>
  </StatTile>
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
.report-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.report-cards--mobile{grid-template-columns:1fr 1fr;gap:8px}
.report-cards .lotus-stat__value{font-size:var(--lotus-text-2xl)}
.report-cards--mobile .lotus-stat{padding:10px 12px 10px}
.report-cards--mobile .lotus-stat__value{font-size:var(--lotus-text-xl);white-space:normal;overflow-wrap:anywhere}
.report-cards--mobile .lotus-stat__label{white-space:normal}
.report-card__more{margin-left:auto;color:var(--lotus-primary-text);font-size:var(--lotus-text-xs);font-weight:var(--lotus-weight-semibold)}
.report-card__more.is-empty{color:var(--lotus-subtle);font-weight:var(--lotus-weight-medium)}
.report-card.is-bad .lotus-stat__value{color:var(--lotus-tone-danger-text)}
</style>
