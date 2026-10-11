"""Pure permission-to-feature mapping and task visibility for the phone portal.

These flags control presentation; every server endpoint checks roles and Farm grants.
"""
ROLE_FEATURES = {
    "Lotus Farm Director": ("overview", "tasks", "management"),
    "Lotus Farm Manager": ("overview", "tasks", "management", "assign", "observation"),
    "Lotus Team Leader": ("tasks",),
    "Lotus Field Technician": ("tasks", "observation"),
    "Lotus QC Manager": ("qc",),
    "Lotus Packing Supervisor": ("packhouse",),
    "Lotus Auditor": ("overview", "management"),
    "Lotus Stock Reviewer": ("packhouse",),
    "Lotus Sales Planner": ("forecast",),
    "Lotus Integration User": ("imports",),
}
ROLE_LABELS = {
    "Lotus Farm Director": "Giám đốc nông trường",
    "Lotus Farm Manager": "Quản lý nông trường",
    "Lotus Team Leader": "Tổ trưởng",
    "Lotus Field Technician": "Kỹ thuật vườn",
    "Lotus QC Manager": "Quản lý chất lượng",
    "Lotus Packing Supervisor": "Quản lý xưởng",
    "Lotus Auditor": "Kiểm tra / đối soát",
    "Lotus Stock Reviewer": "Kiểm tra kho",
    "Lotus Sales Planner": "Kế hoạch bán hàng",
    "Lotus Integration User": "Nhập dữ liệu",
}


def mobile_features(roles, administrator=False):
    if administrator:
        return sorted({key for values in ROLE_FEATURES.values() for key in values})
    return sorted({key for role in set(roles) for key in ROLE_FEATURES.get(role, ())})


def visible_line(line, *, user, roles, team_names=(), administrator=False):
    """Do not disclose other teams' task lines, including those within one shared plan."""
    roles = set(roles)
    if administrator or roles.intersection({"Lotus Farm Director", "Lotus Farm Manager", "Lotus Auditor"}):
        return True
    if "Lotus Team Leader" in roles and (line.get("work_team") in set(team_names) or line.get("responsible") == user):
        return True
    if "Lotus Field Technician" in roles and line.get("responsible") == user:
        return True
    return False
