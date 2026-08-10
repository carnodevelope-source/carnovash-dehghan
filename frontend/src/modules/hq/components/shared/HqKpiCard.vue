<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  hint: { type: String, default: '' },
  tooltip: { type: String, default: '' },
  tone: { type: String, default: 'default' },
  delta: { type: String, default: '' },
  deltaTone: { type: String, default: 'neutral' },
  compact: { type: Boolean, default: false }
})
</script>

<template>
  <article class="hq-kpi" :class="[`tone-${tone}`, { compact }]" :title="tooltip || undefined">
    <div class="hq-kpi-top">
      <small>{{ label }}</small>
      <slot name="icon" />
    </div>
    <strong>{{ value }}</strong>
    <div v-if="hint || delta" class="hq-kpi-meta">
      <span v-if="hint" class="hint">{{ hint }}</span>
      <span v-if="delta" class="delta" :class="deltaTone">{{ delta }}</span>
    </div>
  </article>
</template>

<style scoped>
.hq-kpi {
  position: relative;
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(25, 118, 210, 0.12);
  border-radius: 16px;
  padding: 1.05rem 1.1rem;
  display: grid;
  gap: 0.42rem;
  min-height: 112px;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.85) inset, 0 10px 24px rgba(15, 37, 69, 0.035);
  transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
}
.hq-kpi::before {
  content: '';
  position: absolute;
  inset-inline-start: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: transparent;
}
.hq-kpi:hover {
  border-color: rgba(25, 118, 210, 0.22);
  box-shadow: 0 14px 28px rgba(15, 37, 69, 0.055);
}
.hq-kpi.compact {
  min-height: 0;
  padding: 0.85rem 0.95rem;
}
.hq-kpi-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}
.hq-kpi small {
  color: #647892;
  font-size: 12.5px;
  font-weight: 600;
}
.hq-kpi strong {
  color: #0c3d78;
  font-size: 1.42rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
  letter-spacing: -0.02em;
}
.hq-kpi-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.65rem;
  align-items: center;
}
.hint {
  color: #6b7c93;
  font-size: 12px;
  line-height: 1.45;
}
.delta {
  font-size: 12px;
  font-weight: 700;
  border-radius: 999px;
  padding: 0.12rem 0.45rem;
  background: #f1f5f9;
}
.delta.up { color: #166534; background: #e8f8ea; }
.delta.down { color: #991b1b; background: #fee2e2; }
.delta.neutral { color: #64748b; }
.tone-carno {
  border-color: rgba(25, 118, 210, 0.22);
  background: linear-gradient(165deg, #f4f9ff 0%, #ffffff 58%);
}
.tone-carno::before { background: #1976d2; }
.tone-arakar {
  border-color: rgba(109, 40, 217, 0.2);
  background: linear-gradient(165deg, #faf5ff 0%, #ffffff 58%);
}
.tone-arakar::before { background: #6d28d9; }
.tone-warning {
  border-color: rgba(217, 119, 6, 0.24);
  background: linear-gradient(165deg, #fffaf2 0%, #ffffff 58%);
}
.tone-warning::before { background: #d97706; }
.tone-danger {
  border-color: rgba(220, 38, 38, 0.2);
  background: linear-gradient(165deg, #fff7f7 0%, #ffffff 58%);
}
.tone-danger::before { background: #dc2626; }
.tone-spotlight {
  border-color: rgba(25, 118, 210, 0.28);
  background: linear-gradient(165deg, #eef6ff 0%, #ffffff 62%);
}
.tone-spotlight::before { background: #1976d2; }
@media (prefers-reduced-motion: reduce) {
  .hq-kpi { transition: none; }
}
</style>
