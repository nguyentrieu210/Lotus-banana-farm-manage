# Lotus Banana Farm Manage

Custom Frappe/ERPNext app for Lotus banana farm operations.

## ProMax operating model

Company → Farm → Farm Block → Farm Plot → Crop Cycle → Sucker Selection Batch.

Daily Work Plan links land and tasks to labor, versioned material norms, actual results, consumption/recovery and a blocking Daily Production Close. Incoming QC gates packout; cancellations reduce current ATP while preserving released snapshots. No Xí nghiệp DocType or parallel stock ledger is introduced.

See [ProMax implementation](docs/PROMAX_IMPLEMENTATION.md) for setup, migration, operating steps, BRD naming and remaining acceptance work.

## Forecast pipeline

V1 forecasts the quantity that can realistically be committed, not just gross field weight:

```
Source bunch qty
x bunch survival rate
= expected harvest bunches

x average bunch weight
= gross bunch kg

x quality pass rate
= saleable field kg

x packout rate
= packed/exportable kg

x (1 - safety buffer)
= safe commit kg

- committed Sales Orders
= Available to Promise (ATP)
```

Harvest Profile stores versioned assumptions such as average bunch weight, survival, quality pass, packout, safety buffer, and cut-bud-to-harvest days. These values must be calibrated from Lotus actual data; the app does not ship generic banana agronomy coefficients.

## V1 master data

- Farm
- Farm Block
- Banana Variety
- Crop Cycle
- Harvest Profile
- Defect Reason

## V1 transactions

- Sucker Selection Batch
- Bunch Operation
- Defect Inspection
- Harvest Forecast
- Forecast Allocation
- Harvest Actual

For `Harvest Forecast`, `Forecast Basis = Cut Bud Operations` automatically sums net cut-bud bunches whose expected harvest date falls inside the forecast period. Manual basis remains available for early pilots and reconciliation.

## ERPNext boundary

ERPNext remains responsible for standard commercial and inventory objects such as Item, Customer, Sales Order, Warehouse, Stock, Delivery and Finance. Lotus Farm adds farm-specific production and forecast context and links forecast allocation to submitted ERPNext Sales Orders.

## Not yet included

The BRD implementation branch adds immutable released forecasts, atomic SO Item allocations, versioned QC, traced harvest lots, reconciled Packout Runs, immutable scale readings, the ERPNext Repack bridge and ProMax daily operations. Source staging records do not mean Lotus historical data has been imported.

See [BRD implementation and readiness](docs/BRD_IMPLEMENTATION.md) for migration steps, APIs, verification and the remaining enterprise requirements. Early supply can now be revised from Sucker Selection → Shooting → Cut Bud evidence without double-counting the same cohort. One biological forecast can also split finished supply across multiple approved Items without duplicating the source crop. QR, GIS, offline mobile and automatic delivery fulfilment are not completed.

## Install

```bash
bench get-app https://github.com/nguyentrieu210/Lotus-banana-farm-manage.git
bench --site <site> install-app lotus_farm
bench --site <site> migrate
```

ERPNext is required. Runtime installation on a real Frappe site is still required before calling this production-ready.


## Tests

Pure checks without a Frappe installation:

```bash
python -m unittest discover -s tests -v
```

On a **disposable** ERPNext v16 site:

```bash
bench --site lotus.test run-tests --module lotus_farm.tests.test_brd
```

The site suite includes a concurrency test with committed test fixtures. Never run it on production. The GitHub `Lotus BRD checks` workflow provisions that disposable site and migrates twice.
