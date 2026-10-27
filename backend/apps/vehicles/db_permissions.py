"""Table-scoped account grants; emits no credentials and executes no DDL."""
from django.apps import apps
from .mysql_guards import CAP_TABLE, RUN_TABLE, CUSTOMER_TABLE, VEHICLE_TABLE, account, identifier


def statements(database, user, host, *, maintenance=False):
    account(f'{user}@{host}')
    db = identifier(database)
    principal = f"'{user}'@'{host}'"
    def grant(privileges, table):
        return f'GRANT {privileges} ON {db}.{identifier(table)} TO {principal};'
    if maintenance:
        from .customer_tenant_repair import tracked_models
        result = [grant('SELECT', m._meta.db_table) for m in tracked_models()]
        result += [grant('SELECT, INSERT, UPDATE', RUN_TABLE), grant('SELECT, INSERT', CAP_TABLE),
                   grant('INSERT, UPDATE (yearly_score, score_year, updated_at)', CUSTOMER_TABLE),
                   grant('UPDATE (customer_id)', VEHICLE_TABLE)]
        return result
    tables = {m._meta.db_table for m in apps.get_models(include_auto_created=True) if m._meta.managed and not m._meta.proxy}
    return [grant('SELECT, INSERT, UPDATE, DELETE', table) for table in sorted(tables - {CAP_TABLE, RUN_TABLE})] + [grant('SELECT', 'django_migrations')]
