"""Isolated controller tests for the explicit inherited opening boundary.

These exercise real validation with a small Frappe adapter; they do not claim
database concurrency or stock integration coverage.
"""
import copy
import importlib.util
import json
import sys
import types
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]


class ValidationError(Exception):
    pass


class Doc(dict):
    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        self[key] = value

    def is_new(self):
        return self.get("_new", True)

    def get_doc_before_save(self):
        return self.get("_before")

    def check_permission(self, *args):
        pass


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


class TestInheritedOpening(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.records = {
            "Farm Block": [Doc(name="BLOCK", farm="FARM", farm_zone="A", variety="VAR")],
            "Farm Plot": [Doc(name="PLOT", farm="FARM", farm_block="BLOCK", area_ha=1)],
        }
        self.fields = []
        for path in (ROOT / "lotus_farm/lotus_farm/doctype").glob("*/*.json"):
            schema = json.loads(path.read_text(encoding="utf8"))
            for field in schema.get("fields", []):
                if field.get("fieldtype") == "Link":
                    self.fields.append(Doc(parent=schema["name"], **field))
        self.custom_fields = []
        self.frappe = types.ModuleType("frappe")
        self.frappe.session = Doc(user="Administrator")
        self.frappe.PermissionError = PermissionError
        self.frappe.get_roles = lambda: ["Lotus Farm Manager"]
        self.frappe.throw = self.throw
        self.frappe.get_all = self.get_all
        self.frappe.get_doc = self.get_doc
        self.frappe.get_meta = lambda *args: Doc(has_field=lambda field: False)
        self.frappe.db = Doc(get_value=self.get_value, exists=self.exists)
        utils = types.ModuleType("frappe.utils")
        utils.cint = lambda value: int(value or 0)
        utils.flt = lambda value, precision=None: round(float(value or 0), precision) if precision is not None else float(value or 0)
        utils.getdate = as_date
        utils.get_datetime = lambda value: datetime.fromisoformat(value) if isinstance(value, str) else value
        utils.get_system_timezone = lambda: "Asia/Ho_Chi_Minh"
        utils.nowdate = lambda: "2026-10-21"
        utils.now_datetime = lambda: datetime(2026, 10, 21, 8)
        utils.add_days = lambda value, days: as_date(value) + timedelta(days=days)
        model = types.ModuleType("frappe.model")
        document = types.ModuleType("frappe.model.document")
        document.Document = Doc
        self.modules = patch.dict(sys.modules, {
            "frappe": self.frappe, "frappe.utils": utils,
            "frappe.model": model, "frappe.model.document": document,
        })
        self.modules.start()
        self.controls = self.load("lotus_farm.controls", "lotus_farm/controls.py")
        self.controls.lock = lambda doctype, name: self.events.append(("lock", doctype, name))
        self.inheritance = self.load("lotus_farm.inheritance", "lotus_farm/inheritance.py")
        self.current_lineage_read = self.inheritance.lock_plot_cycles
        self.inheritance.lock_plot_cycles = self.lock_plot_cycles
        self.daily = self.load("lotus_farm.daily_operations", "lotus_farm/daily_operations.py")
        self.Cycle = self.load("lotus_test_cycle", "lotus_farm/lotus_farm/doctype/crop_cycle/crop_cycle.py").CropCycle
        self.Operation = self.load("lotus_test_bunch", "lotus_farm/lotus_farm/doctype/bunch_operation/bunch_operation.py").BunchOperation
        self.Actual = self.load("lotus_test_actual", "lotus_farm/lotus_farm/doctype/harvest_actual/harvest_actual.py").HarvestActual
        self.Inspection = self.load("lotus_test_inspection", "lotus_farm/lotus_farm/doctype/defect_inspection/defect_inspection.py").DefectInspection

    def tearDown(self):
        self.modules.stop()

    @staticmethod
    def throw(message, exception=ValidationError):
        raise exception(message)

    @staticmethod
    def load(name, relative):
        spec = importlib.util.spec_from_file_location(name, ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def matches(row, filters):
        if isinstance(filters, str):
            return row.get("name") == filters
        for key, value in (filters or {}).items():
            actual = row.get(key)
            if isinstance(value, list):
                if value[0] == "!=" and actual == value[1]:
                    return False
                if value[0] == "in" and actual not in value[1]:
                    return False
            elif (actual or "") != (value or ""):
                return False
        return True

    def get_all(self, doctype, filters=None, fields=None, pluck=None, **kwargs):
        rows = self.fields if doctype == "DocField" else self.custom_fields if doctype == "Custom Field" else self.records.get(doctype, [])
        rows = [row for row in rows if self.matches(row, filters)]
        return [row.get(pluck) for row in rows] if pluck else rows

    def get_doc(self, doctype, name, **kwargs):
        return next(row for row in self.records.get(doctype, []) if row.name == name)

    def get_value(self, doctype, filters, fields="name", as_dict=False, for_update=False):
        rows = self.get_all(doctype, filters)
        if not rows:
            return None
        return Doc({field: rows[0].get(field) for field in fields}) if as_dict else rows[0].get(fields)

    def exists(self, doctype, filters):
        self.events.append(("exists", doctype, filters))
        rows = self.get_all(doctype, filters)
        return rows[0].name if rows else None

    def lock_plot_cycles(self, plot):
        self.controls.lock("Farm Plot", plot)
        self.events.append(("current_read", "Crop Cycle", plot))
        return self.get_all("Crop Cycle", {"farm_plot": plot})

    def opening(self, **changes):
        values = dict(doctype="Crop Cycle", name="OPEN", farm="FARM", farm_block="BLOCK", farm_plot="PLOT",
                      cycle_no=3, cycle_type="Ratoon", origin_basis="Handover", parent_cycle=None,
                      planting_date=None, coverage_start_date="2026-10-20", inheritance_note="Prior lot records unavailable",
                      handover_zone="A", variety="VAR", status="Active")
        values.update(changes)
        return self.Cycle(values)

    def transaction(self, cls, doctype, **changes):
        values = dict(doctype=doctype, name="TX", farm="FARM", farm_block="BLOCK", farm_plot="PLOT",
                      crop_cycle="OPEN", sucker_selection_batch=None, operation_date="2026-10-20",
                      harvest_date="2026-10-20", inspection_date="2026-10-20", posting_date="2026-10-20",
                      docstatus=0, meta=Doc(has_field=lambda field: False))
        values.update(changes)
        return cls(values)

    def test_opening_is_explicit_and_serialized_before_duplicate_check(self):
        cycle = self.opening(handover_zone=None)
        cycle.validate()
        self.assertTrue(self.inheritance.is_inherited_opening(cycle))
        self.assertIsNone(cycle.parent_cycle)
        self.assertIsNone(cycle.planting_date)
        self.assertEqual(cycle.handover_zone, "A")
        lock_index = next(i for i, event in enumerate(self.events) if event[:2] == ("lock", "Farm Plot"))
        check_index = next(i for i, event in enumerate(self.events) if event[:2] == ("current_read", "Crop Cycle"))
        self.assertLess(lock_index, check_index)

    def test_opening_requires_manager_note_coverage_and_unknown_history(self):
        for invalid in ({"inheritance_note": " "}, {"coverage_start_date": None}, {"farm_plot": None},
                        {"planting_date": "2020-01-01"}, {"parent_cycle": "PARENT"}, {"cycle_no": 1}):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                self.opening(**invalid).validate()
        self.frappe.session.user = "operator"
        self.frappe.get_roles = lambda: ["System Manager"]
        with self.assertRaises(PermissionError):
            self.opening().validate()

    def test_lineage_read_requests_current_rows_after_the_plot_lock(self):
        query = MagicMock()
        query.select.return_value = query
        query.where.return_value = query
        query.for_update.return_value = query
        query.run.return_value = []
        self.frappe.qb = Doc(DocType=MagicMock(return_value=MagicMock()), from_=MagicMock(return_value=query))
        self.current_lineage_read("PLOT")
        self.assertEqual(self.events[0], ("lock", "Farm Plot", "PLOT"))
        query.for_update.assert_called_once_with()
        query.run.assert_called_once_with(as_dict=True)

    def test_second_opening_and_recreated_mother_are_rejected(self):
        self.records["Crop Cycle"] = [self.opening()]
        with self.assertRaises(ValidationError):
            self.opening(name="SECOND", cycle_no=4).validate()
        with self.assertRaises(ValidationError):
            self.opening(name="MOTHER", cycle_no=1, origin_basis="Observed", planting_date="2026-10-20").validate()

    def test_successor_links_root_and_restores_strict_ssb(self):
        self.records["Crop Cycle"] = [self.opening()]
        successor = self.opening(name="NEXT", cycle_no=4, origin_basis="Observed", parent_cycle="OPEN", coverage_start_date=None)
        successor.validate()
        self.assertFalse(self.inheritance.is_inherited_opening(successor))
        self.records["Crop Cycle"].append(successor)
        for cls, doctype in ((self.Operation, "Bunch Operation"), (self.Actual, "Harvest Actual"), (self.Inspection, "Defect Inspection")):
            with self.subTest(doctype=doctype), self.assertRaises(ValidationError):
                self.transaction(cls, doctype, crop_cycle="NEXT")._validate_scope()
        with self.assertRaises(ValidationError):
            self.daily.plot_scope(self.transaction(Doc, "Daily Work Plan Line", crop_cycle="NEXT"))
        self.records["Sucker Selection Batch"] = [Doc(name="COUNTED", farm="FARM", farm_block="BLOCK", crop_cycle="NEXT")]
        for cls, doctype in ((self.Operation, "Bunch Operation"), (self.Actual, "Harvest Actual"), (self.Inspection, "Defect Inspection")):
            self.transaction(cls, doctype, crop_cycle="NEXT", sucker_selection_batch="COUNTED")._validate_scope()

    def test_opening_scope_without_ssb_and_inclusive_coverage_date(self):
        self.records["Crop Cycle"] = [self.opening()]
        for cls, doctype, field in ((self.Operation, "Bunch Operation", "operation_date"),
                                   (self.Actual, "Harvest Actual", "harvest_date"),
                                   (self.Inspection, "Defect Inspection", "inspection_date")):
            with self.subTest(doctype=doctype):
                self.transaction(cls, doctype)._validate_scope()
                with self.assertRaisesRegex(ValidationError, "ngày bắt đầu theo dõi"):
                    self.transaction(cls, doctype, **{field: "2026-10-19"})._validate_scope()
        self.daily.plot_scope(self.transaction(Doc, "Daily Work Plan Line"))
        with self.assertRaisesRegex(ValidationError, "ngày bắt đầu theo dõi"):
            self.daily.plot_scope(self.transaction(Doc, "Fruit Measurement", posting_date="2026-10-19"))
        with self.assertRaisesRegex(ValidationError, "ngày bắt đầu theo dõi"):
            self.daily.plot_scope(self.transaction(Doc, "Sucker Selection Batch", posting_date=None, selection_date="2026-10-19"))

    def test_supplied_cohort_still_must_match_and_malformed_root_is_not_exempt(self):
        self.records["Crop Cycle"] = [self.opening()]
        self.records["Sucker Selection Batch"] = [Doc(name="OTHER", farm="FARM", farm_block="BLOCK", crop_cycle="OTHER-CYCLE")]
        for cls, doctype in ((self.Operation, "Bunch Operation"), (self.Actual, "Harvest Actual"), (self.Inspection, "Defect Inspection")):
            with self.subTest(doctype=doctype), self.assertRaises(ValidationError):
                self.transaction(cls, doctype, sucker_selection_batch="OTHER")._validate_scope()
        self.records["Crop Cycle"][0].coverage_start_date = None
        with self.assertRaisesRegex(ValidationError, "Hoàn tất vụ đầu kỳ kế thừa và ngày bắt đầu theo dõi trước khi ghi thao tác"):
            self.transaction(self.Operation, "Bunch Operation")._validate_scope()

    def test_explicit_forecast_requires_exact_cut_source_and_normalizes_blank_ssb(self):
        self.records["Crop Cycle"] = [self.opening()]
        self.records["Harvest Forecast"] = [Doc(name="SUPPLY", farm="FARM", farm_block="BLOCK", crop_cycle="OPEN",
            sucker_selection_batch="", process_adoption="PROCESS", saleable_forecast_kg=100,
            period_start_date="2026-12-01", period_end_date="2026-12-31")]
        self.records["Forecast Source Claim"] = [Doc(name="CLAIM", parent="SUPPLY", parenttype="Harvest Forecast", source_cut_operation="CUT")]
        actual = self.transaction(self.Actual, "Harvest Actual", forecast="SUPPLY", source_cut_operation="CUT",
            harvested_bunch_qty=1, gross_weight_kg=10, rejected_weight_kg=0)
        actual.validate()  # Source matching permits consumption outside its planning slice.
        self.assertEqual(actual.saleable_weight_kg, 10)
        for source in (None, "OTHER-CUT"):
            actual.source_cut_operation = source
            with self.subTest(source=source), self.assertRaisesRegex(ValidationError, "Dự thu phải gắn đúng với thao tác cắt bắp nguồn này"):
                actual.validate()

    def test_all_schema_references_freeze_cycle_identity_with_their_correct_field(self):
        for doctype, link in (("Crop Cycle", "parent_cycle"), ("Daily Work Plan Line", "crop_cycle"),
                              ("Plan Cohort", "crop_cycle"), ("Material Consumption", "crop_cycle")):
            with self.subTest(doctype=doctype):
                self.records[doctype] = [Doc(name="DEPENDENT", **{link: "OPEN"})]
                cycle = self.opening(_new=False, _before=self.opening(), coverage_start_date="2026-10-21")
                with self.assertRaisesRegex(ValidationError, "Định danh sản xuất đã dùng thì không được sửa"):
                    self.controls.preserve_lineage(cycle)
                del self.records[doctype]

    def test_custom_links_freeze_identity_and_status_change_is_allowed(self):
        self.custom_fields = [Doc(dt="Custom Operations", fieldname="opening_cycle", fieldtype="Link", options="Crop Cycle")]
        self.records["Custom Operations"] = [Doc(name="CUSTOM", opening_cycle="OPEN")]
        cycle = self.opening(_new=False, _before=self.opening(), inheritance_note="Changed provenance")
        with self.assertRaises(ValidationError):
            self.controls.preserve_lineage(cycle)
        cycle = self.opening(_new=False, _before=self.opening(), status="Harvesting")
        self.controls.preserve_lineage(cycle)

    def test_closing_report_exposes_unknown_planting_and_freezes_provenance(self):
        self.records["Crop Cycle"] = [self.opening()]
        report = self.transaction(self.daily.CycleClose, "Cycle Closing Report")
        report.validate_daily()
        self.assertEqual(report.origin_basis, "Handover")
        self.assertEqual(report.coverage_start_date, "2026-10-20")
        self.assertEqual(report.planting_date_known, 0)
        provenance = json.loads(report.snapshot_json)["cycle_origin"]
        self.assertIsNone(provenance["planting_date"])
        self.assertIsNone(provenance["parent_cycle"])
        self.assertTrue(provenance["inherited_opening"])
        self.assertEqual(report.planted_qty, 0)
        report._before = copy.deepcopy(report)
        report.planting_date_known = 1
        with self.assertRaisesRegex(ValidationError, "Nguồn số liệu kết vụ đã duyệt không được sửa"):
            report.before_update_after_submit()


if __name__ == "__main__":
    unittest.main()
