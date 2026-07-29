"""Feature flags for MariaDB versions shipped by XAMPP.

MariaDB 10.4 does not support INSERT ... RETURNING. Django 5.2 may still
attempt to use RETURNING, so we explicitly disable it in this local backend.
"""

from django.db.backends.mysql.features import DatabaseFeatures as BaseDatabaseFeatures


class DatabaseFeatures(BaseDatabaseFeatures):
    can_return_columns_from_insert = False
    can_return_rows_from_bulk_insert = False
