"""One mobile portal for several Lotus jobs, backed by server-side Farm and role checks."""
import frappe
from frappe.utils import getdate, flt, nowdate

from lotus_farm.controls import farm_allowed, require_role
from lotus_farm.mobile_roles import ROLE_FEATURES, ROLE_LABELS, mobile_features, visible_line


def _identity():
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Vui lòng đăng nhập để mở Lotus.", frappe.AuthenticationError)
    admin = user == "Administrator"
    roles = set(frappe.get_roles(user)).intersection(ROLE_FEATURES)
    if not roles and not admin:
        frappe.throw("Tài khoản chưa được cấp vai trò Lotus.", frappe.PermissionError)
    return user, roles, admin


def _farm(farm):
    _identity()
    if not farm or not farm_allowed(farm):
        frappe.throw("Bạn chưa được cấp quyền vào nông trường này.", frappe.PermissionError)
    record = frappe.get_doc("Farm", farm)
    record.check_permission("read")
    return record


@frappe.whitelist(methods=["GET"])
def profile():
    user, roles, admin = _identity()
    farms = frappe.get_list(
        "Farm", fields=["name", "farm_name", "company"],
        order_by="farm_name asc", limit_page_length=1000
    )
    return dict(
        user=user, roles=[dict(name=r, label=ROLE_LABELS[r]) for r in ROLE_FEATURES if r in roles],
        features=mobile_features(roles, admin),
        farms=farms, today=nowdate()
    )


@frappe.whitelist(methods=["GET"])
def overview(farm, posting_date=None):
    user, roles, admin = _identity()
    record = _farm(farm)
    features = mobile_features(roles, admin)
    date = str(getdate(posting_date or nowdate()))
    if "tasks" not in features and "overview" not in features:
        return dict(farm=farm, date=date, tasks=[], total=0, completed=0, remaining=0)
    team_names = []
    if "Lotus Team Leader" in roles:
        # An explicit leader-to-team assignment, not a guess from job title.
        team_names = frappe.get_all(
            "Work Team", filters={"farm": farm, "active": 1, "lotus_team_leader": user},
            pluck="name", limit_page_length=1000
        )
    plans = frappe.get_all(
        "Daily Work Plan",
        filters={"farm": record.name, "posting_date": date, "docstatus": 1},
        pluck="name", order_by="name asc", limit_page_length=1000
    )
    lines = []
    for name in plans:
        # This query intentionally bypasses parent DocType read for Team Leaders:
        # first enforce Farm grant, then return ONLY each permitted child line.
        plan = frappe.get_doc("Daily Work Plan", name)
        for row in plan.lines:
            if not visible_line(row, user=user, roles=roles, team_names=team_names, administrator=admin):
                continue
            lines.append(dict(
                plan=plan.name, line=row.name, work_team=row.work_team,
                work_name=frappe.db.get_value("Work Type", row.work_type, "work_name") or row.work_type,
                plot_code=frappe.db.get_value("Farm Plot", row.farm_plot, "plot_code") or row.farm_plot,
                farm_plot=row.farm_plot, planned_qty=flt(row.planned_qty), uom=row.uom,
                state=row.execution_state or "Planned", responsible=row.responsible
            ))
    actuals = {}
    ids = [row["line"] for row in lines]
    if ids:
        for result in frappe.get_all(
            "Daily Work Result",
            filters={"work_plan_line": ["in", ids], "docstatus": 1},
            fields=["work_plan_line", "completed_qty"], limit_page_length=5000
        ):
            actuals[result.work_plan_line] = actuals.get(result.work_plan_line, 0) + flt(result.completed_qty)
    for row in lines:
        row["completed_qty"] = actuals.get(row["line"], 0)
        row["status"] = "Completed" if row["line"] in actuals else row.pop("state")
        # Only management roles should see the responsible user's account details.
        if not (admin or roles.intersection({"Lotus Farm Manager", "Lotus Farm Director", "Lotus Auditor"})):
            row.pop("responsible", None)
    completed = sum(row["status"] == "Completed" for row in lines)
    return dict(farm=farm, date=date, tasks=lines, total=len(lines),
                completed=completed, remaining=len(lines) - completed,
                team_assigned=bool(team_names) if "Lotus Team Leader" in roles else None)


@frappe.whitelist(methods=["GET"])
def observation_options(farm):
    user, roles, admin = _identity()
    if "observation" not in mobile_features(roles, admin):
        frappe.throw("Bạn không có quyền ghi nhận tình trạng vườn.", frappe.PermissionError)
    _farm(farm)
    return dict(
        plots=frappe.get_list("Farm Plot", filters={"farm": farm, "active": 1},
            fields=["name", "plot_code", "farm_block"], limit_page_length=1000, order_by="plot_code asc"),
        cycles=frappe.get_list("Crop Cycle", filters={"farm": farm, "status": ["in", ["Active", "Harvesting"]]},
            fields=["name", "farm_plot", "farm_block", "cycle_type"], limit_page_length=1000),
        cohorts=frappe.get_list("Sucker Selection Batch", filters={"farm": farm},
            fields=["name", "crop_cycle"], limit_page_length=1000),
        diseases=frappe.get_list("Disease", filters={"active": 1},
            fields=["name", "disease_name"], limit_page_length=1000)
    )


@frappe.whitelist(methods=["POST"])
def report_observation(farm, posting_date, farm_plot, crop_cycle, disease,
                       affected_plants, severity, action_taken, sucker_selection_batch=None):
    user, roles, admin = _identity()
    if "observation" not in mobile_features(roles, admin):
        frappe.throw("Bạn không có quyền ghi nhận tình trạng vườn.", frappe.PermissionError)
    _farm(farm)
    if not frappe.has_permission("Disease Observation", "create") or not frappe.has_permission("Disease Observation", "submit"):
        frappe.throw("Thiếu quyền tạo và gửi phiếu kiểm tra vườn.", frappe.PermissionError)
    plot = frappe.get_doc("Farm Plot", farm_plot)
    plot.check_permission("read")
    cycle = frappe.get_doc("Crop Cycle", crop_cycle)
    cycle.check_permission("read")
    if plot.farm != farm or cycle.farm != farm or cycle.farm_plot != plot.name or not plot.active:
        frappe.throw("Thửa và vụ chuối không thuộc nông trường đang chọn.")
    if cycle.status not in ("Active", "Harvesting"):
        frappe.throw("Vụ chuối này đã ngừng hoạt động.")
    if severity not in ("Low", "Medium", "High"):
        frappe.throw("Chọn mức độ hợp lệ.")
    try:
        count = int(str(affected_plants))
    except (ValueError, TypeError):
        frappe.throw("Số cây bị ảnh hưởng phải là số nguyên.")
    if count <= 0 or count > 1000000:
        frappe.throw("Số cây bị ảnh hưởng không hợp lệ.")
    if not isinstance(action_taken, str) or not action_taken.strip() or len(action_taken) > 1000:
        frappe.throw("Hãy mô tả tình trạng hoặc cách xử lý (tối đa 1.000 ký tự).")
    illness = frappe.get_doc("Disease", disease)
    illness.check_permission("read")
    if not illness.active:
        frappe.throw("Loại bệnh đã ngừng sử dụng.")
    if cycle.cycle_type == "Ratoon" and not sucker_selection_batch:
        frappe.throw("Vụ tái sinh phải chọn đợt chồi.")
    if sucker_selection_batch:
        cohort = frappe.get_doc("Sucker Selection Batch", sucker_selection_batch)
        cohort.check_permission("read")
        if cohort.crop_cycle != cycle.name:
            frappe.throw("Đợt chồi không thuộc vụ đang chọn.")
    doc = frappe.get_doc(dict(
        doctype="Disease Observation", farm=farm, farm_block=plot.farm_block,
        farm_plot=plot.name, crop_cycle=cycle.name, sucker_selection_batch=sucker_selection_batch,
        posting_date=str(getdate(posting_date)), disease=disease,
        affected_plants=count, severity=severity, action_taken=action_taken.strip()
    ))
    doc.insert()
    doc.submit()
    return dict(name=doc.name, docstatus=doc.docstatus)
