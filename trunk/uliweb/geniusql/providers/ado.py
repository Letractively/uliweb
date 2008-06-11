import sys
# Put COM in free-threaded mode. This first thread will have
# CoInitializeEx called automatically when pythoncom is imported.
sys.coinit_flags = 0

import pythoncom
Empty = pythoncom.Empty
clsctx = pythoncom.CLSCTX_SERVER

import win32com.client

# InvokeTypes args (always pass as *args)
BOF = (1002, 0, 2, (11, 0), ())
EOF = (1006, 0, 2, (11, 0), ())
Recordset_Fields = (0, 0, 2, (9, 0), ())
# This assumes no arguments passed to GetRows
Recordset_GetRows = (1016, 0, 1, (12, 0), ((3, 49), (12, 17), (12, 17)), -1, Empty, Empty)
Recordset_Close = (1014, 0, 1, (24, 0), (),)
Fields_Count = (1, 0, 2, (3, 0), ())
Fields_Item = (0, 0, 2, (9, 0), ((12, 1),))
Field_Name = (1100, 0, 2, (8, 0), ())
Field_Type = (1102, 0, 2, (3, 0), ())
Field_Properties = (500, 0, 2, (9, 0), ())
Property_Value = (0, 0, 2, (12, 0), ())
Connection_Execute = (6, 0, 1, (9, 0), ((8, 1), (16396, 18), (3, 49)))
Connection_OpenSchema = (19, 0, 1, (9, 0), ((3, 1), (12, 17), (12, 17)))

import pywintypes
import datetime
import time

import geniusql
from geniusql import adapters, conns, deparse, errors, sqlwriters

adOpenForwardOnly = 0
adOpenKeyset = 1
adOpenDynamic = 2
adOpenStatic = 3

adLockReadOnly = 1
adLockPessimistic = 2
adLockOptimistic = 3
adLockBatchOptimistic = 4

adSchemaColumns = 4
adSchemaIndexes = 12
adSchemaTables = 20
adSchemaPrimaryKeys = 28

adUseClient = 3

DBCOLUMNFLAGS_WRITE = 0x4
DBCOLUMNFLAGS_WRITEUNKNOWN = 0x8
DBCOLUMNFLAGS_ISFIXEDLENGTH = 0x10
DBCOLUMNFLAGS_ISNULLABLE = 0x20
DBCOLUMNFLAGS_MAYBENULL = 0x40
DBCOLUMNFLAGS_ISLONG = 0x80
DBCOLUMNFLAGS_ISROWID = 0x100
DBCOLUMNFLAGS_ISROWVER = 0x200
DBCOLUMNFLAGS_CACHEDEFERRED = 0x1000


def timedelta_from_com(value, epoch):
    """Return a valid datetime.timedelta from a COM date/time object."""
    return datetime.datetime(value.year, value.month, value.day,
                             value.hour, value.minute, value.second,
                             value.msec) - epoch


class COM_timedelta(adapters.timedelta_to_SQL92DECIMAL):
    
    epoch = datetime.datetime(1899, 12, 30)
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        if isinstance(value, unicode):
            # The value is a stringified NUMERIC of seconds.
            days, secs = divmod(long(value), 86400)
            return datetime.timedelta(int(days), int(secs))
        return timedelta_from_com(value, self.epoch)
    
    def TIMEDELTAADD(op1, op, op2):
        return "(%s %s %s)" % (op1.sql, op, op2.sql)
    TIMEDELTAADD = staticmethod(TIMEDELTAADD)
    
    def DATEADD(dt, td):
        """Return the SQL to add a timedelta to a date."""
        # Days, seconds seems like a good way to avoid overflow.
        return ("DATEADD(dd, FLOOR(%s / 86400), "
                "DATEADD(ss, (%s %% 86400), %s))"
                % (td, td, dt))
    DATEADD = staticmethod(DATEADD)
    
    def DATETIMEADD(dt, td):
        """Return the SQL to add a timedelta to a datetime."""
        return "(%s + (%s / 86400.0))" % (dt, td)
    DATETIMEADD = staticmethod(DATETIMEADD)
    
    def binary_op(self, op1, op, sqlop, op2):
        if op2.pytype is datetime.timedelta:
            return self.TIMEDELTAADD(op1, op, op2)
        else:
            if op == "+":
                if op2.pytype is datetime.date:
                    return self.DATEADD(op2.sql, op1.sql)
                elif op2.pytype is datetime.datetime:
                    return self.DATETIMEADD(op2.sql, op1.sql)
        
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


class COM_time(adapters.time_to_SQL92TIME):
    
    epoch = datetime.datetime(1899, 12, 30)
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        t = timedelta_from_com(value, self.epoch)
        if t.days:
            raise ValueError("Time values greater than 23:59:59 not allowed.")
        h, m = divmod(t.seconds, 3600)
        m, s = divmod(m, 60)
        return datetime.time(int(h), int(m), int(s))


class COM_datetime(adapters.datetime_to_SQL92TIMESTAMP):
    
    epoch = datetime.datetime(1899, 12, 30)
    
    def pull(self, value, dbtype):
        """Return a valid datetime.datetime from a COM date/time object."""
        if value is None:
            return None
        return datetime.datetime(value.year, value.month, value.day,
                                 value.hour, value.minute, value.second,
                                 value.msec)
    
    def DATETIMEADD(dt, td):
        """Return the SQL to add a timedelta to a datetime."""
        return "(%s + (%s / 86400.0))" % (dt, td)
    DATETIMEADD = staticmethod(DATETIMEADD)
    
    def DATETIMEDIFF(d1, d2):
        """Return the SQL to subtract one datetime from another."""
        return "CAST(CAST(%s - %s AS FLOAT) * 86400 AS NUMERIC)" % (d1, d2)
    DATETIMEDIFF = staticmethod(DATETIMEDIFF)
    
    def DATETIMESUB(dt, td):
        """Return the SQL to subtract a timedelta from a datetime."""
        return "(%s - (%s / 86400.0))" % (dt, td)
    DATETIMESUB = staticmethod(DATETIMESUB)
    
    def binary_op(self, op1, op, sqlop, op2):
        if op2.pytype is datetime.datetime:
            if op == "-":
                return self.DATETIMEDIFF(op1.sql, op2.sql)
        elif op2.pytype is datetime.timedelta:
            if op == "+":
                return self.DATETIMEADD(op1.sql, op2.sql)
            elif op == "-":
                return self.DATETIMESUB(op1.sql, op2.sql)
        
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


class COM_date(adapters.date_to_SQL92DATE):
    
    epoch = datetime.datetime(1899, 12, 30)
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        return datetime.date(value.year, value.month, value.day)
    
    def DATEDIFF(d1, d2):
        """Return the SQL to subtract one date from another."""
        # Amazing what a difference a little ".0" can make.
        return "CAST(DATEDIFF(dd, %s, %s) * 86400.0 AS NUMERIC)" % (d2, d1)
    DATEDIFF = staticmethod(DATEDIFF)
    
    def DATEADD(dt, td):
        """Return the SQL to add a timedelta to a date."""
        # Days, seconds seems like a good way to avoid overflow.
        return ("DATEADD(dd, FLOOR(%s / 86400), "
                "DATEADD(ss, (%s %% 86400), %s))"
                % (td, td, dt))
    DATEADD = staticmethod(DATEADD)
    
    def DATESUB(dt, td):
        """Return the SQL to subtract a timedelta from a date."""
        return "(%s - FLOOR(%s / 86400.0))" % (dt, td)
    DATESUB = staticmethod(DATESUB)
    
    def binary_op(self, op1, op, sqlop, op2):
        if op2.pytype is datetime.date:
            if op == "-":
                return self.DATEDIFF(op1.sql, op2.sql)
        elif op2.pytype is datetime.timedelta:
            if op == "+":
                return self.DATEADD(op1.sql, op2.sql)
            elif op == "-":
                return self.DATESUB(op1.sql, op2.sql)
        
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


class ADOSQLDeparser(deparse.SQLDeparser):
    
    # --------------------------- Dispatchees --------------------------- #
    
    def attr_startswith(self, tos, arg):
        self.imperfect = True
        return self.get_expr(tos.sql + " LIKE '" + self.escape_like(arg.sql) + "%'", bool)
    
    def attr_endswith(self, tos, arg):
        self.imperfect = True
        return self.get_expr(tos.sql + " LIKE '%" + self.escape_like(arg.sql) + "'", bool)
    
    def containedby(self, op1, op2):
        self.imperfect = True
        return deparse.SQLDeparser.containedby(self, op1, op2)
    
    def builtins_icontainedby(self, op1, op2):
        # LIKE is already case-insensitive in MS SQL Server;
        # so don't use LOWER().
        if op1.value is not None:
            # Looking for text in a field. Use Like (reverse terms).
            return self.get_expr(op2.sql + " LIKE '%" +
                                 self.escape_like(op1.sql)
                                 + "%'", bool)
        else:
            # Looking for field in (a, b, c)
            atoms = []
            for x in op2.value:
                adapter = op1.dbtype.default_adapter(type(x))
                atoms.append(adapter.push(x, op1.dbtype))
            if atoms:
                return self.get_expr("%s IN (%s)" %
                                     (op1.sql, ", ".join(atoms)), bool)
            else:
                # Nothing will match the empty list, so return none.
                return self.false_expr
        return value
    
    def builtins_istartswith(self, x, y):
        # Like is already case-insensitive in ADO; so don't use LOWER().
        return self.get_expr(x.sql + " LIKE '" + self.escape_like(y.sql) + "%'", bool)
    
    def builtins_iendswith(self, x, y):
        # Like is already case-insensitive in ADO; so don't use LOWER().
        return self.get_expr(x.sql + " LIKE '%" + self.escape_like(y.sql) + "'", bool)
    
    def builtins_ieq(self, x, y):
        # = is already case-insensitive in ADO.
        return self.get_expr(x.sql + " = " + y.sql, bool)
    
    def func__builtin___len(self, x):
        return self.get_expr("Len(" + x.sql + ")", int)


class ADOTable(geniusql.Table):
    
    def _add_column(self, column):
        """Internal function to add the column to the database."""
        coldef = self.schema.columnclause(column)
        # SQL Server doesn't use the "COLUMN" keyword with "ADD"
        self.schema.db.execute_ddl("ALTER TABLE %s ADD %s;" %
                                   (self.qname, coldef))
    
    def _rename(self, oldcol, newcol):
        conn = self.schema.db.connections.get()
        try:
            cat = win32com.client.Dispatch(r'ADOX.Catalog')
            cat.ActiveConnection = conn
            cat.Tables(self.name).Columns(oldcol.name).Name = newcol.name
        finally:
            conn = None
            cat = None
    
    def drop_primary(self):
        """Remove any PRIMARY KEY for this Table."""
        db = self.schema.db
        
        data, _ = db.fetch(adSchemaIndexes, schema=True)
        pknames = [row[5] for row in data
                   if (self.name == row[2]) and row[6]]
        for name in pknames:
            db.execute('ALTER TABLE %s DROP CONSTRAINT %s;'
                       % (self.qname, name))


def connatoms(connstring):
    atoms = {}
    for pair in connstring.split(";"):
        if pair:
            k, v = pair.split("=", 1)
            atoms[k.upper().strip()] = v.strip()
    return atoms


class ADOConnectionManager(conns.ConnectionManager):
    
    # the amount of time to try to close the db connection
    # before raising an exception
    shutdowntimeout = 1 # sec.
    
    # Note these are not the same as a setting of '0' (which would make the
    # timeouts infinite). The value of None means, "use the default".
    ConnectionTimeout = None
    CommandTimeout = None
    
    def _get_conn(self, master=False):
        if master:
            # Must shut down all connections to avoid
            # "being accessed by other users" error.
            self.shutdown()
            
            atoms = connatoms(self.Connect)
            atoms['INITIAL CATALOG'] = "tempdb"
            connectstr = "; ".join(["%s=%s" % (k, v)
                                    for k, v in atoms.iteritems()])
        else:
            connectstr = self.Connect
        
        conn = win32com.client.Dispatch(r'ADODB.Connection')
        if self.ConnectionTimeout is not None:
            conn.ConnectionTimeout = self.ConnectionTimeout
        if self.CommandTimeout is not None:
            conn.CommandTimeout = self.CommandTimeout
        conn.Open(connectstr)
        if self.initial_sql:
            conn._oleobj_.InvokeTypes(
                *(Connection_Execute +
                  (self.initial_sql, pythoncom.Missing, -1)))
        return conn
    
    def _del_conn(self, conn):
        for trial in xrange(self.shutdowntimeout * 10):
            try:
                # This may raise "Operation cannot be performed
                # while executing asynchronously"
                # if a prior operation has not yet completed.
                conn.Close()
                return
            except pywintypes.com_error, e:
                if len(e.args) > 1 and e.args[2]:
                    ecode = e.args[2][-1]
                    if ecode == -2146824577:
                        # "Operation cannot be performed while executing asynchronously"
                        # Try again...
                        time.sleep(0.1)
                        continue
                    elif ecode == -2146824584:
                        # "Operation is not allowed when the object is closed."
                        return
                raise
    
    #                            Transactions                             #
    
    def _start_transaction(self, conn, isolation=None):
        """Start a transaction. Not needed if self.implicit_trans is True."""
        # http://msdn2.microsoft.com/en-us/library/ms173763.aspx
        # "Only one of the isolation level options can be set at a time, and
        # it remains set for that connection until it is explicitly changed
        # ...With one exception, you can switch from one isolation level to
        # another at any time during a transaction. The exception occurs
        # when changing from any isolation level to SNAPSHOT isolation."
        # So swap the usual order of statements to execute SET before BEGIN.
        self.isolate(conn, isolation)
        self.db.execute("BEGIN TRANSACTION;", conn)


class ADOSchema(geniusql.Schema):
    
    tableclass = ADOTable
    
    #                              Discovery                              #
    
    def _get_tables(self, conn=None):
        # cols will be
        # [(u'TABLE_CATALOG', 202), (u'TABLE_SCHEMA', 202), (u'TABLE_NAME', 202),
        # (u'TABLE_TYPE', 202), (u'TABLE_GUID', 72), (u'DESCRIPTION', 203),
        # (u'TABLE_PROPID', 19), (u'DATE_CREATED', 7), (u'DATE_MODIFIED', 7)]
        data, _ = self.db.fetch(adSchemaTables, conn=conn, schema=True)
        return [self.tableclass(str(row[2]), self.db.quote(str(row[2])),
                                self, created=True)
                for row in data
                # Ignore linked and system tables
                if row[3] == "TABLE" and row[1] == self.name]
    
    def _get_table(self, tablename, conn=None):
        # cols will be
        # [(u'TABLE_CATALOG', 202), (u'TABLE_SCHEMA', 202), (u'TABLE_NAME', 202),
        # (u'TABLE_TYPE', 202), (u'TABLE_GUID', 72), (u'DESCRIPTION', 203),
        # (u'TABLE_PROPID', 19), (u'DATE_CREATED', 7), (u'DATE_MODIFIED', 7)]
        data, _ = self.db.fetch(adSchemaTables, conn=conn, schema=True)
        for row in data:
            name = str(row[2])
            if name == tablename and row[1] == self.name:
                return self.tableclass(name, self.db.quote(name),
                                       self, created=True)
        raise errors.MappingError("Table %r not found." % tablename)
    
    def _get_indices(self, table=None, conn=None):
        # cols will be
        # [(u'TABLE_CATALOG', 202), (u'TABLE_SCHEMA', 202), (u'TABLE_NAME', 202),
        # (u'INDEX_CATALOG', 202), (u'INDEX_SCHEMA', 202), (u'INDEX_NAME', 202),
        # (u'PRIMARY_KEY', 11), (u'UNIQUE', 11), (u'CLUSTERED', 11), (u'TYPE', 18),
        # (u'FILL_FACTOR', 3), (u'INITIAL_SIZE', 3), (u'NULLS', 3),
        # (u'SORT_BOOKMARKS', 11), (u'AUTO_UPDATE', 11), (u'NULL_COLLATION', 3),
        # (u'ORDINAL_POSITION', 19), (u'COLUMN_NAME', 202), (u'COLUMN_GUID', 72),
        # (u'COLUMN_PROPID', 19), (u'COLLATION', 2), (u'CARDINALITY', 21),
        # (u'PAGES', 3), (u'FILTER_CONDITION', 202), (u'INTEGRATED', 11)]
        data, _ = self.db.fetch(adSchemaIndexes, conn=conn, schema=True)
        indices = []
        for row in data:
            # I tried passing criteria to OpenSchema, but passing None is
            # not the same as passing pythoncom.Empty (which errors).
            if (row[2] == table.name and row[1] == self.name):
                i = geniusql.Index(row[5], self.db.quote(row[5]),
                                   row[2], row[17], row[7])
                indices.append(i)
        return indices
    
    #                              Container                              #
    
    def _rename(self, oldtable, newtable):
        conn = self.db.connections.get()
        try:
            cat = win32com.client.Dispatch(r'ADOX.Catalog')
            cat.ActiveConnection = conn
            cat.Tables(oldtable.name).Name = newtable.name
        finally:
            conn = None
            cat = None


class ADO_SELECT(sqlwriters.SELECT):
    
    def _get_sql(self):
        """Return an SQL SELECT statement."""
        atoms = ["SELECT"]
        append = atoms.append
        if self.distinct:
            append('DISTINCT')
        # ADO uses 'TOP' instead of 'LIMIT'
        if self.limit is not None:
            append('TOP %d' % self.limit)
        # Microsoft SQL Server has no 'OFFSET' keyword.
        # TODO: provide a generic Stored Procedure for it?
        if self.offset is not None:
            raise NotImplementedError("No such feature: OFFSET")
        append(', '.join(self.input))
        if self.into:
            append("INTO")
            append(self.into)
        if self.fromclause:
            append("FROM")
            append(self.fromclause)
            if self.whereclause:
                append("WHERE")
                append(self.whereclause)
            if self.groupby and len(self.groupby) < len(self.input):
                append("GROUP BY")
                append(", ".join(self.groupby))
            if self.orderby:
                append("ORDER BY")
                append(", ".join(self.orderby))
        return " ".join(atoms)
    sql = property(_get_sql, doc="The SQL string for this SELECT statement.")


class ADOSelectWriter(sqlwriters.SelectWriter):
    statement_class = ADO_SELECT


class ADODatabase(geniusql.Database):
    
    deparser = ADOSQLDeparser
    selectwriter = ADOSelectWriter
    
    #                               Naming                                #
    
    def quote(self, name):
        """Return name, quoted for use in an SQL statement."""
        return '[' + name + ']'
    
    def is_connection_error(self, exc):
        """If the given exception instance is a connection error, return True.
        
        This should return True for errors which arise from broken connections;
        for example, if the database server has dropped the connection socket,
        or is unreachable.
        """
        if isinstance(exc, pywintypes.com_error):
            msg = exc.args[2][2]
            if msg == 'Communication link failure':
                # com_error: (-2147352567, 'Exception occurred.',
                #   (0, 'Microsoft SQL Native Client', 'Communication link failure',
                #    None, 0, -2147467259), None, 'SELECT 42;', 'SELECT 42;')
                return True
            elif msg == 'Shared Memory Provider: No process is on the other end of the pipe.\r\n':
                # com_error: (-2147352567, 'Exception occurred.',
                #   (0, 'Microsoft SQL Native Client',
                #    'Shared Memory Provider: No process is on the other end of the pipe.\r\n',
                #    None, 0, -2147467259), None)
                return True
            elif msg == 'Shared Memory Provider: The pipe is being closed.\r\n':
                return True
            elif msg == 'Operation is not allowed when the object is closed.':
                return True
        return False
    
    def execute(self, sql, conn=None):
        """Return a native response for the given SQL."""
        if conn is None:
            conn = self.connections.get()
##        if isinstance(sql, unicode):
##            sql = sql.encode(self.typeset.encoding)
        
        self.log(sql)
        try:
            bareconn = conn
            if hasattr(conn, 'conn'):
                # 'conn' is a ConnectionWrapper object, which .Open
                # won't accept. Pass the unwrapped connection instead.
                # Note that we CANNOT write "conn = conn.conn", because
                # if we called get() above, we'd lose our only
                # reference to the wrapper and our weakref callback
                # would close the conn before we've executed the SQL.
                bareconn = conn.conn
            
            # Call Execute directly, skipping win32com overhead.
            return bareconn._oleobj_.InvokeTypes(
                *(Connection_Execute + (sql, pythoncom.Missing, -1)))
        except Exception, x:
            if self.is_connection_error(x):
                self.connections.reset(conn)
                bareconn = conn
                if hasattr(conn, 'conn'):
                    bareconn = conn.conn
                return bareconn._oleobj_.InvokeTypes(
                    *(Connection_Execute + (sql, pythoncom.Missing, -1)))
            raise
    
    def fetch(self, sql, conn=None, schema=False):
        """Return rowdata, columns for the given SQL."""
        if conn is None:
            conn = self.connections.get()
        
        res = None
        try:
            if schema:
                # Call OpenSchema(sql) directly, skipping win32com overhead.
                res = conn._oleobj_.InvokeTypes(*(Connection_OpenSchema +
                                                  (sql, Empty, Empty)))
            else:
                res, rows_affected = self.execute(sql, conn)
        except pywintypes.com_error, x:
            if res is not None:
                try:
                    # Close
                    res.InvokeTypes(*Recordset_Close)
                except:
                    pass
                res = None
            x.args += (sql, )
            conn = None
            # "raise x" here or we could get the traceback of the inner try.
            raise x
        
        # Using xrange(Count) is slightly faster than "for x in resFields".
        resFields = res.InvokeTypes(*Recordset_Fields)
        fieldcount = resFields.InvokeTypes(*Fields_Count)
        columns = []
        for i in xrange(fieldcount):
            # Wow. Calling this directly (instead of resFields(i))
            # results in a 29% speedup for a 1-row fetch() of 48 fields.
            x = resFields.InvokeTypes(*(Fields_Item + (i,)))
            
            # Wow. Calling these directly (instead of x.Name, x.Type)
            # results in a 40% speedup for a 1-row fetch() of 48 fields.
            name = x.InvokeTypes(*Field_Name)
            typ = x.InvokeTypes(*Field_Type)
            columns.append((name, typ))
        
        data = []
        if not (res.InvokeTypes(*BOF) and res.InvokeTypes(*EOF)):
            # We tried .MoveNext() and lots of Fields.Item() calls.
            # Using GetRows() beats that time by about 2/3.
            # Inlining GetRows results in a 14% speedup for fetch().
            data = res.InvokeTypes(*Recordset_GetRows)
            
            # Convert cols x rows -> rows x cols
            data = zip(*data)
        try:
            # Close
            res.InvokeTypes(*Recordset_Close)
        except:
            pass
        conn = None
        
        return data, columns


def gen_py():
    """Auto generate .py support for ADO 2.7+"""
    print 'Please wait while support for ADO 2.7+ is verified...'
    
    # Microsoft ActiveX Data Objects 2.8 Library
    result = win32com.client.gencache.EnsureModule('{2A75196C-D9EB-4129-B803-931327F72D5C}', 0, 2, 8)
    if result is not None:
        return
    
    # Microsoft ActiveX Data Objects 2.7 Library
    result = win32com.client.gencache.EnsureModule('{EF53050B-882E-4776-B643-EDA472E8E3F2}', 0, 2, 7)
    if result is not None:
        return
    
    raise ImportError("ADO 2.7 support could not be imported/cached")


if __name__ == '__main__':
    gen_py()
