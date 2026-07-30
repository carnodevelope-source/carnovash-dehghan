<template>
  <label class="base-phone-field" :class="{ 'has-error': showError, 'is-valid': isComplete && !errorText }">
    <span v-if="label" class="base-phone-label">{{ label }}</span>
    <input
      :id="inputId"
      :value="modelValue"
      type="tel"
      inputmode="numeric"
      autocomplete="tel"
      dir="ltr"
      maxlength="11"
      :required="required"
      :disabled="disabled"
      :placeholder="placeholder"
      :aria-invalid="showError ? 'true' : 'false'"
      :aria-describedby="showError ? `${inputId}-error` : undefined"
      @input="onInput"
      @blur="touched = true"
    />
    <small v-if="showError" :id="`${inputId}-error`" class="base-phone-error">{{ errorText }}</small>
    <small v-else-if="hint" class="base-phone-hint">{{ hint }}</small>
  </label>
</template>

<script setup>
import { computed, ref } from 'vue'
import {
  IRAN_MOBILE_PLACEHOLDER,
  iranMobileErrorMessage,
  isValidIranMobile,
  normalizeIranMobile
} from '../../utils/phone'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'شماره موبایل' },
  placeholder: { type: String, default: IRAN_MOBILE_PLACEHOLDER },
  hint: { type: String, default: 'باید با ۰۹ شروع شود و ۱۱ رقم باشد' },
  required: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  allowEmpty: { type: Boolean, default: false },
  showErrorWhenEmpty: { type: Boolean, default: false },
  forceShowError: { type: Boolean, default: false },
  inputId: { type: String, default: () => `phone-${Math.random().toString(36).slice(2, 9)}` }
})

const emit = defineEmits(['update:modelValue', 'valid-change'])

const touched = ref(false)

const errorText = computed(() => iranMobileErrorMessage(props.modelValue, {
  allowEmpty: props.allowEmpty && !props.showErrorWhenEmpty,
  label: props.label || 'شماره موبایل'
}))

const isComplete = computed(() => isValidIranMobile(props.modelValue))

const showError = computed(() => {
  if (props.forceShowError && errorText.value) return true
  if (!errorText.value) return false
  if (touched.value) return true
  return Boolean(props.modelValue) && !isComplete.value
})

const onInput = (event) => {
  const next = normalizeIranMobile(event?.target?.value)
  emit('update:modelValue', next)
  emit('valid-change', isValidIranMobile(next))
}

defineExpose({
  validate: () => {
    touched.value = true
    return !errorText.value
  },
  errorText,
  isValid: isComplete
})
</script>

<style scoped>
.base-phone-field {
  display: grid;
  gap: 6px;
  min-width: 0;
}
.base-phone-label {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}
.base-phone-field input {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  border: 1px solid #d7e3f0;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  letter-spacing: 0.04em;
  transition: border-color .16s ease, box-shadow .16s ease;
}
.base-phone-field input:focus {
  outline: none;
  border-color: #1d4ed8;
  box-shadow: 0 0 0 3px rgba(29, 78, 216, 0.12);
}
.base-phone-field.has-error input {
  border-color: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}
.base-phone-field.is-valid input {
  border-color: #16a34a;
}
.base-phone-error {
  color: #b91c1c;
  font-size: 12px;
  line-height: 1.7;
}
.base-phone-hint {
  color: #64748b;
  font-size: 12px;
  line-height: 1.7;
}
</style>
