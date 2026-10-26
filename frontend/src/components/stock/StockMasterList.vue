<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import ListPage from '../ListPage.vue'
import LotusIcon from '../LotusIcon.vue'
import {Button as UiButton} from '../ui/button'
import {masterColumns} from '../../stock-columns'
import {unitLabel,normalizeUnit} from '../../units'
import LotusField from '../form/LotusField.vue'
// Danh mục kho: Kho · Vật tư · Nhóm vật tư · Đơn vị tính. Open a row to edit it in the shared master form.
const props=defineProps({kind:{type:String,required:true},company:String,session:Object,refreshKey:Number})
const emit=defineEmits(['new-master','edit-master'])
const meta={
 warehouses:{title:'Danh sách kho',master:'warehouse',doctype:'Warehouse',add:'Thêm kho',empty:'Chưa khai báo kho.'},
 items:{title:'Danh mục vật tư',master:'item',doctype:'Item',add:'Thêm vật tư',empty:'Chưa có vật tư.'},
 groups:{title:'Nhóm vật tư',master:'group',doctype:'Item Group',add:'Thêm nhóm vật tư',empty:'Chưa có nhóm vật tư.'},
 uoms:{title:'Đơn vị tính',master:'uom',doctype:'UOM',add:'Thêm đơn vị tính',empty:'Chưa có đơn vị tính.'}
}
const info=computed(()=>meta[props.kind])
const data=ref(null),busy=ref(false),error=ref(''),search=ref('')
// ERPNext ships ~250 technical units (Abampere, Barleycorn…): by default list only units the items use or that have a Vietnamese name.
const uomScope=ref('used')
const usedUoms=computed(()=>new Set((data.value?.items||[]).flatMap(item=>[item.stock_uom,item.pack_uom]).filter(Boolean)))
const rows=computed(()=>{
 let all=data.value?.[props.kind]||[];const q=normalizeUnit(search.value)
 if(props.kind==='uoms'&&uomScope.value==='used'&&!q)all=all.filter(row=>usedUoms.value.has(row.name)||unitLabel(row.name)!==row.name)
 if(!q)return all
 return all.filter(row=>normalizeUnit([row.name,row.item_name,row.warehouse_name,row.item_group,row.parent_item_group,unitLabel(row.name)].filter(Boolean).join(' ')).includes(q))
})
async function load(){
 if(!props.company){data.value=null;return}
 busy.value=true;error.value=''
 try{data.value=await call('lotus_farm.warehouse_masters.master_lists',{company:props.company})}
 catch(e){error.value='Không tải được danh mục: '+e.message}
 finally{busy.value=false}
}
watch(()=>[props.company,props.refreshKey],load,{immediate:true})
defineExpose({refresh:load})
</script>

<template>
 <ListPage :title="info.title" :rows="rows" :columns="masterColumns[kind]" :loading="busy" :error="error" v-model:search="search" :search-placeholder="'Tìm '+info.title.toLowerCase()+'…'" @refresh="load"
   :storage-key="'lotus-stock-master-'+kind" show-empty-headers interactive :empty="search?'Không có dòng khớp từ khóa.':info.empty" @open="row=>emit('edit-master',info.master,row.name)">
  <template v-if="kind==='uoms'" #filters><LotusField v-model="uomScope" aria-label="Phạm vi đơn vị" :options="[{value:'used',label:'Đơn vị đang dùng / có tên tiếng Việt'},{value:'all',label:'Tất cả đơn vị ERPNext'}]" :searchable="false" :empty-option="null"/></template>
  <template #actions><UiButton :disabled="!company||!session?.permissions?.[info.doctype]" @click="emit('new-master',info.master)"><LotusIcon name="plus"/>{{info.add}}</UiButton></template>
 </ListPage>
</template>
