const toPersianDigits = (value) => String(value).replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[digit])

export const CAR_SERVICE_TIER_KEYS = Object.freeze([
  'type_1',
  'type_2',
  'type_3',
  'type_4',
  'type_5',
  'type_6'
])

export const MOTORCYCLE_SERVICE_TIER_KEYS = Object.freeze([
  'type_1',
  'type_2',
  'type_3'
])

export const buildServiceTierOptions = (keys) => keys.map((key, index) => ({
  key,
  value: key,
  label: `تیپ ${toPersianDigits(index + 1)}`
}))

export const carServiceTierOptions = buildServiceTierOptions(CAR_SERVICE_TIER_KEYS)
export const motorcycleServiceTierOptions = buildServiceTierOptions(MOTORCYCLE_SERVICE_TIER_KEYS)

export const serviceTierKeysForPlate = (plateType = 'car') => (
  String(plateType || 'car').trim().toLowerCase() === 'motorcycle'
    ? MOTORCYCLE_SERVICE_TIER_KEYS
    : CAR_SERVICE_TIER_KEYS
)

export const serviceTierOptionsForPlate = (plateType = 'car') => (
  String(plateType || 'car').trim().toLowerCase() === 'motorcycle'
    ? motorcycleServiceTierOptions
    : carServiceTierOptions
)

export const defaultTariffType = 'type_1'

export const normalizeTariffType = (value, plateType = 'car') => {
  const normalized = String(value || defaultTariffType).trim().toLowerCase() || defaultTariffType
  const allowed = serviceTierKeysForPlate(plateType)
  return allowed.includes(normalized) ? normalized : defaultTariffType
}
