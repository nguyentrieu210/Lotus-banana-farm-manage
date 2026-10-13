// Keep empty number fields empty; only convert actual numeric values.
export function normalizeInputValue(raw,numberModifier=false){
  if(!numberModifier||raw==='')return raw
  const n=Number(raw)
  return Number.isNaN(n)?raw:n
}
