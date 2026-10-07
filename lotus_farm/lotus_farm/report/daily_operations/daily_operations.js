frappe.query_reports["Daily Operations"] = {
  filters: [
    {fieldname: "farm", label: "Nông trường", fieldtype: "Link", options: "Farm", reqd: 1},
    {fieldname: "posting_date", label: "Ngày", fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1}
  ]
};
