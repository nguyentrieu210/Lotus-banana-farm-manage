"""Safe, permission-scoped planting worksheet export for 36-month forecast setup.

The worksheet exports existing Lotus lots only. It does not seed invented farm
measurements and never writes production records. Fill missing values from
verified field reports and import through the existing authorized workflow.
"""
import csv
import io
import frappe

from lotus_farm.reporting import records
from lotus_farm.scoping import land_scope, land_filters


@frappe.whitelist()
def planting_template(company=None, farm=None, block=None,zone=None):
    if not frappe.has_permission("Harvest Forecast", "read") or not frappe.has_permission("Farm Block", "read"):
        frappe.throw("Không có quyền tải dữ liệu lô dự thu.", frappe.PermissionError)
    selected = land_scope(company=company, farm=farm, block=block, zone=zone)
    fields = ["name", "farm", "block_code", "block_name", "area_ha", "planting_date", "planting_density"]
    lots = records("Farm Block", land_filters(frappe.get_meta("Farm Block"), selected), fields)
    file = io.StringIO(newline="")
    writer = csv.writer(file)
    writer.writerow(["Mã bản ghi", "Vườn", "Mã lô", "Tên lô", "Diện tích (ha)", "Ngày trồng (YYYY-MM-DD)", "Cây/ha", "Ghi chú"])
    for lot in sorted(lots, key=lambda r: (r.farm or "", r.block_code or "", r.name)):
        writer.writerow([
            lot.name, lot.farm, lot.block_code or "", lot.block_name or "",
            lot.area_ha or 0, str(lot.planting_date or ""), lot.planting_density or "",
            "Cần đối chiếu thực tế trước khi nhập" if not lot.planting_date or not lot.planting_density else "Đã có dữ liệu; kiểm tra lại",
        ])
    return {"file_name": "lotus-ngay-trong-kiem-tra.csv", "csv": file.getvalue(), "row_count": len(lots),
            "note": "Chỉ xuất mẫu điền thông tin. Không tự cập nhật bản ghi, không tự tạo hệ số dự thu."}
