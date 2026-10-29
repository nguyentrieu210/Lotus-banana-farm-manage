export const presenceDays=row=>(Number(!!Number(row.morning_present))+Number(!!Number(row.afternoon_present)))/2
export function applyPresence(row){
 const days=presenceDays(row)
 row.working_hours=days*8;row.workdays=days;row.status=days===1?'Present':days===.5?'Half Day':'Absent'
 if(!Number(row.morning_present))row.morning_time=null
 if(!Number(row.afternoon_present))row.afternoon_time=null
 if(!days)row.overtime_hours=0
 return row
}
export const presencePayload=row=>({morning_present:Number(!!Number(row.morning_present)),afternoon_present:Number(!!Number(row.afternoon_present)),morning_time:row.morning_time||null,afternoon_time:row.afternoon_time||null})
