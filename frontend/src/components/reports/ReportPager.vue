<template>
  <nav v-if="total > 0" class="report-pager" aria-label="صفحه‌بندی جدول">
    <div class="pager-meta">
      <span class="pager-meta-kicker">نمایش صفحه</span>
      <strong>{{ fa(from) }}–{{ fa(to) }}</strong>
      <span>از {{ fa(total) }} ردیف</span>
    </div>

    <div v-if="pages > 1" class="pager-controls">
      <button
        type="button"
        class="pager-nav"
        :disabled="page <= 1"
        aria-label="صفحه قبل"
        @click="go(page - 1)"
      >
        <IconlyIcon name="arrowRight" size="sm" />
        <span>قبلی</span>
      </button>

      <div class="pager-pages" role="list">
        <template v-for="(item, index) in visiblePages" :key="`${item}-${index}`">
          <span v-if="item === 'ellipsis'" class="pager-ellipsis" aria-hidden="true">…</span>
          <button
            v-else
            type="button"
            class="pager-page"
            :class="{ active: item === page }"
            :aria-current="item === page ? 'page' : undefined"
            :aria-label="`صفحه ${item}`"
            @click="go(item)"
          >
            {{ fa(item) }}
          </button>
        </template>
      </div>

      <button
        type="button"
        class="pager-nav next"
        :disabled="page >= pages"
        aria-label="صفحه بعد"
        @click="go(page + 1)"
      >
        <span>بعدی</span>
        <IconlyIcon name="arrowLeft" size="sm" />
      </button>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import IconlyIcon from '../base/IconlyIcon.vue'

const props = defineProps({
  page: { type: Number, default: 1 },
  pages: { type: Number, default: 1 },
  total: { type: Number, default: 0 },
  from: { type: Number, default: 0 },
  to: { type: Number, default: 0 }
})

const emit = defineEmits(['update:page'])

const fa = (value) => Number(value || 0).toLocaleString('fa-IR')

const visiblePages = computed(() => {
  const total = Math.max(1, Number(props.pages) || 1)
  const current = Math.min(Math.max(1, Number(props.page) || 1), total)
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1)

  const items = [1]
  let start = Math.max(2, current - 1)
  let end = Math.min(total - 1, current + 1)
  if (current <= 3) {
    start = 2
    end = 4
  } else if (current >= total - 2) {
    start = total - 3
    end = total - 1
  }
  if (start > 2) items.push('ellipsis')
  for (let number = start; number <= end; number += 1) items.push(number)
  if (end < total - 1) items.push('ellipsis')
  items.push(total)
  return items
})

const go = (next) => {
  const total = Math.max(1, Number(props.pages) || 1)
  const target = Math.min(Math.max(1, Number(next) || 1), total)
  if (target === props.page) return
  emit('update:page', target)
}
</script>

<style scoped>
.report-pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: 22px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(244, 249, 255, 0.88));
  border: 1px solid rgba(191, 215, 255, 0.9);
  box-shadow:
    0 18px 40px -28px rgba(15, 76, 129, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.pager-meta {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.pager-meta-kicker {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: #eef4ff;
  color: #1d4ed8;
  font-size: 11px;
}

.pager-meta strong {
  color: #0f172a;
  font-size: 13px;
}

.pager-controls {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-right: auto;
}

.pager-nav,
.pager-page {
  border: 0;
  cursor: pointer;
  font: inherit;
}

.pager-nav {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 42px;
  padding: 0 14px;
  border-radius: 14px;
  background: #fff;
  color: #0f172a;
  font-size: 12px;
  font-weight: 800;
  border: 1px solid #d7e5f8;
  box-shadow: 0 8px 18px -16px rgba(15, 23, 42, 0.5);
  transition: transform .16s ease, box-shadow .16s ease, background .16s ease, opacity .16s ease;
}

.pager-nav.next {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 14px 28px -16px rgba(37, 99, 235, 0.85);
}

.pager-nav.next :deep(.iconly-shell) {
  --iconly-filter: brightness(0) saturate(100%) invert(100%);
}

.pager-nav:hover:not(:disabled) {
  transform: translateY(-1px);
}

.pager-nav:disabled {
  opacity: .38;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.pager-pages {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid #e2e8f0;
}

.pager-page {
  min-width: 38px;
  height: 38px;
  padding: 0 8px;
  border-radius: 12px;
  background: transparent;
  color: #334155;
  font-size: 13px;
  font-weight: 800;
  transition: background .16s ease, color .16s ease, transform .16s ease;
}

.pager-page:hover {
  background: #eef4ff;
  color: #1d4ed8;
}

.pager-page.active {
  background: linear-gradient(180deg, #1d4ed8, #2563eb);
  color: #fff;
  box-shadow: 0 10px 18px -12px rgba(37, 99, 235, 0.9);
  transform: translateY(-1px);
}

.pager-ellipsis {
  min-width: 18px;
  color: #94a3b8;
  font-weight: 800;
  text-align: center;
}

@media (max-width: 768px) {
  .report-pager {
    padding: 12px;
    border-radius: 20px;
  }

  .pager-controls,
  .pager-pages {
    width: 100%;
    justify-content: center;
    flex-wrap: wrap;
  }

  .pager-nav {
    flex: 1 1 auto;
    justify-content: center;
  }
}
</style>
