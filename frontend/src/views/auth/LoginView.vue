<template>
  <div class="login-page" dir="rtl">
    <video class="login-video" autoplay muted loop playsinline>
      <source src="/Untitled Project.mp4" type="video/mp4" />
    </video>
    <div class="login-video-veil"></div>

    <header class="topbar">
      <div class="brand">
        <span class="brand-badge">CW</span>
        <div class="brand-copy">
          <span class="brand-title">CarnoWah</span>
          <span class="brand-subtitle">ورود مدیران، اپراتورها و ثبت کارواش جدید</span>
        </div>
      </div>
    </header>

    <main class="login-main">
      <section class="login-card">
        <div class="login-head">
          <p class="panel-kicker">ورود به سامانه</p>
          <h2>حساب کاربری خود را باز کنید</h2>
          <span>با نام کاربری یا شماره موبایل مدیر/کاربر وارد شوید.</span>
        </div>

        <form class="login-form" @submit.prevent="onSubmit">
          <label class="field">
            <span>نام کاربری یا شماره همراه</span>
            <input v-model.trim="form.username" type="text" placeholder="مثلا manager01 یا 0912..." autocomplete="username" required />
          </label>

          <label class="field">
            <div class="field-row">
              <span>رمز عبور</span>
              <button class="field-toggle" type="button" @click="showPassword = !showPassword">
                {{ showPassword ? 'پنهان' : 'نمایش' }}
              </button>
            </div>
            <input v-model="form.password" :type="showPassword ? 'text' : 'password'" placeholder="رمز عبور" autocomplete="current-password" required />
          </label>

          <button class="submit-btn" type="submit" :disabled="isLoading">
            {{ isLoading ? 'در حال ورود...' : 'ورود به سامانه' }}
          </button>
          <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
        </form>

        <div class="login-foot">
          <p>کارواش جدید دارید؟</p>
          <button class="text-btn" type="button" @click="openRegisterModal">باز کردن فرم ثبت نام</button>
        </div>
      </section>
    </main>

    <div v-if="registerModal.open" class="register-modal-overlay" @click.self="closeRegisterModal">
      <section class="register-modal">
        <header class="register-modal-head">
          <div>
            <p class="panel-kicker">ثبت نام کارواش</p>
            <h3>اطلاعات کارواش و مدیر را کامل کنید</h3>
            <span>پس از ثبت، کارواش ساخته می‌شود و اطلاعات ورود مدیر نمایش داده شده و با پیامک هم ارسال می‌شود.</span>
          </div>
          <button class="modal-close" type="button" @click="closeRegisterModal">×</button>
        </header>

        <form class="register-form" @submit.prevent="submitRegister">
          <section class="register-section">
            <div class="register-section-head">
              <strong>جزئیات کارواش</strong>
              <span>اطلاعات پایه شعبه‌ای که باید در سامانه ساخته شود</span>
            </div>
            <div class="register-grid">
              <label class="field field-soft full">
                <span>نام کارواش</span>
                <input v-model.trim="registerForm.carwash_name" type="text" placeholder="مثلا کارواش امیران" required />
              </label>
              <label class="field field-soft full">
                <span>آدرس کامل کارواش</span>
                <textarea v-model.trim="registerForm.carwash_address" rows="3" placeholder="شهر، خیابان، پلاک یا توضیح موقعیت" />
              </label>
            </div>
          </section>

          <section class="register-section">
            <div class="register-section-head">
              <strong>جزئیات مدیر کارواش</strong>
              <span>این حساب به عنوان مدیر اصلی شعبه ساخته می‌شود</span>
            </div>
            <div class="register-grid">
              <label class="field field-soft">
                <span>نام مدیر</span>
                <input v-model.trim="registerForm.manager_first_name" type="text" placeholder="مثلا علی" required />
              </label>
              <label class="field field-soft">
                <span>نام خانوادگی مدیر</span>
                <input v-model.trim="registerForm.manager_last_name" type="text" placeholder="مثلا رضایی" required />
              </label>
              <label class="field field-soft">
                <span>نام کاربری</span>
                <input v-model.trim="registerForm.manager_username" type="text" placeholder="مثلا amiran-manager" required />
              </label>
              <label class="field field-soft">
                <span>شماره موبایل مدیر</span>
                <input v-model.trim="registerForm.manager_phone" type="text" inputmode="numeric" placeholder="0912xxxxxxx" required />
              </label>
              <label class="field field-soft">
                <span>رمز عبور اولیه</span>
                <input v-model="registerForm.manager_password" :type="showRegisterPassword ? 'text' : 'password'" placeholder="حداقل 6 کاراکتر" required />
              </label>
              <div class="register-password-box">
                <button class="field-toggle align-start" type="button" @click="showRegisterPassword = !showRegisterPassword">
                  {{ showRegisterPassword ? 'پنهان کردن رمز' : 'نمایش رمز' }}
                </button>
                <p>همین نام کاربری و رمز داخل پیامک هم برای مدیر ارسال می‌شود.</p>
              </div>
            </div>
          </section>

          <p v-if="registerError" class="error-text register-error">{{ registerError }}</p>

          <section v-if="registerSuccess.credentials.username" class="register-result">
            <div class="register-result-head">
              <strong>ثبت نام انجام شد</strong>
              <span>{{ registerSuccess.tenantName }}</span>
            </div>
            <div class="credential-grid">
              <article>
                <small>نام کاربری مدیر</small>
                <strong>{{ registerSuccess.credentials.username }}</strong>
              </article>
              <article>
                <small>رمز عبور اولیه</small>
                <strong>{{ registerSuccess.credentials.password }}</strong>
              </article>
            </div>
            <p class="sms-note" :class="{ danger: registerSuccess.smsAttempted && !registerSuccess.smsOk }">
              {{ registerSuccess.smsMessage }}
            </p>
          </section>

          <footer class="register-actions">
            <button class="ghost-btn" type="button" @click="closeRegisterModal">بستن</button>
            <button class="submit-btn register-submit" type="submit" :disabled="registerLoading">
              {{ registerLoading ? 'در حال ثبت...' : 'ثبت کارواش و مدیر' }}
            </button>
          </footer>
        </form>
      </section>
    </div>

    <footer class="footer">Powered by CarWash Platform © 2026</footer>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api, { ensureCsrfToken } from '../../services/api'
import { useAuthStore } from '../../store/auth.store'
import { defaultRouteByRole } from '../../config/navigation'
import { resolveApiErrorMessage } from '../../utils/apiError'

const showPassword = ref(false)
const showRegisterPassword = ref(false)
const isLoading = ref(false)
const registerLoading = ref(false)
const errorMessage = ref('')
const registerError = ref('')
const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  carwash_name: '',
  carwash_address: '',
  manager_first_name: '',
  manager_last_name: '',
  manager_username: '',
  manager_phone: '',
  manager_password: ''
})

const registerModal = reactive({ open: false })
const registerSuccess = reactive({
  tenantName: '',
  credentials: {
    username: '',
    password: ''
  },
  smsAttempted: false,
  smsOk: false,
  smsMessage: ''
})

const resetRegisterState = () => {
  registerError.value = ''
  registerSuccess.tenantName = ''
  registerSuccess.credentials.username = ''
  registerSuccess.credentials.password = ''
  registerSuccess.smsAttempted = false
  registerSuccess.smsOk = false
  registerSuccess.smsMessage = ''
}

const openRegisterModal = () => {
  resetRegisterState()
  registerModal.open = true
}

const closeRegisterModal = () => {
  registerModal.open = false
}

const onSubmit = async () => {
  if (isLoading.value) return
  errorMessage.value = ''

  if (!form.username || !form.password) {
    errorMessage.value = 'نام کاربری و رمز عبور را وارد کنید.'
    return
  }

  isLoading.value = true
  try {
    await ensureCsrfToken()
    const { data } = await api.post('/auth/login/', {
      username: form.username,
      password: form.password
    })
    authStore.setUser(data)
    await router.push(authStore.isHq ? '/hq' : (defaultRouteByRole[authStore.role] || '/'))
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'ورود ناموفق بود. لطفا اطلاعات را بررسی کنید.')
  } finally {
    isLoading.value = false
  }
}

const submitRegister = async () => {
  if (registerLoading.value) return
  resetRegisterState()

  registerLoading.value = true
  try {
    await ensureCsrfToken()
    const { data } = await api.post('/auth/tenants/register/', {
      carwash_name: registerForm.carwash_name,
      carwash_address: registerForm.carwash_address,
      manager_first_name: registerForm.manager_first_name,
      manager_last_name: registerForm.manager_last_name,
      manager_username: registerForm.manager_username,
      manager_phone: registerForm.manager_phone,
      manager_password: registerForm.manager_password
    })

    registerSuccess.tenantName = data?.tenant?.name || registerForm.carwash_name
    registerSuccess.credentials.username = data?.credentials?.username || registerForm.manager_username
    registerSuccess.credentials.password = data?.credentials?.password || registerForm.manager_password
    registerSuccess.smsAttempted = Boolean(data?.sms?.attempted)
    registerSuccess.smsOk = Boolean(data?.sms?.ok)
    registerSuccess.smsMessage = data?.sms?.ok
      ? 'نام کاربری و رمز عبور برای مدیر پیامک شد.'
      : (data?.sms?.message || 'ثبت انجام شد اما پیامک ارسال نشد.')

    form.username = registerSuccess.credentials.username
    form.password = registerSuccess.credentials.password
  } catch (error) {
    registerError.value = resolveApiErrorMessage(error, 'ثبت نام ناموفق بود.')
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped>
@font-face {
  font-family: 'Vazirmatn';
  src: url('/font/webfonts/Vazirmatn-Regular.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'Vazirmatn';
  src: url('/font/webfonts/Vazirmatn-SemiBold.woff2') format('woff2');
  font-weight: 600;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'Vazirmatn';
  src: url('/font/webfonts/Vazirmatn-Bold.woff2') format('woff2');
  font-weight: 700;
  font-style: normal;
  font-display: swap;
}

.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  background: #f5f2fb;
  color: #0f172a;
  font-family: Vazirmatn, sans-serif;
}

.login-video,
.login-video-veil {
  position: absolute;
  inset: 0;
}

.login-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(1.05) blur(1px);
  transform: scale(1.04);
}

.login-video-veil {
  background:
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.72), transparent 32%),
    radial-gradient(circle at bottom right, rgba(216, 180, 254, 0.28), transparent 34%),
    linear-gradient(180deg, rgba(252, 249, 255, 0.80) 0%, rgba(243, 236, 252, 0.72) 52%, rgba(247, 243, 252, 0.84) 100%);
  backdrop-filter: blur(6px);
}

.topbar {
  height: 76px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  position: relative;
  z-index: 2;
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-badge {
  width: 48px;
  height: 48px;
  border-radius: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f5cc0 0%, #1fb89b 100%);
  color: #fff;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.brand-copy {
  display: grid;
  gap: 4px;
}

.brand-title {
  font-size: 15px;
  font-weight: 800;
}

.brand-subtitle {
  color: #5b6b80;
  font-size: 12px;
}

.text-btn,
.field-toggle,
.ghost-btn,
.modal-close {
  border: 0;
  background: transparent;
  font: inherit;
  cursor: pointer;
}

.login-main {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px 32px 8px;
  z-index: 2;
}

.login-card,
.register-modal {
  position: relative;
  z-index: 2;
}

.panel-kicker {
  margin: 0 0 10px;
  color: #7c3aed;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.login-card {
  width: min(460px, 100%);
  border-radius: 32px;
  padding: 28px;
  border: 1px solid rgba(255, 255, 255, 0.56);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.32) 0%, rgba(255, 255, 255, 0.22) 100%);
  backdrop-filter: blur(22px);
  box-shadow: 0 18px 60px rgba(114, 78, 167, 0.12);
}

.login-head {
  display: grid;
  gap: 8px;
  margin-bottom: 22px;
}

.login-head h2,
.register-modal-head h3 {
  margin: 0;
  font-size: 28px;
}

.login-head span,
.register-modal-head span,
.register-section-head span,
.register-password-box p,
.sms-note {
  color: #5b5a74;
  line-height: 1.9;
  font-size: 13px;
}

.login-form,
.register-form,
.register-section,
.register-grid {
  display: grid;
  gap: 16px;
}

.field {
  display: grid;
  gap: 8px;
}

.field span {
  color: #314155;
  font-size: 13px;
  font-weight: 700;
}

.field-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.field-toggle {
  color: #7c3aed;
  font-size: 12px;
  font-weight: 700;
}

.align-start {
  justify-self: start;
}

.field input,
.field textarea {
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.42);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.58);
  padding: 0 16px;
  font: inherit;
  color: #0f172a;
  transition: border-color .2s ease, background .2s ease, box-shadow .2s ease;
  backdrop-filter: blur(12px);
}

.field input {
  height: 54px;
}

.field textarea {
  min-height: 108px;
  padding-top: 14px;
  resize: vertical;
}

.field input:focus,
.field textarea:focus {
  outline: none;
  border-color: rgba(168, 85, 247, 0.34);
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 0 0 4px rgba(216, 180, 254, 0.18);
}

.submit-btn,
.ghost-btn {
  min-height: 56px;
  border-radius: 18px;
  font-weight: 800;
  font-family: inherit;
  border: none;
}

.submit-btn {
  color: #fff;
  background: #b78cff;
}

.submit-btn:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.error-text {
  margin: 0;
  color: #b42318;
  font-size: 13px;
}

.login-foot {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid rgba(148, 163, 184, 0.16);
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.login-foot p {
  margin: 0;
  color: #5f7087;
}

.text-btn {
  color: #9d6cff;
  font-weight: 800;
}

.register-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(237, 229, 246, 0.44);
  backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 100;
}

.register-modal {
  width: min(980px, 100%);
  max-height: calc(100dvh - 40px);
  border-radius: 32px;
  overflow: auto;
  padding: 22px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.74) 0%, rgba(250, 246, 255, 0.82) 100%);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.56);
  box-shadow: 0 24px 80px rgba(125, 90, 173, 0.12);
}

.register-modal-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.modal-close {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.62);
  color: #0f172a;
  font-size: 28px;
  line-height: 1;
  backdrop-filter: blur(12px);
}

.register-section {
  padding: 18px;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.58);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.44), rgba(255, 255, 255, 0.30));
  backdrop-filter: blur(16px);
}

.register-section-head {
  display: grid;
  gap: 6px;
  margin-bottom: 14px;
}

.register-section-head strong,
.register-result-head strong {
  font-size: 17px;
  color: #0f172a;
}

.register-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field-soft input,
.field-soft textarea {
  background: rgba(255, 255, 255, 0.72);
}

.full {
  grid-column: 1 / -1;
}

.register-password-box {
  display: grid;
  align-content: start;
  gap: 10px;
  border-radius: 22px;
  padding: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.48), rgba(245, 236, 255, 0.56));
  border: 1px solid rgba(255, 255, 255, 0.48);
}

.register-password-box p,
.register-result-head span,
.credential-grid small {
  margin: 0;
}

.register-result {
  border-radius: 24px;
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.56);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.46), rgba(239, 253, 245, 0.40));
  backdrop-filter: blur(14px);
}

.register-result-head {
  display: grid;
  gap: 5px;
  margin-bottom: 14px;
}

.credential-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.credential-grid article {
  border-radius: 20px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.credential-grid small {
  display: block;
  color: #64748b;
  font-size: 12px;
  margin-bottom: 8px;
}

.credential-grid strong {
  font-size: 18px;
  word-break: break-word;
}

.sms-note {
  margin: 14px 0 0;
}

.sms-note.danger {
  color: #b42318;
}

.register-actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.ghost-btn {
  min-width: 132px;
  background: #efe4ff;
  color: #9d6cff;
  backdrop-filter: blur(12px);
}

.register-submit {
  min-width: 220px;
}

.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #7c8ba1;
  font-size: 11px;
  letter-spacing: 0.08em;
  padding: 0 20px 6px;
}

@media (max-width: 980px) {
  .register-grid,
  .credential-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .topbar,
  .login-main,
  .register-modal {
    padding-left: 16px;
    padding-right: 16px;
  }

  .topbar,
  .login-foot,
  .register-modal-head,
  .register-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .login-card,
  .register-modal {
    border-radius: 24px;
  }

  .login-head h2,
  .register-modal-head h3 {
    font-size: 24px;
  }
}
</style>
