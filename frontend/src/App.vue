<template>
  <router-view />
  <GlobalNoticeStack />
  <PermissionPromptModal />
  <BaseSpinner
    v-if="showLoadingOverlay"
    overlay
    size="86px"
    color="#1d4ed8"
    ball-color="#60a5fa"
    label="در حال بارگذاری..."
  />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import BaseSpinner from './components/base/BaseSpinner.vue'
import GlobalNoticeStack from './components/base/GlobalNoticeStack.vue'
import PermissionPromptModal from './components/base/PermissionPromptModal.vue'
import { useLoadingStore } from './store/loading.store'
import { notifyError } from './utils/notify'

// Requests that finish quickly should not blink a full-screen overlay over the
// panel; only a wait the user would actually notice is worth covering the UI.
const OVERLAY_DELAY_MS = 300

const loadingStore = useLoadingStore()
const { isLoading } = storeToRefs(loadingStore)
const showLoadingOverlay = ref(false)
let overlayTimer = null

watch(isLoading, (loading) => {
  if (overlayTimer) {
    window.clearTimeout(overlayTimer)
    overlayTimer = null
  }
  if (!loading) {
    showLoadingOverlay.value = false
    return
  }
  overlayTimer = window.setTimeout(() => {
    overlayTimer = null
    showLoadingOverlay.value = true
  }, OVERLAY_DELAY_MS)
}, { immediate: true })

// Hard safety net: if pending counters drift (aborted nav, HMR, stuck GET),
// clear them so the operator UI never stays non-interactive forever.
let stuckLoadingTimer = null
watch(isLoading, (loading) => {
  if (stuckLoadingTimer) {
    window.clearTimeout(stuckLoadingTimer)
    stuckLoadingTimer = null
  }
  if (!loading) return
  stuckLoadingTimer = window.setTimeout(() => {
    stuckLoadingTimer = null
    if (loadingStore.isLoading) loadingStore.reset()
  }, 25000)
})

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
  if (overlayTimer) window.clearTimeout(overlayTimer)
  if (stuckLoadingTimer) window.clearTimeout(stuckLoadingTimer)
})
</script>
