import {ref,computed,watch,onBeforeUnmount} from 'vue'
import {call,setCSRF} from './api'
import {draftKey,duplicateRows,labelledRows,fold} from './journal-model.js'
export const journalCall=(name,args={},write=false)=>call('lotus_farm.work_journal.'+name,args,write)
export function useWorkJournal(){
 const session=ref(null),farm=ref(''),date=ref(''),catalog=ref({teams:[],blocks:[],works:[]}),record=ref(null),rows=ref([]),baseline=ref('[]'),busy=ref(false),saving=ref(false),error=ref(''),notice=ref(''),attempt=ref(null),search=ref(''),mode=ref('day'),from=ref(''),to=ref(''),filters=ref({work_team:'',farm_block:'',work_type:''}),report=ref({rows:[],groups:[],total_workdays:0}),correction=ref('')
 let version=0,loading=false
 const dirty=computed(()=>JSON.stringify(rows.value)!==baseline.value||!!attempt.value)
 const canWrite=computed(()=>!!record.value?.can_write)
 const duplicates=computed(()=>duplicateRows(rows.value))
 const visible=computed(()=>labelledRows(mode.value==='day'?rows.value:report.value.rows,catalog.value).filter(r=>!search.value||fold([r.team_label,r.block_label,r.work_label,r.notes].join(' ')).includes(fold(search.value))))
 const storage=()=>draftKey(session.value?.user,farm.value,date.value)
 function persist(){if(!session.value?.user||!farm.value||loading)return;try{if(dirty.value)localStorage.setItem(storage(),JSON.stringify({rows:rows.value,expected_modified:record.value?.modified??null,attempt:attempt.value,correction:correction.value}));else localStorage.removeItem(storage())}catch{error.value='Không lưu được bản nháp trên thiết bị. Giữ màn hình này và lưu khi có mạng.'}}
 watch([rows,attempt,correction],persist,{deep:true,flush:'sync'})
 async function load(){const id=++version;if(!farm.value||!date.value)return;busy.value=true;error.value='';loading=true
  try{const [c,data]=await Promise.all([journalCall('catalogue',{farm:farm.value}),journalCall('get',{farm:farm.value,date:date.value})]);if(id!==version)return;catalog.value=c;record.value=data;baseline.value=JSON.stringify(data.rows);rows.value=JSON.parse(JSON.stringify(data.rows));attempt.value=null;correction.value='';const stored=JSON.parse(localStorage.getItem(storage())||'null');if(stored&&data.can_write){rows.value=stored.rows;record.value={...data,modified:stored.expected_modified};attempt.value=stored.attempt;correction.value=stored.correction||'';notice.value='Đã khôi phục bản nháp trên thiết bị; chưa lưu lên hệ thống.'}}
  catch(e){if(id===version){record.value=null;rows.value=[];error.value=e.message}}
  finally{if(id===version){loading=false;busy.value=false}}
 }
 async function init(query={}){busy.value=true;try{session.value=await journalCall('bootstrap');setCSRF(session.value.csrf_token);farm.value=session.value.farms.some(f=>f.name===query.farm)?query.farm:session.value.farms[0]?.name||'';date.value=query.date||session.value.today;from.value=to.value=date.value;if(!farm.value)throw Error('Tài khoản chưa được cấp quyền vườn.');await load()}catch(e){error.value=e.message}finally{busy.value=false}}
 async function save(){if(saving.value||!canWrite.value)return;saving.value=true;error.value='';notice.value=''
  try{if(!attempt.value)attempt.value={farm:farm.value,date:date.value,rows:JSON.parse(JSON.stringify(rows.value)),expected_modified:record.value?.modified??null,request_id:crypto.randomUUID(),correction_reason:correction.value,expected_user:session.value.user};const saved=await journalCall('save',attempt.value,true);loading=true;record.value=saved;rows.value=JSON.parse(JSON.stringify(saved.rows));baseline.value=JSON.stringify(saved.rows);attempt.value=null;correction.value='';localStorage.removeItem(storage());notice.value='Đã lưu nhật ký theo dõi.'}
  catch(e){if(e.status&&e.status<500){attempt.value=null}error.value=e.message}
  finally{loading=false;saving.value=false;persist()}
 }
 async function summary(){if(!farm.value)return;busy.value=true;error.value='';try{report.value=await journalCall('summary',{farm:farm.value,from_date:from.value,to_date:to.value,...filters.value})}catch(e){error.value=e.message}finally{busy.value=false}}
 function discard(){loading=true;rows.value=JSON.parse(JSON.stringify(record.value?.rows||[]));baseline.value=JSON.stringify(rows.value);attempt.value=null;localStorage.removeItem(storage());loading=false}
 function unload(event){if(dirty.value){persist();event.preventDefault();event.returnValue=''}}
 window.addEventListener('beforeunload',unload);onBeforeUnmount(()=>{persist();window.removeEventListener('beforeunload',unload)})
 return {session,farm,date,catalog,record,rows,busy,saving,error,notice,attempt,search,mode,from,to,filters,report,correction,dirty,canWrite,duplicates,visible,load,init,save,summary,discard,persist}
}
