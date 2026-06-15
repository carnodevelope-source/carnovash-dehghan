<template>
  <div ref="rootRef" class="base-date-picker">
    <button type="button" class="picker-input" @click="toggleOpen">
      <span :class="{ placeholder: !modelValue }">{{ modelValue || placeholder }}</span>
      <span class="calendar-icon">▾</span>
    </button>

    <button v-if="clearable && modelValue" type="button" class="clear-btn" @click="clearValue" aria-label="پاک کردن تاریخ">×</button>

    <div v-if="isOpen" class="picker-popup">
      <header class="popup-head">
        <button type="button" class="nav-btn" @click="goPrevMonth">‹</button>
        <div class="head-selects">
          <select v-model.number="currentMonth">
            <option v-for="month in monthOptions" :key="month.value" :value="month.value">{{ month.label }}</option>
          </select>
          <select v-model.number="currentYear">
            <option v-for="year in yearOptions" :key="year" :value="year">{{ year }}</option>
          </select>
        </div>
        <button type="button" class="nav-btn" @click="goNextMonth">›</button>
      </header>

      <div class="week-row">
        <span v-for="day in weekDays" :key="day">{{ day }}</span>
      </div>

      <div class="days-grid">
        <button
          v-for="cell in calendarCells"
          :key="cell.key"
          type="button"
          class="day-cell"
          :class="{ empty: !cell.day, selected: cell.selected, today: cell.today }"
          :disabled="!cell.day"
          @click="selectDay(cell.day)"
        >
          {{ cell.day || '' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: 'انتخاب تاریخ' },
  clearable: { type: Boolean, default: true }
})

const emit = defineEmits(['update:modelValue'])

const rootRef = ref(null)
const isOpen = ref(false)

const monthNames = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
const weekDays = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج']

const getTodayJalali = () => {
  const parts = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric'
  }).formatToParts(new Date())
  const y = Number(parts.find((item) => item.type === 'year')?.value || 1400)
  const m = Number(parts.find((item) => item.type === 'month')?.value || 1)
  const d = Number(parts.find((item) => item.type === 'day')?.value || 1)
  return { y, m, d }
}

const today = getTodayJalali()
const currentYear = ref(today.y)
const currentMonth = ref(today.m)

const parseJalali = (value) => {
  if (!value) return null
  const m = String(value).trim().match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/)
  if (!m) return null
  const y = Number(m[1])
  const month = Number(m[2])
  const day = Number(m[3])
  if (month < 1 || month > 12 || day < 1 || day > 31) return null
  return { y, m: month, d: day }
}

const formatJalali = (y, m, d) => `${y}/${String(m).padStart(2, '0')}/${String(d).padStart(2, '0')}`

const isLeapJalali = (year) => {
  const mod = year % 33
  return [1, 5, 9, 13, 17, 22, 26, 30].includes(mod)
}

const daysInMonth = (year, month) => {
  if (month <= 6) return 31
  if (month <= 11) return 30
  return isLeapJalali(year) ? 30 : 29
}

const jalaliToGregorian = (input) => {
  const value = (input || '').trim().replace(/-/g, '/')
  const match = value.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/)
  if (!match) return null
  const jy = Number(match[1]) - 979
  const jm = Number(match[2]) - 1
  const jd = Number(match[3]) - 1
  const jDaysInMonth = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
  let jDayNo = 365 * jy + Math.floor(jy / 33) * 8 + Math.floor(((jy % 33) + 3) / 4)
  for (let i = 0; i < jm; i += 1) jDayNo += jDaysInMonth[i]
  jDayNo += jd
  let gDayNo = jDayNo + 79
  let gy = 1600 + 400 * Math.floor(gDayNo / 146097)
  gDayNo %= 146097
  let leap = true
  if (gDayNo >= 36525) {
    gDayNo -= 1
    gy += 100 * Math.floor(gDayNo / 36524)
    gDayNo %= 36524
    if (gDayNo >= 365) gDayNo += 1
    else leap = false
  }
  gy += 4 * Math.floor(gDayNo / 1461)
  gDayNo %= 1461
  if (gDayNo >= 366) {
    leap = false
    gDayNo -= 1
    gy += Math.floor(gDayNo / 365)
    gDayNo %= 365
  }
  const gdMonth = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  let gm = 0
  while (gm < 12 && gDayNo >= gdMonth[gm]) {
    gDayNo -= gdMonth[gm]
    gm += 1
  }
  const gd = gDayNo + 1
  return { y: gy, m: gm + 1, d: gd }
}

const firstWeekdayOffset = computed(() => {
  const g = jalaliToGregorian(formatJalali(currentYear.value, currentMonth.value, 1))
  if (!g) return 0
  const jsDay = new Date(g.y, g.m - 1, g.d).getDay()
  return (jsDay + 1) % 7
})

const selectedDate = computed(() => parseJalali(props.modelValue))

const calendarCells = computed(() => {
  const total = daysInMonth(currentYear.value, currentMonth.value)
  const offset = firstWeekdayOffset.value
  const cells = []
  for (let i = 0; i < offset; i += 1) {
    cells.push({ key: `e-${i}`, day: null, selected: false, today: false })
  }
  for (let d = 1; d <= total; d += 1) {
    const selected = Boolean(
      selectedDate.value
      && selectedDate.value.y === currentYear.value
      && selectedDate.value.m === currentMonth.value
      && selectedDate.value.d === d
    )
    const isToday = today.y === currentYear.value && today.m === currentMonth.value && today.d === d
    cells.push({ key: `d-${d}`, day: d, selected, today: isToday })
  }
  while (cells.length % 7 !== 0) {
    cells.push({ key: `t-${cells.length}`, day: null, selected: false, today: false })
  }
  return cells
})

const monthOptions = computed(() => monthNames.map((label, idx) => ({ label, value: idx + 1 })))

const yearOptions = computed(() => {
  const from = today.y - 10
  const to = today.y + 10
  const years = []
  for (let y = from; y <= to; y += 1) years.push(y)
  return years
})

const goPrevMonth = () => {
  if (currentMonth.value === 1) {
    currentMonth.value = 12
    currentYear.value -= 1
    return
  }
  currentMonth.value -= 1
}

const goNextMonth = () => {
  if (currentMonth.value === 12) {
    currentMonth.value = 1
    currentYear.value += 1
    return
  }
  currentMonth.value += 1
}

const selectDay = (day) => {
  if (!day) return
  emit('update:modelValue', formatJalali(currentYear.value, currentMonth.value, day))
  isOpen.value = false
}

const toggleOpen = () => {
  isOpen.value = !isOpen.value
}

const clearValue = () => {
  emit('update:modelValue', '')
}

const onClickOutside = (event) => {
  if (!rootRef.value) return
  if (!rootRef.value.contains(event.target)) {
    isOpen.value = false
  }
}

watch(() => props.modelValue, (value) => {
  const parsed = parseJalali(value)
  if (!parsed) return
  currentYear.value = parsed.y
  currentMonth.value = parsed.m
}, { immediate: true })

onMounted(() => {
  document.addEventListener('click', onClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside)
})
</script>

<style scoped>
.base-date-picker { position: relative; display: flex; align-items: center; gap: 6px; }
.picker-input {
  width: 100%;
  height: 38px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  cursor: pointer;
  font-size: 12px;
}
.picker-input .placeholder { color: #94a3b8; }
.calendar-icon { color: #64748b; font-size: 11px; }
.clear-btn {
  width: 24px;
  height: 24px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  cursor: pointer;
}
.picker-popup {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  width: 280px;
  background: #ffffff;
  border: 1px solid #dbe4f2;
  border-radius: 12px;
  box-shadow: 0 14px 32px -18px rgba(15, 23, 42, 0.45);
  padding: 10px;
  z-index: 40;
}
.popup-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.nav-btn {
  width: 28px;
  height: 28px;
  border: 1px solid #dbe4f2;
  border-radius: 8px;
  background: #f8fbff;
  cursor: pointer;
}
.head-selects { display: flex; gap: 6px; }
.head-selects select {
  height: 30px;
  border: 1px solid #dbe4f2;
  border-radius: 8px;
  background: #fff;
  padding: 0 8px;
  font-size: 12px;
}
.week-row { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 6px; }
.week-row span {
  text-align: center;
  font-size: 11px;
  color: #64748b;
  padding: 4px 0;
}
.days-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.day-cell {
  height: 30px;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  background: #fff;
  font-size: 12px;
  cursor: pointer;
}
.day-cell.empty { border-color: transparent; background: transparent; cursor: default; }
.day-cell.selected { background: #2563eb; border-color: #2563eb; color: #fff; }
.day-cell.today { border-color: #2563eb; }
@media (max-width: 640px) {
  .picker-popup {
    position: fixed;
    top: auto;
    right: 12px;
    left: 12px;
    bottom: 12px;
    width: auto;
    max-height: min(420px, calc(100vh - 24px));
    overflow: auto;
    border-radius: 16px;
  }
}
</style>
