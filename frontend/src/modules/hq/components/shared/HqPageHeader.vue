<script setup>
defineProps({
  breadcrumb: { type: String, default: 'پنل HQ' },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  freshness: { type: String, default: '' }
})
</script>

<template>
  <header class="hq-page-header">
    <div class="copy">
      <p class="crumb">{{ breadcrumb }}</p>
      <div class="title-row">
        <h2>{{ title }}</h2>
        <span v-if="freshness" class="fresh">{{ freshness }}</span>
      </div>
      <p v-if="subtitle" class="sub">{{ subtitle }}</p>
    </div>
    <div class="actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.hq-page-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  background:
    radial-gradient(circle at top right, rgba(25, 118, 210, 0.08), transparent 42%),
    linear-gradient(180deg, #ffffff 0%, #f9fbfe 100%);
  border: 1px solid rgba(25, 118, 210, 0.12);
  border-radius: 18px;
  padding: 1.15rem 1.3rem;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.9) inset, 0 12px 30px rgba(15, 37, 69, 0.04);
}
.copy { min-width: 0; }
.crumb {
  margin: 0;
  color: #6b7c93;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.01em;
}
.title-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: center;
  margin-top: 0.28rem;
}
h2 {
  margin: 0;
  color: #0c3d78;
  font-size: 1.55rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.25;
}
.fresh {
  display: inline-flex;
  align-items: center;
  height: 26px;
  padding: 0 0.7rem;
  border-radius: 999px;
  background: rgba(25, 118, 210, 0.1);
  color: #0f62b3;
  font-size: 12px;
  font-weight: 650;
  border: 1px solid rgba(25, 118, 210, 0.14);
}
.sub {
  margin: 0.42rem 0 0;
  color: #5b6b82;
  font-size: 13.5px;
  line-height: 1.65;
  max-width: 42rem;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
@media (max-width: 768px) {
  .hq-page-header {
    flex-direction: column;
    padding: 1rem 1.05rem;
  }
  h2 { font-size: 1.25rem; }
}
</style>
