// Excel-like checklist selections are isolated for predictable unit tests.
export const excelKey = value => value === null || value === undefined ? '__LOTUS_BLANK__' : String(value)
const normalized = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[đĐ]/g,'d').toLocaleLowerCase('vi').trim()
export function filterExcelChoices(choices,query){
 const search=normalized(query)
 return !search?[...choices]:choices.filter(row=>
  normalized(row.label??row.value).includes(search)||normalized(row.value).includes(search))
}
// Text typed into an Excel header selects the matching values, not just the
// entries displayed in the dropdown. Keep manual checkbox edits separate.
export function excelDefaultSelection(choices,selection,query=''){
 const values=normalized(query)
  ? filterExcelChoices(choices,query).map(row=>row.value)
  : Array.isArray(selection)?selection:choices.map(row=>row.value)
 return values.map(excelKey)
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
 return choices.length>0&&values.length===choices.length?null:values
}

// Value list order: numbers by value, text in Vietnamese order (A2 before A10), blanks last.
const collator=new Intl.Collator('vi',{numeric:true,sensitivity:'base'})
const blank=value=>value===null||value===undefined||value===''
export function sortExcelChoices(choices){
 return [...choices].sort((a,b)=>{
  if(blank(a.value)||blank(b.value))return blank(a.value)-blank(b.value)
  if(typeof a.value==='number'&&typeof b.value==='number')return a.value-b.value
  return collator.compare(String(a.label??a.value),String(b.label??b.value))
 })
}

// Anchor the popup to the RIGHT of the clicked filter; remain inside the viewport.
export function excelPopupLeft(triggerRight, popupWidth, viewportWidth){
 return Math.max(8,Math.min(triggerRight+8,viewportWidth-popupWidth-8))
}
