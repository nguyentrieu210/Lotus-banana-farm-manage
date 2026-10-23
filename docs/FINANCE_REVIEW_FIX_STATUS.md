# Finance review b1bf718 – repair status

Review: eight reproduced defects (four P1, four P2).

## Changes on this branch
- P1 Payment approval: native ERPNext Pay Payment Entry and signed cash Journal Entries now require all signatures with matching content hashes. Direct Journal Entries crediting configured cash/bank accounts are rejected. Accountant native submit grants are removed on migration.
- P1 Amount edited after signing: the next signer rejects a changed fingerprint and must return it for a new signing round.
- P1 Month closing: once Result Closing is posted, native writes and cancellations to that accounting month are blocked. Month lock checks that result closing was completed.
- P1 Inventory costing: when harvested bananas still remain in a warehouse, costing rejects the unsafe direct COGS adjustment. **This is a safety guard, not a completed revaluation solution.** It is not yet safe to auto-close such months; a Stock Reconciliation-based stock valuation that remains consistent with ERPNext Stock Ledger and lot-level 154 accounts still needs implementation and site testing.
- P2 Historical debt: reconcile dated GL with Payment Ledger Entry filtered by the same report date (not today's outstanding_amount).
- P2 Opening account 131: accepts an optional seventh column containing the Customer code; verifies the customer and fills the Journal Entry party.
- P2 Opening partial import: any error in the uploaded file invalidates the commit token.
- P2 Native cancellation: on_cancel reverses the corresponding Lotus Accounting Posting record and clears active_key. Direct cancellation of closing entries remains prohibited.

## Verification status
- Isolated regressions: tests/test_finance_review_regressions.py covers the security guards, dated debt query, opening import cases, and unsold stock safety.
- A real ERPNext/Frappe integration test is **not yet completed**.
- GitHub Actions quality reports failure on the branch, and the base main commit also reports failure. Job logs were unavailable via the connector, so these results are **not** a passing test result.
- Do **not** merge or deploy this draft until all eight behaviours are exercised on a disposable site and the batch / inventory revaluation path is completed.

## Production acceptance checks
1. Accountant tries direct Payment Entry Pay and cash-credit Journal Entry without director approval: both refused.
2. Chief signs 50,000; amount becomes 75,000; next signature refused.
3. Result closing posted; try dated new invoice, stock adjustment and final month lock: changes refused / lock checked.
4. Costing 10 kg harvested with 10 kg still stocked and a 100,000 variance: zero to COGS; valuation must increase correctly in 155 **and** ERPNext stock ledger before allowing close.
5. Past receivables/payables compared after a later payment still show their past-date balances.
6. Import opening 131 with customer: Journal Entry posts with party_type Customer.
7. File with one invalid row: no Journal Entry created for any of the file.
8. Cancel approved voucher via native ERPNext: Lotus link reverses and active_key cleared.
