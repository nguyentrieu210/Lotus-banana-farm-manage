// Pure read-only, deterministic planning simulation. Never posts operational documents.
export const ANCHORS = {Planting:'Trồng',Selection:'Chọn chồi',Shooting:'Trổ buồng','Cut Bud':'Cắt bắp'};
const OFFSET = {Planting:'planting_to_harvest_days',Selection:'sucker_to_harvest_days',Shooting:'shooting_to_harvest_days','Cut Bud':'cut_bud_to_harvest_days'};
const iso = date => date instanceof Date && !Number.isNaN(date.getTime()) ? date.toISOString().slice(0,10) : '';
export function day(date, offset=0) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(date||'')) || !Number.isFinite(Number(offset))) return '';
  const d = new Date(String(date)+'T12:00:00Z');
  if(Number.isNaN(d.getTime()))return '';
  d.setUTCDate(d.getUTCDate()+Number(offset));return iso(d);
}
export function month(date, offset=0) {
  if(!date)return '';
  const parts=String(date).slice(0,10).split('-').map(Number);
  if(parts.length!==3||!parts.every(Number.isFinite))return '';
  const base=new Date(Date.UTC(parts[0],parts[1]-1+offset,1,12));
  const last=new Date(Date.UTC(base.getUTCFullYear(),base.getUTCMonth()+1,0,12)).getUTCDate();
  base.setUTCDate(Math.min(parts[2],last));return iso(base);
}
export const number=value=>value===null||value===undefined||value===''?null:Number.isFinite(Number(value))?Number(value):null;
export const within=(when,start,end)=>!!when&&when>=start&&when<=end;
export function pickProfile(profiles,cohort,block,when) {
  const matches=(profiles||[]).filter(p=>p.approval_state==='Approved'&&Number(p.active)===1
    &&(!p.farm||p.farm===cohort.farm)&&(!p.farm_block||p.farm_block===cohort.farm_block)
    &&(!p.variety||p.variety===block?.variety)
    &&(!p.valid_from||p.valid_from<=when)&&(!p.valid_to||p.valid_to>=when));
  return matches.sort((a,b)=>{
    const specificity=p=>Number(!!p.farm_block)*4+Number(!!p.variety)*2+Number(!!p.farm);
    return specificity(b)-specificity(a)||Number(b.version||0)-Number(a.version||0);
  })[0]||null;
}
export function stages(cohort,profile) {
  const result={};
  if(!profile||!cohort.anchor_date||!OFFSET[cohort.anchor])return {dates:result,harvest:'',warning:'Thiếu mốc hoặc bộ hệ số đã duyệt'};
  const until=number(profile[OFFSET[cohort.anchor]]);
  if(until===null||until<=0)return {dates:{[cohort.anchor]:cohort.anchor_date},harvest:'',warning:'Chưa khai báo số ngày từ mốc đến thu'};
  const harvest=day(cohort.anchor_date,until);
  for(const [anchor,field] of Object.entries(OFFSET)) {
    const d=number(profile[field]);
    if(d!==null&&d>0)result[anchor]=day(harvest,-d);
  }
  result[cohort.anchor]=cohort.anchor_date;
  const ordered=['Planting','Selection','Shooting','Cut Bud'];
  let previous='';
  for(const k of ordered){if(result[k]&&previous&&result[k]<previous)return {dates:result,harvest:'',warning:'Mốc sinh trưởng không đúng thứ tự, kiểm tra bộ hệ số'};if(result[k])previous=result[k];}
  if(previous&&previous>harvest)return {dates:result,harvest:'',warning:'Mốc sinh trưởng vượt ngày thu'};
  return {dates:result,harvest,warning:''};
}
export function allocate(amount,percentages) {
  if(!Number.isSafeInteger(amount)||amount<0||percentages.length!==3||percentages.some(v=>v<0||!Number.isFinite(v))||Math.abs(percentages.reduce((a,b)=>a+b,0)-100)>0.0001)throw Error('Tỷ lệ trổ phải đủ 100%, số buồng là số nguyên');
  const a=Math.floor(amount*percentages[0]/100),b=Math.floor(amount*percentages[1]/100);
  return [a,b,amount-a-b];
}
function floweringWaves(cohort,phase,profile,shares) {
  const shoot=phase.dates.Shooting;
  const interval=number(profile?.shooting_to_harvest_days);
  const cutDays=number(profile?.cut_bud_to_harvest_days);
  if(!shoot||!interval||!Number.isSafeInteger(number(cohort.planned_qty))||cohort.quantity_basis!=='Bunches'
    ||!['Planting','Selection'].includes(cohort.anchor))return [];
  return allocate(Number(cohort.planned_qty),shares).map((count,index)=>{
    const flowering=month(shoot,index);
    const harvest=day(flowering,interval);
    const cut=cutDays>0?day(harvest,-cutDays):'';
    return {ordinal:index+1,quantity:count,dates:{...phase.dates,Shooting:flowering,'Cut Bud':cut},harvest,source:'Mô phỏng 3 đợt'};
  }).filter(w=>w.quantity>0);
}
function latestCohorts(rows,includeDraft) {
  const versions=new Map();
  for(const c of rows||[]) {
    if(!includeDraft&&c.approval_state!=='Approved')continue;
    const key=[c.farm,c.farm_block,c.cohort_code].join('|');
    const previous=versions.get(key);
    if(!previous||Number(c.version)>Number(previous.version)||
      (Number(c.version)===Number(previous.version)&&c.approval_state==='Approved'))versions.set(key,c);
  }
  return [...versions.values()];
}
export function simulate(payload,{from='2026-01-01',months=36,includeDraft=false,flowerShares=[20,60,20],repeatRatoons=true}={}) {
  const start=month(from,0),end=day(month(start,months),-1);
  const blocks=new Map((payload?.blocks||[]).map(b=>[b.name,b]));
  const works=new Map((payload?.works||[]).map(w=>[w.name,w]));
  const normProfiles=payload?.norms||[];
  const rules=(payload?.rules||[]).filter(r=>r.approval_state==='Approved');
  const warnings=new Set(),events=[],harvests=[],materials=[];
  const planCohorts=latestCohorts(payload?.cohorts,includeDraft);
  const cohortsPerBlock=new Map();
  for(const c of planCohorts)cohortsPerBlock.set(c.farm_block,(cohortsPerBlock.get(c.farm_block)||0)+1);
  const addWarning=(cohort,message)=>warnings.add((cohort?.cohort_name||cohort?.cohort_code||'Cấu hình')+': '+message);
  const issue=(cohort,profile,dates,harvest,quantity,tag)=>{
    const workRules=rules.filter(r=>r.farm===cohort.farm&&(!r.valid_from||r.valid_from<=end)&&(!r.valid_to||r.valid_to>=start));
    for(const rule of workRules) {
      if(!dates[rule.anchor])continue;
      const off=number(rule.offset_days);
      if(off===null)continue;
      const monthOffset=number(rule.offset_months)||0;
      const first=day(month(dates[rule.anchor],monthOffset),off);
      const every=number(rule.repeat_days)||0;
      const everyMonth=number(rule.repeat_months)||0;
      let occurrence=0;
      while(first&&occurrence<125) {
        const when=everyMonth?day(month(dates[rule.anchor],monthOffset+everyMonth*occurrence),off):day(first,every*occurrence);
        if(!when||when>end||(harvest&&when>harvest))break;
        if((!rule.valid_from||rule.valid_from<=when)&&(!rule.valid_to||rule.valid_to>=when)&&when>=start) {
          let qty=null;
          if(rule.quantity_basis===cohort.quantity_basis)qty=quantity;
          else if(rule.quantity_basis==='Area'&&Number(blocks.get(cohort.farm_block)?.area_ha)>0) {
            if(cohortsPerBlock.get(cohort.farm_block)===1)qty=Number(blocks.get(cohort.farm_block).area_ha);
            else addWarning(cohort,'Định mức theo ha cần xác nhận diện tích từng đợt; chưa tự nhân diện tích cả lô');
          } else addWarning(cohort,'Đơn vị '+rule.quantity_basis+' khác số lượng đợt '+cohort.quantity_basis+'; chưa quy đổi');
          const work=works.get(rule.work_type);
          if(!work){addWarning(cohort,'Công việc không còn hoạt động: '+rule.work_type);}
          if(qty!==null&&work) {
            const productivity=number(work.productivity_per_workday);
            const labor=productivity>0?qty/productivity:null;
            const norm=normProfiles.find(n=>n.name===rule.norm_profile&&n.approval_state==='Approved'&&n.work_type===work.name&&n.valid_from<=when&&(!n.valid_to||n.valid_to>=when))
              ||normProfiles.find(n=>n.approval_state==='Approved'&&n.work_type===work.name&&n.farm===cohort.farm&&n.valid_from<=when&&(!n.valid_to||n.valid_to>=when));
            if(!norm)addWarning(cohort,'Chưa có định mức vật tư hiệu lực cho '+work.work_name);
            const lines=norm?(payload.norm_lines?.[norm.name]||[]):[];
            for(const line of lines) {
              const basis=number(line.basis_qty);
              if(!basis||basis<=0){addWarning(cohort,'Mức vật tư thiếu khối lượng cơ sở');continue;}
              materials.push({item:line.item,uom:line.uom,quantity:qty/basis*(number(line.norm_qty)||0)*(number(line.frequency)||0)*(number(line.conversion_factor)||0),date:when,cohort:cohort.name});
            }
            events.push({key:[cohort.name,tag,rule.name,occurrence].join('|'),farm_block:cohort.farm_block,cohort:cohort.cohort_name,work_type:work.work_name,date:when,qty,uom:work.uom,
              required_workdays:labor,piecework_cost:Number(work.allow_piecework)===1&&number(work.piecework_rate)>0?qty*Number(work.piecework_rate):null,norm_version:norm?.version??null,projected:true});
          }
        }
        if((!every||every<=0)&&!everyMonth)break;
        occurrence++;
      }
    }
  };
  for(const c of planCohorts) {
    const block=blocks.get(c.farm_block);
    if(!block){addWarning(c,'Lô không thuộc phạm vi đang xem');continue;}
    const profile=pickProfile(payload?.profiles,c,block,c.anchor_date);
    const phase=stages(c,profile);
    if(phase.warning)addWarning(c,phase.warning);
    if(!profile){continue;}
    const count=number(c.planned_qty);
    if(count===null||count<=0){addWarning(c,'Số lượng không hợp lệ');continue;}
    const waves=floweringWaves(c,phase,profile,flowerShares);
    // A single Planting/Selection activity is not repeated three times.
    issue(c,profile,Object.fromEntries(Object.entries(phase.dates).filter(([k])=>k==='Planting'||k==='Selection')),phase.harvest,count,'base');
    const portions=waves.length?waves:[{quantity:count,dates:phase.dates,harvest:phase.harvest,ordinal:1,source:'Mốc của đợt'}];
    for(const wave of portions) {
      issue(c,profile,Object.fromEntries(Object.entries(wave.dates).filter(([k])=>k==='Shooting'||k==='Cut Bud')),wave.harvest,wave.quantity,'wave-'+wave.ordinal);
      if(wave.harvest&&within(wave.harvest,start,end)) {
        const weight=number(profile.avg_bunch_weight_kg),survival=number(profile.bunch_survival_rate_percent),quality=number(profile.quality_pass_rate_percent),packout=number(profile.packout_rate_percent);
        if(c.quantity_basis==='Bunches'&&[weight,survival,quality,packout].every(v=>v!==null)
           &&weight>0&&[survival,quality,packout].every(v=>v>=0&&v<=100)) {
          const gross=wave.quantity*survival/100*weight;
          harvests.push({date:wave.harvest,month:wave.harvest.slice(0,7),farm_block:c.farm_block,cohort:c.cohort_name,wave:wave.ordinal,bunches:wave.quantity,gross_kg:gross,packed_kg:gross*quality/100*packout/100,projected:true});
        } else addWarning(c,'Thiếu số buồng hoặc hệ số đã duyệt để tính kg; không coi cây = buồng.');
      }
    }
    if(repeatRatoons&&phase.harvest&&number(profile.ratoon_interval_days)>0) {
      const gap=number(profile.ratoon_interval_days);
      for(let k=1;k<=8;k++){
        const next=day(phase.harvest,k*gap);
        if(!next||next>end)break;
        // Virtual future ratoons are shown as potential dates, never counted as confirmed yield.
        if(next>=start)harvests.push({date:next,month:next.slice(0,7),farm_block:c.farm_block,cohort:c.cohort_name+' · vụ chồi dự phóng '+(k+1),wave:0,bunches:null,gross_kg:null,packed_kg:null,projected:true,virtual:true});
      }
    }
  }
  const monthly=[];
  for(let i=0;i<months;i++){
    const id=month(start,i).slice(0,7);
    const mEvents=events.filter(e=>e.date.startsWith(id));
    const mHarvest=harvests.filter(e=>e.month===id&&!e.virtual);
    monthly.push({month:id,tasks:mEvents.length,workdays:mEvents.reduce((x,e)=>x+Number(e.required_workdays||0),0),
      piecework_cost:mEvents.reduce((x,e)=>x+Number(e.piecework_cost||0),0),
      bunches:mHarvest.reduce((x,e)=>x+Number(e.bunches||0),0),
      gross_kg:mHarvest.reduce((x,e)=>x+Number(e.gross_kg||0),0),
      packed_kg:mHarvest.reduce((x,e)=>x+Number(e.packed_kg||0),0)});
  }
  return {start,end,events,harvests,materials,monthly,warnings:[...warnings],rule:'Chỉ tính thử, không giao việc, không xuất kho và không cam kết bán.'};
}
