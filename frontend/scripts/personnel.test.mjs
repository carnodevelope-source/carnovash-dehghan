import test from 'node:test'
import assert from 'node:assert/strict'
import { filterPersonnel } from '../src/utils/personnel.mjs'

const workers = [
  { id: 1, full_name: 'رضا', role: 'operator', is_available: true },
  { id: 2, full_name: 'احمد', role: 'worker', is_available: true },
  { id: 3, full_name: 'بهرام', is_available: false },
  { id: 4, full_name: 'جواد', is_available: true, is_active: false }
]

test('active personnel are alphabetic regardless of role, without mutating the source', () => {
  assert.deepEqual(filterPersonnel(workers).map((w) => w.id), [2, 1])
  assert.deepEqual(workers.map((w) => w.id), [1, 2, 3, 4])
})

test('inactive personnel remain accessible separately and in all personnel', () => {
  assert.deepEqual(filterPersonnel(workers, 'inactive').map((w) => w.id), [3, 4])
  assert.deepEqual(filterPersonnel(workers, 'all').map((w) => w.id), [2, 3, 4, 1])
})

test('search normalizes Persian and Arabic letter variants', () => {
  assert.equal(filterPersonnel([{ id: 5, full_name: 'علي كريمي', is_available: true }], 'active', 'علی کریمی').length, 1)
})
