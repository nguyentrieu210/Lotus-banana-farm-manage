<script setup>
import {computed} from 'vue'
import SchemaForm from './SchemaForm.vue'
import {kg,forecastStates} from '../forecast-planning'
const props=defineProps({schema:Object,model:Object,scope:Object,readonly:Boolean})
const oneDrive=computed(()=>!!props.model?.process_adoption||!!props.model?.source_claims?.length)
const legacyFields=new Set(['harvest_profile','item','packout_profile'])
const machineFields=new Set(['forecast_basis','source_bunch_qty','avg_bunch_weight_kg','bunch_survival_rate_percent','quality_pass_rate_percent','packout_rate_percent'])
const groups=[
  {title:'Phạm vi và thời gian',fields:['farm','farm_block','crop_cycle','sucker_selection_batch','planning_granularity','period_start_date','period_end_date','forecast_basis']},
  {title:'Cơ sở tính sản lượng',fields:['harvest_profile','source_bunch_qty','avg_bunch_weight_kg','bunch_survival_rate_percent','quality_pass_rate_percent','packout_rate_percent','safety_buffer_percent','confidence']},
  {title:'Sản phẩm dự kiến',fields:['item','packout_profile','output_plan']},
  {title:'Nguồn OneDrive đã đối chiếu',fields:['process_adoption','source_claims']},
  {title:'Điều chỉnh và ghi chú',fields:['supersedes','revision_reason','notes']},
]
const displayName=(field,child=false)=>field.fieldname==='item'?(child?'Sản phẩm':'Sản phẩm dự kiến'):field.fieldname==='quality_standard'?'Tiêu chuẩn chất lượng':null
const tables=computed(()=>Object.fromEntries(Object.entries(props.schema?.tables||{}).map(([table,fields])=>[table,fields.filter(f=>oneDrive.value||f.fieldname!=='source_share_percent').map(f=>({...f,display_label:displayName(f,true)}))])))
const grouping=name=>({fields:(props.schema?.fields||[]).filter(f=>groups.find(g=>g.title===name)?.fields.includes(f.fieldname)&&(!oneDrive.value||!legacyFields.has(f.fieldname))).map(f=>({...f,read_only:oneDrive.value&&machineFields.has(f.fieldname)?1:f.read_only,display_label:displayName(f)})),tables:tables.value})
const validGroups=computed(()=>groups.filter(g=>grouping(g.title).fields.length&&(g.title!=='Nguồn OneDrive đã đối chiếu'||props.model.process_adoption||props.model.source_claims?.length)))
</script>
<template>
  <div class="forecast-form">
    <p v-if="model.supersedes" class="forecast-revision">Bản điều chỉnh của {{model.supersedes}}. Bắt buộc ghi lý do trước khi phát hành; bản cũ chỉ được thay thế khi không còn hàng đã giữ hoặc đã thu.</p>
    <section v-for="group in validGroups" :key="group.title"><h3>{{group.title}}</h3>
      <p v-if="group.title==='Cơ sở tính sản lượng'" class="forecast-footnote">{{oneDrive?'Số buồng, trọng lượng và tỷ lệ được tính từ nguồn cắt bắp cùng phiên bản OneDrive đã duyệt.':'Nếu chọn nguồn ngoài \'Nhập tay\', hệ thống sẽ tự lấy số buồng từ công việc thực tế. Các tỷ lệ và kết quả chính thức được máy chủ tính khi lưu.'}}</p>
      <p v-if="group.title==='Sản phẩm dự kiến'" class="forecast-footnote">{{oneDrive?'Phân bổ tỷ phần kg sơ chế OneDrive cho từng sản phẩm; không nhân lại tỷ lệ sơ chế hoặc đóng gói.':'Chỉ chọn một cách: 1 sản phẩm và mẫu đóng gói, hoặc nhập nhiều dòng thành phẩm. Không dùng đồng thời cả hai.'}}</p>
      <SchemaForm :schema="grouping(group.title)" :model="model" :scope="scope" :readonly="readonly||group.title==='Nguồn OneDrive đã đối chiếu'"/>
    </section>
    <section><h3>Kết quả tính trên máy chủ</h3>
      <div class="forecast-metrics">
        <div class="forecast-metric"><span>Buồng dự kiến thu</span><strong>{{kg(model.expected_harvest_bunch_qty)}}</strong></div>
        <div class="forecast-metric"><span>Kg buồng</span><strong>{{kg(model.gross_forecast_kg)}}</strong></div>
        <div class="forecast-metric"><span>Kg đóng gói</span><strong>{{kg(model.packed_forecast_kg)}}</strong></div>
        <div class="forecast-metric"><span>Kg có thể giữ</span><strong>{{kg(model.available_to_promise_kg)}}</strong></div>
        <div class="forecast-metric"><span>Trạng thái</span><strong>{{forecastStates[model.supply_state]||'Bản nháp'}}</strong></div>
      </div>
      <p class="forecast-footnote">Đây là số của lần lưu gần nhất, không tự cập nhật khi đang gõ. Lưu phiếu để máy chủ tính lại.</p>
    </section>
  </div>
</template>
