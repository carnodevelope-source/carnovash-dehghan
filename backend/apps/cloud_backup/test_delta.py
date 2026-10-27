from unittest import TestCase
from .delta import diff_fixture, apply_fixture


def row(pk, value):
    return {'model': 'vehicles.vehicleentry', 'pk': pk, 'fields': {'tenant': 3, 'value': value}}


class FixtureDeltaTests(TestCase):
    def test_insert_update_delete_and_unchanged(self):
        before = [row(1, 'old'), row(2, 'deleted'), row(3, 'unchanged')]
        after = [row(1, 'new'), row(3, 'unchanged'), row(4, 'added')]
        delta = diff_fixture(before, after)
        self.assertEqual(len(delta['upserts']), 2)
        self.assertEqual(delta['deletes'], [['vehicles.vehicleentry', '2']])
        self.assertEqual(apply_fixture(before, delta), after)

    def test_tampered_base_is_rejected(self):
        before = [row(1, 'old')]
        delta = diff_fixture(before, [row(1, 'new')])
        with self.assertRaisesRegex(ValueError, 'Base fixture mismatch'):
            apply_fixture([row(1, 'tampered')], delta)

    def test_tampered_result_is_rejected(self):
        before = [row(1, 'old')]
        delta = diff_fixture(before, [row(1, 'new')])
        delta['upserts'][0]['fields']['value'] = 'tampered'
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            apply_fixture(before, delta)

    def test_invalid_tombstone_is_rejected(self):
        before = [row(1, 'old')]
        delta = diff_fixture(before, [])
        delta['deletes'].append(['vehicles.vehicleentry', '1'])
        with self.assertRaisesRegex(ValueError, 'Conflicting tombstone'):
            apply_fixture(before, delta)

    def test_order_independent_input_and_duplicate_rejection(self):
        before = [row(10, 'x'), row(2, 'y')]
        delta = diff_fixture(before, before[::-1])
        self.assertEqual(delta['upserts'], [])
        self.assertEqual(delta['deletes'], [])
        with self.assertRaisesRegex(ValueError, 'Duplicate fixture identity'):
            diff_fixture(before + [row(10, 'duplicate')], before)
