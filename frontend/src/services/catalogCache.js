import api from './api'

const CATALOG_TTL_MS = 90_000

const cache = {
  key: '',
  at: 0,
  services: null,
  workers: null,
  products: null
}

let inflight = null

const catalogKey = (plateType, tariffType) => `${plateType || 'car'}:${tariffType || 'type_1'}`

export const getCachedCatalog = (plateType, tariffType) => {
  const key = catalogKey(plateType, tariffType)
  if (
    cache.key === key
    && (Date.now() - cache.at) < CATALOG_TTL_MS
    && cache.services
    && cache.workers
    && cache.products
  ) {
    return cache
  }
  return null
}

export const loadOperatorCatalog = async ({ plateType = 'car', tariffType = 'type_1', silent = false, force = false } = {}) => {
  const key = catalogKey(plateType, tariffType)
  if (!force) {
    const cached = getCachedCatalog(plateType, tariffType)
    if (cached) return cached
  }
  if (inflight?.key === key) return inflight.promise

  const meta = { trackLoading: false, showErrorToast: silent ? false : undefined }
  const promise = Promise.all([
    api.get('/services/', { params: { plate_type: plateType, tariff_type: tariffType }, meta }),
    api.get('/workers/', { meta }),
    api.get('/products/', { meta })
  ]).then(([serviceResp, workerResp, productResp]) => {
    cache.key = key
    cache.at = Date.now()
    cache.services = serviceResp.data
    cache.workers = workerResp.data
    cache.products = productResp.data
    return cache
  }).finally(() => {
    if (inflight?.key === key) inflight = null
  })

  inflight = { key, promise }
  return promise
}

export const loadOperatorWorkers = async ({ silent = true } = {}) => {
  const meta = { trackLoading: false, showErrorToast: silent ? false : undefined }
  const { data } = await api.get('/workers/', { meta })
  cache.workers = data
  return data
}

export const prefetchOperatorCatalog = (plateType = 'car', tariffType = 'type_1') => {
  void loadOperatorCatalog({ plateType, tariffType, silent: true })
}

export const invalidateOperatorCatalog = () => {
  cache.key = ''
  cache.at = 0
  cache.services = null
  cache.workers = null
  cache.products = null
}
