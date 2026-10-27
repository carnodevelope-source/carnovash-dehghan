import hashlib
from unittest import TestCase
from .media_delta import apply_media, diff_media


def sha(data):
    return hashlib.sha256(data.encode()).hexdigest()


class MediaDeltaTests(TestCase):
    def test_add_modify_remove_and_unchanged(self):
        old = {'old.jpg': sha('old'), 'changed.jpg': sha('before'), 'same.jpg': sha('same')}
        new = {'changed.jpg': sha('after'), 'same.jpg': sha('same'), 'new.jpg': sha('new')}
        delta = diff_media(old, new)
        self.assertEqual(set(delta['upserts']), {'changed.jpg', 'new.jpg'})
        self.assertEqual(delta['deletes'], ['old.jpg'])
        self.assertEqual(apply_media(old, delta), new)

    def test_invalid_digest_and_unsafe_path(self):
        with self.assertRaises(ValueError):
            diff_media({}, {'../other-tenant.jpg': sha('x')})
        with self.assertRaises(ValueError):
            diff_media({}, {'photo.jpg': 'bad'})

    def test_unknown_delete_rejected(self):
        with self.assertRaises(ValueError):
            apply_media({}, {'upserts': {}, 'deletes': ['missing.jpg']})
