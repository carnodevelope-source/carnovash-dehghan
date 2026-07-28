<template>
  <span ref="rootRef" class="help-tip">
    <button
      type="button"
      class="help-tip-btn"
      :class="{ open }"
      :aria-expanded="open ? 'true' : 'false'"
      :aria-label="ariaLabel"
      @click.stop="toggle"
    >
      ؟
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        class="help-tip-backdrop"
        aria-hidden="true"
        @click="close"
      ></div>
      <div
        v-if="open"
        class="help-tip-panel"
        role="dialog"
        :aria-label="ariaLabel"
        :style="panelStyle"
        @click.stop
      >
        <p>{{ text }}</p>
      </div>
    </Teleport>
  </span>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  text: { type: String, required: true },
  ariaLabel: { type: String, default: 'راهنمای این بخش' }
})

const open = ref(false)
const rootRef = ref(null)
const panelPos = ref({ top: 0, left: 0, width: 280 })

const panelStyle = computed(() => ({
  top: `${panelPos.value.top}px`,
  left: `${panelPos.value.left}px`,
  width: `${panelPos.value.width}px`
}))

const placePanel = () => {
  const el = rootRef.value
  if (!el || typeof window === 'undefined') return
  const rect = el.getBoundingClientRect()
  const width = Math.min(300, Math.max(220, window.innerWidth - 24))
  let left = rect.left + rect.width / 2 - width / 2
  left = Math.max(12, Math.min(left, window.innerWidth - width - 12))
  let top = rect.bottom + 10
  const estimatedHeight = 110
  if (top + estimatedHeight > window.innerHeight - 12) {
    top = Math.max(12, rect.top - estimatedHeight - 10)
  }
  panelPos.value = { top, left, width }
}

const close = () => {
  open.value = false
}

const toggle = async () => {
  if (!String(props.text || '').trim()) return
  open.value = !open.value
  if (open.value) {
    await nextTick()
    placePanel()
  }
}

const onKeydown = (event) => {
  if (event.key === 'Escape') close()
}

const onResize = () => {
  if (open.value) placePanel()
}

watch(open, (isOpen) => {
  if (typeof window === 'undefined') return
  if (isOpen) {
    window.addEventListener('keydown', onKeydown)
    window.addEventListener('resize', onResize)
    window.addEventListener('scroll', onResize, true)
  } else {
    window.removeEventListener('keydown', onKeydown)
    window.removeEventListener('resize', onResize)
    window.removeEventListener('scroll', onResize, true)
  }
})

onBeforeUnmount(() => {
  if (typeof window === 'undefined') return
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', onResize)
  window.removeEventListener('scroll', onResize, true)
})
</script>

<style scoped>
.help-tip {
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
  position: relative;
  flex: 0 0 auto;
}

.help-tip-btn {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  border: 1px solid #bfdbfe;
  background: linear-gradient(180deg, #ffffff, #eff6ff);
  color: #1d4ed8;
  font: inherit;
  font-size: 12px;
  font-weight: 900;
  line-height: 1;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.12);
  transition: transform .16s ease, background .16s ease, border-color .16s ease, color .16s ease;
}

.help-tip-btn:hover,
.help-tip-btn.open {
  border-color: #60a5fa;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  color: #ffffff;
  transform: translateY(-1px);
}
</style>

<style>
.help-tip-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  background: transparent;
}

.help-tip-panel {
  position: fixed;
  z-index: 1201;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid #dbeafe;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(239, 246, 255, 0.96));
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.16);
  color: #334155;
  direction: rtl;
  text-align: right;
}

.help-tip-panel p {
  margin: 0;
  font-size: 13px;
  line-height: 1.9;
  font-weight: 700;
}
</style>
