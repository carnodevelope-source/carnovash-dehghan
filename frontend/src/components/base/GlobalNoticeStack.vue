<template>
  <div class="notice-stack" aria-live="polite" aria-atomic="true">
    <transition-group name="notice">
      <article
        v-for="item in items"
        :key="item.id"
        class="notice-card"
        :class="`notice-${item.type}`"
      >
        <div class="notice-accent"></div>
        <div class="notice-body">
          <strong v-if="item.title">{{ item.title }}</strong>
          <p>{{ item.message }}</p>
        </div>
        <button type="button" class="notice-close" @click="dismiss(item.id)">×</button>
      </article>
    </transition-group>
  </div>
</template>

<script setup>
import { onBeforeUnmount, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useNotificationsStore } from '../../store/notifications.store'

const notificationsStore = useNotificationsStore()
const { items } = storeToRefs(notificationsStore)
const timers = new Map()

const clearTimer = (id) => {
  const handle = timers.get(id)
  if (handle) {
    clearTimeout(handle)
    timers.delete(id)
  }
}

const dismiss = (id) => {
  clearTimer(id)
  notificationsStore.remove(id)
}

watch(items, (list) => {
  const activeIds = new Set(list.map((item) => item.id))

  for (const item of list) {
    if (timers.has(item.id)) continue
    const timeout = window.setTimeout(() => {
      dismiss(item.id)
    }, item.duration)
    timers.set(item.id, timeout)
  }

  for (const id of [...timers.keys()]) {
    if (!activeIds.has(id)) clearTimer(id)
  }
}, { deep: true, immediate: true })

onBeforeUnmount(() => {
  for (const id of [...timers.keys()]) clearTimer(id)
})
</script>

<style scoped>
.notice-stack{
  position:fixed;
  left:20px;
  bottom:20px;
  display:grid;
  gap:12px;
  z-index:300;
  width:min(380px,calc(100vw - 24px));
  pointer-events:none
}
.notice-card{
  display:grid;
  grid-template-columns:4px minmax(0,1fr) 40px;
  align-items:start;
  border-radius:20px;
  overflow:hidden;
  background:rgba(255,255,255,.96);
  border:1px solid rgba(226,232,240,.94);
  box-shadow:0 16px 36px rgba(15,23,42,.14);
  backdrop-filter:blur(18px);
  pointer-events:auto
}
.notice-accent{background:var(--notice-accent,#0f172a);min-height:100%}
.notice-body{padding:14px 12px 14px 14px;display:grid;gap:6px}
.notice-body strong{font-size:13px;color:#0f172a}
.notice-body p{margin:0;font-size:13px;line-height:1.9;color:#334155}
.notice-close{
  width:40px;
  height:40px;
  border:0;
  background:transparent;
  color:#64748b;
  font-size:24px;
  line-height:1;
  cursor:pointer
}
.notice-close:hover{color:#0f172a}
.notice-success{--notice-accent:#16a34a}
.notice-error{--notice-accent:#dc2626}
.notice-warning{--notice-accent:#ea580c}
.notice-info{--notice-accent:#2563eb}
.notice-enter-active,.notice-leave-active{transition:all .24s ease}
.notice-enter-from,.notice-leave-to{opacity:0;transform:translateY(10px) scale(.98)}
@media (max-width:640px){
  .notice-stack{left:12px;right:12px;bottom:12px;width:auto}
}
</style>
