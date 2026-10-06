# BRD implementation: planning hardening and measured packout

Source: “Lotus Farm — BRD 360° và thiết kế kỹ thuật cho custom app Frappe/ERPNext”, 6 October 2026. This change implements the first planning/traceability slice of the roadmap. It does not represent completion of the entire BRD or production acceptance.

## Implemented

| BRD requirement | Implementation |
|---|---|
| Farm owner Company | Required standard ERPNext Company link; packout Warehouse and Sales Order must match it |
| Approved profile versions | Submitted Harvest Profile is immutable; profile name/version has a database unique constraint |
| Forecast vintage | Submitted Harvest Forecast freezes profile coefficients, profile version, source document snapshot, formula version, calculation timestamp/user |
| Prevent duplicate source supply | One released forecast per cohort and overlapping harvest period, across all Items in this single-output pilot |
| SO Item allocation | Separate submitted Forecast Reservation for an exact Sales Order Item; same Item, Company, delivery window and Kg stock UOM |
| Concurrent reservation | Sales Order → forecast row locks; current locking reads for reserved totals, materialized totals and demand |
| Retry-safe commands | Versioned operation/reservation endpoints with unique event IDs and payload mismatch rejection |
| Actual immutability | Submitted Bunch Operation and Harvest Actual; cancel/amend lifecycle |
| Harvest lineage | Actual submit creates draft Harvest Lot on QC Hold; only one submitted lot per Actual |
| Raw lot consumption | Submitted packout source rows lock lots and cannot exceed previously unconsumed kilograms |
| Mass reconciliation | Input = all outputs (saleable, byproduct, waste) + recorded loss within site-owned absolute kg tolerance |
| Physical inventory | QC-released packout creates standard draft Material Receipt; standard ERPNext submission creates stock/GL |
| Batch lineage | Batch points to Packout Run; run source rows trace to Actual, cohort, cycle and block |
| Forecast/stock double counting | Stock Entry submit creates immutable Forecast Materialization; report subtracts retired forecast supply; cancellation reverses retirement |
| Availability access | Report uses permission-aware get_list; commands check document permissions; only submitted forecasts are published |
| Validation gates | Pure rule/schema tests, disposable v16 install/migrate integration workflow, separate-connection concurrency gate |

## Pilot limits and unfinished BRD work

- Stock UOM is `Kg`. Carton and other stock UOM reservations/posting are deliberately rejected until validated Item Mapping is implemented.
- A cohort has one finished Item forecast for a harvest period. Multiple grade outputs can be measured in packout, but multiple Item forecast yields from the same biological pool need a shared supply model before enabling them.
- The receipt bridge recognizes finished fruit for the first time in ERP stock. It must not be used if raw fruit has already been received into ERP inventory. Repack/Manufacture, packaging and full production costing require a separate finance-approved route.
- Physical materialization retires safe forecast kg proportionally to raw input / frozen released-raw forecast. Retirement is capped at the remaining safe supply. Lower actual harvest can leave residual projected supply: controlled closing/superseding a forecast after the final harvest is still required.
- Future reservations remain active after stock receipt until explicitly released. Automatic conversion to standard ERPNext Stock Reservation and Delivery Note consumption is NOT implemented. This is conservative (may show shortage) and must not be described as the complete farm-to-delivery scenario.
- Profile/forecast submission is manager approval in this pilot. Multi-role workflows, distinct approval actions, override with expiry, farm operator roles and farm isolation tests remain incomplete. Only the existing System Manager access is granted to the new DocTypes.
- Quality Standard, structured defect occurrence lines, versioned customer specifications and Packout Profile remain open. QC Hold/Released is a manual manager decision, not an automated quality assessment.
- Immutable scale/device readings, calibration proposals, vintage WAPE/Bias, legacy import tooling, GIS geometry versions, photo rules, offline UI, outbox/webhook retry, QR, backup/restore gates and multi-farm UAT remain open.
- Integration and concurrency tests require a real disposable Frappe/ERPNext site. Passing pure tests alone is not proof they passed.

## Existing-site migration

1. Back up the site/database and test this change on a restored disposable copy first.
2. Map every existing Farm to its correct ERPNext Company. No Company is guessed by this change.
3. Check duplicate Harvest Profile name/version pairs before adding the unique constraint. Resolve collisions by assigning explicit new versions, retaining the original evidence.
4. Existing Bunch Operations, profiles, actuals and forecasts remain drafts; migration does not silently approve them or fabricate immutable historical snapshots.
5. Review and submit the profiles and source operations. Set a valid finished Item on each forecast; retain original exported forecast evidence before reviewing/submitting.
6. Existing order-level Forecast Allocation child rows remain stored as read-only evidence. Export/reconcile them by exact Sales Order Item, clear them explicitly in a reviewed migration, then use Forecast Reservation. No automatic guess is made for ambiguous orders or units.
7. Reconcile original commitments, revised safe supply and current ERP stock before accepting new reservations.
8. Test receipt valuation, Stock Ledger and GL with Finance; only then enable the first-receipt route in a pilot.

Do not deploy into a live site until these checks and the outstanding production gates have been completed.

## Verification

Local:

```bash
python -m unittest discover -s tests -v
python -m compileall -q lotus_farm
```

Disposable ERPNext v16 site (Python 3.14, Node 24, MariaDB 11.8):

```bash
bench --site lotus_test install-app lotus_farm
bench --site lotus_test migrate
bench --site lotus_test set-config allow_tests true --parse
bench --site lotus_test run-tests --app lotus_farm --module lotus_farm.tests.test_integration
bench --site lotus_test execute lotus_farm.tests.concurrency.run
```

The concurrency command commits disposable fixtures and opens two independent connections. Never run it against live business data.
