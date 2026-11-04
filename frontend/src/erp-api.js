// Calls into lotus_farm.erp_workbench (native ERPNext/HRMS documents, permissions and controllers on the server).
import {call} from './api'

const encode=args=>Object.fromEntries(Object.entries(args).map(([k,v])=>[k,v!==null&&typeof v==='object'?JSON.stringify(v):v]))
// Reads go as GET (objects JSON-encoded in the query); writes as POST with a JSON body.
export const erp=(method,args={},write=false)=>call('lotus_farm.erp_workbench.'+method,write?args:encode(args),write)

const schemas=new Map()
export function erpSchema(doctype){
 if(!schemas.has(doctype))schemas.set(doctype,erp('schema',{doctype}).catch(error=>{schemas.delete(doctype);throw error}))
 return schemas.get(doctype)
}

// A document built by "Tạo tiếp" / "Sửa đổi" (not saved yet) waits here until its form opens.
let pending=null
export const setPendingDocument=loaded=>{pending=loaded}
export function takePendingDocument(doctype){const loaded=pending;pending=null;return loaded?.doc?.doctype===doctype?loaded:null}

// Binary downloads (PDF, Excel) are plain GET links the browser opens.
export const erpFileUrl=(method,params)=>'/api/method/lotus_farm.erp_workbench.'+method+'?'+new URLSearchParams(encode(params))
export const newClientKey=()=>crypto.randomUUID()
