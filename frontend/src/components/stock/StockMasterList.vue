<script setup>
import {computed,ref,watch} from 'vue'
import {call} from '../../api'
import ListPage from '../ListPage.vue'
import LotusIcon from '../LotusIcon.vue'
import {Button as UiButton} from '../ui/button'
import {masterColumns} from '../../stock-columns'
import {unitLabel,normalizeUnit} from '../../units'
import LotusField from '../form/LotusField.vue'
import WorkspaceListToolbar from '../WorkspaceListToolbar.vue'
import MasterTree from './MasterTree.vue'
// Danh mục kho: Kho · Vật tư · Nhóm vật tư · Đơn vị tính. Open a row to edit it in the shared master form.
const props=defineProps({kind:{type:String,required:true},company:String,session:Object,refreshKey:Number})
const emit=defineEmits(['new-master','edit-master'])
// Nhóm vật tư và kho là cây (nhóm cha → nhóm con / kho con): shown as a tree, not a table.
const treeKinds=['groups','warehouses']
const tree=ref(null)
const money=n=>Number(n||0).toLocaleString('vi-VN')+' đ'
const rootLabel=node=>!node.parent?(props.kind==='groups'?'Tất cả nhóm hàng':'Tất cả kho'):''
const treeNodes=computed(()=>props.kind==='groups'
 ?(data.value?.group_tree||[]).map(g=>({id:g.name,parent:g.parent,label:rootLabel(g)||g.name,isGroup:!!g.is_group,count:g.item_count,meta:g.item_count&&g.active_count<g.item_count?(g.item_count-g.active_count)+' mã ngừng dùng':''}))
 :(data.value?.warehouse_tree||[]).map(w=>({id:w.name,parent:w.parent,label:rootLabel(w)||w.label,isGroup:!!w.is_group,count:w.item_count,muted:!!w.disabled,meta:w.is_group?'':[w.contact,w.stock_value?'Giá trị tồn '+money(w.stock_value):''].filter(Boolean).join(' · ')})))
function openNode(node){if(node.parent)emit('edit-master',info.value.master,node.id)}
function addChild(node){emit('new-master',info.value.master,node.id)}
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
const usedUoms=computed(()=>new Set((data.value?.items||[]).flatMap(item=>[item.stock_uom,item.pack_uom,...(item.conversions||[]).map(c=>c.uom)]).filter(Boolean)))
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
 <section v-if="treeKinds.includes(kind)" class="lotus-list-page" :aria-label="info.title">
  <WorkspaceListToolbar v-model="search" :placeholder="'Tìm '+info.title.toLowerCase()+'…'" :busy="busy" @refresh="load">
   <UiButton :disabled="!company||!session?.permissions?.[info.doctype]" @click="emit('new-master',info.master)"><LotusIcon name="plus"/>{{info.add}}</UiButton>
   <template #tools><UiButton variant="outline" @click="tree?.expandAll()">Mở hết</UiButton><UiButton variant="outline" @click="tree?.collapseAll()">Thu gọn</UiButton></template>
  </WorkspaceListToolbar>
  <p v-if="error" class="lotus-list-page__error" role="alert">{{error}}</p>
  <p v-else-if="busy&&!data" class="lotus-form-note">Đang tải…</p>
  <MasterTree v-else ref="tree" :nodes="treeNodes" :search="search" :storage-key="'stock-'+kind+'-'+company" :count-label="kind==='groups'?'mã':'mã tồn'"
   :group-icon="kind==='groups'?'boxes':'warehouse'" :leaf-icon="kind==='groups'?'package':'warehouse'" :add-label="kind==='groups'?'Thêm nhóm con':'Thêm kho con'"
   :can-add="!!company&&!!session?.permissions?.[info.doctype]" @open="openNode" @add="addChild"/>
  <p class="lotus-form-note">{{kind==='groups'?'Bấm tên nhóm để sửa hoặc chuyển sang nhóm cha khác; số mã ở nhóm cha gồm cả các nhóm con.':'Bấm tên kho để sửa hoặc chuyển nhóm kho; nhóm kho chỉ để gom các kho, hàng nằm ở kho con.'}}</p>
 </section>
 <ListPage v-else :title="info.title" :rows="rows" :columns="masterColumns[kind]" :loading="busy" :error="error" v-model:search="search" :search-placeholder="'Tìm '+info.title.toLowerCase()+'…'" @refresh="load"
   :storage-key="'lotus-stock-master-'+kind" show-empty-headers interactive :empty="search?'Không có dòng khớp từ khóa.':info.empty" @open="row=>emit('edit-master',info.master,row.name)">
  <template v-if="kind==='uoms'" #filters><LotusField v-model="uomScope" aria-label="Phạm vi đơn vị" :options="[{value:'used',label:'Đơn vị đang dùng / có tên tiếng Việt'},{value:'all',label:'Tất cả đơn vị ERPNext'}]" :searchable="false" :empty-option="null"/></template>
  <template #actions><UiButton :disabled="!company||!session?.permissions?.[info.doctype]" @click="emit('new-master',info.master)"><LotusIcon name="plus"/>{{info.add}}</UiButton></template>
 </ListPage>
</template>
