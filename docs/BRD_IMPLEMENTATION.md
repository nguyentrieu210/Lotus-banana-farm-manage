# Lotus BRD implementation — first executable tranche

Source: “Lotus Farm — BRD 360° và thiết kế kỹ thuật cho custom app Frappe/ERPNext”, created 2026-10-06. Baseline main: `2c57b1246204273c5e339249df9ddd0e3f82e2ef`.

This change implements the planning and field-to-packhouse core. It does **not** complete the enterprise/production BRD. Upstream Frappe/ERPNext `version-16` is the integration target; its Python requirement was checked as >=3.14,<3.15. The app's existing v15–v16 metadata remains, but only the v16 site workflow is supplied here.

| BRD requirement | Code in this change | Verification / remaining work |
|---|---|---|
| Farm belongs to Company | Required Company Link, linked warehouse/cost-center validation | Existing Farms must be mapped; no guessed Company migration |
| Block/Cycle/Cohort identity | Unique DB indexes, used identity guards, operation date checks, ratoon cohort validation | Real site suite included; not locally executed |
| Versioned agronomy assumptions | Approved profile/version immutable, explicit rates, cycle variety used | No automatic agronomy coefficients |
| Immutable forecast history | Draft → Released, full source/profile/formula snapshot + hash, explicit superseding revision | Single output Item per forecast; multi-grade forecast vector not implemented |
| Released future supply | Only submitted Cut Bud source records; manual basis needs explanation | Sucker/Shooting forecast bases remain follow-up work |
| Exact SO Item allocation | Validated row, Item, Company, delivery date, stock-UOM Kg conversion | Requires standard ERPNext Sales roles and submitted order |
| Atomic future reservation | Lock SO then forecast; check all future allocations + physical stock reservations | Real two-connection concurrency test included; not locally executed |
| Allocation retry safety | Mandatory client event ID + immutable event result | Same ID/different payload rejected |
| Field QC | Approved/versioned standard; distinct defective units vs defect occurrences; required measurements | Per-parameter sampling statistics and photo evidence not implemented |
| Harvest actual → lot | Submitted actuals; reconciled contributions; cannot consume actual weight twice | Input lot can contain multiple actual sources within a Farm |
| Lot → packout | Locked input lots, QC release role, per-output standards, Kg mass balance | Packing line/labor/cost analytics not implemented |
| Raw scale evidence | Immutable reading, device/reading key, tare validation, idempotent API | Device allowlist/auth binding, physical scale linkage still needed; timestamp inputs normalize to site timezone |
| ERPNext stock bridge | Idempotent Batch creation and **draft Repack Stock Entry** from received raw stock | Warehouse user must review/submit standard ERPNext entry; no custom ledger/GL |
| Physical supply replacement | Stock Entry submission reduces remaining forecast ATP by traced finished output | Site test covers stock/GL creation and forecast replacement |
| Reviewed reversal/reconciliation | Submitted Supply Reconciliation snapshots the exact reversal effect; direct Lotus-linked Stock Entry/SRE cancel is blocked; approved execution uses ERPNext cancel then updates Lotus trace state | Delivered/consumed physical reservations still require downstream delivery reconciliation first |
| Forecast → stock reservation | Explicit link to submitted SRE matching SO Item; removes future commitment | Whole-allocation linking only; partial transitions and delivered-consumption audit remain |
| Farm data isolation | Fail-closed Farm grants, list/document/write checks | Full API/file/export/Company permission matrix remains |
| Profile learning | Weighted kg/bunch and field-release proposal from matched submitted actuals | No auto-approval; persisted calibration runs, holdout backtests/vintage report remain |
| Availability | Permission-aware API returns traced Item/cohort periods, signed ATP/shortage | Existing Desk availability report now filters released Item supply and Farm permissions; full workspace remains |
| Real install/migrate checks | GitHub workflow builds ERPNext v16, installs app, migrates twice, runs site tests | CI must pass before merging/pilot |

## Metric contracts

`source × survival × kg/bunch = gross harvest kg`.

`gross × field-release = released raw kg`.

`released raw × packout yield = expected finished Item kg`.

`expected finished × (1 − safety buffer) = safe commit kg`.

Remaining future supply = max(safe commit − traced posted output, 0). Future ATP = remaining future supply − Reserved future allocations. ATP remains negative when commitments exceed remaining supply. ERPNext separately owns physical inventory and physical reservations.

Field rejection is applied once. A buồng with two defects is still one defective unit. Packout balances input against finished net kg + reject + other recorded loss; tolerance is an explicit site setting, defaulting to zero.

## Existing-data upgrade

1. Back up the site and restore a staging copy.
2. Install/migrate this branch. Existing Company-less Farm records are preserved; assign their actual Company before use.
3. Existing profiles gain `version=1`, `approval_state=Draft`. Confirm coefficient meaning/scope, then approve an explicit version. Rates do not ship with 100% assumptions.
4. Existing operations and actuals remain Draft. Review and submit legitimate records before using them as forecast/lot sources.
5. Existing forecasts remain Draft. Do not delete their legacy allocation rows. Reconcile each row to the exact submitted SO Item and its outstanding Kg demand, then create a separate released forecast and reserve through the API. This branch intentionally refuses to guess row mappings or turn legacy totals into active reservations.
6. Resolve duplicate `(farm, block_code)`, `(block, cycle_no)` or profile key/version values before unique-index migration. No silent merge/deletion.
7. Grant each business/API user an explicit Farm User Permission and the necessary standard ERPNext roles. System Manager alone does not approve Lotus assumptions or gain access to every farm; Administrator is the bootstrap exception.
8. Enable ERPNext Stock Settings “Activate Serial / Batch No for Item” before creating traceable Items. Receive physical raw fruit through standard ERPNext stock documents with Finance-approved valuation. Map raw Item/Warehouse/Batch to the lot before creating a Repack draft. Lotus forecast records never create stock.

## API examples

Call authenticated Frappe method endpoints under `/api/method/`:

| Method | Required inputs |
|---|---|
| `lotus_farm.api.create_operation` | client_event_id, farm, farm_block, crop_cycle, operation_date, operation_type, bunch_qty; ratoon also needs sucker_selection_batch |
| `lotus_farm.api.ingest_scale` | farm, device_id, reading_id, captured_at, gross_kg, tare_kg |
| `lotus_farm.allocations.reserve` | forecast, sales_order, sales_order_item, qty_kg, client_event_id |
| `lotus_farm.allocations.release` | forecast, allocation |
| `lotus_farm.stock_bridge.make_repack_entry` | submitted packout name |
| `lotus_farm.stock_bridge.link_stock_reservation` | forecast, allocation, stock_reservation |
| `lotus_farm.reconciliation.execute` | submitted Supply Reconciliation name |
| `lotus_farm.api.availability` | period_start, period_end; optional Farm/Item |
| `lotus_farm.learning.propose_profile` | matching farm/block/cycle and historical from_date/to_date |

Side-effect commands only allow POST. Permission checks still apply; an API token is not an administrator bypass. Command authorization is held in server context, never trusted from client-supplied document flags.

## Deliberate pilot limits

Do not use this branch for unattended stock/accounting operations. Lotus-linked Repack and physical-reservation cancellation now require a submitted reviewed Supply Reconciliation, and execution still delegates the actual cancellation to standard ERPNext permissions and accounting/stock validation. Reservations with delivered, consumed or transferred quantity remain blocked until downstream delivery reconciliation exists. No automated Delivery Note creation/consumption, approved overcommit override, offline mobile queue, GIS boundary versioning, photo retention, outbox/webhook delivery, legacy importer, production backup/restore or performance proof exists yet.

The site test is for a disposable test database. Its concurrency test commits test fixtures so two independent connections can see them; never run it on a live business site.

## Validation evidence

Executed locally: 22 pure formula/schema/server-guard tests (including 4 original forecasting tests), Python compilation and Ruff F/E9 checks. These do not prove installability, DB concurrency, Farm permission isolation or accounting reconciliation. The separate site suite covers actual document lifecycle, reservation limits/retries, lot/packout overspend, approved-profile immutability, farm grants and two-connection allocation concurrency. Those tests require the provisioned ERPNext site and must pass in CI; no passing site result is claimed in this document.
