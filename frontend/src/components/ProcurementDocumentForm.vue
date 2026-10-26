<script setup>
import {workFarm} from '../work-farm'
import {computed,watch} from 'vue'
import FormGrid from './form/FormGrid.vue'
import FormSection from './form/FormSection.vue'
import LotusField from './form/LotusField.vue'
import LineItemsEditor from './form/LineItemsEditor.vue'
import {Button} from './ui/button'
import LotusMobileButton from './LotusMobileButton.vue'
import DocumentReader from './DocumentReader.vue'
import {unitLabel} from '../units'
import {newPurchaseLine,purchaseUnits,purchaseTotal} from '../mobile-purchase'
import {allowedKinds,purchaseKind,money} from '../procurement'
// Fields of Đề nghị mua / Báo giá / Đơn mua. The surrounding ResponsiveForm owns submit and close.
const props=defineProps({mobile:Boolean,modelValue:Object,catalog:Object,type:String,saving:Boolean})
const emit=defineEmits(['update:modelValue','request','add-supplier','add-item'])
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const options=(rows,label)=>rows?.map(r=>({value:r.name,label:r[label]||r.name}))||[]
const itemOf=code=>props.catalog.items.find(r=>r.name===code)
const vatOptions=['KCT','0','5','8','10'].map(v=>({value:v,label:v==='KCT'?'Không chịu thuế':v+'%'}))
const lineColumns=computed(()=>[
 {field:'item',label:'Mặt hàng',required:true,options:options(props.catalog.items,'item_name'),width:'minmax(200px,2.2fr)'},
 {field:'kind',label:'Loại mua',required:true,options:row=>allowedKinds(itemOf(row.item)),searchable:false,width:'minmax(130px,1fr)'},
 {field:'qty',label:'Số lượng',type:'number',required:true,props:{min:0.000001},width:'minmax(100px,.8fr)'},
 {field:'uom',label:'Đơn vị',required:true,options:row=>purchaseUnits(row.item,props.catalog.items,props.catalog.conversions).map(u=>({value:u,label:unitLabel(u)})),searchable:false,width:'minmax(100px,.8fr)'},
 {field:'rate',label:'Đơn giá chưa VAT',type:'money',props:{min:0},width:'minmax(130px,1fr)'},
 {field:'vat_code',label:'VAT',options:vatOptions,searchable:false,props:{emptyOption:null},width:'minmax(120px,.9fr)'}
])
// Vườn sử dụng and Vận chuyển belong to the whole order. Lines still carry lotus_farm / freight for the server:
// the chosen farm is copied to every line, the order's freight is split by line value (by quantity while prices are empty).
const farmOptions=computed(()=>(props.catalog.farms||[]).map(f=>({value:f.name,label:f.farm_name||f.name})))
const lineFarms=computed(()=>[...new Set((props.modelValue?.items||[]).map(r=>r.lotus_farm||''))])
watch(()=>props.modelValue,draft=>{
 if(!draft)return
 if(draft.order_farm===undefined){const work=workFarm();draft.order_farm=lineFarms.value.length===1&&lineFarms.value[0]?lineFarms.value[0]:!draft.name&&props.catalog.farms?.some(f=>f.name===work)?work:''}
 if(draft.order_freight===undefined)draft.order_freight=(draft.items||[]).reduce((sum,r)=>sum+Number(r.freight||0),0)
},{immediate:true})
function chooseFarm(value){const draft=props.modelValue;draft.order_farm=value||'';for(const row of draft.items||[])row.lotus_farm=draft.order_farm}
watch(()=>[props.modelValue?.order_freight,props.modelValue?.order_farm,...(props.modelValue?.items||[]).map(r=>r.item+'|'+r.qty+'|'+r.rate)],()=>{
 const draft=props.modelValue
 if(!draft||draft.order_freight===undefined)return
 const rows=draft.items||[]
 if(draft.order_farm)for(const row of rows)if(!row.lotus_farm)row.lotus_farm=draft.order_farm
 const total=Math.max(0,Number(draft.order_freight)||0)
 const values=rows.map(r=>Number(r.qty||0)*Number(r.rate||0))
 const basis=values.some(v=>v>0)?values:rows.map(r=>Number(r.qty||0)||1)
 const weight=basis.reduce((a,b)=>a+b,0)||1
 let left=total
 rows.forEach((row,index)=>{const share=index===rows.length-1?left:Math.round(total*basis[index]/weight);row.freight=share;left-=share})
},{immediate:true})
// AI-read quote / invoice / delivery note: pick the matched supplier and append the matched lines; the user reviews before saving.
const vatCode=percent=>{if(percent==null||percent==='')return 'KCT';const p=Number(percent);return ['0','5','8','10'].reduce((best,v)=>Math.abs(Number(v)-p)<Math.abs(Number(best)-p)?v:best,'0')}
const docKinds={quote:'báo giá',invoice:'hóa đơn',delivery_note:'phiếu giao hàng',purchase_order:'đơn đặt hàng',other:'chứng từ'}
function applyDocument(result){
 const draft=props.modelValue,doc=result.document
 const supplier=result.supplier.match?.name
 if(props.type!=='need'&&supplier&&props.catalog.suppliers?.some(s=>s.name===supplier))draft.supplier=supplier
 const documentVat=doc.vat_amount&&doc.subtotal?doc.vat_amount/doc.subtotal*100:null
 const lines=result.lines.filter(line=>line.item&&itemOf(line.item.code)).map(line=>{
  const item=itemOf(line.item.code),units=purchaseUnits(item.name,props.catalog.items,props.catalog.conversions)
  return {...newPurchaseLine(),item:item.name,kind:purchaseKind(item),qty:line.qty||1,uom:units.includes(line.uom)?line.uom:item.stock_uom,rate:line.rate??'',vat_code:vatCode(line.vat_percent??documentVat)}
 })
 if(lines.length)draft.items=[...draft.items.filter(row=>row.item),...lines]
 const ref=[doc.number&&'số '+doc.number,doc.date&&'ngày '+doc.date.split('-').reverse().join('/')].filter(Boolean).join(' ')
 if(ref&&!draft.notes)draft.notes='Theo '+(docKinds[doc.type]||'chứng từ')+' '+ref+(result.supplier.text?' của '+result.supplier.text:'')
}
// Choosing another item resets its unit and purchase kind (desktop picker and phone list alike).
const chosen=new WeakMap()
watch(()=>(props.modelValue?.items||[]).map(r=>r.item),()=>{for(const row of props.modelValue?.items||[]){if(!chosen.has(row)){chosen.set(row,row.item);continue}if(chosen.get(row)!==row.item){chosen.set(row,row.item);const item=itemOf(row.item);Object.assign(row,{uom:item?.stock_uom||'',kind:purchaseKind(item),material_request:'',material_request_item:''})}}},{immediate:true})
</script>
<template>
 <FormSection title="Thông tin chung">
  <FormGrid :columns="3">
   <DocumentReader :mobile="mobile" :disabled="saving" label="Đọc báo giá / hóa đơn bằng AI" @read="applyDocument"/>
   <LotusField v-if="type!=='need'&&catalog.requests?.length" :mobile="mobile" label="Lấy dòng từ đề nghị đã duyệt" :options="options(catalog.requests)" @update:model-value="emit('request',$event)"/>
   <LotusField v-if="type!=='need'" :mobile="mobile" v-model="modelValue.supplier" label="Nhà cung cấp" :options="options(catalog.suppliers,'supplier_name')" required/>
   <LotusField v-if="type!=='need'&&farmOptions.length" :mobile="mobile" :model-value="modelValue.order_farm" label="Vườn sử dụng" :options="farmOptions" empty-option="Không gắn vườn (chi phí chung)" :searchable="false" :hint="lineFarms.length>1&&!modelValue.order_farm?'Các dòng đang thuộc nhiều vườn khác nhau; chọn một vườn để áp cho cả đơn.':''" @update:model-value="chooseFarm"/>
   <LotusField v-if="type!=='need'" :mobile="mobile" v-model="modelValue.order_freight" label="Phí vận chuyển cả đơn" type="money" min="0" hint="Tự chia vào các dòng theo giá trị hàng."/>
   <LotusField :mobile="mobile" v-model="modelValue.warehouse" label="Kho nhận / bộ phận" :options="options(catalog.warehouses,'warehouse_name')" required/>
   <LotusField :mobile="mobile" v-model="modelValue.expected_date" label="Ngày cần hàng / nghiệm thu" type="date" required/>
   <LotusField v-if="type==='quote'" :mobile="mobile" v-model="modelValue.valid_till" label="Hiệu lực báo giá đến" type="date" required/>
   <LotusField :mobile="mobile" v-model="modelValue.notes" :label="type==='need'?'Lý do đề nghị':'Nội dung giao hàng / dịch vụ'" type="textarea" wide :required="type==='need'"/>
  </FormGrid>
 </FormSection>
 <FormSection>
  <LineItemsEditor v-model="modelValue.items" title="Mặt hàng" add-label="Thêm dòng" :columns="lineColumns" :new-row="newPurchaseLine" :mobile="mobile" :readonly="saving">
   <template #footer>
    <component :is="button" v-if="type!=='need'&&catalog.can_create_supplier" type="button" variant="outline" size="sm" @click="emit('add-supplier')">Thêm nhà cung cấp mới</component>
    <component :is="button" v-if="catalog.can_create_item" type="button" variant="outline" size="sm" @click="emit('add-item',modelValue.items.length-1)">Thêm mặt hàng mới</component>
    <span v-if="type!=='need'" class="lotus-form-note lotus-lines__total">Tổng tạm tính {{money(purchaseTotal(modelValue))}} đ</span>
   </template>
  </LineItemsEditor>
 </FormSection>
</template>
