<template>
  <router-view />
  <GlobalNoticeStack />
  <PermissionPromptModal />
  <BaseSpinner
    v-if="isLoading"
    overlay
    size="86px"
    color="#1d4ed8"
    ball-color="#60a5fa"
    label="در حال بارگذاری..."
  />
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import BaseSpinner from './components/base/BaseSpinner.vue'
import GlobalNoticeStack from './components/base/GlobalNoticeStack.vue'
import PermissionPromptModal from './components/base/PermissionPromptModal.vue'
import { useLoadingStore } from './store/loading.store'
import { notifyError } from './utils/notify'

const loadingStore = useLoadingStore()
const { isLoading } = storeToRefs(loadingStore)

const handleUnexpectedError = () => {
  notifyError('در اجرای صفحه خطای غیرمنتظره رخ داد. لطفا صفحه را یک بار نوسازی کنید.', {
    title: 'خطای برنامه'
  })
}

const handleUnhandledRejection = (event) => {
  const reason = event?.reason
  if (reason?.response || reason?.request) return
  handleUnexpectedError()
}

onMounted(() => {
  window.addEventListener('error', handleUnexpectedError)
  window.addEventListener('unhandledrejection', handleUnhandledRejection)
})

onBeforeUnmount(() => {
  window.removeEventListener('error', handleUnexpectedError)
  window.removeEventListener('unhandledrejection', handleUnhandledRejection)
})
</script>
