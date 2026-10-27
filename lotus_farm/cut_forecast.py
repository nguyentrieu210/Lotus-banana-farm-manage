"""Compatibility guard for cached clients of the retired mother-cut simulator."""
import frappe

def _retired():
    frappe.throw("Dự thu đã chuyển sang số cây theo lô và đợt cây. Tải lại trang rồi mở Dự thu theo lô/vụ.")

@frappe.whitelist()
def board(farm=None, zone=None):
    _retired()

@frappe.whitelist(methods=["POST"])
def preview_import(farm, content, file_name=None):
    _retired()

@frappe.whitelist(methods=["POST"])
def commit_import(farm, token, apply_params=1):
    _retired()

@frappe.whitelist(methods=["POST"])
def undo_import(farm, batch):
    _retired()

@frappe.whitelist(methods=["POST"])
def save_profile(farm, values, notes=None):
    _retired()

@frappe.whitelist()
def export_forecast(farm, zone=None):
    _retired()
