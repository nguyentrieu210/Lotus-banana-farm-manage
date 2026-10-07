'use strict';
const $=id=>document.getElementById(id);
const state={session:null,data:null,summary:null,user:localStorage.getItem('lotus-active-user'),task:null};
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=value=>value==null?'—':Number(value).toLocaleString('vi-VN',{maximumFractionDigits:2});
const link=(type,name)=>`<a href="/app/${type.toLowerCase().replaceAll(' ','-')}/${encodeURIComponent(name)}">${esc(name)}</a>`;
const table=(columns,rows)=>`<div class="scroll"><table><thead><tr>${columns.map(c=>`<th>${esc(c[0])}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${columns.map(c=>`<td>${c[2]?c[2](row):esc(row[c[1]]??'—')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
function notice(message){$('notice').textContent=message;}
function today(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function failure(data){try{return JSON.parse(data._server_messages).map(m=>JSON.parse(m).message.replace(/<[^>]*>/g,'')).join('; ');}catch{return data.message||data.exc_type||'Không gửi được. Bản ghi vẫn được giữ trên máy.';}}
async function api(method,args={},write=false){
 const options={credentials:'same-origin',headers:{'Accept':'application/json'}};
 let url='/api/method/'+method;
 if(write){options.method='POST';options.headers['Content-Type']='application/json';options.headers['X-Frappe-CSRF-Token']=state.session?.csrf_token||'';options.body=JSON.stringify(args);}
 else url+='?'+new URLSearchParams(Object.fromEntries(Object.entries(args).filter(([,v])=>v!==null&&v!==undefined)));
 const response=await fetch(url,options);const result=await response.json();
 if(!response.ok||result.exc||result.exc_type)throw new Error(failure(result));
 return result.message;
}
const dbReady=new Promise((resolve,reject)=>{const request=indexedDB.open('lotus-field-v1',1);request.onupgradeneeded=()=>{request.result.createObjectStore('queue',{keyPath:'key'});request.result.createObjectStore('cache',{keyPath:'key'});};request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});
async function db(store,action,value){const database=await dbReady;return new Promise((resolve,reject)=>{const tx=database.transaction(store,action==='getAll'||action==='get'?'readonly':'readwrite');const request=tx.objectStore(store)[action](value);let result;request.onsuccess=()=>{result=request.result;};tx.oncomplete=()=>resolve(result);tx.onerror=()=>reject(tx.error);});}
const cacheKey=()=>`${state.user}|${$('farm').value}|${$('date').value}`;
async function session(){
 const result=await api('lotus_farm.field.session_info');state.session=result;state.user=result.user;localStorage.setItem('lotus-active-user',result.user);
 await db('cache','put',{key:'session|'+result.user,user:result.user,farms:result.farms,capabilities:result.capabilities});
 applyCapabilities(result.capabilities);
 $('user').textContent=result.user;$('farm').innerHTML=result.farms.map(f=>`<option value="${esc(f.name)}">${esc(f.farm_name)} · ${esc(f.name)}</option>`).join('');
 $('connection').textContent='Đã kết nối';return result;
}
async function openDay(){
 const farm=$('farm').value,date=$('date').value;if(!farm)return;
 notice('Đang đọc số liệu…');
 try{
  const caps=state.session?.capabilities||state.capabilities||{field:true,home:true,packhouse:true,map:true,imports:true};
  state.data=caps.field||caps.home?await api('lotus_farm.field.bootstrap',{farm,posting_date:date}):{user:state.user,tasks:[],labor:[],cancellations:[],reasons:[],diseases:[],cycles:[],cohorts:[],geometries:[]};
  if(caps.packhouse)state.packhouse=await api('lotus_farm.reporting.packhouse_day',{farm,posting_date:date});
  if(caps.map&&!caps.field&&!caps.home)state.data.geometries=(await api('lotus_farm.field.map_data',{farm})).features;
  if(state.data.user!==state.user)throw new Error('Tài khoản đã thay đổi; mở lại màn hình trước khi nhập.');
  state.summary=caps.home?await api('lotus_farm.reporting.dashboard',{farm,from_date:date,to_date:date}):{farms:[],forecast:[]};
  await db('cache','put',{key:cacheKey(),data:state.data,summary:state.summary,packhouse:state.packhouse});notice('Số liệu đã cập nhật.');
 }catch(error){const cached=await db('cache','get',cacheKey());if(!cached){notice(error.message);return;}state.data=cached.data;state.summary=cached.summary;state.packhouse=cached.packhouse;notice('Đang dùng bản lưu trên máy. Số liệu có thể đã thay đổi; bản ghi sẽ được kiểm tra lại khi gửi.');}
 render();await renderQueue();
}
function render(){
 const farm=state.summary?.farms[0]||{};
 $('kpis').innerHTML=[['Việc đã làm',farm.work_completion_percent,'%'],['Thiếu / thừa công',farm.labor_gap_workdays,''],['Thu hoạch',farm.harvest_kg,'kg'],['Ra thành phẩm',farm.packout_percent,'%']].map(([label,value,unit])=>`<div class="card"><span>${label}</span><strong>${fmt(value)} <small>${unit}</small></strong></div>`).join('');
 $('tasks').innerHTML=table([['Thửa','farm_plot'],['Việc','work_type',r=>esc(r.work_name||r.work_type)],['Kế hoạch','planned_qty',r=>`${fmt(r.planned_qty)} ${esc(r.uom)}`],['Đã làm','completed_qty',r=>fmt(r.completed_qty)],['Công cần / bố trí','required_workdays',r=>`${fmt(r.required_workdays)} / ${fmt(r.allocated_workdays)}`]],state.data.tasks);
 $('forecast').innerHTML=table([['Kỳ','period_start_date'],['Item','item'],['Dự thu kg','packed_forecast_kg',r=>fmt(r.packed_forecast_kg)],['Đã giữ','committed_qty_kg',r=>fmt(r.committed_qty_kg)],['Còn có thể bán','available_to_promise_kg',r=>fmt(r.available_to_promise_kg)]],state.summary?.forecast||[]);
 $('losses').innerHTML=table([['Thửa','farm_plot'],['Nguyên nhân','reason'],['Buồng hủy','bunch_qty',r=>fmt(r.bunch_qty)],['Phiếu','name',r=>link('Bunch Cancellation',r.name)]],state.data.cancellations);
 $('materials').innerHTML=table([['Nhu cầu chưa ghi dùng','item'],['Số lượng','outstanding_qty',r=>`${fmt(r.outstanding_qty)} ${esc(r.uom)}`],['Phiếu','requirement',r=>link('Material Requirement',r.requirement)]],farm.outstanding_material||[]);
 $('fieldtasks').innerHTML=table([['Thửa','farm_plot'],['Việc','work_type',r=>esc(r.work_name||r.work_type)],['Kế hoạch','planned_qty',r=>`${fmt(r.planned_qty)} ${esc(r.uom)}`],['Kết quả','result',r=>r.result?link('Daily Work Result',r.result):`<button data-task="${esc(r.line)}">Ghi kết quả</button>`]],state.data.tasks);
 document.querySelectorAll('[data-task]').forEach(b=>b.onclick=()=>{state.task=state.data.tasks.find(t=>t.line===b.dataset.task);$('tasktitle').textContent=(state.task.work_name||state.task.work_type)+' · '+(state.task.plot_code||state.task.farm_plot);$('doneqty').value=state.task.planned_qty;$('days').value='';$('unfinished').value='';$('resultdialog').showModal();});
 $('cycle').innerHTML=state.data.cycles.map(c=>`<option value="${esc(c.name)}">${esc(c.farm_plot)} · ${esc(c.name)}</option>`).join('');updateCohorts();updateEvent();renderMap();renderPackhouse();
}

function applyCapabilities(caps){
 state.capabilities=caps||{field:true,home:true,packhouse:true,map:true,imports:true,qc:true};
 const available=[];
 for(const button of document.querySelectorAll('[data-tab]')){const allowed=state.capabilities[button.dataset.tab==='import'?'imports':button.dataset.tab];button.hidden=!allowed;if(allowed)available.push(button);}
 if(available.length)available[0].click();
 $('quickqc').hidden=!state.capabilities.qc;
}
function renderPackhouse(){
 const data=state.packhouse||{lots:[],runs:[],defects:[]};
 $('receivinglots').innerHTML=table([['Lô thu','name',r=>link('Harvest Lot',r.name)],['Ngày nhận','received_date'],['Kg đầu vào','released_raw_kg',r=>fmt(r.released_raw_kg)],['Kiểm chất lượng','qc',r=>r.qc?link('Incoming Quality Inspection',r.qc):'Chưa kiểm'],['Kg còn đóng gói','remaining_to_pack_kg',r=>fmt(r.remaining_to_pack_kg)]],data.lots||[]);
 $('packingruns').innerHTML=table([['Ca đóng gói','name',r=>link('Packout Run',r.name)],['Kg vào','input_kg',r=>fmt(r.input_kg)],['Kg ra','output_kg',r=>fmt(r.output_kg)],['Lệch kg','mass_variance_kg',r=>fmt(r.mass_variance_kg)],['Kho','stock_entry',r=>r.stock_entry?link('Stock Entry',r.stock_entry):'Chưa ghi kho']],data.runs||[]);
 $('qclot').innerHTML=(data.lots||[]).filter(l=>!l.qc).map(l=>`<option value="${esc(l.name)}">${esc(l.name)} · ${fmt(l.released_raw_kg)} kg</option>`).join('');
 $('qcdefect').innerHTML='<option value="">Không loại đầu vào</option>'+(data.defects||[]).map(d=>`<option value="${esc(d.name)}">${esc(d.defect_name)}</option>`).join('');
 const lot=(data.lots||[]).find(l=>l.name===$('qclot').value);$('qcaccepted').value=lot?.released_raw_kg??'';
}

function updateCohorts(){const cycle=$('cycle').value;$('cohort').innerHTML='<option value="">Không có đợt chồi</option>'+state.data.cohorts.filter(c=>c.crop_cycle===cycle).map(c=>`<option value="${esc(c.name)}">${esc(c.name)}</option>`).join('');}
function updateEvent(){
 const type=$('eventtype').value;
 $('reasonlabel').hidden=!['Bunch Cancellation','Disease Observation'].includes(type);
 $('expectedlabel').hidden=type!=='Bunch Cancellation';$('expected').required=type==='Bunch Cancellation';
 $('weightlabel').hidden=!['Harvest Actual','Fruit Measurement','Planting Event'].includes(type);
 $('secondlabel').hidden=!['Bunch Operation','Fruit Measurement','Planting Event','Harvest Actual','Disease Observation'].includes(type);
 const old=$('second');let replacement=document.createElement(type==='Fruit Measurement'||type==='Harvest Actual'?'input':'select');replacement.id='second';old.replaceWith(replacement);
 if(replacement.tagName==='INPUT'){replacement.type='number';replacement.min='0';replacement.step='any';}
 const choices={ 'Bunch Operation':[['Bag','Bao buồng'],['Cut Bud','Cắt bắp'],['Shooting','Trổ buồng'],['Spray','Phun buồng'],['Care','Chăm sóc'],['Inspection','Kiểm tra']], 'Planting Event':[['Planting','Trồng mới'],['Replanting','Trồng dặm']], 'Disease Observation':[['Low','Nhẹ'],['Medium','Vừa'],['High','Nặng']] };
 if(choices[type])replacement.innerHTML=choices[type].map(([v,l])=>`<option value="${v}">${l}</option>`).join('');
 $('secondlabel').firstChild.textContent=({'Fruit Measurement':'Đường kính trung bình (cm)','Harvest Actual':'Khối lượng loại ngoài vườn (kg)','Planting Event':'Loại trồng','Bunch Operation':'Công việc','Disease Observation':'Mức độ'})[type]||'';
 $('weightlabel').firstChild.textContent=({'Harvest Actual':'Khối lượng thu (kg)','Fruit Measurement':'Chiều dài trung bình (cm)','Planting Event':'Diện tích (ha)'})[type]||'';
 const options=type==='Disease Observation'?state.data?.diseases:state.data?.reasons;
 $('reason').innerHTML=(options||[]).map(r=>`<option value="${esc(r.name)}">${esc(r.reason_name||r.disease_name)}</option>`).join('');
}
async function gps(){if(!navigator.geolocation)return {};try{return await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(p=>resolve({latitude:p.coords.latitude,longitude:p.coords.longitude,gps_accuracy_m:p.coords.accuracy}),reject,{timeout:8000,maximumAge:0,enableHighAccuracy:true}));}catch{return {};}}
async function enqueue(target_doctype,values,photo){
 if(!state.user)throw new Error('Đăng nhập và mở ngày làm việc trước khi nhập.');
 const captured_at=new Date().toISOString(),position=await gps();
 $('gps').textContent=position.latitude==null?'Chưa lấy được GPS':`GPS ±${fmt(position.gps_accuracy_m)} m`;
 const event={client_event_id:crypto.randomUUID(),farm:$('farm').value,target_doctype,values,captured_at,...position};
 const entry={key:state.user+'|'+event.client_event_id,user:state.user,event,photo,status:'Pending',error:'',created:captured_at};
 await db('queue','put',entry);notice('Đã lưu trên máy. Gửi khi có kết nối để hệ thống kiểm tra và nhận phiếu.');await renderQueue();
}
async function upload(blob,name){const data=new FormData();data.append('file',blob,name);data.append('is_private','1');
 const response=await fetch('/api/method/upload_file',{method:'POST',credentials:'same-origin',headers:{'X-Frappe-CSRF-Token':state.session.csrf_token},body:data});const result=await response.json();if(!response.ok||result.exc_type)throw new Error(failure(result));return result.message.file_url;}
let syncing=false;
async function sync(){
 if(syncing)return;syncing=true;
 try{
  const current=await api('lotus_farm.field.session_info');if(current.user!==state.user)throw new Error('Tài khoản đã thay đổi. Mở lại màn hình để giữ riêng bản ghi của từng người.');state.session=current;$('connection').textContent='Đã kết nối';
  const queue=(await db('queue','getAll')).filter(q=>q.user===state.user&&!['Sent','Discarded'].includes(q.status)).sort((a,b)=>a.created.localeCompare(b.created));
  for(const entry of queue){
   try{
    if(entry.photo&&!entry.event.photo){entry.event.photo=await upload(entry.photo,entry.photo.name||'field-photo.jpg');await db('queue','put',entry);}
    const result=await api('lotus_farm.field.capture',entry.event,true);entry.status='Sent';entry.result=result;entry.error='';entry.photo=null;
   }catch(error){entry.status='Error';entry.error=error.message;}
   await db('queue','put',entry);await renderQueue();
  }notice('Đã gửi xong lượt này. Các bản ghi lỗi vẫn được giữ để xử lý.');
 }catch(error){notice(error.message);}finally{syncing=false;}
}
async function renderQueue(){const rows=(await db('queue','getAll')).filter(q=>q.user===state.user);$('queuecount').textContent=rows.filter(q=>!['Sent','Discarded'].includes(q.status)).length+' đang chờ';
 $('queue').innerHTML=rows.map(q=>`<div class="pending ${q.status==='Error'?'error':''}"><strong>${esc(q.event.target_doctype)}</strong> · ${esc(q.event.values.posting_date||q.event.values.harvest_date||q.event.values.operation_date)}<br>${esc(q.status==='Sent'?'Đã nhận: '+q.result.document:q.status==='Error'?q.error:'Chưa gửi')}${q.result?.warning?'<br>'+esc(q.result.warning):''}${q.status==='Error'?`<br><button data-reconcile="${esc(q.key)}">Kiểm tra / bỏ bản nhập sai</button>`:''}${q.status==='Discarded'?'<br>Đã bỏ trước khi máy chủ nhận: '+esc(q.discard_reason):''}</div>`).join('');
 document.querySelectorAll('[data-reconcile]').forEach(button=>button.onclick=()=>safe(async()=>{
 const entry=await db('queue','get',button.dataset.reconcile);const current=await api('lotus_farm.field.session_info');if(current.user!==entry.user)throw new Error('Đăng nhập đúng người đã ghi bản này.');state.session=current;
 const status=await api('lotus_farm.field.capture_status',{client_event_id:entry.event.client_event_id});
 if(status.received){entry.status='Sent';entry.result=status;entry.error='';}else{const reason=prompt('Máy chủ chưa nhận bản này. Ghi lý do bỏ bản nhập sai:');if(!reason?.trim())return;entry.status='Discarded';entry.discard_reason=reason.trim();}
 await db('queue','put',entry);await renderQueue();
 }));
}
function renderMap(){
 const features=state.data.geometries||[];const points=[];
 for(const f of features){const polygons=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates;for(const p of polygons)for(const r of p)points.push(...r);}
 if(!points.length){$('mapview').textContent='Chưa có ranh giới thửa được duyệt.';return;}
 const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]),xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
 const width=xmax-xmin||1,height=ymax-ymin||1,ratio=Math.min(920/width,420/height);
 const project=p=>`${40+(p[0]-xmin)*ratio},${450-(p[1]-ymin)*ratio}`;
 $('mapview').innerHTML=`<svg viewBox="0 0 1000 500" role="img" aria-label="Ranh giới các thửa">${features.map(f=>{const polygons=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates;return polygons.map(p=>`<path data-plot="${esc(f.properties.plot)}" d="${p.map(r=>'M'+r.map(project).join(' L')+' Z').join(' ')}" fill-rule="evenodd" fill="#789d6d80" stroke="#375d35"><title>${esc(f.properties.plot)}</title></path>`).join('');}).join('')}</svg>`;
 document.querySelectorAll('[data-plot]').forEach(p=>p.onclick=()=>safe(async()=>{const result=await api('lotus_farm.reporting.plot_history',{farm_plot:p.dataset.plot});$('plothistory').innerHTML=`<article><h2>${esc(result.plot)}</h2>${table([['Ngày','date'],['Loại','doctype'],['Phiếu','name',r=>link(r.doctype,r.name)]],result.events)}${table([['Kỳ dự thu','period_start_date'],['Trạng thái','supply_state'],['Kg thành phẩm','packed_forecast_kg',r=>fmt(r.packed_forecast_kg)]],result.forecasts)}</article>`;}));
}
async function safe(action){try{await action();}catch(error){notice(error.message);}}
$('date').value=today();$('expected').value=today();$('load').onclick=()=>safe(openDay);
$('cycle').onchange=updateCohorts;$('eventtype').onchange=updateEvent;
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('.panel').forEach(p=>p.hidden=p.id!==b.dataset.tab);document.querySelectorAll('[data-tab]').forEach(n=>n.classList.toggle('active',n===b));});
$('saveresult').onclick=()=>safe(async()=>{const t=state.task,done=Number($('doneqty').value),days=Number($('days').value);if(!$('doneqty').value||!$('days').value||done<0||days<0)throw new Error('Nhập khối lượng và số công hợp lệ.');if(done<t.planned_qty&&!$('unfinished').value.trim())throw new Error('Ghi lý do chưa làm hết.');await enqueue('Daily Work Result',{farm_block:t.farm_block,farm_plot:t.farm_plot,crop_cycle:t.crop_cycle,sucker_selection_batch:t.cohort||null,posting_date:$('date').value,work_plan:t.plan,work_plan_line:t.line,completed_qty:done,actual_workdays:days,unfinished_reason:$('unfinished').value});$('resultdialog').close();});
$('eventform').onsubmit=event=>{event.preventDefault();safe(async()=>{const type=$('eventtype').value,c=state.data.cycles.find(c=>c.name===$('cycle').value);if(!c)throw new Error('Chọn vụ.');const cohort=$('cohort').value||null;if(c.cycle_type==='Ratoon'&&!cohort)throw new Error('Vụ chồi cần chọn đợt chồi.');const values={farm_block:c.farm_block,farm_plot:c.farm_plot,crop_cycle:c.name,sucker_selection_batch:cohort,posting_date:$('date').value};const qty=Number($('qty').value),weight=Number($('weight').value),second=$('second').value;
 if(type==='Bunch Cancellation')Object.assign(values,{bunch_qty:qty,reason:$('reason').value,expected_harvest_date:$('expected').value,notes:$('notes').value});
 if(type==='Disease Observation')Object.assign(values,{affected_plants:qty,disease:$('reason').value,severity:second,action_taken:$('notes').value});
 if(type==='Fruit Measurement'){if(qty!==1)throw new Error('Mỗi lần nhập lưu một mẫu; dùng màn Đo trái Lotus để nhập nhiều mẫu.');Object.assign(values,{samples:[{sample_no:'1',lane:$('notes').value,dimension:'Length',value:weight,uom:'cm'},{sample_no:'1',lane:$('notes').value,dimension:'Diameter',value:Number(second),uom:'cm'}],uom:'cm',row_code:$('notes').value});}
 if(type==='Planting Event')Object.assign(values,{plant_qty:qty,area_ha:weight,event_type:second,notes:$('notes').value});
 if(type==='Harvest Actual'){delete values.posting_date;delete values.farm_plot;Object.assign(values,{harvest_date:$('date').value,harvested_bunch_qty:qty,gross_weight_kg:weight,rejected_weight_kg:Number(second||0)});}
 if(type==='Bunch Operation'){delete values.posting_date;delete values.farm_plot;Object.assign(values,{operation_date:$('date').value,operation_type:second,bunch_qty:qty,rejected_qty:0,notes:$('notes').value});}
 await enqueue(type,values,$('photo').files[0]||null);$('photo').value='';});};
$('sync').onclick=sync;
$('exportqueue').onclick=()=>safe(async()=>{const rows=(await db('queue','getAll')).filter(q=>q.user===state.user&&!['Sent','Discarded'].includes(q.status)).map(({photo,...q})=>({...q,has_local_photo:!!photo}));const url=URL.createObjectURL(new Blob([JSON.stringify(rows,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='lotus-pending-records.json';a.click();URL.revokeObjectURL(url);});
$('clearcache').onclick=()=>safe(async()=>{for(const q of await db('queue','getAll'))if(q.user===state.user&&q.status==='Sent')await db('queue','delete',q.key);for(const c of await db('cache','getAll'))if(c.key.startsWith(state.user+'|'))await db('cache','delete',c.key);await renderQueue();notice('Đã xóa số liệu lưu và các bản ghi đã gửi. Bản đang chờ vẫn giữ nguyên.');});
$('suggest').onclick=()=>safe(async()=>{const r=await api('lotus_farm.field.make_suggested_plan',{farm:$('farm').value,posting_date:$('date').value},true);notice('Đã tạo kế hoạch nháp '+r.plan+'; mở sổ chứng từ để kiểm tra và duyệt.');});
$('labor').onclick=()=>safe(async()=>{const r=await api('lotus_farm.field.available_labor',{farm:$('farm').value,posting_date:$('date').value});$('staff').innerHTML=table([['Người','employee_name'],['Còn công bố trí','remaining_workdays'],['Có chấm công','attendance_known',e=>e.attendance_known?'Có':'Chưa xác nhận']],r.employees);});
$('close').onclick=()=>safe(async()=>{const r=await api('lotus_farm.daily_api.preview_close',{farm:$('farm').value,posting_date:$('date').value});$('closechecks').innerHTML=table([['Kết quả','status'],['Nội dung','message'],['Phiếu','reference_name',r=>r.reference_name?link(r.reference_doctype,r.reference_name):'']],r);});
$('accuracy').onclick=()=>safe(async()=>{const end=$('date').value,start=new Date(end+'T00:00:00');start.setDate(start.getDate()-90);const r=await api('lotus_farm.reporting.forecast_vintages',{farm:$('farm').value,from_date:start.toISOString().slice(0,10),to_date:end});$('vintages').innerHTML=table([['Tuần trước thu','horizon_weeks'],['Kỳ','period_start'],['Dự thu kg','forecast_kg',r=>fmt(r.forecast_kg)],['Thực tế kg','actual_kg',r=>fmt(r.actual_kg)],['Lệch tuyệt đối','absolute_error_kg',r=>fmt(r.absolute_error_kg)],['Đối soát','status']],r.rows);});
$('traceform').onsubmit=event=>{event.preventDefault();safe(async()=>{const r=await api('lotus_farm.reporting.trace_item',{item:$('traceitem').value,batch:$('tracebatch').value||null});$('trace').innerHTML=r.map(run=>`<article><h2>${link('Packout Run',run.packout)}</h2>${table([['Farm','farm'],['Lô','farm_block'],['Thửa','farm_plot'],['Vụ','crop_cycle'],['Lô thu','harvest_lot',r=>link('Harvest Lot',r.harvest_lot)]],run.sources)}</article>`).join('')||'Không có nguồn thành phẩm phù hợp trong phạm vi được xem.';});};
$('deliveries').onclick=()=>safe(async()=>{const r=await api('lotus_farm.reporting.delivery_progress',{farm:$('farm').value});$('deliveryrows').innerHTML=table([['Đơn','sales_order',r=>link('Sales Order',r.sales_order)],['Item','item'],['Đã giao kg','delivered_kg',r=>fmt(r.delivered_kg)],['Còn phải giao kg','remaining_demand_kg',r=>fmt(r.remaining_demand_kg)],['Giữ nguồn','state']],r);});
$('stageform').onsubmit=event=>{event.preventDefault();safe(async()=>{if(!state.session)throw new Error('Kết nối và đăng nhập trước khi tải file.');const file=$('workbook').files[0];const url=await upload(file,file.name);const r=await api('lotus_farm.importing.stage_workbook',{farm:$('farm').value,source_file:$('source').value,mapping:$('mapping').value,file_url:url},true);$('batch').value=r.batch;$('stageinfo').textContent=`Đã đọc ${r.row_count} dòng, ${r.invalid_count} dòng có lỗi. Batch: ${r.batch}`;});};
$('previewimport').onclick=()=>safe(async()=>{const r=await api('lotus_farm.importing.preview_import',{batch:$('batch').value},true);$('importresult').innerHTML=table([['Dòng','row'],['Kết quả','status'],['Lỗi','error']],r);});
$('commitimport').onclick=()=>safe(async()=>{const r=await api('lotus_farm.importing.import_rows',{batch:$('batch').value},true);$('importresult').textContent='Đã tạo '+r.created_drafts.length+' phiếu nháp. Mở batch để đối soát và duyệt.';});
window.addEventListener('online',()=>{$('connection').textContent='Có mạng · bấm gửi bản đang chờ';});window.addEventListener('offline',()=>{$('connection').textContent='Mất mạng · giữ bản ghi trên máy';});
(async()=>{try{await session();await openDay();}catch(error){const cached=state.user?await db('cache','get','session|'+state.user):null;if(cached){$('user').textContent=cached.user;applyCapabilities(cached.capabilities);$('farm').innerHTML=cached.farms.map(f=>`<option value="${esc(f.name)}">${esc(f.farm_name)}</option>`).join('');$('connection').textContent='Chưa kết nối';await openDay();}else{notice('Đăng nhập ERPNext rồi mở lại màn hình.');$('user').innerHTML='<a href="/login" style="color:inherit">Đăng nhập</a>';}}if('serviceWorker' in navigator)navigator.serviceWorker.register('./sw.js',{scope:'./'}).catch(()=>notice('Trình duyệt chưa hỗ trợ mở lại màn hình khi mất mạng; bản ghi vẫn được giữ trên máy.'));})();

let qcAttempt=null;
$('qclot').onchange=()=>{$('qcaccepted').value=(state.packhouse?.lots||[]).find(l=>l.name===$('qclot').value)?.released_raw_kg??'';qcAttempt=null;};
$('qcform').onsubmit=event=>{event.preventDefault();safe(async()=>{
 const payload={farm:$('farm').value,posting_date:$('date').value,harvest_lot:$('qclot').value,accepted_kg:Number($('qcaccepted').value),defect_reason:$('qcdefect').value||null};
 const signature=JSON.stringify(payload);if(!qcAttempt||qcAttempt.signature!==signature)qcAttempt={signature,event:crypto.randomUUID()};
 const result=await api('lotus_farm.packhouse.receive_quality',{...payload,client_event_id:qcAttempt.event},true);
 notice('Đã nhận phiếu QC '+result.document);await openDay();
});};
