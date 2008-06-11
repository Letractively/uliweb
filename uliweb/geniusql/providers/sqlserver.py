import datetime

from geniusql import adapters, dbtypes, errors, objects
from geniusql.providers import ado



# ------------------------------ Adapters ------------------------------ #


class SQLServer_time(ado.COM_time):
    
    epoch = datetime.datetime(1900, 1, 1)


def _compare_strings(self, op1, op, sqlop, op2):
    """Return the SQL for a comparison operation (or raise TypeError).
    
    op1 and op2 will be SQLExpression objects.
    op will be an index into opcode.cmp_op.
    sqlop will be the matching SQL for the given operator.
    """
    # ADO comparison operators for strings are case-insensitive.
    if op in ('<', '<=', '==', '!=', '>', '>='):
        # Some operations on strings can be emulated with the
        # Convert function.
        return ("Convert(binary, %s) %s Convert(binary, %s)"
                % (op1.sql, sqlop, op2.sql))
    else:
        raise TypeError("Microsoft SQL Server cannot compare strings "
                        "using %r in a case-sensitive way." % sqlop)

class SQLServer_str_to_VARCHAR(adapters.str_to_SQL92VARCHAR):
    escapes = [("'", "''")]
    compare_op = _compare_strings

class SQLServer_unicode_to_VARCHAR(adapters.unicode_to_SQL92VARCHAR):
    escapes = [("'", "''")]
    compare_op = _compare_strings

class SQLServer_Pickler(adapters.Pickler):
    escapes = [("'", "''")]
    compare_op = _compare_strings



# ---------------------------- DatabaseTypes ---------------------------- #


# See http://doc.ddart.net/mssql/sql70/ca-co_1.htm
# for an implicit conversion table.


class SQLServerStringType(dbtypes.SQL92VARCHAR):
    encoding = 'ISO-8859-1'
    
    default_adapters = dbtypes.SQL92VARCHAR.default_adapters.copy()
    default_adapters.update({str: SQLServer_str_to_VARCHAR(),
                             unicode: SQLServer_unicode_to_VARCHAR(),
                             None: SQLServer_Pickler(),
                             })

class BINARY(SQLServerStringType):
    max_bytes = 8000
    variable = False

class VARBINARY(SQLServerStringType):
    max_bytes = 8000
    variable = True

class CHAR(SQLServerStringType):
    max_bytes = 8000
    variable = False

class VARCHAR(SQLServerStringType):
    max_bytes = 8000
    variable = True
##    
##    def cast(self, sql, totype):
##        """Cast the given SQL expression from this type to another."""
##        if isinstance(totype, (TINYINT, SMALLINT, INT, BIGINT)):
##            return ("(CASE WHEN ISNUMERIC(%s)=1 THEN CAST(%s AS %s) END)"
##                    % (sql, sql, totype.__class__.__name__))
##        raise TypeError("Could not cast %r from %r to %r."
##                        % (sql, self, totype))

class NCHAR(SQLServerStringType):
    synonyms=['WCHAR']
    max_bytes = 4000
    variable = False

class NVARCHAR(SQLServerStringType):
    synonyms=['VARWCHAR']
    max_bytes = 4000
    variable = True

# "ntext, text, and image data types will be removed in a future version
# of Microsoft SQL Server. Avoid using these data types in new development
# work, and plan to modify applications that currently use them.
# Use nvarchar(max), varchar(max), and varbinary(max) instead."
# http://msdn2.microsoft.com/en-us/library/ms187993.aspx
class NTEXT(dbtypes.TEXT):
    synonyms = ['LONGVARWCHAR']
    encoding = 'ISO-8859-1'
    bytes = max_bytes = ((2 ** 30) - 1) * 2

class TEXT(dbtypes.TEXT):
    synonyms = ['LONGVARCHAR']
    encoding = 'ISO-8859-1'
    bytes = max_bytes = (2 ** 31) - 1

class IMAGE(dbtypes.TEXT):
    synonyms = ['LONGVARBINARY']
    encoding = 'ISO-8859-1'
    bytes = max_bytes = (2 ** 31) - 1


class BIT(dbtypes.SQL92BIT):
    synonyms = ['BOOLEAN']

# "Sure, there are two 4-byte integers stored. But they are
# packed together into a BINARY(8). The first 4-byte being
# the elapsed number days since SQL Server's base date of
# 1900-01-01. The Second 4-bytes Store the Time of Day
# Represented as the Number of Milliseconds After Midnight."
# http://www.sql-server-performance.com/fk_datetime.asp

# Note also that SQL Server allows DATETIME in the range:
# "1753-01-01 00:00:00.0" to "9999-12-31 23:59:59.997".
class DATETIME(dbtypes.SQL92TIMESTAMP):
    synonyms = ['DBTIMESTAMP']
    _min=datetime.datetime(1753, 1, 1)
    _max=datetime.datetime(9999, 12, 31)
    default_adapters = {datetime.datetime: ado.COM_datetime(),
                        datetime.date: ado.COM_date(),
                        datetime.time: SQLServer_time(),
                        }

class SMALLDATETIME(dbtypes.SQL92DATE):
    _min=datetime.datetime(1900, 1, 1)
    _max=datetime.datetime(2079, 6, 6)


class REAL(dbtypes.SQL92REAL):
    synonyms = ['SINGLE']

class FLOAT(dbtypes.SQL92DOUBLE):
    synonyms = ['DOUBLE']


class TINYINT(dbtypes.SQL92SMALLINT):
    synonyms = ['UNSIGNEDTINYINT']
    bytes = max_bytes = 1
    signed = False
    default_adapters = {int: adapters.int_to_SQL92SMALLINT(1),
                        long: adapters.int_to_SQL92SMALLINT(1),
                        }

class SMALLINT(dbtypes.SQL92SMALLINT):
    pass

class INT(dbtypes.SQL92INTEGER):
    synonyms = ['INTEGER', 'IDENTITY']

class BIGINT(dbtypes.SQL92INTEGER):
    """8-byte BIGINT type for SQL Server (2000+ only)."""
    bytes = max_bytes = 8
    default_pytype = long
    default_adapters = {int: adapters.int_to_SQL92INTEGER(8),
                        long: adapters.int_to_SQL92INTEGER(8),
                        }


class DECIMAL(dbtypes.SQL92DECIMAL):
    synonyms = ['NUMERIC']
    
    # Docs say 38, but when I try to set/retrieve a value from a DECIMAL
    # column with a precision of 30, the scale is off by one; that is,
    #   writing '11111111111111111111111111.1111'
    #   returns '11111111111111111111111111.111'
    # With a precision of 31, the scale is off by two, and so on.
    # If the resulting scale moves the decimal point far enough,
    # then None is returned instead of a number. For example,
    #   writing '111111111111111111111111111.1111'
    #   returns '111111111111111111111111111.111',
    # but
    #   writing '111111111111111111111111111111.1'
    #   returns None!!
    max_precision = 29
    max_scale = 29
    
    default_adapters = dbtypes.SQL92DECIMAL.default_adapters.copy()
    default_adapters[datetime.timedelta] = ado.COM_timedelta()


class MoneyType(dbtypes.FrozenByteType):
    
    scale = 4
    default_pytype = dbtypes.SQL92DECIMAL.default_pytype
    
    def range(self):
        """Return self.max - self.min."""
        return self._max - self._min
    
    def min(self):
        """Return the minimum value allowed."""
        return self._min
    
    def max(self):
        """Return the maximum value allowed."""
        return self._max

class MONEY(MoneyType):
    synonyms = ['CURRENCY']
    bytes = max_bytes = 8
    _min = -922,337,203,685,477.5808
    _max = 922,337,203,685,477.5807

class SMALLMONEY(MoneyType):
    bytes = max_bytes = 4
    _min = -214,748.3648
    _max = 214,748.3647

class TIMESTAMP(dbtypes.DatabaseType):
    """Automatic, unique binary numbers for version-stamping rows.
    
    The timestamp data type is just an incrementing number and does
    not preserve a date or a time. To record a date or time, use a
    datetime data type."""
    synonyms = ['ROWVERSION']

class UNIQUEIDENTIFIER(dbtypes.DatabaseType):
    """A 16-byte GUID."""
    pass


class SQLServerTypeSet(dbtypes.DatabaseTypeSet):
    
    # These are not adapter.push(bool) (which are used on one side of 
    # a comparison). Instead, these are used when the whole (sub)expression
    # is True or False, e.g. "WHERE TRUE", or "WHERE TRUE and 'a'.'b' = 3".
    expr_true = "(1=1)"
    expr_false = "(1=0)"
    
    known_types = {'float': [REAL, FLOAT],
                   'varchar': [VARCHAR, TEXT, VARBINARY, NVARCHAR, NTEXT,
                               IMAGE],
                   'char': [CHAR, BINARY, NCHAR],
                   'int': [TINYINT, SMALLINT, INT, BIGINT],
                   'bool': [BIT],
                   'datetime': [DATETIME, SMALLDATETIME],
                   'date': [DATETIME, SMALLDATETIME],
                   'time': [DATETIME, SMALLDATETIME],
                   'timedelta': [],
                   'numeric': [DECIMAL],
                   'other': [MONEY, SMALLMONEY, TIMESTAMP, UNIQUEIDENTIFIER],
                   }
    
    def dbtype_for_str(self, hints):
        # The bytes hint shall not reflect the usual 4-byte base for varchar.
        bytes = int(hints.get('bytes', 255))
        
        if bytes == 0 or bytes > 8000:
            # Okay, what the @#$%& is wrong with Redmond??!?! We can't even
            # compare TEXT or NTEXT fields??!? Fine. We'll deny such, and
            # warn the deployer with less swearing and exclamation points.
            errors.warn("You have defined a string property without "
                        "limiting its length. Microsoft SQL Server does "
                        "not allow comparisons on string fields larger "
                        "than 8000 characters. Some of your data may be "
                        "truncated.")
            # 8000 *bytes* is the absolute upper limit for varchar and
            # varbinary. If there are further fields defined for the row,
            # or the codepage uses a double-byte character set, we still
            # might exceed the max size (8060) for a record. We *could*
            # calc the total record size, and adjust accordingly. Meh.
            bytes = 8000
        
        for dbtype in self.known_types['varchar']:
            if bytes <= dbtype.max_bytes:
                return dbtype(bytes=bytes)
        
        raise ValueError("%r is greater than the maximum bytes %r."
                         % (bytes, dbtype.max_bytes))


class SQLServerDeparser(ado.ADOSQLDeparser):
    
    like_escapes = [("[", "[[]"), ("%", "[%]"), ("_", "[_]"),
                    ("?", "[?]"), ("#", "[#]")]
    
    def builtins_now(self):
        return self.get_expr("GETDATE()", datetime.datetime)
    
    def builtins_today(self):
        return self.get_expr("DATEADD(dd, DATEDIFF(dd, 0, getdate()), 0)",
                             datetime.date)
    
    def builtins_year(self, x):
        return self.get_expr("DATEPART(year, " + x.sql + ")", int)
    
    def builtins_month(self, x):
        return self.get_expr("DATEPART(month, " + x.sql + ")", int)
    
    def builtins_day(self, x):
        return self.get_expr("DATEPART(day, " + x.sql + ")", int)
    
    def builtins_utcnow(self):
        return self.get_expr("GETUTCDATE()", datetime.datetime)


class SQLServerTable(ado.ADOTable):
    
    def _rename(self, oldcol, newcol):
        self.schema.db.execute_ddl("EXEC sp_rename '%s.%s', '%s', 'COLUMN'" %
                                   (self.name, oldcol.name, newcol.name))
    
    def _grab_new_ids(self, idkeys, conn):
        """Insert a row using the table's SERIAL field."""
        # For some reason, using SCOPE_IDENTITY or IDENTITY failed (returned
        # None) when retrieving ID's just after a 99-thread-test ran. Moving
        # the multithreading test fixed it. IDENT_CURRENT worked regardless.
        data, _ = self.schema.db.fetch("SELECT IDENT_CURRENT('%s');"
                                       % self.qname, conn)
        return {idkeys[0]: data[0][0]}
    
    def insert(self, **kwargs):
        """Insert a row and return it, including any new identifiers."""
        conn = self.schema.db.connections.get()
        
        # SQL Server doesn't allow inserts on IDENTITY columns by default.
        # See http://msdn2.microsoft.com/en-us/library/ms188059.aspx
        has_manual_identity = False
        for key, col in self.iteritems():
            if col.autoincrement and kwargs.get(key) is not None:
                has_manual_identity = True
                break
        
        if has_manual_identity:
            try:
                self.schema.db.execute("SET IDENTITY_INSERT %s ON;" %
                                       self.qname, conn)
            except ado.pywintypes.com_error, exc:
                if exc.args[2][5] == -2147217900:
                    # com_error: (-2147352567, 'Exception occurred.',
                    #    (0, 'Microsoft SQL Native Client',
                    #    "IDENTITY_INSERT is already ON for table
                    #    'dejavu_test.dbo.testZoo'. Cannot perform SET
                    #    operation for table 'testNothingToDoWithZoos'.",
                    #    None, 0, -2147217900), None,
                    #    'SET IDENTITY_INSERT [testNothingToDoWithZoos] ON')
                    oldtable = re.match(
                        r"IDENTITY_INSERT is already ON for table '(.*)'.*",
                        exc.args[2][2]).groups()[0]
                    self.schema.db.execute("SET IDENTITY_INSERT %s OFF;" %
                                           oldtable, conn)
                    self.schema.db.execute("SET IDENTITY_INSERT %s ON;" %
                                           self.qname, conn)
                else:
                    raise
        
        idkeys = []
        values = {}
        for key, col in self.iteritems():
            if col.autoincrement and kwargs.get(key) is None:
                # Skip this field, since we're using a sequencer
                idkeys.append(key)
                continue
            if key in kwargs:
                values[key] = kwargs[key]
        
        self.schema.db.insert((self, values), conn)
        
        # Note that the 'kwargs' dict has already been copied simply
        # by being passed as kwargs. So modifying it in-place won't
        # mangle the caller's original dict.
        if idkeys:
            for k, v in self._grab_new_ids(idkeys, conn).iteritems():
                col = self[k]
                kwargs[k] = col.adapter.pull(v, col.dbtype)
        return kwargs


class SQLServerConnectionManager(ado.ADOConnectionManager):
    
    default_isolation = "READ COMMITTED"


class SQLServerSchema(ado.ADOSchema):
    
    tableclass = SQLServerTable
    
    # See http://www.carlprothman.net/Technology/DataTypeMapping/tabid/97/Default.aspx
    adotypes = {
        # SQL Server              ADO Name
        2: SMALLINT,        # SMALLINT
        3: INT,             # INTEGER (also for IDENTITY (SQL Server 6.5))
        4: REAL,            # SINGLE
        5: FLOAT,           # DOUBLE
        6: MONEY,           # CURRENCY (also could be SMALLMONEY)
        11: BIT,            # BOOLEAN
        # 12: SQL_VARIANT,  # VARIANT (2000 +)
        17: TINYINT,        # UNSIGNEDTINYINT
        20: BIGINT,         # BIGINT
        128: BINARY,        # BINARY (also could be TIMESTAMP)
        129: CHAR,          # CHAR
        130: NCHAR,         # WCHAR (7.0+)
        131: DECIMAL,       # DECIMAL, NUMERIC
        135: DATETIME,      # DBTIMESTAMP (also could be SMALLDATETIME)
        200: VARCHAR,       # VARCHAR
        201: TEXT,          # LONGVARCHAR
        202: NVARCHAR,      # VARWCHAR
        203: NTEXT,         # LONGVARWCHAR (7.0+)
        204: VARBINARY,     # VARBINARY
        205: IMAGE,         # LONGVARBINARY
        # 0: EMPTY,
        # 7: DATE, 8: BSTR, 9: IDISPATCH, 10: ERROR,
        # 13: IUNKNOWN, 14: DECIMAL, 16: TINYINT,
        # 18: UNSIGNEDSMALLINT, 19: UNSIGNEDINT, 21: UNSIGNEDBIGINT,
        # 72: GUID,
        # 132: USERDEFINED, 133: DBDATE, 134: DBTIME,
    }
    
    def __init__(self, db, name=None):
        if name is None:
            name = 'dbo'
        ado.ADOSchema.__init__(self, db, name)
    
    def _get_columns(self, table, conn=None):
        # For some reason, adSchemaPrimaryKeys would only return a single
        # record for a PK that had multiple columns. Use adSchemaIndexes.
        # coldefs will be:
        # [(u'TABLE_CATALOG', 202), (u'TABLE_SCHEMA', 202), (u'TABLE_NAME', 202),
        # (u'INDEX_CATALOG', 202), (u'INDEX_SCHEMA', 202), (u'INDEX_NAME', 202),
        # (u'PRIMARY_KEY', 11), (u'UNIQUE', 11), (u'CLUSTERED', 11), (u'TYPE', 18),
        # (u'FILL_FACTOR', 3), (u'INITIAL_SIZE', 3), (u'NULLS', 3),
        # (u'SORT_BOOKMARKS', 11), (u'AUTO_UPDATE', 11), (u'NULL_COLLATION', 3),
        # (u'ORDINAL_POSITION', 19), (u'COLUMN_NAME', 202), (u'COLUMN_GUID', 72),
        # (u'COLUMN_PROPID', 19), (u'COLLATION', 2), (u'CARDINALITY', 21),
        # (u'PAGES', 3), (u'FILTER_CONDITION', 202), (u'INTEGRATED', 11)]
        data, _ = self.db.fetch(ado.adSchemaIndexes, conn=conn, schema=True)
        pknames = [row[17] for row in data
                   if (table.name == row[2]) and row[6]]
        
        # columns will be
        # [(u'TABLE_CATALOG', 202), (u'TABLE_SCHEMA', 202), (u'TABLE_NAME', 202),
        # (u'COLUMN_NAME', 202), (u'COLUMN_GUID', 72), (u'COLUMN_PROPID', 19),
        # (u'ORDINAL_POSITION', 19), (u'COLUMN_HASDEFAULT', 11),
        # (u'COLUMN_DEFAULT', 203), (u'COLUMN_FLAGS', 19), (u'IS_NULLABLE', 11),
        # (u'DATA_TYPE', 18), (u'TYPE_GUID', 72), (u'CHARACTER_MAXIMUM_LENGTH', 19),
        # (u'CHARACTER_OCTET_LENGTH', 19), (u'NUMERIC_PRECISION', 18),
        # (u'NUMERIC_SCALE', 2), (u'DATETIME_PRECISION', 19),
        # (u'CHARACTER_SET_CATALOG', 202), (u'CHARACTER_SET_SCHEMA', 202),
        # (u'CHARACTER_SET_NAME', 202), (u'COLLATION_CATALOG', 202),
        # (u'COLLATION_SCHEMA', 202), (u'COLLATION_NAME', 202),
        # (u'DOMAIN_CATALOG', 202), (u'DOMAIN_SCHEMA', 202),
        # (u'DOMAIN_NAME', 202), (u'DESCRIPTION', 203)]
        data, _ = self.db.fetch(ado.adSchemaColumns, conn=conn, schema=True)
        
        cols = []
        typer = self.db.typeset
        for row in data:
            # I tried passing criteria to OpenSchema, but passing None is
            # not the same as passing pythoncom.Empty (which errors).
            if row[2] != table.name:
                continue
            
            dbtypetype = self.adotypes[row[11]]
            dbtype = dbtypetype()
            pytype = dbtype.default_pytype
            if pytype is None:
                raise TypeError("%r has no default pytype." % dbtype)
            
            default = row[8]
            if default is not None:
                if "SQL Server 2005" in self.db._version:
                    # From http://msdn2.microsoft.com/en-us/library/ms143359.aspx:
                    # "The original text of an expression is decoded and
                    # normalized and the output of this operation is stored
                    # in the catalog metadata. The semantics of the decoded
                    # expression will be equivalent to the original text;
                    # however, there are no syntactic guarantees. For example,
                    # a computed column expression entered as c1 + c2 + 1 will
                    # appear as (([c1]+[c2])+(1)) in the definition column in
                    # the sys.computed_columns system catalog view."
                    if isinstance(default, basestring):
                        if pytype in (float, int, long):
                            # Assume default is similar to u'((1.0))'
                            default = default[2:-2]
                default = pytype(default)
            
            name = str(row[3])
            c = objects.Column(pytype, dbtype, default,
                               key=(name in pknames),
                               name=name, qname=self.db.quote(name))
            
            colflags = int(row[9])
            if ((colflags & ado.DBCOLUMNFLAGS_ISFIXEDLENGTH)
                and not (colflags & ado.DBCOLUMNFLAGS_WRITE)):
                c.autoincrement = True
            
            if dbtypetype in typer.known_types['int']:
                dbtype.bytes = row[15]
            elif dbtypetype in typer.known_types['float']:
                dbtype.precision = row[15]
                dbtype.scale = row[16]
            elif dbtypetype in typer.known_types['numeric']:
                dbtype.precision = row[15]
                dbtype.scale = row[16]
            elif (dbtypetype in typer.known_types['char'] or
                  dbtype in typer.known_types['varchar']):
                if row[13]:
                    # row[13] will be a float
                    dbtype.bytes = b = int(row[13])
            
            c.adapter = dbtype.default_adapter(pytype)
            cols.append(c)
        return cols
    
    def create(self):
        self.clear()
    
    def drop(self):
        self.clear()
    
    def columnclause(self, column):
        """Return a clause for the given column for CREATE or ALTER TABLE.
        
        This will be of the form:
            name type [DEFAULT x|IDENTITY(initial, 1) NOT NULL]
        """
        dbtype = column.dbtype.ddl()
        
        clause = ""
        if column.autoincrement:
            if not isinstance(column.dbtype, dbtypes.SQL92INTEGER):
                raise ValueError("SQL Server does not allow IDENTITY "
                                 "columns of type %r" % dbtype)
            clause = " IDENTITY(%s, 1) NOT NULL" % column.initial
        else:
            # SQL Server does not allow a column to have
            # both an IDENTITY clause and a DEFAULT clause.
            default = column.default or ""
            if default:
                clause = " DEFAULT %s" % column.adapter.push(default, column.dbtype)
        
        return '%s %s%s' % (column.qname, dbtype, clause)


class SQLServer2005_SELECT(ado.ADO_SELECT):
    
    def _get_sql(self):
        """Return an SQL SELECT statement."""
        if self.offset is None:
            return ado.ADO_SELECT._get_sql(self)
        
        # Crazy hackery but it works.
        atoms = ["SELECT"]
        append = atoms.append
        
        append(', '.join(self.input))
        append("FROM (SELECT")
        
        if self.distinct:
            append('DISTINCT')
        append(', '.join(self.input))
        append(", ROW_NUMBER() OVER (ORDER BY %s) as _internal_rownum" %
               ", ".join(self.orderby))
        if self.fromclause:
            append("FROM")
            append(self.fromclause)
            if self.whereclause:
                append("WHERE")
                append(self.whereclause)
            if self.groupby and len(self.groupby) < len(self.input):
                append("GROUP BY")
                append(", ".join(self.groupby))
        
        append(") as tabledata")
        if self.into:
            append("INTO")
            append(self.into)
        append("WHERE _internal_rownum BETWEEN %d AND %d "
               "ORDER BY _internal_rownum;" %
               (self.offset + 1, self.offset + self.limit))
        
        return " ".join(atoms)
    sql = property(_get_sql, doc="The SQL string for this SELECT statement.")


class SQLServer2005SelectWriter(ado.ADOSelectWriter):
    statement_class = SQLServer2005_SELECT


class SQLServerDatabase(ado.ADODatabase):
    
    deparser = SQLServerDeparser
    typeset = SQLServerTypeSet()
    connectionmanager = SQLServerConnectionManager
    schemaclass = SQLServerSchema
    
    # "The ORDER BY clause is invalid in views, inline functions,
    # derived tables, subqueries, and common table expressions,
    # unless TOP or FOR XML is also specified."
    ordered_views = False
    
    def __init__(self, **kwargs):
        ado.ADODatabase.__init__(self, **kwargs)
        self._version = self.version()
        if "SQL Server 2005" in self._version:
            self.connections.isolation_levels.append("SNAPSHOT")
            self.selectwriter = SQLServer2005SelectWriter
    
    def version(self):
        conn = self.connections._get_conn(master=True)
        adov = conn.Version
        data, coldefs = self.fetch("SELECT @@VERSION;", conn)
        sqlv, = data[0]
        conn.Close()
        del conn
        return "ADO Version: %s\n%s" % (adov, sqlv)
    
    ALLOW_SNAPSHOT_ISOLATION = True
    
    def create(self):
        conn = self.connections._get_conn(master=True)
        self.execute_ddl("CREATE DATABASE %s;" % self.qname, conn)
        if self.ALLOW_SNAPSHOT_ISOLATION:
            self.execute_ddl("ALTER DATABASE %s SET ALLOW_SNAPSHOT_ISOLATION ON;" %
                             self.qname, conn)
        conn.Close()
    
    def drop(self):
        conn = self.connections._get_conn(master=True)
        try:
            try:
                self.execute_ddl("DROP DATABASE %s;" % self.qname, conn)
            except ado.pywintypes.com_error, exc:
                if exc.args[2][5] == -2147217865:
                    # com_error: (-2147352567, 'Exception occurred.',
                    #    (0, 'Microsoft SQL Native Client', "Cannot drop the
                    #    database 'dejavu_test', because it does not exist or
                    #    you do not have permission.", None, 0, -2147217865),
                    #    None, 'DROP DATABASE [dejavu_test];')
                    raise errors.MappingError(exc.args[2][2])
        finally:
            conn.Close()
    
    def is_timeout_error(self, exc):
        """If the given exception instance is a lock timeout, return True.
        
        This should return True for errors which arise from transaction
        locking timeouts; for example, if the database prevents 'dirty
        reads' by raising an error.
        """
        # com_error: (-2147352567, 'Exception occurred.',
        #   (0, 'Microsoft OLE DB Provider for SQL Server',
        #    'Timeout expired', None, 0, -2147217871), None,
        #    "UPDATE [testVet] SET [City] = 'Tehachapi' ... ;")
        if not isinstance(exc, ado.pywintypes.com_error):
            return False
        return exc.args[2][5] == -2147217871
