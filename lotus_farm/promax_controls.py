"""Controls for the remaining ProMax masters and integration records."""
import json
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, add_days
from lotus_farm.controls import check_farm, command_allowed, validate_version, validate_warehouse, local_timestamp, require_role
from lotus_farm.rules import canonical_hash, RuleError
from lotus_farm.promax_rules import geometry, coordinates


class GeometryMaster(Document):
    def validate(self):
        check_farm(self)
        plot=frappe.get_doc('Farm Plot',self.farm_plot);plot.check_permission('read')
        if plot.farm!=self.farm:frappe.throw('Thửa của hình học phải thuộc vườn.')
        validate_version(self,'farm_plot',('Lotus Farm Manager',))
        try:self.geojson=json.dumps(geometry(self.geojson),separators=(',',':'))
        except (ValueError,KeyError,TypeError,RuleError) as exc:frappe.throw(str(exc))
    def on_trash(self):
        if self.approval_state=='Approved':frappe.throw('Hình học đã duyệt được giữ lại để kiểm toán.')


class DeviceMaster(Document):
    def validate(self):
        check_farm(self)
        require_role('Lotus Integration User')
        if self.unit!='Kg' or getdate(self.calibration_due)<getdate(self.calibrated_on):
            frappe.throw('Cân phải dùng Kg và có kỳ hiệu chuẩn hợp lệ.')
        user=frappe.get_doc('User',self.integration_user)
        if not user.enabled or (user.name!='Administrator' and 'Lotus Integration User' not in frappe.get_roles(user.name)):
            frappe.throw('Gắn thiết bị với một người dùng đồng bộ Lotus đang hoạt động.')
        before=self.get_doc_before_save()
        if before and any(self.get(f)!=before.get(f) for f in ('farm','device_id','integration_user')):
            frappe.throw('Định danh thiết bị và người dùng gắn kèm không được sửa; hãy đăng ký thiết bị thay thế.')


class ScheduleMaster(Document):
    def validate(self):
        check_farm(self)
        validate_version(self,'rule_name',('Lotus Farm Manager',))
        if not -365 <= int(self.offset_days or 0) <= 365 or int(self.repeat_days or 0)<0 or getdate(self.valid_to)<getdate(self.valid_from):
            frappe.throw('Độ lệch lịch và thời gian hiệu lực không hợp lệ.')
        if not -120 <= int(self.get('offset_months') or 0) <= 120 or not 0 <= int(self.get('repeat_months') or 0) <= 120:
            frappe.throw('Khoảng tháng lịch không hợp lệ.')
        if self.get('repeat_months') and self.repeat_days:
            frappe.throw('Chỉ chọn lặp theo ngày hoặc theo tháng lịch.')
        if self.norm_profile:
            profile=frappe.get_doc('Material Norm Profile',self.norm_profile);profile.check_permission('read')
            if profile.farm!=self.farm or profile.work_type!=self.work_type or profile.approval_state!='Approved':
                frappe.throw('Định mức của lịch phải được duyệt cho cùng vườn và loại công việc.')
    def on_trash(self):
        if self.approval_state=='Approved':frappe.throw('Không được xóa lịch đã duyệt.')


class CaptureRecord(Document):
    def validate(self):
        check_farm(self)
        if not self.is_new() or not command_allowed(self,'field_capture'):
            frappe.throw('Dùng lệnh ghi nhận hiện trường; bằng chứng đã nhận không được sửa.')
        if self.captured_by!=frappe.session.user:frappe.throw('Người ghi nhận phải là người đang đăng nhập.')
        self.captured_at=local_timestamp(self.captured_at)
        if self.captured_at>now_datetime():frappe.throw('Thời điểm ghi nhận không được ở tương lai.')
        if self.latitude is not None and self.longitude is not None:
            try:coordinates(self.latitude,self.longitude)
            except RuleError as exc:frappe.throw(str(exc))
        if float(self.gps_accuracy_m or 0)<0:frappe.throw('Độ chính xác GPS không được âm.')
        self.event_key=canonical_hash([self.captured_by,self.client_event_id])
        self.payload_hash=canonical_hash(json.loads(self.payload_json))
        self.server_received_at=now_datetime()
    def on_trash(self):frappe.throw('Không được xóa bằng chứng hiện trường.')


class ImportMapping(Document):
    def validate(self):
        require_role('Lotus Integration User')
        validate_version(self,'mapping_name',('Lotus Integration User',))
        from lotus_farm.importing import IMPORT_FIELDS
        if self.target_doctype not in IMPORT_FIELDS:frappe.throw('Đích nhập nằm ngoài danh sách nhập được kiểm soát.')
        if int(self.header_row or 0)<1 or int(self.first_data_row or 0)<=int(self.header_row):frappe.throw('Chỉ rõ dòng tiêu đề và dòng dữ liệu đầu tiên.')
        if self.decimal_mark not in ('.',',') or self.grouping_mark==self.decimal_mark:frappe.throw('Dấu thập phân và dấu phân cách hàng nghìn phải khác nhau.')
        if self.approval_state=='Approved' and not json.loads(self.business_key_columns or '[]'):
            frappe.throw('Duyệt các cột khóa nghiệp vụ ổn định trước khi dùng ánh xạ này.')
        seen=set()
        for row in self.fields:
            if row.target_field not in IMPORT_FIELDS[self.target_doctype] or row.target_field in seen:
                frappe.throw('Chỉ ánh xạ được các trường đích đã duyệt và không trùng.')
            seen.add(row.target_field)
            if row.value_map_json:
                if not isinstance(json.loads(row.value_map_json),dict):frappe.throw('Bảng ánh xạ giá trị phải là một đối tượng JSON.')
    def on_trash(self):
        if self.approval_state=='Approved':frappe.throw('Ánh xạ đã duyệt không được sửa.')


class IntegrationTask(Document):
    def validate(self):
        check_farm(self)
        require_role('Lotus Integration User')
        self.event_key=canonical_hash([self.source_system,self.external_id,self.source_hash])
        registry=frappe.get_doc('Source File Registry',self.source_file);registry.check_permission('read')
        if registry.sha256!=self.source_hash:frappe.throw('Mã băm công việc phải khớp nguồn đã đăng ký.')
        before=self.get_doc_before_save()
        if self.is_new() and self.status!='Pending':frappe.throw('Công việc mới bắt đầu ở trạng thái Chờ.')
        if before:
            for f in ('farm','external_id','source_system','source_hash','source_file','mapping','file','posting_date'):
                if self.get(f)!=before.get(f):frappe.throw('Nguồn công việc không được sửa; hãy tạo phiên bản nguồn mới.')
            for f in ('status','retry_count','sync_error','last_sync_at','source_import_batch'):
                if self.get(f)!=before.get(f) and not command_allowed(self,'run_integration'):
                    frappe.throw('Dùng lệnh thử lại đồng bộ.')
    def on_trash(self):frappe.throw('Không được xóa lịch sử đồng bộ.')


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
                    frappe.throw('Mã tham chiếu không được sửa.')


class PackSpec(Document):
    def validate(self):
        validate_version(self,'spec_code',('Lotus Packing Supervisor',))
        from lotus_farm.controls import validate_item,positive
        validate_item(self.item);positive(self.kg_per_carton,'Kg per carton')
        if getdate(self.valid_to)<getdate(self.valid_from):frappe.throw('Ngày của quy cách đóng gói không hợp lệ.')
    def on_trash(self):
        if self.approval_state=='Approved':frappe.throw('Không được xóa quy cách đã duyệt.')


def amendment_guard(doc,method=None):
    if doc.get('amended_from') and doc.is_new() and not doc.get('amendment_reason'):
        frappe.throw('Nhập lý do sửa đổi để giải thích điều chỉnh trước khi tạo bản thay thế.')


def pack_spec_guard(doc,method=None):
    strict=frappe.db.get_single_value('Lotus Farm Settings','require_pack_classification')
    for row in doc.outputs:
        if strict and row.output_type=='Finished' and not (row.grade and row.market and row.pack_specification):
            frappe.throw('Thành phẩm cần hạng, thị trường và quy cách đóng gói đã duyệt sau ngày chuyển đổi.')
        if strict and row.output_type=='Secondary' and not row.secondary_type:
            frappe.throw('Phân loại phụ phẩm đầu ra sau ngày chuyển đổi.')
        for f,t in (('grade','Product Grade'),('market','Market'),('secondary_type','Secondary Product Type')):
            if row.get(f) and not frappe.db.get_value(t,row.get(f),'enabled'):frappe.throw('Phân loại đầu ra đã chọn đang ngừng dùng.')
        if row.pack_specification:
            spec=frappe.get_doc('Pack Specification',row.pack_specification);spec.check_permission('read')
            if spec.approval_state!='Approved' or spec.item!=row.item or not getdate(spec.valid_from)<=getdate(doc.packing_date)<=getdate(spec.valid_to):
                frappe.throw('Quy cách đóng gói phải đã duyệt, còn hiệu lực và khớp vật tư đầu ra.')
            if abs(float(row.cartons or 0)*float(spec.kg_per_carton)-float(row.net_kg or 0))>0.0005:
                frappe.throw('Số thùng và khối lượng theo quy cách phải khớp số kg đầu ra.')
        if row.output_type=='Finished' and row.secondary_type:frappe.throw('Thành phẩm không được có loại phụ phẩm.')


class OneDriveFeed(Document):
    def validate(self):
        require_role('System Manager')
        check_farm(self)
        import re
        for key in ('tenant_id','client_id','drive_id','folder_id'):
            if not re.fullmatch(r'[A-Za-z0-9!_.-]+',self.get(key) or ''):frappe.throw('Dùng mã Graph, không dùng đường dẫn URL, cho '+key)
        if self.integration_user=='Administrator' or 'Lotus Integration User' not in frappe.get_roles(self.integration_user):
            frappe.throw('Chọn một người dùng đồng bộ riêng, đang hoạt động và có quyền với vườn.')
        from lotus_farm.controls import farm_allowed
        if not frappe.db.get_value('User',self.integration_user,'enabled') or not farm_allowed(self.farm,self.integration_user):
            frappe.throw('Người dùng đồng bộ của nguồn dữ liệu phải đang hoạt động và được cấp quyền vườn này.')
        mapping=frappe.get_doc('Source Import Mapping',self.mapping);mapping.check_permission('read')
        if mapping.approval_state!='Approved':frappe.throw('Duyệt ánh xạ nguồn trước khi bật nguồn dữ liệu.')
        before=self.get_doc_before_save()
        if before and not command_allowed(self,'poll_onedrive'):
            if any(self.get(k)!=before.get(k) for k in ('delta_link','last_sync_at','last_error')):frappe.throw('Điểm đánh dấu của nguồn dữ liệu do lệnh lấy dữ liệu tự cập nhật.')
            if any(self.get(k)!=before.get(k) for k in ('drive_id','folder_id','farm','mapping','filename_pattern')):
                self.delta_link=None


class InventoryItem(Document):
    def validate(self):
        check_farm(self)
        from lotus_farm.rules import quantity
        quantity(self.size_bytes or 0,'Dung lượng tệp')
        if not command_allowed(self,'source_inventory') and (self.is_new() or any(self.get(k)!=self.get_doc_before_save().get(k) for k in ('external_item_id','inventory_key','source_path','source_filename','extension','size_bytes','source_modified_at','source_created_at','deleted','source_file'))):
            frappe.throw('Thông tin tồn kho do nguồn dữ liệu đã duyệt ghi, không nhập tay.')


def bunch_tag_guard(doc,method=None):
    from lotus_farm.onedrive_workspace import tag_lineage
    tag_lineage(doc, method)
    if doc.bunch_tag:
        tag=frappe.get_doc('Bunch Tag',doc.bunch_tag);tag.check_permission('read')
        if tag.get('process_adoption'):
            return
        effective_day = getdate(add_days(doc.operation_date,14)) if tag.get('source_kind') == 'Lotus Weekly' and doc.operation_type == 'Bud Injection' else getdate(doc.operation_date)
        if not tag.enabled or (tag.valid_from and effective_day<getdate(tag.valid_from)) or (tag.valid_to and effective_day>getdate(tag.valid_to)):
            frappe.throw('Thẻ buồng đang ngừng dùng hoặc ngoài thời gian hiệu lực.')


def defect_master_guard(doc,method=None):
    before=doc.get_doc_before_save()
    if before:
        for key in ('defect_code','category','defect_group'):
            if doc.get(key)!=before.get(key):
                # A reason taxonomy remains stable after it occurs in actual evidence.
                references=frappe.get_all('DocField',filters={'options':'Defect Reason','fieldtype':'Link'},fields=['parent','fieldname'])
                if any(frappe.db.exists(r.parent,{r.fieldname:doc.name}) for r in references):
                    frappe.throw('Định danh và nhóm lỗi đã dùng không được sửa; hãy tạo lý do mới.')
