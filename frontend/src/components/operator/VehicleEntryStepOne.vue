<template>
  <section class="entry-step">
    <div class="step-layout">
      <article class="ai-panel">
        <header class="panel-head">
          <h3>دوربین و هوش مصنوعی</h3>
          <p>می‌توانید عکس پلاک بگیرید یا اطلاعات را دستی وارد کنید.</p>
        </header>

        <div
          class="camera-box"
          :class="{ active: cameraState.active, loading: cameraState.loading }"
          role="button"
          tabindex="0"
          @click="captureFromVideo"
          @keydown.enter.prevent="captureFromVideo"
        >
          <video ref="cameraVideoRef" class="camera-video" autoplay playsinline muted></video>
          <canvas ref="cameraCanvasRef" class="camera-canvas"></canvas>
          <div class="camera-overlay">
            <div class="plate-guide">{{ cameraState.loading ? 'در حال پردازش پلاک...' : 'محل قرارگیری پلاک' }}</div>
          </div>
          <span>{{ cameraState.active ? 'روی تصویر کلیک کنید تا پلاک استخراج شود' : 'ابتدا دوربین را باز کنید' }}</span>
        </div>

        <div class="camera-actions">
          <button type="button" class="camera-action primary-camera" :disabled="cameraState.loading" @click="startCamera">
            {{ cameraState.active ? 'راه‌اندازی مجدد دوربین' : 'باز کردن دوربین' }}
          </button>
          <button type="button" class="camera-action" :disabled="cameraState.loading || !cameraState.active" @click="captureFromVideo">
            {{ cameraState.loading ? 'در حال تشخیص...' : 'تشخیص پلاک' }}
          </button>
          <button type="button" class="camera-action" :disabled="cameraState.loading" @click="cameraFileInputRef?.click()">
            دوربین گوشی / عکس
          </button>
          <input ref="cameraFileInputRef" class="camera-file" type="file" accept="image/*" capture="environment" @change="processCameraFile" />
        </div>

        <p v-if="cameraState.message" class="camera-message" :class="{ error: cameraState.error }">
          {{ cameraState.message }}
        </p>

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
          <div v-if="letterSuggestionOptions.length > 1" class="letter-suggestions">
            <button
              v-for="option in letterSuggestionOptions"
              :key="option"
              type="button"
              class="letter-chip"
              :class="{ active: form.plateLetter === option }"
              @click="selectLetterSuggestion(option)"
            >
              {{ option }}
            </button>
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
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
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

const cameraVideoRef = ref(null)
const cameraCanvasRef = ref(null)
const cameraFileInputRef = ref(null)
const cameraStream = ref(null)
const cameraState = reactive({
  active: false,
  loading: false,
  message: '',
  error: false,
  lastConfidence: 0,
  lastLatency: 0
})
const letterSuggestions = ref([])
const aiSessionId = `entry-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
const isMobileDevice = /Android|iPhone|iPad|iPod|Mobile|Opera Mini|IEMobile/i.test(window.navigator.userAgent || '')
const canUseLiveCamera = Boolean(window.isSecureContext || ['localhost', '127.0.0.1'].includes(window.location.hostname))
const OCR_LETTER_CONFUSIONS = {
  ب: ['ب', 'س', 'ص'],
  س: ['س', 'ب', 'ص'],
  ص: ['ص', 'س', 'ب'],
  ق: ['ق', 'ی'],
  ی: ['ی', 'ق'],
  ر: ['ر', 'ط'],
  ط: ['ط', 'ر']
}

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
  syncLetterSuggestions(form.plateLetter)
}

const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (d) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)))
  .replace(/\D/g, '')

const onlyDigits = (key) => {
  form[key] = normalizeDigits(form[key])
}

const onlyLetter = () => {
  form.plateLetter = normalizePlateLetter(form.plateLetter)
  syncLetterSuggestions(form.plateLetter)
}

const normalizePlateLetter = (value) => {
  const raw = String(value || '').replace(/\s+/g, '').slice(0, 1)
  const englishMap = { A: 'ا', B: 'ب', D: 'د', H: 'ه', J: 'ج', L: 'ل', M: 'م', N: 'ن', P: 'پ', S: 'س', T: 'ط', V: 'و', Y: 'ی' }
  const upper = raw.toUpperCase()
  if (englishMap[upper]) return englishMap[upper]
  return raw.replace(/[^آابپتثجچحخدذرزسشصضطظعغفقکگلمنوهی]/g, '')
}

const buildLetterSuggestions = (letter) => {
  const normalized = normalizePlateLetter(letter)
  if (!normalized) return []
  return OCR_LETTER_CONFUSIONS[normalized] || [normalized]
}

const syncLetterSuggestions = (letter) => {
  letterSuggestions.value = buildLetterSuggestions(letter)
}

const selectLetterSuggestion = (letter) => {
  form.plateLetter = normalizePlateLetter(letter)
  syncLetterSuggestions(form.plateLetter)
}

const setCameraMessage = (message, isError = false) => {
  cameraState.message = message
  cameraState.error = isError
}

const stopCamera = () => {
  if (cameraStream.value) {
    cameraStream.value.getTracks().forEach((track) => track.stop())
  }
  cameraStream.value = null
  cameraState.active = false
  if (cameraVideoRef.value) cameraVideoRef.value.srcObject = null
}

const startCamera = async () => {
  if (cameraState.loading) return
  setCameraMessage('')
  try {
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraMessage('دسترسی مستقیم به دوربین در این مرورگر فعال نیست. از گزینه دوربین گوشی / عکس استفاده کنید.', true)
      return
    }
    stopCamera()
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1280 },
        height: { ideal: 720 }
      },
      audio: false
    })
    cameraStream.value = stream
    if (cameraVideoRef.value) {
      cameraVideoRef.value.srcObject = stream
      await cameraVideoRef.value.play()
    }
    cameraState.active = true
    setCameraMessage('دوربین آماده است. پلاک را داخل کادر بگذارید و روی تصویر کلیک کنید.')
  } catch (error) {
    stopCamera()
    const isInsecure = !canUseLiveCamera
    setCameraMessage(
      isInsecure
        ? 'برای دوربین زنده روی گوشی باید سایت با HTTPS باز شود. فعلاً از گزینه دوربین گوشی / عکس استفاده کنید.'
        : 'اجازه دسترسی به دوربین داده نشد یا دوربین در دسترس نیست.',
      true
    )
  }
}

const dataUrlFromCanvas = (source, sourceWidth, sourceHeight) => {
  const canvas = cameraCanvasRef.value || document.createElement('canvas')
  const maxWidth = 1600
  const scale = Math.min(1, maxWidth / Math.max(1, sourceWidth))
  canvas.width = Math.max(1, Math.round(sourceWidth * scale))
  canvas.height = Math.max(1, Math.round(sourceHeight * scale))
  const context = canvas.getContext('2d')
  context.drawImage(source, 0, 0, canvas.width, canvas.height)
  return canvas.toDataURL('image/jpeg', 0.94)
}

const readFileAsDataUrl = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = () => resolve(String(reader.result || ''))
  reader.onerror = () => reject(new Error('file_read_failed'))
  reader.readAsDataURL(file)
})

const captureStillFromTrack = async () => {
  const track = cameraStream.value?.getVideoTracks?.()[0]
  if (!track || typeof window.ImageCapture !== 'function') return ''
  try {
    const imageCapture = new window.ImageCapture(track)
    const bitmap = await imageCapture.grabFrame()
    return dataUrlFromCanvas(bitmap, bitmap.width, bitmap.height)
  } catch (_error) {
    return ''
  }
}

const processCameraFile = async (event) => {
  const file = event.target?.files?.[0]
  event.target.value = ''
  if (!file || cameraState.loading) return
  const image = new Image()
  const objectUrl = URL.createObjectURL(file)
  try {
    const originalImageDataUrl = await readFileAsDataUrl(file)
    await new Promise((resolve, reject) => {
      image.onload = resolve
      image.onerror = reject
      image.src = objectUrl
    })
    const imageDataUrl = image.naturalWidth >= 900 ? originalImageDataUrl : dataUrlFromCanvas(image, image.naturalWidth, image.naturalHeight)
    await recognizePlateImage(imageDataUrl)
  } catch (_error) {
    setCameraMessage('تصویر انتخاب‌شده قابل خواندن نیست.', true)
  } finally {
    URL.revokeObjectURL(objectUrl)
  }
}

const captureFromVideo = async () => {
  if (cameraState.loading || form.isAnonymous || form.isPieceWash) return
  if (!cameraState.active || !cameraVideoRef.value?.videoWidth) {
    await startCamera()
    return
  }
  const highResDataUrl = await captureStillFromTrack()
  const video = cameraVideoRef.value
  const imageDataUrl = highResDataUrl || dataUrlFromCanvas(video, video.videoWidth, video.videoHeight)
  await recognizePlateImage(imageDataUrl)
}

const applyRecognizedPlate = (data) => {
  const left = normalizeDigits(data?.plate_left || '')
  const mid = normalizeDigits(data?.plate_mid || '')
  const right = normalizeDigits(data?.plate_right || '')
  const letter = normalizePlateLetter(data?.plate_letter || '')
  const suggestions = buildLetterSuggestions(letter)
  if (left.length !== 2 || mid.length !== 3 || right.length !== 2 || !letter) return false
  form.isAnonymous = false
  form.isPieceWash = false
  form.plateLeft = left
  form.plateLetter = letter
  form.plateMid = mid
  form.plateRight = right
  letterSuggestions.value = suggestions
  return true
}

const tryResolveLetterFromHistory = async () => {
  if (form.isAnonymous || form.isPieceWash) return false
  if (form.plateLeft.length !== 2 || form.plateMid.length !== 3 || form.plateRight.length !== 2) return false
  const candidates = buildLetterSuggestions(form.plateLetter)
  if (candidates.length <= 1) return false
  const responses = await Promise.allSettled(
    candidates.map((letter) => api.get('/vehicles/plate-lookup/', {
      params: {
        plate_left: form.plateLeft.trim(),
        plate_letter: letter,
        plate_mid: form.plateMid.trim(),
        plate_right: form.plateRight.trim()
      },
      meta: { trackLoading: false }
    }))
  )
  const matches = responses
    .map((result, index) => ({ result, letter: candidates[index] }))
    .filter(({ result }) => result.status === 'fulfilled' && result.value?.data?.found)

  if (matches.length !== 1) return false
  const match = matches[0]
  form.plateLetter = match.letter
  form.driver = String(match.result.value.data.driver_name || '').trim()
  form.mobile = normalizeDigits(String(match.result.value.data.driver_phone || ''))
  syncLetterSuggestions(match.letter)
  return true
}

const recognizePlateImage = async (imageDataUrl) => {
  cameraState.loading = true
  setCameraMessage('در حال ارسال تصویر و تشخیص پلاک...')
  try {
    const { data } = await api.post('/vehicles/plate-recognition/', {
      session_id: aiSessionId,
      image_base64: imageDataUrl
    }, { meta: { trackLoading: false } })
    cameraState.lastConfidence = Number(data?.confidence || 0)
    cameraState.lastLatency = Number(data?.latency_ms || 0)
    if (!data?.accepted) {
      setCameraMessage(data?.detail || 'درخواست تشخیص پلاک پذیرفته نشد.', true)
      return
    }
    if (!applyRecognizedPlate(data)) {
      const extractedText = String(data?.persian_text || data?.text || '').trim()
      const aiReason = String(data?.reason || '').trim()
      setCameraMessage(
        extractedText
          ? `متن پلاک خوانده شد اما فرم آن کامل نیست: ${extractedText}`
          : `پلاک در تصویر پیدا نشد${aiReason ? ` (${aiReason})` : ''}. عکس واضح‌تر و نزدیک‌تر بگیرید.`,
        true
      )
      return
    }
    const correctedFromHistory = await tryResolveLetterFromHistory()
    const confidenceText = cameraState.lastConfidence ? ` | اطمینان ${(cameraState.lastConfidence * 100).toFixed(0)}٪` : ''
    setCameraMessage(
      correctedFromHistory
        ? `پلاک ${plate.value} از روی سابقه مشتری اصلاح و ثبت شد${confidenceText}.`
        : `پلاک ${plate.value} ثبت شد${confidenceText}.`
    )
  } catch (error) {
    const detail = error?.response?.data?.detail || 'ارتباط با سرویس تشخیص پلاک برقرار نشد.'
    setCameraMessage(detail, true)
  } finally {
    cameraState.loading = false
  }
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

const detectedPlate = computed(() => plate.value || '-- - --- --')
const detectedModelColor = computed(() => {
  const text = `${form.model.trim()} ${form.color.trim()}`.trim()
  return text || '---'
})
const letterSuggestionOptions = computed(() => letterSuggestions.value)

watch(() => props.vehicleInfo, (value) => {
  hydrateForm(value || {})
}, { immediate: true, deep: true })

watch(() => form.isAnonymous, (value) => {
  if (value) {
    stopCamera()
    form.plateLeft = ''
    form.plateLetter = ''
    form.plateMid = ''
    form.plateRight = ''
    letterSuggestions.value = []
    form.model = '1111'
    form.color = '1111'
    return
  }
  if (form.model === '1111') form.model = ''
  if (form.color === '1111') form.color = ''
})

watch(() => form.isPieceWash, (value) => {
  if (!value) return
  stopCamera()
  form.isAnonymous = false
  form.plateLeft = ''
  form.plateLetter = ''
  form.plateMid = ''
  form.plateRight = ''
  letterSuggestions.value = []
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

onMounted(async () => {
  if (form.isAnonymous || form.isPieceWash) return
  if (!isMobileDevice) return
  if (!navigator.mediaDevices?.getUserMedia) {
    setCameraMessage('این مرورگر دوربین زنده را پشتیبانی نمی‌کند. از گزینه دوربین گوشی / عکس استفاده کنید.', true)
    return
  }
  if (!canUseLiveCamera) {
    setCameraMessage('برای فعال شدن دوربین زنده در موبایل باید سایت را با HTTPS باز کنید. در این حالت از گزینه دوربین گوشی / عکس استفاده کنید.', true)
    return
  }
  await startCamera()
})

onBeforeUnmount(() => {
  stopCamera()
})
</script>

<style scoped>
.entry-step {
  display: block;
  padding: 18px;
  min-height: 0;
  height: auto;
  overflow: visible;
  background: transparent;
}

.step-layout {
  min-height: 0;
  height: auto;
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
  gap: 0;
  width: 100%;
  max-width: 100%;
  border: 1px solid rgba(199, 220, 255, 0.9);
  border-radius: 28px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(18px);
  box-shadow: 0 26px 60px -38px rgba(15, 23, 42, 0.35);
}

.ai-panel,
.form-panel {
  padding: 24px;
  display: grid;
  align-content: start;
  gap: 16px;
  min-height: 0;
  min-width: 0;
}

.ai-panel {
  background:
    radial-gradient(circle at top, rgba(65, 211, 255, 0.14), transparent 35%),
    linear-gradient(180deg, rgba(244, 249, 255, 0.96), rgba(237, 245, 255, 0.9));
  border-left: 1px solid rgba(226, 232, 240, 0.9);
  overflow: visible;
}

.form-panel {
  background: rgba(255, 255, 255, 0.88);
  overflow: visible;
  padding-bottom: max(24px, env(safe-area-inset-bottom));
}

.panel-head h3 {
  margin: 0;
  font-size: 22px;
  color: #0f172a;
}

.panel-head p {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.9;
  color: #64748b;
}

.camera-box {
  position: relative;
  min-height: 280px;
  border: 1px solid rgba(148, 197, 255, 0.75);
  border-radius: 24px;
  background:
    radial-gradient(circle at top, rgba(191, 219, 254, 0.45), transparent 38%),
    rgba(255, 255, 255, 0.72);
  cursor: pointer;
  color: #334155;
  font-weight: 700;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85), 0 22px 44px -34px rgba(30, 111, 217, 0.45);
  overflow: hidden;
  display: block;
}

.camera-box.active {
  background: #020617;
  border-color: rgba(59, 130, 246, 0.72);
}

.camera-box.loading {
  cursor: wait;
}

.camera-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity .2s ease;
}

.camera-box.active .camera-video {
  opacity: 1;
}

.camera-canvas,
.camera-file {
  display: none;
}

.camera-overlay {
  position: absolute;
  inset: 16px;
  border: 2px dashed #9cc4f5;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.plate-guide {
  border: 2px solid #2563eb;
  border-radius: 16px;
  padding: 14px 20px;
  background: rgba(219, 234, 254, 0.82);
  color: #1d4ed8;
  font-size: 13px;
}

.camera-box.active .camera-overlay {
  border-color: rgba(255, 255, 255, 0.74);
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.06), rgba(15, 23, 42, 0.24));
}

.camera-box.active .plate-guide {
  background: rgba(37, 99, 235, 0.82);
  color: #fff;
  border-color: rgba(255, 255, 255, 0.82);
}

.camera-box > span {
  position: absolute;
  bottom: 16px;
  right: 18px;
  font-size: 13px;
  z-index: 2;
  max-width: calc(100% - 36px);
  padding: 8px 11px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  color: #1e293b;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.1);
}

.camera-box.active > span {
  background: rgba(15, 23, 42, 0.72);
  color: #fff;
}

.camera-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 9px;
}

.camera-action {
  min-height: 42px;
  border: 1px solid #d4e2f5;
  border-radius: 15px;
  background: linear-gradient(180deg, #fff, #f4f8ff);
  color: #315f9f;
  font-weight: 800;
  cursor: pointer;
  padding: 0 10px;
}

.camera-action.primary-camera {
  border-color: transparent;
  background: linear-gradient(135deg, #1e5fae, #3b82c4);
  color: #fff;
}

.camera-action:disabled {
  opacity: .58;
  cursor: not-allowed;
}

.camera-message {
  margin: -4px 0 0;
  padding: 11px 13px;
  border: 1px solid #bfdbfe;
  border-radius: 16px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
  line-height: 1.8;
  font-weight: 700;
}

.camera-message.error {
  border-color: #fecdd3;
  background: #fff1f2;
  color: #9f1239;
}

.ai-result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.result-card {
  border: 1px solid rgba(199, 220, 255, 0.9);
  border-radius: 18px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 14px 28px -30px rgba(15, 23, 42, 0.45);
}

.result-card small {
  display: block;
  margin-bottom: 5px;
  color: #64748b;
  font-size: 11px;
}

.result-card strong {
  color: #0f172a;
  font-size: 14px;
}

.form-panel {
  gap: 14px;
}

.field {
  display: grid;
  gap: 7px;
}

.field > span {
  font-size: 12px;
  color: #475569;
  font-weight: 700;
}

.field input,
.field textarea {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  border: 1px solid #c8d7ea;
  border-radius: 18px;
  padding: 0 14px;
  font: inherit;
  background: #fff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
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

.toggle-check {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.toggle-check input {
  width: 17px;
  height: 17px;
}

.field input {
  height: 48px;
}

.field textarea {
  min-height: 96px;
  padding-top: 12px;
  resize: vertical;
}

.field input:focus,
.field textarea:focus {
  outline: 2px solid rgba(96, 165, 250, 0.18);
  border-color: #60a5fa;
}

.piece-wash-toggle-row {
  display: flex;
  justify-content: flex-end;
}

.plate-row {
  display: grid;
  grid-template-columns: 78px auto 92px 72px 78px;
  gap: 8px;
  align-items: center;
  justify-content: start;
  width: 100%;
  max-width: 100%;
  padding: 10px;
  border: 1px solid #dce6f7;
  border-radius: 22px;
  background: #f9fbff;
  overflow: hidden;
}

.plate-row span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 48px;
  text-align: center;
  color: #64748b;
  font-weight: 700;
}

.plate-row input {
  min-width: 0;
  text-align: center;
  font-weight: 800;
  line-height: 48px;
  padding: 0;
}

.letter-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.letter-chip {
  min-width: 42px;
  height: 38px;
  border: 1px solid #d5e3f7;
  border-radius: 14px;
  background: #f8fbff;
  color: #334155;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
  transition: background-color .18s ease, border-color .18s ease, color .18s ease, box-shadow .18s ease;
}

.letter-chip.active {
  border-color: #1e6fd9;
  background: rgba(30, 111, 217, 0.1);
  color: #0f172a;
  box-shadow: 0 10px 18px -14px rgba(30, 111, 217, 0.75);
}

.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.actions {
  position: sticky;
  bottom: 0;
  z-index: 2;
  margin-top: 6px;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding-top: 12px;
  padding-bottom: 4px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.92) 28%, #fff 100%);
}

.actions button {
  height: 48px;
  border-radius: 18px;
  border: 0;
  padding: 0 18px;
  font-weight: 800;
  cursor: pointer;
}

.secondary {
  background: #eef2f7;
  color: #334155;
}

.primary {
  background: linear-gradient(135deg, #0058be 0%, #1e6fd9 100%);
  color: #fff;
  box-shadow: 0 16px 28px -18px rgba(0, 88, 190, 0.55);
}

.actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 1024px) {
  .step-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto;
  }
  .ai-panel {
    border-left: 0;
    border-bottom: 1px solid #e2e8f0;
    overflow: visible;
  }
}

@media (max-width: 640px) {
  .entry-step {
    padding: 12px;
    padding-bottom: max(12px, env(safe-area-inset-bottom));
    height: auto;
    overflow: visible;
  }
  .step-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto;
    gap: 0;
    height: auto;
    min-height: auto;
    border: 1px solid rgba(205, 223, 247, 0.95);
    border-radius: 24px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 22px 42px -34px rgba(15, 23, 42, 0.28);
    overflow: hidden;
  }
  .ai-panel,
  .form-panel {
    padding: 14px;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    overflow: visible;
  }
  .ai-panel {
    border-bottom: 1px solid rgba(205, 223, 247, 0.95);
    overflow: visible;
  }
  .panel-head h3 {
    font-size: 17px;
  }
  .panel-head p {
    font-size: 11px;
    margin-top: 5px;
  }
  .grid-2,
  .ai-result-grid,
  .camera-actions { grid-template-columns: 1fr; }
  .plate-tools,
  .piece-wash-toggle-row { flex-direction: column; align-items: stretch; }
  .plate-row {
    grid-template-columns: 48px minmax(0, 1fr) 56px 44px 48px;
    gap: 4px;
    padding: 6px;
    border-radius: 18px;
  }
  .field input {
    height: 40px;
    font-size: 12px;
  }
  .field textarea {
    min-height: 72px;
    font-size: 12px;
  }
  .actions {
    gap: 8px;
    padding-top: 10px;
    padding-bottom: max(6px, env(safe-area-inset-bottom));
  }
  .actions button {
    flex: 1 1 100%;
    height: 42px;
    font-size: 13px;
    border-radius: 16px;
  }
  .camera-box { min-height: 210px; border-radius: 20px; }
  .camera-overlay { inset: 12px; border-radius: 16px; }
  .camera-box > span,
  .result-card strong,
  .toggle-check,
  .field > span {
    font-size: 11px;
  }
  .plate-guide {
    font-size: 11px;
    border-radius: 14px;
    padding: 10px 14px;
  }
}

@media (max-width: 380px) {
  .entry-step {
    padding: 10px;
  }

  .ai-panel,
  .form-panel {
    padding: 12px;
  }

  .plate-row {
    grid-template-columns: 42px minmax(0, 1fr) 50px 40px 42px;
    gap: 4px;
    padding: 5px;
  }

  .plate-row span,
  .plate-row input {
    height: 36px;
    line-height: 36px;
    font-size: 11px;
  }

  .field input {
    padding-inline: 10px;
  }
}
</style>
