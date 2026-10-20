// Roster grid helpers (pure): selected cells -> set_roster changes, weekly rotation, date stepping.
export function addDays(iso,days){const d=new Date(iso+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+days);return d.toISOString().slice(0,10)}
export function mondayOf(iso){const d=new Date(iso+'T00:00:00Z');return addDays(iso,-((d.getUTCDay()+6)%7))}

// cells: [{employee,date}] -> one change per run of consecutive days of one employee.
export function changesFor(cells,shift){
 const byEmployee=new Map()
 for(const c of cells){if(!byEmployee.has(c.employee))byEmployee.set(c.employee,new Set());byEmployee.get(c.employee).add(c.date)}
 const changes=[]
 for(const [employee,dates] of byEmployee){
  const sorted=[...dates].sort();let from=sorted[0],to=sorted[0]
  for(const day of sorted.slice(1)){if(day===addDays(to,1)){to=day;continue}changes.push({employee,from,to,shift:shift||''});from=to=day}
  changes.push({employee,from,to,shift:shift||''})
 }
 return changes
}

// Rotate through `pattern` week by week from `start` (a Monday); offset staggers employees.
export function rotationChanges(employees,start,weeks,pattern,stagger=false){
 if(!pattern.length||weeks<1)return []
 return employees.flatMap((employee,index)=>Array.from({length:weeks},(_,week)=>({employee,from:addDays(start,7*week),to:addDays(start,7*week+6),
  shift:pattern[(week+(stagger?index:0))%pattern.length]})))
}

export function shortShift(name){const match=String(name||'').match(/(\d+)\s*$/);return match?'C'+match[1]:String(name||'').slice(0,3)}
