export const normalizeSearch=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase()
export function filterRoles(roles,query='',group='',selected=[],onlySelected=false){
 const needle=normalizeSearch(query)
 return roles.filter(role=>(!group||role.group===group)&&(!onlySelected||selected.includes(role.name))&&normalizeSearch(role.label+' '+role.name).includes(needle))
}
export function scopeWarnings(form){
 const roles=new Set(form.roles||[]),grants=form.advanced_grants||[]
 const hasFarm=form.farms?.length||grants.some(g=>g.doctype==='Farm')
 const hasTeam=form.teams?.length||grants.some(g=>g.doctype==='Work Team')
 const field=['Lotus Farm Manager','Lotus Team Leader','Lotus Field Supervisor','Lotus Auditor','Lotus Price Approver','Lotus Crew Leader'].some(r=>roles.has(r))
 const warnings=[]
 if(field&&!hasFarm)warnings.push('Chưa cấp vườn: tài khoản sẽ bị chặn khi mở dữ liệu thuộc vườn, kể cả có quyền quản trị hệ thống.')
 if(!['Lotus Farm Manager','Lotus Auditor','Lotus Price Approver'].some(r=>roles.has(r))&&['Lotus Team Leader','Lotus Field Supervisor'].some(r=>roles.has(r))&&!hasTeam)warnings.push('Tổ trưởng và giám sát hiện trường cần được cấp tổ trong vườn được chọn.')
 return warnings
}
