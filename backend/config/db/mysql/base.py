"""MySQL/MariaDB backend compatible with XAMPP MariaDB 10.4.

Django 5.1+ requires MariaDB 10.5+, but local XAMPP still ships 10.4.x.
This wrapper keeps the stock MySQL backend and only skips the hard version gate.
"""

from django.db.backends.mysql.base import DatabaseWrapper as BaseDatabaseWrapper


class DatabaseWrapper(BaseDatabaseWrapper):
    def check_database_version_supported(self):
        return
