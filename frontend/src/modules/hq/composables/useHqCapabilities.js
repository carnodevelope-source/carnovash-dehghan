import { computed } from 'vue'
import { useAuthStore } from '../../../store/auth.store'

export function useHqCapabilities(capabilitiesFromApi = null) {
  const authStore = useAuthStore()

  const role = computed(() => {
    if (authStore.isHqAdmin) return 'hq_admin'
    if (authStore.isHqFinance) return 'hq_finance'
    if (authStore.isHqProjectManager) return 'hq_project_manager'
    return 'hq_support'
  })

  const apiCaps = computed(() => capabilitiesFromApi?.value || capabilitiesFromApi || {})

  const caps = computed(() => {
    const fromApi = apiCaps.value || {}
    if (fromApi.role) return fromApi

    if (role.value === 'hq_admin') {
      return {
        role: 'hq_admin',
        see_all_projects: true,
        see_financial: true,
        see_holding_profit: true,
        see_costs: true,
        mutate_status: true,
        register_payment: true,
        export: true,
        bulk: true,
        technical_settings: true
      }
    }
    if (role.value === 'hq_finance') {
      return {
        role: 'hq_finance',
        see_all_projects: true,
        see_financial: true,
        see_holding_profit: true,
        see_costs: true,
        mutate_status: false,
        register_payment: true,
        export: true,
        bulk: false,
        technical_settings: false
      }
    }
    if (role.value === 'hq_project_manager') {
      return {
        role: 'hq_project_manager',
        see_all_projects: false,
        see_financial: true,
        see_holding_profit: false,
        see_costs: false,
        mutate_status: true,
        register_payment: false,
        export: true,
        bulk: true,
        technical_settings: false
      }
    }
    return {
      role: 'hq_support',
      see_all_projects: true,
      see_financial: false,
      see_holding_profit: false,
      see_costs: false,
      mutate_status: false,
      register_payment: false,
      export: false,
      bulk: false,
      technical_settings: false
    }
  })

  const canSeeReports = computed(() => authStore.isHqAdmin || authStore.isHqFinance)
  const canSeeServices = computed(() => authStore.isHq)

  return {
    role,
    caps,
    canSeeReports,
    canSeeServices,
    seeFinancial: computed(() => Boolean(caps.value.see_financial)),
    seeHoldingProfit: computed(() => Boolean(caps.value.see_holding_profit)),
    canMutateStatus: computed(() => Boolean(caps.value.mutate_status)),
    canRegisterPayment: computed(() => Boolean(caps.value.register_payment)),
    canExport: computed(() => Boolean(caps.value.export)),
    canBulk: computed(() => Boolean(caps.value.bulk)),
    isAdmin: computed(() => role.value === 'hq_admin')
  }
}
