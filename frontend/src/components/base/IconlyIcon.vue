<template>
  <span class="iconly-shell" :class="[`size-${size}`, { decorative }]" :aria-hidden="decorative ? 'true' : undefined">
    <img v-if="src" :src="src" :alt="decorative ? '' : alt" class="iconly-img" />
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { iconSrc } from '../../config/iconly'

const props = defineProps({
  name: { type: String, required: true },
  alt: { type: String, default: '' },
  size: { type: String, default: 'md' },
  decorative: { type: Boolean, default: true }
})

const src = computed(() => iconSrc(props.name))
</script>

<style scoped>
.iconly-shell {
  --iconly-filter: brightness(0) saturate(100%) invert(33%) sepia(18%) saturate(1139%) hue-rotate(179deg) brightness(95%) contrast(92%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}

.iconly-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: var(--iconly-filter);
}

.size-xs { width: 14px; height: 14px; }
.size-sm { width: 16px; height: 16px; }
.size-md { width: 18px; height: 18px; }
.size-lg { width: 20px; height: 20px; }
.size-xl { width: 24px; height: 24px; }
</style>
