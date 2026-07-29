<template>
  <section class="entry-step">
    <div class="step-layout">
      <article v-if="showAiPanel" class="ai-panel">
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
          <span>{{ cameraHintText }}</span>
        </div>

        <div class="camera-actions">
          <button type="button" class="camera-action primary-camera" :disabled="cameraState.loading" @click="startCamera()">
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
            <PlateBadge
              :plate-number="detectedPlate"
              :plate-left="detectedPlateParts.left"
              :plate-letter="detectedPlateParts.letter"
              :plate-mid="detectedPlateParts.mid"
              :plate-right="detectedPlateParts.right"
              :plate-type="detectedPlateType"
              compact
            />
          </div>
          <div class="result-card">
            <small>مدل و رنگ</small>
            <strong>{{ detectedModelColor }}</strong>
          </div>
        </div>

        <section v-if="!form.isPieceWash && !isMobileViewport" class="tariff-type-row" aria-label="تیپ نرخنامه">
          <span>تیپ نرخنامه</span>
          <div class="tariff-bubbles" :style="tariffBubblesStyle">
            <button
              v-for="option in availableTariffTypeOptions"
              :key="option.value"
              type="button"
              class="tariff-bubble"
              :class="{ active: form.tariffType === option.value }"
              @click="form.tariffType = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </section>
      </article>

      <form class="form-panel" @submit.prevent="onContinue">
        <header class="panel-head">
          <h3>فرم تکمیلی</h3>
          <p>{{ form.isPieceWash ? 'برای قطعه‌شویی، فقط شماره تماس برای ادامه الزامی است.' : 'در این مرحله فقط شماره تماس برای ادامه الزامی است.' }}</p>
        </header>

        <div v-if="isMobileViewport" class="ai-toggle-row">
          <button type="button" class="ai-toggle-btn" @click="toggleAiPanel">
            {{ isAiPanelCollapsed ? 'پلاک خوان' : 'بستن پلاک خوان' }}
          </button>
        </div>

        <div v-if="!form.isPieceWash" class="field">
          <span>شماره پلاک</span>
          <PlateEditor
            v-model:plate-left="form.plateLeft"
            v-model:plate-letter="form.plateLetter"
            v-model:plate-mid="form.plateMid"
            v-model:plate-right="form.plateRight"
            v-model:plate-type="form.plateType"
            v-model:anonymous="form.isAnonymous"
            v-model:piece-wash="form.isPieceWash"
            :letter-suggestions="letterSuggestionOptions"
            show-anonymous-toggle
            show-piece-wash-toggle
          />
        </div>
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
            <span>جنسیت راننده</span>
            <div class="gender-bubbles" role="radiogroup" aria-label="جنسیت راننده">
              <button
                type="button"
                class="gender-bubble"
                :class="{ active: form.driverGender === 'male' }"
                @click="form.driverGender = 'male'"
              >
                مرد
              </button>
              <button
                type="button"
                class="gender-bubble"
                :class="{ active: form.driverGender === 'female' }"
                @click="form.driverGender = 'female'"
              >
                زن
              </button>
            </div>
          </label>
          <label class="field">
            <span>شماره تماس</span>
            <input v-model="form.mobile" dir="ltr" placeholder="0912..." @input="onlyDigits('mobile')" />
            <small v-if="form.mobile && !isPhoneValid" class="field-error">شماره تماس باید دقیقا 11 رقم و با 09 شروع شود.</small>
          </label>
        </div>

        <section v-if="!form.isPieceWash && isMobileViewport" class="tariff-type-row mobile-tariff-row" aria-label="شماره تیپ">
          <span>شماره تیپ:</span>
          <div class="tariff-bubbles" :style="mobileTariffBubblesStyle">
            <button
              v-for="option in availableTariffTypeOptions"
              :key="option.value"
              type="button"
              class="tariff-bubble"
              :class="{ active: form.tariffType === option.value }"
              @click="form.tariffType = option.value"
            >
              {{ option.label.replace('تیپ ', '') }}
            </button>
          </div>
        </section>

        <section v-if="!form.isPieceWash && !isMobileViewport && !showAiPanel" class="tariff-type-row" aria-label="تیپ نرخنامه">
          <span>تیپ نرخنامه</span>
          <div class="tariff-bubbles" :style="tariffBubblesStyle">
            <button
              v-for="option in availableTariffTypeOptions"
              :key="option.value"
              type="button"
              class="tariff-bubble"
              :class="{ active: form.tariffType === option.value }"
              @click="form.tariffType = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </section>

        <label v-if="!form.isPieceWash" class="field">
          <span>توضیحات</span>
          <textarea v-model="form.note" rows="3" placeholder="نکات تکمیلی"></textarea>
        </label>

        <footer class="actions">
          <button type="button" class="secondary" :disabled="submitting || actionLocked" @click="onRefer">ارجاع</button>
          <button type="submit" class="primary" :disabled="!canSubmit || submitting || actionLocked">{{ submitting || actionLocked ? 'در حال ثبت...' : 'ادامه' }}</button>
        </footer>
      </form>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import api from '../../services/api'
import PlateBadge from '../vehicles/PlateBadge.vue'
import PlateEditor from '../vehicles/PlateEditor.vue'
import { buildPlateNumber, getAmbiguousLetterSuggestions, isValidIranMobile, normalizeDigits, normalizePhone, normalizePlateLetter, resolvePlateParts } from '../../utils/plate'
import {
  defaultTariffType,
  normalizeTariffType,
  serviceTierOptionsForPlate
} from '../../utils/serviceTiers'

const emit = defineEmits(['cancel', 'continue', 'refer'])
const props = defineProps({
  vehicleInfo: { type: Object, default: () => ({}) },
  submitting: { type: Boolean, default: false }
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
  driverGender: 'male',
  mobile: '',
  customerScore: 0,
  customerLoyaltyVisitCount: 0,
  customerLoyaltyDiscountPercent: 0,
  note: '',
  tariffType: defaultTariffType,
  plateType: 'car',
  isAnonymous: false,
  isPieceWash: false
})
const detectedPlateSnapshot = ref({
  left: '',
  letter: '',
  mid: '',
  right: '',
  plateNumber: '',
  plateType: 'car'
})
const aiRecognitionSnapshot = ref({
  sessionId: '',
  rawText: '',
  persianText: '',
  convertedPlate: '',
  convertedPlateLeft: '',
  convertedPlateLetter: '',
  convertedPlateMid: '',
  convertedPlateRight: '',
  convertedPlateType: 'car',
  imageBase64: '',
  confidence: null,
  latencyMs: null
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
const isAiPanelCollapsed = ref(false)
const isMobileViewport = ref(window.matchMedia('(max-width: 640px)').matches)
const actionLocked = ref(false)
const mobileViewportQuery = window.matchMedia('(max-width: 640px)')
let isHydratingForm = false
const aiSessionId = `entry-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
const isMobileDevice = /Android|iPhone|iPad|iPod|Mobile|Opera Mini|IEMobile/i.test(window.navigator.userAgent || '')
const canUseLiveCamera = Boolean(window.isSecureContext || ['localhost', '127.0.0.1'].includes(window.location.hostname))
const normalizeAiConfidence = (value) => {
  if (value === null || value === undefined || value === '') return null
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return null
  return Math.round(Math.min(999.99, Math.max(0, numericValue)) * 100) / 100
}
const isAnonymousVisit = (data = {}) => {
  if (Boolean(data.isPieceWash || data.is_piece_wash)) return false
  const model = String(data.model || data.car_model || '').trim()
  const color = String(data.color || data.car_color || '').trim()
  const plateNumber = String(data.plate || data.plate_number || '').trim()
  return Boolean(data.isAnonymous || data.is_anonymous) || (model === '1111' && color === '1111') || plateNumber === '1111'
}
const showAiPanel = computed(() => !props.vehicleInfo?.hideAiPanel && (!isMobileViewport.value || !isAiPanelCollapsed.value))
const availableTariffTypeOptions = computed(() => serviceTierOptionsForPlate(form.plateType))
const tariffBubblesStyle = computed(() => {
  const count = Math.max(1, availableTariffTypeOptions.value.length)
  const columns = Math.min(count, count <= 3 ? count : 3)
  return { gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }
})
const mobileTariffBubblesStyle = computed(() => {
  const count = Math.max(1, availableTariffTypeOptions.value.length)
  const columns = Math.min(count, 6)
  return { gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }
})

const syncMobileViewport = (event) => {
  isMobileViewport.value = Boolean(event?.matches ?? mobileViewportQuery.matches)
  if (!isMobileViewport.value) isAiPanelCollapsed.value = false
}

const toggleAiPanel = () => {
  isAiPanelCollapsed.value = !isAiPanelCollapsed.value
  if (!isAiPanelCollapsed.value && !cameraState.active && !form.isAnonymous && !form.isPieceWash && navigator.mediaDevices?.getUserMedia && canUseLiveCamera) {
    startCamera({ silent: false }).catch(() => {})
  }
}

const isMotorcyclePlate = () => form.plateType === 'motorcycle'
const hasCompleteManualPlate = () => (
  isMotorcyclePlate()
    ? form.plateMid.length === 3 && form.plateLetter.length === 5
    : form.plateLeft.length === 2 && form.plateMid.length === 3 && form.plateRight.length === 2 && form.plateLetter.length === 1
)

const hydrateForm = (data = {}) => {
  const plateType = String(data.plateType || data.plate_type || 'car').trim() || 'car'
  const resolvedParts = resolvePlateParts({
    raw: data.plate || data.plate_number || '',
    plate_left: data.plateLeft || data.plate_left || '',
    plate_letter: data.plateLetter || data.plate_letter || '',
    plate_mid: data.plateMid || data.plate_mid || '',
    plate_right: data.plateRight || data.plate_right || '',
    plate_type: plateType
  })
  form.id = data.id ?? null
  form.plateLeft = plateType === 'motorcycle' ? '' : String(resolvedParts.left || '').slice(0, 2)
  form.plateLetter = plateType === 'motorcycle'
    ? String(resolvedParts.letter || '').slice(0, 5)
    : normalizePlateLetter(String(resolvedParts.letter || '').slice(0, 1))
  form.plateMid = String(resolvedParts.mid || '').slice(0, 3)
  form.plateRight = plateType === 'motorcycle' ? '' : String(resolvedParts.right || '').slice(0, 2)
  form.model = String(data.model || data.car_model || '')
  form.color = String(data.color || data.car_color || '')
  form.driver = String(data.driver || data.driver_name || '')
  form.driverGender = ['male', 'female'].includes(String(data.driverGender || data.driver_gender || '').trim())
    ? String(data.driverGender || data.driver_gender).trim()
    : 'male'
  form.mobile = normalizeDigits(String(data.mobile || data.driver_phone || ''))
  form.customerScore = Math.max(0, Number(data.customerScore ?? data.customer_score ?? 0))
  form.customerLoyaltyVisitCount = Math.max(0, Number(data.customerLoyaltyVisitCount ?? data.customer_loyalty_visit_count ?? 0))
  form.customerLoyaltyDiscountPercent = Math.max(0, Number(data.customerLoyaltyDiscountPercent ?? data.customer_loyalty_discount_percent ?? 0))
  form.note = String(data.note || data.notes || '')
  form.tariffType = normalizeTariffType(data.tariffType || data.tariff_type, form.plateType)
  form.plateType = plateType
  form.isAnonymous = isAnonymousVisit(data)
  form.isPieceWash = Boolean(data.isPieceWash || data.is_piece_wash)
  detectedPlateSnapshot.value = {
    left: String(data.detectedPlateLeft || '').trim(),
    letter: normalizePlateLetter(String(data.detectedPlateLetter || '').trim()),
    mid: String(data.detectedPlateMid || '').trim(),
    right: String(data.detectedPlateRight || '').trim(),
    plateNumber: String(data.detectedPlate || '').trim(),
    plateType: String(data.detectedPlateType || form.plateType || 'car').trim() || 'car'
  }
  aiRecognitionSnapshot.value = {
    sessionId: String(data.aiSessionId || '').trim(),
    rawText: String(data.aiRawText || '').trim(),
    persianText: String(data.aiPersianText || '').trim(),
    convertedPlate: String(data.aiConvertedPlate || '').trim(),
    convertedPlateLeft: String(data.aiConvertedPlateLeft || '').trim(),
    convertedPlateLetter: String(data.aiConvertedPlateLetter || '').trim(),
    convertedPlateMid: String(data.aiConvertedPlateMid || '').trim(),
    convertedPlateRight: String(data.aiConvertedPlateRight || '').trim(),
    convertedPlateType: String(data.aiConvertedPlateType || form.plateType || 'car').trim() || 'car',
    imageBase64: String(data.aiImageBase64 || '').trim(),
    confidence: normalizeAiConfidence(data.aiConfidence),
    latencyMs: data.aiLatencyMs ?? null
  }
  syncLetterSuggestions(form.plateType === 'car' ? form.plateLetter : '')
}

const onlyDigits = (key) => {
  const normalized = key === 'mobile' ? normalizePhone(form[key]) : normalizeDigits(form[key]).replace(/\D/g, '')
  form[key] = normalized
}

const buildLetterSuggestions = (letter, rawOcrText = '') => {
  if (isMotorcyclePlate()) return []
  return getAmbiguousLetterSuggestions(letter, rawOcrText)
}

const syncLetterSuggestions = (letter, rawOcrText = '') => {
  letterSuggestions.value = buildLetterSuggestions(letter, rawOcrText)
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

const cameraErrorMessage = (error) => {
  if (!canUseLiveCamera) {
    return 'برای دوربین زنده روی گوشی باید سایت با HTTPS باز شود. فعلاً از گزینه دوربین گوشی / عکس استفاده کنید.'
  }
  const name = String(error?.name || '')
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return 'اجازه دسترسی به دوربین داده نشد. از تنظیمات مرورگر اجازه دوربین را برای این سایت فعال کنید، یا از گزینه دوربین گوشی / عکس استفاده کنید.'
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return 'دوربینی روی این دستگاه پیدا نشد. از گزینه دوربین گوشی / عکس استفاده کنید.'
  }
  if (name === 'NotReadableError' || name === 'TrackStartError') {
    return 'دوربین در دسترس نیست؛ شاید برنامه دیگری در حال استفاده از آن باشد.'
  }
  if (name === 'OverconstrainedError' || name === 'ConstraintNotSatisfiedError') {
    return 'تنظیمات دوربین پشتیبانی نمی‌شود. دوباره تلاش کنید یا از گزینه دوربین گوشی / عکس استفاده کنید.'
  }
  if (name === 'SecurityError') {
    return 'مرورگر به دلایل امنیتی دسترسی به دوربین را مسدود کرده است.'
  }
  return 'باز کردن دوربین ممکن نشد. دکمه «باز کردن دوربین» را بزنید یا از گزینه دوربین گوشی / عکس استفاده کنید.'
}

const requestCameraStream = async () => {
  const attempts = [
    {
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1280 },
        height: { ideal: 720 }
      },
      audio: false
    },
    { video: { facingMode: 'environment' }, audio: false },
    { video: true, audio: false }
  ]
  let lastError = null
  for (const constraints of attempts) {
    try {
      return await navigator.mediaDevices.getUserMedia(constraints)
    } catch (error) {
      lastError = error
      if (['NotAllowedError', 'PermissionDeniedError', 'SecurityError'].includes(error?.name)) {
        throw error
      }
    }
  }
  throw lastError || new Error('camera_unavailable')
}

const startCamera = async ({ silent = false } = {}) => {
  if (cameraState.loading) return
  if (!silent) setCameraMessage('')
  try {
    if (!navigator.mediaDevices?.getUserMedia) {
      if (!silent) {
        setCameraMessage('دسترسی مستقیم به دوربین در این مرورگر فعال نیست. از گزینه دوربین گوشی / عکس استفاده کنید.', true)
      }
      return
    }
    if (!canUseLiveCamera) {
      if (!silent) {
        setCameraMessage('برای دوربین زنده روی گوشی باید سایت با HTTPS باز شود. فعلاً از گزینه دوربین گوشی / عکس استفاده کنید.', true)
      }
      return
    }
    stopCamera()
    const stream = await requestCameraStream()
    cameraStream.value = stream
    if (cameraVideoRef.value) {
      cameraVideoRef.value.srcObject = stream
      cameraVideoRef.value.setAttribute('playsinline', 'true')
      cameraVideoRef.value.muted = true
      await cameraVideoRef.value.play()
    }
    cameraState.active = true
    setCameraMessage('دوربین آماده است. هر وقت روی تصویر کلیک کنید همان لحظه پلاک خوانده می‌شود.')
  } catch (error) {
    stopCamera()
    if (!silent) setCameraMessage(cameraErrorMessage(error), true)
  }
}

const dataUrlFromCanvas = (source, sourceWidth, sourceHeight) => {
  const canvas = cameraCanvasRef.value || document.createElement('canvas')
  const maxWidth = 960
  const scale = Math.min(1, maxWidth / Math.max(1, sourceWidth))
  canvas.width = Math.max(1, Math.round(sourceWidth * scale))
  canvas.height = Math.max(1, Math.round(sourceHeight * scale))
  const context = canvas.getContext('2d')
  context.drawImage(source, 0, 0, canvas.width, canvas.height)
  return canvas.toDataURL('image/jpeg', 0.78)
}

const readFileAsDataUrl = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = () => resolve(String(reader.result || ''))
  reader.onerror = () => reject(new Error('file_read_failed'))
  reader.readAsDataURL(file)
})

const processCameraFile = async (event) => {
  const file = event.target?.files?.[0]
  event.target.value = ''
  if (!file || cameraState.loading) return
  const image = new Image()
  const objectUrl = URL.createObjectURL(file)
  try {
    await new Promise((resolve, reject) => {
      image.onload = resolve
      image.onerror = reject
      image.src = objectUrl
    })
    const imageDataUrl = dataUrlFromCanvas(image, image.naturalWidth, image.naturalHeight)
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
  const video = cameraVideoRef.value
  const imageDataUrl = dataUrlFromCanvas(video, video.videoWidth, video.videoHeight)
  await recognizePlateImage(imageDataUrl)
}

const applyRecognizedPlate = (data) => {
  const plateType = String(data?.plate_type || form.plateType || 'car').trim() || 'car'
  const left = normalizeDigits(data?.plate_left || '')
  const mid = normalizeDigits(data?.plate_mid || '')
  const right = normalizeDigits(data?.plate_right || '')
  const letter = plateType === 'motorcycle'
    ? normalizeDigits(data?.plate_letter || '').replace(/\D/g, '').slice(0, 5)
    : normalizePlateLetter(data?.plate_letter || '')
  const suggestions = plateType === 'motorcycle'
    ? []
    : buildLetterSuggestions(letter, data?.text || data?.raw_text || '')
  if (plateType === 'motorcycle') {
    if (mid.length !== 3 || letter.length !== 5) return false
  } else if (left.length !== 2 || mid.length !== 3 || right.length !== 2 || !letter) {
    return false
  }
  form.isAnonymous = false
  form.isPieceWash = false
  form.plateType = plateType
  form.plateLeft = plateType === 'motorcycle' ? '' : left
  form.plateLetter = letter
  form.plateMid = mid
  form.plateRight = plateType === 'motorcycle' ? '' : right
  detectedPlateSnapshot.value = {
    left: plateType === 'motorcycle' ? '' : left,
    letter,
    mid,
    right: plateType === 'motorcycle' ? '' : right,
    plateNumber: buildPlateNumber({ left, letter, mid, right, plateType }),
    plateType
  }
  letterSuggestions.value = suggestions
  return true
}

const tryResolveLetterFromHistory = async () => {
  if (isMotorcyclePlate()) return false
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
  applyPlateLookupData(match.result.value.data)
  syncLetterSuggestions(match.letter)
  return true
}

const recognizePlateImage = async (imageDataUrl) => {
  cameraState.loading = true
  setCameraMessage('در حال ارسال همین تصویر و تشخیص پلاک...')
  try {
    const { data } = await api.post('/vehicles/plate-recognition/', {
      session_id: aiSessionId,
      image_base64: imageDataUrl,
      force_process: false
    }, { meta: { trackLoading: false } })
    const recognizedConfidence = normalizeAiConfidence(data?.confidence)
    cameraState.lastConfidence = recognizedConfidence ?? 0
    cameraState.lastLatency = Number(data?.latency_ms || 0)
    const recognizedPlateType = String(data?.plate_type || form.plateType || 'car').trim() || 'car'
    const recognizedPlateMid = recognizedPlateType === 'motorcycle'
      ? normalizeDigits(data?.plate_mid || '').replace(/\D/g, '').slice(0, 3)
      : String(data?.plate_mid || '').trim()
    const recognizedPlateLetter = recognizedPlateType === 'motorcycle'
      ? normalizeDigits(data?.plate_letter || '').replace(/\D/g, '').slice(0, 5)
      : normalizePlateLetter(data?.plate_letter || '')
    aiRecognitionSnapshot.value = {
      sessionId: aiSessionId,
      rawText: String(data?.text || '').trim(),
      persianText: String(data?.persian_text || '').trim(),
      convertedPlate: String(data?.plate_number || '').trim(),
      convertedPlateLeft: recognizedPlateType === 'motorcycle' ? '' : String(data?.plate_left || '').trim(),
      convertedPlateLetter: recognizedPlateLetter,
      convertedPlateMid: recognizedPlateMid,
      convertedPlateRight: recognizedPlateType === 'motorcycle' ? '' : String(data?.plate_right || '').trim(),
      convertedPlateType: recognizedPlateType,
      imageBase64: imageDataUrl,
      confidence: recognizedConfidence,
      latencyMs: data?.latency_ms ?? null
    }
    if (data?.mode === 'stub') {
      setCameraMessage(data?.detail || 'مدل واقعی تشخیص پلاک هنوز روی سرویس AI نصب نشده است.', true)
      return
    }
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
    if (isMobileViewport.value) isAiPanelCollapsed.value = true
  } catch (error) {
    const detail = error?.response?.data?.detail || 'ارتباط با سرویس تشخیص پلاک برقرار نشد.'
    setCameraMessage(detail, true)
  } finally {
    cameraState.loading = false
  }
}

const plate = computed(() => {
  if (form.isAnonymous) return ''
  return buildPlateNumber({
    left: form.plateLeft.trim(),
    letter: form.plateLetter.trim(),
    mid: form.plateMid.trim(),
    right: form.plateRight.trim(),
    plateType: form.plateType
  })
})

const isPhoneValid = computed(() => isValidIranMobile(form.mobile))
const canSubmit = computed(() => {
  if (form.isPieceWash) return isPhoneValid.value
  return isPhoneValid.value && availableTariffTypeOptions.value.some((option) => option.value === form.tariffType)
})

const payload = () => ({
  id: form.id,
  plate: form.isPieceWash ? '' : plate.value,
  plateLeft: form.isAnonymous || form.isPieceWash || isMotorcyclePlate() ? '' : form.plateLeft.trim(),
  plateLetter: form.isAnonymous || form.isPieceWash ? '' : form.plateLetter.trim(),
  plateMid: form.isAnonymous || form.isPieceWash ? '' : form.plateMid.trim(),
  plateRight: form.isAnonymous || form.isPieceWash || isMotorcyclePlate() ? '' : form.plateRight.trim(),
  model: form.isPieceWash ? 'قطعه‌شویی' : (form.isAnonymous ? '1111' : form.model.trim()),
  color: form.isPieceWash ? '-' : (form.isAnonymous ? '1111' : form.color.trim()),
  driver: form.driver.trim(),
  driverGender: form.driverGender,
  mobile: form.mobile.trim(),
  customerScore: form.customerScore,
  customerLoyaltyVisitCount: form.customerLoyaltyVisitCount,
  customerLoyaltyDiscountPercent: form.customerLoyaltyDiscountPercent,
  note: form.isPieceWash ? '' : form.note.trim(),
  tariffType: form.tariffType,
  plateType: form.plateType,
  isAnonymous: form.isAnonymous,
  isPieceWash: form.isPieceWash,
  detectedPlate: detectedPlate.value,
  detectedPlateLeft: detectedPlateParts.value.left,
  detectedPlateLetter: detectedPlateParts.value.letter,
  detectedPlateMid: detectedPlateParts.value.mid,
  detectedPlateRight: detectedPlateParts.value.right,
  detectedPlateType: detectedPlateType.value,
  aiSessionId: form.isAnonymous || form.isPieceWash ? '' : aiRecognitionSnapshot.value.sessionId,
  aiRawText: form.isAnonymous || form.isPieceWash ? '' : aiRecognitionSnapshot.value.rawText,
  aiPersianText: form.isAnonymous || form.isPieceWash ? '' : aiRecognitionSnapshot.value.persianText,
  aiConvertedPlate: form.isAnonymous || form.isPieceWash ? '' : aiRecognitionSnapshot.value.convertedPlate,
  aiConvertedPlateLeft: form.isAnonymous || form.isPieceWash ? '' : aiRecognitionSnapshot.value.convertedPlateLeft,
  aiConvertedPlateLetter: form.isAnonymous || form.isPieceWash ? '' : aiRecognitionSnapshot.value.convertedPlateLetter,
  aiConvertedPlateMid: form.isAnonymous || form.isPieceWash ? '' : aiRecognitionSnapshot.value.convertedPlateMid,
  aiConvertedPlateRight: form.isAnonymous || form.isPieceWash ? '' : aiRecognitionSnapshot.value.convertedPlateRight,
  aiConvertedPlateType: form.isAnonymous || form.isPieceWash ? '' : aiRecognitionSnapshot.value.convertedPlateType,
  aiImageBase64: form.isAnonymous || form.isPieceWash ? '' : aiRecognitionSnapshot.value.imageBase64,
  aiConfidence: form.isAnonymous || form.isPieceWash ? null : aiRecognitionSnapshot.value.confidence,
  aiLatencyMs: form.isAnonymous || form.isPieceWash ? null : aiRecognitionSnapshot.value.latencyMs
})

const onContinue = () => {
  if (!canSubmit.value || props.submitting || actionLocked.value) return
  actionLocked.value = true
  emit('continue', payload())
}

const onRefer = () => {
  if (props.submitting || actionLocked.value) return
  actionLocked.value = true
  emit('refer', payload())
}

watch(() => props.submitting, (value) => {
  if (!value) actionLocked.value = false
})

const detectedPlateParts = computed(() => resolvePlateParts({
  raw: detectedPlateSnapshot.value.plateNumber,
  plate_left: detectedPlateSnapshot.value.left,
  plate_letter: detectedPlateSnapshot.value.letter,
  plate_mid: detectedPlateSnapshot.value.mid,
  plate_right: detectedPlateSnapshot.value.right,
  plate_type: detectedPlateSnapshot.value.plateType
}))
const detectedPlateType = computed(() => detectedPlateSnapshot.value.plateType || form.plateType || 'car')
const detectedPlate = computed(() => (
  buildPlateNumber({
    ...detectedPlateParts.value,
    plateType: detectedPlateType.value
  }) || (detectedPlateType.value === 'motorcycle' ? '--- -----' : '-- - --- --')
))
const cameraHintText = computed(() => {
  if (!cameraState.active) return 'ابتدا دوربین را باز کنید'
  if (cameraState.loading) return 'در حال تشخیص پلاک...'
  return 'برای تشخیص پلاک روی تصویر کلیک کنید'
})
const detectedModelColor = computed(() => {
  const text = `${form.model.trim()} ${form.color.trim()}`.trim()
  return text || '---'
})
const letterSuggestionOptions = computed(() => letterSuggestions.value)

watch(() => props.vehicleInfo, (value) => {
  isHydratingForm = true
  hydrateForm(value || {})
  requestAnimationFrame(() => {
    isHydratingForm = false
  })
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

watch(() => form.plateType, (value) => {
  if (value === 'motorcycle') {
    form.plateLeft = ''
    form.plateRight = ''
    form.plateLetter = normalizeDigits(form.plateLetter).replace(/\D/g, '').slice(0, 5)
    letterSuggestions.value = []
  } else {
    form.plateLetter = normalizePlateLetter(form.plateLetter)
    syncLetterSuggestions(form.plateLetter)
  }
  if (!availableTariffTypeOptions.value.some((option) => option.value === form.tariffType)) {
    form.tariffType = defaultTariffType
  }
  detectedPlateSnapshot.value = {
    ...detectedPlateSnapshot.value,
    plateType: detectedPlateSnapshot.value.plateNumber ? detectedPlateSnapshot.value.plateType : value
  }
})

watch(() => form.plateLetter, (value) => {
  if (isHydratingForm || form.plateType !== 'car') return
  syncLetterSuggestions(value)
})

let lookupTimer = null
let lookupToken = 0
const applyPlateLookupData = (data = {}) => {
  form.model = String(data.car_model || data.model || '').trim()
  form.color = String(data.car_color || data.color || '').trim()
  form.driver = String(data.driver_name || data.driver || '').trim()
  form.driverGender = ['male', 'female'].includes(String(data.driver_gender || data.driverGender || '').trim())
    ? String(data.driver_gender || data.driverGender).trim()
    : form.driverGender
  form.mobile = normalizeDigits(String(data.driver_phone || data.mobile || ''))
  form.customerScore = Math.max(0, Number(data.customer_score ?? data.customerScore ?? 0))
  form.customerLoyaltyVisitCount = Math.max(0, Number(data.customer_loyalty_visit_count ?? data.customerLoyaltyVisitCount ?? 0))
  form.customerLoyaltyDiscountPercent = Math.max(0, Number(data.customer_loyalty_discount_percent ?? data.customerLoyaltyDiscountPercent ?? 0))
  form.plateType = String(data.plate_type || form.plateType || 'car').trim() || 'car'
  if (data.tariff_type || data.tariffType) {
    form.tariffType = normalizeTariffType(data.tariff_type || data.tariffType, form.plateType)
  }
}

watch(
  () => [form.plateLeft, form.plateLetter, form.plateMid, form.plateRight, form.plateType, form.isAnonymous, form.isPieceWash],
  async () => {
    if (lookupTimer) clearTimeout(lookupTimer)
    if (isHydratingForm || form.isAnonymous || form.isPieceWash) return
    const hasFullPlate = hasCompleteManualPlate()
    if (!hasFullPlate) return
    lookupTimer = setTimeout(async () => {
      const token = ++lookupToken
      const lookupPlateNumber = plate.value
      try {
        const { data } = await api.get('/vehicles/plate-lookup/', {
          params: {
            plate_number: lookupPlateNumber,
            plate_left: form.plateLeft.trim(),
            plate_letter: form.plateLetter.trim(),
            plate_mid: form.plateMid.trim(),
            plate_right: form.plateRight.trim(),
            plate_type: form.plateType
          }
        })
        if (token !== lookupToken) return
        if (data?.found) {
          applyPlateLookupData(data)
          return
        }
        // First-time plate: show visit=1 and score=0.5 from API preview
        form.customerScore = Math.max(0, Number(data?.customer_score ?? 0.5))
        form.customerLoyaltyVisitCount = Math.max(1, Number(data?.customer_loyalty_visit_count ?? 1))
        form.customerLoyaltyDiscountPercent = Math.max(
          0,
          Number(data?.customer_loyalty_discount_percent ?? 0)
        )
      } catch (_error) {
      }
    }, 220)
  }
)

onMounted(async () => {
  mobileViewportQuery.addEventListener('change', syncMobileViewport)
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
  // Auto-open only silently: many mobile browsers need a tap before they show the permission prompt.
  await startCamera({ silent: true })
  if (!cameraState.active) {
    setCameraMessage('برای فعال شدن دوربین، دکمه «باز کردن دوربین» را بزنید.')
  }
})

onBeforeUnmount(() => {
  mobileViewportQuery.removeEventListener('change', syncMobileViewport)
  if (lookupTimer) clearTimeout(lookupTimer)
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
  background: #fff;
  box-shadow: 0 12px 32px -28px rgba(15, 23, 42, 0.35);
  contain: content;
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
  display: none;
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
  display: none;
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
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

.result-card :deep(.plate-badge) {
  margin-top: 4px;
}

.ai-toggle-row {
  display: none;
}

.ai-toggle-btn {
  min-height: 34px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 999px;
  background: linear-gradient(180deg, #ffffff, #eff6ff);
  color: #0f4c81;
  padding: 0 12px;
  font: inherit;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
}

.form-panel {
  gap: 14px;
}

.tariff-type-row {
  display: grid;
  gap: 9px;
  padding: 12px;
  border: 1px solid #d8e6f7;
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(244, 248, 255, 0.86));
}

.tariff-type-row > span {
  color: #334155;
  font-size: 12px;
  font-weight: 900;
}

.tariff-bubbles {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.tariff-bubble {
  height: 38px;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 999px;
  background: #ffffff;
  color: #334155;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 900;
  transition: background .18s ease, color .18s ease, border-color .18s ease, transform .18s ease;
}

.tariff-bubble.active {
  border-color: #0058be;
  background: linear-gradient(135deg, #0058be, #2170e4);
  color: #ffffff;
  box-shadow: 0 12px 24px -18px rgba(0, 88, 190, 0.72);
}

.tariff-bubble:not(.active):hover {
  border-color: #93c5fd;
  background: #eff6ff;
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
  border: 0;
  border-radius: 18px;
  padding: 0 14px;
  font: inherit;
  background: rgba(244, 248, 255, 0.78);
  box-shadow: none;
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

.plate-type-select {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.plate-type-select select {
  height: 36px;
  border: 1px solid #c8d7ea;
  border-radius: 12px;
  background: #fff;
  padding: 0 10px;
  font: inherit;
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
  background: rgba(239, 246, 255, 0.96);
}

.gender-bubbles {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 5px;
  border: 1px solid #dbe7f5;
  border-radius: 18px;
  background: #f8fbff;
}

.gender-bubble {
  height: 38px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  color: #475569;
  font: inherit;
  font-weight: 900;
  cursor: pointer;
}

.gender-bubble.active {
  background: linear-gradient(135deg, #1e5fae, #3b82c4);
  color: #fff;
  box-shadow: 0 12px 22px -18px rgba(30, 95, 174, .75);
}

.piece-wash-toggle-row {
  display: flex;
  justify-content: flex-end;
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
  border-radius: 12px;
  padding: 10px;
  overflow: hidden;
  direction: ltr;
}

.manual-plate-main {
  min-width: 0;
  flex: 1;
  background: #6f59ef18;
}

.manual-plate-car .manual-plate-main {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  border-radius: 7px 0 0 7px;
  padding: 6px 18px;
}

.manual-plate-motorcycle .manual-plate-main {
  display: grid;
  grid-template-rows: auto auto;
  gap: 6px;
  padding: 8px 10px 9px;
  border-radius: 10px 0 0 10px;
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.08), transparent 34%),
    linear-gradient(180deg, rgba(255,255,255,0.98), rgba(241,245,249,0.95));
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-right: 0;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.72);
}

.manual-plate-blue {
  min-width: 52px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #2563eb;
  color: #fff;
  border-radius: 0 7px 7px 0;
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  padding-top: 12px;
  padding-bottom: 8px;
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
  background: transparent !important;
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
  background: transparent !important;
  font-size: 28px;
  font-weight: 950;
  letter-spacing: 0.18em;
  padding: 0 6px;
}

.motor-row-top,
.motor-row-bottom {
  display: grid;
  align-items: center;
  gap: 8px;
}

.motor-row-top {
  grid-template-columns: 1fr;
  justify-items: center;
}

.motor-row-bottom {
  grid-template-columns: 1fr;
  justify-items: center;
}

.letter-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.anonymous-plate-note,
.field-error {
  color: #b91c1c;
  font-size: 11px;
  font-weight: 700;
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
  .ai-toggle-row {
    display: flex;
    justify-content: flex-start;
  }
  .panel-head h3 {
    font-size: 17px;
  }
  .panel-head p {
    font-size: 11px;
    margin-top: 5px;
  }
  .ai-result-grid { grid-template-columns: 1fr; }
  .camera-actions,
  .grid-2,
  .tariff-bubbles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .tariff-type-row {
    padding: 10px;
    border-radius: 16px;
  }
  .tariff-bubbles {
    gap: 6px;
  }
  .tariff-bubble {
    aspect-ratio: 1 / 1;
    height: auto;
    min-height: 34px;
    font-size: 11px;
    padding: 0;
  }
  .mobile-tariff-row .tariff-bubbles {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .mobile-tariff-row .tariff-bubble {
    border-radius: 999px;
    font-size: 13px;
  }
  .camera-action {
    min-height: 40px;
    padding: 8px;
    font-size: 11px;
    line-height: 1.6;
  }
  .plate-tools,
  .piece-wash-toggle-row {
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
  .plate-row {
    gap: 4px;
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
  .motor-row-top {
    grid-template-columns: 1fr;
  }
  .motor-row-bottom {
    grid-template-columns: 1fr;
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
  .result-card :deep(.plate-badge) {
    padding: 2px;
    border-radius: 8px;
  }
  .result-card :deep(.plate-white-wrap) {
    gap: 3px;
    padding: 2px 4px;
  }
  .result-card :deep(.plate-two),
  .result-card :deep(.plate-three) {
    height: 14px;
    font-size: 9px;
    padding-top: 2px;
    padding-bottom: 1px;
  }
  .result-card :deep(.plate-letter) {
    min-width: 8px;
    font-size: 9px;
  }
  .result-card :deep(.plate-blue) {
    min-width: 18px;
    font-size: 8px;
    padding-top: 2px;
    padding-bottom: 1px;
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

  .motor-row-top {
    grid-template-columns: 1fr;
  }
  .motor-row-bottom {
    grid-template-columns: 1fr;
  }
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
  .field input {
    padding-inline: 10px;
  }
  .tariff-bubble {
    height: 32px;
    font-size: 10px;
  }
  .camera-actions,
  .grid-2,
  .tariff-bubbles {
    gap: 6px;
  }
  .camera-action {
    min-height: 38px;
    font-size: 10px;
    padding-inline: 6px;
  }
}
</style>
