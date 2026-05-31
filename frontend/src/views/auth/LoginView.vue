<template>
  <div class="login-page" dir="rtl">
    <header class="topbar">
      <div class="brand">
        <span class="brand-title">CarWash</span>
        <span class="brand-subtitle">سامانه مدیریت</span>
      </div>
      <div class="lang">فارسی</div>
    </header>

    <main class="login-main">
      <div class="decor decor-right"></div>
      <div class="decor decor-left"></div>

      <section class="login-card">
        <div class="login-head">
          <h1>خوش آمدید</h1>
          <p>لطفا وارد حساب کاربری خود شوید</p>
        </div>

        <form class="login-form" @submit.prevent="onSubmit">
          <label class="field">
            <span>نام کاربری یا شماره همراه</span>
            <input v-model="form.username" type="text" placeholder="نام کاربری یا شماره همراه" />
          </label>

          <label class="field">
            <div class="field-row">
              <span>رمز عبور</span>
            </div>
            <input v-model="form.password" :type="showPassword ? 'text' : 'password'" placeholder="رمز عبور" />
          </label>

          <button class="submit-btn" type="submit" :disabled="isLoading">
            {{ isLoading ? 'در حال ورود...' : 'ورود به سامانه' }}
          </button>
          <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
        </form>

        <p class="support">نیاز به راهنمایی دارید؟ <a href="#">تماس با پشتیبانی</a></p>
      </section>
    </main>

    <footer class="footer">Powered by CarWash Platform © 2026</footer>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api, { ensureCsrfToken } from '../../services/api'
import { useAuthStore } from '../../store/auth.store'
import { defaultRouteByRole } from '../../config/navigation'

const showPassword = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')
const router = useRouter()
const authStore = useAuthStore()
const form = reactive({
  username: '',
  password: ''
})

const onSubmit = async () => {
  errorMessage.value = ''
  isLoading.value = true
  try {
    await ensureCsrfToken()
    await api.post('/auth/login/', {
      username: form.username,
      password: form.password
    })
    await authStore.fetchMe()

    await router.push(defaultRouteByRole[authStore.role] || '/')
  } catch (error) {
    errorMessage.value =
      error?.response?.data?.detail ||
      error?.response?.data?.non_field_errors?.[0] ||
      'ورود ناموفق بود. لطفا اطلاعات را بررسی کنید.'
  } finally {
    isLoading.value = false
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
  src: url('/font/webfonts/Vazirmatn-Medium.woff2') format('woff2');
  font-weight: 500;
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
  background: #f7f9fb;
  color: #191c1e;
  font-family: Vazirmatn, sans-serif;
}
.topbar {
  height: 64px;
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid #e4e7ee;
}
.brand { display: flex; align-items: center; gap: 8px; }
.brand-title { color: #0058be; font-weight: 700; }
.brand-subtitle { color: #727785; font-size: 12px; border-right: 1px solid #d8dbe2; padding-right: 8px; }
.lang { color: #727785; font-size: 14px; }
.login-main {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: hidden;
}
.decor {
  position: absolute;
  border-radius: 999px;
  filter: blur(80px);
  opacity: 0.4;
}
.decor-right { width: 360px; height: 360px; right: -80px; top: -60px; background: #acedff; }
.decor-left { width: 280px; height: 280px; left: -80px; bottom: -60px; background: #d8e2ff; }
.login-card {
  width: 100%;
  max-width: 420px;
  background: #fff;
  border-radius: 20px;
  border: 1px solid #e7e9ef;
  box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.08);
  padding: 32px;
  z-index: 1;
}
.login-head { text-align: center; margin-bottom: 24px; }
.login-head h1 { margin: 0 0 8px; font-size: 24px; }
.login-head p { margin: 0; color: #535a66; }
.login-form { display: grid; gap: 16px; }
.field { display: grid; gap: 8px; font-size: 14px; color: #535a66; }
.field input[type='text'],
.field input[type='password'] {
  height: 48px;
  border: 0;
  border-radius: 14px;
  background: #f2f4f6;
  padding: 0 14px;
  font-family: inherit;
}
.field input:focus { outline: 2px solid #0058be; }
.field-row { display: flex; justify-content: space-between; align-items: center; }
.submit-btn {
  height: 56px;
  border: 0;
  border-radius: 12px;
  color: #fff;
  font-weight: 700;
  cursor: pointer;
  background: linear-gradient(135deg, #0058be 0%, #00b4d8 100%);
  box-shadow: 0 8px 20px rgba(0, 88, 190, 0.25);
}
.submit-btn:disabled { opacity: 0.72; cursor: not-allowed; }
.error-text { margin: 0; color: #ba1a1a; font-size: 13px; text-align: center; }
.support { margin: 22px 0 0; text-align: center; color: #535a66; font-size: 14px; }
.support a { color: #0058be; font-weight: 700; text-decoration: none; }
.footer {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #7e8591;
  font-size: 10px;
  letter-spacing: 0.12em;
}
</style>
