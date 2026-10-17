# Hướng dẫn thiết lập dự thu bằng tiếng Việt – Lotus

## Các bước trong màn Thiết lập hệ số
1. **Áp dụng cho vườn nào?** Điền tên bộ hệ số, chọn Vườn 222/180, có thể chọn giống và lô cụ thể. Nếu chọn Vườn và để trống Lô, hệ số dùng chung cho lô thuộc vườn đó. Nhập ngày bắt đầu áp dụng bộ hệ số (không phải ngày trồng).
2. **Bao lâu thì thu?** Điền số **ngày** kể từ ngày trồng, chọn chồi, trổ buồng, cắt bắp đến ngày dự kiến thu. Để trống nếu chưa được kỹ thuật xác nhận. Điền khoảng cách dự kiến giữa vụ chồi để có kế hoạch xa 36 tháng.
3. **Một buồng được bao nhiêu kg?** Điền cân nặng trung bình mỗi buồng, tỷ lệ buồng còn thu được, đạt chất lượng và ra thành phẩm. Nhập 90% dưới dạng `90`, không phải `0.9`. Tỷ lệ dự phòng là lượng giữ lại an toàn khi cam kết bán, không ảnh hưởng số tấn buồng trên bảng 3 năm.
4. **Thử tính với 1.000 buồng** chỉ minh họa ngay trong biểu mẫu, không ghi sổ/không tạo dự thu thật.
5. **Thông tin nâng cao** giữ các trường tình trạng duyệt, phiên bản, đang sử dụng và ghi chú nguồn số liệu. Trường tự động `calibration_json` và `calibration_hash` chỉ đọc, không đưa vào form người dùng vì không được sửa bằng tay.

Không tạo giá trị mặc định cho bất kỳ số ngày hay tỷ lệ nào. Cần người có thẩm quyền xác nhận và bộ hệ số phải `Approved` mới tham gia dự thu.

## Cần phân biệt
- Ngày trồng cụ thể của mỗi **Lô** nhập trong thông tin lô, hoặc dùng bảng rà soát 64 lô đã có.
- Bộ hệ số dự thu mô tả quy luật sinh trưởng và tỷ lệ hao hụt **cấp vườn/giống/lô**.
- Các số buồng trổ, cắt bắp có nguồn từ bản ghi công việc và không phải gõ lại trong màn hệ số.

## Không đổi nghiệp vụ
- Quyền đọc/sửa/duyệt do Frappe quyết định, không thay bằng kiểm tra CSS.
- Giữ nguyên trường, khóa, logic tính, dữ liệu và nguồn đã duyệt.
- Chỉ đổi cách trình bày khi mở `Harvest Profile` từ màn Dự thu.
