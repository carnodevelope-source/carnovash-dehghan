const item = (label, route) => ({ label, route })

const supportItem = item('پشتیبانی', '/support')

export const navigationByRole = {
  accountant: [
    {
      key: 'finance',
      label: 'مالی',
      items: [
        item('کیف پول', '/manager/wallet'),
        supportItem
      ]
    }
  ],
  admin: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        item('مدیریت خودروها', '/'),
        item('گزارشات', '/manager/reports'),
        item('تنظیمات', '/manager/settings'),
        item('کیف پول', '/manager/wallet'),
        supportItem
      ]
    }
  ],
  manager: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        item('مدیریت خودروها', '/'),
        item('گزارشات', '/manager/reports'),
        item('تنظیمات', '/manager/settings'),
        item('کیف پول', '/manager/wallet'),
        supportItem
      ]
    }
  ],
  owner: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        item('مدیریت خودروها', '/'),
        supportItem
      ]
    }
  ],
  operator: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        item('مدیریت خودروها', '/'),
        supportItem
      ]
    }
  ],
  worker: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        item('مدیریت خودروها', '/'),
        supportItem
      ]
    }
  ]
}

export const defaultRouteByRole = {
  accountant: '/manager/wallet',
  admin: '/',
  manager: '/',
  owner: '/',
  operator: '/',
  worker: '/'
}
