<template>
  <div
    class="plate-badge plate-box"
    :class="[`plate-${plateType}`, { compact, empty: !hasPlate }]"
    dir="ltr"
  >
    <template v-if="plateType === 'motorcycle'">
      <div class="plate-blue motor-blue">
        <span>I.R.</span>
        <span>IRAN</span>
      </div>
      <div class="motor-main">
        <div class="motor-row top">
          <span class="plate-cell mid">{{ resolved.mid || '---' }}</span>
        </div>
        <div class="motor-bottom">
          <span class="plate-cell bottom">{{ motorcycleBottomDigits }}</span>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="plate-white-wrap">
        <span class="plate-part plate-two">{{ resolved.right || '--' }}</span>
        <span class="plate-part plate-letter">{{ resolved.letter || '-' }}</span>
        <span class="plate-part plate-three">{{ resolved.mid || '---' }}</span>
      </div>
      <span class="plate-blue">{{ resolved.left || '--' }}</span>
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
  compact: { type: Boolean, default: false }
})

const resolved = computed(() => resolvePlateParts({
  raw: props.plateNumber,
  plate_left: props.plateLeft,
  plate_letter: props.plateLetter,
  plate_mid: props.plateMid,
  plate_right: props.plateRight,
  plate_type: props.plateType
}))

const motorcycleBottomDigits = computed(() => {
  if (props.plateType !== 'motorcycle') return ''
  return resolved.value.letter || '-----'
})

const hasPlate = computed(() => Object.values(resolved.value).some(Boolean))
</script>

<style scoped>
.plate-badge {
  display: flex;
  align-items: stretch;
  justify-content: center;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  border-radius: 14px;
  padding: 8px;
  direction: ltr;
  overflow: hidden;
  position: relative;
}

.plate-white-wrap,
.motor-main {
  min-width: 0;
  display: flex;
}

.plate-white-wrap {
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: #6f59ef18;
  color: #111827;
  border-radius: 7px 0 0 7px;
  padding: 4px 12px;
}

.motor-main {
  flex: 1;
  background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(241,245,249,0.95));
  color: #111827;
  display: flex;
  overflow: hidden;
  border-radius: 10px 0 0 10px;
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-right: 0;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.72);
}

.plate-part {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.plate-two,
.plate-three {
  font-size: 24px;
  font-weight: 700;
  height: 40px;
  padding-top: 12px;
  padding-bottom: 8px;
}

.plate-letter {
  font-size: 24px;
  font-weight: 700;
  min-width: 20px;
  padding-top: 2px;
}

.plate-blue {
  min-width: 52px;
  background: #2563eb;
  color: #ffffff;
  border-radius: 0 7px 7px 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 24px;
  line-height: 1;
  padding-top: 12px;
  padding-bottom: 8px;
}

.motor-blue {
  min-width: 38px;
  flex-direction: column;
  gap: 4px;
  font-size: 9px;
  letter-spacing: 0.05em;
  padding-top: 8px;
  padding-bottom: 6px;
}

.plate-cell {
  color: #0f172a;
  font-weight: 900;
  line-height: 1;
  text-shadow: 0 1px 0 rgba(255,255,255,0.4);
}

.plate-motorcycle .motor-main {
  display: grid;
  grid-template-rows: auto auto;
  padding: 6px 10px 7px;
  gap: 4px;
  position: relative;
}

.plate-motorcycle .motor-main::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.08), transparent 34%),
    linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0));
  pointer-events: none;
}

.motor-row,
.motor-bottom {
  display: grid;
  align-items: center;
}

.motor-row.top {
  justify-content: center;
}

.motor-bottom {
  justify-content: center;
}

.plate-motorcycle .plate-cell {
  font-size: clamp(12px, 1.9vw, 17px);
  text-align: center;
  max-width: 100%;
  overflow: hidden;
}

.plate-motorcycle .plate-cell.mid {
  font-size: clamp(16px, 2.4vw, 22px);
  letter-spacing: 0.16em;
}

.plate-motorcycle .plate-cell.bottom {
  font-size: clamp(19px, 3.1vw, 28px);
  letter-spacing: 0.12em;
  white-space: nowrap;
  text-overflow: clip;
}

.compact {
  padding: 4px;
}

.compact .plate-white-wrap {
  padding: 4px 8px;
  gap: 6px;
}

.compact .plate-two,
.compact .plate-three {
  height: 24px;
  font-size: 15px;
  padding-top: 5px;
  padding-bottom: 3px;
}

.compact .plate-letter {
  min-width: 12px;
  font-size: 15px;
  padding-top: 0;
}

.compact .plate-blue {
  min-width: 32px;
  font-size: 13px;
  padding-top: 5px;
  padding-bottom: 3px;
}

.compact .motor-blue {
  min-width: 28px;
  gap: 3px;
  font-size: 7px;
  padding-top: 5px;
  padding-bottom: 4px;
}

.compact.plate-motorcycle .motor-main {
  padding: 4px 6px 5px;
  gap: 2px;
  border-radius: 8px 0 0 8px;
}

.compact.plate-motorcycle .plate-cell {
  font-size: 9px;
}

.compact.plate-motorcycle .plate-cell.mid {
  font-size: 11px;
  letter-spacing: 0.1em;
}

.compact.plate-motorcycle .plate-cell.bottom {
  font-size: 13px;
  letter-spacing: 0.08em;
}

.empty {
  opacity: 0.72;
}
</style>
