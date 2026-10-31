// Quantities from stock/source APIs are in stock units; entered quantities use the selected unit.
export function itemUnits(row){
 const base=row.stock_uom||row.uom
 const units=base?[{uom:base,conversion_factor:1}]:[]
 const configured=row.uoms?.length?row.uoms:(row.pack_uom?[{uom:row.pack_uom,conversion_factor:row.pack_factor}]:[])
 for(const entry of configured){
  const factor=Number(entry.conversion_factor)
  if(entry.uom&&!units.some(u=>u.uom===entry.uom)&&Number.isFinite(factor)&&factor>0)units.push({uom:entry.uom,conversion_factor:factor})
 }
 return units
}
export function conversionFactor(row){
 return itemUnits(row).find(u=>u.uom===(row.uom||row.stock_uom))?.conversion_factor??NaN
}
export function stockQuantity(row){return Number(row.qty)*conversionFactor(row)}
export function quantityLimit(row){
 const factor=conversionFactor(row)
 return Number.isFinite(factor)&&factor>0&&row.remaining_qty!=null?Number(row.remaining_qty)/factor:undefined
}
