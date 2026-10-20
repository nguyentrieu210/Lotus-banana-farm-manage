<script setup>
import {computed,ref,onMounted,onBeforeUnmount,watch,nextTick} from 'vue'
import {useRouter} from 'vue-router'
import {useWorkJournal,journalCall} from './use-work-journal'
import {blankJournalRow,cloneJournalRow,rowErrors} from './journal-model.js'
import {useWorkspaceConfirm} from './use-workspace-confirm'
import {useMobileConfirm} from './use-mobile-confirm'
import WorkspaceConfirm from './components/WorkspaceConfirm.vue'
import WorkspaceModal from './components/WorkspaceModal.vue'
import LotusMobileDialog from './components/LotusMobileDialog.vue'
import DataTable from './components/DataTable.vue'
import SearchSelect from './components/SearchSelect.vue'
import MobileLinkField from './components/MobileLinkField.vue'
import LotusMobileInput from './components/LotusMobileInput.vue'
import LotusMobileButton from './components/LotusMobileButton.vue'
import JournalField from './components/JournalField.vue'
import {Button} from './components/ui/button'
import {Input} from './components/ui/input'
import {Textarea} from './components/ui/textarea'
import {DatePicker} from './components/ui/date-picker'
import {unitLabel} from './units'
import {label as fieldLabel} from './labels'
const props=defineProps({embedded:Boolean,mobile:Boolean})
const router=props.embedded?useRouter():null
const j=useWorkJournal()
const {session,farm,date,catalog,record,rows,busy,saving,error,notice,attempt,search,mode,from,to,filters,report,correction,dirty,canWrite,duplicates,visible}=j
const desktopConfirm=useWorkspaceConfirm(),mobileConfirm=useMobileConfirm()
const mobileConfirmDialog=mobileConfirm.dialog
const ask=(text,title)=>props.mobile?mobileConfirm.ask(text):desktopConfirm.ask(text,title)
const editor=ref(null),historyDialog=ref(null),selected=ref(null),original=ref(null),newRow=ref(false),errors=ref({}),historyRows=ref([])
const Btn=computed(()=>props.mobile?LotusMobileButton:Button),Text=computed(()=>props.mobile?LotusMobileInput:Input),Picker=computed(()=>props.mobile?MobileLinkField:SearchSelect),Modal=computed(()=>props.mobile?LotusMobileDialog:WorkspaceModal)
const locked=computed(()=>busy.value||saving.value||!!attempt.value)
const options=(kind,label,code,current)=>catalog.value[kind].filter(r=>r.active||r.name===current).map(r=>({value:r.name,label:[r[code],r[label]].filter((v,i,a)=>v&&a.indexOf(v)===i).join(' · ')||r.name}))
const farms=computed(()=>(session.value?.farms||[]).map(f=>({value:f.name,label:f.farm_name||f.name})))
const columns=[{field:'team_label',headerName:'Tổ/đội'},{field:'block_label',headerName:'Lô lớn'},{field:'work_label',headerName:'Công việc',minWidth:180},{field:'uom',headerName:'ĐVT',valueFormatter:p=>unitLabel(p.value)||p.value},{field:'quantity',headerName:'Số lượng'},{field:'workdays',headerName:'Tổng công'},{field:'notes',headerName:'Ghi chú',minWidth:180}]
const exportURL=computed(()=>'/api/method/lotus_farm.work_journal.export?'+new URLSearchParams({farm:farm.value,from_date:mode.value==='day'?date.value:from.value,to_date:mode.value==='day'?date.value:to.value,...(mode.value==='summary'?filters.value:{})}))
function syncURL(){if(props.embedded&&router){const query={...router.currentRoute.value.query,farm:farm.value,date:date.value};router.replace({path:'/nhat-ky-cong-viec',query})}else if(props.mobile){const url=new URL(location.href);url.searchParams.set('farm',farm.value);url.searchParams.set('date',date.value);window.history.replaceState(window.history.state,'',url.pathname+url.search)}}
async function changeScope(nextFarm=farm.value,nextDate=date.value){if(locked.value)return;if(dirty.value&&!await ask('Có thay đổi chưa lưu. Rời phạm vi này? Bản nháp vẫn được giữ trên thiết bị.','Đổi nhật ký'))return;j.persist();farm.value=nextFarm;date.value=nextDate;await j.load();syncURL();if(mode.value==='summary')await j.summary()}
async function switchMode(next){if(locked.value)return;mode.value=next;if(next==='summary'){from.value||=date.value;to.value||=date.value;await j.summary()}}
async function refresh(){if(dirty.value&&!await ask('Tải lại dữ liệu máy chủ và bỏ bản nháp đang nhập?','Tải lại nhật ký'))return;j.discard();await j.load();if(mode.value==='summary')await j.summary()}
async function edit(row){if(mode.value!=='day')return;errors.value={};newRow.value=!row;const actual=row?rows.value.find(r=>r.row_id===row.row_id):blankJournalRow();if(!row)rows.value.push(actual);selected.value=actual;original.value=JSON.parse(JSON.stringify(actual));await nextTick();editor.value.showModal()}
function closeEditor(cancel=false){if(cancel&&canWrite.value&&original.value){if(newRow.value)rows.value=rows.value.filter(r=>r.row_id!==selected.value.row_id);else Object.assign(selected.value,original.value)}editor.value.close();selected.value=null;original.value=null}
function acceptRow(){errors.value=rowErrors(selected.value);if(Object.keys(errors.value).length)return;closeEditor()}
async function removeRow(){if(await ask('Xóa dòng này khỏi bản đang nhập? Sau khi lưu, thay đổi vẫn có trong lịch sử.','Xóa dòng')){rows.value=rows.value.filter(r=>r.row_id!==selected.value.row_id);closeEditor()}}
function duplicate(){const copy=cloneJournalRow(selected.value);rows.value.push(copy);closeEditor()}
async function save(){for(let i=0;i<rows.value.length;i++){if(Object.keys(rowErrors(rows.value[i])).length){error.value='Dòng '+(i+1)+': '+Object.values(rowErrors(rows.value[i]))[0];return}}await j.save()}
async function showHistory(){try{historyRows.value=await journalCall('history',{farm:farm.value,date:date.value});await nextTick();historyDialog.value.showModal()}catch(e){error.value=e.message}}
function workChanged(){selected.value.uom=catalog.value.works.find(w=>w.name===selected.value.work_type)?.uom||''}
function historyLines(entry){const change=c=>fieldLabel(c[0],({has_quantity:'Có số lượng',has_workdays:'Có số công',quantity:'Số lượng',workdays:'Tổng công',notes:'Ghi chú',correction_reason:'Lý do sửa thay'})[c[0]])+': '+String(c[1]??'Trống')+' → '+String(c[2]??'Trống');const data=entry.changes;return [...(data.changed||[]).map(change),...(data.added||[]).map(()=> 'Thêm dòng công việc'),...(data.removed||[]).map(()=> 'Xóa dòng công việc'),...(data.row_changed||[]).flatMap(row=>(row[3]||[]).map(c=>'Sửa dòng '+(Number(row[1])+1)+' · '+change(c)))]}
let removeGuard
onMounted(async()=>{const query=Object.fromEntries(new URLSearchParams(location.search));await j.init(query);if(props.embedded&&router){removeGuard=router.beforeEach(async(to,old)=>{if(old.path!=='/nhat-ky-cong-viec'||(to.path===old.path&&to.query.farm===old.query.farm&&to.query.date===old.query.date))return true;if(saving.value)return false;return !dirty.value||await ask('Có thay đổi chưa lưu. Rời màn hình? Bản nháp vẫn được giữ trên thiết bị.','Rời nhật ký')})}syncURL()})
onBeforeUnmount(()=>removeGuard?.())
if(router)watch(()=>router.currentRoute.value.fullPath,async()=>{const route=router.currentRoute.value;if(route.path!=='/nhat-ky-cong-viec')return;const f=String(route.query.farm||farm.value),d=String(route.query.date||date.value);if(f!==farm.value||d!==date.value){j.persist();farm.value=f;date.value=d;await j.load()}})
defineExpose({isDirty:()=>dirty.value,confirmLeave:()=>!dirty.value||ask('Nhật ký chưa lưu. Bản nháp được giữ trên thiết bị. Rời màn hình?'),persist:j.persist})
</script>
<template>
 <section class="work-journal" :class="{'work-journal--mobile':mobile}" aria-label="Nhật ký công việc">
  <div class="journal-toolbar">
   <component :is="Picker" :model-value="farm" :options="farms" label="Vườn" :searchable="false" :disabled="locked" @update:model-value="changeScope($event,date)"/>
   <LotusMobileInput v-if="mobile" label="Ngày" type="date" :model-value="date" :max="session?.today" :disabled="locked" @update:model-value="changeScope(farm,$event)"/>
   <DatePicker v-else label="Ngày" :model-value="date" :max="session?.today" :disabled="locked" @update:model-value="changeScope(farm,$event)"/>
   <component :is="Btn" :disabled="locked" @click="refresh">Làm mới</component>
   <component :is="Text" v-model="search" aria-label="Tìm nhật ký" placeholder="Tìm tổ, lô, công việc…" type="search"/>
   <component :is="Btn" :disabled="locked" @click="switchMode(mode==='day'?'summary':'day')">{{mode==='day'?'Tổng hợp':'Theo ngày'}}</component>
   <template v-if="mode==='day'&&canWrite"><component :is="Btn" :disabled="locked" @click="edit()">Thêm dòng</component><component :is="Btn" :disabled="busy||saving||!dirty" @click="save">{{saving?'Đang lưu…':attempt?'Thử lưu lại':'Lưu nhật ký'}}</component></template>
  </div>
  <p v-if="error" role="alert" class="error">{{error}}</p><p v-if="notice" role="status">{{notice}}</p>
  <p v-if="attempt" class="notice">Chưa xác nhận được kết quả lưu. Giữ nguyên nội dung và thử lưu lại hoặc tải lại để đối chiếu.</p>
  <p v-if="duplicates.length" class="notice">Có dòng trùng tổ, lô và công việc. Kiểm tra trước khi lưu; hệ thống không tự gộp.</p>
  <div v-if="mode==='summary'" class="journal-toolbar">
   <LotusMobileInput v-if="mobile" v-model="from" label="Từ ngày" type="date"/><DatePicker v-else v-model="from" label="Từ ngày"/>
   <LotusMobileInput v-if="mobile" v-model="to" label="Đến ngày" type="date"/><DatePicker v-else v-model="to" label="Đến ngày"/>
   <component v-for="[key,kind,label,code,title] in [['work_team','teams','team_name','team_code','Tổ/đội'],['farm_block','blocks','block_code','block_code','Lô lớn'],['work_type','works','work_name','work_code','Công việc']]" :is="Picker" :key="key" v-model="filters[key]" :options="[{value:'',label:'Tất cả'},...options(kind,label,code)]" :label="title"/>
   <component :is="Btn" :disabled="busy" @click="j.summary">Tra cứu</component>
  </div>
  <div class="journal-meta"><small v-if="mode==='day'&&record?.modified">Cập nhật: {{record.modified_by}} · {{record.modified}}</small><small v-if="dirty">Bản đang nhập chưa lưu trên hệ thống.</small><a v-if="farm" :href="exportURL">Xuất Excel</a><component v-if="mode==='day'&&record?.name" :is="Btn" @click="showHistory">Lịch sử thay đổi</component></div>
  <JournalField v-if="mode==='day'&&canWrite&&record?.owner&&record.owner!==session?.user" :mobile="mobile" label="Lý do sửa thay người lập" required v-slot="f"><component :is="Text" v-bind="f" v-model="correction" maxlength="500"/></JournalField>
  <DataTable v-if="!mobile" :rows="visible" :columns="mode==='day'?columns:[{field:'date',headerName:'Ngày'},...columns]" :loading="busy" :interactive="mode==='day'" storage-key="work-journal" empty="Chưa có dòng nhật ký trong phạm vi này." @open="edit"/>
  <div v-else class="journal-cards"><p v-if="!visible.length">Chưa có dòng nhật ký.</p><article v-for="row in visible" :key="row.row_id+(row.date||'')" class="mobile-list-card"><strong>{{row.work_label}}</strong><p>{{row.team_label}} · Lô {{row.block_label}}{{row.date?' · '+row.date:''}}</p><p>Số lượng: {{row.quantity??'Chưa có'}} {{unitLabel(row.uom)||row.uom}} · Công: {{row.workdays??'Chưa có'}}</p><p v-if="row.notes">{{row.notes}}</p><LotusMobileButton v-if="mode==='day'" :disabled="locked" @click="edit(row)">{{canWrite?'Xem / sửa':'Xem chi tiết'}}</LotusMobileButton></article></div>
  <section v-if="mode==='summary'" aria-label="Tổng hợp nhật ký theo dõi"><p>Tổng công nhật ký theo dõi: <strong>{{report.total_workdays}}</strong></p><p v-for="group in report.groups" :key="group.work_type+'|'+group.uom">{{catalog.works.find(w=>w.name===group.work_type)?.work_name||group.work_type}}: {{group.quantity??'Chưa có'}} {{unitLabel(group.uom)||group.uom}} · {{group.workdays??'Chưa có'}} công</p></section>
  <component :is="Modal" ref="editor" title="Dòng nhật ký" :busy="saving" bare @cancel="closeEditor(true)">
   <h2>{{canWrite?'Dòng nhật ký':'Chi tiết nhật ký'}}</h2>
   <form v-if="selected" @submit.prevent="acceptRow"><fieldset :disabled="!canWrite||locked" class="journal-form">
    <JournalField v-for="[key,kind,label,code,title] in [['work_team','teams','team_name','team_code','Tổ/đội'],['farm_block','blocks','block_code','block_code','Lô lớn'],['work_type','works','work_name','work_code','Công việc']]" :key="key" :mobile="mobile" :label="title" required :error="errors[key]" v-slot="f"><component :is="Picker" v-bind="f" v-model="selected[key]" :label="title" :options="options(kind,label,code,selected[key])" :searchable="true" @update:model-value="key==='work_type'&&workChanged()"/></JournalField>
    <p>Đơn vị tính: {{unitLabel(selected.uom)||selected.uom||'Chọn công việc'}}</p>
    <JournalField v-for="[key,title] in [['quantity','Số lượng thực hiện'],['workdays','Tổng công']]" :key="key" :mobile="mobile" :label="title" :error="errors[key]" v-slot="f"><component :is="Text" v-bind="f" v-model="selected[key]" :aria-label="title" type="number" inputmode="decimal" min="0" step="any"/></JournalField>
    <JournalField :mobile="mobile" label="Ghi chú" :error="errors.notes" v-slot="f"><component :is="mobile?LotusMobileInput:Textarea" v-bind="f" v-model="selected.notes" type="textarea" maxlength="500" rows="2"/></JournalField>
   </fieldset><div class="journal-actions"><component :is="Btn" type="button" @click="closeEditor(true)">{{canWrite?'Hủy':'Đóng'}}</component><template v-if="canWrite"><component :is="Btn" type="button" :disabled="locked" @click="removeRow">Xóa dòng</component><component :is="Btn" type="button" :disabled="locked" @click="duplicate">Nhân bản</component><component :is="Btn" type="submit" :disabled="locked">Giữ dòng</component></template></div></form>
  </component>
  <component :is="Modal" ref="historyDialog" title="Lịch sử thay đổi nhật ký" bare><h2>Lịch sử thay đổi nhật ký</h2><p v-if="!historyRows.length">Chưa có lần sửa sau khi tạo.</p><article v-for="(entry,i) in historyRows" :key="i"><strong>{{entry.user}} · {{entry.at}}</strong><p v-for="(line,k) in historyLines(entry)" :key="k">{{line}}</p></article><component :is="Btn" @click="historyDialog.close()">Đóng</component></component>
  <WorkspaceConfirm v-if="!mobile" :open="desktopConfirm.open.value" :title="desktopConfirm.title.value" :message="desktopConfirm.message.value" :alert-only="desktopConfirm.alertOnly.value" @answer="desktopConfirm.finish"/>
  <LotusMobileDialog v-else ref="mobileConfirmDialog" @cancel="mobileConfirm.finish(false)"><h2>Xác nhận</h2><p>{{mobileConfirm.message.value}}</p><LotusMobileButton @click="mobileConfirm.finish(false)">Ở lại</LotusMobileButton><LotusMobileButton @click="mobileConfirm.finish(true)">Đồng ý</LotusMobileButton></LotusMobileDialog>
 </section>
</template>
<style>
.work-journal{padding:var(--lotus-space-3);min-width:0}.journal-toolbar{display:flex;align-items:center;gap:var(--lotus-space-2);overflow-x:auto;white-space:nowrap;margin-bottom:var(--lotus-space-3)}.journal-toolbar>*{flex-shrink:0}.journal-toolbar .search-select{min-width:var(--lotus-control-width,180px)}.journal-meta,.journal-actions{display:flex;align-items:center;gap:var(--lotus-space-3);flex-wrap:wrap;margin:var(--lotus-space-2) 0}.journal-form{display:grid;gap:var(--lotus-space-3);border:0;padding:0;min-width:0}.journal-history{white-space:pre-wrap;overflow-wrap:anywhere;font-size:var(--lotus-text-xs)}.work-journal--mobile{padding:0}.work-journal--mobile .journal-toolbar{white-space:normal;flex-wrap:wrap;overflow:visible}.work-journal--mobile .journal-toolbar>*{max-width:100%;min-width:0;flex:1 1 45%}.work-journal--mobile .journal-form{max-height:65vh;overflow:auto}.journal-cards{display:grid;gap:var(--lotus-space-2)}.journal-cards article{overflow-wrap:anywhere}
</style>
