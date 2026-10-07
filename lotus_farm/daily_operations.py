"""Farm → Plot daily transactions and farm-day close controls."""
import json
import re
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt, now_datetime
from lotus_farm.controls import check_farm, lock, require_role, validate_version, validate_warehouse, whole_count
from lotus_farm.rules import quantity, canonical_hash, RuleError
from lotus_farm.operations_rules import material_needed, labor_needed, labor_summary, completion

DATE_FIELDS = {
    'Bunch Operation': 'operation_date', 'Harvest Actual': 'harvest_date',
    'Defect Inspection': 'inspection_date', 'Harvest Lot': 'received_date',
    'Packout Run': 'packing_date',
}
DAILY_TYPES = (
    'Daily Work Plan', 'Daily Work Result', 'Labor Allocation', 'Daily Labor Summary',
    'Material Requirement', 'Material Consumption', 'Material Recovery', 'Bunch Cancellation',
    'Planting Event', 'Disease Observation', 'Fruit Measurement', 'Incoming Quality Inspection', 'Secondary Product Movement',
)


def number(value, label='Quantity', positive=False):
    try:
        return float(quantity(value, label, positive=positive))
    except RuleError as exc:
        frappe.throw(str(exc))


def rule(func, *args):
    try:
        return func(*args)
    except RuleError as exc:
        frappe.throw(str(exc))


def day_guard(doc, method=None):
    if not doc.get('farm'):
        return
    check_farm(doc)
    lock('Farm', doc.farm)
    field = DATE_FIELDS.get(doc.doctype, 'posting_date')
    before = doc.get_doc_before_save()
    dates = {getdate(d.get(field)) for d in (doc, before) if d and d.get(field)}
    farms = {d.get('farm') for d in (doc, before) if d and d.get('farm')}
    for farm in sorted(farms):
        if farm != doc.farm:
            lock('Farm', farm)
        for date in dates:
            if frappe.db.exists('Daily Production Close', {'farm': farm, 'posting_date': date, 'docstatus': 1}):
                frappe.throw('This Farm day is closed. Cancel the daily close with a reason before correcting data.')


def plot_scope(doc, method=None):
    check_farm(doc)
    if doc.doctype == 'Crop Cycle':
        before=doc.get_doc_before_save()
        if before and before.get('farm_plot') and not doc.get('farm_plot'):
            frappe.throw('A mapped Cycle cannot lose its Plot.')
        if doc.is_new() and not doc.get('farm_plot'):
            frappe.throw('New Crop Cycles require a Farm Plot. Map legacy cycles explicitly.')
        plot_name = doc.get('farm_plot')
    else:
        cycle = frappe.get_doc('Crop Cycle', doc.crop_cycle)
        cycle.check_permission('read')
        if cycle.status == 'Closed' and doc.doctype != 'Cycle Closing Report' and (doc.is_new() or doc.docstatus == 1):
            frappe.throw('Cycle is closed. Reopen its closing report before adding production records.')
        if cycle.farm != doc.farm or cycle.farm_block != doc.farm_block:
            frappe.throw('Cycle must match the Farm and Block.')
        if doc.get('farm_plot') and doc.farm_plot != cycle.get('farm_plot'):
            frappe.throw('Plot must match the Crop Cycle.')
        before=doc.get_doc_before_save()
        historical_forecast=doc.doctype=='Harvest Forecast' and before and before.supply_state!='Draft'
        if not historical_forecast:
            doc.farm_plot = cycle.get('farm_plot')
        plot_name = doc.farm_plot
        if doc.doctype in DAILY_TYPES and not plot_name:
            frappe.throw('Map the legacy cycle to a Plot before daily operations.')
        if doc.get('sucker_selection_batch'):
            cohort = frappe.get_doc('Sucker Selection Batch', doc.sucker_selection_batch)
            cohort.check_permission('read')
            if cohort.crop_cycle != cycle.name:
                frappe.throw('Cohort belongs to another Cycle.')
        elif cycle.cycle_type == 'Ratoon' and doc.doctype in (*DAILY_TYPES, 'Daily Work Plan Line'):
            frappe.throw('Ratoon operations require a Sucker Selection Batch.')
        date = doc.get('posting_date')
        if date and cycle.planting_date and getdate(date) < getdate(cycle.planting_date):
            frappe.throw('Operation date precedes planting.')
        if date and doc.get('sucker_selection_batch') and getdate(date) < getdate(cohort.selection_date):
            frappe.throw('Operation date precedes sucker selection.')
    if plot_name:
        plot = frappe.get_doc('Farm Plot', plot_name)
        plot.check_permission('read')
        if plot.farm != doc.farm or plot.farm_block != doc.farm_block:
            frappe.throw('Plot must belong to the selected Farm and Block.')
    if doc.meta.has_field('company'):
        company = frappe.db.get_value('Farm', doc.farm, 'company')
        if doc.get('company') and doc.company != company:
            frappe.throw('Company must match the Farm.')
        doc.company = company


def company_scope(doc):
    company = frappe.db.get_value('Farm', doc.farm, 'company')
    if not company or (doc.get('company') and doc.company != company):
        frappe.throw('Company must match the Farm.')
    doc.company = company


def plan_line(doc):
    plan = frappe.get_doc('Daily Work Plan', doc.work_plan, for_update=True)
    plan.check_permission('read')
    lock('Daily Work Plan', plan.name)
    if plan.docstatus != 1 or plan.farm != doc.farm or getdate(plan.posting_date) != getdate(doc.posting_date):
        frappe.throw('Work Plan must be submitted for the same Farm/day.')
    row = next((r for r in plan.lines if r.name == doc.work_plan_line), None)
    if not row:
        frappe.throw('Select an exact Work Plan Line belonging to this Plan.')
    for field in ('farm_block', 'farm_plot', 'crop_cycle', 'sucker_selection_batch'):
        if (doc.get(field) or '') != (row.get(field) or ''):
            frappe.throw('Result/allocation/material scope must match the Work Plan Line.')
    return row


class DailyDocument(Document):
    def validate(self):
        if self.doctype == 'Cycle Closing Report':
            check_farm(self)
            lock('Farm',self.farm)
        else:
            day_guard(self)
        company_scope(self)
        if self.get('crop_cycle'):
            plot_scope(self)
        if self.get('amended_from') and not (self.get('amendment_reason') or '').strip():
            frappe.throw('Amendment reason is required.')
        self.validate_daily()

    def validate_daily(self):
        pass

    def before_cancel(self):
        day_guard(self)

    def on_trash(self):
        day_guard(self)


class PlotMaster(Document):
    def validate(self):
        check_farm(self)
        lock('Farm', self.farm)
        company_scope(self)
        block = frappe.get_doc('Farm Block', self.farm_block)
        block.check_permission('read')
        if block.farm != self.farm or not block.active:
            frappe.throw('Plot requires an active Block in the same Farm.')
        area=number(self.area_ha, 'Plot area', positive=True)
        siblings=sum(flt(v) for v in frappe.get_all('Farm Plot',filters={'farm_block':self.farm_block,'active':1,'name':['!=',self.name]},pluck='area_ha'))
        if self.active and siblings+area>flt(block.area_ha)+0.000001:
            frappe.throw('Active Plot areas exceed the Block area.')
        before = self.get_doc_before_save()
        if before and any(self.get(f) != before.get(f) for f in ('farm', 'farm_block', 'plot_code')):
            if frappe.db.exists('Crop Cycle', {'farm_plot': self.name}):
                frappe.throw('Used Plot identities cannot be reassigned.')
        if frappe.db.exists('Farm Plot', {'farm_block': self.farm_block, 'plot_code': self.plot_code, 'name': ['!=', self.name]}):
            frappe.throw('Plot code must be unique within its Block.')


class TeamMaster(Document):
    def validate(self):
        check_farm(self)
        if frappe.db.exists('Work Team', {'farm': self.farm, 'team_code': self.team_code, 'name': ['!=', self.name]}):
            frappe.throw('Team code must be unique within its Farm.')


class WorkTypeMaster(Document):
    def validate(self):
        number(self.productivity_per_workday or 0, 'Productivity')


class NormProfile(Document):
    def validate(self):
        check_farm(self)
        lock('Farm', self.farm)
        validate_version(self, 'profile_name', ('Lotus Farm Manager',))
        work = frappe.get_doc('Work Type', self.work_type)
        if not work.active:
            frappe.throw('Work Type is inactive.')
        if not self.lines:
            frappe.throw('A norm profile requires material lines.')
        seen = set()
        for row in self.lines:
            if row.item in seen:
                frappe.throw('Combine duplicate Items into one norm line.')
            seen.add(row.item)
            item = frappe.get_doc('Item', row.item)
            item.check_permission('read')
            if item.disabled or not item.is_stock_item or row.uom != item.stock_uom:
                frappe.throw('Material norm requires an active stock Item with its stock UOM.')
            basis = frappe.get_doc('Norm Basis', row.norm_basis)
            if not basis.active or basis.uom != work.uom:
                frappe.throw('Norm basis UOM must match the Work Type UOM. Use an explicit conversion factor.')
            for field in ('norm_qty', 'basis_qty', 'frequency', 'conversion_factor'):
                number(row.get(field), field, positive=field!='norm_qty')
        if self.approval_state == 'Approved':
            if not self.valid_to:
                frappe.throw('Approved material norms require Valid To so later versions can take effect without changing history.')
            filters = {'farm': self.farm, 'work_type': self.work_type, 'approval_state': 'Approved', 'name': ['!=', self.name]}
            for other in frappe.get_all(self.doctype, filters=filters, fields=['name','valid_from','valid_to']):
                if getdate(other.valid_from) <= getdate(self.valid_to or '9999-12-31') and getdate(self.valid_from) <= getdate(other.valid_to or '9999-12-31'):
                    frappe.throw('Approved material norms cannot overlap for the same Farm and Work Type.')

    def on_trash(self):
        if self.approval_state == 'Approved':
            frappe.throw('Approved norm versions cannot be deleted.')


def applicable_norm(profile, farm, work_type, date):
    norm = frappe.get_doc('Material Norm Profile', profile)
    norm.check_permission('read')
    if norm.farm != farm or norm.work_type != work_type or norm.approval_state != 'Approved':
        frappe.throw('Select an approved norm for this Farm and Work Type.')
    if getdate(date) < getdate(norm.valid_from) or (norm.valid_to and getdate(date) > getdate(norm.valid_to)):
        frappe.throw('Material norm is not effective on the work date.')
    return norm


class WorkPlan(DailyDocument):
    def validate_daily(self):
        if not self.lines:
            frappe.throw('Work Plan requires at least one task.')
        seen = set()
        for row in self.lines:
            row.farm = self.farm
            row.company = self.company
            row.posting_date = self.posting_date
            plot_scope(row)
            if not frappe.db.get_value('Farm Plot', row.farm_plot, 'active'):
                frappe.throw('Work requires an active Plot.')
            key = (row.crop_cycle, row.sucker_selection_batch, row.work_type)
            if key in seen:
                frappe.throw('Combine duplicate Cycle/Cohort/Work Type tasks into one line.')
            seen.add(key)
            work = frappe.get_doc('Work Type', row.work_type)
            work.check_permission('read')
            if not work.active:
                frappe.throw('Work Type is inactive.')
            row.uom = work.uom
            number(row.planned_qty, 'Planned quantity', positive=True)
            row.productivity_per_workday = number(work.productivity_per_workday, 'Productivity', positive=True)
            row.required_workdays = rule(labor_needed, row.planned_qty, row.productivity_per_workday)['required_workdays']
            if row.norm_profile:
                row.norm_version = applicable_norm(row.norm_profile, self.farm, row.work_type, self.posting_date).version
            else:
                row.norm_version = 0


class WorkResult(DailyDocument):
    def validate_daily(self):
        row = plan_line(self)
        number(self.completed_qty, 'Completed quantity')
        number(self.actual_workdays, 'Actual workdays')
        if frappe.db.exists(self.doctype, {'work_plan_line': self.work_plan_line, 'docstatus': 1, 'name': ['!=', self.name]}):
            frappe.throw('Each work plan line has one submitted daily result. Cancel/amend to correct it.')
        if self.docstatus == 1:
            rule(completion, row.planned_qty, self.completed_qty, self.unfinished_reason)


class LaborAllocationRecord(DailyDocument):
    def validate_daily(self):
        plan_line(self)
        amount = number(self.allocated_workdays, 'Allocated workdays', positive=True)
        if self.work_team:
            team = frappe.get_doc('Work Team', self.work_team)
            team.check_permission('read')
            if team.farm != self.farm or not team.active:
                frappe.throw('Work Team must be active in the same Farm.')
        if self.employee:
            employee = frappe.get_doc('Employee', self.employee, for_update=True)
            employee.check_permission('read')
            if employee.company != self.company or employee.status != 'Active':
                frappe.throw('Employee must be active in the same Company.')
            # Farm lock precedes Employee lock, ensuring cross-Farm staffing serializes.
            lock('Employee', self.employee)
            table=frappe.qb.DocType(self.doctype)
            used=[r[0] for r in (frappe.qb.from_(table).select(table.allocated_workdays)
                .where((table.employee==self.employee)&(table.posting_date==self.posting_date)&(table.docstatus==1)&(table.name!=self.name)).for_update().run())]
            if sum(flt(x) for x in used)+amount > 1.000001:
                frappe.throw('Employee cannot be allocated more than one workday per date.')
        elif not self.work_team or not self.allocation_note:
            frappe.throw('Aggregate allocation requires a Work Team and an explanatory note.')


class LaborSummary(DailyDocument):
    def validate_daily(self):
        values = rule(labor_summary, self.headcount, self.present, self.staffing_target, self.actual_workdays, self.area_ha)
        for field, value in values.items():
            self.set(field, value)
        if frappe.db.exists(self.doctype, {'farm': self.farm, 'posting_date': self.posting_date, 'work_category': self.work_category, 'work_area': self.work_area, 'docstatus': 1, 'name': ['!=', self.name]}):
            frappe.throw('One submitted labor summary is allowed per Farm/day/category/work area.')


class MaterialRequirementRecord(DailyDocument):
    def validate_daily(self):
        row = plan_line(self)
        if not row.norm_profile:
            frappe.throw('Work Plan Line has no approved material norm.')
        norm = applicable_norm(row.norm_profile, self.farm, row.work_type, self.posting_date)
        self.norm_profile, self.norm_version = norm.name, norm.version
        self.lines = []
        for source in norm.lines:
            values = {f: source.get(f) for f in ('item','uom','norm_basis','norm_qty','basis_qty','frequency','conversion_factor')}
            values['required_qty'] = rule(material_needed, row.planned_qty, source.norm_qty, source.basis_qty, source.frequency, source.conversion_factor)
            self.append('lines', values)
        if frappe.db.exists(self.doctype, {'work_plan_line': self.work_plan_line, 'docstatus': 1, 'name': ['!=', self.name]}):
            frappe.throw('One submitted material requirement is allowed per work plan line.')


def entry_detail(entry_name, detail_name, company):
    entry = frappe.get_doc('Stock Entry', entry_name, for_update=True)
    entry.check_permission('read')
    lock('Stock Entry', entry_name)
    if entry.docstatus != 1 or entry.company != company:
        frappe.throw('Stock Entry must be submitted in the same Company.')
    row = next((r for r in entry.items if r.name == detail_name), None)
    if not row:
        frappe.throw('Stock Entry Detail must belong to the selected Stock Entry.')
    return entry, row


class MaterialConsumptionRecord(DailyDocument):
    def validate_daily(self):
        result = frappe.get_doc('Daily Work Result', self.work_result)
        result.check_permission('read')
        if result.docstatus != 1 or any((self.get(f) or '') != (result.get(f) or '') for f in ('farm','farm_block','farm_plot','crop_cycle','sucker_selection_batch')) or getdate(result.posting_date) != getdate(self.posting_date):
            frappe.throw('Consumption must match a submitted Work Result for this Plot/day.')
        req = frappe.get_doc('Material Requirement', self.material_requirement)
        req.check_permission('read')
        if req.docstatus != 1 or req.work_plan_line != result.work_plan_line:
            frappe.throw('Material Requirement must match the Work Result task.')
        norm = next((r for r in req.lines if r.item == self.item), None)
        if not norm:
            frappe.throw('Item is not part of the task Material Requirement.')
        validate_warehouse(self.warehouse, self.company)
        entry, row = entry_detail(self.stock_entry, self.stock_entry_detail, self.company)
        if entry.purpose != 'Material Issue' or row.item_code != self.item or row.s_warehouse != self.warehouse or row.t_warehouse or getdate(entry.posting_date) != getdate(self.posting_date):
            frappe.throw('Consumption requires the matching dated Material Issue row from this Warehouse.')
        self.uom = row.stock_uom
        if self.uom != norm.uom:
            frappe.throw('Issue stock UOM does not match the norm.')
        if frappe.db.exists(self.doctype, {'stock_entry_detail': row.name, 'docstatus': 1, 'name': ['!=', self.name]}):
            frappe.throw('Issue row already belongs to another submitted consumption. Split ERP issue rows by task.')
        self.issued_qty = number(row.transfer_qty, 'Issued quantity', positive=True)
        used = number(self.consumed_qty, 'Consumed quantity')
        if used > self.issued_qty:
            frappe.throw('Consumed quantity exceeds issued stock.')
        self.remaining_qty = self.issued_qty-used

    def before_cancel(self):
        super().before_cancel()
        if frappe.db.exists('Material Recovery', {'consumption': self.name, 'docstatus': 1}):
            frappe.throw('Cancel material recoveries first.')


class MaterialRecoveryRecord(DailyDocument):
    def validate_daily(self):
        consumption = frappe.get_doc('Material Consumption', self.consumption)
        consumption.check_permission('read')
        lock('Material Consumption', self.consumption)
        if consumption.docstatus != 1 or any((self.get(f) or '') != (consumption.get(f) or '') for f in ('farm','farm_block','farm_plot','crop_cycle','sucker_selection_batch')):
            frappe.throw('Recovery must match a submitted Material Consumption scope.')
        if getdate(self.posting_date) < getdate(consumption.posting_date):
            frappe.throw('Recovery cannot precede consumption.')
        amount = number(self.recovered_qty, 'Recovered quantity', positive=True)
        used = sum(flt(x) for x in frappe.get_all(self.doctype, filters={'consumption': self.consumption, 'docstatus': 1, 'name': ['!=', self.name]}, pluck='recovered_qty'))
        if used+amount > flt(consumption.remaining_qty)+0.000001:
            frappe.throw('Recovery exceeds unconsumed issued quantity.')
        entry, row = entry_detail(self.stock_entry, self.stock_entry_detail, self.company)
        if entry.purpose != 'Material Receipt' or row.item_code != consumption.item or row.stock_uom != consumption.uom or not row.t_warehouse or row.s_warehouse or getdate(entry.posting_date) != getdate(self.posting_date):
            frappe.throw('Recovery requires a matching dated Material Receipt row.')
        if abs(flt(row.transfer_qty)-amount) > 0.000001:
            frappe.throw('Recovery quantity must equal its ERP receipt row.')
        if frappe.db.exists(self.doctype, {'stock_entry_detail': row.name, 'docstatus': 1, 'name': ['!=', self.name]}):
            frappe.throw('Receipt row already belongs to another recovery.')


class CancellationRecord(DailyDocument):
    def validate_daily(self):
        if whole_count(self.bunch_qty, 'Cancelled bunches') < 1:
            frappe.throw('Cancelled bunches must be a positive whole count.')
        if getdate(self.expected_harvest_date) < getdate(self.posting_date):
            frappe.throw('Expected harvest date cannot precede cancellation.')
        reason = frappe.get_doc('Cancellation Reason', self.reason)
        if not reason.active or not frappe.db.get_value('Cancellation Reason Group', reason.reason_group, 'active'):
            frappe.throw('Cancellation reason/group is inactive.')
        if self.source_operation:
            operation = frappe.get_doc('Bunch Operation', self.source_operation)
            operation.check_permission('read')
            lock('Bunch Operation', self.source_operation)
            if operation.docstatus != 1 or any((self.get(f) or '') != (operation.get(f) or '') for f in ('farm','farm_block','farm_plot','crop_cycle','sucker_selection_batch')):
                frappe.throw('Source operation must match this submitted production scope.')
            if getdate(self.posting_date) < getdate(operation.operation_date) or (operation.expected_harvest_date and getdate(self.expected_harvest_date) != getdate(operation.expected_harvest_date)):
                frappe.throw('Cancellation date/expected harvest must match the source operation.')
            used = sum(flt(x) for x in frappe.get_all(self.doctype, filters={'source_operation': self.source_operation,'docstatus':1,'name':['!=',self.name]}, pluck='bunch_qty'))
            if used+self.bunch_qty > operation.net_bunch_qty:
                frappe.throw('Cancelled bunches exceed the source operation net bunches.')

    def on_submit(self):
        invalidate_draft_forecasts(self)

    def on_cancel(self):
        invalidate_draft_forecasts(self)


def invalidate_draft_forecasts(doc):
    # Released snapshots remain immutable. A new revision explicitly records these actuals.
    for name in frappe.get_all('Harvest Forecast', filters={'crop_cycle':doc.crop_cycle,'sucker_selection_batch':doc.sucker_selection_batch or '', 'supply_state':['in',['Draft','Released']]}, pluck='name'):
        forecast = frappe.get_doc('Harvest Forecast', name)
        forecast.save()


def cancellation_adjustment(doc):
    """Only losses for this harvest period, at the same cycle/cohort grain."""
    from lotus_farm.operations_rules import remaining_bunches
    rows = frappe.get_all('Bunch Cancellation', filters={
        'crop_cycle': doc.crop_cycle, 'sucker_selection_batch': doc.sucker_selection_batch or '',
        'docstatus': 1, 'expected_harvest_date': ['between',[doc.period_start_date,doc.period_end_date]],
    }, fields=['name','bunch_qty','reason','posting_date','expected_harvest_date'], order_by='name')
    doc.cancellation_bunch_qty = sum(flt(r.bunch_qty) for r in rows)
    doc.net_source_bunch_qty = rule(remaining_bunches, doc.source_bunch_qty, [r.bunch_qty for r in rows])
    if rows:
        snapshot = json.loads(doc.source_snapshot or '{}')
        snapshot['pre_cancellation_bunch_qty'] = doc.source_bunch_qty
        snapshot['cancellations'] = rows
        doc.source_snapshot = json.dumps(snapshot, default=str, sort_keys=True)


class PlantingRecord(DailyDocument):
    def validate_daily(self):
        if whole_count(self.plant_qty, 'Plants') < 1:
            frappe.throw('Planting requires positive plants.')
        area = number(self.area_ha, 'Planted area', positive=True)
        if area > flt(frappe.db.get_value('Farm Plot', self.farm_plot, 'area_ha')):
            frappe.throw('Planted area exceeds Plot area.')


class DiseaseRecord(DailyDocument):
    def validate_daily(self):
        if whole_count(self.affected_plants, 'Affected plants') < 1:
            frappe.throw('Disease observation requires positive affected plants.')
        if not frappe.db.get_value('Disease', self.disease, 'active'):
            frappe.throw('Disease is inactive.')


class MeasurementRecord(DailyDocument):
    def validate_daily(self):
        if whole_count(self.sample_count, 'Sample count') < 1:
            frappe.throw('Measurement requires samples.')
        number(self.average_length, 'Length', positive=True)
        number(self.average_diameter, 'Diameter', positive=True)


class IncomingQC(DailyDocument):
    def validate_daily(self):
        lot = frappe.get_doc('Harvest Lot', self.harvest_lot)
        lot.check_permission('read')
        lock('Harvest Lot', self.harvest_lot)
        if lot.docstatus != 1 or lot.farm != self.farm or getdate(self.posting_date) < getdate(lot.received_date):
            frappe.throw('Incoming QC requires a submitted lot from this Farm, after receipt.')
        self.received_kg = lot.released_raw_kg
        self.accepted_kg = number(self.accepted_kg, 'Accepted kg')
        if self.accepted_kg > self.received_kg:
            frappe.throw('Accepted kg exceeds lot weight.')
        self.rejected_kg = self.received_kg-self.accepted_kg
        seen = set()
        for row in self.defects:
            if row.defect_reason in seen:
                frappe.throw('Duplicate defect reason.')
            seen.add(row.defect_reason)
            whole_count(row.affected_units, 'Affected units')
            whole_count(row.occurrences, 'Occurrences')
            if row.occurrences < row.affected_units:
                frappe.throw('Defect occurrences must cover affected units.')
        if self.rejected_kg and not self.defects:
            frappe.throw('Rejected incoming weight requires defect reasons.')
        if frappe.db.exists(self.doctype, {'harvest_lot':self.harvest_lot,'docstatus':1,'name':['!=',self.name]}):
            frappe.throw('One submitted incoming inspection is allowed per Harvest Lot.')

    def before_cancel(self):
        super().before_cancel()
        source, run = frappe.qb.DocType('Packout Run Source'), frappe.qb.DocType('Packout Run')
        if (frappe.qb.from_(source).join(run).on(source.parent==run.name).select(run.name)
            .where((source.harvest_lot==self.harvest_lot)&(run.docstatus==1)).run()):
            frappe.throw('Cancel dependent Packout Runs before incoming QC.')


def incoming_packout_guard(doc, method=None):
    # Existing submitted historical runs remain readable; all new packouts require incoming QC.
    if doc.docstatus == 2:
        return
    for row in doc.sources or []:
        qc = frappe.get_all('Incoming Quality Inspection', filters={'harvest_lot': row.harvest_lot,'docstatus':1}, fields=['name','accepted_kg'])
        if not qc:
            if doc.is_new() or doc.docstatus == 1:
                frappe.throw('Incoming QC must be submitted before packing this lot.')
            continue
        src, run = frappe.qb.DocType('Packout Run Source'), frappe.qb.DocType('Packout Run')
        used = (frappe.qb.from_(src).join(run).on(src.parent==run.name).select(src.input_kg)
            .where((src.harvest_lot==row.harvest_lot)&(run.docstatus==1)&(run.name!=doc.name)).run())
        if sum(flt(x[0]) for x in used)+flt(row.input_kg) > flt(qc[0].accepted_kg)+0.0005:
            frappe.throw('Packout input exceeds incoming QC accepted weight.')


def stock_context_cancel(doc, method=None):
    refs = [('Material Consumption','stock_entry'),('Material Recovery','stock_entry'),('Secondary Product Movement','stock_entry')]
    for doctype, field in refs:
        if frappe.db.exists(doctype, {field:doc.name,'docstatus':1}):
            frappe.throw('Cancel submitted Lotus material contexts before reversing ERP stock.')


def close_checks(farm, date):
    checks = []
    def add(code, ok, message, doctype='', name=''):
        checks.append(dict(check_code=code, status='Pass' if ok else 'Block', message=message,
                           reference_doctype=doctype, reference_name=name))
    filters = {'farm':farm, 'posting_date':date, 'docstatus':['<',2]}
    for doctype in DAILY_TYPES:
        for row in frappe.get_all(doctype, filters=filters, fields=['name','docstatus']):
            if row.docstatus == 0:
                add('draft',False,'Submit or delete unfinished daily drafts.',doctype,row.name)
    plans = frappe.get_all('Daily Work Plan', filters={**filters,'docstatus':1}, pluck='name')
    add('work_plan',bool(plans),'At least one submitted Work Plan is required.')
    for name in plans:
        plan = frappe.get_doc('Daily Work Plan', name)
        for line in plan.lines:
            results = frappe.get_all('Daily Work Result', filters={'work_plan_line':line.name,'docstatus':1}, fields=['name','completed_qty','actual_workdays','unfinished_reason'])
            add('work_result',len(results)==1,'One submitted result is required per task.','Daily Work Plan',name)
            if not results:
                continue
            result = results[0]
            add('unfinished_reason',flt(result.completed_qty)>=flt(line.planned_qty) or bool((result.unfinished_reason or '').strip()),'Unfinished tasks require a reason.','Daily Work Result',result.name)
            allocated = sum(flt(x) for x in frappe.get_all('Labor Allocation', filters={'work_plan_line':line.name,'docstatus':1}, pluck='allocated_workdays'))
            add('labor',flt(result.actual_workdays)<=allocated+0.000001,'Actual labor cannot exceed submitted allocation.','Daily Work Result',result.name)
            if flt(result.completed_qty)>0:
                add('labor_evidence',flt(result.actual_workdays)>0,'Completed work requires actual labor.','Daily Work Result',result.name)
            if line.norm_profile:
                requirements = frappe.get_all('Material Requirement', filters={'work_plan_line':line.name,'docstatus':1},pluck='name')
                add('material_requirement',len(requirements)==1,'Task requires its submitted material requirement.','Daily Work Plan',name)
                if requirements and flt(result.completed_qty)>0:
                    req = frappe.get_doc('Material Requirement',requirements[0])
                    for material in req.lines:
                        if not flt(material.required_qty):
                            continue
                        contexts = frappe.get_all('Material Consumption',filters={'work_result':result.name,'item':material.item,'docstatus':1},fields=['name','remaining_qty'])
                        add('consumption',bool(contexts),'Completed material task requires actual stock consumption.','Daily Work Result',result.name)
                        for context in contexts:
                            returned = sum(flt(x) for x in frappe.get_all('Material Recovery',filters={'consumption':context.name,'docstatus':1},pluck='recovered_qty'))
                            add('recovery',abs(flt(context.remaining_qty)-returned)<=0.000001,'Issued quantity must reconcile to consumed plus recovered.','Material Consumption',context.name)
    for doctype, field in DATE_FIELDS.items():
        for row in frappe.get_all(doctype,filters={'farm':farm,field:date,'docstatus':['<',2]},fields=['name','docstatus']):
            add('production_submitted',row.docstatus==1,'Production records must be submitted. Cancel or delete unused drafts.',doctype,row.name)
            if doctype=='Harvest Actual' and row.docstatus==1:
                actual=frappe.get_doc(doctype,row.name)
                source,lot=frappe.qb.DocType('Harvest Lot Source'),frappe.qb.DocType('Harvest Lot')
                amounts=(frappe.qb.from_(source).join(lot).on(source.parent==lot.name).select(source.contributed_kg)
                    .where((source.harvest_actual==row.name)&(lot.docstatus==1)).run())
                add('harvest_receipt',abs(sum(flt(x[0]) for x in amounts)-flt(actual.saleable_weight_kg))<=0.0005,
                    'All released harvest weight must be traced into submitted receiving lots.',doctype,row.name)
            if doctype=='Harvest Lot' and row.docstatus==1:
                add('incoming_qc',bool(frappe.db.exists('Incoming Quality Inspection',{'harvest_lot':row.name,'docstatus':1})),'Received lot requires incoming QC.',doctype,row.name)
            if doctype=='Packout Run' and row.docstatus==1:
                run = frappe.get_doc(doctype,row.name)
                add('mass_balance',abs(flt(run.mass_variance_kg))<=flt(frappe.db.get_single_value('Lotus Farm Settings','mass_balance_tolerance_kg')),'Packout mass balance must reconcile.',doctype,row.name)
                add('stock_posted',bool(run.stock_entry and frappe.db.get_value('Stock Entry',run.stock_entry,'docstatus')==1),'Finished goods require a submitted ERP stock entry.',doctype,row.name)
    for name in frappe.get_all('Integration Event',filters={'farm':farm,'status':['in',['Pending','Failed']]},pluck='name'):
        add('integration',False,'Resolve unfinished integration events before closing.','Integration Event',name)
    return checks


class DailyClose(Document):
    def validate(self):
        check_farm(self)
        lock('Farm',self.farm)
        company_scope(self)
        if self.amended_from and not (self.amendment_reason or '').strip():
            frappe.throw('Amendment reason is required.')
        if self.docstatus != 1:
            self.set('checks',close_checks(self.farm,self.posting_date))
            self.snapshot_hash = canonical_hash([r.as_dict() for r in self.checks])

    def before_submit(self):
        require_role('Lotus Farm Manager')
        lock('Farm',self.farm)
        if frappe.db.exists(self.doctype,{'farm':self.farm,'posting_date':self.posting_date,'docstatus':1,'name':['!=',self.name]}):
            frappe.throw('Farm day is already closed.')
        self.set('checks',close_checks(self.farm,self.posting_date))
        blockers=[r.message for r in self.checks if r.status=='Block']
        if blockers:
            frappe.throw('Daily close blocked: '+ '; '.join(dict.fromkeys(blockers)))
        self.snapshot_hash=canonical_hash([r.as_dict() for r in self.checks])
        self.closed_by,self.closed_at=frappe.session.user,now_datetime()

    def before_update_after_submit(self):
        from frappe.utils import get_datetime
        before=self.get_doc_before_save()
        keys=('name','idx','check_code','reference_doctype','reference_name','status','message')
        def checks(doc):
            return [tuple(r.get(k) for k in keys) for r in doc.checks]
        unchanged=(self.company==before.company and self.farm==before.farm
                   and getdate(self.posting_date)==getdate(before.posting_date)
                   and self.snapshot_hash==before.snapshot_hash
                   and self.closed_by==before.closed_by
                   and get_datetime(self.closed_at)==get_datetime(before.closed_at)
                   and checks(self)==checks(before))
        if not unchanged:
            frappe.throw('Submitted daily close snapshot is immutable.')

    def before_cancel(self):
        require_role('Lotus Farm Manager')
        lock('Farm',self.farm)
        if not (self.reopen_reason or '').strip():
            frappe.throw('Reopen reason is required before cancelling daily close.')


class SourceRegistry(Document):
    def validate(self):
        if not re.fullmatch(r'[0-9a-f]{64}',self.sha256 or ''):
            frappe.throw('Source file hash must be lowercase SHA-256.')
        before=self.get_doc_before_save()
        if before and frappe.db.exists('Source Import Batch',{'source_file':self.name}):
            for field in ('source_key','source_path','source_filename','sha256','business_period'):
                if self.get(field)!=before.get(field):
                    frappe.throw('Used source identity/hash is immutable; register a new file version.')


class LegacyMap(Document):
    def validate(self):
        check_farm(self)
        company_scope(self)
        before=self.get_doc_before_save()
        if before and before.approval_state=='Approved':
            for field in ('legacy_key','legacy_company','legacy_source_unit','legacy_farm','company','farm','approval_state','approved_by','approved_at'):
                if self.get(field)!=before.get(field):
                    frappe.throw('Approved organization mapping is immutable.')
        elif self.approval_state=='Approved':
            require_role('Lotus Farm Manager')
            self.approved_by,self.approved_at=frappe.session.user,now_datetime()


class ImportBatch(Document):
    def validate(self):
        check_farm(self)
        lock('Farm',self.farm)
        source=frappe.get_doc('Source File Registry',self.source_file)
        source.check_permission('read')
        self.source_hash=source.sha256
        if not self.rows:
            frappe.throw('Import batch requires source rows.')
        seen=set();resolved=0
        for row in self.rows:
            if row.row_key in seen or int(row.source_row or 0)<1:
                frappe.throw('Import row keys must be unique and source rows positive.')
            seen.add(row.row_key)
            try:raw=json.loads(row.raw_json)
            except (ValueError,TypeError):frappe.throw('Import row raw JSON is invalid.')
            if row.source_hash!=canonical_hash(raw):
                frappe.throw('Import row hash must match its raw JSON.')
            if row.row_status=='Imported':
                mapping=frappe.get_all('Legacy Organization Map',filters={'legacy_key':row.legacy_org_key,'approval_state':'Approved','farm':self.farm},pluck='name')
                if not mapping:
                    frappe.throw('Imported rows require an approved organization mapping to this Farm.')
                if not row.target_doctype or not row.target_name or not frappe.db.exists(row.target_doctype,row.target_name):
                    frappe.throw('Imported row must reference an existing target document.')
                target=frappe.get_doc(row.target_doctype,row.target_name)
                target.check_permission('read')
                if not target.meta.has_field('farm') or target.get('farm')!=self.farm:
                    frappe.throw('Imported target must belong to this Farm.')
                if target.meta.has_field('source_import_batch') and target.source_import_batch!=self.name:
                    frappe.throw('Imported target must retain this import batch lineage.')
                prior=frappe.db.sql('''select r.name from `tabSource Import Row` r join `tabSource Import Batch` b on b.name=r.parent where b.docstatus=1 and b.source_file=%s and r.row_key=%s and r.row_status='Imported' and b.name!=%s limit 1 FOR UPDATE''',(self.source_file,row.row_key,self.name))
                if prior:
                    frappe.throw('Source row was already imported in a submitted batch.')
                resolved+=1
            elif row.row_status=='Rejected':
                if not row.reject_reason or not row.reject_owner:
                    frappe.throw('Rejected row requires a reason and an owner.')
                resolved+=1
        self.resolved_percent=resolved/len(self.rows)*100

    def before_submit(self):
        require_role('Lotus Integration User')
        lock('Source File Registry',self.source_file)
        # Recheck under the source lock so retries cannot submit duplicate source rows.
        self.validate()
        if self.resolved_percent < 99.5:
            frappe.throw('At least 99.5% of scoped rows must be imported or explicitly rejected.')


def live_loss_fraction(doc):
    """New submitted cancellations reduce current ATP, without rewriting the release snapshot."""
    current = sum(flt(r) for r in frappe.get_all("Bunch Cancellation", filters={
        "crop_cycle": doc.crop_cycle, "sucker_selection_batch": doc.sucker_selection_batch or "",
        "docstatus": 1, "expected_harvest_date": ["between", [doc.period_start_date, doc.period_end_date]],
    }, pluck="bunch_qty"))
    recorded = flt(doc.get("cancellation_bunch_qty"))
    net = doc.get("net_source_bunch_qty")
    if doc.formula_version != 'lotus-forecast/5' or net is None:
        net = doc.source_bunch_qty
    return min(max(current-recorded, 0) / flt(net), 1) if flt(net) else 0


def packout_losses(doc):
    totals={'Reject':0,'Process Loss':0}
    for row in doc.loss_details or []:
        totals[row.loss_type]+=number(row.weight_kg,'Loss weight',positive=True)
    if abs(totals['Reject']-flt(doc.reject_kg))>0.0005 or abs(totals['Process Loss']-flt(doc.other_loss_kg))>0.0005:
        frappe.throw('Packout loss details must explain all rejected and process-loss weight.')


class SecondaryMovement(DailyDocument):
    def validate_daily(self):
        run=frappe.get_doc('Packout Run',self.packout_run)
        run.check_permission('read')
        if run.docstatus!=1 or run.farm!=self.farm or getdate(self.posting_date)<getdate(run.packing_date):
            frappe.throw('Secondary movement requires a submitted packout in the same Farm.')
        output=next((r for r in run.outputs if r.item==self.item and r.output_type=='Secondary'),None)
        if not output:
            frappe.throw('Item must be a secondary output from this Packout Run.')
        if not run.stock_entry or frappe.db.get_value('Stock Entry',run.stock_entry,'docstatus')!=1:
            frappe.throw('Post the packout stock before recording secondary movement.')
        entry,row=entry_detail(self.stock_entry,self.stock_entry_detail,self.company)
        if entry.purpose not in ('Material Issue','Material Transfer') or row.item_code!=self.item or row.stock_uom!='Kg' or not row.s_warehouse or getdate(entry.posting_date)!=getdate(self.posting_date):
            frappe.throw('Secondary movement must match its dated ERP stock issue/transfer row in Kg.')
        batch=row.batch_no
        if row.serial_and_batch_bundle:
            bundle=frappe.get_doc('Serial and Batch Bundle',row.serial_and_batch_bundle)
            if len(bundle.entries)!=1:
                frappe.throw('Secondary movement requires one Batch.')
            batch=bundle.entries[0].batch_no
        if batch!=output.batch:
            frappe.throw('Secondary movement Batch must match its source packout.')
        if abs(number(self.quantity_kg,'Secondary kg',positive=True)-flt(row.transfer_qty))>0.0005:
            frappe.throw('Secondary movement quantity must equal the ERP stock row.')
        if frappe.db.exists(self.doctype,{'stock_entry_detail':row.name,'docstatus':1,'name':['!=',self.name]}):
            frappe.throw('Stock row already has a submitted secondary movement.')


class CycleClose(DailyDocument):
    def validate_daily(self):
        if self.sucker_selection_batch:
            frappe.throw('Cycle close covers the entire Cycle; leave Cohort blank.')
        cycle=frappe.get_doc('Crop Cycle',self.crop_cycle)
        if cycle.cycle_type=='Ratoon':
            # The day scope validator normally requires a cohort only for row-level actuals.
            pass
        self.area_ha=frappe.db.get_value('Farm Plot',self.farm_plot,'area_ha')
        actuals=frappe.get_all('Harvest Actual',filters={'crop_cycle':self.crop_cycle,'docstatus':1},fields=['name','harvested_bunch_qty','gross_weight_kg','saleable_weight_kg'])
        self.harvested_bunch_qty=sum(flt(r.harvested_bunch_qty) for r in actuals)
        self.gross_harvest_kg=sum(flt(r.gross_weight_kg) for r in actuals)
        self.released_harvest_kg=sum(flt(r.saleable_weight_kg) for r in actuals)
        self.planted_qty=sum(flt(v) for v in frappe.get_all('Planting Event',filters={'crop_cycle':self.crop_cycle,'docstatus':1},pluck='plant_qty'))
        self.cancelled_bunch_qty=sum(flt(v) for v in frappe.get_all('Bunch Cancellation',filters={'crop_cycle':self.crop_cycle,'docstatus':1},pluck='bunch_qty'))
        self.actual_workdays=sum(flt(v) for v in frappe.get_all('Daily Work Result',filters={'crop_cycle':self.crop_cycle,'docstatus':1},pluck='actual_workdays'))
        self.finished_kg=self.secondary_kg=self.reject_kg=self.process_loss_kg=0
        actual_names={r.name for r in actuals}
        run_evidence=[]
        for name in frappe.get_all('Packout Run',filters={'farm':self.farm,'docstatus':1},pluck='name'):
            run=frappe.get_doc('Packout Run',name);share=0
            for source in run.sources:
                lot=frappe.get_doc('Harvest Lot',source.harvest_lot)
                contributing=sum(flt(r.contributed_kg) for r in lot.sources if r.harvest_actual in actual_names)
                if lot.released_raw_kg and run.input_kg:
                    share+=flt(source.input_kg)/flt(run.input_kg)*contributing/flt(lot.released_raw_kg)
            if share:
                run_evidence.append({'packout_run':run.name,'share':share})
                self.finished_kg+=sum(flt(r.net_kg) for r in run.outputs if r.output_type!='Secondary')*share
                self.secondary_kg+=sum(flt(r.net_kg) for r in run.outputs if r.output_type=='Secondary')*share
                self.reject_kg+=flt(run.reject_kg)*share
                self.process_loss_kg+=flt(run.other_loss_kg)*share
        self.tons_per_ha=self.gross_harvest_kg/1000/number(self.area_ha,'Cycle area',positive=True)
        evidence=dict(actuals=actuals,packouts=run_evidence,metrics={f:self.get(f) for f in ('area_ha','planted_qty','cancelled_bunch_qty','harvested_bunch_qty','gross_harvest_kg','released_harvest_kg','finished_kg','secondary_kg','reject_kg','process_loss_kg','tons_per_ha','actual_workdays')})
        self.snapshot_json=json.dumps(evidence,default=str,sort_keys=True)
        self.snapshot_hash=canonical_hash(evidence)

    def before_submit(self):
        require_role('Lotus Farm Manager')
        lock('Crop Cycle',self.crop_cycle)
        if frappe.db.exists(self.doctype,{'crop_cycle':self.crop_cycle,'docstatus':1,'name':['!=',self.name]}):
            frappe.throw('Cycle already has a submitted closing report.')
        if frappe.db.exists('Harvest Forecast',{'crop_cycle':self.crop_cycle,'supply_state':'Released'}):
            frappe.throw('Close/reconcile released forecasts before ending this Cycle.')
        for doctype in DAILY_TYPES:
            meta=frappe.get_meta(doctype)
            if not meta.has_field('crop_cycle'):
                continue
            for row in frappe.get_all(doctype,filters={'crop_cycle':self.crop_cycle,'docstatus':['<',2]},fields=['name','docstatus','posting_date']):
                if row.docstatus==0 or not frappe.db.exists('Daily Production Close',{'farm':self.farm,'posting_date':row.posting_date,'docstatus':1}):
                    frappe.throw('Submit all Cycle transactions and close their Farm days first.')
        for actual_name in frappe.get_all('Harvest Actual',filters={'crop_cycle':self.crop_cycle,'docstatus':1},pluck='name'):
            actual=frappe.get_doc('Harvest Actual',actual_name)
            source,lot=frappe.qb.DocType('Harvest Lot Source'),frappe.qb.DocType('Harvest Lot')
            received=(frappe.qb.from_(source).join(lot).on(source.parent==lot.name).select(lot.name,source.contributed_kg)
                .where((source.harvest_actual==actual_name)&(lot.docstatus==1)).run())
            if abs(sum(flt(r[1]) for r in received)-flt(actual.saleable_weight_kg))>0.0005:
                frappe.throw('Cycle harvest must be fully traced into receiving lots before closing.')
            for lot_name,_ in received:
                qc=frappe.get_all('Incoming Quality Inspection',filters={'harvest_lot':lot_name,'docstatus':1},fields=['accepted_kg'])
                if not qc:
                    frappe.throw('Cycle lots require submitted incoming QC before closing.')
                src,run=frappe.qb.DocType('Packout Run Source'),frappe.qb.DocType('Packout Run')
                packed=(frappe.qb.from_(src).join(run).on(src.parent==run.name).select(run.name,src.input_kg,run.stock_entry)
                    .where((src.harvest_lot==lot_name)&(run.docstatus==1)).run())
                if abs(sum(flt(r[1]) for r in packed)-flt(qc[0].accepted_kg))>0.0005:
                    frappe.throw('All QC accepted Cycle weight must be packed before closing.')
                if any(not r[2] or frappe.db.get_value('Stock Entry',r[2],'docstatus')!=1 for r in packed):
                    frappe.throw('Cycle finished goods must be posted to ERP stock before closing.')
        from lotus_farm.controls import command
        cycle=frappe.get_doc('Crop Cycle',self.crop_cycle)
        cycle.status='Closed'
        with command(cycle,'cycle_close'):
            cycle.save()

    def before_update_after_submit(self):
        before=self.get_doc_before_save()
        if self.snapshot_json!=before.snapshot_json or self.snapshot_hash!=before.snapshot_hash:
            frappe.throw('Submitted Cycle closing metrics are immutable.')

    def before_cancel(self):
        require_role('Lotus Farm Manager')
        lock('Farm',self.farm)
        if not (self.reopen_reason or '').strip():
            frappe.throw('Cycle reopen reason is required.')
        from lotus_farm.controls import command
        cycle=frappe.get_doc('Crop Cycle',self.crop_cycle)
        cycle.status='Harvesting'
        with command(cycle,'cycle_close'):
            cycle.save()


class LegacyCycleMapping(Document):
    def validate(self):
        require_role('Lotus Farm Manager')
        check_farm(self)
        lock('Farm',self.farm)
        cycle=frappe.get_doc('Crop Cycle',self.crop_cycle);cycle.check_permission('write')
        plot=frappe.get_doc('Farm Plot',self.farm_plot);plot.check_permission('read')
        if cycle.farm!=self.farm or plot.farm!=self.farm or cycle.farm_block!=plot.farm_block or not plot.active:
            frappe.throw('Legacy Cycle and active Plot must belong to the same Farm/Block.')
        if cycle.farm_plot:
            frappe.throw('Only unmapped legacy cycles can use this mapping command.')
        if not (self.reason or '').strip():
            frappe.throw('Legacy cycle mapping requires a reason.')
        if frappe.db.exists('Harvest Forecast',{'crop_cycle':cycle.name,'supply_state':'Released'}):
            frappe.throw('Close/reconcile released forecasts before mapping legacy land.')
        if cycle.parent_cycle:
            parent=frappe.get_doc('Crop Cycle',cycle.parent_cycle)
            if parent.farm_plot!=plot.name:
                frappe.throw('Map the parent cycle to this Plot first.')

    def before_submit(self):
        self.validate()
        lock('Crop Cycle',self.crop_cycle)
        if frappe.db.get_value('Crop Cycle',self.crop_cycle,'farm_plot'):
            frappe.throw('Legacy Cycle was already mapped.')
        if frappe.db.exists('Crop Cycle',{'farm_plot':self.farm_plot,'cycle_no':frappe.db.get_value('Crop Cycle',self.crop_cycle,'cycle_no')}):
            frappe.throw('Plot already has this Cycle number.')
        # Deliberately do not overwrite submitted actuals or frozen forecast snapshots.
        # This reviewed mapping augments the land reference on the legacy cycle only.
        frappe.db.set_value('Crop Cycle',self.crop_cycle,'farm_plot',self.farm_plot)

    def before_cancel(self):
        frappe.throw('Submitted legacy cycle mappings are permanent audit records.')


class CancellationReasonMaster(Document):
    def validate(self):
        before=self.get_doc_before_save()
        if before and frappe.db.exists('Bunch Cancellation',{'reason':self.name}):
            if any(self.get(f)!=before.get(f) for f in ('reason_code','reason_name','reason_group')):
                frappe.throw('Used cancellation classification cannot be reassigned. Create a new reason; deactivate the old one.')


class ReasonAliasMaster(Document):
    def validate(self):
        from lotus_farm.source_data import source_text
        self.legacy_alias=(source_text(self.legacy_alias) or '').casefold()
        if not self.legacy_alias:
            frappe.throw('Legacy alias is required.')
