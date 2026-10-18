# Thử nghiệm Lotus VIP 126 trên live, không ghi dữ liệu giả vào phiếu

Ngày: 18/10/2026. API: `lotus_farm.vip126_trial.calendar`. Quyền đọc `Harvest Forecast` và `Farm Block` bắt buộc.

Nguồn tham khảo nghiệp vụ OneDrive: `XĐG_Kế hoạch sản lượng và xuất bán.xlsx`, `Theo dõi trồng mới.xlsx`, `Báo cáo chọn chồi.xlsx`, `FM BÁO CÁO KẾT QUẢ CB - TH - SC - ĐG CHUỐI.xlsx`.

Kịch bản cơ sở chỉ để thử: với 34/64 lô thiếu số cây, dùng diện tích × 2.600 cây/ha; khu A lấy ngày trổ dự kiến người dùng đưa ra 01/11/2026; B–E lần lượt giả lập 01/12/2026, 01/01/2027, 01/02/2027, 01/03/2027. Kết quả kế hoạch lịch sử tham khảo 17 kg thành phẩm trên buồng đã sơ chế và 98% buồng thu được sơ chế. Tỷ lệ cắt/thu và khối lượng buồng thô là dữ liệu giả định kiểm thử.

Tách bạch:
- Tỷ lệ từ cây có buồng, buồng trổ đến cắt, cắt đến thu, thu đến sơ chế.
- Tấn thành phẩm = số buồng sơ chế × 17kg, không nhân thêm phần QC hoặc packout đã gộp trong mức kg thành phẩm.
- Khoảng cách chọn chồi ~183 ngày và khoảng cách các lần thu chồi ~270 ngày là **hai loại mốc khác nhau**; các số này chưa hiệu chuẩn thực tế.

Giao diện `/lotus/forecast`: mặc định `Chạy thử đủ 64 lô`, có chuyển sang `Chỉ dữ liệu đang có`. Lọc A–E, kịch bản thấp/cơ sở/cao, biểu đồ tháng, bảng lịch 36 tháng. Có chức năng giả lập ngày trồng/chọn chồi/trổ/cắt bắp/thu hoạch cho một lô, trả kết quả dự phóng lại toàn bộ chu kỳ.

Tuyệt đối không ghi số cây giả, mốc giả hoặc tấn giả vào Farm Block, Crop Cycle, các phiếu đã nộp, kho, mua hàng, hoặc đơn bán. `commit_ready=False`, `approved=False`, `releasable_kg=0`. Bộ hệ số HP-00002 tiếp tục Draft, inactive.
