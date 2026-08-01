<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="permission-prompt-overlay"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      @click.self="onCancel"
    >
      <section class="permission-prompt-panel" :class="`kind-${kind}`">
        <header class="permission-prompt-head">
          <div class="permission-prompt-icon" aria-hidden="true">
            <span class="permission-glyph" :class="kind"></span>
          </div>
          <div>
            <h3 :id="titleId">{{ title }}</h3>
            <p>{{ message }}</p>
          </div>
        </header>
        <p v-if="detail" class="permission-prompt-detail">{{ detail }}</p>
        <footer class="permission-prompt-actions">
          <button type="button" class="permission-btn ghost" :disabled="busy" @click="onCancel">
            {{ cancelLabel }}
          </button>
          <button
            v-if="secondaryLabel"
            type="button"
            class="permission-btn secondary"
            :disabled="busy"
            @click="onSecondary"
          >
            {{ secondaryLabel }}
          </button>
          <button type="button" class="permission-btn primary" :disabled="busy" @click="onConfirm">
            {{ busy ? 'در حال ادامه...' : confirmLabel }}
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { usePermissionPromptStore } from '../../store/permissionPrompt.store'

const store = usePermissionPromptStore()
const {
  open,
  kind,
  title,
  message,
  detail,
  confirmLabel,
  cancelLabel,
  secondaryLabel,
  busy
} = storeToRefs(store)

const titleId = computed(() => 'permission-prompt-title')

const onConfirm = () => store.confirm()
const onCancel = () => store.cancel()
const onSecondary = () => store.secondary()
</script>

<style scoped>
.permission-prompt-overlay {
  position: fixed;
  inset: 0;
  z-index: 420;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgba(15, 23, 42, 0.48);
  backdrop-filter: blur(6px);
}
.permission-prompt-panel {
  width: min(460px, 100%);
  border-radius: 22px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #dbe7f5;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.28);
  padding: 18px;
  display: grid;
  gap: 14px;
}
.permission-prompt-head {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.permission-prompt-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: #dbe9ff;
}
.permission-glyph {
  width: 22px;
  height: 22px;
  border: 2px solid #1d4ed8;
  border-radius: 6px;
  position: relative;
  box-sizing: border-box;
}
.permission-glyph.camera::after {
  content: '';
  position: absolute;
  inset: 4px;
  border: 2px solid #1d4ed8;
  border-radius: 50%;
}
.permission-glyph:not(.camera) {
  border-radius: 50%;
}
.permission-glyph:not(.camera)::after {
  content: '';
  position: absolute;
  left: 5px;
  top: 3px;
  width: 6px;
  height: 8px;
  border: 2px solid #1d4ed8;
  border-bottom: 0;
  border-radius: 6px 6px 0 0;
}
.permission-prompt-head h3 {
  margin: 0 0 6px;
  font-size: 18px;
  color: #0f172a;
}
.permission-prompt-head p {
  margin: 0;
  color: #475569;
  line-height: 1.85;
  font-size: 13px;
}
.permission-prompt-detail {
  margin: 0;
  padding: 12px 14px;
  border-radius: 14px;
  background: #eff6ff;
  color: #1e3a8a;
  font-size: 12px;
  line-height: 1.85;
}
.permission-prompt-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.permission-btn {
  border: 0;
  border-radius: 12px;
  padding: 10px 14px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.permission-btn:disabled {
  opacity: 0.65;
  cursor: wait;
}
.permission-btn.primary {
  background: linear-gradient(135deg, #1d4ed8, #0ea5e9);
  color: #fff;
}
.permission-btn.secondary {
  background: #e2e8f0;
  color: #0f172a;
}
.permission-btn.ghost {
  background: transparent;
  color: #64748b;
  border: 1px solid #d7e3f0;
}
@media (max-width: 560px) {
  .permission-prompt-actions {
    flex-direction: column-reverse;
  }
  .permission-btn {
    width: 100%;
  }
}
</style>
