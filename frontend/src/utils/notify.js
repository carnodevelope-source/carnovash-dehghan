import { getActivePinia } from 'pinia'
import { useNotificationsStore } from '../store/notifications.store'

const withStore = (callback) => {
  if (!getActivePinia()) return null
  return callback(useNotificationsStore())
}

export const pushNotification = (message, type = 'info', options = {}) => withStore((store) => store.push(message, type, options))

export const notifySuccess = (message, options = {}) => pushNotification(message, 'success', options)
export const notifyError = (message, options = {}) => pushNotification(message, 'error', options)
export const notifyWarning = (message, options = {}) => pushNotification(message, 'warning', options)
export const notifyInfo = (message, options = {}) => pushNotification(message, 'info', options)
