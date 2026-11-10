// Shared plumbing of the Mua hàng screens (spec 003, R22). Every view split out of ProcurementWorkspace
// calls the server the same way: lotus_farm.<module>.<method>, retried with the same key on a MariaDB
// snapshot conflict (purchaseRequest).
import {call} from '../../api'
import {purchaseRequest} from '../../procurement'

export const procurementApi=(name,args={},write=false)=>purchaseRequest(call,'lotus_farm.procurement.'+name,args,write)
export const lotusMethod=(module,name,args={},write=false)=>purchaseRequest(call,'lotus_farm.'+module+'.'+name,args,write)
