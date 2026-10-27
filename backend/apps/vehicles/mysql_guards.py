"""Versioned MySQL 8.4 guards. Migration code; keep v1 bodies immutable."""
import hashlib
import re
from contextlib import contextmanager

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

CAP_TABLE = 'vehicles_customertenantauthorization'
RUN_TABLE = 'vehicles_customertenantrepairrun'
VEHICLE_TABLE = 'vehicles_vehicleentry'
CUSTOMER_TABLE = 'vehicles_customerprofile'
ERROR = 'Customer ownership validation failed.'
PREFIX = 'cw_customer_guard_v1_'


def identifier(value):
    if not re.fullmatch(r'[A-Za-z0-9_]+', value):
        raise ImproperlyConfigured('Unsafe database guard identifier.')
    return f'`{value}`'


def definer_user(database):
    return 'cw_guard_' + hashlib.sha256(database.encode()).hexdigest()[:16]


def account(value):
    try:
        user, host = value.split('@')
    except (ValueError, AttributeError):
        raise ImproperlyConfigured('Configure CUSTOMER_TENANT_GUARD_APP_ACCOUNT as user@host.') from None
    if not re.fullmatch(r'[A-Za-z0-9_]+', user) or not re.fullmatch(r'[A-Za-z0-9_.%:-]+', host):
        raise ImproperlyConfigured('Unsafe database account identifier.')
    return user, host


def grant_rows(cursor, principal=None):
    if principal:
        cursor.execute('SHOW GRANTS FOR %s@%s', principal)
    else:
        cursor.execute('SHOW GRANTS')
    return [row[0] for row in cursor.fetchall()]


def assert_restricted_grants(grants, database, *, maintenance=False, cursor=None):
    """Fail closed on roles, wildcard grants, DDL, EXECUTE and grant delegation."""
    base_tables = None
    for statement in grants:
        if re.fullmatch(r'GRANT USAGE ON \*\.\* TO .+', statement) and 'WITH GRANT OPTION' not in statement:
            continue
        match = re.match(r'GRANT (.+) ON `([^`]+)`\.`([^`]+)` TO ', statement)
        if not match or 'WITH GRANT OPTION' in statement or match[2] != database:
            raise ImproperlyConfigured('Database account has unsafe global/schema/role privileges.')
        privileges, table = match[1], match[3]
        if cursor is not None:
            if base_tables is None:
                cursor.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_TYPE=%s', [database, 'BASE TABLE'])
                base_tables = {row[0] for row in cursor.fetchall()}
            if table not in base_tables:
                raise ImproperlyConfigured('View/nonexistent-table grants require independent security review.')
        # Column grants contain commas inside parentheses.
        words = re.findall(r'(?:^|, )([A-Z ]+)(?: \([^)]*\))?(?=, |$)', privileges)
        if not words or any(word not in {'SELECT', 'INSERT', 'UPDATE', 'DELETE'} for word in words):
            raise ImproperlyConfigured('Database account has unsafe table privileges.')
        if not maintenance and table in {CAP_TABLE, RUN_TABLE}:
            raise ImproperlyConfigured('Application account can access maintenance authorization/audit data.')
        if maintenance:
            from .customer_tenant_repair import tracked_models
            allowed_select = {m._meta.db_table for m in tracked_models()} | {CAP_TABLE, RUN_TABLE}
            if table not in allowed_select or 'DELETE' in words:
                raise ImproperlyConfigured('Maintenance account has unnecessary privileges.')
            if table == CAP_TABLE and any(word not in {'SELECT', 'INSERT'} for word in words):
                raise ImproperlyConfigured('Maintenance cannot modify or reuse authorization records.')
            if table not in {CAP_TABLE, RUN_TABLE, CUSTOMER_TABLE, VEHICLE_TABLE} and words != ['SELECT']:
                raise ImproperlyConfigured('Maintenance can modify financial/history data.')
            if table == VEHICLE_TABLE and any(word not in {'SELECT', 'UPDATE'} for word in words):
                raise ImproperlyConfigured('Maintenance cannot insert/delete vehicles.')
            if table == VEHICLE_TABLE and 'UPDATE' in words and not re.search(r'UPDATE \(`customer_id`\)', privileges):
                raise ImproperlyConfigured('Maintenance vehicle updates must be column scoped.')
            if table == CUSTOMER_TABLE and 'UPDATE' in words and not re.search(r'UPDATE \(`score_year`, `updated_at`, `yearly_score`\)', privileges):
                # MySQL sorts column names lexicographically in SHOW GRANTS.
                raise ImproperlyConfigured('Maintenance customer updates must be score scoped.')


def require_maintenance(connection):
    if connection.vendor == 'mysql':
        with connection.cursor() as cursor:
            assert_restricted_grants(grant_rows(cursor), connection.settings_dict['NAME'], maintenance=True, cursor=cursor)
            # Prove authorization capability without issuing any permission.
            cursor.execute(f'SELECT id FROM {identifier(CAP_TABLE)} WHERE 1=0')


def bodies():
    validate = f'''
        SET guard_owner = NULL;
        SELECT tenant_id INTO guard_owner FROM {identifier(CUSTOMER_TABLE)}
        WHERE id = NEW.customer_id FOR SHARE;
        IF guard_owner IS NULL OR NEW.tenant_id IS NULL OR guard_owner <> NEW.tenant_id THEN
            {{invalid}}
        END IF;
    '''
    reject = f"SIGNAL SQLSTATE '45000' SET MYSQL_ERRNO=1644, MESSAGE_TEXT='{ERROR}';"
    declarations = 'DECLARE guard_owner BIGINT DEFAULT NULL; DECLARE guard_cap BIGINT DEFAULT NULL; DECLARE CONTINUE HANDLER FOR NOT FOUND SET guard_owner = NULL;'
    consume = f'''
        SET guard_cap = NULL;
        IF OLD.tenant_id <=> NEW.tenant_id THEN
            SELECT id INTO guard_cap FROM {identifier(CAP_TABLE)}
            WHERE connection_id = CONNECTION_ID() AND vehicle_id = OLD.id
              AND tenant_id <=> NEW.tenant_id
              AND from_customer_id <=> OLD.customer_id AND to_customer_id = NEW.customer_id
              AND consumed_at IS NULL AND expires_at > UTC_TIMESTAMP(6)
            ORDER BY id LIMIT 1 FOR UPDATE;
        END IF;
        IF guard_cap IS NULL THEN {reject} END IF;
        UPDATE {identifier(CAP_TABLE)} SET consumed_at = UTC_TIMESTAMP(6) WHERE id = guard_cap;
    '''
    return {
        PREFIX + 'customer_bu': (CUSTOMER_TABLE, 'UPDATE', f'BEGIN IF NOT (NEW.tenant_id <=> OLD.tenant_id) OR NOT (NEW.id <=> OLD.id) THEN {reject} END IF; END'),
        PREFIX + 'customer_bd': (CUSTOMER_TABLE, 'DELETE', f'BEGIN {reject} END'),
        PREFIX + 'vehicle_bi': (VEHICLE_TABLE, 'INSERT', f'BEGIN {declarations} IF NEW.customer_id IS NOT NULL THEN {validate.format(invalid=reject)} END IF; END'),
        PREFIX + 'vehicle_bu': (VEHICLE_TABLE, 'UPDATE', f'''BEGIN {declarations}
            IF NOT (NEW.id <=> OLD.id) OR NOT (NEW.tenant_id <=> OLD.tenant_id) THEN {reject} END IF;
            IF NOT (NEW.customer_id <=> OLD.customer_id) OR NOT (NEW.tenant_id <=> OLD.tenant_id) THEN
                IF NEW.customer_id IS NOT NULL THEN {validate.format(invalid=consume)} END IF;
            END IF;
        END'''),
    }


def normalize(sql):
    return ' '.join(sql.split())


def installed(cursor):
    cursor.execute('SELECT TRIGGER_NAME, EVENT_OBJECT_TABLE, EVENT_MANIPULATION, ACTION_STATEMENT, DEFINER, ACTION_TIMING FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()')
    return {row[0]: row[1:] for row in cursor.fetchall() if row[0].startswith(PREFIX)}


def expected_definer(database):
    return definer_user(database) + '@localhost'


def verify_existing(cursor, database):
    current = installed(cursor)
    definitions = bodies()
    if set(current) - set(definitions):
        raise ImproperlyConfigured('Unexpected reserved trigger name.')
    for name, (table, event, body) in definitions.items():
        if name in current:
            actual = current[name]
            if (actual[0], actual[1], normalize(actual[2]), actual[3], actual[4]) != (table, event, normalize(body), expected_definer(database), 'BEFORE'):
                raise ImproperlyConfigured('Guard trigger collision or altered definition; manual review required.')
    return current


def definer_grants(database):
    return {
        f'GRANT SELECT, TRIGGER ON {identifier(database)}.{identifier(CUSTOMER_TABLE)}',
        f'GRANT SELECT, TRIGGER ON {identifier(database)}.{identifier(VEHICLE_TABLE)}',
        f'GRANT SELECT, UPDATE (`consumed_at`) ON {identifier(database)}.{identifier(CAP_TABLE)}',
    }


def preflight(connection, cursor):
    if connection.mysql_version[:2] != (8, 4) or connection.mysql_is_mariadb:
        raise ImproperlyConfigured('Customer guards require MySQL 8.4/InnoDB.')
    database = connection.settings_dict['NAME']
    identifier(database)
    principal = account(getattr(settings, 'CUSTOMER_TENANT_GUARD_APP_ACCOUNT', None))
    assert_restricted_grants(grant_rows(cursor, principal), database, cursor=cursor)
    grants = ' '.join(grant_rows(cursor))
    if 'WITH GRANT OPTION' not in grants or not ('CREATE USER' in grants or 'ALL PRIVILEGES ON *.*' in grants):
        raise ImproperlyConfigured('Guard installation requires a dedicated provisioning/migration principal.')
    for table in (CAP_TABLE, RUN_TABLE, VEHICLE_TABLE, CUSTOMER_TABLE):
        cursor.execute('SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s', [table])
        row = cursor.fetchone()
        if not row or row[0] != 'InnoDB':
            raise ImproperlyConfigured('Guard tables must exist and use InnoDB.')
    expected_columns = {
        VEHICLE_TABLE: {'id': 'bigint', 'tenant_id': 'bigint', 'customer_id': 'bigint'},
        CUSTOMER_TABLE: {'id': 'bigint', 'tenant_id': 'bigint'},
        CAP_TABLE: {'id': 'bigint', 'connection_id': 'bigint', 'vehicle_id': 'bigint',
                    'tenant_id': 'bigint', 'from_customer_id': 'bigint', 'to_customer_id': 'bigint',
                    'repair_run_id': 'bigint', 'plan_hash': 'varchar',
                    'expires_at': 'datetime', 'consumed_at': 'datetime'},
    }
    for table, expected in expected_columns.items():
        cursor.execute('SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s', [table])
        actual = dict(cursor.fetchall())
        if any(actual.get(column) != data_type for column, data_type in expected.items()):
            raise ImproperlyConfigured('Guard column types do not match the reviewed schema.')
    for table, required in ((CUSTOMER_TABLE, ['tenant_id', 'phone']), (CAP_TABLE, ['connection_id', 'vehicle_id'])):
        cursor.execute('SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s ORDER BY INDEX_NAME, SEQ_IN_INDEX', [table])
        indexes = {}
        for name, column, non_unique in cursor.fetchall():
            indexes.setdefault((name, non_unique), []).append(column)
        if not any(columns == required and (table != CUSTOMER_TABLE or not non_unique)
                   for (_, non_unique), columns in indexes.items()):
            raise ImproperlyConfigured('Required customer/authorization index is missing.')
    # Column checks are read-only and precede any DDL/account modification.
    cursor.execute(f'SELECT id, tenant_id, customer_id FROM {identifier(VEHICLE_TABLE)} LIMIT 0')
    cursor.execute(f'SELECT id, tenant_id FROM {identifier(CUSTOMER_TABLE)} LIMIT 0')
    cursor.execute(f'SELECT connection_id, vehicle_id, tenant_id, from_customer_id, to_customer_id, expires_at, consumed_at FROM {identifier(CAP_TABLE)} LIMIT 0')
    verify_existing(cursor, database)
    cursor.execute('SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE() AND EVENT_OBJECT_TABLE IN (%s,%s) AND ACTION_TIMING=%s', [VEHICLE_TABLE, CUSTOMER_TABLE, 'BEFORE'])
    if any(row[0] not in bodies() for row in cursor.fetchall()):
        raise ImproperlyConfigured('Unreviewed BEFORE trigger can alter ownership; manual integration review required.')
    user = definer_user(database)
    cursor.execute('SELECT account_locked FROM mysql.user WHERE User=%s AND Host=%s', [user, 'localhost'])
    existing = cursor.fetchone()
    if existing and existing[0] != 'Y':
        raise ImproperlyConfigured('Guard definer account must be locked.')
    if existing:
        expected = definer_grants(database)
        for grant in grant_rows(cursor, (user, 'localhost')):
            if grant.startswith('GRANT USAGE ON *.* TO '):
                continue
            if grant.split(' TO ')[0] not in expected or 'WITH GRANT OPTION' in grant:
                raise ImproperlyConfigured('Guard definer has unexpected privileges.')
    return database, user, bool(existing)


@contextmanager
def ddl_window(connection):
    with connection.cursor() as cursor:
        database = connection.settings_dict['NAME']
        lock_name = 'cw_guard_install_' + hashlib.sha256(database.encode()).hexdigest()[:24]
        cursor.execute('SELECT GET_LOCK(%s, 10)', [lock_name])
        if cursor.fetchone()[0] != 1:
            raise ImproperlyConfigured('Another guard installer is active.')
        cursor.execute('SELECT @@session.lock_wait_timeout')
        old_timeout = cursor.fetchone()[0]
        cursor.execute('SET SESSION lock_wait_timeout=5')
        try:
            yield cursor
        finally:
            cursor.execute('SET SESSION lock_wait_timeout=%s', [old_timeout])
            cursor.execute('SELECT RELEASE_LOCK(%s)', [lock_name])


def install(connection):
    if connection.vendor != 'mysql':
        return  # SQLite development/test only; never a claim of SQL enforcement.
    with ddl_window(connection) as cursor:
        database, user, existed = preflight(connection, cursor)
        before = installed(cursor)
        created = []
        try:
            if not existed:
                cursor.execute('CREATE USER %s@%s ACCOUNT LOCK', [user, 'localhost'])
            principal = f"'{user}'@'localhost'"
            for table in (CUSTOMER_TABLE, VEHICLE_TABLE):
                cursor.execute(f'GRANT SELECT, TRIGGER ON {identifier(database)}.{identifier(table)} TO {principal}')
            cursor.execute(f'GRANT SELECT, UPDATE (consumed_at) ON {identifier(database)}.{identifier(CAP_TABLE)} TO {principal}')
            for name, (table, event, body) in bodies().items():
                if name not in before:
                    cursor.execute(f'CREATE DEFINER={principal} TRIGGER {identifier(name)} BEFORE {event} ON {identifier(table)} FOR EACH ROW {body}')
                    created.append(name)
            verify_existing(cursor, database)
        except Exception:
            # MySQL DDL auto-commits. Compensate only artifacts created by this
            # attempt; preserve pre-existing matching guards and every data row.
            for name in reversed(created):
                cursor.execute(f'DROP TRIGGER {identifier(name)}')
            if not existed:
                cursor.execute('DROP USER IF EXISTS %s@%s', [user, 'localhost'])
            raise


def uninstall(connection):
    if connection.vendor != 'mysql':
        return
    with ddl_window(connection) as cursor:
        database, _, _ = preflight(connection, cursor)
        current = verify_existing(cursor, database)
        removed = []
        try:
            for name in reversed(list(bodies())):
                if name in current:
                    cursor.execute(f'DROP TRIGGER {identifier(name)}')
                    removed.append(name)
            cursor.execute('DROP USER IF EXISTS %s@%s', [definer_user(database), 'localhost'])
        except Exception:
            principal = f"'{definer_user(database)}'@'localhost'"
            for name in removed:
                table, event, body = bodies()[name]
                cursor.execute(f'CREATE DEFINER={principal} TRIGGER {identifier(name)} BEFORE {event} ON {identifier(table)} FOR EACH ROW {body}')
            raise
        # Authorization and encrypted journal evidence are retained by 0028/0026.
