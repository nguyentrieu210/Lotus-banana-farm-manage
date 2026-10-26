import {useScope} from './store'
// Vườn làm việc chosen in the top bar (scope.farm, saved per user). New documents and farm filters start from it;
// components mounted without the app store (tests, standalone pages) get no default.
export function workFarm(){try{return useScope().farm||''}catch{return ''}}
