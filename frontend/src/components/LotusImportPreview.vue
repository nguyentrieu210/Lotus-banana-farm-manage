<script setup>
import LotusField from './form/LotusField.vue'
import {computed,onMounted,ref,watch} from 'vue'
import {call} from '../api'
import DataTable from './DataTable.vue'
const props=defineProps({farm:{type:String,default:''},block:{type:String,default:''}})
const data=ref(null),loading=ref(false),error=ref('')
const search=ref(''),missingOnly=ref(false)
const amount=n=>new Intl.NumberFormat('vi-VN',{maximumFractionDigits:2}).format(Number(n||0))
let sequence=0
async function reload(){
 const id=++sequence; loading.value=true;error.value=''
 try{
  const result=await call('lotus_farm.forecast_import_preview.preview',{farm:props.farm||null,block:props.block||null})
  if(id===sequence)data.value=result
 }catch(e){if(id===sequence)error.value=e.message||'Không đọc được mẫu nhập'}
 finally{if(id===sequence)loading.value=false}
}
onMounted(reload)
watch(()=>[props.farm,props.block],reload)
const tableColumns=[{field:'code',headerName:'Lô lớn'},{field:'area_ha',headerName:'Diện tích',valueFormatter:p=>amount(p.value)+' ha'},{field:'tree_count',headerName:'Số cây có nguồn',valueFormatter:p=>p.value==null?'Chưa có':amount(p.value)},{field:'count_status',headerName:'Trạng thái',valueFormatter:p=>p.data?.area_match?p.value:'Cần đối chiếu diện tích'}]
const rows=computed(()=>data.value?.rows?.filter(r=>
 (!missingOnly.value||r.tree_count===null)&&
 (!search.value||r.code.toLowerCase().includes(search.value.trim().toLowerCase()))
 )||[])
</script>
<template>
<details class="lotus-import" open>
  <summary><span><strong>Đối chiếu số cây Vườn 222</strong><small>Excel gốc + số cây từ biển lô · Chưa xác nhận kiểm kê thực địa</small></span><span class="lotus-import__tag">Cần kiểm kê</span></summary>
  <div class="lotus-import__body">
    <p v-if="loading" class="lotus-import__info">Đang đọc bảng nhập riêng…</p>
    <p v-if="error" role="alert" class="lotus-import__error">{{error}} <button @click="reload">Thử lại</button></p>
    <p v-if="data&&!data.available" class="lotus-import__info">{{data.message}}</p>
    <template v-if="data?.available">
      <p class="lotus-import__source"><b>Nguồn:</b> {{data.source}} · Đã đối chiếu với hồ sơ lô, có nguồn cập nhật từng lô. <button type="button" @click="reload" :disabled="loading">Làm mới</button></p>
      <div class="lotus-import__metrics">
        <article><small>Lô lớn khớp hệ thống</small><strong>{{data.summary.lots}}</strong></article>
        <article><small>Lô đã có số cây</small><strong>{{data.summary.counted_lots}} / {{data.summary.lots}}</strong></article>
        <article><small>Tổng số cây có nguồn</small><strong>{{amount(data.summary.known_trees)}}</strong></article>
        <article><small>Thiếu số cây</small><strong>{{data.summary.missing_count_lots}} lô</strong></article>
      </div>
      <div v-if="data.summary.area_mismatch_lots?.length" class="lotus-import__error" role="alert">Chênh lệch diện tích so với Lotus: {{data.summary.area_mismatch_lots.join(', ')}}. Cần kiểm tra trước khi sử dụng.</div>
      <div v-if="data.zone_a_outlook" class="lotus-import__flower">
        <div>
          <span class="lotus-import__eyebrow">ƯỚC TÍNH KHU A · CHƯA TRỔ THỰC TẾ</span>
          <h3>Dự kiến trổ hoa {{data.zone_a_outlook.flowering_date.split('-').reverse().join('/')}}</h3>
          <p>Khoảng thu của ba đợt trổ <b>{{data.zone_a_outlook.harvest_from.split('-').reverse().join('/')}} – {{data.zone_a_outlook.harvest_to.split('-').reverse().join('/')}}</b>.</p>
          <small>{{data.zone_a_outlook.scope_note}} Theo quy tắc trổ 20/60/20, cắt bắp sau 17 ngày rồi thu sau 60–70 ngày.</small>
        </div>
        <span class="lotus-import__confidence">Độ tin cậy thấp</span>
      </div>
      <div class="lotus-import__zones">
        <article v-for="g in data.groups" :key="g.zone"><b>Khu {{g.zone}}</b><span>{{g.counted_lots}}/{{g.lots}} lô có số cây</span><strong>{{amount(g.known_trees)}} cây</strong><small>{{amount(g.area_ha)}} ha</small></article>
      </div>
      <div class="lotus-import__filters">
        <LotusField label="Tìm lô" v-model="search" type="search" placeholder="A5, B12…"/>
        <LotusField type="checkbox" label="Chỉ hiện lô thiếu số cây"  v-model="missingOnly"/>
      </div>
      <div class="lotus-import__scroll">
        <DataTable :rows="rows" :columns="tableColumns" row-key="block" storage-key="import-lot-preview"/>
      </div>
      <p class="lotus-import__footer">{{data.notice}} Ngày trổ khu A chỉ là ước tính cấp khu; không tạo bản ghi “Đã trổ” cho từng lô.</p>
    </template>
  </div>
</details>
</template>
<style scoped>
.lotus-import{margin:16px 0 20px;border:1px solid var(--lotus-border,var(--lotus-neutral-200));background:var(--lotus-surface,#fff);border-radius:12px;color:var(--lotus-text,var(--lotus-neutral-800))}
.lotus-import>summary{display:flex;align-items:center;justify-content:space-between;gap:12px;cursor:pointer;padding:15px 18px}
.lotus-import>summary span:first-child{display:grid;gap:3px}
.lotus-import>summary strong{font-size:15px}
.lotus-import>summary small,.lotus-import__info{font-size:12px;color:var(--lotus-muted,var(--lotus-neutral-500))}
.lotus-import__tag,.lotus-import__confidence{border-radius:7px;padding:5px 9px;white-space:nowrap;background:var(--lotus-neutral-100);color:var(--lotus-primary-700);font-size:11px;font-weight:650}
.lotus-import__body{border-top:1px solid var(--lotus-border,var(--lotus-neutral-200));padding:15px 17px;display:grid;gap:14px}
.lotus-import__source{font-size:12px;color:var(--lotus-muted,var(--lotus-neutral-600));margin:0}
.lotus-import__source button,.lotus-import__error button{font:inherit;background:transparent;border:0;color:var(--lotus-accent,var(--lotus-primary-600));cursor:pointer;text-decoration:underline}
.lotus-import__metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}
.lotus-import__metrics article{border:1px solid var(--lotus-border,var(--lotus-neutral-200));padding:11px 13px;display:grid;gap:6px;border-radius:9px}
.lotus-import__metrics small{font-size:11px;color:var(--lotus-muted,var(--lotus-neutral-600))}
.lotus-import__metrics strong{font-size:21px;font-weight:750;font-variant-numeric:tabular-nums}
.lotus-import__flower{display:flex;justify-content:space-between;align-items:flex-start;gap:15px;padding:16px;border:1px solid var(--lotus-neutral-200);border-radius:10px;background:var(--lotus-neutral-50);color:var(--lotus-success-800)}
.lotus-import__flower h3{font-size:17px;margin:5px 0}
.lotus-import__flower p{margin:4px 0;font-size:13px}
.lotus-import__flower small{font-size:11px;line-height:1.6;display:block}
.lotus-import__flower a{color:var(--lotus-info-700);text-decoration:underline}
.lotus-import__eyebrow{font-size:10px;font-weight:750;letter-spacing:.05em}
.lotus-import__zones{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px}
.lotus-import__zones article{display:grid;gap:3px;border:1px solid var(--lotus-border,var(--lotus-neutral-200));border-radius:9px;padding:10px 12px;font-size:12px}
.lotus-import__zones article strong{font-size:15px}
.lotus-import__zones article span,.lotus-import__zones article small{font-size:11px;color:var(--lotus-muted,var(--lotus-neutral-600))}
.lotus-import__filters{display:flex;align-items:center;gap:15px;flex-wrap:wrap;font-size:12px}
.lotus-import__filters label{display:flex;align-items:center;gap:8px}
.lotus-import__filters input[type=search]{height:34px;min-width:150px;padding:5px 9px;border:1px solid var(--lotus-border,var(--lotus-neutral-200));border-radius:7px}
.lotus-import__check input{accent-color:var(--lotus-primary-600)}
.lotus-import__scroll{max-height:290px;overflow:auto;border:1px solid var(--lotus-border,var(--lotus-neutral-200));border-radius:9px}
.lotus-import table{border-collapse:collapse;width:100%;font-size:12px}
.lotus-import th{text-align:left;background:var(--lotus-table-header,var(--lotus-neutral-50));position:sticky;top:0;padding:9px 12px}
.lotus-import td{padding:9px 12px;border-top:1px solid var(--lotus-border,var(--lotus-neutral-100))}
.lotus-import__footer{margin:0;font-size:11px;color:var(--lotus-muted,var(--lotus-neutral-600))}
.lotus-import__error{color:var(--lotus-primary-700);font-size:12px}
.dark .lotus-import__flower{background:var(--lotus-neutral-800);color:var(--lotus-neutral-200);border-color:var(--lotus-success-700)}
@media(max-width:850px){.lotus-import__metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.lotus-import__zones{grid-template-columns:repeat(3,minmax(0,1fr))}.lotus-import__flower{flex-direction:column}}
@media(max-width:480px){.lotus-import__zones{grid-template-columns:repeat(2,minmax(0,1fr))}.lotus-import__scroll{overflow-x:auto}.lotus-import table{min-width:520px}}
</style>