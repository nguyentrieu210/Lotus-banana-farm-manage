export const STOCK_QUICK_FILTERS={
 minimum:{field:'stock_status',values:['Dưới tối thiểu']},
 demand:{field:'coverage_status',values:['Cần mua','Chờ nhập']}
}

export function updateColumnFilter(current,field,values){
 const next={...current}
 if(values===null)delete next[field]
 else next[field]=values
 return next
}

export function toggleStockQuickFilter(current,kind){
 const preset=STOCK_QUICK_FILTERS[kind]
 if(!preset)throw new Error('Bộ lọc nhanh không hợp lệ')
 const next={...current}
 // Quick actions are mutually exclusive; deliberate header filters remain visible.
 for(const [name,other] of Object.entries(STOCK_QUICK_FILTERS)){
  if(name!==kind)delete next[other.field]
 }
 const existing=next[preset.field]
 if(Array.isArray(existing)&&existing.length===preset.values.length&&
    preset.values.every(value=>existing.includes(value))){
  delete next[preset.field]
 }else next[preset.field]=[...preset.values]
 return next
}

export function shiftISODate(day,offset){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(String(day||'')))return ''
 const date=new Date(day+'T00:00:00Z')
 if(Number.isNaN(date.getTime()))return ''
 date.setUTCDate(date.getUTCDate()+offset)
 return date.toISOString().slice(0,10)
}

export function hasStockSearchFilters(search,filters){
 return !!String(search||'').trim()||Object.keys(filters||{}).length>0
}

export function stockEmptyKind({company,warehouseCount,catalogueCount,filteredCount,loading}){
 if(loading)return 'loading'
 if(!company)return 'no-company'
 if(!warehouseCount)return 'no-warehouse'
 if(!catalogueCount)return 'no-items'
 if(filteredCount===0)return 'no-matches'
 return 'results'
}
