"""Phiếu báo cáo ngày của một tổ, in ra giấy (route /lotus/in-phieu-ngay?report=...). The layout is the one fixed by
lotus_farm.lot_paper_form.form_url, so the photo read later matches the printed columns."""
import frappe

from lotus_farm import lot_paper_form
from lotus_farm import print_kit as pk

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw("Vui lòng đăng nhập.", frappe.AuthenticationError)
    data = lot_paper_form.print_context(frappe.form_dict.get("report"))
    p = pk.page(data["company"], "PHIẾU BÁO CÁO NGÀY", data["report"], posting_date=data["date"], landscape=True, toolbar=True)
    p.info = [dict(label="Vườn", value=data["farm_name"]), dict(label="Đội", value=data["crew_name"]), dict(label="Tổ", value=data["team_name"]),
              dict(label="Ngày", value=pk.vn_date(data["date"]))]
    p.info_columns = 4
    p.form = data["form"]
    p.blank_rows = max(0, 3 - len(data["form"]["rows"]) % 3) if data["form"]["rows"] else 6
    context.html = pk.render("daily_form.html", p)
    context.no_cache = 1
