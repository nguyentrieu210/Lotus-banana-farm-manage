<script setup>
import {computed,ref} from 'vue'
import {call,upload} from '../../api'
import ModalForm from '../form/ModalForm.vue'
import {Button as UiButton} from '../ui/button'
import {FilePickerButton} from '../ui/file-input'
import {formatDate} from '../../format'
import {amountText} from '../../lot-entry-model.js'
// Phiếu giấy của tổ-ngày (lotus_farm.lot_paper_form): print the form, then read a photo of it into draft lines marked
// "máy đọc". The photo stays next to the lô still to check; a lô is checked by opening it and saving it, and the report
// cannot be sent while any machine-read line is unchecked.
const props=defineProps({data:{type:Object,required:true},farm:{type:String,required:true},team:{type:String,required:true},date:{type:String,required:true},
 editable:Boolean,mobile:Boolean})
const emit=defineEmits(['changed','open-lot'])
const busy=ref(false),error=ref(''),result=ref(null),zoom=ref(false)
const paper=computed(()=>props.data.paper||null)
const works=computed(()=>Object.fromEntries((props.data.works||[]).map(w=>[w.name,w])))
const pending=computed(()=>(props.data.lots||[]).map(lot=>({lot,lines:(lot.lines||[]).filter(l=>l.machine_read&&l.review_flags)})).filter(x=>x.lines.length))
async function print(){
 busy.value=true;error.value=''
 const win=window.open('','_blank')
 try{
  const r=await call('lotus_farm.lot_paper_form.form_url',{farm:props.farm,team:props.team,date:props.date},true)
  if(win)win.location=r.url;else window.location.href=r.url
  emit('changed','')
 }catch(e){error.value=e.message;win?.close()}
 finally{busy.value=false}
}
async function read([file]){
 if(!file)return
 busy.value=true;error.value='';result.value=null
 try{
  const report=props.data.report?.name||(await call('lotus_farm.lot_report.open_report',{farm:props.farm,team:props.team,date:props.date},true)).name
  const stored=await upload(file)
  result.value=await call('lotus_farm.lot_paper_form.read_photo',{report,file_url:stored.file_url},true)
  emit('changed','Máy đọc được '+result.value.lines+' dòng ở '+result.value.lots.length+' lô. Mở từng lô để kiểm rồi lưu trước khi gửi.')
 }catch(e){error.value=e.message}
 finally{busy.value=false}
}
const when=v=>v?formatDate(v)+' '+String(v).slice(11,16):''
const lineText=l=>(works.value[l.work_type]?.label||l.work_type)+(l.qty!=null?' · '+amountText(l.qty):'')+(l.weight_kg?' · '+amountText(l.weight_kg)+' kg':'')+(l.done?' · xong cả lô':'')
</script>

<template>
 <section class="paper-review" :class="{'paper-review--mobile':mobile}" :aria-busy="busy">
  <div class="paper-review__bar">
   <div><strong>Phiếu giấy</strong>
    <span v-if="paper?.read_at">Đã đọc ảnh lúc {{when(paper.read_at)}}<template v-if="pending.length"> · còn {{pending.length}} lô chưa kiểm</template><template v-else> · đã kiểm hết</template></span>
    <span v-else-if="paper?.printed_at">Đã in phiếu lúc {{when(paper.printed_at)}}. Ghi xong thì chụp ảnh phiếu.</span>
    <span v-else>In phiếu cho tổ ghi tay, rồi chụp ảnh để máy điền sẵn.</span></div>
   <div class="paper-review__actions">
    <UiButton type="button" variant="outline" :disabled="busy" @click="print">In phiếu giấy</UiButton>
    <FilePickerButton v-if="editable" variant="outline" accept="image/*" :capture="mobile?'environment':undefined"
     :label="mobile?'Chụp ảnh phiếu':'Đọc ảnh phiếu'" :disabled="busy" @files="read">{{mobile?'Chụp ảnh phiếu':'Đọc ảnh phiếu'}}</FilePickerButton>
   </div>
  </div>
  <p v-if="busy" class="lotus-form-note" role="status">Đang xử lý phiếu…</p>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <div v-if="paper?.photo&&(pending.length||paper.notes?.length)" class="paper-review__body">
   <button type="button" class="paper-review__photo" @click="zoom=true"><img :src="paper.photo" alt="Ảnh phiếu đã chụp"/></button>
   <div class="paper-review__list">
    <article v-for="p in pending" :key="p.lot.block" class="paper-review__lot">
     <header><strong>Lô {{p.lot.code}}</strong><UiButton type="button" size="sm" @click="emit('open-lot',p.lot)">Kiểm lô này</UiButton></header>
     <p v-for="l in p.lines" :key="l.name"><span>{{lineText(l)}}</span><em>{{l.review_flags}}</em></p>
    </article>
    <ul v-if="paper.notes?.length" class="paper-review__notes"><li v-for="n in paper.notes" :key="n">{{n}}</li></ul>
   </div>
  </div>
  <ModalForm :model-value="zoom" title="Ảnh phiếu" width="1100px" readonly @update:model-value="v=>zoom=v">
   <img v-if="paper?.photo" class="paper-review__big" :src="paper.photo" alt="Ảnh phiếu đã chụp, cỡ lớn"/>
  </ModalForm>
 </section>
</template>

<style>
.paper-review{display:grid;gap:8px;padding:10px 12px;border:1px dashed var(--lotus-border-strong);border-radius:var(--lotus-radius-md);background:var(--lotus-surface)}
.paper-review__bar{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.paper-review__bar>div:first-child{display:grid;gap:2px}
.paper-review__bar span{font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.paper-review__actions{display:flex;gap:8px;flex-wrap:wrap}
.paper-review__body{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:12px}
.paper-review--mobile .paper-review__body{grid-template-columns:1fr}
.paper-review__photo{padding:0;border:1px solid var(--lotus-border);border-radius:var(--lotus-radius-md);background:none;cursor:zoom-in;max-height:420px;overflow:hidden}
.paper-review__photo img{width:100%;display:block;object-fit:contain}
.paper-review__list{display:grid;gap:8px;align-content:start}
.paper-review__lot{display:grid;gap:4px;padding:8px 10px;border:1px solid var(--lotus-border);border-left:4px solid var(--lotus-warning);border-radius:var(--lotus-radius-md)}
.paper-review__lot header{display:flex;justify-content:space-between;align-items:center;gap:8px}
.paper-review__lot p{margin:0;display:grid;gap:1px;font-size:var(--lotus-text-sm)}
.paper-review__lot em{font-style:normal;color:var(--lotus-warning)}
.paper-review__notes{margin:0;padding-left:18px;font-size:var(--lotus-text-sm);color:var(--lotus-muted)}
.paper-review__big{width:100%;display:block}
</style>
