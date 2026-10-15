# Nông trường Farm 222 Thuận Phú

Đã nhập vào site local `frontend`, công ty `Lotus Agritech`, mã nông trường
`LOTUS-222`. Đây là dữ liệu danh mục lấy từ bản đồ 222, không dùng seed demo
và không bao gồm bản đồ HTT 170 ha.

- Farm: diện tích danh nghĩa 222 ha.
- 64 Farm Block: lô chăm sóc; tổng diện tích ghi trên PDF 215,16 ha.
- 200 Farm Plot: mã thửa tưới có đúng một lô cha theo bảng nguồn.
- 64 Farm Block Geometry và 200 Plot Geometry: Draft, chưa xác minh GPS.
- A35, C17, C24, E6, E7: lưu trong báo cáo, chưa tạo Farm Plot vì lô cha
  chưa thống nhất. Bộ nguồn vẫn giữ đủ 205 mã.

PDF ghi diện tích lô với ít chữ số hơn diện tích thửa. Có 21 lô mà tổng thửa
nguồn vượt diện tích lô từ 0,0006 đến 0,0114 ha. Với 71 thửa trong các lô này,
diện tích dùng lập kế hoạch được giảm theo tỷ lệ, làm tròn xuống 6 chữ số,
để không vượt diện tích lô. Không sửa số nguồn hoặc tăng diện tích lô.
Các số nguồn và số dùng kế hoạch được lưu trong hai File riêng tư đính kèm Farm:
`farm-222-map-source.json` và `farm-222-import-report.json`.
Ghi chú từng lô và lý do ranh từng thửa cũng ghi rõ điều chỉnh.

## Nhập lại

`tools/import_farm_222.py` chạy bằng Python của bench từ thư mục `bench/sites`:

```sh
../env/bin/python /path/import_farm_222.py --company 'Lotus Agritech' \
  --bundle /path/farm-222-map.json --report /path/report.json
# Thêm --commit để lưu; mặc định chạy thử rồi rollback.
```

Chạy lại cùng nguồn không tạo trùng. Nếu danh mục có số liệu khác, dừng và rollback
để kiểm tra, không ghi đè. Không tự tạo vụ cây, giống, ngày trồng, tổ lao động
hoặc phiếu giao việc. Cần bổ sung dữ liệu nghiệp vụ này trước khi giao việc thực tế.

Kiểm tra trên site: API `lotus_farm.mobile_assignment.options('LOTUS-222')`
trả đủ 64 lô và 200 thửa đang hoạt động; tổng diện tích thửa không vượt lô;
nguồn đính kèm là File riêng tư; chạy lại tạo thêm 0 bản ghi.

## Xác nhận tách mã của chủ nông trường ngày 14/10/2026

Các mã chung trên bản đồ đại diện các lô thực địa khác nhau, không phải bản ghi
trùng cần xóa. Đã tạo thêm 6 thửa, nâng tổng danh mục lên 206:

| Mã mới | Thuộc lô chăm sóc | Diện tích ha | Các phần ha |
|---|---|---:|---|
| A35a | A4 | 0,44 | 0,22 + 0,22 |
| A35b | A5 | 0,44 | 0,44 |
| C17a | C4 | 0,50 | 0,50 |
| C17b | C6 | 0,34 | 0,34 |
| C24a | C13 | 0,74 | 0,49 + 0,25 |
| C24b | C7 | 0,63 | 0,63 |

Chỉ còn E6 và E7 chờ xác nhận. Mã nguồn A35/C17/C24 vẫn được giữ trong bộ PDF
gốc, nhưng không tạo thửa ERP chung cho chúng. Các mã mới có nhãn tìm kiếm trên
bản đồ tại vị trí diện tích nguồn. Không sao chép polygon cũ cho nhiều thửa:
ranh mới chờ rà soát, 200 ranh thửa Draft đã có được giữ nguyên.

Diện tích 6 thửa xác nhận được lưu đúng số người dùng. Để không vượt số tổng lô
PDF đã làm tròn, diện tích kế hoạch của 8 thửa cũ trong C4/C6/C7/C13 giảm theo
tỷ lệ, mức giảm từng thửa dưới 0,004 ha. Lưu đầy đủ số trước/sau trong File
resolution report riêng tư đính kèm Farm. Bộ nguồn PDF không bị sửa.

`tools/resolve_farm_222_parcels.py` nhận `--resolutions`, `--report`, tùy chọn
`--commit`; mặc định rollback. Chạy lại không tạo trùng hoặc giảm tiếp diện tích.
Không chạy lại bước nhập PDF gốc sau khi đã có xác nhận tách mã.

### Hoàn tất E6/E7 và gộp nhãn hiển thị

Chủ nông trường đã xác nhận tiếp:

| Mã mới | Thuộc lô chăm sóc | Diện tích ha |
|---|---|---:|
| E6a | E4 | 0,79 |
| E6b | E5 | 0,25 |
| E7a | E10 | 0,46 |
| E7b | E4 | 0,58 |

Danh mục hiện có **210 thửa**, không còn mã nào trong 5 mã ban đầu chờ xác nhận
lô cha. Ranh tách mới vẫn chưa xác minh. E6a và E7b cùng E4 nhưng giữ riêng vì
khác mã gốc, theo xác nhận trực tiếp của chủ nông trường.

Chỉ gộp các phần cùng mã gốc và lô cha: A35a có một nhãn tổng 0,44 ha;
C24a có một nhãn tổng 0,74 ha. Giữ tọa độ nhãn các phần và diện tích gốc trong
`v2/data/parcel-resolutions.json`, dùng trung bình vị trí theo diện tích để đặt
nhãn tổng. Bản hiển thị care bỏ nhãn mã cũ/diện tích thành phần liên quan,
nguồn SVG gốc được bảo toàn. Vẫn thấy diện tích thành phần trong bảng chi tiết.

Để giữ đúng 0,25 ha xác nhận ở E5, diện tích kế hoạch của E1/E2/E3 giảm tổng
0,0087 ha do tổng lô PDF làm tròn; báo cáo đính kèm giữ số trước/sau.

## Chín tổ tạm và danh mục công việc từ code repo

Theo yêu cầu chủ nông trường, đã tạo T01–T09, tên Tổ 01 (tạm) đến Tổ 09 (tạm),
đang hoạt động và thuộc `LOTUS-222`. Chưa có dữ liệu tổ trưởng, số người hoặc
địa bàn cố định nên không tự gán các thông tin này.

Nhập tên/đơn vị từ hằng `WORKS` trong `lotus_farm/mobile_demo_seed.py` bằng AST,
không gọi seed mẫu. Mã công việc thật có tiền tố `LOTUS-`, không dùng `DEMO-`.

| Nhóm công đoạn | Mã công việc | Tên | Đơn vị nguồn |
|---|---|---|---|
| Chăm sóc buồng | LOTUS-BAG | Bao buồng | Bunch |
| Chăm sóc buồng | LOTUS-PROP | Chống buồng | Tree |
| Chăm sóc buồng | LOTUS-BUD | Cắt bắp | Bunch |
| Chăm sóc cây | LOTUS-LEAF | Cắt lá | Ha |
| Chăm sóc cây | LOTUS-SICK | Cắt lá bệnh | Ha |
| Chăm sóc cây | LOTUS-WEED | Phát cỏ | Ha |
| Trồng và chăm sóc | LOTUS-REPLANT | Trồng dặm | Tree |
| Trồng và chăm sóc | LOTUS-FERT | Bón phân | Tree |

Không nhập định mức năng suất minh họa của seed. `productivity_per_workday`
để 0 (chưa cấu hình); các công việc có thể chọn trong danh mục nhưng API giao
việc sẽ yêu cầu cấu hình năng suất dương trước khi tạo phiếu. Chưa tạo vụ cây.
Các loại thao tác `Bunch Operation` và phiếu quy trình thu hoạch/xưởng đã có
schema riêng, không biến chúng thành công việc trùng trong Work Type.

Script `tools/import_farm_222_work_catalog.py` nhận `--source`, `--report`,
`--commit`, mặc định rollback. Có kiểm tra danh mục giao việc nhận 9 tổ,
8 công việc, 64 lô và 210 thửa; chạy lại tạo thêm 0 bản ghi. Báo cáo nguồn và
SHA-256 đính kèm Farm dưới dạng File riêng tư. Không tạo nhân sự, giao việc,
phiếu kho hoặc dữ liệu mẫu khác.
