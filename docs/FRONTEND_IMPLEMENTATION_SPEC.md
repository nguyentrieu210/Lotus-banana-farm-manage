# Lotus Frontend — Implementation Specification

**Depends on:** [FRONTEND_BRD.md](FRONTEND_BRD.md)  
**Backend coverage:** [BRD_COVERAGE.md](BRD_COVERAGE.md)

## 1. Mục tiêu kỹ thuật

Xây SPA Vue 3 tại `/lotus`, chạy cùng Frappe site và tái sử dụng backend ProMax hiện có.

Không thay backend bằng API riêng chỉ để phục vụ frontend mới nếu Frappe resource/custom method hiện tại đã đủ.

## 2. Package baseline

Khóa version tại đầu implementation branch:

- Vue 3.
- frappe-ui.
- vue-router.
- pinia.
- vite.
- TypeScript nếu team chấp nhận; khuyến nghị dùng để khóa contract frontend.
- PWA plugin chỉ khi offline module bắt đầu.

Không lấy dependency trôi theo `develop` của Frappe CRM/Frappe UI.

## 3. Source layout

```text
frontend/
  index.html
  package.json
  vite.config.ts
  src/
    main.ts
    App.vue

    app/
      router/
        index.ts
        routes.ts
        guards.ts
      layouts/
        AppLayout.vue
        FieldLayout.vue

    modules/
      dashboard/
      farms/
      planning/
      forecast/
      work/
      labor/
      materials/
      losses/
      measurements/
      harvest/
      qc/
      packhouse/
      close/
      trace/
      reports/
      admin/

    components/
      common/
      domain/

    composables/
    repositories/
    stores/
    offline/
    types/
    utils/
```

## 4. Router contract

Named routes:

| Name | Path |
|---|---|
| today | /lotus/today |
| farms | /lotus/farms |
| farm | /lotus/farms/:farm |
| block | /lotus/blocks/:block |
| plot | /lotus/plots/:plot |
| cycle | /lotus/cycles/:cycle |
| plans | /lotus/plans |
| forecast | /lotus/forecast |
| work | /lotus/work |
| labor | /lotus/labor |
| materials | /lotus/materials |
| losses | /lotus/losses |
| measurements | /lotus/measurements |
| harvest | /lotus/harvest |
| incoming-qc | /lotus/incoming-qc |
| packhouse | /lotus/packhouse |
| daily-close | /lotus/daily-close |
| cycle-close | /lotus/cycle-close |
| trace | /lotus/trace |
| reports | /lotus/reports |
| masters | /lotus/admin/masters |
| imports | /lotus/admin/imports |
| settings | /lotus/admin/settings |

Query sync:

- farm.
- block.
- plot.
- cycle.
- date/from/to.
- status.
- search.
- sort.
- group.
- view.

## 5. Session bootstrap

First request:

`lotus_farm.field.session_info`

Store:

```ts
type SessionState = {
  user: string
  farms: FarmOption[]
  capabilities: Record<string, boolean>
}
```

Rules:

- same-site cookie session.
- no API secret in browser.
- CSRF token used for POST/upload.
- capability controls navigation/action visibility.
- backend permission remains authoritative.

## 6. Scope store

```ts
type ScopeState = {
  company?: string
  farm?: string
  block?: string
  plot?: string
  cycle?: string
  date: string
}
```

Priority:

route query/params → persisted last safe scope → first permitted Farm.

Never restore a Farm the session no longer permits.

## 7. Repository contracts

### fieldRepository

- sessionInfo()
- bootstrap(farm, date)
- capture(event)
- captureStatus(clientEventId)
- mapData(farm)
- makeSuggestedPlan(farm, date)
- availableLabor(farm, date)

### reportingRepository

- dashboard(farm, from, to)
- packhouseDay(farm, date)
- plotHistory(plot)
- forecastVintages(farm, from, to)
- traceItem(item, batch?)
- deliveryProgress(farm)

### closeRepository

- previewDaily(farm, date)

### packhouseRepository

- receiveQuality(payload)

### importRepository

- stageWorkbook(payload)
- previewImport(batch)
- importRows(batch)

### resource repositories

CRUD cho DocType khi không cần command atomic.

## 8. Shared component contracts

### ScopePicker

Props:

- session farms.
- current scope.
- max depth.
- disabled levels.

Events:

- update:scope.

Behavior:

- farm change clears invalid block/plot/cycle.
- no Xí nghiệp level.

### OpsDataTable

Features:

- server paging.
- server sort.
- server filter.
- column config.
- row actions.
- bulk select optional.
- loading/empty/error.

### OpsViewControls

- filter builder.
- sort.
- group.
- list/board toggle.
- saved view optional V1.

### ExceptionBanner

Input:

- severity.
- blocking.
- code.
- message.
- reference doctype/name.

CTA opens source transaction.

### SyncStatus

States:

- Online.
- Offline.
- Pending n.
- Syncing.
- Error n.

### OfflineQueueDrawer

Each row:

- doctype.
- captured_at.
- status.
- error.
- photo pending.
- server reconciliation action.

## 9. Today data flow

```text
route scope/date
→ dashboard()
→ bootstrap()
→ optional packhouseDay()
→ view model
→ KPI/cards/tables
```

Do not issue one request per card.

If latency becomes high, backend may add one orchestration endpoint later, but only after measurement.

## 10. Work write flow

Online:

```text
form
→ validate client
→ capture(Daily Work Result)
→ server validates scope/state/idempotency
→ invalidate bootstrap/dashboard
```

Offline:

```text
form
→ local UUID
→ IndexedDB
→ show Pending
→ reconnect
→ upload photo if any
→ capture()
→ mark Sent/Error
→ captureStatus() before discard
```

## 11. Offline schema

```ts
type QueueEntry = {
  key: string
  user: string
  event: {
    client_event_id: string
    farm: string
    target_doctype: string
    values: Record<string, unknown>
    captured_at: string
    latitude?: number
    longitude?: number
    gps_accuracy_m?: number
    photo?: string
  }
  status: 'Pending' | 'Syncing' | 'Sent' | 'Error' | 'Discarded'
  error?: string
  result?: unknown
  created: string
  discard_reason?: string
}
```

Storage must be namespaced by user.

## 12. Idempotency

For field capture and QC retry:

- preserve the same event id while payload is unchanged;
- payload change creates a new attempt id;
- server remains final authority;
- client must never “fix duplicate” by silently deleting a pending row.

## 13. Upload contract

Use Frappe `upload_file`.

Rules:

- private file.
- CSRF.
- queue photo blob locally first.
- upload only during sync.
- after upload success persist file URL into queued event before capture.
- failed upload keeps queue row recoverable.

## 14. Dashboard view model

Normalize server response into frontend model; do not make components depend directly on unstable nested payload.

Example:

```ts
type TodayViewModel = {
  kpis: {
    workCompletion?: number
    laborGap?: number
    harvestKg?: number
    packoutPercent?: number
    cancellationBunches?: number
    closeBlockingCount?: number
  }
  tasks: WorkRow[]
  forecast: ForecastRow[]
  losses: LossRow[]
  materials: MaterialRow[]
  alerts: AlertRow[]
}
```

## 15. Work module

Pages:

- WorkListPage.
- WorkBoardPage.
- WorkDetailPage.

Dialogs:

- CreatePlanDialog.
- RecordResultDialog.
- AllocateLaborDialog.
- MaterialRequirementDialog.

Rules:

- incomplete work requires reason per backend rule;
- units displayed from Work Type;
- no client-only business formula considered authoritative.

## 16. Labor module

Pages:

- LaborBoardPage.
- LaborDayDetail.

Columns:

- group.
- available.
- attendance known.
- required.
- allocated.
- actual.
- gap.

Attendance unknown must stay unknown.

## 17. Material module

Pages:

- RequirementList.
- RequirementDetail.

Actions:

- calculate/recalculate if allowed.
- refresh ERP availability.
- create Material Request.
- open linked Stock Entry.
- record consumption/recovery via existing flow.

Never maintain a frontend “stock balance” cache as source of truth.

## 18. Loss module

Pages:

- LossList.
- LossAnalytics.

Quick create must use canonical reason master.

Show:

- linked forecast period.
- ATP impact when backend returns it.
- original forecast snapshot remains immutable.

## 19. Measurement module

Use child-row editor:

- sample number.
- lane/row.
- length/diameter/value fields that backend DocType actually exposes.
- UOM.

Avoid 140-column screen.

## 20. Harvest module

Pages:

- HarvestList.
- HarvestDetail.
- HarvestLotDetail.

Actions:

- capture actual.
- open lot.
- show QR.
- trace.

Immutable submitted actual rule reflected in UI.

## 21. QC module

Components:

- QCSummary.
- DefectMatrix.
- QCQuickDialog.

Reuse `receive_quality` for quick path. Use DocType form/resource when multi-defect edit needs full document.

## 22. Packhouse module

Pages:

- PackhouseDay.
- PackoutRunDetail.

Tabs:

- Inputs.
- QC.
- Outputs.
- Secondary.
- Loss.
- ERP stock.
- Reconciliation.

Mass-balance display is read from backend values.

## 23. Close module

DailyClosePage:

- preview button.
- grouped checks.
- blocking/non-blocking.
- reference links.
- submit action when server says allowed.
- reopen flow requires reason.

Do not duplicate close rules in Vue.

## 24. Trace module

Search input:

- Harvest Lot.
- Item.
- Batch.
- Plot.

Render:

- TraceTimeline.
- source tree.
- links to Frappe documents.

## 25. Import Center

Pages:

- SourceFiles.
- Mapping.
- Batch.
- Reconciliation.
- IntegrationErrors.

Important states:

- Unknown source.
- Active source.
- staged.
- invalid.
- ready.
- imported draft.
- reconciled.

Do not hide rejected/pending counts.

## 26. Map module

Prefer Leaflet or another proven Vue-compatible map library only after version pin.

Data:

- approved GeoJSON.
- Plot identity.
- status/metrics as overlay.

Click:

- route to Plot 360.
- optional side drawer history.

## 27. Frappe UI usage

Use Frappe UI as base design language, not merely as a CSS dependency.

Prefer shared wrappers for:

- Button.
- FormControl.
- Dialog.
- Dropdown.
- Tabs.
- Tooltip.
- Badge.
- Toast.
- list/table primitives.

Lotus-specific logic lives in domain components, not patched into base components.

## 28. Error handling

Repository normalizes:

- HTTP error.
- Frappe `_server_messages`.
- permission error.
- validation error.
- conflict/idempotency error.
- offline/network error.

UX:

- field validation inline.
- action error toast/banner.
- queue error remains visible until resolved.
- no silent retry for destructive actions.

## 29. Cache/invalidation

Invalidate by domain event:

- work result → work + dashboard.
- cancellation → loss + forecast + dashboard.
- harvest → harvest + dashboard + receiving.
- QC → QC + packhouse.
- packout → packhouse + dashboard + trace.
- close → close + dashboard.

Avoid global “reload everything” after every save.

## 30. Permission tests

Mandatory E2E:

1. Farm A user cannot route/open Farm B.
2. guessed DocType ID from Farm B returns denied.
3. hidden sidebar entry is not the only protection.
4. offline row captured before permission revoke is rejected at sync.
5. QC user cannot execute manager-only action.
6. import user cannot create arbitrary target DocType outside configured mapping/permission.

## 31. Frontend test matrix

### Unit

- repository normalization.
- route↔scope sync.
- queue reducer.
- idempotency attempt logic.
- view model mappers.

### Component

- loading.
- empty.
- error.
- no-permission.
- state/action visibility.
- dialogs.

### E2E

- Today drill-down.
- Work complete.
- offline work event.
- cancellation.
- harvest.
- QC.
- packhouse.
- close preview.
- trace.
- import dry-run.

### Browser widths

- 360.
- 390.
- 430.
- 768.
- 1024.
- 1440.

## 32. Migration from current field UI

Current files:

- `lotus_farm/public/field/index.html`
- `lotus_farm/public/field/app.js`
- PWA/service worker assets.

Do not delete first.

Parity checklist before redirect:

- session/capabilities.
- Farm/date bootstrap.
- Today KPIs.
- work result.
- all field event types.
- IndexedDB persistence.
- photo.
- GPS.
- sync/retry.
- capture_status reconciliation.
- QC.
- trace.
- import.
- map.
- close preview.

After parity + UAT:

1. `/lotus` becomes preferred route.
2. old field UI marked legacy.
3. keep fallback during pilot/hypercare.
4. remove only after cutover sign-off.

## 33. Definition of Done per screen

A screen is done only when:

- route exists;
- permission guard exists;
- loading/empty/error/no-permission exist;
- backend source identified;
- actions follow document state;
- server-side pagination used where needed;
- mobile behavior defined;
- acceptance test automated or in UAT matrix;
- trace links work;
- no duplicate business formula exists in Vue.

## 34. Recommended delivery order

### FE0

- scaffold.
- auth/session.
- router/layout.
- Frappe UI.
- ScopePicker.
- repository/error layer.

### FE1

- Today.
- Farm/Plot 360.
- Work read.
- Trace.
- Map read.

### FE2

- Work write.
- Labor.
- Material.
- Loss.
- Measurement.
- Harvest.

### FE3

- QC.
- Packhouse.
- Close.
- Import Center.

### FE4

- offline parity.
- PWA.
- GPS/photo/QR.
- performance/accessibility polish.

## 35. Non-functional requirements

- No secret in browser bundle.
- Same-site session by default.
- CSP compatible with Frappe deployment.
- server paging for large lists.
- lazy-load heavy modules/map.
- accessible keyboard focus for forms/dialogs.
- visible sync state.
- Vietnamese labels first; identifiers/code in detail only.
- audit/history reachable without editing data.
- frontend must survive backend permission denial gracefully.

## 36. Open business decisions

Frontend coding can start, but production sign-off still needs:

- official Farm/Lô/Thửa master.
- exact approval/reopen matrix.
- tolerance values.
- official grade/package/market masters.
- exact OneDrive source priority.
- device/scale operating rules.
- UAT device/browser list.
- SLA and concurrent-user target.

Các mục này phải cấu hình/khóa nghiệp vụ; không được “đoán cho chạy”.
