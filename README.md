# Lotus Banana Farm Manage

Custom Frappe/ERPNext app for Lotus banana farm operations.

## V0 goal

Answer one operational question reliably:

> For each farm and harvest period, how many kilograms are forecast, how much is saleable after defects and safety buffer, how much is already committed to Sales Orders, and how much remains available to promise?

## V0 scope

- Farm and farm block master data
- Bunch operations: cut bud, spray, bag, care, inspection
- Defect inspection
- Harvest forecast
- Sales Order allocation linked to submitted ERPNext Sales Orders
- Harvest actual and forecast variance
- Lotus Farm Settings
- Harvest Availability report with ATP and shortage summary
- Pure forecast calculation tests and GitHub Actions static checks

Not included in V0: QR per bunch, GIS, AI forecast, mobile app, full packing workflow.

## Core calculation

```
Gross Forecast
- expected defect
= Saleable Forecast
- safety buffer
= Safe Saleable
- committed Sales Orders
= Available to Promise (ATP)
```

If ATP is negative, V0 exposes the shortage instead of hiding it.

## Install

```bash
bench get-app https://github.com/nguyentrieu210/Lotus-banana-farm-manage.git
bench --site <site> install-app lotus_farm
bench --site <site> migrate
```

ERPNext is required. Configure harvest age, average bunch weight, defect rate and safety buffer from Lotus actual field data; V0 does not ship generic agronomy assumptions.
