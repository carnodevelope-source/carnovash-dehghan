<script setup>
import { computed, ref } from 'vue'
import { formatJalaliDate } from '../../../../utils/date'
import { formatMoney, formatFaNumber } from '../../utils/formatters.js'

const props = defineProps({
  points: { type: Array, default: () => [] },
  series: {
    type: Array,
    default: () => ([
      { key: 'hq_share_total', label: 'کارنو', color: '#1976d2', fill: 'rgba(25, 118, 210, 0.22)' },
      { key: 'rah_share_total', label: 'آراکار', color: '#7c3aed', fill: 'rgba(124, 58, 237, 0.18)' }
    ])
  },
  height: { type: Number, default: 220 },
  emptyText: { type: String, default: 'در این بازه روند ثبت نشده است.' }
})

const hoverIndex = ref(null)
const W = 640
const H = computed(() => props.height)
const chartCssHeight = computed(() => `${props.height}px`)
const PAD = { top: 18, right: 16, bottom: 36, left: 52 }

const chartPoints = computed(() => (props.points || []).map((p, i) => ({
  ...p,
  i,
  date: p.date,
  values: props.series.reduce((acc, s) => {
    acc[s.key] = Math.max(0, Number(p[s.key] || 0))
    return acc
  }, {})
})))

const maxValue = computed(() => {
  let max = 0
  for (const p of chartPoints.value) {
    for (const s of props.series) max = Math.max(max, p.values[s.key] || 0)
  }
  if (max <= 0) return 1
  const mag = 10 ** Math.floor(Math.log10(max))
  const nice = Math.ceil(max / mag) * mag
  return nice || 1
})

const innerW = computed(() => W - PAD.left - PAD.right)
const innerH = computed(() => H.value - PAD.top - PAD.bottom)

function xAt(i, n = chartPoints.value.length) {
  if (n <= 1) return PAD.left + innerW.value / 2
  return PAD.left + (i / (n - 1)) * innerW.value
}

function yAt(v) {
  const t = Math.max(0, Math.min(1, Number(v || 0) / maxValue.value))
  return PAD.top + innerH.value * (1 - t)
}

function buildSmoothPath(values) {
  const n = values.length
  if (!n) return ''
  if (n === 1) {
    const x = xAt(0, 1)
    const y = yAt(values[0])
    return `M ${x} ${y}`
  }
  const pts = values.map((v, i) => ({ x: xAt(i, n), y: yAt(v) }))
  let d = `M ${pts[0].x} ${pts[0].y}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[i + 2] || p2
    const cp1x = p1.x + (p2.x - p0.x) / 6
    const cp1y = p1.y + (p2.y - p0.y) / 6
    const cp2x = p2.x - (p3.x - p1.x) / 6
    const cp2y = p2.y - (p3.y - p1.y) / 6
    d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`
  }
  return d
}

function buildAreaPath(values) {
  const line = buildSmoothPath(values)
  if (!line || !values.length) return ''
  const n = values.length
  const x0 = xAt(0, n)
  const x1 = xAt(n - 1, n)
  const base = PAD.top + innerH.value
  return `${line} L ${x1} ${base} L ${x0} ${base} Z`
}

const seriesPaths = computed(() => props.series.map((s) => {
  const values = chartPoints.value.map((p) => p.values[s.key] || 0)
  return {
    ...s,
    line: buildSmoothPath(values),
    area: buildAreaPath(values),
    dots: values.map((v, i) => ({
      x: xAt(i, values.length),
      y: yAt(v),
      value: v,
      zero: v <= 0
    }))
  }
}))

const yTicks = computed(() => {
  const steps = 4
  return Array.from({ length: steps + 1 }, (_, i) => {
    const value = (maxValue.value * i) / steps
    return { value, y: yAt(value), label: abbreviateMoney(value) }
  })
})

const xLabels = computed(() => {
  const pts = chartPoints.value
  if (!pts.length) return []
  const maxLabels = Math.min(6, pts.length)
  const step = Math.max(1, Math.ceil((pts.length - 1) / Math.max(1, maxLabels - 1)))
  const indices = new Set([0, pts.length - 1])
  for (let i = step; i < pts.length - 1; i += step) indices.add(i)
  return [...indices].sort((a, b) => a - b).map((i) => ({
    i,
    x: xAt(i, pts.length),
    label: shortJalali(pts[i].date)
  }))
})

const totals = computed(() => props.series.map((s) => ({
  ...s,
  total: chartPoints.value.reduce((sum, p) => sum + (p.values[s.key] || 0), 0)
})))

const activePoint = computed(() => {
  if (hoverIndex.value == null) return null
  return chartPoints.value[hoverIndex.value] || null
})

const tooltipStyle = computed(() => {
  const p = activePoint.value
  if (!p) return {}
  const x = xAt(p.i, chartPoints.value.length)
  const leftPct = (x / W) * 100
  return {
    left: `${Math.max(8, Math.min(92, leftPct))}%`,
    transform: 'translateX(-50%)'
  }
})

function abbreviateMoney(value) {
  const n = Number(value || 0)
  if (n >= 1_000_000_000) return `${formatFaNumber((n / 1_000_000_000).toFixed(1))} میلیارد`
  if (n >= 1_000_000) return `${formatFaNumber((n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 1))} م`
  if (n >= 1_000) return `${formatFaNumber((n / 1_000).toFixed(n >= 10_000 ? 0 : 1))} هزار`
  return formatFaNumber(Math.round(n))
}

function shortJalali(date) {
  const full = formatJalaliDate(date)
  if (!full || full === '—') return '—'
  const parts = String(full).split('/')
  if (parts.length >= 3) return `${parts[1]}/${parts[2]}`
  return full
}

function onMove(event) {
  const pts = chartPoints.value
  if (!pts.length) return
  const svg = event.currentTarget
  if (!svg?.createSVGPoint || !svg.getScreenCTM) {
    const rect = svg.getBoundingClientRect()
    const ratio = (event.clientX - rect.left) / Math.max(1, rect.width)
    const x = ratio * W
    let best = 0
    let bestDist = Infinity
    for (let i = 0; i < pts.length; i++) {
      const dist = Math.abs(xAt(i, pts.length) - x)
      if (dist < bestDist) { bestDist = dist; best = i }
    }
    hoverIndex.value = best
    return
  }
  const pt = svg.createSVGPoint()
  pt.x = event.clientX
  pt.y = event.clientY
  const local = pt.matrixTransform(svg.getScreenCTM().inverse())
  let best = 0
  let bestDist = Infinity
  for (let i = 0; i < pts.length; i++) {
    const dist = Math.abs(xAt(i, pts.length) - local.x)
    if (dist < bestDist) { bestDist = dist; best = i }
  }
  hoverIndex.value = best
}

function onLeave() {
  hoverIndex.value = null
}
</script>

<template>
  <div class="hq-trend" dir="rtl">
    <div v-if="!chartPoints.length" class="hq-trend-empty">{{ emptyText }}</div>
    <template v-else>
      <div class="hq-trend-meta">
        <div v-for="item in totals" :key="item.key" class="hq-trend-stat">
          <span class="swatch" :style="{ background: item.color }" />
          <div>
            <small>{{ item.label }}</small>
            <strong>{{ formatMoney(item.total) }}</strong>
          </div>
        </div>
        <div class="hq-trend-stat muted">
          <div>
            <small>نقاط روند</small>
            <strong>{{ formatFaNumber(chartPoints.length) }} روز</strong>
          </div>
        </div>
      </div>

      <div class="hq-trend-stage">
        <div v-if="activePoint" class="hq-trend-tip" :style="tooltipStyle">
          <strong>{{ formatJalaliDate(activePoint.date) }}</strong>
          <p v-for="s in series" :key="s.key">
            <i :style="{ background: s.color }" />
            {{ s.label }}
            <b>{{ formatMoney(activePoint.values[s.key]) }}</b>
          </p>
        </div>

        <svg
          class="hq-trend-svg"
          :viewBox="`0 0 ${W} ${H}`"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="نمودار روند سهم‌ها"
          @mousemove="onMove"
          @mouseleave="onLeave"
        >
          <defs>
            <linearGradient v-for="s in series" :id="`fill-${s.key}`" :key="`g-${s.key}`" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" :stop-color="s.color" stop-opacity="0.32" />
              <stop offset="100%" :stop-color="s.color" stop-opacity="0.02" />
            </linearGradient>
            <filter id="soft-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="1.2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <g class="grid">
            <line
              v-for="tick in yTicks"
              :key="`gy-${tick.value}`"
              :x1="PAD.left"
              :x2="W - PAD.right"
              :y1="tick.y"
              :y2="tick.y"
            />
          </g>

          <g class="y-axis">
            <text
              v-for="tick in yTicks"
              :key="`yl-${tick.value}`"
              :x="PAD.left - 8"
              :y="tick.y + 3"
              text-anchor="end"
            >{{ tick.label }}</text>
          </g>

          <g v-for="s in seriesPaths" :key="`area-${s.key}`">
            <path :d="s.area" :fill="`url(#fill-${s.key})`" />
          </g>

          <g v-for="s in seriesPaths" :key="`line-${s.key}`" filter="url(#soft-glow)">
            <path :d="s.line" fill="none" :stroke="s.color" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
          </g>

          <g v-if="activePoint">
            <line
              class="guide"
              :x1="xAt(activePoint.i)"
              :x2="xAt(activePoint.i)"
              :y1="PAD.top"
              :y2="PAD.top + innerH"
            />
          </g>

          <g v-for="s in seriesPaths" :key="`dots-${s.key}`">
            <circle
              v-for="(d, i) in s.dots"
              :key="`${s.key}-${i}`"
              :cx="d.x"
              :cy="d.y"
              :r="hoverIndex === i ? 5.2 : (d.zero ? 2.2 : 3.4)"
              :fill="d.zero ? '#fff' : s.color"
              :stroke="s.color"
              stroke-width="2"
              class="dot"
              :class="{ active: hoverIndex === i }"
            />
          </g>

          <g class="x-axis">
            <text
              v-for="lab in xLabels"
              :key="`xl-${lab.i}`"
              :x="lab.x"
              :y="H - 10"
              text-anchor="middle"
            >{{ lab.label }}</text>
          </g>
        </svg>
      </div>

      <div class="hq-trend-legend">
        <span v-for="s in series" :key="`leg-${s.key}`">
          <i :style="{ background: s.color }" /> {{ s.label }}
        </span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.hq-trend {
  display: grid;
  gap: 0.75rem;
  min-height: 220px;
}
.hq-trend-empty {
  min-height: 180px;
  display: grid;
  place-items: center;
  color: #6b7c93;
  font-size: 13px;
  background:
    radial-gradient(circle at top, rgba(25, 118, 210, 0.06), transparent 55%),
    #f8fbff;
  border: 1px dashed rgba(25, 118, 210, 0.18);
  border-radius: 14px;
}
.hq-trend-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}
.hq-trend-stat {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.7rem;
  border-radius: 12px;
  background: linear-gradient(180deg, #f8fbff, #f3f7fc);
  border: 1px solid rgba(25, 118, 210, 0.1);
  min-width: 132px;
}
.hq-trend-stat.muted { background: #fff; }
.hq-trend-stat .swatch {
  width: 8px;
  height: 28px;
  border-radius: 999px;
}
.hq-trend-stat small {
  display: block;
  color: #6b7c93;
  font-size: 11px;
  margin-bottom: 0.1rem;
}
.hq-trend-stat strong {
  color: #0f2545;
  font-size: 13px;
  font-weight: 780;
  font-variant-numeric: tabular-nums;
}
.hq-trend-stage {
  position: relative;
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(248, 251, 255, 0.95), rgba(255, 255, 255, 0.9));
  border: 1px solid rgba(25, 118, 210, 0.08);
  overflow: hidden;
}
.hq-trend-svg {
  width: 100%;
  height: v-bind(chartCssHeight);
  display: block;
  cursor: crosshair;
}
.grid line {
  stroke: rgba(100, 120, 146, 0.14);
  stroke-dasharray: 3 4;
}
.y-axis text,
.x-axis text {
  fill: #7a8aa0;
  font-size: 11px;
  font-family: inherit;
}
.guide {
  stroke: rgba(15, 37, 69, 0.28);
  stroke-dasharray: 4 4;
}
.dot {
  transition: r 120ms ease, opacity 120ms ease;
}
.dot.active {
  filter: drop-shadow(0 0 4px rgba(25, 118, 210, 0.45));
}
.hq-trend-tip {
  position: absolute;
  top: 10px;
  z-index: 2;
  min-width: 168px;
  padding: 0.55rem 0.7rem;
  border-radius: 12px;
  background: rgba(15, 37, 69, 0.92);
  color: #fff;
  box-shadow: 0 12px 28px rgba(15, 37, 69, 0.22);
  pointer-events: none;
  backdrop-filter: blur(6px);
}
.hq-trend-tip strong {
  display: block;
  font-size: 12px;
  margin-bottom: 0.35rem;
  color: #dbeafe;
  font-weight: 700;
}
.hq-trend-tip p {
  margin: 0.18rem 0 0;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 12px;
  color: #e8eef8;
}
.hq-trend-tip i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
}
.hq-trend-tip b {
  margin-right: auto;
  font-variant-numeric: tabular-nums;
  font-weight: 750;
  color: #fff;
}
.hq-trend-legend {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  color: #6b7c93;
  font-size: 12px;
}
.hq-trend-legend i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-left: 0.3rem;
}
</style>
