<script setup>
import {computed} from 'vue'
import ProcurementField from './ProcurementField.vue'
import {Button} from './ui/button'
import LotusMobileButton from './LotusMobileButton.vue'
import {newPurchaseLine,purchaseUnits} from '../mobile-purchase'
import {allowedKinds,purchaseKind} from '../procurement'
const props=defineProps({mobile:Boolean,modelValue:Object,catalog:Object,type:String,saving:Boolean})
const emit=defineEmits(['update:modelValue','submit','cancel','request'])
const button=computed(()=>props.mobile?LotusMobileButton:Button)
const options=(rows,label)=>rows?.map(r=>({value:r.name,label:r[label]||r.name}))||[]
function patch(v){emit('update:modelValue',{...props.modelValue,...v})}
function line(i,v){patch({items:props.modelValue.items.map((r,n)=>n===i?{...r,...v}:r)})}
function choose(i,code){const item=props.catalog.items.find(r=>r.name===code);line(i,{item:code,uom:item?.stock_uom||'',kind:purchaseKind(item),material_request:'',material_request_item:''})}
</script>
<template><form class="procurement-form" @submit.prevent="emit('submit')"><fieldset :disabled="saving">
 <div class="procurement-fields">
  <ProcurementField v-if="type!=='need'&&catalog.requests?.length" :mobile="mobile" label="Lấy dòng từ đề nghị đã duyệt" :options="options(catalog.requests)" @update:model-value="emit('request',$event)"/>
  <ProcurementField v-if="type!=='need'" :mobile="mobile" v-model="modelValue.supplier" label="Nhà cung cấp" :options="options(catalog.suppliers,'supplier_name')" required/>
  <ProcurementField :mobile="mobile" v-model="modelValue.warehouse" label="Kho nhận / bộ phận" :options="options(catalog.warehouses,'warehouse_name')" required/>
  <ProcurementField :mobile="mobile" v-model="modelValue.expected_date" label="Ngày cần hàng / nghiệm thu" type="date" required/>
  <ProcurementField v-if="type==='quote'" :mobile="mobile" v-model="modelValue.valid_till" label="Hiệu lực báo giá đến" type="date" required/>
  <ProcurementField :mobile="mobile" v-model="modelValue.notes" :label="type==='need'?'Lý do đề nghị':'Nội dung giao hàng / dịch vụ'" type="textarea" :required="type==='need'"/>
 </div>
 <section v-for="(r,i) in modelValue.items" :key="r.id||i" class="procurement-line">
  <div class="procurement-actions"><strong>Dòng {{i+1}}</strong><component :is="button" v-if="modelValue.items.length>1" type="button" @click="patch({items:modelValue.items.filter((_,n)=>n!==i)})">Xóa dòng</component></div>
  <div class="procurement-fields">
   <ProcurementField :mobile="mobile" :model-value="r.item" label="Mặt hàng" :options="options(catalog.items,'item_name')" required @update:model-value="choose(i,$event)"/>
   <ProcurementField :mobile="mobile" v-model="r.kind" label="Loại mua" :options="allowedKinds(catalog.items.find(x=>x.name===r.item))" :searchable="false" required/>
   <ProcurementField v-if="catalog.farms?.length" :mobile="mobile" v-model="r.lotus_farm" label="Vườn sử dụng" :options="options(catalog.farms)"/>
   <ProcurementField :mobile="mobile" v-model="r.qty" label="Số lượng" type="number" min="0.000001" step="any" required/>
   <ProcurementField :mobile="mobile" v-model="r.uom" label="Đơn vị" :options="purchaseUnits(r.item,catalog.items,catalog.conversions).map(u=>({value:u,label:u}))" :searchable="false" required/>
   <ProcurementField :mobile="mobile" v-model="r.rate" label="Đơn giá chưa VAT" type="number" min="0" step="any"/>
   <ProcurementField :mobile="mobile" v-model="r.vat_code" label="VAT" :options="['KCT','0','5','8','10'].map(v=>({value:v,label:v==='KCT'?'Không chịu thuế':v+'%'}))" :searchable="false"/>
   <ProcurementField :mobile="mobile" v-model="r.freight" label="Vận chuyển dòng này" type="number" min="0" step="any"/>
  </div>
 </section>
 <div class="procurement-actions"><component :is="button" type="button" @click="patch({items:[...modelValue.items,newPurchaseLine()]})">Thêm dòng</component><component :is="button" type="submit" :disabled="saving">Lưu nháp</component><component :is="button" type="button" @click="emit('cancel')">Đóng</component></div>
</fieldset></form></template>
