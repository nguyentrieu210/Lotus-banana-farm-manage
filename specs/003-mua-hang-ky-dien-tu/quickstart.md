# Quickstart: kiểm chứng spec 003

Hướng dẫn chạy để chứng minh tính năng hoạt động. Endpoint xem [contracts/api.md](contracts/api.md); trạng thái và trường xem [data-model.md](data-model.md).

## 1. Chuẩn bị

1. **Mã:** worktree `C:\code\lotus-003-mua-hang`, nhánh `003-mua-hang-ky-dien-tu`. Không làm trong `C:\code\lotus-local-test-20261104\app`, vì cây đó đang dùng cho spec 002.
2. **Frontend:**
   ```bash
   cd /c/code/lotus-003-mua-hang/frontend && npm ci
   ```
3. **Container thử** từ image đang dùng cho bản local, gắn mã của worktree, nối vào mạng của bộ `lotus-vps-test`:
   ```bash
   MSYS_NO_PATHCONV=1 docker run -d --name lotus-003-test \
     --network lotus-vps-test_frappe_network \
     -v lotus-vps-test_sites:/home/frappe/frappe-bench/sites \
     -v C:/code/lotus-003-mua-hang:/home/frappe/frappe-bench/apps/lotus_farm \
     -p 127.0.0.1:8098:8000 lotus-local-test:20261104 sleep infinity
   ```
4. **Site thử riêng `mua.test`**, khôi phục từ bản sao lưu mới nhất của site `frontend`, rồi chạy `bench --site mua.test migrate` trong `lotus-003-test`.
   - Không migrate site `frontend`.
   - Không chạy `bench build`, vì thư mục `sites/assets` dùng chung.
5. **Tắt gửi thật** trên `mua.test`: thông báo đẩy và email (`mute_emails = 1`) trong site config.

## 2. Kiểm thử tự động

> Từ 10/11/2026 các bộ test không chạy trên máy làm việc. Chạy trên VPS ở thư mục thử riêng `/opt/lotus-003-test/app` (bản chép của worktree) với bộ dùng-rồi-bỏ `lotus-003-proc` (CSDL riêng, site `procurement.test`, dựng bằng `IMAGE=lotus-release:<bản đang chạy> tools/test_site_procurement.sh site`), hoặc trên GitHub Actions. Không chạy trên site thật.
>
> Kết quả 10/11/2026 trên VPS: frontend 677/677; `verify_procurement` 23/23; `verify_procurement_complete` 34/34; `verify_purchase_flow` 22/22; `verify_procurement_concurrency` 4/4. Các script dùng bản sao site thật (`verify_signing.py`, `verify_purchase_proposal.py`, `verify_vat_in_cost.py`) chạy lần cuối trên `mua.test` ở máy làm việc trước khi có quy định này.


| Loại | Lệnh | Kỳ vọng |
|---|---|---|
| Quy tắc thuần | `docker exec lotus-003-test bash -lc "cd apps/lotus_farm && python -m unittest discover -s tests -v"` | Qua hết, gồm các test mới: `test_purchase_status`, `test_proposal_rules` (giai đoạn), `test_signing_rules` (chuỗi `purchase_receipt`, bước kiểm tra), `test_procurement_rules` (tuổi nợ, ngưỡng tổng in) |
| Tích hợp | `docker exec -e SITE=mua.test -e LOTUS_PROCUREMENT_TEST_ONLY=1 lotus-003-test bash -lc "cd sites && python ../apps/lotus_farm/tests/integration/<script>.py"` | Mỗi script in OK và rollback dữ liệu tạm |
| Frontend | `cd frontend && npm test && npm run build` | Qua hết; build không lỗi |
| DOM điện thoại | `MOBILE_UX_HAPPY_DOM=frontend/node_modules/happy-dom/lib/index.js node tools/verify_mobile_purchase_dom.mjs` | Không tràn ngang ở 320, 390, 844 px |

Các script tích hợp cần chạy:
- `verify_signing.py`, `verify_signing_inbox.py` (mới), `verify_signed_copy.py` (mới);
- `verify_purchase_proposal.py`, `verify_purchase_flow.py`;
- `verify_procurement.py`, `verify_procurement_complete.py`, `verify_procurement_concurrency.py`;
- `verify_finance.py`, `verify_vat_in_cost.py`, `verify_receipt_reason.py`, `verify_statements.py`;
- các script kho trước đây dùng `lotus_policy_approved`.

## 3. Kịch bản tay trên site thử

Dùng 6 tài khoản thử, có ảnh chữ ký và ký nháy:
- người đề xuất (tổ trưởng);
- trưởng bộ phận;
- mua hàng/kế toán;
- kế toán trưởng;
- giám đốc;
- thủ kho.

Điện thoại thử bằng Chrome ở chế độ thiết bị 390 px và 320 px; máy tính ở 1440 px.

### US1: Ký điện tử

1. Giám đốc bật thông báo trên app Mua hàng. Kế toán lập phiếu chi trả 1 hóa đơn rồi ký bước 1.
   - Kỳ vọng: không lỗi; kế toán trưởng nhận thông báo; bấm thông báo mở đúng tấm ký phiếu chi.
2. Kế toán trưởng ký, rồi giám đốc ký trên điện thoại.
   - Kỳ vọng: phiếu được ghi sổ; người lập nhận "Đã ký đủ"; có một `Lotus Signed Copy`.
   - Quét QR trên PDF: trang `/verify/lotus` báo khớp bản lưu.
3. Tạo 3 đề xuất và 2 phiếu chi cùng chờ giám đốc. Mở `/lotus/cho-ky` trên máy tính.
   - Kỳ vọng: 5 dòng, đủ cột như contract.
   - Chọn cả 5, bấm Ký nhiều, xác nhận một lần: kết quả từng dòng hiện riêng. Làm một dòng cố ý lỗi (sửa chứng từ ở tab khác): dòng đó báo lỗi, 4 dòng kia vẫn ký.
4. Trưởng bộ phận không có quyền xem danh sách đề xuất, nhưng được chỉ định ký.
   - Kỳ vọng: thấy và ký được từ Chờ tôi ký trên app Công việc.
5. Chuyển người ký bước 2 sang người khác, có lý do.
   - Kỳ vọng: người mới nhận thông báo; lịch sử có sự kiện REASSIGN.
6. Đổi ảnh chữ ký của giám đốc, mở lại PDF ở bước 2.
   - Kỳ vọng: PDF vẫn mang ảnh cũ.
7. Mở email "Đến lượt bạn ký" trên máy tính.
   - Kỳ vọng: link `/lotus/mo` mở màn máy tính. Trên điện thoại cùng link mở app điện thoại.

### US2: Bảng đề xuất mua

1. Thủ kho lập đề xuất 5 dòng trên app Kho điện thoại.
   - Kỳ vọng: cùng form đầy đủ như app Mua hàng; gửi xong mở chi tiết.
2. Đề xuất nhập từ Excel chưa có lý do: khi ký gửi, hộp ký hỏi lý do.
3. Ký đủ 4 bước (2 trên máy tính, 2 trên điện thoại), lập đơn cho 3 dòng, nhận đủ 3 dòng, rồi Đóng phần chưa mua kèm lý do.
   - Kỳ vọng: "Đã nhận đủ". Lập hóa đơn cho phần đã nhận thì chuyển "Đã xong".
   - Số đếm từng giai đoạn trên bảng đúng ở mọi bước.
4. Hủy một đề xuất chưa có đơn: phải có lý do, sang "Đã hủy". Đề xuất đã có đơn thì không hủy được.

### US3: Đơn mua

1. Nhập 2 báo giá cho một đề xuất. Trên điện thoại chọn NCC A giá 120.000 đ, rồi Lập đơn từ đề xuất.
   - Kỳ vọng: đơn có sẵn NCC A, 120.000 đ.
2. Thêm một dòng ngoài đề xuất rồi lưu.
   - Kỳ vọng: hiện cảnh báo dòng đó ngay khi lưu.
3. Gửi duyệt. Giám đốc trả lại trên máy tính; sửa đơn; giám đốc duyệt trên điện thoại.
   - Kỳ vọng: lý do trả lại hiện ở cả hai giao diện; đơn duyệt có PDF lưu; "In đơn mua" mở bản đó.
4. Chọn giá rẻ nhất từ đề xuất đã ký đủ.
   - Kỳ vọng: đơn vẫn ở "Chờ duyệt", không tự duyệt.
5. Gọi submit đơn qua REST bằng một tài khoản có vai trò duyệt nhưng không phải người được chỉ định.
   - Kỳ vọng: bị chặn.
6. Đánh dấu Đã gửi NCC, rồi NCC đã xác nhận.
   - Kỳ vọng: danh sách hiện đúng trạng thái. Hủy đơn chưa nhận: các dòng đề xuất quay lại "Chờ mua".

### US4: Nhập kho

1. Thủ kho nhận 60/100 bao trên điện thoại, kèm 2 ảnh và chữ ký tay người giao.
   - Kỳ vọng: phiếu "Đã nhập kho" mang chữ ký thủ kho; có bản PDF lưu; đơn còn chờ 40.
2. Bấm xác nhận khi chưa có chữ ký người giao và chưa có ảnh phiếu giao.
   - Kỳ vọng: bị chặn và có lời nhắc.
3. Hai trình duyệt cùng nhận 40 bao còn lại.
   - Kỳ vọng: chỉ một bên thành công; bên kia nhận "Còn nhận được 0".
4. Trả 5 bao trong app.
   - Kỳ vọng: phiếu trả ghi sổ ngay. Nếu đã có hóa đơn: có lời nhắc lập hóa đơn điều chỉnh.
5. Ngắt mạng lúc bấm xác nhận, bật lại rồi bấm lần nữa.
   - Kỳ vọng: chỉ có một phiếu.

### US5: Hóa đơn NCC

1. Hóa đơn chờ nhập có 2 phiếu nhận của NCC A (một phiếu đã có file PDF hóa đơn) và 1 phiếu Mua nhanh.
2. Lập hóa đơn cho 2 phiếu nhận, với thuế 5% và 8% xen nhau và phí vận chuyển, gõ tổng in.
   - Kỳ vọng: file gốc hiện cạnh form; tổng khớp; không có bút toán 1331; giá vốn gồm thuế.
3. Đổi đơn giá một dòng thành 125.000 đ (đơn mua 120.000 đ).
   - Kỳ vọng: phải ghi lý do lệch.
4. Nhập lại cùng NCC + ký hiệu + số ở màn Tài chính.
   - Kỳ vọng: bị chặn trùng.
5. Hủy một hóa đơn đã có phiếu chi.
   - Kỳ vọng: bị chặn, kèm hướng dẫn. Hủy hóa đơn chưa thanh toán: được, có lý do; phiếu Mua nhanh liên quan lập lại hóa đơn được.

### US6: Công nợ và trả tiền

1. NCC có 3 hóa đơn (1 quá hạn 40 ngày), 1 phiếu nhận chưa có hóa đơn, 1 tạm ứng. Xem công nợ ngày chốt hôm nay trên máy tính và điện thoại.
   - Kỳ vọng: nhóm tuổi nợ đúng; "hàng đã nhận chưa có hóa đơn" tách riêng; phép đối chiếu với sổ cái 331 và 3388 + 33881 lệch 0.
2. Chọn 2 hóa đơn, lập phiếu chi chuyển khoản có số tham chiếu và ảnh ủy nhiệm chi, ký đủ 3 bước.
   - Kỳ vọng: hóa đơn chuyển "Đã trả"; công nợ giảm; in giấy đề nghị chi có chữ ký và QR.
3. In biên bản đối chiếu từ 01/10 đến hôm nay.
   - Kỳ vọng: số đầu kỳ, phát sinh, cuối kỳ khớp sổ chi tiết.
4. Bấm phiếu chi trong phần tiến độ của đề xuất.
   - Kỳ vọng: mở đúng phiếu chi.

## 4. Trước khi đưa lên VPS

- Toàn bộ mục 2 qua, và kịch bản mục 3 được ghi lại bằng ảnh màn hình.
- Rà ma trận thao tác (spec) trên điện thoại 320 px và máy tính.
- Chạy thử patch trên bản sao dữ liệu thật:
  - trả các đơn "Chờ duyệt" chưa có vòng ký về Nháp;
  - xóa `Lotus Signing Challenge`;
  - bật thiết lập giá vốn theo hóa đơn.

  Ghi lại số đơn bị trả về.
- Trên site thật, ngay trước khi nâng cấp, tìm phiếu nhận do bản cũ ghi phí vận chuyển của hộ kinh doanh vào 33881 (research.md R16). Danh sách rỗng thì không cần làm gì thêm. Nếu có phiếu, lập hóa đơn cho các phiếu đó trước khi nâng cấp.

  ```sql
  select pr.name, pr.posting_date, pr.per_billed from `tabPurchase Receipt` pr
    join `tabPurchase Taxes and Charges` t on t.parent=pr.name and t.parenttype='Purchase Receipt'
   where pr.docstatus=1 and t.charge_type='Actual' and t.category in ('Valuation','Valuation and Total')
     and t.account_head like '33881%';
  ```

  Bản sao ngày 10/11/2026 không có phiếu nào như vậy.
- Gộp `main` mới nhất trước khi đưa lên, theo `merge-plan.md`. `main` (737f686) đã xóa 79 bảng đời cũ. Chạy thử gộp có 13 tệp xung đột; cách giải từng tệp đã chuẩn bị và kiểm lại.
- Build lại giao diện (`npm run build` trong `frontend/`, chạy trên VPS) sau khi gộp, rồi commit: bản dựng trong `lotus_farm/public/frontend` đang là của `main`.
- Thêm mục mới ở đầu `frontend/src/release-notes.js`.
- Chỉ commit, đẩy và triển khai khi chủ vườn yêu cầu, theo quy trình phát hành trong bộ nhớ dự án (sao lưu, build từ ảnh đang chạy, migrate, smoke test).

## 5. Kết quả chạy (T106, T116: 10/11/2026; T140: 11/11/2026)

Nơi chạy: VPS, bộ thử riêng `lotus-003-proc` (CSDL riêng), image `lotus-release:40f8330` đang chạy thật, code nhánh 003 đã gộp `main`. Bản sao site thật `mua.test` dựng từ bản sao lưu `20261110_203110` của site `frontend`, đã bỏ khóa gửi thông báo đẩy, tắt email và lịch chạy. Không đụng site thật.

### Tự động (mục 2)

| Bộ | Site | Kết quả |
|---|---|---|
| Test giao diện | — | 650/650. Các ca thêm vào:<br>• lớp và kiểu chữ của hộp thoại điện thoại;<br>• hộp thoại mang theo luật điện thoại của màn mua hàng;<br>• các loại lỗi tải tệp;<br>• danh sách phiếu nhận gửi dạng JSON;<br>• nhãn từng loại điều chỉnh của hóa đơn;<br>• thuế suất theo ngày hóa đơn;<br>• công nợ tách khoản NCC phải hoàn. |
| `verify_signing.py` | bản sao site thật | qua (đơn mẫu chép không mang theo liên kết đề xuất đã đặt hết) |
| `verify_purchase_proposal.py` | bản sao site thật | qua |
| `verify_vat_in_cost.py` | bản sao site thật | 24/24 |
| `verify_sign_notify.py` (lỗi B1) | bản sao site thật | qua |
| `verify_procurement.py` | procurement.test | 51/51. test_24–test_32 (giá vốn theo hóa đơn, R16): hộ kinh doanh, hàng trả trước và sau hóa đơn, khác giá, khác thuế suất, phiếu nhận không thuế, dịch vụ trên đơn kèm phí vận chuyển, kỳ đã khóa, "đã có hóa đơn" theo giá trị, tài sản, khớp sổ ở mọi ngày chốt, chặn hủy riêng. test_33–test_42 (rà soát lần 2): tài sản tách chiếc, phí vận chuyển theo dòng, trả hết sau hóa đơn, hóa đơn điều chỉnh theo hóa đơn gốc, Period Closing Voucher, tạm ứng theo đơn, thuế 8% hết hạn, làm tròn hóa đơn khấu trừ, Buying Settings, hóa đơn điều chỉnh khi kỳ đã khóa. test_43–test_51 (rà soát lần 3): đơn đã đóng, tạm ứng của tháng đã kết chuyển, khoản NCC phải hoàn khi kỳ đã khóa, hủy hóa đơn không chênh lệch, làm tròn "đã có hóa đơn", bổ sung giá Mua nhanh và đối chiếu Tài chính, tạm ứng theo dòng, tài sản hóa đơn trước khi thuế 8% hết hạn, các loại khóa sổ |
| `verify_procurement_complete.py` | procurement.test | 62/62 (11 ca riêng, cộng 51 ca của `verify_procurement` mà nó nạp lại) |
| `verify_sales.py` (chép, đổi site sang bản sao, tạm đặt thuế khấu trừ trong giao dịch) | bản sao site thật | Qua phần bán hàng, thu tiền, hóa đơn dịch vụ thuế 10% (Nợ 1331), bảng kê mua vào theo thuế suất dòng, xuất Excel, đối chiếu phải thu. Phép đối chiếu bảng kê với TK 1331 lệch vì tháng 11 của bản sao đã có hóa đơn hộ kinh doanh (từ 04/11). Đó là do đổi chế độ thuế giữa tháng, không phải lỗi; ở chế độ hộ kinh doanh, phép này nay hiện dòng thông tin. |
| `verify_finance.py` | bản sao site thật | Dừng ở bước 1 (xem trước sơ đồ tài khoản TT133 → TT99). Công cụ không có tài khoản để chuyển số dư 33881 (thuế chờ hóa đơn của các phiếu thử). Bước này dùng một lần khi chuyển sơ đồ tài khoản, ngoài phạm vi spec 003. Phép đối chiếu "hàng về chưa có hóa đơn" được kiểm ở test_48. |
| `verify_purchase_flow.py` | procurement.test | 23/23 (thêm test_23: đề xuất giữ giá đã gõ) |
| `verify_procurement_concurrency.py` | procurement.test | 4/4 |
| Test đơn vị Python | — | 340, lỗi 3 ca cũ ở `test_warehouse_guards` (có từ trước spec 003) |
| Trình duyệt thật (Chromium) 1440, 844, 390, 320 px | bản sao site thật | 32 lượt mở, không tràn ngang, không lỗi trang (xem `checklists/ui-audit.md`) |

### Kịch bản mục 3 và ca kiểm tương ứng

| Kịch bản | Kiểm bằng | Kết quả |
|---|---|---|
| US1.1–2 phiếu chi ký đủ, thông báo không làm hỏng việc ký, có bản PDF lưu | `verify_signing`, `verify_sign_notify` | qua |
| US1.3 Chờ tôi ký, ký nhiều, một dòng bị sửa thì báo riêng | `verify_signing` (bulk) | qua |
| US1.5 chuyển người ký có lý do, có sự kiện REASSIGN | `verify_signing` | qua |
| US2 đóng phần chưa mua, hủy có lý do, nhập Excel hỏi lý do, số đếm giai đoạn | `verify_purchase_proposal` (us2) | qua |
| US3.1–6 giữ NCC và giá báo giá, cảnh báo khi lưu, trả lại có lý do, không tự duyệt, chặn submit qua REST, trạng thái đơn | `verify_purchase_flow` 13–19 | qua |
| US4.1–2 nhận một bước có ảnh và chữ ký người giao, thiếu thì bị chặn, PDF lưu | `verify_purchase_flow` 20–21 | qua |
| US4.3 hai người nhận cùng lúc | `verify_procurement_concurrency` | qua |
| US4.4 trả hàng ghi sổ ngay, nhắc hóa đơn điều chỉnh | `verify_procurement` 18 | qua |
| US4.5 gửi lại cùng yêu cầu chỉ có một phiếu | `verify_purchase_flow` 20, `verify_procurement` 17 | qua |
| US5.1–5 hóa đơn chờ nhập, thuế 5% và 8%, lệch giá có lý do, chặn trùng giữa các đường, chặn hủy khi đã chi | `verify_procurement` 20–23, `verify_vat_in_cost` | qua |
| US6.1–3 tuổi nợ, hàng chưa có hóa đơn, phiếu chi nhiều hóa đơn và tạm ứng, sổ chi tiết, biên bản đối chiếu, đảo phiếu | `verify_procurement_complete` 30 | qua |

### Kịch bản mục 3 thao tác thật trên trình duyệt (T116)

Các bước ở mục 3 được làm lại bằng Chromium trên VPS, với bản sao site thật `mua.test` (`tools/test_site_copy_live.sh`). Mỗi vai trò đăng nhập bằng tài khoản riêng:
- tổ trưởng, trưởng bộ phận, mua hàng, kế toán, kế toán trưởng, giám đốc, thủ kho;
- tài khoản do `tools/uat-003/uat_setup.py` tạo, chỉ trên bản sao.

Thao tác trên điện thoại chạy ở 390×844, có chế độ chạm; thao tác trên máy tính ở 1440 px. Ảnh chụp từng bước nằm ở `/opt/lotus-003-test/browser/uat/` trên VPS.

| Kịch bản | Bước | Kết quả cuối |
|---|---|---|
| `tools/uat-003/uat-1-signing.cjs`: US1, US2 | 16 | 16/16 |
| `uat-3-orders.cjs`: US3 | 11 | 11/11 |
| `uat-4-receiving.cjs`: US4 (gồm mạng rớt lúc xác nhận, hai người nhận cùng lúc, trả hàng trong app) | 7 | 7/7 |
| `uat-5-invoices.cjs`: US5, US6 (hóa đơn hai phiếu nhận khác giá và thuế suất, 3388 và 33881 về 0, chặn trùng, hủy, công nợ, phiếu chi ký 3 bước, đối chiếu) | 11 | 11/11 |

Bảng trên khớp cả ba lần chạy:
- T127, sau T107–T128;
- T140 (11/11/2026), sau vòng rà soát 2;
- T148 (11/11/2026), sau vòng rà soát 3.

Mỗi lần đều dựng lại giao diện và khởi động lại máy chủ thử trước khi chạy. uat-5 kiểm 33881 và 3388 về 0, tính cả bút toán chuyển thuế của hóa đơn. Tệp `.uat` (mật khẩu tài khoản thử) đã xóa sau lần chạy cuối; muốn chạy lại thì chạy `uat_setup.py` để tạo lại.

Lần chạy đầu tìm ra các lỗi sau, đã sửa và chạy lại (chi tiết ở tasks.md T107–T115):
- đề xuất mất giá đã gõ;
- trên điện thoại không ký được vì hộp xác nhận bị che;
- giám đốc không duyệt được đơn lập từ báo giá;
- lập đơn trên điện thoại không mang NCC và giá đã chọn;
- "In đơn mua" không mở bản PDF đã ký;
- lỗi tải tệp hiện tên lỗi kỹ thuật;
- biểu mẫu hóa đơn báo JSONDecodeError;
- hóa đơn tính cả hàng đã trả;
- 33881 còn tiền khi hóa đơn khác giá hoặc thuế suất;
- tên file ở phiếu nhận dính liền nhau.

Lần chạy lại T127 tìm thêm lỗi B6: khi hàng đợi nền đầy, giám đốc không ký được đề xuất. Lỗi đã sửa (T128).

Hai vòng rà soát độc lập trên mã (11/11/2026) tìm thêm các lỗi ghi sổ. Mỗi vòng có năm người đọc, mỗi người một góc nhìn, và mỗi phát hiện có người tìm cách bác bỏ bằng mã ERPNext 16.

Vòng 1 (sửa ở T117–T125):
- hàng trả lại dồn chênh lệch vào 632;
- hai phiếu bù trừ nhau làm mất bút toán;
- phiếu nhận không thuế nhưng hóa đơn có thuế;
- kỳ đã khóa;
- dòng dịch vụ;
- "đã có hóa đơn" theo giá trị;
- khớp sổ ở mọi ngày chốt.

Vòng 2 (36 phát hiện: 21 xác nhận, 1 có thể, 14 bác bỏ; sửa ở T129–T139):
- tài sản tách chiếc bị tính thuế và phí hai lần;
- thuế 8% hết hạn chặn nhập kho và chặn hóa đơn tài sản;
- phí vận chuyển của dịch vụ vào hàng kho; phí chia theo giá trị thay vì theo dòng;
- trả hết hoặc trả sau hóa đơn;
- hóa đơn điều chỉnh không theo hóa đơn gốc;
- Period Closing Voucher;
- số chờ hóa đơn bỏ phần âm;
- tạm ứng theo đơn trừ hai lần và chỉ kiểm ở một màn;
- nhãn điều chỉnh, làm tròn hóa đơn khấu trừ;
- hủy hóa đơn điều chỉnh;
- thứ tự ghi phiếu chia.

Vòng 3 (25 phát hiện, 24 xác nhận; sửa ở T141–T147):
- hóa đơn trên phiếu nhận của đơn đã đóng;
- tạm ứng của tháng đã kết chuyển;
- đo đúng khoản NCC phải hoàn;
- làm tròn "đã có hóa đơn" và "đã trả hết hàng";
- đối chiếu Tài chính theo 3388 + 33881 (T082);
- công nợ tách khoản NCC phải hoàn;
- bổ sung giá Mua nhanh;
- tạm ứng và "còn phải lập hóa đơn" theo dòng;
- thuế 8% trên biểu mẫu, báo giá, đơn và tài sản;
- bảng kê thuế GTGT.

Phần lẻ đồng, phiếu nhận cũ ghi phí vào 33881 và chi phí nhận hàng của hàng trả lại được ghi ở research.md R16.

Chạy lại: chép `tools/uat-003` vào `/opt/lotus-003-test/browser`. Chạy `uat_setup.py` và `uat_perm.py` trong container thử, ghi dòng JSON cuối vào `.uat` (quyền 600). Sau đó chạy `node uat-1-signing.cjs`, rồi lần lượt uat-3, uat-4, uat-5 theo đúng thứ tự, vì kịch bản sau dùng chứng từ của kịch bản trước. Xong việc thì xóa `.uat`.

### Mục 4 trên bản sao dữ liệu thật

- Patch `return_unsigned_pending_orders`: đã chạy; site thật hiện không có đơn mua nào, nên không đơn nào bị trả về Nháp.
- Patch `drop_signing_challenge`: đã chạy; DocType và bảng `Lotus Signing Challenge` không còn.
- Thiết lập ERPNext sau migrate:
  - `over_billing_allowance` = 100;
  - `maintain_same_rate` = 0;
  - định giá lại theo giá hóa đơn của ERPNext = 0, vì Lotus tự ghi phần chênh theo từng hóa đơn (R16);
  - tính hóa đơn cho hàng bị loại = 0.

  Lần chạy đầu ở bước này để định giá lại = 1. Buổi thử kịch bản trên trình duyệt cho thấy cách đó không đủ (research.md R16).
- Đối chiếu công nợ trên dữ liệu thật: sổ cái 331 khớp. "Hàng đã nhận chưa có hóa đơn" là 2.094.234.400 đ, sổ cái 3388 là 2.107.054.400 đ. Mọi phiếu nhập còn chờ hóa đơn khớp sổ cái từng đồng; phần lệch 12.820.000 đ gồm:
  - 4 bút toán ghi tay vào 3388 (ACC-JV-2026-00007, -00018, -00020, -00022; ghi chú SQ222-0xx), cộng 4.660.000 đ;
  - hóa đơn Mua nhanh ACC-PINV-2026-00018 (lập trước spec 003) xóa 3388 ít hơn phiếu nhập MAT-STE-2026-00029 là 8.160.000 đ.

  Kế toán cần xem lại hai khoản này; màn Công nợ báo lệch đúng như thiết kế.

### Còn lại cho người dùng thật

Kịch bản trên trình duyệt đã làm thay được một phần:
- mở link trong email "Đến lượt bạn ký" trên máy tính và điện thoại;
- mở trang `/verify/lotus` theo đường QR in trên phiếu;
- mạng rớt đúng lúc xác nhận nhập kho.

Những bước sau vẫn cần người cầm máy thật:
- nhận thông báo đẩy trên điện thoại thật và bấm mở;
- quét QR bằng camera trên bản in giấy A4, và xem bản in bằng mắt;
- mất sóng thật trên điện thoại ngoài vườn;
- vòng nghiệm thu của 6 vai trò thật (SC-011).

Các bước này đã gom thành một phiếu theo từng vai trò, có ô đánh dấu, ở `checklists/acceptance.md`. Làm sau khi đưa lên site thật, với một lần mua nhỏ có thật.
