"""
Uses the MySQLdb package at:
http://sourceforge.net/projects/mysql-python

From the MySQL manual:

"If the server SQL mode has ANSI_QUOTES enabled, string literals can be
quoted only with single quotes. A string quoted with double quotes will be
interpreted as an identifier."

So use single quotes throughout.
"""

# Use _mysql directly to avoid all of the DB-API overhead.
import _mysql
import datetime

import geniusql
from geniusql import adapters, dbtypes, conns, deparse, errors, providers, typerefs



# ------------------------------ Adapters ------------------------------ #


class MySQL_VARCHAR_Adapter(adapters.str_to_SQL92VARCHAR):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        if not isinstance(value, str):
            value = value.encode(dbtype.encoding)
        return "'" + _mysql.escape_string(value) + "'"


class MySQL_float_adapter(adapters.float_to_SQL92DOUBLE):
    
    def compare_op(self, op1, op, sqlop, op2):
        if op2.dbtype in (FLOAT, DOUBLE):
            # MySQL provides no reliable method to compare floats in SQL.
            # Raising TypeError will tell the SQL deparser to mark float
            # comparisons as imperfect (so they'll be done in Python).
            raise TypeError("MySQL cannot reliably compare floats: %s" % sql)
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


def DAY_SECOND(td):
    """Return "INTERVAL 'D H:M:S' DAY_SECOND" from the given timedelta."""
    # I figured DAY_SECOND would be best for avoiding
    # overflows, but I really don't know.
    h, m = divmod(td.seconds, 3600)
    m, s = divmod(m, 60)
    return "INTERVAL '%s %s:%s:%s' DAY_SECOND" % (td.days, h, m, s)


class MySQL_datetime_to_DATETIME(adapters.datetime_to_SQL92TIMESTAMP):
    
    def binary_op(self, op1, op, sqlop, op2):
        if op2.pytype is datetime.date:
            if op == "-":
                # Assume NUMERIC secs (default for datetime.timedelta)
                # The MySQL docs say, "TIMEDIFF() returns expr1 - expr2
                # expressed as a time value", but the "hours" component
                # can increase arbitrarily (e.g. "23165:38:16").
                return "TIME_TO_SEC(TIMEDIFF(%s, %s))" % (op1.sql, op2.sql)
        elif op2.pytype is datetime.timedelta:
            if op in ("-", "+"):
                return "(%s %s %s)" % (op1.sql, sqlop, DAY_SECOND(op2.value))
        elif op2.pytype is datetime.datetime:
            if op == "-":
                return ("((DATEDIFF(%s, %s) * 86400) + "
                        "TIME_TO_SEC(%s) - TIME_TO_SEC(%s))"
                        % (op1.sql, op2.sql, op1.sql, op2.sql))
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


class MySQL_date_to_DATE(adapters.date_to_SQL92DATE):
    
    def binary_op(self, op1, op, sqlop, op2):
        if op2.pytype is datetime.date:
            if op == "-":
                # Assume NUMERIC secs (default for datetime.timedelta)
                return "(DATEDIFF(%s, %s) * 86400)" % (op1.sql, op2.sql)
        elif op2.pytype is datetime.timedelta:
            if op in ("-", "+"):
                return "%s %s INTERVAL %s DAY" % (op1.sql, sqlop, op2.value.days)
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


class MySQL_timedelta_to_DECIMAL(adapters.timedelta_to_SQL92DECIMAL):
    
    def binary_op(self, op1, op, sqlop, op2):
        if op2.pytype is datetime.timedelta:
            return "%s %s %s" % (op1.sql, sqlop, op2.sql)
        elif op == "+":
            if op2.pytype is datetime.datetime:
                return "%s + %s" % (DAY_SECOND(op1.value), op2.sql)
            elif op2.pytype is datetime.date:
                return "INTERVAL %s DAY + %s" % (op1.value.days, op2.sql)
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


# ---------------------------- DatabaseTypes ---------------------------- #


# These are 5.0 types

# TRUE and FALSE only work with 4.1 or better.
# We could use BOOLEAN, but it wasn't introduced until 4.1.0.
class BOOL(dbtypes.SQL92BIT):
    # This is actually a synonym for TINYINT(1)
    synonyms = ['BOOLEAN']


class TINYINT(dbtypes.SQL92SMALLINT):
    bytes = 1
    # MySQL allows TINYINT to be signed or unsigned.
    signed = True

class SMALLINT(dbtypes.SQL92SMALLINT):
    bytes = 2

class MEDIUMINT(dbtypes.SQL92INTEGER):
    bytes = 3

class INT(dbtypes.SQL92INTEGER):
    synonyms = ['INTEGER']

class BIGINT(dbtypes.SQL92INTEGER):
    bytes = 8


class DECIMAL(dbtypes.SQL92DECIMAL):
    synonyms = ['DECIMAL', 'DEC', 'NUMERIC']
    
    default_adapters = dbtypes.SQL92DECIMAL.default_adapters.copy()
    default_adapters[datetime.timedelta] = MySQL_timedelta_to_DECIMAL()
    
    # "Before 3.23.6, precision and scale both must be specified explicitly."
    _precision = 10
    max_precision = 16
    
    # DECIMAL_MAX_SCALE is 30 in every copy of MySQL 5 I can find.
    # Not sure what the limits are in older versions.
    max_scale = 30
    
    def ddl(self):
        """Return the type for use in CREATE or ALTER statements."""
        if self.precision is not None:
            if self.scale is not None:
                return "DECIMAL(%s, %s)" % (self.precision, self.scale)
            return "DECIMAL(%s)" % self.precision
        return "DECIMAL"

class DECIMAL503(DECIMAL):
    max_precision = 64

class DECIMAL505(DECIMAL):
    max_precision = 65


class FLOAT(dbtypes.SQL92REAL):
    default_adapters = dbtypes.SQL92REAL.default_adapters.copy()
    default_adapters[float] = MySQL_float_adapter()

class DOUBLE(dbtypes.SQL92DOUBLE):
    synonyms = ['REAL', 'DOUBLE PRECISION']
    default_adapters = dbtypes.SQL92DOUBLE.default_adapters.copy()
    default_adapters[float] = MySQL_float_adapter()


class DATETIME(dbtypes.SQL92TIMESTAMP):
    _min = datetime.datetime(1000, 1, 1)
    _max = datetime.datetime(9999, 12, 31, 23, 59, 59)
    default_adapters = dbtypes.SQL92TIMESTAMP.default_adapters.copy()
    default_adapters[datetime.datetime] = MySQL_datetime_to_DATETIME()

class DATE(dbtypes.SQL92DATE):
    _min = datetime.date(1000, 1, 1)
    _max = datetime.date(9999, 12, 31)
    default_adapters = dbtypes.SQL92DATE.default_adapters.copy()
    default_adapters[datetime.date] = MySQL_date_to_DATE()

class TIME(dbtypes.SQL92TIME):
    pass



class CHAR(dbtypes.SQL92CHAR):
    variable = False
    bytes = max_bytes = 255

class VARCHAR(dbtypes.SQL92VARCHAR):
    variable = True
    bytes = 255
    max_bytes = 255

class VARCHAR503(VARCHAR):
    # "The maximum effective length of a VARCHAR in MySQL 5.0.3 and
    # later is determined by the maximum row size and the character
    # set used. The maximum column length is subject to a row size
    # of 65,532 bytes."
    max_bytes = 65535
    synonyms = ['VARCHAR']
    
    def ddl(self):
        """Return the type for use in CREATE or ALTER statements."""
        return "VARCHAR(%s)" % self.bytes


class BINARY(dbtypes.SQL92CHAR):
    variable = False
    bytes = max_bytes = 255

class VARBINARY(dbtypes.SQL92VARCHAR):
    variable = True
    bytes = 255
    max_bytes = 255

class VARBINARY503(VARBINARY):
    # "The maximum effective length of a VARCHAR in MySQL 5.0.3 and
    # later is determined by the maximum row size and the character
    # set used. The maximum column length is subject to a row size
    # of 65,532 bytes."
    max_bytes = 65535
    synonyms = ['VARBINARY']
    
    def ddl(self):
        """Return the type for use in CREATE or ALTER statements."""
        return "VARBINARY(%s)" % self.bytes


class TINYBLOB(dbtypes.TEXT):
    bytes = max_bytes = (2 ** 8) - 1

class BLOB(dbtypes.TEXT):
    bytes = max_bytes = (2 ** 16) - 1

class MEDIUMBLOB(dbtypes.TEXT):
    bytes = max_bytes = (2 ** 24) - 1

class LONGBLOB(dbtypes.TEXT):
    bytes = max_bytes = (2 ** 32) - 1


class TINYTEXT(dbtypes.TEXT):
    bytes = max_bytes = (2 ** 8) - 1

class TEXT(dbtypes.TEXT):
    bytes = max_bytes = (2 ** 16) - 1

class MEDIUMTEXT(dbtypes.TEXT):
    bytes = max_bytes = (2 ** 24) - 1

class LONGTEXT(dbtypes.TEXT):
    bytes = max_bytes = (2 ** 32) - 1



class MySQLTypeSet(dbtypes.DatabaseTypeSet):
    
    # TRUE and FALSE only work with 4.1 or better.
    expr_true = "1"
    expr_false = "0"
    
    known_types = {'float': [FLOAT, DOUBLE],
                   # MySQL VARBINARY/BLOBs will do case-sensitive comparisons.
                   # They also won't truncate trailing spaces like VARCHAR does.
                   'varchar': [VARBINARY, TINYBLOB, BLOB, MEDIUMBLOB, LONGBLOB],
                   'char': [BINARY],
                   'int': [TINYINT, SMALLINT, MEDIUMINT, INT, BIGINT],
                   'bool': [BOOL],
                   'datetime': [DATETIME],
                   'date': [DATE],
                   'time': [TIME],
                   'timedelta': [],
                   'numeric': [DECIMAL],
                   'other': [CHAR, VARCHAR],
                   }
    
    def __init__(self, version):
        self.version = version
        
        if self.version >= providers.Version("4.1.1"):
            # TRUE and FALSE only work with 4.1 or better.
            self.expr_true = "TRUE"
            self.expr_false = "FALSE"
        if self.version >= providers.Version("5.0.3"):
            self.known_types['numeric'] = [DECIMAL503]
            self.known_types['varchar'] = [VARBINARY503, TINYBLOB, BLOB,
                                           MEDIUMBLOB, LONGBLOB]
        if self.version >= providers.Version("5.0.5"):
            self.known_types['numeric'] = [DECIMAL505]


class MySQLDeparser(deparse.SQLDeparser):
    
    like_escapes = [("%", r"\%"), ("_", r"\_")]
    
    def builtins_today(self):
        return self.get_expr("CURDATE()", datetime.date)


class MySQLDeparser411(MySQLDeparser):
    
    # Before MySQL 4.1.1, BINARY comparisons could use UPPER()
    # or LOWER() to perform case-insensitive comparisons. Newer
    # versions must use CONVERT() to obtain a case-sensitive
    # encoding, like utf8.
    
    def builtins_icontainedby(self, op1, op2):
        if op1.value is not None:
            # Looking for text in a field. Use Like (reverse terms).
            return self.get_expr("CONVERT(" + op2.sql +
                                 " USING utf8) LIKE '%" +
                                 self.escape_like(op1.sql)
                                 + "%'", bool)
        else:
            # Looking for field in (a, b, c).
            atoms = []
            for x in op2.value:
                adapter = op1.dbtype.default_adapter(type(x))
                atoms.append(adapter.push(x, op1.dbtype))
            return self.get_expr("CONVERT(%s USING utf8) IN (%s)" %
                                 (op1.sql, ", ".join(atoms)), bool)
    
    def builtins_istartswith(self, x, y):
        return self.get_expr("CONVERT(" + x.sql + " USING utf8) LIKE '" +
                             self.escape_like(y.sql) + "%'", bool)
    
    def builtins_iendswith(self, x, y):
        return self.get_expr("CONVERT(" + x.sql + " USING utf8) LIKE '%" +
                             self.escape_like(y.sql) + "'", bool)
    
    def builtins_ieq(self, x, y):
        return self.get_expr("CONVERT(" + x.sql + " USING utf8) = " + y.sql,
                             bool)
    
    def builtins_utcnow(self):
        return self.get_expr("UTC_TIMESTAMP()", datetime.datetime)


class MySQLIndexSet(geniusql.IndexSet):
    
    def __delitem__(self, key):
        t = self.table
        # MySQL might rename multiple-column indices to "PRIMARY"
        for i in t.schema.db._get_indices(t.name):
            if i.colname == self[key].colname:
                t.schema.db.execute_ddl('DROP INDEX %s ON %s;' %
                                        (i.qname, t.qname))


class MySQLTable(geniusql.Table):
    
    def create(self):
        """Create this table in the database."""
        db = self.schema.db
        
        # Set table.created to True, which should "turn on"
        # any future ALTER TABLE statements.
        self.created = True
        
        fields = []
        incr_fields = []
        pk = []
        for colkey, col in self.iteritems():
            fields.append(self.schema.columnclause(col))
            if col.autoincrement:
                if col.initial != 1:
                    incr_fields.append(col)
                    if col.initial < 1:
                        errors.warn("MySQL interprets manually setting an "
                                    "AUTO_INCREMENT column value to 0 as "
                                    "'use the next available value in the "
                                    "sequence'. By setting %s.initial to %r, "
                                    "there is a slight chance you will "
                                    "encounter this in the future." %
                                    (col.name, col.initial))
            
            if col.key:
                qname = col.qname
                dbtype = col.dbtype
                if isinstance(dbtype, dbtypes.TEXT):
                    # MySQL won't allow indexes on a BLOB field without a
                    # specific index prefix length. We choose 255 just for fun.
                    qname = "%s(255)" % qname
                pk.append(qname)
        
        if pk:
            pk = ", PRIMARY KEY (%s)" % ", ".join(pk)
        else:
            pk = ""
        
        encoding = db.encoding
        if encoding:
            encoding = " CHARACTER SET %s" % encoding
        
        db.execute_ddl('CREATE TABLE %s (%s%s)%s;' %
                       (self.qname, ", ".join(fields), pk, encoding))
        
        if incr_fields:
            # Wow, what a hack. We have to INSERT a dummy row to set the
            # autoincrement initial value(s), and we can't delete it until
            # after the CREATE INDEX statements (or the counter will revert).
            fields = ", ".join([col.qname for col in incr_fields])
            values = ", ".join([str(col.initial - 1) for col in incr_fields])
            db.execute_ddl("INSERT INTO %s (%s) VALUES (%s);"
                           % (self.qname, fields, values))
        
        for k, index in self.indices.iteritems():
            dbtype = self[k].dbtype
            if isinstance(dbtype, dbtypes.TEXT):
                # MySQL won't allow indexes on a BLOB field without a
                # specific index prefix length. We choose 255 just for fun.
                db.execute_ddl('CREATE INDEX %s ON %s (%s(255));' %
                               (index.qname, self.qname, db.quote(index.colname)))
            else:
                db.execute_ddl('CREATE INDEX %s ON %s (%s);' %
                               (index.qname, self.qname, db.quote(index.colname)))
        
        if incr_fields:
            db.execute_ddl("DELETE FROM %s" % self.qname)
    
    def _rename(self, oldcol, newcol):
        self.schema.db.execute_ddl("ALTER TABLE %s CHANGE %s %s %s;" %
                                   (self.qname, oldcol.qname, newcol.qname,
                                    oldcol.dbtype.ddl()))
    
    def _grab_new_ids(self, idkeys, conn):
        return {idkeys[0]: conn.insert_id()}
    
    def drop_primary(self):
        """Remove any PRIMARY KEY for this Table."""
        self.schema.db.execute('ALTER TABLE %s DROP PRIMARY KEY;' % self.qname)
    
    def set_primary(self):
        """Set the PRIMARY KEY for this Table."""
        pk = [column.qname for column in self.itervalues() if column.key]
        if pk:
            # For MySQL, we MUST do this in a single statement.
            self.schema.db.execute("ALTER TABLE %s DROP PRIMARY KEY, "
                                   "ADD PRIMARY KEY (%s);" %
                                   (self.qname, ", ".join(pk)))
        else:
            self.drop_primary()
    
    def insert(self, **kwargs):
        """Insert a row and return it, including any new identifiers."""
        # MySQL interprets "INSERT INTO x (ID) VALUES (0)" to mean
        # "use the next available number in the sequence" if
        # x is AUTO_INCREMENT.
        for key, col in self.iteritems():
            if col.autoincrement and kwargs.get(key, None) == 0:
                raise ValueError("MySQL does not allow manually setting an "
                                 "AUTO_INCREMENT column value to 0.")
        return geniusql.Table.insert(self, **kwargs)


connargs = ["host", "user", "passwd", "db", "port", "unix_socket",
            "conv", "connect_time", "compress", "named_pipe",
            "init_command", "read_default_file", "read_default_group",
            "cursorclass", "client_flag",
            ]

class MySQLConnectionManager(conns.ConnectionManager):
    
    # InnoDB default
    default_isolation = "REPEATABLE READ"
    
    def _get_conn(self, master=False):
        if master:
            args = self.connargs.copy()
            args['db'] = 'mysql'
        else:
            args = self.connargs
        
        try:
            conn = _mysql.connect(**args)
            if self.initial_sql:
                conn.query(self.initial_sql)
        except _mysql.OperationalError, x:
            if x.args[0] == 1040:   # Too many connections
                raise errors.OutOfConnectionsError
            raise
        return conn
    
    def _del_conn(self, conn):
        """Close a connection object."""
        try:
            conn.close()
        except _mysql.ProgrammingError, exc:
            # ProgrammingError: closing a closed connection
            if exc.args == ('closing a closed connection',):
                pass
            else:
                raise
    
    def _start_transaction(self, conn, isolation=None):
        """Start a transaction."""
        # http://dev.mysql.com/doc/refman/5.1/en/set-transaction.html
        # "The default behavior of SET TRANSACTION is to set the
        # isolation level for the next (not yet started) transaction."
        # So swap the usual order of statements to execute SET before START.
        self.isolate(conn, isolation)
        self.db.execute("START TRANSACTION;", conn)


class MySQLSchema(geniusql.Schema):
    
    tableclass = MySQLTable
    indexsetclass = MySQLIndexSet
    
    def columnclause(self, column):
        """Return a clause for the given column for CREATE or ALTER TABLE.
        
        This will be of the form "name type [DEFAULT x] [AUTO_INCREMENT]"
        """
        autoincr = ""
        if column.autoincrement:
            autoincr = " AUTO_INCREMENT"
        
        default = column.default or ""
        if default:
            default = column.adapter.pull(default, column.dbtype)
            default = " DEFAULT %s" % default
        
        return "%s %s%s%s" % (column.qname, column.dbtype.ddl(),
                              default, autoincr)
    
    def _get_tables(self, conn=None):
        data, _ = self.db.fetch("SHOW TABLES FROM %s" % self.db.qname, conn=conn)
        return [self.tableclass(row[0], self.db.quote(row[0]),
                                self, created=True)
                for row in data]
    
    def _get_table(self, tablename, conn=None):
        data, _ = self.db.fetch("SHOW TABLES FROM %s LIKE '%s'"
                             % (self.db.qname, tablename), conn=conn)
        for row in data:
            name = row[0]
            if name == tablename:
                return self.tableclass(name, self.db.quote(name),
                                       self, created=True)
        raise errors.MappingError("Table %r not found." % tablename)
    
    def _get_columns(self, table, conn=None):
        # cols are: Field, Type, Null, Key, Default, Extra.
        # See http://dev.mysql.com/doc/refman/4.1/en/describe.html
        data, _ = self.db.fetch("SHOW COLUMNS FROM %s.%s" %
                                (self.db.qname, table.qname), conn=conn)
        cols = []
        for row in data:
            hints = {}
            dbtypename = row[1].upper()
            atoms = dbtypename.split("(", 1)
            
            dbtype = self.db.typeset.canonicalize(atoms.pop(0))()
            
            if atoms:
                args = atoms[0][:-1]
                if isinstance(dbtype, DECIMAL):
                    args = [x.strip() for x in args.split(",")]
                    dbtype.precision, dbtype.scale = map(int, args)
                else:
                    dbtype.bytes = int(args)
            
            key = (row[3] == "PRI")
            pytype = dbtype.default_pytype
            col = geniusql.Column(pytype, dbtype, None, key,
                                  name=row[0], qname=self.db.quote(row[0]))
            col.adapter = dbtype.default_adapter(col.pytype)
            
            if row[4]:
                col.default = col.adapter.pull(row[4], col.dbtype)
            if "auto_increment" in row[5].lower():
                col.autoincrement = True
            
            cols.append(col)
        return cols
    
    def _get_indices(self, table, conn=None):
        indices = []
        try:
            # cols are: Table, Non_unique, Key_name, Seq_in_index, Column_name,
            # Collation, Cardinality, Sub_part, Packed, Null, Index_type, Comment
            data, _ = self.db.fetch("SHOW INDEX FROM %s.%s"
                                    % (self.db.qname, table.qname), conn=conn)
        except _mysql.ProgrammingError, x:
            if x.args[0] != 1146:
                raise
        else:
            for row in data:
                i = geniusql.Index(row[2], self.db.quote(row[2]),
                                   row[0], row[4], not row[1])
                indices.append(i)
        return indices


class MySQLDatabase(geniusql.Database):
    
    sql_name_max_length = 64
    # MySQL uses case-sensitive database and table names on Unix, but
    # not on Windows. Use all-lowercase identifiers to work around the
    # problem. "Column names, index names, and column aliases are not
    # case sensitive on any platform."
    # If deployers set lower_case_table_names to 1, it would help.
    sql_name_caseless = True
    encoding = "utf8"
    
    connectionmanager = MySQLConnectionManager
    schemaclass = MySQLSchema
    
    def __init__(self, **kwargs):
        kwargs['name'] = kwargs['db']
        geniusql.Database.__init__(self, **kwargs)
        
        self.connections.connargs = dict([(k, v) for k, v in kwargs.iteritems()
                                          if k in connargs])
        
        self.deparser = MySQLDeparser
        
        # Get the version string from MySQL, to see if we need
        # a different deparser.
        conn = self.connections._get_conn(master=True)
        rowdata, cols = self.fetch("SELECT version();", conn)
        conn.close()
        v = rowdata[0][0]
        self._version = providers.Version(v)
        
        # deparser
        if self._version > providers.Version("4.1.1"):
            self.deparser = MySQLDeparser411
        
        self.typeset = MySQLTypeSet(self._version)
    
    def version(self):
        return "MySQL Version: %s\nMySQLdb Version: %s" % (self._version, _mysql.version_info)
    
    def quote(self, name):
        """Return name, quoted for use in an SQL statement."""
        return '`' + name.replace('`', '``') + '`'
    
    def is_connection_error(self, exc):
        """If the given exception instance is a connection error, return True.
        
        This should return True for errors which arise from broken connections;
        for example, if the database server has dropped the connection socket,
        or is unreachable.
        """
        if isinstance(exc, _mysql.OperationalError):
            # OperationalError: (2006, 'MySQL server has gone away')
            return exc.args[0] == 2006
        return False
    
    def execute(self, sql, conn=None):
        """Return a native response for the given SQL."""
        try:
            return geniusql.Database.execute(self, sql, conn=conn)
        except _mysql.OperationalError, x:
            if x.args[0] == 1030 and x.args[1] == 'Got error 139 from storage engine':
                raise ValueError("row length exceeds 8000 byte limit")
            raise
    
    def fetch(self, sql, conn=None):
        """Return rowdata, columns(name, type) for the given sql.
        
        sql should be a SQL string.
        
        rowdata will be an iterable of iterables containing the result values.
        columns will be an iterable of (column name, data type) pairs.
        """
        if conn is None:
            conn = self.connections.get()
        self.execute(sql, conn)
        
        # store_result uses a client-side cursor
        res = conn.store_result()
        
        # The Python MySQLdb library swallows lock timeouts and returns []
        # (for example, when deadlocked during a SERIALIZABLE transaction).
        # Raise an error instead.
        # Oddly, although the deadlock will stall the conn.query() call,
        # the error message is only available after store_result().
        err = conn.error()
        if err == "Lock wait timeout exceeded; try restarting transaction":
            raise _mysql.OperationalError(1205, err)
        
        if res is None:
            return [], []
        return res.fetch_row(0, 0), res.describe()
    
    def is_timeout_error(self, exc):
        # OperationalError: (1205, 'Lock wait timeout exceeded; try restarting transaction')
        if not isinstance(exc, _mysql.OperationalError):
            return False
        return exc.args[0] == 1205
    
    def create(self):
        # _mysql has create_db and drop_db commands, but they're deprecated.
        encoding = self.encoding
        if encoding:
            encoding = " CHARACTER SET %s" % encoding
        sql = 'CREATE DATABASE %s%s;' % (self.qname, encoding)
        conn = self.connections._get_conn(master=True)
        self.execute_ddl(sql, conn)
        conn.close()
    
    def drop(self):
        conn = self.connections._get_conn(master=True)
        try:
            try:
                self.execute_ddl('DROP DATABASE %s;' % self.qname, conn)
            except _mysql.OperationalError, x:
                # OperationalError: (1008, "Can't drop database
                # 'dejavu_test'; database doesn't exist")
                if x.args[0] == 1008:
                    raise errors.MappingError(x.args[1])
        finally:
            conn.close()

