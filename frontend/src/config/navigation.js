export const navigationByRole = {
  accountant: [
    {
      key: 'accounting',
      label: 'حسابداری',
      items: [
        { label: 'انبار', route: '/accounting?tab=inventory' },
        { label: 'خرید', route: '/accounting?tab=purchases' },
        { label: 'فروش', route: '/accounting?tab=sales' },
        { label: 'سند حسابداری', route: '/accounting?tab=vouchers' }
      ]
    }
  ],
  admin: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        { label: 'مدیریت خودروها', route: '/' },
        { label: 'گزارشات', route: '/manager/reports' },
        { label: 'تنظیمات', route: '/manager/settings' },
        { label: 'حسابداری', route: '/accounting?tab=inventory' }
      ]
    }
  ],
  manager: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        { label: 'مدیریت خودروها', route: '/' },
        { label: 'گزارشات', route: '/manager/reports' },
        { label: 'تنظیمات', route: '/manager/settings' },
        { label: 'حسابداری', route: '/accounting?tab=inventory' }
      ]
    }
  ],
  owner: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        { label: 'مدیریت خودروها', route: '/' }
      ]
    }
  ],
  operator: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        { label: 'مدیریت خودروها', route: '/' }
      ]
    }
  ],
  worker: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        { label: 'مدیریت خودروها', route: '/' }
      ]
    }
  ]
}
