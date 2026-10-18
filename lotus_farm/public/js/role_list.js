/* Lotus Role List: hide framework's default English roles in the everyday list.
   This is ONLY a visual filter. Never delete roles, rename IDs or change permissions. */
frappe.listview_settings["Role"] = {
  filters: [["name", "like", "Lotus %"]],
  onload(listview) {
    const roleFilter = () => listview.filter_area.get().find(
      (row) => row[0] === "Role" && row[1] === "name" &&
        row[2] === "like" && row[3] === "Lotus %"
    );
    // A saved list layout can override the default; restore the Lotus scope.
    if (!roleFilter()) {
      listview.filter_area.add("Role", "name", "like", "Lotus %");
    }
    // System managers can still inspect built-in roles when troubleshooting.
    if (!frappe.user.has_role("System Manager")) return;
    let visibleAll = false;
    const button = listview.page.add_inner_button("Xem role hệ thống", () => {
      visibleAll = !visibleAll;
      if (visibleAll) {
        listview.filter_area.remove("name");
        button.text("Chỉ role Lotus");
      } else {
        listview.filter_area.add("Role", "name", "like", "Lotus %");
        button.text("Xem role hệ thống");
      }
    });
  }
};
