export function updateColumnFilter(current,field,values){
 const next={...current}
 if(values===null)delete next[field]
 else next[field]=values
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
