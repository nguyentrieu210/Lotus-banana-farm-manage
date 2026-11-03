# Vietnamese release — 2026-11-03

The PO files retain the message IDs and contexts of the installed application
versions. Only translations were merged from the official upstream Vietnamese
catalogs, then completed using the supplemental application CSV and checked for
format placeholders, template variables and link attributes.

Upstream sources:

- https://github.com/frappe/frappe/blob/develop/frappe/locale/vi.po — Git blob `f8ac95780956f8620cc2d3dc6a368c2cd1c5827e`
- https://github.com/frappe/erpnext/blob/develop/erpnext/locale/vi.po — Git blob `370ea1e2017313b1cd0a125d2c8d8b216799093c`
- https://github.com/frappe/hrms/blob/develop/hrms/locale/vi.po — Git blob `170c7aca98fb7d2d8743ba92fda150ed1227717c`

These Git blob IDs identify the fetched files, rather than repository commits.
The corresponding current source locations are the same paths on `develop`.
Preserve each source catalog's existing copyright and license notices.

Catalog coverage: Frappe 6,340; ERPNext 10,300; HRMS 2,172 nonempty messages.
The metadata audit covered 819 doctypes and 7,462 UI strings across both sites.
The final frontend audit also covers 354 filter captions/choices in 179 DML reports.
The DML repository's `translations/vi-reports.csv` supplies report captions absent
from upstream, and both packs use Vietnamese stock-unit, serial-number and batch labels.
Remaining untranslated human UI strings: zero in that captured inventory.
Technical IDs, document codes, numbering series, brands and format identifiers
remain unchanged. This inventory is a bounded check, not a claim about arbitrary
future records or third-party error messages.

`final-catalog-stats.json` records the 15 literal-percent labels for which Babel
mistakes prose such as "% of" for printf syntax. Genuine format placeholders
are checked. Compiled GNU gettext catalogs were read back and matched against
the source catalogs.

Deployment uses `Dockerfile.vietnamese-release` from exact Lotus/DML git archives
and the tested frontend builds, with the verified previous release as its base.
Compile only Vietnamese catalogs using `frappe.gettext.translate.compile_translations`
after switching the application image. No application/schema upgrade is needed.

For **each** backed-up site, first run
`lotus_farm.vietnamese.install_vietnamese` with its default `dry_run=True`.
Then execute with `dry_run=False` and a unique `audit_id` to import native
Translation records, set System Settings language to `vi`, and set enabled users'
language preference to `vi`. Templates that native Translation HTML validation
would modify stay in the PO/frontend catalogs. Protected per-site audit files
allow `lotus_farm.vietnamese.rollback_vietnamese(audit_id=...)` to restore only
this operation's translations and language preferences.

`Accounts` is **Kế toán**, `Account` is **Tài khoản kế toán**, and `Bank Account`
is **Tài khoản ngân hàng**. Frontend captions are translated separately from
stored Select values, DocType keys, document names and permissions.
