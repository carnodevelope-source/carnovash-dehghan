<template>
  <div
    class="iran-plate"
    :class="[
      `iran-plate-${kind}`,
      { 'iran-plate-compact': compact, 'iran-plate-empty': !hasPlate }
    ]"
    dir="ltr"
    :title="label"
  >
    <template v-if="kind === 'motorcycle'">
      <div class="iran-plate-ir">
        <span>I.R.</span>
        <span>IRAN</span>
      </div>
      <div class="iran-plate-motor-body">
        <strong class="iran-plate-motor-top">{{ parts.mid || '---' }}</strong>
        <strong class="iran-plate-motor-bottom">{{ parts.letter || '-----' }}</strong>
      </div>
    </template>
    <template v-else>
      <div class="iran-plate-body">
        <strong>{{ parts.right || '--' }}</strong>
        <em>{{ parts.letter || '-' }}</em>
        <strong>{{ parts.mid || '---' }}</strong>
      </div>
      <div class="iran-plate-city">
        <small>ایران</small>
        <strong>{{ parts.left || '--' }}</strong>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { resolvePlateParts } from '../../utils/plate'

const props = defineProps({
  plateNumber: { type: String, default: '' },
  plateLeft: { type: String, default: '' },
  plateLetter: { type: String, default: '' },
  plateMid: { type: String, default: '' },
  plateRight: { type: String, default: '' },
  plateType: { type: String, default: 'car' },
  compact: { type: Boolean, default: true }
})

const kind = computed(() => (props.plateType === 'motorcycle' ? 'motorcycle' : 'car'))

const parts = computed(() => resolvePlateParts({
  raw: props.plateNumber,
  plate_left: props.plateLeft,
  plate_letter: props.plateLetter,
  plate_mid: props.plateMid,
  plate_right: props.plateRight,
  plate_type: props.plateType
}))

const hasPlate = computed(() => Object.values(parts.value).some((value) => String(value || '').trim()))

const label = computed(() => {
  if (kind.value === 'motorcycle') {
    return [parts.value.mid, parts.value.letter].filter(Boolean).join(' ') || props.plateNumber || ''
  }
  const white = [parts.value.right, parts.value.letter, parts.value.mid].filter(Boolean).join(' ')
  return [white, parts.value.left].filter(Boolean).join(' - ') || props.plateNumber || ''
})
</script>

<style scoped>
.iran-plate {
  --plate-ink: #111827;
  --plate-blue: #2563eb;
  --plate-face: #f4f5ff;
  display: inline-flex;
  align-items: stretch;
  width: max-content;
  max-width: none;
  min-width: 0;
  height: 34px;
  border: 0;
  border-radius: 6px;
  overflow: hidden;
  background: var(--plate-face);
  box-sizing: border-box;
  vertical-align: middle;
  font-family: Tahoma, "Segoe UI", Arial, sans-serif;
  flex-shrink: 0;
}

.iran-plate-body,
.iran-plate-motor-body {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 4px 12px;
  background: var(--plate-face);
  color: var(--plate-ink);
  border-radius: 6px 0 0 6px;
}

.iran-plate-body strong,
.iran-plate-body em,
.iran-plate-motor-body strong,
.iran-plate-city strong {
  margin: 0;
  font-style: normal;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
}

.iran-plate-body strong {
  font-size: 13px;
  letter-spacing: 0.04em;
}

.iran-plate-body em {
  font-size: 12px;
  min-width: 12px;
  text-align: center;
}

.iran-plate-city {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  min-width: 30px;
  padding: 2px 5px;
  background: var(--plate-blue);
  color: #fff;
  border: 0;
  border-radius: 0 6px 6px 0;
}

.iran-plate-city small {
  font-size: 5.5px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: 0.02em;
}

.iran-plate-city strong {
  font-size: 11px;
  letter-spacing: 0.03em;
  margin-top: 1px;
}

.iran-plate-motorcycle {
  height: 42px;
}

.iran-plate-ir {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-width: 24px;
  padding: 3px 4px;
  background: var(--plate-blue);
  color: #fff;
  border: 0;
  border-radius: 0 6px 6px 0;
  font-size: 6px;
  font-weight: 800;
  letter-spacing: 0.04em;
  line-height: 1.05;
  order: 2;
}

.iran-plate-motor-body {
  flex-direction: column;
  gap: 2px;
  padding: 4px 12px;
  min-width: 54px;
  border-radius: 6px 0 0 6px;
  order: 1;
}

.iran-plate-motor-top {
  font-size: 11px;
  letter-spacing: 0.12em;
}

.iran-plate-motor-bottom {
  font-size: 13px;
  letter-spacing: 0.08em;
}

.iran-plate-compact.iran-plate-car {
  height: 30px;
}

.iran-plate-compact .iran-plate-body {
  gap: 10px;
  padding: 4px 12px;
}

.iran-plate-compact .iran-plate-body strong {
  font-size: 12px;
}

.iran-plate-compact .iran-plate-body em {
  font-size: 11px;
}

.iran-plate-compact .iran-plate-city {
  min-width: 26px;
  padding: 1px 4px;
}

.iran-plate-compact .iran-plate-city small {
  font-size: 5px;
}

.iran-plate-compact .iran-plate-city strong {
  font-size: 10px;
}

.iran-plate-empty {
  opacity: 0.7;
}
</style>
