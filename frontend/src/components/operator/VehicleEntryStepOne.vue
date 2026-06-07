<template>
  <section class="entry-step">
    <div class="step-layout">
      <article class="ai-panel">
        <header class="panel-head">
          <h3>دوربین و هوش مصنوعی</h3>
          <p>می‌توانید عکس پلاک بگیرید یا اطلاعات را دستی وارد کنید.</p>
        </header>

        <button type="button" class="camera-box" @click="onCaptureMock">
          <div class="camera-overlay">
            <div class="plate-guide">محل قرارگیری پلاک</div>
          </div>
          <span>برای شبیه‌سازی اسکن، کلیک کنید</span>
        </button>

        <div class="ai-result-grid">
          <div class="result-card">
            <small>پلاک شناسایی‌شده</small>
            <strong dir="ltr">{{ detectedPlate }}</strong>
          </div>
          <div class="result-card">
            <small>مدل و رنگ</small>
            <strong>{{ detectedModelColor }}</strong>
          </div>
        </div>
      </article>

      <form class="form-panel" @submit.prevent="onContinue">
        <header class="panel-head">
          <h3>فرم تکمیلی</h3>
          <p>{{ form.isPieceWash ? 'برای قطعه‌شویی فقط نام و شماره تلفن لازم است.' : 'برای ادامه، پلاک، مدل، رنگ و شماره تلفن الزامی است.' }}</p>
        </header>

        <label v-if="!form.isPieceWash" class="field">
          <span>شماره پلاک</span>
          <div class="plate-tools">
            <label class="toggle-check">
              <input v-model="form.isAnonymous" type="checkbox" />
              <span>بی‌نام</span>
            </label>
            <label class="toggle-check">
              <input v-model="form.isPieceWash" type="checkbox" />
              <span>قطعه‌شویی</span>
            </label>
          </div>
          <div class="plate-row" dir="ltr">
            <input v-model="form.plateRight" :disabled="form.isAnonymous" maxlength="2" inputmode="numeric" placeholder="67" @input="onlyDigits('plateRight')" />
            <span>-</span>
            <input v-model="form.plateMid" :disabled="form.isAnonymous" maxlength="3" inputmode="numeric" placeholder="345" @input="onlyDigits('plateMid')" />
            <input v-model="form.plateLetter" :disabled="form.isAnonymous" maxlength="1" placeholder="ب" @input="onlyLetter" />
            <input v-model="form.plateLeft" :disabled="form.isAnonymous" maxlength="2" inputmode="numeric" placeholder="12" @input="onlyDigits('plateLeft')" />
          </div>
        </label>
        <div v-else class="piece-wash-toggle-row">
          <label class="toggle-check">
            <input v-model="form.isPieceWash" type="checkbox" />
            <span>قطعه‌شویی</span>
          </label>
        </div>

        <div v-if="!form.isPieceWash" class="grid-2">
          <label class="field">
            <span>مدل خودرو</span>
            <input v-model="form.model" :disabled="form.isAnonymous" placeholder="مثال: پژو 206" />
          </label>
          <label class="field">
            <span>رنگ خودرو</span>
            <input v-model="form.color" :disabled="form.isAnonymous" placeholder="مثال: سفید" />
          </label>
        </div>

        <div class="grid-2">
          <label class="field">
            <span>{{ form.isPieceWash ? 'نام مشتری' : 'نام راننده (اختیاری)' }}</span>
            <input v-model="form.driver" placeholder="نام و نام خانوادگی" />
          </label>
          <label class="field">
            <span>شماره تماس</span>
            <input v-model="form.mobile" dir="ltr" placeholder="0912..." @input="onlyDigits('mobile')" />
          </label>
        </div>

        <label v-if="!form.isPieceWash" class="field">
          <span>توضیحات</span>
          <textarea v-model="form.note" rows="3" placeholder="نکات تکمیلی"></textarea>
        </label>

        <footer class="actions">
          <button type="button" class="secondary" @click="onRefer">ارجاع</button>
          <button type="submit" class="primary" :disabled="!canSubmit">ادامه</button>
        </footer>
      </form>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import api from '../../services/api'

const emit = defineEmits(['cancel', 'continue', 'refer'])
const props = defineProps({
  vehicleInfo: { type: Object, default: () => ({}) }
})

const form = reactive({
  id: null,
  plateLeft: '',
  plateLetter: '',
  plateMid: '',
  plateRight: '',
  model: '',
  color: '',
  driver: '',
  mobile: '',
  note: '',
  isAnonymous: false,
  isPieceWash: false
})

const hydrateForm = (data = {}) => {
  const plateNumber = String(data.plate || data.plate_number || '').trim()
  const parts = plateNumber.split(/\s+/).filter(Boolean)
  form.id = data.id ?? null
  form.plateLeft = String(data.plateLeft || data.plate_left || parts[0] || '').slice(0, 2)
  form.plateLetter = normalizePlateLetter(String(data.plateLetter || data.plate_letter || parts[1] || '').slice(0, 1))
  form.plateMid = String(data.plateMid || data.plate_mid || parts[2] || '').slice(0, 3)
  form.plateRight = String(data.plateRight || data.plate_right || parts[3] || '').slice(0, 2)
  form.model = String(data.model || data.car_model || '')
  form.color = String(data.color || data.car_color || '')
  form.driver = String(data.driver || data.driver_name || '')
  form.mobile = normalizeDigits(String(data.mobile || data.driver_phone || ''))
  form.note = String(data.note || data.notes || '')
  form.isAnonymous = Boolean(data.isAnonymous)
  form.isPieceWash = Boolean(data.isPieceWash || data.is_piece_wash)
}

const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (d) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)))
  .replace(/\D/g, '')

const onlyDigits = (key) => {
  form[key] = normalizeDigits(form[key])
}

const onlyLetter = () => {
  form.plateLetter = normalizePlateLetter(form.plateLetter)
}

const normalizePlateLetter = (value) => {
  const raw = String(value || '').replace(/\s+/g, '').slice(0, 1)
  const englishMap = { A: 'ا', B: 'ب', D: 'د', H: 'ه', J: 'ج', L: 'ل', M: 'م', N: 'ن', P: 'پ', S: 'س', T: 'ط', V: 'و', Y: 'ی' }
  const upper = raw.toUpperCase()
  if (englishMap[upper]) return englishMap[upper]
  return raw.replace(/[^آابپتثجچحخدذرزسشصضطظعغفقکگلمنوهی]/g, '')
}

const plate = computed(() => {
  if (form.isAnonymous) return '1111'
  const left = form.plateLeft.trim()
  const letter = form.plateLetter.trim()
  const mid = form.plateMid.trim()
  const right = form.plateRight.trim()
  if (!left || !letter || !mid || !right) return ''
  return `${left} ${letter} ${mid} ${right}`
})

const canSubmit = computed(() => {
  if (form.isPieceWash) {
    return form.driver.trim() && form.mobile.trim()
  }
  const hasPlate = form.isAnonymous || (form.plateLeft.length === 2 && form.plateMid.length === 3 && form.plateRight.length === 2 && form.plateLetter.length === 1)
  const hasModel = form.isAnonymous || form.model.trim()
  const hasColor = form.isAnonymous || form.color.trim()
  return hasPlate && hasModel && hasColor && form.mobile.trim()
})

const payload = () => ({
  id: form.id,
  plate: form.isPieceWash ? '' : plate.value,
  plateLeft: form.isAnonymous || form.isPieceWash ? '' : form.plateLeft.trim(),
  plateLetter: form.isAnonymous || form.isPieceWash ? '' : form.plateLetter.trim(),
  plateMid: form.isAnonymous || form.isPieceWash ? '' : form.plateMid.trim(),
  plateRight: form.isAnonymous || form.isPieceWash ? '' : form.plateRight.trim(),
  model: form.isPieceWash ? 'قطعه‌شویی' : (form.isAnonymous ? '1111' : form.model.trim()),
  color: form.isPieceWash ? '-' : (form.isAnonymous ? '1111' : form.color.trim()),
  driver: form.driver.trim(),
  mobile: form.mobile.trim(),
  note: form.isPieceWash ? '' : form.note.trim(),
  isAnonymous: form.isAnonymous,
  isPieceWash: form.isPieceWash
})

const onContinue = () => {
  if (!canSubmit.value) return
  emit('continue', payload())
}

const onRefer = () => {
  emit('refer', payload())
}

const onCaptureMock = () => {
  if (form.isAnonymous) return
  if (!form.plateLeft) form.plateLeft = '12'
  if (!form.plateLetter) form.plateLetter = 'ب'
  if (!form.plateMid) form.plateMid = '345'
  if (!form.plateRight) form.plateRight = '67'
  if (!form.model) form.model = 'پژو 206'
  if (!form.color) form.color = 'سفید'
}

const detectedPlate = computed(() => plate.value || '-- - --- --')
const detectedModelColor = computed(() => {
  const text = `${form.model.trim()} ${form.color.trim()}`.trim()
  return text || '---'
})

watch(() => props.vehicleInfo, (value) => {
  hydrateForm(value || {})
}, { immediate: true, deep: true })

watch(() => form.isAnonymous, (value) => {
  if (value) {
    form.plateLeft = ''
    form.plateLetter = ''
    form.plateMid = ''
    form.plateRight = ''
    form.model = '1111'
    form.color = '1111'
    return
  }
  if (form.model === '1111') form.model = ''
  if (form.color === '1111') form.color = ''
})

watch(() => form.isPieceWash, (value) => {
  if (!value) return
  form.isAnonymous = false
  form.plateLeft = ''
  form.plateLetter = ''
  form.plateMid = ''
  form.plateRight = ''
  form.model = ''
  form.color = ''
  form.note = ''
})

let lookupTimer = null
let lookupToken = 0
watch(
  () => [form.plateLeft, form.plateLetter, form.plateMid, form.plateRight, form.isAnonymous],
  async () => {
    if (lookupTimer) clearTimeout(lookupTimer)
    if (form.isAnonymous) return
    const hasFullPlate = form.plateLeft.length === 2 && form.plateMid.length === 3 && form.plateRight.length === 2 && form.plateLetter.length === 1
    if (!hasFullPlate) return
    lookupTimer = setTimeout(async () => {
      const token = ++lookupToken
      try {
        const { data } = await api.get('/vehicles/plate-lookup/', {
          params: {
            plate_left: form.plateLeft.trim(),
            plate_letter: form.plateLetter.trim(),
            plate_mid: form.plateMid.trim(),
            plate_right: form.plateRight.trim()
          }
        })
        if (token !== lookupToken || !data?.found) return
        form.driver = String(data.driver_name || '').trim()
        form.mobile = normalizeDigits(String(data.driver_phone || ''))
      } catch (_error) {
      }
    }, 220)
  }
)
</script>

<style scoped>
.entry-step { padding: 22px; background: #f7f9fb; height: 100%; min-height: 0; overflow-y: auto; overflow-x: hidden; }
.step-layout { display: grid; grid-template-columns: 1fr 1fr; border: 1px solid #dbe3ef; border-radius: 18px; overflow: hidden; background: #fff; }
.ai-panel, .form-panel { padding: 22px; display: grid; gap: 16px; }
.ai-panel { background: #f8fbff; border-left: 1px solid #e2e8f0; }
.panel-head h3 { margin: 0; font-size: 20px; color: #0f172a; }
.panel-head p { margin: 6px 0 0; font-size: 13px; color: #64748b; }
.camera-box { position: relative; min-height: 250px; border: 1px solid #cbd5e1; border-radius: 14px; background: linear-gradient(145deg, #eef4ff, #f8fafc); cursor: pointer; color: #334155; font-weight: 600; }
.camera-overlay { position: absolute; inset: 12px; border: 2px dashed #93c5fd; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.plate-guide { border: 2px solid #3b82f6; border-radius: 8px; padding: 12px 18px; background: #dbeafe; color: #1d4ed8; font-size: 13px; }
.camera-box > span { position: absolute; bottom: 14px; right: 14px; font-size: 13px; }
.ai-result-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.result-card { border: 1px solid #dbe3ef; border-radius: 12px; padding: 10px 12px; background: #fff; }
.result-card small { display: block; margin-bottom: 4px; color: #64748b; font-size: 11px; }
.result-card strong { color: #0f172a; font-size: 14px; }
.form-panel { gap: 12px; }
.field { display: grid; gap: 6px; }
.field > span { font-size: 12px; color: #475569; font-weight: 600; }
.field input, .field textarea { width: 100%; border: 1px solid #cbd5e1; border-radius: 10px; padding: 0 10px; font: inherit; background: #fff; }
.plate-tools { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.toggle-check { display: inline-flex; align-items: center; gap: 6px; color: #334155; font-size: 12px; font-weight: 700; }
.toggle-check input { width: 16px; height: 16px; }
.field input { height: 42px; }
.field textarea { min-height: 90px; padding-top: 10px; resize: vertical; }
.field input:focus, .field textarea:focus { outline: 2px solid #bfdbfe; border-color: #60a5fa; }
.piece-wash-toggle-row { display: flex; justify-content: flex-end; }
.plate-row { display: grid; grid-template-columns: 72px auto 84px 64px 72px; gap: 8px; align-items: center; justify-content: start; }
.plate-row span { display: inline-flex; align-items: center; justify-content: center; height: 42px; text-align: center; color: #64748b; font-weight: 700; }
.plate-row input { text-align: center; font-weight: 700; line-height: 42px; padding: 0; }
.grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.actions { margin-top: 4px; display: flex; gap: 8px; justify-content: flex-end; }
.actions button { height: 42px; border-radius: 10px; border: 0; padding: 0 14px; font-weight: 700; cursor: pointer; }
.secondary { background: #dcfce7; color: #166534; }
.primary { background: linear-gradient(135deg, #0058be 0%, #3b82f6 100%); color: #fff; }
.actions button:disabled { opacity: .5; cursor: not-allowed; }

@media (max-width: 1024px) {
  .step-layout { grid-template-columns: 1fr; }
  .ai-panel { border-left: 0; border-bottom: 1px solid #e2e8f0; }
}

@media (max-width: 640px) {
  .entry-step { padding: 12px; }
  .ai-panel, .form-panel { padding: 14px; }
  .grid-2 { grid-template-columns: 1fr; }
  .ai-result-grid { grid-template-columns: 1fr; }
  .plate-row { grid-template-columns: 62px auto 74px 56px 62px; }
  .actions { flex-wrap: wrap; }
  .actions button { flex: 1 1 100%; }
}
</style>
