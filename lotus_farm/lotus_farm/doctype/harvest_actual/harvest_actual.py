import frappe
from frappe.model.document import Document
from frappe.utils import flt
from lotus_farm.controls import whole_count
from lotus_farm.daily_operations import number
from lotus_farm.inheritance import INHERITED_CYCLE_FIELDS, is_inherited_opening, validate_coverage_date


class HarvestActual(Document):
    def validate(self):
        self._validate_scope()

        gross_weight = number(self.gross_weight_kg, "Gross weight", positive=True)
        rejected_weight = number(self.rejected_weight_kg, "Rejected weight")
        self.harvested_bunch_qty = whole_count(self.harvested_bunch_qty, "Harvested bunches")
        if self.harvested_bunch_qty < 1:
            frappe.throw("Thu hoạch cần số buồng là số nguyên dương.")
        from lotus_farm.harvest_matching import match_forecast
        if not self.forecast:
            self.forecast = match_forecast(self)
        if rejected_weight > gross_weight:
            frappe.throw("Khối lượng loại không được vượt khối lượng cân tổng.")

        self.saleable_weight_kg = flt(gross_weight - rejected_weight, 3)
        self.forecast_saleable_kg = 0
        self.variance_kg = 0
        self.variance_percent = 0

        if self.forecast:
            forecast = frappe.db.get_value(
                "Harvest Forecast",
                self.forecast,
                ["farm", "farm_block", "crop_cycle", "sucker_selection_batch", "saleable_forecast_kg", "process_adoption"],
                as_dict=True,
                for_update=True,
            )
            if not forecast:
                frappe.throw("Dự thu không tồn tại.")
            if (
                forecast.farm != self.farm
                or forecast.farm_block != self.farm_block
                or forecast.crop_cycle != self.crop_cycle
            ):
                frappe.throw("Dự thu phải thuộc cùng vườn, lô và vụ.")
            if (forecast.sucker_selection_batch or '') != (self.sucker_selection_batch or ''):
                frappe.throw("Dự thu phải thuộc cùng đợt chọn chồi.")
            sources = set(frappe.get_all('Forecast Source Claim', filters={
                'parent': self.forecast, 'parenttype': 'Harvest Forecast',
            }, pluck='source_cut_operation'))
            if (sources or forecast.process_adoption) and (not self.get('source_cut_operation') or sources != {self.get('source_cut_operation')}):
                frappe.throw('Dự thu phải gắn đúng với thao tác cắt bắp nguồn này.')

            self.forecast_saleable_kg = flt(forecast.saleable_forecast_kg or 0, 3)
            self.variance_kg = flt(self.saleable_weight_kg - self.forecast_saleable_kg, 3)
            if self.forecast_saleable_kg:
                self.variance_percent = flt(self.variance_kg / self.forecast_saleable_kg * 100, 2)

    def _validate_scope(self):
        block_farm = frappe.db.get_value("Farm Block", self.farm_block, "farm")
        if block_farm and block_farm != self.farm:
            frappe.throw("Lô phải thuộc vườn đã chọn.")

        cycle = frappe.db.get_value(
            "Crop Cycle",
            self.crop_cycle,
            ["farm", "farm_block", *INHERITED_CYCLE_FIELDS],
            as_dict=True,
        )
        if not cycle:
            frappe.throw("Vụ không tồn tại.")
        if cycle.farm != self.farm or cycle.farm_block != self.farm_block:
            frappe.throw("Vụ phải thuộc vườn và lô đã chọn.")
        validate_coverage_date(cycle, self.harvest_date)
        if cycle.cycle_type == "Ratoon" and not self.sucker_selection_batch and not is_inherited_opening(cycle):
            frappe.throw("Thu hoạch vụ chồi (lưu gốc) phải chọn đợt chọn chồi.")

        if self.sucker_selection_batch:
            batch_cycle = frappe.db.get_value(
                "Sucker Selection Batch", self.sucker_selection_batch, "crop_cycle"
            )
            if batch_cycle != self.crop_cycle:
                frappe.throw("Đợt chọn chồi phải thuộc vụ đã chọn.")

    def before_cancel(self):
        source = frappe.qb.DocType("Harvest Lot Source")
        lot = frappe.qb.DocType("Harvest Lot")
        rows = (
            frappe.qb.from_(source)
            .join(lot)
            .on(source.parent == lot.name)
            .select(lot.name)
            .where((source.harvest_actual == self.name) & (lot.docstatus == 1))
            .run()
        )
        if rows:
            frappe.throw("Hủy các lô thu hoạch phụ thuộc trước khi hủy lần thu hoạch này.")
