export const ATTENDANCE_ROUTE = '/manager/attendance'

const ATTENDANCE_ALLOWED_ROLES = ['manager', 'admin']
const ATTENDANCE_UPGRADE_MESSAGE = 'برای استفاده از ورود و خروج باید اشتراک این قابلیت را خریداری کنید.'

export const hasAttendanceAccess = (user) => {
  const role = String(user?.role || '').trim().toLowerCase()
  if (!ATTENDANCE_ALLOWED_ROLES.includes(role)) return false
  if (user?.menu_access?.attendance === true) return true
  return Array.isArray(user?.purchased_menu_access) && user.purchased_menu_access.includes('attendance')
}

export const getAttendanceUpgradeMessage = () => ATTENDANCE_UPGRADE_MESSAGE
