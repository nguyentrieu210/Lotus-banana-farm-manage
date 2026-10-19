import {foldVietnamese} from './warehouse-mobile-helpers.js'
// Accent-insensitive option matching shared by every picker (desktop Combobox, mobile link/search fields).
// Spaces and dashes are ignored so "lo a1" finds "Lô A-1".
const squash=value=>foldVietnamese(value).replace(/[\s-]+/g,'')
export function matchesOption(option,query){
 const q=squash(query);if(!q)return true
 return squash([option.label,option.value,option.subtitle,option.group].filter(Boolean).join(' ')).includes(q)
}
export function filterOptions(options,query){return (options||[]).filter(option=>matchesOption(option,query))}
