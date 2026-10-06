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
- Manual Sales Order allocation linked to ERPNext
- Harvest actual and forecast variance
- Shared Lotus Farm Settings

Not included in V0: QR per bunch, GIS, AI forecast, mobile app, full packing workflow.

## Install

```bash
bench get-app https://github.com/nguyentrieu210/Lotus-banana-farm-manage.git
bench --site <site> install-app lotus_farm
bench --site <site> migrate
```

ERPNext is required.
