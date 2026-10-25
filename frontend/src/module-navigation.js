import {visibleHrNavigation,normalizeHrView,hrQuery} from './hr-navigation.js'
import {visibleBuyingNavigation,normalizeBuyingView,buyingQuery} from './procurement-navigation.js'
import {visibleStockNavigation,normalizeStockView,stockQuery} from './stock-navigation.js'
// Modules whose sidebar group lists their own views (navGroups[].kind). The sidebar, page titles and active state read this registry.
// viewPath: the page whose ?param picks the view; items on other paths (HR → cham-cong) are active whenever that page is open.
export const sectionedModules={
 hr:{paths:['nhan-su','cham-cong'],viewPath:'nhan-su',prop:'hrView',items:visibleHrNavigation,normalize:normalizeHrView,query:hrQuery,setupLabel:'Thiết lập nhân sự',toggleOnly:true},
 buying:{paths:['mua-hang'],viewPath:'mua-hang',prop:'buyingView',items:visibleBuyingNavigation,normalize:normalizeBuyingView,query:buyingQuery,setupLabel:'Danh mục mua hàng',toggleOnly:true},
 stock:{paths:['kho'],viewPath:'kho',prop:'stockView',items:visibleStockNavigation,normalize:normalizeStockView,query:stockQuery,setupLabel:'Danh mục kho',toggleOnly:true},
}
export function moduleForPath(path){return Object.values(sectionedModules).find(m=>m.paths.includes(path))}
