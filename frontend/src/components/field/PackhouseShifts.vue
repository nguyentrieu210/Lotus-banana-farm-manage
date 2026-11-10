<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import LotusField from '../form/LotusField.vue'
import FormGrid from '../form/FormGrid.vue'
import ModalForm from '../form/ModalForm.vue'
import DataTable from '../DataTable.vue'
import {Button as UiButton} from '../ui/button'
import {formatDate} from '../../format'
import {amountText,swatch} from '../../lot-entry-model.js'
// Xưởng (lotus_farm.shift): packhouse shifts and the bunches they took in, by lô and ribbon colour from confirmed harvest
// lines. A shift opens in a dialog: its sources and what it packed while it is open; once closed, the split by kg (kg and
// cartons per bunch per lô), the trace back to the field, and for the accountant the draft finished-goods receipt.
const props=defineProps({farm:{type:String,required:true},mobile:Boolean})
const api=(name,args={},write=false)=>call('lotus_farm.shift.'+name,args,write)
const iso=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')
const today=iso(new Date())
const since=ref(iso(new Date(Date.now()-30*864e5))),rows=ref([]),busy=ref(false),error=ref(''),notice=ref('')
const opened=ref(null),form=ref(null),offered=ref([]),saving=ref(false),formError=ref(''),traced=ref(null)
let asked=0
async function load(){
 const mine=++asked
 busy.value=true;error.value=''
 try{const result=await api('shifts',{farm:props.farm,from_date:since.value,to_date:today});if(mine===asked)rows.value=result}
 catch(e){if(mine===asked)error.value=e.message}
 finally{if(mine===asked)busy.value=false}
}
watch(()=>[props.farm,since.value],load,{immediate:true})

const receiptText=r=>r.docstatus!==1?'Đang mở':r.receipt_state===1?'Đã nhập kho':r.receipt_state===0?'Phiếu nhập kho nháp':'Chưa nhập kho'
const pct=v=>v==null?'—':amountText(v)+'%'
const time=v=>String(v||'').slice(11,16)
function blank(){return {name:'',modified:'',shift_code:'',posting_date:today,start:'07:00',end:'16:00',finished_kg:null,secondary_kg:null,cartons:null,notes:'',sources:{}}}
async function offer(day,name){offered.value=await api('harvest_sources',{farm:props.farm,date:day,name:name||undefined})}
async function openNew(){formError.value='';notice.value='';form.value=blank();opened.value=null;await offer(today)}
async function open(row){
 formError.value='';notice.value='';traced.value=null
 try{
  const data=await api('shift',{name:row.name})
  opened.value=data
  if(data.doc.docstatus===0&&data.can_write)await edit(data)
 }catch(e){error.value=e.message}
}
async function edit(data){
 const d=data.doc
 form.value={name:d.name,modified:d.modified,shift_code:d.shift_code,posting_date:d.posting_date,start:time(d.started_at),end:time(d.ended_at),
  finished_kg:d.finished_kg,secondary_kg:d.secondary_kg,cartons:d.cartons,notes:d.notes||'',
  sources:Object.fromEntries((d.sources||[]).map(s=>[s.harvest_entry||s.farm_block+':'+s.bunch_tag,{on:true,bunches:s.bunches,kg:s.kg,farm_block:s.farm_block,bunch_tag:s.bunch_tag,harvest_entry:s.harvest_entry}]))}
 opened.value=null
 await offer(d.posting_date,d.name)
}
// The harvest lines the shift can take, with the ones already on it first.
const choices=computed(()=>{
 if(!form.value)return []
 const list=offered.value.map(o=>({...o,key:o.harvest_entry}))
 for(const [key,s] of Object.entries(form.value.sources))if(!list.some(o=>o.key===key))list.unshift({key,harvest_entry:s.harvest_entry,farm_block:s.farm_block,bunch_tag:s.bunch_tag,block_code:'',colour:'',left:s.bunches,bunches:s.bunches,kg:s.kg})
 return list
})
function toggle(o,on){
 if(!on){delete form.value.sources[o.key];return}
 const take=Math.min(o.left,o.bunches||o.left),share=o.bunches?take/o.bunches:1
 form.value.sources[o.key]={on:true,bunches:take,kg:Math.round(o.kg*share*1000)/1000,farm_block:o.farm_block,bunch_tag:o.bunch_tag,harvest_entry:o.harvest_entry}
}
const picked=computed(()=>Object.values(form.value?.sources||{}))
// A shift holds one row per lô and colour: harvest lines of the same lô and colour picked together are added up
// (the row then traces to every harvest of that colour, not to one line).
function mergedSources(list){
 const rows=new Map()
 for(const s of list){
  const key=s.farm_block+'|'+s.bunch_tag,row=rows.get(key)
  if(row){row.bunches+=Number(s.bunches||0);row.kg=Math.round((row.kg+Number(s.kg||0))*1000)/1000;row.harvest_entry=null}
  else rows.set(key,{farm_block:s.farm_block,bunch_tag:s.bunch_tag,bunches:Number(s.bunches||0),kg:Number(s.kg||0),harvest_entry:s.harvest_entry||null})
 }
 return [...rows.values()]
}
const totalKg=computed(()=>picked.value.reduce((n,s)=>n+Number(s.kg||0),0))
const totalBunches=computed(()=>picked.value.reduce((n,s)=>n+Number(s.bunches||0),0))
async function save(close=false){
 const f=form.value
 if(!f.shift_code||!f.posting_date||!f.start||!f.end){formError.value='Nhập mã ca, ngày và giờ bắt đầu, kết thúc.';return}
 if(!picked.value.length){formError.value='Chọn ít nhất một dòng thu hoạch làm nguồn buồng.';return}
 saving.value=true;formError.value=''
 try{
  const values={shift_code:f.shift_code,posting_date:f.posting_date,started_at:f.posting_date+' '+f.start+':00',ended_at:f.posting_date+' '+f.end+':00',
   finished_kg:Number(f.finished_kg||0),secondary_kg:Number(f.secondary_kg||0),cartons:Number(f.cartons||0),notes:f.notes,
   sources:mergedSources(picked.value)}
  let data=await api('save_shift',{farm:props.farm,values:JSON.stringify(values),name:f.name||undefined,expected_modified:f.modified||undefined},true)
  if(close)data=await api('close_shift',{name:data.doc.name,expected_modified:data.doc.modified},true)
  notice.value=close?'Đã đóng ca '+data.doc.shift_code+'.':'Đã lưu ca '+data.doc.shift_code+'.'
  form.value=null;opened.value=close?data:null;await load()
 }catch(e){formError.value=e.message}
 finally{saving.value=false}
}
async function showTrace(){try{traced.value=await api('trace',{shift:opened.value.doc.name})}catch(e){formError.value=e.message}}
async function receive(){
 saving.value=true;formError.value=''
 try{
  const r=await call('lotus_farm.finance.costing.receive_shift',{shift:opened.value.doc.name},true)
  notice.value='Đã lập phiếu nhập kho nháp '+r.stock_entry+': '+amountText(r.kg)+' kg, '+amountText(Math.round(r.amount))+' đ. Kế toán kiểm rồi duyệt ở Kho.'
  opened.value=await api('shift',{name:opened.value.doc.name});await load()
 }catch(e){formError.value=e.message}
 finally{saving.value=false}
}
const splitColumns=[
 {field:'block_code',headerName:'Lô',minWidth:70},{field:'colour',headerName:'Màu dây',minWidth:90},
 {field:'bunches',headerName:'Buồng',minWidth:80,sum:true},{field:'kg',headerName:'Kg vào',minWidth:90,sum:true},
 {field:'finished_kg',headerName:'Thành phẩm (kg)',minWidth:120,sum:true},{field:'cartons',headerName:'Thùng',minWidth:80,sum:true},
 {field:'kg_per_bunch',headerName:'Kg/buồng',minWidth:90,sum:false},{field:'cartons_per_bunch',headerName:'Thùng/buồng',minWidth:100,sum:false},
 {field:'packout_percent',headerName:'Tỷ lệ đóng gói',valueFormatter:p=>p.value==null?'':amountText(p.value)+'%',minWidth:110,sum:false},
]
</script>

<template>
 <section class="packhouse" :class="{'packhouse--mobile':mobile}" :aria-busy="busy">
  <div class="packhouse__tools">
   <LotusField v-model="since" label="Ca từ ngày" type="date" :mobile="mobile"/>
   <UiButton type="button" @click="openNew">Thêm ca</UiButton>
  </div>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-if="notice" class="stock-success" role="status">{{notice}}</p>
  <p v-if="!busy&&!rows.length" class="lotus-form-note">Chưa có ca đóng gói trong khoảng này.</p>
  <div class="packhouse__cards">
   <button v-for="r in rows" :key="r.name" type="button" class="packhouse__card" :class="{'is-open':r.docstatus!==1}" @click="open(r)">
    <strong>Ca {{r.shift_code}} · {{formatDate(r.posting_date)}}</strong>
    <span>{{amountText(r.input_kg)}} kg vào · {{amountText(r.finished_kg)}} kg thành phẩm ({{pct(r.packout_percent)}}) · {{amountText(r.cartons)}} thùng</span>
    <span>{{amountText(r.bunches)}} buồng từ {{r.lots}} lô · {{receiptText(r)}}</span>
   </button>
  </div>

  <ModalForm :model-value="!!form" :title="form?.name?'Ca '+form.shift_code:'Thêm ca đóng gói'" width="900px" submit-label="Lưu ca" :busy="saving" :error="formError"
   @update:model-value="v=>!v&&(form=null)" @submit="save(false)">
   <template v-if="form">
    <FormGrid :columns="mobile?1:3">
     <LotusField v-model="form.shift_code" label="Mã ca" required placeholder="VD: S1" :mobile="mobile"/>
     <LotusField v-model="form.posting_date" label="Ngày" type="date" required :mobile="mobile" @update:model-value="d=>offer(d,form.name)"/>
     <div class="packhouse__times"><LotusField v-model="form.start" label="Bắt đầu" type="time" required :mobile="mobile"/><LotusField v-model="form.end" label="Kết thúc" type="time" required :mobile="mobile"/></div>
    </FormGrid>
    <h3 class="packhouse__title">Nguồn buồng (dòng thu hoạch đã xác nhận)</h3>
    <p v-if="!choices.length" class="lotus-form-note">Không có buồng đã thu mà chưa vào xưởng đến ngày này.</p>
    <ul class="packhouse__sources">
     <li v-for="o in choices" :key="o.key" :class="{'is-on':!!form.sources[o.key]}">
      <LotusField :model-value="!!form.sources[o.key]" type="checkbox" :label="'Lô '+(o.block_code||o.farm_block)+' · '+(o.colour||'')+(o.week?' tuần '+o.week:'')" :mobile="mobile" @update:model-value="v=>toggle(o,v)"/>
      <span><b class="packhouse__swatch" :style="{background:swatch(o.colour_code)}" aria-hidden="true"></b>thu {{o.posting_date?formatDate(o.posting_date):''}} · còn {{amountText(o.left)}} buồng</span>
      <div v-if="form.sources[o.key]" class="packhouse__qty">
       <LotusField v-model="form.sources[o.key].bunches" label="Buồng" type="number" inputmode="numeric" required :mobile="mobile"/>
       <LotusField v-model="form.sources[o.key].kg" label="Kg" type="number" inputmode="decimal" required :mobile="mobile"/>
      </div>
     </li>
    </ul>
    <p class="lotus-form-note">Đã chọn {{amountText(totalBunches)}} buồng, {{amountText(totalKg)}} kg đưa vào ca.</p>
    <h3 class="packhouse__title">Kết quả đóng gói</h3>
    <FormGrid :columns="mobile?1:3">
     <LotusField v-model="form.finished_kg" label="Thành phẩm (kg)" type="number" inputmode="decimal" :mobile="mobile"/>
     <LotusField v-model="form.secondary_kg" label="Phụ phẩm (kg)" type="number" inputmode="decimal" :mobile="mobile"/>
     <LotusField v-model="form.cartons" label="Số thùng" type="number" inputmode="numeric" :mobile="mobile"/>
    </FormGrid>
    <LotusField v-model="form.notes" label="Ghi chú" type="textarea" :mobile="mobile"/>
    <div class="packhouse__close"><UiButton type="button" variant="outline" :disabled="saving" @click="save(true)">Lưu và đóng ca</UiButton>
     <span class="lotus-form-note">Đóng ca thì không sửa được nữa; số được chia theo kg cho từng lô.</span></div>
   </template>
  </ModalForm>

  <ModalForm :model-value="!!opened" :title="opened?'Ca '+opened.doc.shift_code+' · '+formatDate(opened.doc.posting_date):''" width="960px" readonly :error="formError"
   @update:model-value="v=>!v&&(opened=null)">
   <template v-if="opened">
    <p class="lotus-form-note">{{amountText(opened.doc.input_kg)}} kg vào · {{amountText(opened.doc.finished_kg)}} kg thành phẩm · {{amountText(opened.doc.secondary_kg)}} kg phụ phẩm ·
     hao {{amountText(opened.doc.loss_kg)}} kg · tỷ lệ đóng gói {{pct(opened.doc.packout_percent)}} · {{amountText(opened.doc.cartons)}} thùng</p>
    <DataTable :rows="opened.split" :columns="splitColumns" row-key="harvest_entry" storage-key="packhouse-split" :selection-enabled="false" :paginate="false"
     :export-title="'Ca '+opened.doc.shift_code+' theo lô'"/>
    <div class="packhouse__actions">
     <UiButton type="button" variant="outline" @click="showTrace">Truy vết về lô</UiButton>
     <UiButton v-if="opened.doc.docstatus===0&&opened.can_write" type="button" variant="outline" @click="edit(opened)">Sửa ca</UiButton>
     <UiButton v-if="opened.doc.docstatus===1&&opened.can_receive&&opened.receipt_state==null" type="button" :disabled="saving" @click="receive">Lập phiếu nhập kho thành phẩm</UiButton>
     <span v-if="opened.receipt_state!=null" class="lotus-form-note">Phiếu nhập kho {{opened.doc.stock_entry}}: {{opened.receipt_state===1?'đã duyệt':'nháp, chờ duyệt ở Kho'}}</span>
    </div>
    <div v-if="traced" class="packhouse__trace">
     <article v-for="t in traced.sources" :key="t.farm_block+t.bunch_tag">
      <strong>Lô {{t.block_code}} · {{t.colour}} · {{amountText(t.bunches)}} buồng</strong>
      <span v-for="h in t.harvests" :key="h.name">Thu {{formatDate(h.posting_date)}}: {{amountText(h.qty)}} buồng, {{amountText(h.weight_kg)}} kg</span>
      <span v-if="!t.sprays.length">Không có dòng phun thuốc, bón phân trong 90 ngày trước khi thu.</span>
      <span v-for="s in t.sprays" :key="s.name+s.item_code">{{formatDate(s.posting_date)}} · {{s.work_name}} · {{s.item_name||s.item_code}}<template v-if="s.dose"> · {{s.dose}}</template><template v-if="s.phi_days"> · cách ly {{s.phi_days}} ngày</template></span>
     </article>
    </div>
   </template>
  </ModalForm>
 </section>
</template>

<style>
.packhouse{display:grid;gap:12px;min-width:0}
.packhouse__tools{display:flex;gap:12px;align-items:end;flex-wrap:wrap}
.packhouse__tools>*:first-child{min-width:180px}
.packhouse__cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:8px}
.packhouse--mobile .packhouse__cards{grid-template-columns:1fr}
.packhouse__card{display:grid;gap:3px;padding:10px 12px;text-align:left;font:inherit;color:inherit;border:1px solid var(--lotus-border);border-left:4px solid var(--lotus-success);border-radius:var(--lotus-radius-md);background:var(--lotus-surface);cursor:pointer}
.packhouse__card.is-open{border-left-color:var(--lotus-warning)}
.packhouse__card strong{color:var(--lotus-text-strong)}
.packhouse__card span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.packhouse__title{margin:12px 0 4px;font-size:var(--lotus-text-sm);font-weight:600;color:var(--lotus-muted)}
.packhouse__times{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.packhouse__sources{list-style:none;margin:0;padding:0;display:grid;gap:6px}
.packhouse__sources li{display:grid;gap:4px;padding:6px 8px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md)}
.packhouse__sources li.is-on{border-color:var(--lotus-primary)}
.packhouse__sources span{font-size:var(--lotus-text-sm);color:var(--lotus-muted);display:flex;align-items:center;gap:6px}
.packhouse__qty{display:grid;grid-template-columns:repeat(2,minmax(0,160px));gap:8px}
.packhouse__swatch{display:inline-block;width:12px;height:12px;border-radius:50%;border:1px solid var(--lotus-border)}
.packhouse__close,.packhouse__actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:8px}
.packhouse__trace{display:grid;gap:8px;margin-top:8px}
.packhouse__trace article{display:grid;gap:2px;padding:8px 10px;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md)}
.packhouse__trace span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
</style>
