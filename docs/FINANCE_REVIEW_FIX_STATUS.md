# Finance repair release — review b1bf718

## Safety fixes (P1)
1. Native ERPNext payment submission requires the whole approved signature chain; ordinary accountants have native Payment Entry/Journal Entry submit permissions removed.
2. Re-signing rejects changed voucher fingerprints (including 50,000 -> 75,000).
3. Posting after result close is refused at the ERPNext server; month close checks closing results.
4. Pricing variance MUST NOT enter COGS 632 while harvested product remains in any warehouse (including transfers). This patch safely refuses closing such costing runs. **Automatic stock revaluation on 155 is not implemented**. To finalize a month with unsold bananas, a follow-up ERPNext Stock Ledger-based valuation workflow is required; never bypass this guard by making a manual Journal Entry to 155.

## Other fixes (P2)
5. Historical payable/receivable reconciliation uses the dated Payment Ledger; payable amounts have the ERPNext positive convention.
6. Opening account 131 accepts Customer code in an optional seventh column and Journal Entry party_type=Customer.
7. An opening spreadsheet containing invalid or unbalanced rows gets no commit token; no partial posting.
8. ERPNext native cancellations mark the Lotus Accounting Posting link Reversed and release the active key.

## Verification
- Windows host ran tests against production base image without connecting to the live site: 241 Python unit tests passed, including finance regressions. Frontend tests: 430 passed. Vite production build: passed.
- Local live site is named frontend. Backup copied outside Docker volume to C:/code/Lotus-live-backups/20261023_124621-frontend-* before deploying.
- GitHub Actions jobs were failing within a few seconds on both the old main and the fix branch, so their result is not considered a valid integration pass.
- No direct production financial transactions were inserted by these tests.

## Remaining requirement
For genuine end-to-end automatic costing, implement and verify valuation transfer from 154 to stock account 155 via ERPNext Stock Ledger, with sold portion only in 632 and batch-level, warehouse-level and lot-level tests. Do not claim this step is complete or turn off the protective refusal.
