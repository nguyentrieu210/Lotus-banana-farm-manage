# Lotus workspace

The mobile console, warehouse and assignment entry points share `WorkspaceBar`,
theme tokens and `compact.css`. Desktop tables use a shared 36 px AG Grid theme
and the version-matched Vietnamese locale. Phones keep larger touch targets and
record lists. The sidebar and light/dark preference persist in local storage and
update across tabs. The header exposes permitted navigation, command search
(Ctrl/Cmd K, arrows, Enter, Escape), account information and logout.

The red header spans the full main area, meets the dark sidebar without a gutter,
and is 50 px tall. A divider separates the sidebar brand from navigation.
Red accents distinguish primary actions and key values.
Excel-style checkbox filters collect values before pagination from all records
within the user's current scope. Link choices and filters use native popovers
so they remain visible and interactive above dialogs.

Warehouse setup supports editing items, leaf item groups and warehouses.
Deletion uses native permissions and reference checks. Stock documents can be
deleted only while drafts; edits check the original modification timestamp.
Minimum stock is stored per warehouse in the hidden Item JSON field
`lotus_minimum_stock`; this does not create automatic purchase requests.
Shortage is calculated per warehouse before aggregation. The integration check
creates temporary masters, verifies minimum stock and draft edits/deletion, and
rolls back all changes.

Stock receipt rates are per stock unit and in the selected company's currency.
Additional expenses require positive amounts, descriptions and readable,
enabled, non-group Expense accounts belonging to that company and currency.
ERPNext allocates costs by basic item value and updates valuation on submission.
The simple form rejects additional costs with a zero allocation basis. Other
stock operations cannot pass receipt costs. Supplier payable invoices remain
separate from stock receipts.

The receipt integration check uses a database transaction that is rolled back:
two incoming lines at 100,000 each plus 50,000 expenses allocate 25,000 to each
line; stock value becomes 250,000. Unit costs are 12,500 and 25,000, and a
subsequent issue of two units from the first line uses 25,000 of stock value.
Unit tests cover invalid amounts, allocation basis, account company/currency,
permission checks, unsupported operations and dialog dismissal boundaries.
