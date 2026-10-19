import {themeQuartz} from 'ag-grid-community'
export const compactGridTheme=themeQuartz.withParams({accentColor:'var(--lotus-accent)',backgroundColor:'var(--lotus-surface)',foregroundColor:'var(--lotus-text)',headerBackgroundColor:'var(--lotus-table-header)',headerTextColor:'var(--lotus-table-heading)',borderColor:'var(--lotus-border)',rowHoverColor:'var(--lotus-soft)',fontFamily:'var(--lotus-font)',fontSize:12,rowHeight:36,headerHeight:34,spacing:4})
export const desktopGridThemes={
 comfortable:compactGridTheme.withParams({fontSize:14,rowHeight:48,headerHeight:42,spacing:6}),
 compact:compactGridTheme.withParams({fontSize:13,rowHeight:38,headerHeight:38,spacing:4}),
}
