frappe.query_reports["Harvest Availability"] = {
    filters: [
        {
            fieldname: "farm",
            label: __("Farm"),
            fieldtype: "Link",
            options: "Farm"
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        }
    ]
};
