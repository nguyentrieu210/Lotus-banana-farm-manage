<script setup>
import LotusField from './form/LotusField.vue'
import {computed} from 'vue'
import {Icon,NoticeBar} from 'vant'
import MobileLinkField from './MobileLinkField.vue'
import LotusMobileInput from './LotusMobileInput.vue'
import LotusMobileSelect from './LotusMobileSelect.vue'
import LotusMobileButton from './LotusMobileButton.vue'
import LotusMobileFile from './LotusMobileFile.vue'
import {unitLabel} from '../units'
import {newPurchaseLine,purchaseUnits,purchaseTotal,PURCHASE_MODES} from '../mobile-purchase'
import {purchaseKind,allowedKinds} from '../procurement'
const props=defineProps({modelValue:{type:Object,required:true},items:{type:Array,default:()=>[]},conversions:{type:Array,default:()=>[]},
 warehouses:{type:Array,default:()=>[]},suppliers:{type:Array,default:()=>[]},farms:{type:Array,default:()=>[]},requests:{type:Array,default:()=>[]},selectedRequest:{type:String,default:''},
 currency:{type:String,default:'VND'},canCreateSupplier:Boolean,canCreateItem:Boolean,saving:Boolean,online:{type:Boolean,default:true},quote:Object,saved:Object})
const emit=defineEmits(['update:modelValue','update:quote','update:selectedRequest','submit','add-supplier','add-item','retry-quote','view-saved','new-order'])
const order=computed(()=>props.modelValue)
const warehouseOptions=computed(()=>props.warehouses.map(r=>({value:r.name,label:r.warehouse_name||r.name})))
const supplierOptions=computed(()=>props.suppliers.filter(r=>!r.disabled).map(r=>({value:r.name,label:r.supplier_name||r.name})))
const itemOptions=computed(()=>props.items.map(r=>({value:r.name,label:r.item_name||r.name})))
const requestOptions=computed(()=>[{value:'',label:'Nhập đơn mới'},...props.requests.map(r=>({value:r.name,label:r.name+' · '+r.items.length+' mặt hàng'}))])
const total=computed(()=>Number(purchaseTotal(order.value)).toLocaleString('vi-VN',{maximumFractionDigits:0})+' '+props.currency)
function patch(values){emit('update:modelValue',{...order.value,...values})}
function linePatch(index,values){patch({items:order.value.items.map((r,i)=>i===index?{...r,...values}:r)})}
function chooseItem(index,code){const item=props.items.find(r=>r.name===code);linePatch(index,{item:code,uom:item?.stock_uom||'',kind:purchaseKind(item),material_request:'',material_request_item:''})}
</script>
<template>
 <section v-if="saved" class="lotus-purchase-result" aria-live="polite">
  <Icon :name="saved.quoteError?'warning-o':'checked'" :class="{'has-warning':saved.quoteError}"/>
  <h2>Đã lưu đơn nháp</h2><strong>{{saved.name}}</strong>
  <NoticeBar v-if="saved.quoteError" wrapable :scrollable="false" text="Đơn đã lưu. Báo giá chưa tải lên; thử lại bên dưới."/>
  <LotusMobileButton v-if="saved.quoteError" class="mobile-submit" :loading="saving" :disabled="saving||!online" @click="emit('retry-quote')">Tải lại báo giá</LotusMobileButton>
  <LotusMobileButton class="mobile-submit" :disabled="saving" @click="emit('view-saved')">Xem đơn đã lưu</LotusMobileButton>
  <LotusMobileButton class="mobile-add" :disabled="saving||!!saved.quoteError" @click="emit('new-order')">Tạo đơn mới</LotusMobileButton>
 </section>
 <form v-else class="lotus-purchase-form" @submit.prevent="emit('submit')">
  <fieldset class="mobile-form-fields" :disabled="saving">
   <MobileLinkField v-if="requests.length&&!order.name" label="Lấy hàng từ đề nghị mua" :model-value="selectedRequest" :options="requestOptions" placeholder="Chọn đề nghị mua nếu có" @update:modelValue="emit('update:selectedRequest',$event)"/>
   <MobileLinkField label="Nhà cung cấp" :model-value="order.supplier" :options="supplierOptions" :searchable="true" placeholder="Gõ tìm nhà cung cấp…" required @update:modelValue="patch({supplier:$event})"/>
   <LotusMobileButton v-if="canCreateSupplier" class="lotus-purchase-add-supplier" :disabled="saving||!online" @click="emit('add-supplier')">+ Thêm nhà cung cấp</LotusMobileButton>
   <LotusMobileSelect label="Cách mua" :model-value="order.mode" :options="PURCHASE_MODES" @update:modelValue="patch({mode:$event})"/>
   <MobileLinkField label="Kho nhận mặc định" :model-value="order.warehouse" :options="warehouseOptions" :searchable="false" placeholder="Chọn kho nhận" required @update:modelValue="patch({warehouse:$event,items:order.items.map(r=>({...r,warehouse:r.material_request?r.warehouse:''}))})"/>
   <LotusMobileInput label="Ngày giao dự kiến" :model-value="order.expected_date" type="date" required @update:modelValue="patch({expected_date:$event})"/>
   <h2>Mặt hàng</h2>
   <section v-for="(line,index) in order.items" :key="line.id||line._key" class="lotus-purchase-line mobile-line">
    <div class="mobile-line-title"><strong>Hàng {{index+1}}</strong><LotusMobileButton v-if="order.items.length>1" :aria-label="'Xóa hàng '+(index+1)" @click="patch({items:order.items.filter((_,i)=>i!==index)})">Xóa</LotusMobileButton></div>
    <MobileLinkField label="Tên hàng" :model-value="line.item" :options="itemOptions" :searchable="true" placeholder="Gõ tên hoặc mã hàng…" required @update:modelValue="chooseItem(index,$event)"/>
    <LotusMobileButton v-if="canCreateItem" @click="emit('add-item',index)">Thêm mặt hàng</LotusMobileButton>
    <div class="mobile-qty-grid"><LotusMobileInput label="Số lượng" :model-value="line.qty" type="number" min="0.000001" step="any" inputmode="decimal" required @update:modelValue="linePatch(index,{qty:$event})"/>
     <LotusMobileSelect label="Đơn vị" :model-value="line.uom" :options="purchaseUnits(line.item,items,conversions).map(u=>({value:u,label:unitLabel(u)}))" required @update:modelValue="linePatch(index,{uom:$event})"/></div>
    <LotusMobileInput label="Đơn giá" :model-value="line.rate" type="money" placeholder="Theo báo giá" @update:modelValue="linePatch(index,{rate:$event})"/>
    <LotusMobileSelect label="Loại mua" :model-value="line.kind||purchaseKind(items.find(r=>r.name===line.item))" :options="allowedKinds(items.find(r=>r.name===line.item))" @update:modelValue="linePatch(index,{kind:$event})"/>
    <LotusMobileSelect label="VAT" :model-value="line.vat_code||'KCT'" :options="['KCT','0','5','8','10'].map(v=>({value:v,label:v==='KCT'?'Không chịu thuế':v+'%'}))" @update:modelValue="linePatch(index,{vat_code:$event})"/>
    <LotusMobileInput label="Vận chuyển dòng này" :model-value="line.freight||0" type="money" @update:modelValue="linePatch(index,{freight:$event})"/>
    <MobileLinkField v-if="farms.length" label="Vườn sử dụng" :model-value="line.lotus_farm||''" :options="farms.map(f=>({value:f.name,label:f.farm_name||f.name}))" @update:modelValue="linePatch(index,{lotus_farm:$event})"/>
    <small v-if="line.material_request" class="mobile-subtle">Theo đề nghị {{line.material_request}}</small>
   </section>
   <LotusMobileButton class="mobile-add" @click="patch({items:[...order.items,newPurchaseLine()]})">+ Thêm mặt hàng</LotusMobileButton>
   <div class="lotus-purchase-total"><span>Tổng tiền tạm tính</span><strong>{{total}}</strong></div>
   <LotusField mobile label="Tệp báo giá (tùy chọn)" type="file" accept=".pdf,image/jpeg,image/png,image/webp" :disabled="saving" :hint="quote?quote.name:''" @change="emit('update:quote',$event.target.files?.[0]||null)"/>
   <LotusMobileInput label="Ghi chú giao hàng" :model-value="order.notes" type="textarea" :rows="3" maxlength="500" @update:modelValue="patch({notes:$event})"/>
   <LotusMobileButton type="submit" class="mobile-submit" :loading="saving" :disabled="saving||!online">Lưu đơn nháp</LotusMobileButton>
  </fieldset>
 </form>
</template>
