const item = (label, route, iconName = '') => ({ label, route, iconName })

const supportItem = item('پشتیبانی', '/support', 'chat')

export const navigationByRole = {
  accountant: [
    {
      key: 'finance',
      label: 'مالی',
      items: [
        item('کیف پول', '/manager/wallet', 'wallet'),
        supportItem
      ]
    }
  ],
  admin: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        item('مدیریت خودروها', '/', 'home'),
        item('باشگاه مشتریان', '/manager/customer-club', 'users3'),
        item('گزارشات', '/manager/reports', 'graph'),
        item('ورود و خروج', '/manager/attendance', 'calendar'),
        item('تنظیمات', '/manager/settings', 'setting'),
        item('کیف پول', '/manager/wallet', 'wallet'),
        supportItem
      ]
    }
  ],
  manager: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        item('مدیریت خودروها', '/', 'home'),
        item('باشگاه مشتریان', '/manager/customer-club', 'users3'),
        item('گزارشات', '/manager/reports', 'graph'),
        item('ورود و خروج', '/manager/attendance', 'calendar'),
        item('تنظیمات', '/manager/settings', 'setting'),
        item('کیف پول', '/manager/wallet', 'wallet'),
        supportItem
      ]
    }
  ],
  owner: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        item('مدیریت خودروها', '/', 'home'),
        supportItem
      ]
    }
  ],
  operator: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        item('مدیریت خودروها', '/', 'home'),
        supportItem
      ]
    }
  ],
  worker: [
    {
      key: 'operations',
      label: 'عملیات',
      items: [
        item('مدیریت خودروها', '/', 'home'),
        supportItem
      ]
    }
  ]
}

export const navigationRouteMeta = Object.values(navigationByRole)
  .flatMap((groups) => groups || [])
  .flatMap((group) => group.items || [])
  .reduce((acc, navItem) => {
    acc[navItem.route] = navItem
    return acc
  }, {})

export const defaultRouteByRole = {
  accountant: '/manager/wallet',
  admin: '/',
  manager: '/',
  owner: '/',
  operator: '/',
  worker: '/'
}
