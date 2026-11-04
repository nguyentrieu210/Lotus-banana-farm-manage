// Column flags the app reads itself (DataTable, grid-format, grid-totals, mobile cards, column chooser, export).
// DataTable strips them before AG Grid sees the column: AG Grid warns (#307/#310) on any colDef key it does not know.
// Adding a new app-only flag? Add it here; tests/grid-app-keys.test.js fails on any unknown key in a column literal.
export const GRID_APP_KEYS=['mobileValue','unitField','autoHide','groupNumbers','suppressExport','hideOnMobile','filterable','defaultHidden','columnChooserLocked','sum']
