<script setup>
import {computed} from 'vue'
import {AgGridVue} from 'ag-grid-vue3'
import {AllCommunityModule,ModuleRegistry,themeQuartz} from 'ag-grid-community'
import {Button as UiButton} from './ui/button'
ModuleRegistry.registerModules([AllCommunityModule])
const props=defineProps({rows:{type:Array,default:()=>[]},columns:{type:Array,required:true},loading:Boolean,empty:{type:String,default:'Chưa có dữ liệu.'},interactive:Boolean})
const emit=defineEmits(['open','cell-open'])
const theme=themeQuartz.withParams({accentColor:'#5262ce',backgroundColor:'#fff',foregroundColor:'#263042',headerBackgroundColor:'#fafbfc',borderColor:'#e6e8ef',rowHoverColor:'#f5f7fb',fontFamily:'Inter, system-ui, sans-serif',fontSize:13,rowHeight:48,headerHeight:42,spacing:6})
const defs=computed(()=>props.columns.map(c=>({...c,flex:c.flex||1,minWidth:c.minWidth||140,sortable:true,filter:true,resizable:true})))
function value(row,col){const value=col.valueGetter?col.valueGetter({data:row}):row[col.field];return col.valueFormatter?col.valueFormatter({value,data:row}):value??'—'}
function open(event){if(props.interactive&&event.data)emit('open',event.data)}
</script>
<template>
 <div class="lotus-data-table" :aria-busy="loading">
  <div v-if="!rows.length" class="empty stock-empty" role="status">{{loading?'Đang tải…':empty}}</div>
  <template v-else>
   <div class="lotus-ag-grid-shell" :class="{'lotus-ag-grid-shell--scroll':rows.length>10}"><AgGridVue class="lotus-ag-grid" :theme="theme" :row-data="rows" :column-defs="defs" :dom-layout="rows.length>10?'normal':'autoHeight'" :animate-rows="true" :enable-cell-text-selection="true" @row-clicked="open" @cell-clicked="emit('cell-open',$event)" @cell-key-down="event=>{if(event.event?.key==='Enter'){open(event);emit('cell-open',event)}}" /></div>
   <div class="lotus-mobile-records"><component :is="interactive?UiButton:'article'" v-for="(row,index) in rows" :key="row.name||index" class="lotus-mobile-record" variant="ghost" @click="interactive&&emit('open',row)"><strong>{{value(row,columns[0])}}</strong><span v-for="col in columns.slice(1)" :key="col.field||col.headerName" class="lotus-mobile-record-detail"><span>{{col.headerName}}</span><UiButton v-if="col.colId" variant="link" size="sm" @click.stop="emit('cell-open',{data:row,colDef:col})">{{value(row,col)}}</UiButton><span v-else>{{value(row,col)}}</span></span></component></div>
  </template>
 </div>
</template>
