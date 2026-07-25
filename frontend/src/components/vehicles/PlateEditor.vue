<template>
  <div class="plate-editor" :class="{ 'plate-editor-disabled': disabled, 'plate-editor-dense': dense }">
    <div v-if="showTypeSwitch || showAnonymousToggle || showPieceWashToggle" class="plate-tools">
      <label v-if="showTypeSwitch" class="plate-type-select">
        <span>نوع پلاک</span>
        <select :value="plateKind" :disabled="disabled" @change="setPlateType($event.target.value)">
          <option value="car">خودرو</option>
          <option value="motorcycle">موتور سیکلت</option>
        </select>
      </label>
      <label v-if="showAnonymousToggle" class="toggle-check">
        <input :checked="anonymous" :disabled="disabled" type="checkbox" @change="emit('update:anonymous', $event.target.checked)" />
        <span>بی‌نام</span>
      </label>
      <label v-if="showPieceWashToggle" class="toggle-check">
        <input :checked="pieceWash" :disabled="disabled" type="checkbox" @change="emit('update:pieceWash', $event.target.checked)" />
        <span>قطعه‌شویی</span>
      </label>
    </div>

    <div
      v-if="!anonymous && !pieceWash"
      class="plate-entry-shell"
      :class="[`plate-entry-${plateKind}`]"
    >
      <div v-if="plateKind === 'motorcycle'" class="manual-plate-badge manual-plate-motorcycle" dir="ltr">
        <div class="manual-plate-blue manual-plate-blue-motor">
          <span>I.R.</span>
          <span>IRAN</span>
        </div>
        <div class="manual-plate-main">
          <div class="motor-row-top">
            <input
              :value="plateMid"
              class="plate-input mid"
              maxlength="3"
              inputmode="numeric"
              pattern="[0-9]*"
              autocomplete="off"
              placeholder="---"
              :disabled="disabled"
              @focus="selectFieldText"
              @keydown="onDigitKeydown"
              @paste="onDigitPaste($event, 'plateMid', 3)"
              @input="handleMotorPartInput('plateMid', $event)"
            />
          </div>
          <div class="motor-row-bottom">
            <input
              :value="plateLetter"
              class="plate-input motor-bottom-input"
              maxlength="5"
              inputmode="numeric"
              pattern="[0-9]*"
              autocomplete="off"
              placeholder="-----"
              :disabled="disabled"
              @focus="selectFieldText"
              @keydown="onDigitKeydown"
              @paste="onDigitPaste($event, 'plateLetter', 5)"
              @input="handleMotorPartInput('plateLetter', $event)"
            />
          </div>
        </div>
      </div>
      <div v-else class="manual-plate-badge manual-plate-car" dir="ltr">
        <div class="manual-plate-main manual-plate-white-wrap">
          <input
            ref="plateRightInputRef"
            :value="plateRight"
            class="plate-input right"
            maxlength="2"
            inputmode="numeric"
            pattern="[0-9]*"
            autocomplete="off"
            placeholder="--"
            :disabled="disabled"
            @focus="selectFieldText"
            @keydown="onDigitKeydown"
            @paste="onDigitPaste($event, 'plateRight', 2)"
            @input="handleCarPartInput('plateRight', $event)"
          />
          <select
            ref="plateLetterInputRef"
            :value="plateLetter"
            class="plate-input letter plate-letter-select"
            :disabled="disabled"
            @change="handleCarPartInput('plateLetter', $event)"
          >
            <option value="">حرف</option>
            <option v-for="letter in plateLetterOptions" :key="letter" :value="letter">{{ letter }}</option>
          </select>
          <input
            ref="plateMidInputRef"
            :value="plateMid"
            class="plate-input mid"
            maxlength="3"
            inputmode="numeric"
            pattern="[0-9]*"
            autocomplete="off"
            placeholder="---"
            :disabled="disabled"
            @focus="selectFieldText"
            @keydown="onDigitKeydown"
            @paste="onDigitPaste($event, 'plateMid', 3)"
            @input="handleCarPartInput('plateMid', $event)"
          />
        </div>
        <div class="manual-plate-blue">
          <input
            ref="plateLeftInputRef"
            :value="plateLeft"
            class="plate-input blue-input"
            maxlength="2"
            inputmode="numeric"
            pattern="[0-9]*"
            autocomplete="off"
            placeholder="--"
            :disabled="disabled"
            @focus="selectFieldText"
            @keydown="onDigitKeydown"
            @paste="onDigitPaste($event, 'plateLeft', 2)"
            @input="handleCarPartInput('plateLeft', $event)"
          />
        </div>
      </div>
    </div>
    <div v-else class="anonymous-plate-note">
      {{ pieceWash ? 'برای قطعه‌شویی پلاک خودرو ثبت نمی‌شود.' : 'برای پذیرش بی‌نام، ورود دستی پلاک پنهان می‌شود.' }}
    </div>

    <div
      v-if="plateKind === 'car' && letterSuggestions.length > 1"
      class="letter-suggestions-panel"
      role="group"
      aria-label="انتخاب حرف مبهم پلاک"
    >
      <p class="letter-suggestions-hint">
        حرف شبیه چند گزینه است — یکی را انتخاب کنید
      </p>
      <div class="letter-suggestions">
        <button
          v-for="option in letterSuggestions"
          :key="option"
          type="button"
          class="letter-chip"
          :class="{ active: plateLetter === option }"
          :disabled="disabled"
          @click="selectLetterSuggestion(option)"
        >
          <span class="letter-chip-glyph">{{ option }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { normalizeDigits, normalizePlateLetter } from '../../utils/plate'

const emit = defineEmits([
  'update:plateLeft',
  'update:plateLetter',
  'update:plateMid',
  'update:plateRight',
  'update:plateType',
  'update:anonymous',
  'update:pieceWash'
])

const props = defineProps({
  plateLeft: { type: String, default: '' },
  plateLetter: { type: String, default: '' },
  plateMid: { type: String, default: '' },
  plateRight: { type: String, default: '' },
  plateType: { type: String, default: 'car' },
  anonymous: { type: Boolean, default: false },
  pieceWash: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  showTypeSwitch: { type: Boolean, default: true },
  showAnonymousToggle: { type: Boolean, default: false },
  showPieceWashToggle: { type: Boolean, default: false },
  letterSuggestions: { type: Array, default: () => [] },
  dense: { type: Boolean, default: false }
})

const plateRightInputRef = ref(null)
const plateLetterInputRef = ref(null)
const plateMidInputRef = ref(null)
const plateLeftInputRef = ref(null)

const plateLetterOptions = ['الف', 'ب', 'پ', 'ت', 'ث', 'ج', 'چ', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'ژ', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ک', 'گ', 'ل', 'م', 'ن', 'و', 'ه', 'ی']
const plateKind = computed(() => (props.plateType === 'motorcycle' ? 'motorcycle' : 'car'))

const digitPart = (value, limit) => normalizeDigits(value).replace(/\D/g, '').slice(0, limit)

const isDigitKeyEvent = (event) => {
  if (event.ctrlKey || event.metaKey || event.altKey) return true
  const allowed = ['Backspace', 'Delete', 'Tab', 'Enter', 'Escape', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End']
  if (allowed.includes(event.key)) return true
  return /^[0-9۰-۹٠-٩]$/.test(event.key)
}

const onDigitKeydown = (event) => {
  if (!isDigitKeyEvent(event)) event.preventDefault()
}

const onDigitPaste = (event, key, limit) => {
  event.preventDefault()
  const pasted = digitPart(event.clipboardData?.getData('text') || '', limit)
  emit(`update:${key}`, pasted)
  if (event.target) event.target.value = pasted
  if (plateKind.value !== 'motorcycle') focusNextPlatePart(key, pasted)
}

const setPlateType = (value) => {
  const nextType = value === 'motorcycle' ? 'motorcycle' : 'car'
  emit('update:plateType', nextType)
  emit('update:plateMid', digitPart(props.plateMid, 3))
  if (nextType === 'motorcycle') {
    emit('update:plateLeft', '')
    emit('update:plateRight', '')
    emit('update:plateLetter', digitPart(props.plateLetter, 5))
    return
  }
  emit('update:plateLetter', normalizePlateLetter(props.plateLetter))
}

const selectFieldText = (event) => {
  const element = event?.target
  if (!element || typeof element.select !== 'function') return
  requestAnimationFrame(() => element.select())
}

const focusNextPlatePart = (key, nextValue) => {
  if (plateKind.value === 'motorcycle') return
  const target = {
    plateRight: String(nextValue || '').length >= 2 ? plateLetterInputRef.value : null,
    plateLetter: String(nextValue || '').trim() ? plateMidInputRef.value : null,
    plateMid: String(nextValue || '').length >= 3 ? plateLeftInputRef.value : null
  }[key]
  if (!target || typeof target.focus !== 'function') return
  requestAnimationFrame(() => target.focus())
}

const handleCarPartInput = (key, event) => {
  const rawValue = event?.target?.value || ''
  let nextValue = ''
  if (key === 'plateLetter') {
    nextValue = normalizePlateLetter(rawValue)
    emit('update:plateLetter', nextValue)
  } else {
    const limits = { plateLeft: 2, plateMid: 3, plateRight: 2 }
    nextValue = digitPart(rawValue, limits[key] || 2)
    emit(`update:${key}`, nextValue)
    if (event?.target) event.target.value = nextValue
  }
  focusNextPlatePart(key, nextValue)
}

const handleMotorPartInput = (key, event) => {
  const rawValue = event?.target?.value || ''
  const nextValue = digitPart(rawValue, key === 'plateLetter' ? 5 : 3)
  emit(`update:${key}`, nextValue)
  if (event?.target) event.target.value = nextValue
}

const selectLetterSuggestion = (letter) => {
  if (plateKind.value !== 'car') return
  emit('update:plateLetter', normalizePlateLetter(letter))
}
</script>

<style scoped>
.plate-editor {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.plate-editor-disabled {
  opacity: .72;
}

.plate-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  padding: 8px 12px;
  border-radius: 16px;
  background: #f4f8ff;
  border: 1px solid #dde8f8;
}

.toggle-check,
.plate-type-select {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.toggle-check input {
  width: 17px;
  height: 17px;
}

.plate-type-select select {
  height: 36px;
  border: 1px solid #c8d7ea;
  border-radius: 12px;
  background: #fff;
  padding: 0 10px;
  font: inherit;
}

.plate-entry-shell {
  display: block;
}

.manual-plate-badge {
  display: flex;
  align-items: stretch;
  justify-content: center;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  border-radius: 8px;
  padding: 0;
  overflow: hidden;
  direction: ltr;
  border: 0;
  background: transparent;
}

.manual-plate-main {
  min-width: 0;
  flex: 1;
  background: #f4f5ff;
}

.manual-plate-car .manual-plate-main {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-radius: 6px 0 0 6px;
  padding: 4px 12px;
}

.manual-plate-motorcycle .manual-plate-main {
  display: grid;
  grid-template-rows: auto auto;
  gap: 4px;
  padding: 8px 10px 9px;
  border-radius: 6px 0 0 6px;
  background: #f4f5ff;
  border: 0;
  box-shadow: none;
}

.manual-plate-blue {
  min-width: 52px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #2563eb;
  color: #fff;
  border-radius: 0 6px 6px 0;
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  padding: 12px 0 8px;
  border: 0;
}

.manual-plate-blue-motor {
  flex-direction: column;
  gap: 4px;
  font-size: 9px;
  letter-spacing: 0.05em;
}

.plate-input {
  min-width: 0;
  height: 40px;
  border: 0;
  border-radius: 8px;
  background: transparent !important;
  text-align: center;
  color: #111827;
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
  padding: 0;
  font-family: inherit;
}

.manual-plate-car .plate-input.right,
.manual-plate-car .plate-input.left {
  width: 88px;
}

.manual-plate-car .plate-input.mid {
  width: 126px;
}

.manual-plate-car .plate-input.letter {
  width: 88px;
  min-width: 68px;
  padding: 0 18px 0 8px;
}

.blue-input {
  width: 74px !important;
  background: transparent !important;
  color: #ffffff;
  font-size: 24px;
  font-weight: 800;
}

.plate-input::placeholder {
  color: #94a3b8;
  opacity: 1;
}

.plate-input:focus {
  outline: none;
  background: transparent !important;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.14);
}

.plate-input.letter {
  font-size: 24px;
}

.plate-letter-select {
  appearance: auto;
  -webkit-appearance: menulist;
  direction: rtl;
  cursor: pointer;
  color: #0f172a;
  background-color: rgba(255, 255, 255, 0.2) !important;
}

.manual-plate-motorcycle .plate-input.mid {
  max-width: 200px;
  width: 100%;
  height: 52px;
  line-height: 52px;
  border: 1px solid transparent;
  border-radius: 14px;
  justify-self: center;
  font-size: 30px;
  font-weight: 950;
  letter-spacing: 0.16em;
  padding: 0 4px;
}

.manual-plate-motorcycle .motor-bottom-input {
  width: min(100%, 260px);
  height: 54px;
  line-height: 54px;
  border: 1px solid transparent;
  border-radius: 14px;
  font-size: 28px;
  font-weight: 950;
  letter-spacing: 0.18em;
  padding: 0 6px;
}

.motor-row-top,
.motor-row-bottom {
  display: grid;
  align-items: center;
  grid-template-columns: 1fr;
  justify-items: center;
  gap: 8px;
}

.letter-suggestions-panel {
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(241, 248, 255, 0.95), rgba(236, 244, 255, 0.88));
  border: 1px solid #cfe0f5;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
  animation: letter-suggest-in 0.28s ease-out;
}

.letter-suggestions-hint {
  margin: 0;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.45;
}

.letter-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.anonymous-plate-note {
  color: #b91c1c;
  font-size: 11px;
  font-weight: 700;
}

.letter-chip {
  min-width: 46px;
  height: 42px;
  padding: 0 12px;
  border: 1px solid #b9d0ea;
  border-radius: 999px;
  background: #fff;
  color: #1e3a5f;
  font-weight: 900;
  cursor: pointer;
  transition: transform 0.15s ease, background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.letter-chip:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: #7eb0e4;
  background: #f7fbff;
}

.letter-chip:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.letter-chip-glyph {
  display: inline-block;
  font-size: 18px;
  line-height: 1;
}

.letter-chip.active {
  background: linear-gradient(135deg, #1d4f91, #2f6fad);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 6px 14px rgba(29, 79, 145, 0.22);
}

@keyframes letter-suggest-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 640px) {
  .plate-tools {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    flex-wrap: nowrap;
    gap: 6px;
  }

  .plate-type-select,
  .toggle-check {
    font-size: 10px;
    gap: 5px;
  }

  .plate-type-select select {
    height: 32px;
    padding: 0 8px;
    font-size: 10px;
  }

  .manual-plate-badge {
    max-width: none;
    border-radius: 12px;
    padding: 6px;
  }

  .manual-plate-car .manual-plate-main {
    gap: 8px;
    padding: 4px 8px;
  }

  .manual-plate-motorcycle .manual-plate-main {
    padding: 8px 10px;
  }

  .plate-input {
    height: 20px;
    line-height: 1;
    border-radius: 6px;
    font-size: 11px;
  }

  .plate-input.letter {
    font-size: 11px;
  }

  .manual-plate-car .plate-input.right,
  .manual-plate-car .plate-input.left {
    width: 40px;
  }

  .manual-plate-car .plate-input.mid {
    width: 56px;
  }

  .manual-plate-car .plate-input.letter {
    width: 54px;
    min-width: 48px;
    padding: 0 12px 0 2px;
  }

  .manual-plate-blue {
    min-width: 24px;
    font-size: 10px;
    padding-top: 4px;
    padding-bottom: 2px;
  }

  .manual-plate-blue-motor {
    gap: 4px;
    font-size: 8px;
  }

  .manual-plate-motorcycle .plate-input.mid {
    max-width: 108px;
    height: 34px;
    line-height: 34px;
    border-radius: 14px;
    font-size: 16px;
  }

  .manual-plate-motorcycle .motor-bottom-input {
    width: min(100%, 150px);
    height: 34px;
    line-height: 34px;
    border-radius: 14px;
    font-size: 14px;
  }
}

@media (max-width: 380px) {
  .plate-input {
    height: 18px;
    font-size: 10px;
    border-radius: 6px;
  }

  .plate-input.letter {
    font-size: 11px;
  }

  .manual-plate-car .plate-input.right,
  .manual-plate-car .plate-input.left {
    width: 34px;
  }

  .manual-plate-car .plate-input.mid {
    width: 48px;
  }

  .manual-plate-car .plate-input.letter {
    width: 50px;
    min-width: 46px;
    padding: 0 10px 0 2px;
  }

  .manual-plate-motorcycle .plate-input.mid {
    max-width: 92px;
    height: 30px;
    line-height: 30px;
    border-radius: 12px;
    font-size: 14px;
  }

  .manual-plate-motorcycle .motor-bottom-input {
    width: min(100%, 132px);
    height: 30px;
    line-height: 30px;
    border-radius: 12px;
    font-size: 12px;
  }
}

.plate-editor-dense .manual-plate-badge {
  max-width: 320px;
}

.plate-editor-dense .manual-plate-car .manual-plate-main {
  gap: 6px;
  padding: 2px 8px;
}

.plate-editor-dense .manual-plate-blue {
  min-width: 40px;
  font-size: 16px;
  padding: 6px 0;
}

.plate-editor-dense .plate-input {
  height: 32px;
  font-size: 16px;
}

.plate-editor-dense .manual-plate-car .plate-input.right,
.plate-editor-dense .manual-plate-car .plate-input.left {
  width: 42px;
}

.plate-editor-dense .manual-plate-car .plate-input.mid {
  width: 58px;
}

.plate-editor-dense .manual-plate-car .plate-input.letter {
  width: 58px;
  min-width: 52px;
  padding: 0 4px;
}

.plate-editor-dense .blue-input {
  width: 40px !important;
  font-size: 16px;
}

.plate-editor-dense .manual-plate-motorcycle .manual-plate-main {
  padding: 4px 6px;
  gap: 2px;
}

.plate-editor-dense .manual-plate-motorcycle .plate-input.mid,
.plate-editor-dense .manual-plate-motorcycle .motor-bottom-input {
  height: 28px;
  line-height: 28px;
  font-size: 14px;
  max-width: 120px;
  width: 100%;
}
</style>
