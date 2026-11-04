// Các bộ lọc nhân sự chấm công: chức vụ, phòng ban cha và bộ phận trực thuộc.
export const UNASSIGNED = '__lotus_unassigned__'

export function organizationOf(row, departmentParents = {}) {
  const designation = String(row?.designation || '').trim()
  const assigned = String(row?.department || '').trim()
  const parent = String(departmentParents[assigned] || '').trim()
  if (assigned && parent && parent !== 'All Departments' && parent !== assigned) {
    return { designation, department: parent, division: assigned }
  }
  return { designation, department: assigned, division: '' }
}

function equalsFilter(value, selected) {
  return !selected || (selected === UNASSIGNED ? !value : value === selected)
}

export function filterAttendanceOrganization(rows, filters = {}, parents = {}) {
  return rows.filter(row => {
    const org = organizationOf(row, parents)
    return equalsFilter(org.designation, filters.designation)
      && equalsFilter(org.department, filters.department)
      && equalsFilter(org.division, filters.division)
  })
}

export function organizationOptions(rows, field, parents = {}, emptyLabel = 'Chưa phân') {
  const values = new Set(rows.map(row => organizationOf(row, parents)[field]))
  const options = [...values].filter(Boolean)
    .sort((a,b) => a.localeCompare(b, 'vi'))
    .map(value => ({value, label: value.replace(/ - LT$/, '')}))
  if (values.has('')) options.unshift({value:UNASSIGNED, label:emptyLabel})
  return options
}
