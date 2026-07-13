export const ATTENDANCE_ROUTE = '/manager/attendance'

const ATTENDANCE_ALLOWED_ROLES = ['manager', 'admin']
const ATTENDANCE_UPGRADE_MESSAGE = 'ورود و خروج تا ۵ نیرو رایگان است. برای نیروهای بیشتر باید آپشن ورود و خروج را از کیف پول خریداری کنید.'

export const hasFeatureAccess = (user, featureKey) => {
  const normalizedFeatureKey = String(featureKey || '').trim()
  if (!normalizedFeatureKey) return false
  if (user?.menu_access?.[normalizedFeatureKey] === true) return true
  return Array.isArray(user?.purchased_menu_access) && user.purchased_menu_access.includes(normalizedFeatureKey)
}

export const hasAttendanceAccess = (user) => {
  const role = String(user?.role || '').trim().toLowerCase()
  return ATTENDANCE_ALLOWED_ROLES.includes(role)
}

export const requiresAttendanceUpgrade = (user) => {
  if (!user) return false
  if (user?.attendance_feature_purchased === true) return false
  if (user?.attendance_upgrade_required === true) return true
  const workerCount = Number(user?.attendance_worker_count || 0)
  const freeLimit = Number(user?.attendance_free_workers_limit || 5)
  return workerCount > freeLimit
}

export const getAttendanceUpgradeMessage = () => ATTENDANCE_UPGRADE_MESSAGE
