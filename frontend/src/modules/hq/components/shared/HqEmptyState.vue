<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  actionLabel: { type: String, default: '' }
})
defineEmits(['action'])
</script>

<template>
  <div class="hq-empty">
    <div class="hq-empty-mark" aria-hidden="true" />
    <strong>{{ title }}</strong>
    <p v-if="description">{{ description }}</p>
    <button v-if="actionLabel" type="button" class="hq-empty-btn" @click="$emit('action')">{{ actionLabel }}</button>
  </div>
</template>

<style scoped>
.hq-empty {
  display: grid;
  gap: 0.5rem;
  place-items: center;
  text-align: center;
  padding: 2.2rem 1.2rem;
  color: #647892;
  background:
    radial-gradient(circle at top, rgba(25, 118, 210, 0.06), transparent 48%),
    #f8fbff;
  border: 1px dashed rgba(25, 118, 210, 0.2);
  border-radius: 16px;
}
.hq-empty-mark {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background:
    linear-gradient(135deg, rgba(25, 118, 210, 0.16), rgba(25, 118, 210, 0.05));
  border: 1px solid rgba(25, 118, 210, 0.14);
  margin-bottom: 0.15rem;
}
.hq-empty strong {
  color: #0c3d78;
  font-size: 15px;
  font-weight: 750;
}
.hq-empty p {
  margin: 0;
  max-width: 34rem;
  font-size: 13px;
  line-height: 1.75;
}
.hq-empty-btn {
  margin-top: 0.4rem;
  border: 0;
  background: linear-gradient(180deg, #2b86e0 0%, #1976d2 100%);
  color: #fff;
  border-radius: 999px;
  height: 38px;
  padding: 0 1.1rem;
  cursor: pointer;
  font-weight: 700;
  box-shadow: 0 10px 20px rgba(25, 118, 210, 0.22);
}
</style>
