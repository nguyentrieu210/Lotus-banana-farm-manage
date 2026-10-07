frappe.ui.form.on('Harvest Lot',{
 refresh(frm){
  if(frm.is_new())return;
  frm.add_custom_button(__('QR lô thu hoạch'),()=>frappe.call({method:'lotus_farm.field.lot_qr',args:{harvest_lot:frm.doc.name},callback({message:m}){
   const dialog=new frappe.ui.Dialog({title:__('QR lô thu hoạch'),fields:[{fieldtype:'HTML',fieldname:'qr'}]});
   const image=document.createElement('img');image.src=m.image;image.alt=m.harvest_lot;image.style.width='240px';
   const title=document.createElement('p');title.textContent=m.harvest_lot;
   const target=document.createElement('a');target.href=m.url;target.textContent=__('Mở phiếu nguồn');
   dialog.fields_dict.qr.$wrapper.empty().append(image,title,target);dialog.show();
  }}));
  frm.add_custom_button(__('Truy nguồn'),()=>frappe.call({method:'lotus_farm.reporting.trace_lot',args:{harvest_lot:frm.doc.name},callback({message:m}){
   const dialog=new frappe.ui.Dialog({title:__('Nguồn lô thu hoạch'),fields:[{fieldtype:'HTML',fieldname:'sources'}]});
   const table=document.createElement('table');table.className='table table-bordered';
   const fields=['farm','farm_block','farm_plot','crop_cycle','cohort','harvest_actual','contributed_kg'];
   const header=table.insertRow();for(const f of fields){const cell=document.createElement('th');cell.textContent=f;header.append(cell);}
   for(const row of m.sources){const tr=table.insertRow();for(const f of fields)tr.insertCell().textContent=row[f]??'';}
   dialog.fields_dict.sources.$wrapper.empty().append(table);dialog.show();
  }}));
 }
});
