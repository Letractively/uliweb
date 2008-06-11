import datetime

from geniusql import adapters, conns, dbtypes, objects, sqlwriters, typerefs
from geniusql import isolation as _isolation
from geniusql.providers import ado

import win32com.client


# ------------------------------ Adapters ------------------------------ #


class MSAccess_timedelta(ado.COM_timedelta):
    
    def TIMEDELTAADD(op1, op, op2):
        return "CDate(%s %s %s)" % (op1.sql, op, op2.sql)
    TIMEDELTAADD = staticmethod(TIMEDELTAADD)
    
    def DATETIMEADD(dt, td):
        """Return the SQL to add a timedelta to a datetime."""
        return "CDate(%s + %s)" % (dt, td)
    DATETIMEADD = staticmethod(DATETIMEADD)
    
    def DATEADD(dt, td):
        """Return the SQL to add a timedelta to a date."""
        # Important to use Fix (instead of CLng, for example)
        # for negative numbers.
        return "DateAdd('d', Fix(%s), %s)" % (td, dt)
    DATEADD = staticmethod(DATEADD)
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        # This took a lot of work to get right, because timedelta
        # seconds are positive even if the days are negative.
        # So is the fractional portion of a negative Access Date!
        # Very important we use repr here so we get all 17 decimal
        # digits in the float.
        return ("CDate(#12/30/1899# + (%r) + %r)" %
                (value.days, (value.seconds / 86400.0)))

class MSAccess_date(ado.COM_date):
    
    def DATEADD(dt, td):
        """Return the SQL to add a timedelta to a date."""
        # Important to use Fix (instead of CLng, for example)
        # for negative numbers.
        return "DateAdd('d', Fix(%s), %s)" % (td, dt)
    DATEADD = staticmethod(DATEADD)
    
    def DATEDIFF(d1, d2):
        """Return the SQL to subtract one date from another."""
        # Important to use Fix (instead of CLng, for example)
        # for negative numbers.
        return "CDate(Fix(%s) - Fix(%s))" % (d1, d2)
    DATEDIFF = staticmethod(DATEDIFF)
    DATESUB = DATEDIFF
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        return '#%s/%s/%s#' % (value.month, value.day, value.year)


class MSAccess_datetime(ado.COM_datetime):
    
    def DATETIMEADD(dt, td):
        """Return the SQL to add a timedelta to a datetime."""
        return "CDate(%s + %s)" % (dt, td)
    DATETIMEADD = staticmethod(DATETIMEADD)
    
    def DATETIMEDIFF(d1, d2):
        """Return the SQL to subtract one (datetime or date expr) from another."""
        return "CDate(%s - %s)" % (d1, d2)
    DATETIMEDIFF = staticmethod(DATETIMEDIFF)
    DATETIMESUB = DATETIMEDIFF
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        return ('#%s/%s/%s %02d:%02d:%02d#' %
                (value.month, value.day, value.year,
                 value.hour, value.minute, value.second))

class MSAccess_time(ado.COM_time):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        return '#%02d:%02d:%02d#' % (value.hour, value.minute, value.second)


class CURRENCY_float(adapters.float_to_SQL92DOUBLE):
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        if isinstance(value, tuple):
            # See http://groups.google.com/group/comp.lang.python/
            #           browse_frm/thread/fed03c64735c9e9c
            value = map(long, value)
            return ((value[1] & 0xFFFFFFFFL) | (value[0] << 32)) / 1e4
        return float(value)

class CURRENCY_decimal(adapters.decimal_to_SQL92DECIMAL):
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        # pywin32 build 205 began support for returning
        # COM Currency objects as decimal objects.
        # See http://pywin32.cvs.sourceforge.net/pywin32/pywin32/CHANGES.txt?view=markup
        if not isinstance(value, typerefs.decimal.Decimal):
            # See http://groups.google.com/group/comp.lang.python/
            #           browse_frm/thread/fed03c64735c9e9c
            value = map(long, value)
            value = (value[1] & 0xFFFFFFFFL) | (value[0] << 32)
            return typerefs.decimal.Decimal(value) / 10000
        return value

if typerefs.fixedpoint:
    class CURRENCY_FixedPoint(adapters.fixedpoint_to_SQL92DECIMAL):
        
        def pull(self, value, dbtype):
            if value is None:
                return None
            if isinstance(value, typerefs.decimal.Decimal):
                value = str(value)
                scale = 0
                atoms = value.rsplit(".", 1)
                if len(atoms) > 1:
                    scale = len(atoms[-1])
                return typerefs.fixedpoint.FixedPoint(value, scale)
            else:
                # See http://groups.google.com/group/comp.lang.python/
                #           browse_frm/thread/fed03c64735c9e9c
                value = map(long, value)
                value = (value[1] & 0xFFFFFFFFL) | (value[0] << 32)
                return typerefs.fixedpoint.FixedPoint(value, 4) / 1e4



def _compare_strings(self, op1, op, sqlop, op2):
    """Return the SQL for a comparison operation (or raise TypeError).
    
    op1 and op2 will be SQLExpression objects.
    op will be an index into opcode.cmp_op.
    sqlop will be the matching SQL for the given operator.
    """
    # ADO comparison operators for strings are case-insensitive.
    if op in ('<', '<=', '==', '!=', '>', '>='):
        # Some operations on strings can be emulated with the
        # StrComp function. Oddly enough, "StrComp(x, y) op 0"
        # is the same as "x op y" in most cases.
        return "StrComp(%s, %s) %s 0" % (op1.sql, op2.sql, sqlop)
    else:
        raise TypeError("Microsoft Access cannot compare strings "
                        "using %r in a case-sensitive way." % sqlop)

class MSAccess_VARCHAR_Adapter(adapters.str_to_SQL92VARCHAR):
    escapes = [("'", "''")]
    compare_op = _compare_strings

class MSAccess_UNICODE_Adapter(adapters.unicode_to_SQL92VARCHAR):
    escapes = [("'", "''")]
    compare_op = _compare_strings

class MSAccess_Pickler(adapters.Pickler):
    escapes = [("'", "''")]
    compare_op = _compare_strings


# ---------------------------- DatabaseTypes ---------------------------- #

# These are Access 2000+ types.
# See http://msdn2.microsoft.com/en-us/library/aa140015(office.10).aspx
# http://msdn2.microsoft.com/en-us/library/ms714540.aspx
# http://office.microsoft.com/en-us/access/HP010322481033.aspx

# "A Text field can store up to 255 characters, but the default field size
# is 50 characters. A Memo field can store up to 65,536 characters. If you
# want to store formatted text or long documents, you should create an OLE
# Object field instead of a Memo field. Both Text and Memo data types store
# only the characters entered in a field; space characters for unused
# positions in the field aren't stored. You can sort or group on a Text
# field or a Memo field, but Access only uses the first 255 characters
# when you sort or group on a Memo field."

class TEXT(dbtypes.SQL92VARCHAR):
    
    # Actually 255 chars, 2 bytes per char unless compressed
    max_bytes = 255
    bytes = 255
    variable = True
    encoding = 'ISO-8859-1'
    
    # "With the Microsoft Jet 4.0 database engine, all data for the TEXT
    # data types are now stored in the Unicode 2-byte character
    # representation format. It replaces the Multi-byte Character Set
    # (MBCS) format that was used in previous versions. Although Unicode
    # representation requires more space to store each character, columns
    # with TEXT data types can be defined to automatically compress the
    # data if it is possible to do so.
    # 
    # When you create TEXT data types with SQL, the Unicode compression
    # property defaults to No. To set the Unicode compression property
    # to Yes, use the WITH COMPRESSION (or WITH COMP) keywords at the
    # field-level declaration."
    with_compression = False
    
    default_adapters = dbtypes.SQL92VARCHAR.default_adapters.copy()
    default_adapters.update({str: MSAccess_VARCHAR_Adapter(),
                             unicode: MSAccess_UNICODE_Adapter(),
                             None: MSAccess_Pickler(),
                             })
    
    def ddl(self):
        """Return the type for use in CREATE or ALTER statements."""
        withcomp = ""
        if self.with_compression:
            withcomp = " WITH COMPRESSION"
        return "%s(%s)%s" % (self.__class__.__name__, self.bytes, withcomp)


class MEMO(dbtypes.TEXT):
    # MEMO is 1 GB max when set programatically (only 64K when set
    # in Access UI). But then, 1 GB is the limit for the whole DB.
    # Note that OpenSchema will return a DATA_TYPE of "WCHAR".
    synonyms = ['WCHAR']
    bytes = max_bytes = 65535           # (2.14 GB if not binary data)
    variable = True
    encoding = 'ISO-8859-1'
    
    default_adapters = dbtypes.TEXT.default_adapters.copy()
    default_adapters.update({str: MSAccess_VARCHAR_Adapter(),
                             unicode: MSAccess_UNICODE_Adapter(),
                             None: MSAccess_Pickler(),
                             })


class TINYINT(dbtypes.SQL92SMALLINT):
    synonyms = ['INTEGER1', 'BYTE']
    bytes = max_bytes = 1
    signed = False

class SMALLINT(dbtypes.SQL92SMALLINT):
    synonyms = ['SHORT', 'INTEGER2']

class INTEGER(dbtypes.SQL92INTEGER):
    synonyms = ['LONG', 'INT', 'INTEGER4']


class REAL(dbtypes.SQL92REAL):
    synonyms = ['SINGLE', 'FLOAT4', 'IEEESINGLE']

class FLOAT(dbtypes.SQL92DOUBLE):
    synonyms = ['DOUBLE', 'FLOAT8', 'IEEEDOUBLE', 'NUMBER']


class DECIMAL(dbtypes.SQL92DECIMAL):
    synonyms = ['NUMERIC', 'DEC']
    
    # "...precision, the default is 18 and the maximum allowed value is 28.
    # For the scale, the default is 0 and the maximum allowed value is 28."
    _precision = 18
    max_precision = 28
    scale = 0
    max_scale = 28


class CURRENCY(dbtypes.FrozenPrecisionType):
    
    # "The CURRENCY data type is used to store numeric data that contains
    # up to 15 digits on the left side of the decimal point, and up to 4
    # digits on the right. It uses 8 bytes of memory for storage, and its
    # only synonym is MONEY."
    synonyms = ['MONEY']
    
    precision = max_precision = 19
    scale = property(lambda self: 4, lambda self, value: None)
    
    default_adapters = {float: CURRENCY_float()}
    default_pytype = float
    if typerefs.fixedpoint:
        default_pytype = typerefs.fixedpoint.FixedPoint
        default_adapters[typerefs.fixedpoint.FixedPoint] = CURRENCY_FixedPoint()
    if typerefs.decimal:
        if hasattr(typerefs.decimal, "Decimal"):
            default_pytype = typerefs.decimal.Decimal
            default_adapters[typerefs.decimal.Decimal] = CURRENCY_decimal()
        else:
            default_pytype = typerefs.decimal.Decimal
            default_adapters[typerefs.decimal] = CURRENCY_decimal()


class YESNO(dbtypes.SQL99BOOLEAN):
    # "The BOOLEAN data types are logical types that result in either True
    # or False values. They use 1 byte of memory for storage, and their
    # synonyms are BIT, LOGICAL, LOGICAL1, and YESNO. A True value is
    # equal to -1 while a False value is equal to 0."
    pass


class BINARY(dbtypes.AdjustableByteType):
    # "The BINARY data type is used to store a small amount of any type
    # of data in its native, binary format. It uses 1 byte of memory for
    # each character stored, and you can optionally specify the number
    # of bytes to be allocated. If the number of bytes is not specified,
    # it defaults to 510 bytes, which is the maximum number of bytes
    # allowed. Its synonyms are BINARY, VARBINARY, and BINARY VARYING.
    # The BINARY data type is not available in the Access user interface."
    synonyms = ['VARBINARY', 'BINARY VARYING']
    bytes = 510
    max_bytes = 510
    variable = False


class DATETIME(dbtypes.SQL92TIMESTAMP):
    # "The DATETIME data type is used to store date, time, and combination
    # date/time values for the years ranging from 100 to 9999.
    # It uses 8 bytes of memory for storage, and its synonyms are
    # DATE, TIME, DATETIME, and TIMESTAMP.
    synonyms = ['DATE', 'TIME', 'TIMESTAMP']
    _min = datetime.datetime(100, 1, 1)
    _max = datetime.datetime(9999, 12, 31)
    
    default_adapters = {datetime.datetime: MSAccess_datetime(),
                        datetime.date: MSAccess_date(),
                        datetime.time: MSAccess_time(),
                        datetime.timedelta: MSAccess_timedelta(),
                        }


class MSAccessTypeSet(dbtypes.DatabaseTypeSet):
    
    known_types = {'float': [REAL, FLOAT],
                   'varchar': [TEXT, MEMO],
                   'char': [BINARY],
                   'int': [TINYINT, SMALLINT, INTEGER],
                   'bool': [YESNO],
                   'datetime': [DATETIME],
                   'date': [DATETIME],
                   'time': [DATETIME],
                   'timedelta': [DATETIME],
                   'numeric': [DECIMAL],
                   'other': [CURRENCY],
                   }


class MSAccessDeparser(ado.ADOSQLDeparser):
    sql_cmp_op = {'<': '<',
                  '<=': '<=',
                  '==': '=',
                  '!=': '<>',
                  '>': '>',
                  '>=': '>=',
                  'in': 'in',
                  'not in': 'not in',
                  }
    
    like_escapes = [("[", "[[]"), ("%", "[%]"), ("_", "[_]"),
                    ("?", "[?]"), ("#", "[#]")]
    
    def builtins_now(self):
        return self.get_expr("Now()", datetime.datetime)
    
    def builtins_today(self):
        return self.get_expr("DateValue(Now())", datetime.date)
    
    def builtins_year(self, x):
        return self.get_expr("Year(" + x.sql + ")", int)
    
    def builtins_month(self, x):
        return self.get_expr("Month(" + x.sql + ")", int)
    
    def builtins_day(self, x):
        return self.get_expr("Day(" + x.sql + ")", int)


class MSAccessTable(ado.ADOTable):
    
    def _grab_new_ids(self, idkeys, conn):
        data, _ = self.schema.db.fetch("SELECT @@IDENTITY;", conn)
        return {idkeys[0]: data[0][0]}


class MSAccessConnectionManager(ado.ADOConnectionManager):
    
    poolsize = 0
    default_isolation = "READ UNCOMMITTED"
    isolation_levels = ["READ UNCOMMITTED",]
    
    def _set_factory(self):
        # MS Access can't use a pool, because there doesn't seem
        # to be a commit timeout. See http://support.microsoft.com/kb/200300
        # for additional synchronization issues.
        self._factory = conns.SingleConnection(self._get_conn, self._del_conn,
                                               self.retry)
    
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
            isolation = isolation.name
            if isolation not in self.isolation_levels:
                raise ValueError("IsolationLevel %r not allowed by %s."
                                 % (isolation, self.__class__.__name__))
        
        # No action to take, since you can't actually set iso level.
        pass


class MSAccessSchema(ado.ADOSchema):
    
    tableclass = MSAccessTable
    
    # See http://www.carlprothman.net/Technology/DataTypeMapping/tabid/97/Default.aspx
    adotypes = {
        # MS Access             ADO Name
        2: SMALLINT,            # SMALLINT
        3: INTEGER,             # INTEGER
        4: REAL,                # SINGLE
        5: FLOAT,               # DOUBLE
        6: CURRENCY,            # CURRENCY
        7: DATETIME,            # DATE (Access 97)
        11: YESNO,              # BOOLEAN
        17: TINYINT,            # UNSIGNEDTINYINT
        128: BINARY,            # BINARY
        130: MEMO,              # WCHAR
        131: DECIMAL,           # NUMERIC (Access 2000)
        135: DATETIME,          # DBTIMESTAMP (ODBC 97)
        200: TEXT,              # VARCHAR (Access 97)
        201: MEMO,              # LONGVARCHAR (Access 97)
        202: TEXT,              # VARWCHAR (Access 2000)
        203: MEMO,              # LONGVARWCHAR (Access 2000+)
        # 205: OLEOBJECT,       # LONGVARBINARY
        # 0: EMPTY,
        # 8: BSTR, 9: IDISPATCH, 10: ERROR,
        # 12: VARIANT, 13: IUNKNOWN, 14: DECIMAL, 16: TINYINT,
        # 18: UNSIGNEDSMALLINT, 19: UNSIGNEDINT, 20: BIGINT,
        # 21: UNSIGNEDBIGINT, 72: GUID,
        # 129: CHAR, 
        # 132: USERDEFINED, 133: DBDATE, 134: DBTIME,
        # 204: VARBINARY,
    }
    
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
                   if (row[2] == table.name and
                       row[1] == self.name) and row[6]]
        
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
                if issubclass(pytype, (int, long, float)):
                    # We may have stuck extraneous quotes in the default
                    # value when using numeric defaults with MSAccess.
                    if default.startswith("'") and default.endswith("'"):
                        default = default[1:-1]
                default = pytype(default)
            
            name = str(row[3])
            c = objects.Column(pytype, dbtype, default,
                               key=(name in pknames),
                               name=name, qname=self.db.quote(name))
            
            if dbtypetype in typer.known_types['int']:
                dbtype.bytes = row[15]
            elif dbtypetype in typer.known_types['float']:
                dbtype.precision = row[15]
                dbtype.scale = row[16]
            elif dbtypetype in typer.known_types['numeric']:
                dbtype.precision = row[15]
                dbtype.scale = row[16]
            elif dbtypetype is MEMO:
                pass
            elif (dbtypetype in typer.known_types['char'] or
                  dbtypetype in typer.known_types['varchar']):
                if row[13]:
                    # row[13] will be a float
                    dbtype.bytes = int(row[13])
                else:
                    # I'm kinda guessing on this. If we use "MEMO" in an
                    # MSAccess CREATE statement, it comes back as "WCHAR",
                    # and seems to support over 65536 bytes.
                    dbtype.bytes = (2 ** 31) - 1
            
            c.adapter = dbtype.default_adapter(pytype)
            cols.append(c)
        
        # Horrible hack to get autoincrement property
        if conn is None:
            conn = self.db.connections._factory()
        try:
            sql = "SELECT * FROM %s WHERE FALSE;" % table.qname
            bareconn = conn
            if hasattr(conn, 'conn'):
                # 'conn' is a ConnectionWrapper object, which .Open
                # won't accept. Pass the unwrapped connection instead.
                bareconn = conn.conn
            
            # Call conn.Open(sql) directly, skipping win32com overhead.
            res, rows_affected = conn._oleobj_.InvokeTypes(6, 0, 1, (9, 0),
                                            ((8, 1), (16396, 18), (3, 49)),
                                            # *args =
                                            sql, ado.pythoncom.Missing, -1)
        except ado.pywintypes.com_error, x:
            try:
                res.InvokeTypes(*ado.Recordset_Close)
            except:
                pass
            res = None
            x.args += (sql, )
            conn = None
            
            try:
                # Return no columns when inspecting system tables
                if "no read permission" in x.args[2][2]:
                    conn = None
                    return []
            except IndexError:
                pass
            
            # "raise x" here or we could get the traceback of the inner try.
            raise x
        
        resFields = res.InvokeTypes(*ado.Recordset_Fields)
        for c in cols:
            f = resFields.InvokeTypes(0, 0, 2, (9, 0), ((12, 1),), c.name)
            fprops = f.InvokeTypes(*ado.Field_Properties)
            fprop = fprops.InvokeTypes(0, 0, 2, (9, 0), ((12, 1), ), "ISAUTOINCREMENT")
            c.autoincrement = fprop.InvokeTypes(*ado.Property_Value)
            if c.autoincrement:
                # Grumble. Get the Seed value from ADOX.
                try:
                    cat = win32com.client.Dispatch(r'ADOX.Catalog')
                    cat.ActiveConnection = conn
                    adoxcol = cat.Tables(table.name).Columns(c.name)
                    c.initial = adoxcol.Properties('Seed').Value
                    adoxcol = None
                finally:
                    cat = None
        
        try:
            res.InvokeTypes(*ado.Recordset_Close)
        except:
            pass
        conn = None
        
        return cols
    
    def columnclause(self, column):
        """Return a clause for the given column for CREATE or ALTER TABLE.
        
        This will be of the form:
            name type [DEFAULT x|AUTOINCREMENT(initial, 1)]
        """
        ddl = column.dbtype.ddl()
        
        if column.autoincrement:
            if column.dbtype.default_pytype not in (int, long):
                raise ValueError("Microsoft Access does not allow COUNTER "
                                 "columns of type %r" % dbtype)
            ddl = " COUNTER(%s, 1) NOT NULL" % column.initial
        else:
            # MS Access does not allow a column to have
            # both an AUTOINCREMENT clause and a DEFAULT clause.
            default = column.default or None
            if default:
                defspec = column.adapter.push(default, column.dbtype)
                if isinstance(default, (int, long)):
                    # Crazy quote hack to get a numeric default to work.
                    defspec = "'%s'" % defspec
                ddl = "%s DEFAULT %s" % (ddl, defspec)
        
        return '%s %s' % (column.qname, ddl)


class MSAccess_DELETE(sqlwriters.DELETE):
    """A DELETE SQL statement. Usually produced by a DeleteWriter.
    
    input: a list of SQL expressions, one for each column in the DELETE clause.
    """
    
    def _get_sql(self):
        """Return an SQL DELETE statement."""
        atoms = ["DELETE"]
        append = atoms.append
        if self.input:
            append(', '.join(self.input))
        else:
            # MS Access needs an asterisk to delete
            append('*')
        if self.fromclause:
            append("FROM")
            append(self.fromclause)
            if self.whereclause:
                append("WHERE")
                append(self.whereclause)
        return " ".join(atoms)
    sql = property(_get_sql, doc="The SQL string for this DELETE statement.")


class MSAccessDeleteWriter(sqlwriters.DeleteWriter):
    statement_class = MSAccess_DELETE


class MSAccessDatabase(ado.ADODatabase):
    
    deparser = MSAccessDeparser
    typeset = MSAccessTypeSet()
    connectionmanager = MSAccessConnectionManager
    schemaclass = MSAccessSchema
    deletewriter = MSAccessDeleteWriter
    
    ordered_views = False
    
    def version(self):
        conn = win32com.client.Dispatch(r'ADODB.Connection')
        v = conn.Version
        del conn
        return "ADO Version: %s" % v
    
    def create(self):
        # By not providing an Engine Type, it defaults to 5 = Access 2000.
        cat = win32com.client.Dispatch(r'ADOX.Catalog')
        cat.Create(self.connections.Connect)
        cat.ActiveConnection.Close()
    
    def drop(self):
        # Must shut down our only connection to avoid
        # "Permission denied" error on os.remove call below.
        self.connections.shutdown()
        
        import os
        # This should accept relative or absolute paths
        if os.path.exists(self.name):
            os.remove(self.name)

