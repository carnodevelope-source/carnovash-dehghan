<template>
  <div class="login-page" dir="rtl">
    <video class="login-video" autoplay muted loop playsinline preload="metadata" poster="/login-poster.webp">
      <source src="/login-hero.mp4" type="video/mp4" />
    </video>
    <div class="login-video-veil"></div>

    <header class="topbar">
      <div class="brand">
        <span class="brand-badge">CW</span>
        <div class="brand-copy">
          <span class="brand-title">CarnoWash</span>
          <span class="brand-subtitle">ورود مدیران، اپراتورها و ثبت کارواش جدید</span>
        </div>
      </div>
    </header>

    <main class="login-main">
      <section class="login-card">
        <div class="login-head">
          <p class="panel-kicker">ورود به سامانه</p>
          <h1>ورود به سامانه مدیریت کارواش CarnoWash</h1>
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
            <span>پس از ثبت، مدارک به پشتیبانی ارسال می‌شود. بعد از تایید پشتیبان، پیامک فعال‌سازی فرستاده می‌شود و لاگین مدیر باز خواهد شد.</span>
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
              <label class="field field-soft full">
                <span>مدارک شناسایی کسب‌وکار</span>
                <input type="file" multiple accept=".jpg,.jpeg,.png,.pdf,.webp" @change="onRegisterDocumentsChange" />
                <small class="upload-hint">حداقل یک فایل بارگذاری کنید. فرمت‌های مجاز: تصویر یا PDF</small>
                <div v-if="registerForm.business_identity_documents.length" class="upload-file-list">
                  <span v-for="file in registerForm.business_identity_documents" :key="`${file.name}-${file.size}`">{{ file.name }}</span>
                </div>
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
                <p>بعد از تایید پشتیبانی، همین نام کاربری و رمز برای مدیر پیامک می‌شود و امکان ورود فعال خواهد شد.</p>
              </div>
            </div>
          </section>

          <p v-if="registerError" class="error-text register-error">{{ registerError }}</p>

          <section v-if="registerSuccess.pendingApproval" class="register-result">
            <div class="register-result-head">
              <strong>درخواست ثبت شد</strong>
              <span>{{ registerSuccess.tenantName }}</span>
            </div>
            <div class="credential-grid">
              <article>
                <small>شماره پیگیری تیکت</small>
                <strong>#{{ registerSuccess.ticketId || '-' }}</strong>
              </article>
              <article>
                <small>وضعیت</small>
                <strong>در انتظار تایید پشتیبانی</strong>
              </article>
            </div>
            <p class="sms-note">
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

    <footer class="footer">Powered by CarnoWash Platform © 2026</footer>
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
  manager_password: '',
  business_identity_documents: []
})

const registerModal = reactive({ open: false })
const registerSuccess = reactive({
  tenantName: '',
  pendingApproval: false,
  ticketId: 0,
  smsMessage: ''
})

const resetRegisterState = () => {
  registerError.value = ''
  registerSuccess.tenantName = ''
  registerSuccess.pendingApproval = false
  registerSuccess.ticketId = 0
  registerSuccess.smsMessage = ''
}

const resetRegisterForm = () => {
  registerForm.carwash_name = ''
  registerForm.carwash_address = ''
  registerForm.manager_first_name = ''
  registerForm.manager_last_name = ''
  registerForm.manager_username = ''
  registerForm.manager_phone = ''
  registerForm.manager_password = ''
  registerForm.business_identity_documents = []
}

const openRegisterModal = () => {
  resetRegisterState()
  resetRegisterForm()
  registerModal.open = true
}

const closeRegisterModal = () => {
  registerModal.open = false
}

const onRegisterDocumentsChange = (event) => {
  registerForm.business_identity_documents = Array.from(event?.target?.files || [])
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
  if (!registerForm.business_identity_documents.length) {
    registerError.value = 'بارگذاری حداقل یک مدرک شناسایی کسب‌وکار الزامی است.'
    return
  }

  registerLoading.value = true
  try {
    await ensureCsrfToken()
    const payload = new FormData()
    payload.append('carwash_name', registerForm.carwash_name)
    payload.append('carwash_address', registerForm.carwash_address || '')
    payload.append('manager_first_name', registerForm.manager_first_name)
    payload.append('manager_last_name', registerForm.manager_last_name)
    payload.append('manager_username', registerForm.manager_username)
    payload.append('manager_phone', registerForm.manager_phone)
    payload.append('manager_password', registerForm.manager_password)
    registerForm.business_identity_documents.forEach((file) => {
      payload.append('business_identity_documents', file)
    })
    const { data } = await api.post('/auth/tenants/register/', payload, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    registerSuccess.tenantName = data?.tenant?.name || registerForm.carwash_name
    registerSuccess.pendingApproval = data?.registration?.status === 'pending'
    registerSuccess.ticketId = Number(data?.registration?.ticket_id || 0)
    registerSuccess.smsMessage = data?.registration?.message || 'درخواست شما برای بررسی پشتیبانی ثبت شد.'
    form.username = registerForm.manager_username
    form.password = ''
    resetRegisterForm()
  } catch (error) {
    registerError.value = resolveApiErrorMessage(error, 'ثبت نام ناموفق بود.')
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped>
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
  filter: blur(6px);
  transform: scale(1.04);
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
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.32) 0%, rgba(255, 255, 255, 0.22) 100%);
  backdrop-filter: blur(5px);
  box-shadow: 0 18px 60px rgba(114, 78, 167, 0.12);
}

.login-head {
  display: grid;
  gap: 8px;
  margin-bottom: 22px;
}

.login-head h1,
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
  color: #91bfff;
}

.text-btn {
  color: #5b5a74;
  font-weight: 800;
}

.register-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(237, 229, 246, 0.44);
  backdrop-filter: blur(9px);
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
  backdrop-filter: blur(20px);
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

.upload-hint {
  color: #64748b;
  font-size: 12px;
}

.upload-file-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.upload-file-list span {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.58);
  font-size: 12px;
  color: #334155;
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
  .login-page {
    background-image: image-set(
      url('/Mobile-bg-640.avif') type('image/avif'),
      url('/Mobile-bg-640.webp') type('image/webp'),
      url('/Mobile-bg.jpg') type('image/jpeg')
    );
    background-position: center center;
    background-size: cover;
    background-repeat: no-repeat;
  }

  .login-video {
    display: none;
  }

  .login-video-veil {
    display: none;
  }

  .login-card {
    border-color: rgba(255, 255, 255, 0.282);
    background: linear-gradient(180deg, rgba(62, 63, 67, 0.562) 0%, rgba(19, 45, 246, 0) 100%);
    backdrop-filter: blur(3px);
    box-shadow: 0 22px 56px rgba(15, 23, 42, 0.22);
  }

  .field input,
  .field textarea {
    background: rgba(255, 255, 255, 0.82);
    border-color: rgba(255, 255, 255, 0.78);
    backdrop-filter: blur(5px);
  }

  .field input:focus,
  .field textarea:focus {
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.22);
  }

  .brand-title,
  .brand-subtitle,
  .panel-kicker,
  .login-head h1,
  .login-head span,
  .field span,
  .field-toggle,
  .login-foot p,
  .text-btn {
    color: #f8fbff;
  }

  .login-head h1 {
    text-shadow: 0 8px 24px rgba(15, 23, 42, 0.28);
  }

  .brand-subtitle,
  .login-head span,
  .login-foot p {
    color: rgba(248, 251, 255, 0.9);
  }

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

  .login-head h1,
  .register-modal-head h3 {
    font-size: 24px;
  }
}
</style>
