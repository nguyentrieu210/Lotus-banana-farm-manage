// Excel-like checklist selections are isolated for predictable unit tests.
export const excelKey = value => value === null || value === undefined ? '__LOTUS_BLANK__' : String(value)
const normalized = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('vi').trim()
export function filterExcelChoices(choices,query){
 const search=normalized(query)
 return !search?[...choices]:choices.filter(row=>
  normalized(row.label??row.value).includes(search)||normalized(row.value).includes(search))
}
export function toggleExcelVisible(selected,visible,allVisible){
 const next=new Set(selected)
 for(const item of visible){
  const key=excelKey(item.value)
  if(allVisible)next.delete(key)
  else next.add(key)
 }
 return [...next]
}
export function excelAppliedValues(choices,selected){
 const checked=new Set(selected)
 const values=choices.filter(row=>checked.has(excelKey(row.value))).map(row=>row.value)
 return values.length===choices.length?null:values
}

// Anchor the popup to the RIGHT of the clicked filter; remain inside the viewport.
export function excelPopupLeft(triggerRight, popupWidth, viewportWidth){
 return Math.max(8,Math.min(triggerRight+8,viewportWidth-popupWidth-8))
}
