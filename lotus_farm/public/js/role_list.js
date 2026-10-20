/* Show every role. Labels are translated without changing role identifiers. */
frappe.listview_settings['Role'] = {
  onload(listview) {
    const legacy = listview.filter_area.get().some(row => row[0] === 'Role' && row[1] === 'name' && row[2] === 'like' && row[3] === 'Lotus %');
    if (legacy) listview.filter_area.remove('name');
  }
};
