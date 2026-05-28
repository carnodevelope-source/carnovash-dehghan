# 🌞 Design System — Carwash Premium UI (Light Mode)
**Modern, Clean, Luxurious, Soft & Impactful**

---

## 1️⃣ حس کلی (Light Edition)

این سیستم باید احساس:
- **تمیز و براق** (مثل ماشین تازه شسته‌شده)
- **نرم و دلنشین**
- **لوکس ولی گرم**
- **حرفه‌ای ولی دوستانه**
- **مدرن و هوشمند**
- **عمق بصری با سایه‌های ملایم**

### کلمات کلیدی برند
- Clean & Fresh
- Soft Luxury
- Bright Premium
- Warm Professional
- Smart Operations
- Elegant Simplicity

---

## 2️⃣ پالت رنگی (Light Mode)

### Background Colors
```css
--bg-main: #F8FAFC;           /* سفید خاکستری خیلی روشن */
--bg-surface: #FFFFFF;        /* سفید خالص */
--bg-card: #FFFFFF;           /* کارت‌ها */
--bg-elevated: #FFFFFF;       /* مودال‌ها */
--bg-subtle: #F1F5F9;         /* پس‌زمینه ثانویه */
--bg-hover: #F8FAFC;          /* hover state */
```

### Text Colors
```css
--text-primary: #0F172A;      /* متن اصلی - تیره */
--text-secondary: #475569;    /* متن ثانویه */
--text-muted: #64748B;        /* متن کم‌اهمیت */
--text-disabled: #94A3B8;     /* غیرفعال */
--text-inverse: #FFFFFF;      /* روی دکمه‌های رنگی */
```

### Border Colors
```css
--border-light: #E2E8F0;      /* border معمولی */
--border-medium: #CBD5E1;     /* border واضح‌تر */
--border-strong: #94A3B8;     /* border پررنگ */
--border-focus: #3B82F6;      /* focus state */
```

### Brand Colors (Primary)
```css
--primary-50: #EFF6FF;
--primary-100: #DBEAFE;
--primary-200: #BFDBFE;
--primary-300: #93C5FD;
--primary-400: #60A5FA;
--primary-500: #3B82F6;       /* اصلی */
--primary-600: #2563EB;       /* hover */
--primary-700: #1D4ED8;       /* active */
--primary-800: #1E40AF;
--primary-900: #1E3A8A;
```

### Secondary Colors (Cyan/Teal)
```css
--cyan-50: #ECFEFF;
--cyan-100: #CFFAFE;
--cyan-200: #A5F3FC;
--cyan-300: #67E8F9;
--cyan-400: #22D3EE;
--cyan-500: #06B6D4;          /* اصلی */
--cyan-600: #0891B2;
--cyan-700: #0E7490;
```

### Success (Green)
```css
--success-50: #F0FDF4;
--success-100: #DCFCE7;
--success-500: #10B981;       /* اصلی */
--success-600: #059669;
--success-700: #047857;
```

### Warning (Orange)
```css
--warning-50: #FFF7ED;
--warning-100: #FFEDD5;
--warning-500: #F59E0B;       /* اصلی */
--warning-600: #D97706;
```

### Error (Red)
```css
--error-50: #FEF2F2;
--error-100: #FEE2E2;
--error-500: #EF4444;         /* اصلی */
--error-600: #DC2626;
```

### Accent Colors
```css
--violet-500: #8B5CF6;
--violet-600: #7C3AED;
--emerald-500: #10B981;
--orange-500: #F97316;
```

### Status Colors (وضعیت خودرو)
```css
--status-entered: #8B5CF6;       /* بنفش */
--status-entered-bg: #F5F3FF;
--status-entered-border: #DDD6FE;

--status-assigned: #3B82F6;      /* آبی */
--status-assigned-bg: #EFF6FF;
--status-assigned-border: #BFDBFE;

--status-inprogress: #F59E0B;    /* نارنجی */
--status-inprogress-bg: #FFF7ED;
--status-inprogress-border: #FED7AA;

--status-ready: #10B981;         /* سبز */
--status-ready-bg: #F0FDF4;
--status-ready-border: #BBF7D0;

--status-completed: #06B6D4;     /* فیروزه‌ای */
--status-completed-bg: #ECFEFF;
--status-completed-border: #A5F3FC;

--status-cancelled: #EF4444;     /* قرمز */
--status-cancelled-bg: #FEF2F2;
--status-cancelled-border: #FECACA;
```

### Gradients (Soft & Premium)
```css
--gradient-primary: linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%);
--gradient-premium: linear-gradient(135deg, #EFF6FF 0%, #ECFEFF 100%);
--gradient-violet: linear-gradient(135deg, #8B5CF6 0%, #3B82F6 100%);
--gradient-success: linear-gradient(135deg, #10B981 0%, #06B6D4 100%);
--gradient-warm: linear-gradient(135deg, #F59E0B 0%, #F97316 100%);
```

---

## 3️⃣ تایپوگرافی

### Font Family
```css
/* فارسی */
--font-primary: 'Vazirmatn', 'IRANSans', 'Tahoma', sans-serif;

/* انگلیسی/UI */
--font-secondary: 'Inter', 'SF Pro Display', -apple-system, system-ui, sans-serif;

/* اعداد مالی */
--font-mono: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
```

### Font Sizes
```css
--text-xs: 0.75rem;      /* 12px - Labels کوچک */
--text-sm: 0.875rem;     /* 14px - متن ثانویه */
--text-base: 1rem;       /* 16px - متن اصلی */
--text-lg: 1.125rem;     /* 18px - Subheadings */
--tex
حتماً؛ این نسخه را **تم لایت** و **production-ready** می‌دهم.

# Design Tokens — Light Theme
```css
:root {
  --bg-main: #F8FAFC;
  --bg-surface: #FFFFFF;
  --bg-subtle: #F1F5F9;

  --text-primary: #0F172A;
  --text-secondary: #475569;
  --text-muted: #64748B;
  --text-inverse: #FFFFFF;

  --border-light: #E2E8F0;
  --border-medium: #CBD5E1;
  --border-focus: #3B82F6;

  --primary: #3B82F6;
  --primary-hover: #2563EB;
  --primary-soft: #DBEAFE;

  --cyan: #06B6D4;
  --success: #10B981;
  --warning: #F59E0B;
  --danger: #EF4444;
  --violet: #8B5CF6;

  --status-entered: #8B5CF6;
  --status-assigned: #3B82F6;
  --status-inprogress: #F59E0B;
  --status-ready: #10B981;
  --status-completed: #06B6D4;
  --status-cancelled: #EF4444;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;

  --shadow-xs: 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow-sm: 0 4px 12px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 10px 30px rgba(15, 23, 42, 0.08);
  --shadow-lg: 0 20px 50px rgba(15, 23, 42, 0.12);
  --shadow-glow: 0 10px 25px rgba(59, 130, 246, 0.18);

  --gradient-primary: linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%);
  --gradient-soft: linear-gradient(135deg, #EFF6FF 0%, #ECFEFF 100%);

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;

  --text-xs: 12px;
  --text-sm: 14px;
  --text-base: 16px;
  --text-lg: 18px;
  --text-xl: 20px;
  --text-2xl: 24px;
  --text-3xl: 30px;

  --font-primary: 'Vazirmatn', sans-serif;
  --font-secondary: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```

# Visual Direction
- پس‌زمینه روشن و تمیز
- کارت‌های سفید با سایه نرم
- اکشن‌های اصلی با آبی/فیروزه‌ای
- وضعیت‌ها با badgeهای soft
- حس premium با gradientهای خیلی کنترل‌شده، نه شلوغ

# Component Rules

## Button
```css
.btn-primary {
  background: var(--gradient-primary);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-glow);
}

.btn-secondary {
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
}

.btn-ghost {
  background: transparent;
  color: var(--primary);
  border: 1px solid transparent;
}
```

## Input
```css
.input {
  background: var(--bg-surface);
  border: 1px solid var(--border-light);
  color: var(--text-primary);
  border-radius: 14px;
}

.input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}
```

## Card
```css
.card {
  background: var(--bg-surface);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 20px;
  box-shadow: var(--shadow-md);
}
```

## Modal
- سفید خالص
- سایه عمیق ولی نرم
- backdrop روشن با blur کم
- هدر و فوتر ثابت

## Table
- header روشن
- hover آبی خیلی خیلی ملایم
- borderهای تمیز
- اعداد مالی با `mono`

## Badge
- متن پررنگ
- پس‌زمینه pastel
- border همرنگ ملایم
- شکل pill

# Status Badge Map
- Entered → بنفش روشن
- Assigned → آبی روشن
- InProgress → نارنجی روشن
- Ready → سبز روشن
- Completed → فیروزه‌ای روشن
- Cancelled → قرمز روشن

# Page Feeling

## Vehicle Intake
- سفید، تمیز، سریع
- بخش AI scan با قاب روشن و subtle glow
- فرم دستی بسیار خوانا

## Operator Board
- کارت‌های سفید با hierarchy قوی
- پلاک بزرگ
- badge وضعیت کاملاً واضح
- CTAهای محدود و مشخص

## Services Modal
- سه بخش:
  - خدمات
  - نیروی اجرا
  - خلاصه مالی
- summary سمت چپ/بالا برجسته‌تر

## Reports
- KPI cards بالا
- فیلترها داخل toolbar سفید
- جدول بسیار تمیز و مالی‌محور

# Motion
- hover: $160ms$
- modal open: $220ms$
- easing: `ease-out`
- بدون انیمیشن‌های سنگین

# Brand Personality
این تم باید بگوید:
- تمیز
- دقیق
- حرفه‌ای
- مدرن
- خوش‌حس
- قابل اعتماد
