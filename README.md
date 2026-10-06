# Lotus Banana Farm Manage

Custom Frappe/ERPNext app for Lotus banana farm operations.

## V1 operating model

V1 separates permanent land master data from production cycles and daily cohorts:

```
Farm
  -> Farm Block
      -> Crop Cycle
          -> Sucker Selection Batch (Cycle 2+ cohort by selection date)
              -> Bunch Operation
              -> Defect Inspection
              -> Harvest Forecast
              -> Harvest Actual
```

This is intentional: Cycle 1 is anchored by planting date, while ratoon cycles are tracked through actual sucker-selection batches. A block can therefore have several selection cohorts on different dates without forcing one artificial "Cycle 2 date".

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

V1 does not yet include QR per bunch, GIS, AI prediction, mobile app, automated Sales Order item-to-farm matching, or a full packing transaction workflow.

## Install

```bash
bench get-app https://github.com/nguyentrieu210/Lotus-banana-farm-manage.git
bench --site <site> install-app lotus_farm
bench --site <site> migrate
```

ERPNext is required. Runtime installation on a real Frappe site is still required before calling this production-ready.
