"""Immutable uploaded blobs: replacement creates a new name, never overwrites.

A snapshot pins the media directory with a shared flock. Physical deletion
uses nonblocking exclusive flock; a busy blob is left for later garbage
collection, so deleting a record never waits for a backup. No DB writes lock.
"""
import os
from contextlib import contextmanager
from django.conf import settings
from django.core.files.storage import FileSystemStorage


@contextmanager
def media_read_lock():
    import fcntl
    fd = os.open(settings.MEDIA_ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH)
        yield
    finally:
        os.close(fd)


class ImmutableMediaStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        kwargs.pop('allow_overwrite', None)
        super().__init__(*args, allow_overwrite=False, **kwargs)

    def _open(self, name, mode='rb'):
        if any(flag in mode for flag in 'wax+'):
            raise ValueError('immutable_media_write_requires_new_name')
        return super()._open(name, mode)

    def delete(self, name):
        import fcntl
        if not name:
            return
        fd = os.open(self.location, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                # Keeping an unreferenced immutable file is safer than deleting
                # bytes still needed by an in-flight MVCC snapshot.
                return
            super().delete(name)
        finally:
            os.close(fd)
