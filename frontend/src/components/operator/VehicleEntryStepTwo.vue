<template>
  <section class="step-two">
    <div class="step-layout">
      <article class="summary-panel">
        <header class="panel-head">
          <h3>اطلاعات خودرو</h3>
          <p>اطلاعات مرحله اول قابل بازبینی است.</p>
        </header>

        <div class="plate-card" dir="ltr">
          <span class="plate-left">{{ vehiclePlate.left }}</span>
          <span class="plate-letter">{{ vehiclePlate.letter }}</span>
          <span class="plate-mid">{{ vehiclePlate.mid }}</span>
          <span class="plate-right">{{ vehiclePlate.right }}</span>
        </div>

        <div class="info-grid">
          <p><span>مدل</span><strong>{{ vehicleInfo?.model || '-' }}</strong></p>
          <p><span>رنگ</span><strong>{{ vehicleInfo?.color || '-' }}</strong></p>
          <p><span>راننده</span><strong>{{ driverName || '-' }}</strong></p>
          <p><span>شماره تماس</span><strong dir="ltr">{{ driverPhone || '-' }}</strong></p>
        </div>

        <div class="driver-edit">
          <label>
            <span>ویرایش نام راننده</span>
            <input v-model="driverName" placeholder="نام و نام خانوادگی" />
          </label>
          <label>
            <span>ویرایش شماره تماس</span>
            <input v-model="driverPhone" dir="ltr" placeholder="0912..." />
          </label>
        </div>
      </article>

      <article class="assign-panel">
        <header class="panel-head">
          <h3>تخصیص خدمات و پرسنل</h3>
          <p>حداقل یک خدمت و یک نیرو انتخاب کنید.</p>
        </header>

        <section class="block">
          <h4>خدمات</h4>
          <div class="services-grid">
            <label
              v-for="service in services"
              :key="service.id"
              class="service-item"
              :class="{ active: selectedServiceIds.includes(service.id) }"
            >
              <input v-model="selectedServiceIds" type="checkbox" :value="service.id" />
              <div>
                <strong>{{ service.title }}</strong>
                <small>{{ formatMoney(service.price) }}</small>
              </div>
            </label>
            <p v-if="!services.length" class="empty-row">خدمت فعالی یافت نشد.</p>
          </div>
        </section>

        <section class="block">
          <h4>نیروی اجرایی</h4>
          <div class="workers-grid">
            <button
              v-for="worker in staffList"
              :key="worker.id"
              type="button"
              class="worker-chip"
              :class="{ active: selectedStaffId === worker.id }"
              @click="selectedStaffId = worker.id"
            >
              {{ worker.name }}
            </button>
            <p v-if="!staffList.length" class="empty-row">نیروی فعالی یافت نشد.</p>
          </div>
        </section>
      </article>
    </div>

    <footer class="actions">
      <button type="button" class="ghost" @click="$emit('back')">بازگشت</button>
      <button type="button" class="secondary" :disabled="!canRefer" @click="onRefer">ارجاع</button>
      <button type="button" class="primary" :disabled="!canAssign" @click="onAssign">تخصیص</button>
    </footer>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../../services/api'

const props = defineProps({ vehicleInfo: { type: Object, default: () => ({}) } })
const emit = defineEmits(['back', 'refer', 'assign'])

const services = ref([])
const staffList = ref([])
const selectedServiceIds = ref([])
const selectedStaffId = ref(null)
const driverName = ref(props.vehicleInfo?.driver || '')
const driverPhone = ref(props.vehicleInfo?.mobile || '')

const selectedServices = computed(() => services.value.filter((s) => selectedServiceIds.value.includes(s.id)))
const selectedStaff = computed(() => staffList.value.find((w) => w.id === selectedStaffId.value) || null)
const canRefer = computed(() => driverPhone.value.trim().length > 0)
const canAssign = computed(() => canRefer.value && selectedServices.value.length > 0 && !!selectedStaff.value)

const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (d) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)))
  .replace(/\D/g, '')

const formatMoney = (value) => `${Number(value || 0).toLocaleString('fa-IR')} تومان`

const vehiclePlate = computed(() => {
  const raw = String(props.vehicleInfo?.plate || '').trim()
  const [left = '--', letter = '-', mid = '---', right = '--'] = raw.split(/\s+/).filter(Boolean)
  return { left, letter, mid, right }
})

const payload = () => ({
  vehicle: { ...props.vehicleInfo, driver: driverName.value.trim(), mobile: normalizeDigits(driverPhone.value) },
  services: selectedServices.value,
  staff: selectedStaff.value
})

const onRefer = () => { if (!canRefer.value) return; emit('refer', payload()) }
const onAssign = () => { if (!canAssign.value) return; emit('assign', payload()) }

onMounted(async () => {
  const [servicesRes, workersRes] = await Promise.allSettled([api.get('/services/'), api.get('/workers/')])
  services.value = servicesRes.status === 'fulfilled'
    ? (Array.isArray(servicesRes.value.data) ? servicesRes.value.data : []).filter((i) => i.is_active).map((i) => ({ id: i.id, title: i.name, price: Number(i.base_price || 0) }))
    : []
  staffList.value = workersRes.status === 'fulfilled'
    ? (Array.isArray(workersRes.value.data) ? workersRes.value.data : []).filter((i) => i.is_available).map((i) => ({ id: i.id, name: i.full_name }))
    : []
  if (props.vehicleInfo?.serviceIds?.length) selectedServiceIds.value = [...props.vehicleInfo.serviceIds]
  if (props.vehicleInfo?.staffId) selectedStaffId.value = props.vehicleInfo.staffId
})
</script>

<style scoped>
.step-two { padding: 22px; background: #f7f9fb; display: grid; gap: 12px; }
.step-layout { display: grid; grid-template-columns: 1fr 1.2fr; gap: 14px; }
.summary-panel, .assign-panel { border: 1px solid #dbe3ef; border-radius: 16px; background: #fff; padding: 16px; display: grid; gap: 12px; }
.summary-panel { background: #f8fbff; }
.panel-head h3 { margin: 0; color: #0f172a; font-size: 20px; }
.panel-head p { margin: 4px 0 0; color: #64748b; font-size: 12px; }
.plate-card { display: grid; grid-template-columns: 64px 64px 84px 64px; justify-content: center; gap: 6px; border: 1px solid #cbd5e1; border-radius: 12px; background: #fff; padding: 8px; }
.plate-card span { height: 42px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; color: #0f172a; background: #f8fafc; }
.info-grid { display: grid; gap: 8px; }
.info-grid p { margin: 0; border: 1px solid #e2e8f0; border-radius: 10px; padding: 8px 10px; display: grid; gap: 3px; background: #fff; }
.info-grid p span { font-size: 11px; color: #64748b; }
.info-grid p strong { font-size: 13px; color: #0f172a; }
.driver-edit { display: grid; gap: 8px; }
.driver-edit label { display: grid; gap: 4px; }
.driver-edit label span { font-size: 12px; color: #475569; font-weight: 600; }
.driver-edit input { height: 40px; border: 1px solid #cbd5e1; border-radius: 10px; padding: 0 10px; }
.block h4 { margin: 0 0 8px; font-size: 14px; color: #334155; }
.services-grid { display: grid; gap: 8px; max-height: 260px; overflow: auto; padding-left: 2px; }
.service-item { border: 1px solid #dbe3ef; border-radius: 10px; padding: 10px; display: flex; align-items: center; gap: 8px; cursor: pointer; background: #fff; }
.service-item.active { border-color: #60a5fa; background: #eff6ff; }
.service-item input { accent-color: #2563eb; }
.service-item strong { display: block; font-size: 13px; color: #0f172a; }
.service-item small { display: block; margin-top: 2px; font-size: 11px; color: #64748b; }
.workers-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.worker-chip { border: 1px solid #cbd5e1; border-radius: 999px; height: 36px; padding: 0 14px; background: #fff; color: #334155; font-weight: 600; cursor: pointer; }
.worker-chip.active { border-color: #1d4ed8; background: #dbeafe; color: #1e3a8a; }
.empty-row { margin: 0; font-size: 12px; color: #64748b; }
.actions { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
.actions button { height: 42px; border-radius: 10px; border: 0; padding: 0 14px; font-weight: 700; cursor: pointer; }
.ghost { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; }
.secondary { background: #dcfce7; color: #166534; }
.primary { background: linear-gradient(135deg, #0058be 0%, #3b82f6 100%); color: #fff; }
.actions button:disabled { opacity: .5; cursor: not-allowed; }

@media (max-width: 1024px) {
  .step-layout { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .step-two { padding: 12px; }
  .actions { flex-wrap: wrap; }
  .actions button { flex: 1 1 100%; }
}
</style>
