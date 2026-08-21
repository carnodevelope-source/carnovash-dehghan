<template>
  <div class="spinner-wrap" :class="{ overlay }" role="status" aria-live="polite">
    <div :style="sizeStyles" class="spinner spinner--ping-pong">
      <div :style="innerStyles" class="spinner-inner">
        <div class="board">
          <div class="left"></div>
          <div class="right"></div>
          <div class="ball"></div>
        </div>
      </div>
    </div>
    <p v-if="label" class="spinner-label">{{ label }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: { type: String, default: '72px' },
  color: { type: String, default: '#1d4ed8' },
  ballColor: { type: String, default: '#60a5fa' },
  label: { type: String, default: '' },
  overlay: { type: Boolean, default: false }
})

const sizeStyles = computed(() => ({
  width: props.size,
  height: props.size
}))

const innerStyles = computed(() => {
  const sizeNumber = parseInt(String(props.size), 10) || 72
  return {
    transform: `scale(${sizeNumber / 250})`,
    '--bg-color': props.color,
    '--ball-color': props.ballColor
  }
})
</script>

<style scoped>
.spinner-wrap {
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 10px;
}

.spinner-wrap.overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  /* No backdrop-filter: it forces a full-viewport GPU composite every time the
     overlay appears, which is painful on the tablets used on the shop floor. */
  background: rgba(238, 246, 255, 0.88);
}

.spinner {
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
}

.spinner * {
  line-height: 0;
  box-sizing: border-box;
}

.board {
  width: 250px;
  position: relative;
}

.left,
.right {
  height: 50px;
  width: 15px;
  background: var(--bg-color);
  display: inline-block;
  position: absolute;
}

.left {
  left: 0;
  animation: pingpong-position1 2s linear infinite;
}

.right {
  right: 0;
  animation: pingpong-position2 2s linear infinite;
}

.ball {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: var(--ball-color);
  position: absolute;
  animation: pingpong-bounce 2s linear infinite;
}

.spinner-label {
  margin: 0;
  font-size: 13px;
  color: #1e3a8a;
  font-weight: 700;
}

@keyframes pingpong-position1 {
  0% { top: -60px; }
  25% { top: 0; }
  50% { top: 60px; }
  75% { top: -60px; }
  100% { top: -60px; }
}

@keyframes pingpong-position2 {
  0% { top: 60px; }
  25% { top: 0; }
  50% { top: -60px; }
  75% { top: -60px; }
  100% { top: 60px; }
}

@keyframes pingpong-bounce {
  0% { top: -35px; left: 10px; }
  25% { top: 25px; left: 225px; }
  50% { top: 75px; left: 10px; }
  75% { top: -35px; left: 225px; }
  100% { top: -35px; left: 10px; }
}
@media (max-width: 640px) {
  .board {
    width: min(250px, 72vw);
  }
}
</style>
