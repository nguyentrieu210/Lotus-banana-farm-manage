import {themeQuartz} from 'ag-grid-community'
// The shared table theme, built from the Lotus tokens (spec 004, FR-011 to FR-013a).
// Colours are CSS variables, so light, dark and outdoor follow the page without rebuilding the grid.
// Sizes are numbers because the grid lays rows out in JS; GRID_DENSITY must match the --lotus-table-* tokens
// of each density in lotus-tokens.css (tests/grid-theme.test.js checks it).
export const GRID_DENSITY=Object.freeze({
 compact:Object.freeze({rowHeight:36,headerHeight:36,fontSize:13,headerFontSize:12,cellHorizontalPadding:10}),
 comfortable:Object.freeze({rowHeight:44,headerHeight:40,fontSize:14,headerFontSize:12,cellHorizontalPadding:12}),
})
export const GRID_VARIANTS=Object.freeze(['default','stock'])

const line=color=>({style:'solid',width:1,color})
const COLOURS=Object.freeze({
 accentColor:'var(--lotus-primary)',
 backgroundColor:'var(--lotus-surface)',
 foregroundColor:'var(--lotus-text)',
 borderColor:'var(--lotus-table-border)',
 fontFamily:'var(--lotus-font)',
 headerBackgroundColor:'var(--lotus-table-header)',
 headerTextColor:'var(--lotus-table-heading)',
 headerFontWeight:600,
 headerCellHoverBackgroundColor:'var(--lotus-table-hover)',
 headerRowBorder:line('var(--lotus-border-strong)'),
 rowBorder:line('var(--lotus-table-border)'),
 oddRowBackgroundColor:'var(--lotus-table-zebra)',
 rowHoverColor:'var(--lotus-table-hover)',
 selectedRowBackgroundColor:'var(--lotus-table-selected)',
 pinnedRowBackgroundColor:'var(--lotus-table-total)',
 pinnedRowFontWeight:650,
 pinnedColumnBorder:line('var(--lotus-border-strong)'),
 wrapperBorder:line('var(--lotus-table-border)'),
 wrapperBorderRadius:8,
 rangeSelectionBorderColor:'var(--lotus-focus-ring)',
 spacing:4,
})
// Kho: every cell and header centred, vertical lines between columns (accepted by the owner; FR-013a).
const VARIANT_PARAMS=Object.freeze({
 default:{},
 stock:{columnBorder:line('var(--lotus-table-border)'),headerColumnBorder:line('var(--lotus-table-border)')},
})

const cache=new Map()
// One theme object per density and variant: the grid re-applies CSS only when the object changes.
export function lotusGridTheme(density='compact',variant='default'){
 const d=GRID_DENSITY[density]?density:'compact',v=VARIANT_PARAMS[variant]?variant:'default',key=d+'|'+v
 if(!cache.has(key))cache.set(key,themeQuartz.withParams({...COLOURS,...GRID_DENSITY[d],...VARIANT_PARAMS[v]}))
 return cache.get(key)
}

// Kept for older imports.
export const compactGridTheme=lotusGridTheme('compact')
export const desktopGridThemes={compact:lotusGridTheme('compact'),comfortable:lotusGridTheme('comfortable')}
