export const ATTENDANCE_ROUTE = '/manager/attendance'

const ATTENDANCE_ENABLED_TENANTS = ['کارواش آبی']
const ATTENDANCE_ALLOWED_ROLES = ['manager', 'admin']
const ATTENDANCE_UPGRADE_MESSAGE = 'برای استفاده از ورود و خروج باید اشتراک این قابلیت را خریداری کنید.'

const normalizeValue = (value) => String(value || '').trim().toLocaleLowerCase('fa-IR')

export const hasAttendanceAccess = (user) => {
  const role = String(user?.role || '').trim().toLowerCase()
  if (!ATTENDANCE_ALLOWED_ROLES.includes(role)) return false
  const tenantName = normalizeValue(user?.tenant_name)
  return ATTENDANCE_ENABLED_TENANTS.some((item) => normalizeValue(item) === tenantName)
}

export const getAttendanceUpgradeMessage = () => ATTENDANCE_UPGRADE_MESSAGE
