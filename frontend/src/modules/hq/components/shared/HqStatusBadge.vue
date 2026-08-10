<script setup>
import { computed } from 'vue'
import {
  getStatusMeta,
  getPaymentStatusMeta,
  getHealthMeta,
  getWalletHealthMeta,
  getShareOwnerMeta,
  getDirectionMeta
} from '../../constants/hq-status-meta'

const props = defineProps({
  kind: { type: String, default: 'status' },
  value: { type: String, default: '' },
  label: { type: String, default: '' }
})

const meta = computed(() => {
  if (props.kind === 'payment') return getPaymentStatusMeta(props.value)
  if (props.kind === 'health') return getHealthMeta(props.value)
  if (props.kind === 'wallet') return getWalletHealthMeta(props.value)
  if (props.kind === 'share') return getShareOwnerMeta(props.value)
  if (props.kind === 'direction') return getDirectionMeta(props.value)
  return getStatusMeta(props.value)
})

const text = computed(() => props.label || meta.value.label)
</script>

<template>
  <span class="hq-badge" :class="[`tone-${meta.tone}`, `kind-${kind}`]">
    <i class="hq-badge-dot" aria-hidden="true" />
    <span>{{ text }}</span>
  </span>
</template>

<style scoped>
.hq-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.38rem;
  height: 26px;
  padding: 0 0.62rem;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
  background: #eef2f7;
  color: #475569;
  border: 1px solid transparent;
}
.hq-badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.85;
}
.tone-success { background: #eaf8ed; color: #166534; border-color: rgba(22, 101, 52, 0.1); }
.tone-warning { background: #fff6e8; color: #9a3412; border-color: rgba(154, 52, 18, 0.1); }
.tone-danger { background: #feeeee; color: #991b1b; border-color: rgba(153, 27, 27, 0.1); }
.tone-info { background: #e8f5fe; color: #075985; border-color: rgba(7, 89, 133, 0.1); }
.tone-neutral { background: #f1f5f9; color: #475569; border-color: rgba(71, 85, 105, 0.08); }
.tone-carno { background: #e8f2fc; color: #0f62b3; border-color: rgba(15, 98, 179, 0.12); }
.tone-arakar { background: #f4ecff; color: #6d28d9; border-color: rgba(109, 40, 217, 0.12); }
</style>
