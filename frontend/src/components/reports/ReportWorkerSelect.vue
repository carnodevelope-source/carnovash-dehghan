<template>
  <div ref="root" class="worker-select" @keydown.esc.stop="close(true)">
    <button ref="trigger" type="button" class="worker-trigger" :aria-expanded="open" aria-label="انتخاب نیرو" @click="open = !open">
      <span>{{ selectedWorker?.full_name || 'همه نیروها' }}</span>
      <svg class="chevron" :class="{ rotated: open }" width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="m6 9 6 6 6-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>
    <div v-if="open" class="worker-menu">
      <div class="status-tabs" role="group" aria-label="وضعیت نیروها">
        <button v-for="item in statuses" :key="item.value" type="button" :aria-pressed="status === item.value" :class="{ active: status === item.value }" @click="status = item.value">
          {{ item.label }}
        </button>
      </div>
      <div class="worker-options" role="group" aria-label="انتخاب نیرو">
        <button type="button" class="worker-option" :class="{ selected: !modelValue }" @click="select('')">
          <span>همه نیروها</span><span v-if="!modelValue" aria-hidden="true">✓</span>
        </button>
        <button v-for="worker in visibleWorkers" :key="worker.id" type="button" class="worker-option" :class="{ selected: String(worker.id) === String(modelValue) }" @click="select(String(worker.id))">
          <span>{{ worker.full_name }}</span>
          <span v-if="String(worker.id) === String(modelValue)" aria-hidden="true">✓</span>
        </button>
        <p v-if="!visibleWorkers.length" class="empty-state">نیرویی در این گروه وجود ندارد.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  workers: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:modelValue'])
const root = ref(null)
const trigger = ref(null)
const open = ref(false)
const status = ref('all')
const statuses = [
  { value: 'active', label: 'فعال' },
  { value: 'inactive', label: 'غیرفعال' },
  { value: 'all', label: 'همه' }
]
const selectedWorker = computed(() => props.workers.find((worker) => String(worker.id) === String(props.modelValue)))
const visibleWorkers = computed(() => props.workers.filter((worker) => (
  status.value === 'all' || (status.value === 'active' ? worker.is_available : !worker.is_available)
)))
const close = (restoreFocus = false) => {
  open.value = false
  if (restoreFocus) trigger.value?.focus()
}
const select = (value) => {
  emit('update:modelValue', value)
  close(true)
}
watch(visibleWorkers, (workers) => {
  if (props.modelValue && !workers.some((worker) => String(worker.id) === String(props.modelValue))) {
    emit('update:modelValue', '')
  }
})
const onOutside = (event) => {
  if (!root.value?.contains(event.target)) close()
}
const onFocusOutside = (event) => {
  if (!root.value?.contains(event.target)) close()
}
onMounted(() => {
  document.addEventListener('pointerdown', onOutside)
  document.addEventListener('focusin', onFocusOutside)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onOutside)
  document.removeEventListener('focusin', onFocusOutside)
})
</script>

<style scoped>
.worker-select{position:relative;min-width:0;font-size:inherit}
button{font:inherit;cursor:pointer}
.worker-trigger{display:flex;align-items:center;justify-content:space-between;gap:8px;width:100%;height:38px;padding:0 10px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#0f172a;text-align:right}
.worker-trigger span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chevron{flex-shrink:0;color:#64748b;transition:transform .18s ease}
.chevron.rotated{transform:rotate(180deg)}
.worker-menu{position:absolute;inset-inline:0;top:calc(100% + 6px);z-index:40;min-width:200px;padding:8px;border:1px solid #dbe4f0;border-radius:14px;background:#fff;box-shadow:0 12px 32px #0f172a24}
.status-tabs{display:flex;gap:4px;padding:4px;margin-bottom:6px;border-radius:9px;background:#f1f5f9}
.status-tabs button{flex:1;padding:7px 4px;border:0;border-radius:7px;background:transparent;color:#64748b}
.status-tabs button.active{background:#fff;color:#2563eb;box-shadow:0 1px 4px #0f172a14;font-weight:700}
.worker-options{max-height:260px;overflow-y:auto;overscroll-behavior:contain}
.worker-option{display:flex;align-items:center;justify-content:space-between;gap:8px;width:100%;padding:10px;border:0;border-radius:8px;background:#fff;color:#334155;text-align:right}
.worker-option:hover{background:#f1f5f9}
.worker-option.selected{color:#2563eb;background:#eff6ff;font-weight:700}
button:focus-visible{outline:2px solid #2563eb;outline-offset:2px}
.empty-state{padding:12px 6px;color:#64748b;text-align:center}
@media(max-width:768px){.worker-trigger{height:34px}}
</style>
