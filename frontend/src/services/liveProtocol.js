const compareNumericIds = (left, right) => {
  const a = String(left || '')
  const b = String(right || '')
  if (!/^\d+$/.test(a) || !/^\d+$/.test(b)) return 0
  if (a.length !== b.length) return a.length > b.length ? 1 : -1
  return a === b ? 0 : (a > b ? 1 : -1)
}

const boundedSet = (map, key, value, maximum) => {
  map.delete(key)
  map.set(key, value)
  while (map.size > maximum) map.delete(map.keys().next().value)
}

// Kept dependency-free so browser-ordering behavior can be verified by Node's
// built-in test runner as well as through the Vue application.
export function createLiveProtocolState ({ maxRecentIds = 1000 } = {}) {
  const maximum = Math.max(10, Number(maxRecentIds) || 1000)
  const seenIds = new Map()
  const entityWatermarks = new Map()
  let duplicateDrops = 0
  let outOfOrderDrops = 0

  const accept = (payload, fallbackId = '') => {
    const id = String(payload?.event_id || payload?.id || fallbackId || '')
    if (!id) return { accepted: true, id: '' }
    if (seenIds.has(id)) {
      duplicateDrops += 1
      return { accepted: false, id, reason: 'duplicate' }
    }

    const entity = String(payload?.entity || '')
    const entityId = String(payload?.entity_id || '')
    const entityKey = entity && entityId ? `${entity}:${entityId}` : ''
    const previousId = entityKey ? entityWatermarks.get(entityKey) : ''
    if (entityKey && previousId && compareNumericIds(id, previousId) <= 0) {
      boundedSet(seenIds, id, Date.now(), maximum)
      outOfOrderDrops += 1
      return { accepted: false, id, reason: 'out_of_order' }
    }

    boundedSet(seenIds, id, Date.now(), maximum)
    if (entityKey && /^\d+$/.test(id)) boundedSet(entityWatermarks, entityKey, id, maximum)
    return { accepted: true, id }
  }

  return {
    accept,
    diagnostics: () => ({
      recentEventIds: seenIds.size,
      trackedEntities: entityWatermarks.size,
      duplicateDrops,
      outOfOrderDrops
    })
  }
}

export { compareNumericIds }
