// AG Grid modules Lotus actually uses, registered once. AllCommunityModule pulled ~700 KB into the main bundle.
// In dev, ValidationModule reports any feature that needs a module missing from this list.
import {ModuleRegistry,ClientSideRowModelModule,ClientSideRowModelApiModule,LocaleModule,RowStyleModule,CellStyleModule,ColumnApiModule,RowAutoHeightModule,ValidationModule} from 'ag-grid-community'
ModuleRegistry.registerModules([ClientSideRowModelModule,ClientSideRowModelApiModule,LocaleModule,RowStyleModule,CellStyleModule,ColumnApiModule,RowAutoHeightModule,...(import.meta.env.DEV?[ValidationModule]:[])])
