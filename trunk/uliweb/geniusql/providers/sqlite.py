import datetime
import os
import sys
import time

import geniusql
from geniusql import adapters, dbtypes, conns, deparse, errors, providers, sqlwriters, typerefs
from geniusql import isolation as _isolation

try:
    # Use _sqlite3 directly to avoid all of the DB-API overhead.
    # This assumes the one built into Python 2.5+
    import _sqlite3 as _sqlite
    _version = providers.Version(_sqlite.sqlite_version)
except ImportError:
    # Use _sqlite directly to avoid all of the DB-API overhead.
    # This will import the "old API for SQLite 3.x",
    # using e.g. pysqlite 1.1.7
    try:
        # Is the single module on the python path?
        import _sqlite
    except ImportError:
        # Try pysqlite2
        from pysqlite2 import _sqlite
    _version = _sqlite.sqlite_version
    if callable(_version):
        # Newer versions of pysqlite have a string instead of a function.
        _version = _version()
    _version = providers.Version(_version)

_driver_version = providers.Version(getattr(_sqlite, "version", "1"))
if _driver_version >= 2:
    _cursor_required = True
    _fetchall_required = True
    _lastrowid_support = True
else:
    _cursor_required = True
    _fetchall_required = True
    _lastrowid_support = True

# ESCAPE keyword was added Nov 2004, 1 month after 3.0.8 release.
_escape_support = (_version > providers.Version([3, 0, 8]))
if not _escape_support:
    _escape_warning = ("Version %s of sqlite does not support "
                       "wildcard literals." % _version)
    errors.warn(_escape_warning)

_add_column_support = (_version >= providers.Version([3, 2, 0]))
_rename_table_support = (_version >= providers.Version([3, 1, 0]))
_autoincrement_support = (_version >= providers.Version([3, 1, 0]))
_cast_support = (_version >= providers.Version([3, 2, 3]))
_trim_support = (_version >= providers.Version([3, 3, 14]))

# ------------------------------ Adapters ------------------------------ #


def DATEADD(d, days):
    """Return the SQL to add a number of days to a date."""
    return "date(%s, '%s days')" % (d, days)

def DATEDIFF(d1, d2):
    """Return the SQL to subtract one date from another."""
    # "The julianday() function returns the number of days since
    # noon in Greenwich on November 24, 4714 B.C. The julian day
    # number is the preferred internal representation of dates."
    return "((julianday(%s) * 86400) - (julianday(%s) * 86400))" % (d1, d2)

def DATETIMEADD(dt, td):
    """Return the SQL to add a timedelta to a datetime."""
    return "datetime(%s, '%s days', '%s seconds')" % (dt, td.days, td.seconds)

def DATETIMEDIFF(d1, d2):
    """Return the SQL to subtract one datetime from another."""
    return "((julianday(%s) * 86400) - (julianday(%s) * 86400))" % (d1, d2)


class SQLite_datetime_to_TEXT(adapters.datetime_to_SQL92TIMESTAMP):
    
    def binary_op(self, op1, op, sqlop, op2):
        if op2.pytype is datetime.datetime:
            if op == "-":
                return DATETIMEDIFF(op1.sql, op2.sql)
        elif op2.pytype is datetime.timedelta:
            if op == "+":
                return DATETIMEADD(op1.sql, op2.value)
            elif op == "-":
                return DATETIMEADD(op1.sql, -op2.value)
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))

class SQLite_date_to_TEXT(adapters.date_to_SQL92DATE):
    
    def binary_op(self, op1, op, sqlop, op2):
        if op2.pytype is datetime.date:
            if op == "-":
                return DATEDIFF(op1.sql, op2.sql)
        elif op2.pytype is datetime.timedelta:
            if op == "+":
                return DATEADD(op1.sql, op2.value.days)
            elif op == "-":
                return DATEADD(op1.sql, -op2.value.days)
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))

class SQLite_timedelta_to_TEXT(adapters.timedelta_to_SQL92DECIMAL):
    
    def binary_op(self, op1, op, sqlop, op2):
        if op2.pytype is datetime.timedelta:
            return "(%s %s %s)" % (op1.sql, op, op2.sql)
        else:
            if op == "+":
                if op2.pytype is datetime.date:
                    return DATEADD(op2.sql, op1.value.days)
                elif op2.pytype is datetime.datetime:
                    return DATETIMEADD(op2.sql, op1.value)
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


class SQLite_str_to_TEXT(adapters.str_to_SQL92VARCHAR):
    # C-style backslash escapes are not supported.
    # See http://www.sqlite.org/lang_expr.html
    escapes = [("'", "''")]

class SQLite_unicode_to_TEXT(adapters.unicode_to_SQL92VARCHAR):
    # C-style backslash escapes are not supported.
    # See http://www.sqlite.org/lang_expr.html
    escapes = [("'", "''")]

class SQLite_Pickler(adapters.Pickler):
    # C-style backslash escapes are not supported.
    # See http://www.sqlite.org/lang_expr.html
    escapes = [("'", "''")]


# --------------------------- Database Types --------------------------- #


class INTEGER(dbtypes.SQL92INTEGER):
    _bytes = max_bytes = 2 ** 30

class TEXT(dbtypes.TEXT):
    # "A single row can hold up to 2 ** 30 bytes of data
    #   in the current implementation."
    _bytes = max_bytes = 2 ** 30
    synonyms = ['NUMERIC']
    
    default_adapters = dbtypes.TEXT.default_adapters.copy()
    default_adapters.update({str: SQLite_str_to_TEXT(),
                             unicode: SQLite_unicode_to_TEXT(),
                             datetime.datetime: SQLite_datetime_to_TEXT(),
                             datetime.date: SQLite_date_to_TEXT(),
                             datetime.timedelta: SQLite_timedelta_to_TEXT(),
                             None: SQLite_Pickler(),
                             })


class REAL(dbtypes.SQL92DOUBLE):
    pass

class NUMERIC(dbtypes.SQL92DECIMAL):
    # numeric precision is in decimal digits.
    #
    # SQLite uses 64-bit floats for all numbers;
    # 53 of those bits are significant; 2 ** 53 = 9007199254740992L
    # = almost-but-not-quite-16 decimal digits = 15 decimal digits.
    # Use one digit for the sign, and you've got 14 decimal digits.
    _precision = max_precision = 14
    scale = 14
    max_scale = 14

class NONE(dbtypes.DatabaseType):
    pass


class SQLiteTypeSet(dbtypes.DatabaseTypeSet):
    """For a column and Python type, return a database type.
    
    From http://www.sqlite.org/datatype3.html:
        
        "The type affinity of a column is determined by the declared
        type of the column, according to the following rules:
        1. If the datatype contains the string "INT" then it is
           assigned INTEGER affinity.
        2. If the datatype of the column contains any of the strings
           "CHAR", "CLOB", or "TEXT" then that column has TEXT affinity.
           Notice that the type VARCHAR contains the string "CHAR" and
           is thus assigned TEXT affinity.
        3. If the datatype for a column contains the string "BLOB" or
           if no datatype is specified then the column has affinity NONE.
        4. If the datatype for a column contains any of the strings
           "REAL", "FLOA", or "DOUB" then the column has REAL affinity.
        5. Otherwise, the affinity is NUMERIC."
    """
    
    known_types = {
        'int': [INTEGER],
        'float': [REAL],
        
        # &^%$#@! SQLite tries to convert NUMERIC values to REAL, so e.g.
        # INSERT INTO x VALUES 1111.1111 will result in 1111.1111000000001
        # Therefore, we must *always* use TEXT.
        # See "Manifest Typing" in the SQLite docs.
        'numeric': [],
        
        'varchar': [TEXT],
        'bool': [INTEGER],
        'datetime': [TEXT],
        'date': [TEXT],
        'time': [TEXT],
        'timedelta': [],
        'other': [],
        }
    
    # These are not adapter.push(bool) (which are used on one side of 
    # a comparison). Instead, these are used when the whole (sub)expression
    # is True or False, e.g. "WHERE TRUE", or "WHERE TRUE and 'a'.'b' = 3".
    expr_true = "1"
    expr_false = "0"



class SQLiteDeparser(deparse.SQLDeparser):
    
    like_escapes = [("%", "\%"), ("_", "\_")]
    
    def attr_startswith(self, tos, arg):
        if _escape_support:
            return self.get_expr(tos.sql + " LIKE '" +
                                 self.escape_like(arg.sql) +
                                 r"%' ESCAPE '\'", bool)
        else:
            if "%" in arg.sql or "_" in arg.sql:
                raise ValueError(_escape_warning)
            else:
                return self.get_expr(tos.sql + " LIKE '" +
                                     arg.sql.strip(r"'\"") + "%'", bool)
    
    def attr_endswith(self, tos, arg):
        if _escape_support:
            return self.get_expr(tos.sql + " LIKE '%" +
                                 self.escape_like(arg.sql) +
                                 r"' ESCAPE '\'", bool)
        else:
            if "%" in arg.sql or "_" in arg.sql:
                raise ValueError(_escape_warning)
            else:
                return self.get_expr(tos.sql + " LIKE '%" +
                                     arg.sql.strip(r"'\"") + "'", bool)
    
    def containedby(self, op1, op2):
        if op1.value is not None:
            # Looking for text in a field. Use Like (reverse terms).
            if _escape_support:
                return self.get_expr(op2.sql + " LIKE '%" +
                                     self.escape_like(op1.sql) +
                                     r"%' ESCAPE '\'", bool)
            else:
                if "%" in op1.sql or "_" in op1.sql:
                    raise ValueError(_escape_warning)
                else:
                    return self.get_expr(op2.sql + " LIKE '%" +
                                         op1.sql.strip(r"'\"") + r"%'", bool)
        else:
            # Looking for field in (a, b, c)
            atoms = []
            for x in op2.value:
                adapter = op1.dbtype.default_adapter(type(x))
                atoms.append(adapter.push(x, op1.dbtype))
            return self.get_expr(op1.sql + " IN (" + ", ".join(atoms) + ")",
                                 bool)
    
    def builtins_icontainedby(self, op1, op2):
        if op1.value is not None:
            # Looking for text in a field. Use Like (reverse terms).
            if _escape_support:
                return self.get_expr("LOWER(" + op2.sql + ") LIKE '%" +
                                     self.escape_like(op1.sql).lower() +
                                     r"%' ESCAPE '\'", bool)
            else:
                if "%" in op1.sql or "_" in op1.sql:
                    raise ValueError(_escape_warning)
                else:
                    return self.get_expr("LOWER(" + op2.sql + ") LIKE '%" +
                                         op1.sql.strip("'\"").lower() +
                                         r"%'", bool)
        else:
            # Looking for field in (a, b, c).
            # Force all args to lowercase for case-insensitive comparison.
            atoms = []
            for x in op2.value:
                adapter = op1.dbtype.default_adapter(type(x))
                atoms.append(adapter.push(x.lower(), op1.dbtype))
            return self.get_expr("LOWER(%s) IN (%s)" %
                                 (op1.sql, ", ".join(atoms)), bool)
    
    def builtins_istartswith(self, x, y):
        if _escape_support:
            return self.get_expr("LOWER(" + x.sql + ") LIKE '" +
                                 self.escape_like(y.sql)
                                 + r"%' ESCAPE '\'", bool)
        else:
            if "%" in y.sql or "_" in y.sql:
                raise ValueError(_escape_warning)
            else:
                return self.get_expr("LOWER(" + x.sql + ") LIKE '" +
                                    y.sql.strip("'\"") + r"%'", bool)
    
    def builtins_iendswith(self, x, y):
        if _escape_support:
            return self.get_expr("LOWER(" + x.sql + ") LIKE '%" +
                                 self.escape_like(y.sql)
                                 + r"%' ESCAPE '\'", bool)
        else:
            if "%" in y.sql or "_" in y.sql:
                raise ValueError(_escape_warning)
            else:
                return self.get_expr("LOWER(" + x.sql + ") LIKE '%" +
                                     y.sql.strip("'\"") + r"%'", bool)
    
    def builtins_now(self):
        """Return a datetime.datetime for the current time in the local TZ."""
        # The 'localtime' modifier is not thread-safe.
        # Manually modify the time.
        neg, h, m = adapters.localtime_offset()
        sign = "+"
        if neg:
            sign = "-"
        e = ("datetime('now', '%s%s hours', '%s%s minutes')"
             % (sign, h, sign, m))
        return self.get_expr(e, datetime.datetime)
    
    def builtins_utcnow(self):
        return self.get_expr("datetime('now')", datetime.datetime)
    
    def builtins_today(self):
        # The 'localtime' modifier is not thread-safe.
        # Manually modify the time.
        neg, h, m = adapters.localtime_offset()
        sign = "+"
        if neg:
            sign = "-"
        e = ("date('now', '%s%s hours', '%s%s minutes')"
             % (sign, h, sign, m))
        return self.get_expr(e, datetime.date)
    
    def builtins_year(self, x):
        return self.get_expr("CAST(strftime('%Y', " + x.sql +
                             ") AS NUMERIC)", int)
    
    def builtins_month(self, x):
        return self.get_expr("CAST(strftime('%m', " + x.sql +
                             ") AS NUMERIC)", int)
    
    def builtins_day(self, x):
        return self.get_expr("CAST(strftime('%d', " + x.sql +
                             ") AS NUMERIC)", int)



class SQLiteTable(geniusql.Table):
    """A table in a database; a dict of Column objects.
    
    Values in this dict must be instances of Column (or a subclass of it).
    Keys should be consumer-friendly names for each Column value.
    
    name: the SQL name for this table (unquoted).
    qname: the SQL name for this table (quoted).
    schema: the schema for this table.
    created: whether or not this Table has a concrete implementation in the
        database. If False (the default), then changes to Table items can be
        made with impunity. If True, then appropriate ALTER TABLE commands
        are executed whenever a consumer adds or deletes items from the
        Table, or calls methods like 'rename'.
    indices: a dict-like IndexSet of Index objects.
    references: a dict of the form:
        {name: (near Column key, far Table key, far Column key)}.
    
    Various versions of SQLite have limited support for ALTER TABLE.
    When necessary, this class will compensate with the following process:
    
      1. Create a temp table which has the desired new schema.
      2. Copy the entire dataset from the original table to the temp table.
      3. Drop the original table.
      4. Re-create the original table with the desired new schema.
      5. Copy the entire dataset from the temp table to the re-created table.
      6. Drop the temporary table.
    
    Needless to say, this can take a LOT longer than most other stores.
    """
    
    def create(self, skip_indices=False):
        # Set table.created to True, which should "turn on"
        # any future ALTER TABLE statements.
        self.created = True
        
        fields = []
        pk = []
        autoincr_col = None
        for key, col in self.iteritems():
            fields.append(self.schema.columnclause(col))
            
            if col.autoincrement:
                # MUST create the sequence after the table is created,
                # or we get into a "no such table" loop inside execute.
                autoincr_col = (key, col)
            
            if col.key:
                pk.append(col.qname)
        
        if (autoincr_col is None) and pk:
            # Seems we can't have both an AUTOINCREMENT and another PK
            pk = ", PRIMARY KEY (%s)" % ", ".join(pk)
        else:
            pk = ""
        
        self.schema.db.execute_ddl('CREATE TABLE %s (%s%s);' %
                                   (self.qname, ", ".join(fields), pk))
        
        if autoincr_col:
            # Columns created using schema.column() can't make their own
            # sequence names because the tablename isn't available.
            # So we do it here if needed.
            key, col = autoincr_col
            if col.sequence_name is None:
                col.sequence_name = self.schema.sequence_name(self.name, key)
            self.schema.create_sequence(self, col)
        
        if not skip_indices:
            for index in self.indices.itervalues():
                self.schema.db.execute_ddl(
                    'CREATE INDEX %s ON %s (%s);' %
                    (index.qname, self.qname,
                     self.schema.db.quote(index.colname)))
    
    def _start_temp(self):
        """Convert self into a temporary table. Not thread-safe."""
        self.origname = self.name
        self.origqname = self.qname
        self.name = "temp_" + self.name
        self.qname = self.schema.db.quote(self.name)
    
    def _finish_temp(self, selfields=None):
        """Convert self from a temporary table. Not thread-safe."""
        # CREATE the temporary TABLE.
        self.create(skip_indices=True)
        
        tempqname = self.qname
        
        # Copy data from the original table to the temp table.
        if selfields is None:
            selfields = [c.qname for c in self.itervalues()]
        self.schema.db.execute_ddl("INSERT INTO %s SELECT %s FROM %s;" %
                                   (tempqname, ", ".join(selfields),
                                    self.origqname))
        
        # DROP the original TABLE.
        self.schema.db.execute_ddl('DROP TABLE %s;' % self.origqname)
        
        # CREATE the new TABLE. Note we do not skip indices here;
        # SQLite dropped the old ones when we dropped the original table.
        self.name = self.origname
        self.qname = self.origqname
        self.create()
        
        # Copy data from the temp table to the final table.
        # For some odd reason, using "SELECT *"
        # mixes up the fields (during rename, at least).
        selfields = ", ".join([c.qname for c in self.values()])
        self.schema.db.execute("INSERT INTO %s (%s) SELECT %s FROM %s;"
                               % (self.qname, selfields, selfields,
                                  tempqname))
        
        # DROP the temporary TABLE.
        self.schema.db.execute_ddl('DROP TABLE %s;' % tempqname)
    
    if not _add_column_support:
        def __setitem__(self, key, column):
            if not self.created:
                super(SQLiteTable, self).__setitem__(key, column)
                return
            
            if key in self:
                del self[key]
            
            self._start_temp()
            super(SQLiteTable, self).__setitem__(key, column)
            
            selfields = []
            for k, c in self.iteritems():
                qname = c.qname
                if k == key:
                    # This is a new column. Populate with NULL.
                    qname = "NULL AS %s" % qname
                selfields.append(qname)
            self._finish_temp(selfields)
    
    def __delitem__(self, key):
        if key in self.indices:
            del self.indices[key]
        
        if not self.created:
            dict.__delitem__(self, key)
            return
        
        column = self[key]
        if column.autoincrement:
            # This may or may not be a no-op, depending on the DB.
            self.schema.drop_sequence(column)
        
        self._start_temp()
        dict.__delitem__(self, key)
        self._finish_temp()
    
    def rename(self, oldkey, newkey):
        """Rename a Column."""
        oldcol = self[oldkey]
        oldname = oldcol.name
        newname = self.schema.column_name(self.name, newkey)
        
        if oldname != newname:
            self._start_temp()
            
            dict.__delitem__(self, oldkey)
            dict.__setitem__(self, newkey, oldcol)
            oldcol.name = newname
            oldcol.qname = self.schema.db.quote(newname)
            
            selfields = []
            for k, c in self.iteritems():
                qname = c.qname
                if k == newkey:
                    qname = "%s AS %s" % (self.schema.db.quote(oldname), qname)
                selfields.append(qname)
            self._finish_temp(selfields)
    
    def _grab_new_ids(self, idkeys, conn):
        if _lastrowid_support:
            new_id = conn.lastrowid
        else:
            new_id = conn.sqlite_last_insert_rowid()
        return {idkeys[0]: new_id}
    
    def set_primary(self):
        """Assert the PRIMARY KEY for this Table, using its Column.key values."""
        self._start_temp()
        self._finish_temp()
    
    def drop_primary(self):
        """Remove any PRIMARY KEY for this Table."""
        pk_cols = [col for col in self.itervalues() if col.key]
        self._start_temp()
        for col in pk_cols:
            col.key = False
        self._finish_temp()
        for col in pk_cols:
            col.key = True



class SQLiteSelectWriter(sqlwriters.SelectWriter):
    
    def _joinclause(self, join):
        on_clauses = []
        
        t1, t2 = join.table1, join.table2
        if isinstance(t1, geniusql.Join):
            name1, oc = self._joinclause(t1)
            on_clauses.extend(oc)
            tlist1 = iter(t1)
        else:
            # t1 is a Table class wrapper.
            name1 = self.joinname(t1)
            tlist1 = [t1]
        
        if isinstance(t2, geniusql.Join):
            name2, oc = self._joinclause(t2)
            on_clauses.extend(oc)
            tlist2 = iter(t2)
        else:
            # t2 is a Table class wrapper.
            name2 = self.joinname(t2)
            tlist2 = [t2]
        
        if join.leftbiased is None:
            j = "%s INNER JOIN %s" % (name1, name2)
        elif join.leftbiased is True:
            j = "%s LEFT JOIN %s" % (name1, name2)
        else:
            # My version (3.0.8) of SQLite says:
            # "RIGHT and FULL OUTER JOINs are not currently supported".
            j = "%s LEFT JOIN %s" % (name2, name1)
        
        # Find an association between the two halves.
        for A in tlist1:
            for B in tlist2:
                on = self.onclause(A, B, join.path)
                if on:
                    on_clauses.append(on)
                    return j, on_clauses
                
                on = self.onclause(B, A, join.path)
                if on:
                    on_clauses.append(on)
                    return j, on_clauses
        
        raise ReferenceError("No reference found between %s and %s."
                             % (name1, name2))
    
    def joinclause(self, join):
        # SQLite doesn't do nested JOINs, but instead applies
        # them in order. Therefore, we need a single ON-clause
        # at the end of the list of tables. For example:
        # "From a LEFT JOIN b LEFT JOIN c ON a.ID = b.ID AND b.Name = c.Name"
        joins, on_clauses = self._joinclause(join)
        return "%s ON %s" % (joins, " AND ".join(on_clauses))


class SQLiteConnectionManager(conns.ConnectionManager):
    
    default_isolation = "SERIALIZABLE"
    isolation_levels = ["SERIALIZABLE"]
    
    def __init__(self, db):
        self.transactions = {}
        self.db = db
        # Can't set up the factory until we have a schema.
    
    def _set_factory(self):
        if self.db.name == ":memory:":
            # "Multiple connections to ":memory:" within a single process
            # create a fresh database each time"
            # http://www.sqlite.org/cvstrac/wiki?p=InMemoryDatabase
            # So we need to give :memory: databases a SingleConnection.
            self._factory = conns.SingleConnection(self._get_conn, self._del_conn,
                                                   self.retry)
        elif not self.db.threadsafe:
            self._factory = conns.ConnectionPerThread(self._get_conn, self._del_conn,
                                                      self.retry)
        else:
            # Use the default behavior (pool)
            conns.ConnectionManager._set_factory(self)
    
    if _cursor_required:
        def _get_conn(self):
            # SQLite should create the DB if missing.
            # valid _sqlite3 kwargs: "database", "timeout", "detect_types",
            # "isolation_level", "check_same_thread", "factory",
            # "cached_statements".
            # Instead of "timeout", we re-use the old
            # deadlock_timeout code inside execute.
            conn = _sqlite.connect(database=self.db.name, check_same_thread=False)
            
            # None sets "autocommit mode" on. This turns off the silly
            # PySQLite behavior of trying to handle transactions for you
            # behind the scenes, and returns to the default SQLite behavior.
            conn.isolation_level = None
            
            conn.text_factory = str
            c = conn.cursor()
            if self.initial_sql:
                c.execute(self.initial_sql)
            return c
    else:
        def _get_conn(self):
            conn = _sqlite.connect(self.db.name, self.db.mode)
            if self.initial_sql:
                conn.execute(self.initial_sql)
            return conn
    
    def isolate(self, conn, isolation=None):
        """Set the isolation level of the given connection.
        
        If 'isolation' is None, our default_isolation will be used for new
        connections. Valid values for the 'isolation' argument may be native
        values for your particular database. However, it is recommended you
        pass items from the global 'levels' list instead; these will be
        automatically replaced with native values.
        
        For many databases, this must be executed after START TRANSACTION.
        """
        if isolation is None:
            isolation = self.default_isolation
        
        if isinstance(isolation, _isolation.IsolationLevel):
            # Map the given IsolationLevel object to a native value.
            # This base class uses the four ANSI names as native values.
            isolation = isolation.name
        
        if isolation not in self.isolation_levels:
            raise ValueError("IsolationLevel %r not allowed by %s. "
                             "Try one of %r instead."
                             % (isolation, self.__class__.__name__,
                                self.isolation_levels))
        
        # Nothing to do here, since we only allow one level.
        pass
    
    def _start_transaction(self, conn, isolation=None):
        """Start a transaction."""
        self.db.execute("BEGIN;", conn)
        self.isolate(conn, isolation)
    
    def rollback(self):
        """Roll back the current transaction."""
        key = self.id()
        if key in self.transactions:
            self.db.execute("ROLLBACK;", self.transactions[key])
            del self.transactions[key]
    
    def commit(self):
        """Commit the current transaction."""
        key = self.id()
        if key in self.transactions:
            self.db.execute("COMMIT;", self.transactions[key])
            del self.transactions[key]


class SQLiteSchema(geniusql.Schema):
    
    tableclass = SQLiteTable
    
    def _get_tables(self, conn=None):
        data, _ = self.db.fetch("SELECT name FROM sqlite_master "
                                "WHERE type = 'table' AND "
                                "name != 'sqlite_sequence';", conn)
        # Note that we set Table.created here, since these already exist in the DB.
        return [self.tableclass(row[0], self.db.quote(row[0]),
                                self, created=True)
                for row in data]
    
    def _get_table(self, tablename, conn=None):
        data, _ = self.db.fetch("SELECT name FROM sqlite_master WHERE name = "
                                "'%s' AND type = 'table';" % tablename, conn)
        # Note that we set Table.created here, since these already exist in the DB.
        for name, in data:
            if name == tablename:
                return self.tableclass(name, self.db.quote(name),
                                       self, created=True)
        raise errors.MappingError("Table %r not found." % tablename)
    
    def _get_columns(self, table, conn=None):
        # cid, name, type, notnull, dflt_value, pk
        data, _ = self.db.fetch("PRAGMA table_info(%s);" % table.qname,
                                conn=conn)
        
        cols = []
        for row in data:
            cid, name, dbtypename, notnull, default, pk = row
            dbtypename = dbtypename.split("(")[0].upper()
            dbtypetype = self.db.typeset.canonicalize(dbtypename)
            dbtype = dbtypetype()
            
            c = geniusql.Column(dbtype.default_pytype, dbtype,
                                default, key=bool(pk),
                                name=name, qname=self.db.quote(name))
            c.adapter = dbtype.default_adapter(c.pytype)
            
            # !@#$%^&. SQLite actually FORCES any "INTEGER PRIMARY KEY"
            # column to autoincrement when you insert NULL.
            # See http://sqlite.org/faq.html#q1.
            if dbtype is INTEGER and c.key:
                c.autoincrement = True
            
            cols.append(c)
        
        return cols
    
    def _get_indices(self, table, conn=None):
        data, _ = self.db.fetch(
            "SELECT name, tbl_name, sql FROM sqlite_master "
            "WHERE type = 'index' AND tbl_name = '%s';" % table.name, conn)
        
        indices = []
        for row in data:
            if row[2]:
                colname = row[2].split("(")[-1]
                i = geniusql.Index(row[0], self.db.quote(row[0]),
                                   row[1], colname[1:-2])
                indices.append(i)
        return indices
    
    def sequence_name(self, tablename, columnkey):
        "Return the SQL sequence name for the given table name and column key."
        # If you want to use a map from your ORM's property names
        # to DB sequence names, override this method (that's why
        # the tablename must be included in the args).
        return self.db.sql_name(tablename)
    
    def create_sequence(self, table, column):
        """Create a SEQUENCE for the given column."""
        if column.sequence_name is not None:
            # SQLite AUTOINCREMENT columns start at 1 by default.
            # Manhandle the special SQLITE_SEQUENCE table to include
            # the value of sequencer.initial - 1.
            prev = column.initial - 1
            data, coldefs = self.db.fetch(
                "SELECT * FROM SQLITE_SEQUENCE WHERE name = '%s';" %
                column.sequence_name)
            if data:
                self.db.execute(
                    "UPDATE SQLITE_SEQUENCE SET seq = %s WHERE name = '%s';" %
                    (prev, column.sequence_name))
            else:
                self.db.execute(
                    "INSERT INTO SQLITE_SEQUENCE (seq, name) VALUES (%s, '%s');" %
                    (prev, column.sequence_name))
    
    def drop_sequence(self, column):
        """Drop a SEQUENCE for the given column."""
        if column.sequence_name is not None:
            self.db.execute("DELETE FROM SQLITE_SEQUENCE WHERE name = '%s';"
                            % column.sequence_name)
    
    def columnclause(self, column):
        """Return a clause for the given column for CREATE or ALTER TABLE.
        
        This will be of the form:
            "name type [DEFAULT x | PRIMARY KEY AUTOINCREMENT]"
        """
        if column.autoincrement:
            # From http://www.sqlite.org/datatypes.html:
            # "One exception to the typelessness of SQLite is a column whose
            # type is INTEGER PRIMARY KEY. (And you must use "INTEGER" not
            # "INT". A column of type INT PRIMARY KEY is typeless just like
            # any other.) INTEGER PRIMARY KEY columns must contain a 32-bit
            # signed integer. Any attempt to insert non-integer data will
            # result in an error."
            coldef = "INTEGER PRIMARY KEY AUTOINCREMENT"
        else:
            coldef = column.dbtype.ddl()
            
            default = column.default or ""
            if not isinstance(default, str):
                default = column.adapter.push(default, column.dbtype)
            if default:
                coldef += " DEFAULT %s" % default
        return '%s %s' % (column.qname, coldef)
    
    def _rename(self, oldtable, newtable):
        if _rename_table_support:
            self.db.execute_ddl("ALTER TABLE %s RENAME TO %s" %
                                (oldtable.qname, newtable.qname))
        else:
            raise NotImplementedError
    
    def drop(self):
        """Drop this schema from the database."""
        if self.db.name == ':memory:':
            # Not much we can do, here. If we try to drop a table, we end
            # up stuck in "database schema has changed"-land forever.
            # Just assume for now we're going to drop the whole database.
            self.db.drop()
            self.db.create()
        else:
            # Must shut down all connections to avoid
            # "being accessed by other users" error.
            self.db.connections.shutdown()
            
            seen = {}
            for tkey, table in self.items():
                # We might have multiple keys pointing at the same table.
                if table.name not in seen:
                    del self[tkey]
                    seen[table.name] = None


class SQLiteDatabase(geniusql.Database):
    
    sql_name_max_length = 0
    
    deparser = SQLiteDeparser
    selectwriter = SQLiteSelectWriter
    typeset = SQLiteTypeSet()
    connectionmanager = SQLiteConnectionManager
    
    schemaclass = SQLiteSchema
    multischema = False
    
    pks_must_be_indexed = False
    
    # Based on SQLite FAQ: http://www.sqlite.org/faq.html#q8
    # Override as needed.
    threadsafe = ("win" in sys.platform)
    
    def __init__(self, **kwargs):
        kwargs['mode'] = int(kwargs.pop('mode', '0755'), 8)
        
        if kwargs['name'] != ':memory:':
            if not os.path.isabs(kwargs['name']):
                kwargs['name'] = os.path.join(os.getcwd(), kwargs['name'])
        
        geniusql.Database.__init__(self, **kwargs)
    
##    def _get_dbinfo(self, conn=None):
##        dbinfo = {}
##        for pragma in ('encoding', 'case_sensitive_like', 'locking_mode',
##                       'page_size', 'read_uncommitted'):
##            dbinfo[pragma] = self.get_pragma(pragma, conn)
##        return dbinfo
    
    def get_pragma(self, name, conn=None):
        data, _ = self.fetch("PRAGMA %s;" % name, conn=conn)
        return data[0][0]
    
    def create(self):
        self.connections._set_factory()
        self.connections.get()
    
    def drop(self):
        self.connections.shutdown()
        if self.name != ":memory:":
            # This should accept relative or absolute paths
            os.remove(self.name)
    
    def quote(self, name):
        """Return name, quoted for use in an SQL statement.
        
        From the SQLite docs:
            Keywords can be used as identifiers in three ways:
            'keyword'   Interpreted as a literal string if it occurs in a
                        legal string context, otherwise as an identifier.
            "keyword"   Interpreted as an identifier if it matches a known
                        identifier and occurs in a legal identifier context,
                        otherwise as a string.
            [keyword]   Always interpreted as an identifier.
        
        ...we'll use the third option (square brackets).
        """
        return "[" + name + "]"
    
    def is_timeout_error(self, exc):
        if not isinstance(exc, _sqlite.OperationalError):
            return False
        return exc.args[0] == 'database is locked'
    
    # If you get "OperationalError: ('database is locked',
    #   'Waited 60 seconds for deadlock to clear.', 'SOME SQL;')",
    # then you need to either increase the deadlock_timeout value
    # until you stop getting that error, redesign your SQL commands
    # to avoid deadlocks, or get an enterprise-class database.
    deadlock_timeout = 20
    
    def execute(self, sql, conn=None):
        """Return a native response for the given SQL."""
        try:
            if conn is None:
                conn = self.connections.get()
            if isinstance(sql, unicode):
                sql = sql.encode(self.encoding)
            self.log(sql)
            start = time.time()
            while True:
                try:
                    return conn.execute(sql)
                except (_sqlite.OperationalError, _sqlite.DatabaseError), x:
                    msg = x.args[0]
                    if ((msg.startswith("no such table") or
                         msg == "database schema has changed")):
                        if not self.connections.in_transaction():
                            # Bah. Shut down all connections and get a new one,
                            # since some previous connection changed the schema.
                            self.connections.shutdown()
                            conn = self.connections._factory()
                            continue
                    if self.is_timeout_error(x) and self.deadlock_timeout:
                        if time.time() - start < self.deadlock_timeout:
                            time.sleep(0.000001)
                            continue
                        else:
                            x.args += (("Waited %s seconds for deadlock to "
                                        "clear." % self.deadlock_timeout),)
                raise
        except Exception, x:
            x.args += (sql,)
            # Dereference the connection so that release() is called back.
            conn = None
            raise
    
    def fetch(self, sql, conn=None):
        """Return rowdata, columns(name, type) for the given sql.
        
        sql should be a SQL string.
        
        rowdata will be an iterable of iterables containing the result values.
        columns will be an iterable of (column name, data type) pairs.
        """
        if _fetchall_required:
            cursor = self.execute(sql, conn)
            data = cursor.fetchall()
            coldefs = [(c[0], c[1]) for c in cursor.description]
            return data, coldefs
        else:
            res = self.execute(sql, conn)
            return res.row_list, res.col_defs
    
    def version(self):
        return ("SQLite Version: %s\nPySQLite version: %s" %
                (_version, _driver_version))

