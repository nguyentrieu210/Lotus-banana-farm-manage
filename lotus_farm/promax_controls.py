"""Controls for the remaining ProMax masters and integration records."""
import json
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime
from lotus_farm.controls import check_farm, command_allowed, validate_version, validate_warehouse, local_timestamp, require_role
from lotus_farm.rules import canonical_hash, RuleError
from lotus_farm.promax_rules import geometry, coordinates


class GeometryMaster(Document):
    def validate(self):
        check_farm(self)
        plot=frappe.get_doc('Farm Plot',self.farm_plot);plot.check_permission('read')
        if plot.farm!=self.farm:frappe.throw('Geometry Plot must belong to the Farm.')
        validate_version(self,'farm_plot',('Lotus Farm Manager',))
        try:self.geojson=json.dumps(geometry(self.geojson),separators=(',',':'))
        except (ValueError,KeyError,TypeError,RuleError) as exc:frappe.throw(str(exc))
    def on_trash(self):
        if self.approval_state=='Approved':frappe.throw('Approved geometry is retained for audit.')


class DeviceMaster(Document):
    def validate(self):
        check_farm(self)
        require_role('Lotus Integration User')
        if self.unit!='Kg' or getdate(self.calibration_due)<getdate(self.calibrated_on):
            frappe.throw('Scale requires Kg and a valid calibration period.')
        user=frappe.get_doc('User',self.integration_user)
        if not user.enabled or (user.name!='Administrator' and 'Lotus Integration User' not in frappe.get_roles(user.name)):
            frappe.throw('Bind the device to an enabled Lotus Integration User.')
        before=self.get_doc_before_save()
        if before and any(self.get(f)!=before.get(f) for f in ('farm','device_id','integration_user')):
            frappe.throw('Device identity and user binding are immutable; register a replacement.')


class ScheduleMaster(Document):
    def validate(self):
        check_farm(self)
        validate_version(self,'rule_name',('Lotus Farm Manager',))
        if not -365 <= int(self.offset_days or 0) <= 365 or int(self.repeat_days or 0)<0 or getdate(self.valid_to)<getdate(self.valid_from):
            frappe.throw('Schedule offsets and effective period are invalid.')
        if not -120 <= int(self.get('offset_months') or 0) <= 120 or not 0 <= int(self.get('repeat_months') or 0) <= 120:
            frappe.throw('Khoảng tháng lịch không hợp lệ.')
        if self.get('repeat_months') and self.repeat_days:
            frappe.throw('Chỉ chọn lặp theo ngày hoặc theo tháng lịch.')
        if self.norm_profile:
            profile=frappe.get_doc('Material Norm Profile',self.norm_profile);profile.check_permission('read')
            if profile.farm!=self.farm or profile.work_type!=self.work_type or profile.approval_state!='Approved':
                frappe.throw('Schedule norm must be approved for the same Farm and Work Type.')
    def on_trash(self):
        if self.approval_state=='Approved':frappe.throw('Approved schedules cannot be deleted.')


class CaptureRecord(Document):
    def validate(self):
        check_farm(self)
        if not self.is_new() or not command_allowed(self,'field_capture'):
            frappe.throw('Use the field capture command; received evidence is immutable.')
        if self.captured_by!=frappe.session.user:frappe.throw('Capture user must match the signed-in user.')
        self.captured_at=local_timestamp(self.captured_at)
        if self.captured_at>now_datetime():frappe.throw('Capture cannot be in the future.')
        if self.latitude is not None and self.longitude is not None:
            try:coordinates(self.latitude,self.longitude)
            except RuleError as exc:frappe.throw(str(exc))
        if float(self.gps_accuracy_m or 0)<0:frappe.throw('GPS accuracy cannot be negative.')
        self.event_key=canonical_hash([self.captured_by,self.client_event_id])
        self.payload_hash=canonical_hash(json.loads(self.payload_json))
        self.server_received_at=now_datetime()
    def on_trash(self):frappe.throw('Field evidence cannot be deleted.')


class ImportMapping(Document):
    def validate(self):
        require_role('Lotus Integration User')
        validate_version(self,'mapping_name',('Lotus Integration User',))
        from lotus_farm.importing import IMPORT_FIELDS
        if self.target_doctype not in IMPORT_FIELDS:frappe.throw('Target is outside the controlled import list.')
        if int(self.header_row or 0)<1 or int(self.first_data_row or 0)<=int(self.header_row):frappe.throw('Specify header and first data row explicitly.')
        if self.decimal_mark not in ('.',',') or self.grouping_mark==self.decimal_mark:frappe.throw('Decimal and grouping marks must differ.')
        if self.approval_state=='Approved' and not json.loads(self.business_key_columns or '[]'):
            frappe.throw('Approve explicit stable business key columns before using this mapping.')
        seen=set()
        for row in self.fields:
            if row.target_field not in IMPORT_FIELDS[self.target_doctype] or row.target_field in seen:
                frappe.throw('Only unique approved target fields can be mapped.')
            seen.add(row.target_field)
            if row.value_map_json:
                if not isinstance(json.loads(row.value_map_json),dict):frappe.throw('Value map must be a JSON object.')
    def on_trash(self):
        if self.approval_state=='Approved':frappe.throw('Approved mapping is immutable.')


class IntegrationTask(Document):
    def validate(self):
        check_farm(self)
        require_role('Lotus Integration User')
        self.event_key=canonical_hash([self.source_system,self.external_id,self.source_hash])
        registry=frappe.get_doc('Source File Registry',self.source_file);registry.check_permission('read')
        if registry.sha256!=self.source_hash:frappe.throw('Task hash must match the registered source.')
        before=self.get_doc_before_save()
        if self.is_new() and self.status!='Pending':frappe.throw('New tasks start Pending.')
        if before:
            for f in ('farm','external_id','source_system','source_hash','source_file','mapping','file','posting_date'):
                if self.get(f)!=before.get(f):frappe.throw('Task source is immutable; create a new source version.')
            for f in ('status','retry_count','sync_error','last_sync_at','source_import_batch'):
                if self.get(f)!=before.get(f) and not command_allowed(self,'run_integration'):
                    frappe.throw('Use the integration retry command.')
    def on_trash(self):frappe.throw('Integration history cannot be deleted.')


class WarehouseMap(Document):
    def validate(self):
        check_farm(self)
        validate_warehouse(self.warehouse,frappe.db.get_value('Farm',self.farm,'company'))


class ReferenceMaster(Document):
    def validate(self):
        before=self.get_doc_before_save()
        if before:
            for f in self.meta.fields:
                if f.fieldname.endswith('_code') and self.get(f.fieldname)!=before.get(f.fieldname):
                    frappe.throw('Reference codes are immutable.')


class PackSpec(Document):
    def validate(self):
        validate_version(self,'spec_code',('Lotus Packing Supervisor',))
        from lotus_farm.controls import validate_item,positive
        validate_item(self.item);positive(self.kg_per_carton,'Kg per carton')
        if getdate(self.valid_to)<getdate(self.valid_from):frappe.throw('Pack specification dates are invalid.')
    def on_trash(self):
        if self.approval_state=='Approved':frappe.throw('Approved specifications cannot be deleted.')


def amendment_guard(doc,method=None):
    if doc.get('amended_from') and doc.is_new() and not doc.get('amendment_reason'):
        frappe.throw('Explain the correction in Amendment Reason before creating the replacement.')


def pack_spec_guard(doc,method=None):
    strict=frappe.db.get_single_value('Lotus Farm Settings','require_pack_classification')
    for row in doc.outputs:
        if strict and row.output_type=='Finished' and not (row.grade and row.market and row.pack_specification):
            frappe.throw('Finished output requires Grade, Market and an approved Pack Specification after cutover.')
        if strict and row.output_type=='Secondary' and not row.secondary_type:
            frappe.throw('Classify the secondary product output after cutover.')
        for f,t in (('grade','Product Grade'),('market','Market'),('secondary_type','Secondary Product Type')):
            if row.get(f) and not frappe.db.get_value(t,row.get(f),'enabled'):frappe.throw('Selected output classification is inactive.')
        if row.pack_specification:
            spec=frappe.get_doc('Pack Specification',row.pack_specification);spec.check_permission('read')
            if spec.approval_state!='Approved' or spec.item!=row.item or not getdate(spec.valid_from)<=getdate(doc.packing_date)<=getdate(spec.valid_to):
                frappe.throw('Pack specification must be approved, effective and match the output Item.')
            if abs(float(row.cartons or 0)*float(spec.kg_per_carton)-float(row.net_kg or 0))>0.0005:
                frappe.throw('Carton count and specification weight must match output kg.')
        if row.output_type=='Finished' and row.secondary_type:frappe.throw('Finished output cannot have a secondary product type.')


class OneDriveFeed(Document):
    def validate(self):
        require_role('System Manager')
        check_farm(self)
        import re
        for key in ('tenant_id','client_id','drive_id','folder_id'):
            if not re.fullmatch(r'[A-Za-z0-9!_.-]+',self.get(key) or ''):frappe.throw('Use a Graph ID, not a URL, for '+key)
        if self.integration_user=='Administrator' or 'Lotus Integration User' not in frappe.get_roles(self.integration_user):
            frappe.throw('Choose a dedicated enabled integration user with Farm permissions.')
        from lotus_farm.controls import farm_allowed
        if not frappe.db.get_value('User',self.integration_user,'enabled') or not farm_allowed(self.farm,self.integration_user):
            frappe.throw('Feed integration user must be enabled and granted this Farm.')
        mapping=frappe.get_doc('Source Import Mapping',self.mapping);mapping.check_permission('read')
        if mapping.approval_state!='Approved':frappe.throw('Approve the source mapping before enabling the feed.')
        before=self.get_doc_before_save()
        if before and not command_allowed(self,'poll_onedrive'):
            if any(self.get(k)!=before.get(k) for k in ('delta_link','last_sync_at','last_error')):frappe.throw('Feed checkpoints are maintained by the polling command.')
            if any(self.get(k)!=before.get(k) for k in ('drive_id','folder_id','farm','mapping','filename_pattern')):
                self.delta_link=None


class InventoryItem(Document):
    def validate(self):
        check_farm(self)
        from lotus_farm.rules import quantity
        quantity(self.size_bytes or 0,'File size')
        if not command_allowed(self,'source_inventory') and (self.is_new() or any(self.get(k)!=self.get_doc_before_save().get(k) for k in ('external_item_id','inventory_key','source_path','source_filename','extension','size_bytes','source_modified_at','source_created_at','deleted','source_file'))):
            frappe.throw('Inventory metadata is recorded by the approved source feed.')


def bunch_tag_guard(doc,method=None):
    from lotus_farm.onedrive_workspace import tag_lineage
    tag_lineage(doc, method)
    if doc.bunch_tag:
        tag=frappe.get_doc('Bunch Tag',doc.bunch_tag);tag.check_permission('read')
        if tag.get('process_adoption'):
            return
        if not tag.enabled or (tag.valid_from and getdate(doc.operation_date)<getdate(tag.valid_from)) or (tag.valid_to and getdate(doc.operation_date)>getdate(tag.valid_to)):
            frappe.throw('Bunch tag is inactive or outside its effective period.')


def defect_master_guard(doc,method=None):
    before=doc.get_doc_before_save()
    if before:
        for key in ('defect_code','category','defect_group'):
            if doc.get(key)!=before.get(key):
                # A reason taxonomy remains stable after it occurs in actual evidence.
                references=frappe.get_all('DocField',filters={'options':'Defect Reason','fieldtype':'Link'},fields=['parent','fieldname'])
                if any(frappe.db.exists(r.parent,{r.fieldname:doc.name}) for r in references):
                    frappe.throw('Used defect identity and grouping are immutable; create a new reason.')
