// Restrict Work (phone + daily plan) to large Farm Blocks; retain legacy plot data.
const fs=require('node:fs');
function edit(file,transform){
 let content=fs.readFileSync(file,'utf8').replace(/\r\n/g,'\n');
 const old=content;content=transform(content);
 if(content===old)throw Error('No changes applied: '+file);
 fs.writeFileSync(file,content,'utf8');
 console.log('updated',file);
}
function replace(source,oldText,newText,label){
 const count=source.split(oldText).length-1;
 if(count!==1)throw Error((label||oldText.slice(0,50))+' match='+count);
 return source.replace(oldText,newText)
}
edit('lotus_farm/daily_operations.py',s=>{
 s=replace(s,`            plot_scope(row)
            if not frappe.db.get_value('Farm Plot', row.farm_plot, 'active'):
                frappe.throw('Work requires an active Plot.')
`,`            block = frappe.get_doc('Farm Block', row.farm_block)
            block.check_permission('read')
            if block.farm != self.farm or not block.active:
                frappe.throw('Công việc phải thuộc Lô lớn đang hoạt động của vườn.')
            # Legacy cycles/plots remain readable; newly assigned jobs have only a Farm Block.
            if row.farm_plot or row.crop_cycle:
                if not row.crop_cycle:
                    frappe.throw('Dữ liệu cũ có thửa phải liên kết vụ phù hợp.')
                plot_scope(row)
                if not frappe.db.get_value('Farm Plot', row.farm_plot, 'active'):
                    frappe.throw('Historical work requires an active Plot.')
            else:
                row.farm_plot = None
                row.crop_cycle = None
                row.sucker_selection_batch = None
`,'WorkPlan block validation');
 s=replace(s,
 `            key = (row.crop_cycle, row.sucker_selection_batch, row.work_type, row.payment_mode)
            if key in seen:
                frappe.throw('Combine duplicate Cycle/Cohort/Work Type/Payment Mode tasks into one line.')`,
 `            scope_key = ('plot', row.farm_plot, row.crop_cycle, row.sucker_selection_batch) if row.farm_plot else ('block', row.farm_block)
            key = (scope_key, row.work_type, row.payment_mode)
            if key in seen:
                frappe.throw('Gộp các dòng trùng Lô, công việc và hình thức trả công.')
`,'WorkPlan duplicate key');
 return s;
});
edit('lotus_farm/rate_approval.py',s=>replace(s,
 `                "name": row.name, "plot": row.farm_plot,`,
 `                "name": row.name, "block": row.farm_block, "plot": row.farm_plot,`,
 'approval signature block'));
edit('lotus_farm/daily_api.py',s=>{
 return replace(s,
 `work_name=frappe.db.get_value('Work Type',line.work_type,'work_name'),plot_code=frappe.db.get_value('Farm Plot',line.farm_plot,'plot_code'),uom=line.uom`,
 `work_name=frappe.db.get_value('Work Type',line.work_type,'work_name'),block_code=frappe.db.get_value('Farm Block',line.farm_block,'block_code'),plot_code=frappe.db.get_value('Farm Plot',line.farm_plot,'plot_code') if line.farm_plot else None,uom=line.uom`,
 'daily overview block_code');
});
edit('lotus_farm/work_mobile.py',s=>{
 s=replace(s,`fields=["name", "posting_date", "farm_plot", "work_plan", "work_plan_line",`,
 `fields=["name", "posting_date", "farm_block", "farm_plot", "work_plan", "work_plan_line",`,
 'result history block');
 s=replace(s,`        row["plot_code"] = frappe.db.get_value("Farm Plot", row.farm_plot, "plot_code") or row.farm_plot`,
 `        row["block_code"] = frappe.db.get_value("Farm Block", row.farm_block, "block_code") or row.farm_block
        row["plot_code"] = frappe.db.get_value("Farm Plot", row.farm_plot, "plot_code") if row.farm_plot else None`,
 'history display block');
 return s;
});
for(const path of [
 'lotus_farm/lotus_farm/doctype/daily_work_plan_line/daily_work_plan_line.json',
 'lotus_farm/lotus_farm/doctype/daily_work_result/daily_work_result.json'
]){
 let schema=JSON.parse(fs.readFileSync(path,'utf8'));
 for(const f of schema.fields){
  if(f.fieldname==='farm_block')f.label='Lô lớn';
  if(['farm_plot','crop_cycle'].includes(f.fieldname)){
   f.reqd=0;f.hidden=1;
   f.label=f.fieldname==='farm_plot'?'Thửa (dữ liệu cũ)':'Vụ (dữ liệu cũ)';
  }
 }
 fs.writeFileSync(path,JSON.stringify(schema,null,2)+'\n','utf8');
 console.log('updated',path);
}
edit('frontend/src/WorkMobile.vue',s=>{
 s=replace(s,
 `const plotOptions=computed(()=>(assignOptions.value?.plots||[]).map(p=>({value:'plot:'+p.name,label:'Thửa '+(p.plot_code||p.name)+' · '+(p.area_ha||0)+' ha'})))
const locationOptions=computed(()=>[...blockOptions.value,...plotOptions.value])`,
 `const locationOptions=computed(()=>blockOptions.value)`,
 'remove small-plot picker');
 s=s.replaceAll('Lô / thửa','Lô lớn')
    .replaceAll('Gõ mã lô hoặc thửa…','Gõ mã Lô…')
    .replaceAll('Thửa <b>','Lô <b>')
    .replaceAll('thửa hoặc tổ','lô hoặc tổ')
    .replaceAll('thửa…','lô…')
    .replaceAll('Thửa','Lô');
 s=s.replaceAll('t.plot_code||t.farm_plot','t.block_code||t.farm_block||t.plot_code||t.farm_plot')
    .replaceAll('task.plot_code||task.farm_plot','task.block_code||task.farm_block||task.plot_code||task.farm_plot')
    .replaceAll('item.plot_code||item.farm_plot','item.block_code||item.farm_block||item.plot_code||item.farm_plot')
    .replaceAll('selected.plot_code||selected.farm_plot','selected.block_code||selected.farm_block||selected.plot_code||selected.farm_plot')
    .replaceAll('r.plot_code','r.block_code||r.plot_code')
    .replaceAll('line.plot_code','line.block_code||line.plot_code');
 s=s.replaceAll('Lô hoặc thửa','Lô lớn')
 return s;
});
edit('frontend/tests/work-mobile-parity.test.js',s=>s.replaceAll('Gõ mã lô hoặc thửa…','Gõ mã Lô…'));
console.log('Completed block-only work migration source updates.');
