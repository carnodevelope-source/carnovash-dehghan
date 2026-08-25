import test from 'node:test'
import assert from 'node:assert/strict'
import { createLiveProtocolState } from '../src/services/liveProtocol.js'

test('drops a duplicate event and keeps bounded diagnostics', () => {
  const state = createLiveProtocolState({ maxRecentIds: 10 })
  assert.equal(state.accept({ id: '101', entity: 'vehicle', entity_id: '1' }).accepted, true)
  assert.equal(state.accept({ id: '101', entity: 'vehicle', entity_id: '1' }).reason, 'duplicate')
  assert.equal(state.diagnostics().duplicateDrops, 1)
})

test('drops a late event only when it would downgrade the same entity', () => {
  const state = createLiveProtocolState({ maxRecentIds: 10 })
  assert.equal(state.accept({ id: '104', entity: 'vehicle', entity_id: '1' }).accepted, true)
  assert.equal(state.accept({ id: '103', entity: 'vehicle', entity_id: '2' }).accepted, true)
  assert.equal(state.accept({ id: '102', entity: 'vehicle', entity_id: '1' }).reason, 'out_of_order')
  assert.equal(state.diagnostics().outOfOrderDrops, 1)
})

test('recent ID and entity maps cannot grow beyond their configured bound', () => {
  const state = createLiveProtocolState({ maxRecentIds: 10 })
  for (let id = 1; id <= 50; id += 1) {
    state.accept({ id: String(id), entity: 'vehicle', entity_id: String(id) })
  }
  assert.equal(state.diagnostics().recentEventIds, 10)
  assert.equal(state.diagnostics().trackedEntities, 10)
})
