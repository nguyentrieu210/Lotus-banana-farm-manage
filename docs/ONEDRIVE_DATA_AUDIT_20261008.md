# OneDrive data audit — 08/10/2026

Result: **not ready for complete import**.

Actions evidence: https://github.com/nguyentrieu210/Lotus-banana-farm-manage/actions/runs/37725102482
Validated commit: a8987b8fa766cf3cceeb4cd41c4d3ec3e8ee16db
Audit script: scripts/audit_onedrive_values.py
Detailed JSON and row examples: the onedrive-data-audit artifact on that run.

## Sources and coverage

| Fixture | Original workbook | Source date modified | Extracted sections |
| --- | --- | --- | ---: |
| labor.csv | XNC_BC nhân sự hằng ngày.xlsx | 02/09/2025 | 17 |
| plots.csv | DATALO BAO CAO NGAY - XN CHUOI.xlsx | 05/10/2026 | 7 |
| materials.csv | 20250321_File master vật tư quý II xí nghiệp chuối BP1.xlsx | 29/05/2025 | 20 |
| reasons.csv | Nguyên nhân hủy chuối.xlsx | 22/05/2025 | 3 |

Files were read from the connected OneDrive. Fixture content is the complete text extraction returned by the connector, including form-feed section separators and CSV export row indexes. Section positions are explicit; original sheet names are not available in the extraction. These are historical user source files, not verified Lotus production data. No source file was changed.

## Verified results from Actions

| Check | Result |
| --- | --- |
| Detailed labor source table | 32,616 extracted rows; exceeds current 10,000-row XLSX sheet import limit |
| Negative labor counts | 3,078 detail rows contain negative headcount/present/absent values |
| Labor balance | 125 complete detail rows do not satisfy headcount = present + absent |
| Missing labor counts | 12,627 detail rows have at least one blank required count; requires review, not automatic zero |
| Plot plant counts | 306 rows have fractional current plant quantities; separate estimated/planned quantities from counted plants before integer import |
| Material source rows | 5,590 rows inspected; quantities aggregated separately by source unit, never added across kg/tấn/lít |
| Cancellation category total | The single populated example has 218 bunches, matching its category sum |
| Cancellation reason master import | Defect Reason is absent from the current import target allowlist |

Example: labor for 01/11/2024, XNC-BP1, BP1B, Công nhân cân has 45 current workers, 48 present, and -3 absent. This requires a business explanation/correction before import.

## Limits and next work

- Original XLSX downloads returned HTTP 403. The audit cannot verify original formulas, cached formula freshness, merged cells, external links, exact Excel row numbers or raw-file hashes. CSV hashes cover the extracted fixture bytes only.
- Actions data-readiness intentionally failed with exit code 2 after writing the report. This is a data-readiness finding, not a Python crash.
- The separate ERPNext rerun checks the existing generated integration fixtures. It does not prove these four workbooks were imported into ERPNext.
- Live app-to-OneDrive authentication was not exercised. Connector access and the app's client-credentials feed are separate connections.
- Split approved labor sources into batches; define organization, work-category, item, unit and reason mappings; review negative/imbalanced counts and fractional planned plant counts; then run raw-XLSX staging, preview and reconciliation on disposable ERPNext.
- Never amend historical source values, convert unknown blanks to zero, round plant counts or auto-approve mappings merely to make the test green.
