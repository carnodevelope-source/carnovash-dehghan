import { getActivePinia } from 'pinia'
import { usePermissionPromptStore } from '../store/permissionPrompt.store'

const withStore = (callback) => {
  if (!getActivePinia()) return Promise.resolve({ confirmed: false, secondary: false })
  return callback(usePermissionPromptStore())
}

export const askPermissionPrompt = (options = {}) => withStore((store) => store.ask(options))

export const askCameraPermission = (options = {}) => askPermissionPrompt({
  kind: 'camera',
  title: 'دسترسی به دوربین',
  message: 'برای تشخیص پلاک، کارنوواش به دوربین دستگاه نیاز دارد. با تأیید، مرورگر از شما اجازه دسترسی می‌گیرد.',
  detail: 'اگر قبلاً رد کرده باشید، از تنظیمات مرورگر برای این سایت، دسترسی دوربین را فعال کنید و دوباره تلاش کنید.',
  confirmLabel: 'تأیید و باز کردن دوربین',
  cancelLabel: 'الان نه',
  secondaryLabel: 'استفاده از عکس / دوربین گوشی',
  ...options
})

export const askCameraDeniedHelp = (options = {}) => askPermissionPrompt({
  kind: 'camera',
  title: 'دسترسی دوربین داده نشد',
  message: 'مرورگر اجازه دوربین را نداد. می‌توانید دوباره تلاش کنید یا از گزینه عکس استفاده کنید.',
  detail: 'مسیر معمول: تنظیمات مرورگر ← تنظیمات سایت ← دوربین ← اجازه',
  confirmLabel: 'تلاش دوباره',
  cancelLabel: 'بستن',
  secondaryLabel: 'انتخاب عکس',
  ...options
})
