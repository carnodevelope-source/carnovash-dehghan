<template>
  <router-view />
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
import { storeToRefs } from 'pinia'
import BaseSpinner from './components/base/BaseSpinner.vue'
import { useLoadingStore } from './store/loading.store'

const loadingStore = useLoadingStore()
const { isLoading } = storeToRefs(loadingStore)
</script>
