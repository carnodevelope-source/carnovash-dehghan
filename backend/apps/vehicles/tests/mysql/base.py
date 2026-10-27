"""Isolated test databases only: flush with admin TRUNCATE, keep guards active."""
from django.db.backends.mysql.base import DatabaseWrapper as MySQLWrapper
from django.db.backends.mysql.operations import DatabaseOperations as MySQLOperations


class DatabaseOperations(MySQLOperations):
    def sql_flush(self, style, tables, *, reset_sequences=False, allow_cascade=False):
        # DELETE is intentionally forbidden for customer history. The test DBA
        # may TRUNCATE disposable schemas; the ordinary account cannot do so.
        return super().sql_flush(style, tables, reset_sequences=True, allow_cascade=allow_cascade)


class DatabaseWrapper(MySQLWrapper):
    ops_class = DatabaseOperations
