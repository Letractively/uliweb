import datetime
try:
    import cPickle as pickle
except ImportError:
    import pickle
import re
seq_name = re.compile(r"nextval\('([^:]+)'.*\)")
escape_oct = re.compile(r"[\000-\037\177-\377]")
replace_oct = lambda m: r"\\%03o" % ord(m.group(0))
unescape_oct = re.compile(r"\\(\d\d\d)")
replace_unoct = lambda m: chr(int(m.group(1), 8))
import threading

import geniusql
from geniusql import adapters, dbtypes, deparse, errors


# ------------------------------ Adapters ------------------------------ #


class PgDATE_Adapter(adapters.date_to_SQL92DATE):
    
    def binary_op(self, op1, op, sqlop, op2):
        if op2.pytype is datetime.timedelta:
            # Postgres assumes a "date" is actually midnight, so we
            # need to drop any h:m:s from our interval.
            return "(%s %s date_trunc('day', %s))" % (op1.sql, sqlop, op2.sql)
        elif op2.pytype is datetime.date:
            # Cast to timestamp to achieve an INTERVAL result
            return "(%s::TIMESTAMP %s %s::TIMESTAMP)" % (op1.sql, sqlop, op2.sql)
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


class datetime_to_PgTIMESTAMPTZ_Adapter(adapters.Adapter):
    """Adapter for timezone-naive datetime objects.
    
    Postgres stores all timestamps as UTC internally, adjusting inbound
    values based on their timezone component, and offsetting outbound
    values relative to the Postgres 'timezone' config entry.
    
    This adapter assumes you always want to push and pull datetime objects
    that have no timezone. Therefore, it doesn't supply a timezone atom
    when sending datetime data to Postgres. When retrieving values, any
    offset is silently ignored. That is, in both case, we assume you
    correctly set the connection's timezone attribute.
    """
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        return ("'%04d-%02d-%02d %02d:%02d:%02d'" %
                (value.year, value.month, value.day,
                 value.hour, value.minute, value.second))
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value
        chunks = (value[0:4], value[5:7], value[8:10],
                  value[11:13], value[14:16], value[17:19])
        args = map(int, chunks)
        
        ms, tz = None, None
        mstz = value[19:]
        if mstz:
            signpos = mstz.find("+")
            if signpos == -1:
                signpos = mstz.find("-")
            
            if signpos != -1:
                # We have a timezone. Split it off.
                ms = mstz[:signpos]
            else:
                ms = mstz
            
            if ms:
                ms = int(ms.strip("."))
        
        args.append(ms or 0)
        
        return datetime.datetime(*args)


class datetime_tz_to_PgTIMESTAMPTZ_Adapter(adapters.Adapter):
    """Adapter for timezone-aware datetime objects.
    
    Postgres stores all timestamps as UTC internally, adjusting inbound
    values based on their timezone component, and offsetting outbound
    values relative to the Postgres 'timezone' config entry.
    
    This adapter assumes you always want to push and pull datetime objects
    that have a valid tzinfo. Therefore, it always tries to supply a
    timezone atom when sending datetime data to Postgres. If you push
    a datetime with a tzinfo of None, "+00" is used for the timezone.
    When retrieving values, any offset in the database value is used to
    form a valid tzinfo object for the value (see dbtypes.FixedTimeZone).
    In both directions, we assume you correctly set the connection's
    timezone attribute.
    """
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        
        if value.tzinfo is None:
            h, m = 0, 0
        else:
            h, m = divmod(value.tzinfo.utcoffset(value), 60)
        
        if h < 0:
            h = abs(h)
            sign = "-"
        else:
            sign = "+"
        
        return ("TIMESTAMP WITH TIME ZONE "
                "'%04d-%02d-%02d %02d:%02d:%02d%s%02d:%02d'" %
                (value.year, value.month, value.day,
                 value.hour, value.minute, value.second,
                 sign, h, m))
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value
        chunks = (value[0:4], value[5:7], value[8:10],
                  value[11:13], value[14:16], value[17:19])
        args = map(int, chunks)
        
        ms, tz = None, None
        mstz = value[19:]
        if mstz:
            signpos = mstz.find("+")
            if signpos == -1:
                signpos = mstz.find("-")
            
            if signpos != -1:
                # We have a timezone. Split it off.
                ms, tz = mstz[:signpos], mstz[signpos:]
            else:
                ms, tz = mstz, ""
            
            if ms:
                ms = int(ms.strip("."))
            
            if tz:
                if ":" in tz:
                    h, m = map(int, h.split(":", 1))
                else:
                    h, m = int(tz), 0
                tz = dbtypes.FixedTimeZone((h * 60) + m)
        
        args.append(ms or 0)
        args.append(tz or None)
        return datetime.datetime(*args)


class PgINTERVAL_Adapter(adapters.Adapter):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        # Ignore microseconds for now
        h, m = divmod(value.seconds, 3600)
        m, s = divmod(m, 60)
        return "interval '%s %s:%s:%s'" % (value.days, h, m, s)
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        if isinstance(value, datetime.timedelta):
            return value
        
        # When an interval is returned, it will be of typename
        # "interval" or "TIMESTAMP".
        # Assume it's in ISO format; e.g. "964 days 18:29:45.4769999981"
        # >>> re.split(r"( ?days? ?)", "18:35:49.3222")
        # ['18:35:49.3222']
        # >>> re.split(r"( ?days? ?)", "964 days 18:29:45.4769999981")
        # ['964', ' days ', '18:29:45.4769999981']
        # >>> re.split(r"( ?days? ?)", "964 days")
        # ['964', ' days', '']
        # >>> re.split(r"( ?days? ?)", "1 day")
        # ['1', ' day', '']
        days = 0
        atoms = re.split(r"( ?days? ?)", value)
        hms = atoms.pop()
        if atoms:
            # ...then we have a day component
            days = int(atoms[0])
            if not hms:
                return datetime.timedelta(days)
        
        h, m, s = hms.split(":", 2)
        if h.startswith("-"):
            neg = True
            h = abs(int(h))
        else:
            neg = False
            h = int(h)
        s = (h * 3600) + (int(m) * 60) + float(s)
        if neg:
            s = -s
        
        return datetime.timedelta(days, s)
    
    def binary_op(self, op1, op, sqlop, op2):
        if op2.pytype is datetime.date:
            # Postgres assumes a "date" is actually midnight, so we
            # need to drop any h:m:s from our interval.
            return "(date_trunc('day', %s) %s %s)" % (op1.sql, sqlop, op2.sql)
        elif op2.pytype in (datetime.datetime, datetime.timedelta):
            return "(%s %s %s)" % (op1.sql, sqlop, op2.sql)
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


class Pg_str_to_VARCHAR(adapters.str_to_SQL92VARCHAR):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        if not isinstance(value, str):
            value = value.encode(dbtype.encoding)
        for pat, repl in self.escapes:
            value = value.replace(pat, repl)
        
        # Escape octal sequences
        value = escape_oct.sub(replace_oct, value)
        return "'" + value + "'"
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        # Unescape octal sequences
        value = unescape_oct.sub(replace_unoct, value)
        
        # Return values don't ever seem to be unicode
##        if isinstance(value, unicode):
##            return value.encode(dbtype.encoding)
##        else:
        return value


class Pg_unicode_to_VARCHAR(adapters.unicode_to_SQL92VARCHAR):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        if not isinstance(value, str):
            value = value.encode(dbtype.encoding)
        for pat, repl in self.escapes:
            value = value.replace(pat, repl)
        
        # Escape octal sequences
        value = escape_oct.sub(replace_oct, value)
        return "'" + value + "'"
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        # Unescape octal sequences
        value = unescape_oct.sub(replace_unoct, value)
        # Return values don't ever seem to be unicode
##        if isinstance(value, unicode):
##            return value
##        else:
        return unicode(value, dbtype.encoding)


class PgPickler(adapters.Pickler):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        value = pickle.dumps(value, 2)
        
        if not isinstance(value, str):
            value = value.encode(dbtype.encoding)
        for pat, repl in self.escapes:
            value = value.replace(pat, repl)
        
        # Escape octal sequences
        value = escape_oct.sub(replace_oct, value)
        return "'" + value + "'"
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        # Unescape octal sequences
        value = unescape_oct.sub(replace_unoct, value)
        
        # Return values don't ever seem to be unicode.
##        # Coerce to str for pickle.loads restriction.
##        if isinstance(value, unicode):
##            value = value.encode(dbtype.encoding)
##        else:
##            value = str(value)
        return pickle.loads(value)



class PgFLOAT4_Adapter(adapters.float_to_SQL92REAL):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        # Use quotes to restrict the value to single precision, so that
        # comparisons work between existing values and supplied constants.
        # See http://archives.postgresql.org/pgsql-bugs/2004-02/msg00062.php
        return "'%r'" % value
    
    def compare_op(self, op1, op, sqlop, op2):
        if isinstance(op2.dbtype, FLOAT8):
            # Downcast to the smaller type
            return "(%s %s (%s)::FLOAT4)" % (op1.sql, sqlop, op2.sql)
        elif isinstance(op2.dbtype, (INT2, INT4, INT8, FLOAT4)):
            return "(%s %s %s)" % (op1.sql, sqlop, op2.sql)
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


# ---------------------------- BYTEA Adapters ---------------------------- #


class Pg_str_to_BYTEA(Pg_str_to_VARCHAR):
    """Python str to PostgreSQL bytea adapter.
    
    For the most part, Postgres bytea works like Python's str: a sequence
    of bytes. Certain bytes have to be octal-escaped for consumption by PG.
    
    See http://www.postgresql.org/docs/8.1/interactive/datatype-binary.html
    """
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        def repl(char):
            o = ord(char)
            if o <= 31 or o == 39 or o == 92 or o >= 127:
                return r"\\%03d" % int(oct(o))
            return char
        return "'%s'::bytea" % "".join(map(repl, value))


class Pg_unicode_to_BYTEA(Pg_unicode_to_VARCHAR):
    """Python unicode to PostgreSQL bytea adapter.
    
    For the most part, Postgres bytea works like Python's str: a sequence
    of bytes. Certain bytes have to be octal-escaped for consumption by PG.
    
    See http://www.postgresql.org/docs/8.1/interactive/datatype-binary.html
    """
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        if not isinstance(value, str):
            value = value.encode(dbtype.encoding)
        def repl(char):
            o = ord(char)
            if o <= 31 or o == 39 or o == 92 or o >= 127:
                return r"\\%03d" % int(oct(o))
            return char
        return "'%s'::bytea" % "".join(map(repl, value))


class PgBYTEA_Pickler(PgPickler):
    """Python object to PostgreSQL bytea adapter.
    
    For the most part, Postgres bytea works like Python's str: a sequence
    of bytes. Certain bytes have to be octal-escaped for consumption by PG.
    
    See http://www.postgresql.org/docs/8.1/interactive/datatype-binary.html
    """
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        
        value = pickle.dumps(value, 2)
        
        def repl(char):
            o = ord(char)
            if o <= 31 or o == 39 or o == 92 or o >= 127:
                return r"\\%03d" % int(oct(o))
            return char
        return "'%s'::bytea" % "".join(map(repl, value))


# ---------------------------- DatabaseTypes ---------------------------- #

# See http://www.postgresql.org/docs/8.1/static/datatype.html

# Not implemented here:
# 
# box         rectangular box in the plane
# cidr        IPv4 or IPv6 network address
# circle      circle in the plane
# line        infinite line in the plane
# lseg        line segment in the plane
# macaddr     MAC address
# path        geometric path in the plane
# point       geometric point in the plane
# polygon     closed geometric path in the plane
# timetz      time of day, including time zone


class BOOLEAN(dbtypes.SQL99BOOLEAN):
    """A logical Boolean (true/false)."""
    synonyms = ['BOOL']


class BYTEA(dbtypes.FrozenByteType):
    """A type for binary data ("byte array")."""
    default_adapters = {str: Pg_str_to_BYTEA(),
                        unicode: Pg_unicode_to_BYTEA(),
                        None: PgBYTEA_Pickler(),
                        }
    default_pytype = str
    encoding = 'utf8'

class BIT(dbtypes.SQL92VARCHAR):
    """A fixed-length bit string"""
    variable = False
    default_adapters = {str: Pg_str_to_VARCHAR(),
                        unicode: Pg_unicode_to_VARCHAR(),
                        None: PgPickler(),
                        }

class VARBIT(dbtypes.SQL92VARCHAR):
    """A variable-length bit string."""
    synonyms = ['BIT VARYING']
    variable = True
    default_adapters = {str: Pg_str_to_VARCHAR(),
                        unicode: Pg_unicode_to_VARCHAR(),
                        None: PgPickler(),
                        }

class CHAR(dbtypes.SQL92CHAR):
    """A fixed-length character string."""
    synonyms = ['CHARACTER', 'BPCHAR']
    default_adapters = {str: Pg_str_to_VARCHAR(),
                        unicode: Pg_unicode_to_VARCHAR(),
                        None: PgPickler(),
                        }

class VARCHAR(dbtypes.SQL92VARCHAR):
    """A variable-length character string."""
    synonyms = ['CHARACTER VARYING']
    variable = True
    default_adapters = {str: Pg_str_to_VARCHAR(),
                        unicode: Pg_unicode_to_VARCHAR(),
                        None: PgPickler(),
                        }


class ComparableInfinity(object):
    
    def __cmp__(self, other):
        if isinstance(other, self.__class__):
            return False
        return True
    
    def __str__(self):
        return "Infinity"
    
    def __repr__(self):
        return "%s.%s()" % (self.__module__, self.__class__.__name__)



class TEXT(dbtypes.TEXT):
    """A variable-length character string."""
    # TEXT has no hard byte limit.
    _bytes = max_bytes = ComparableInfinity()
    
    default_adapters = dbtypes.TEXT.default_adapters.copy()
    default_adapters.update({str: Pg_str_to_VARCHAR(),
                             unicode: Pg_unicode_to_VARCHAR(),
                             None: PgPickler(),
                             })

class NAME(dbtypes.TEXT):
    """63-character type for storing system identifiers."""
    _bytes = max_bytes = 63
    
    default_adapters = dbtypes.TEXT.default_adapters.copy()
    default_adapters.update({str: Pg_str_to_VARCHAR(),
                             unicode: Pg_unicode_to_VARCHAR(),
                             None: PgPickler(),
                             })


# Float types.
# "In addition to ordinary numeric values, the floating-point types
# have several special values: Infinity, -Infinity, NaN."

class FLOAT4(dbtypes.SQL92REAL):
    """A single precision floating-point number."""
    synonyms = ['REAL']
    default_adapters = {float: PgFLOAT4_Adapter()}

class FLOAT8(dbtypes.SQL92DOUBLE):
    """A double precision floating-point number."""
    synonyms = ['DOUBLE PRECISION']


class INT2(dbtypes.SQL92SMALLINT):
    """A signed two-byte integer."""
    synonyms = ['SMALLINT']

class INT4(dbtypes.SQL92INTEGER):
    """A signed four-byte integer."""
    
    # "The data types serial and bigserial are not true types, but merely
    # a notational convenience for setting up unique identifier columns
    # (similar to the AUTO_INCREMENT property supported by some other
    # databases).
    synonyms = ['INT', 'INTEGER', 'SERIAL', 'SERIAL4']

class INT8(dbtypes.SQL92INTEGER):
    synonyms = ['BIGINT', 'BIGSERIAL', 'SERIAL8']
    _bytes = max_bytes = 8
    default_adapters = {int: adapters.int_to_SQL92INTEGER(8),
                        long: adapters.int_to_SQL92INTEGER(8),
                        }


class TIMESTAMP(dbtypes.SQL92TIMESTAMP):
    """A date and time."""
    pass

class TIMESTAMPTZ(dbtypes.SQL92TIMESTAMP):
    """A date and time."""
    default_adapters = {datetime.datetime: datetime_to_PgTIMESTAMPTZ_Adapter()}

class DATE(dbtypes.SQL92DATE):
    """A calendar date (year, month, day)."""
    default_adapters = {datetime.date: PgDATE_Adapter()}

class TIME(dbtypes.SQL92TIME):
    """A time of day."""
    pass

class INTERVAL(dbtypes.AdjustablePrecisionType):
    """A time span."""
    default_adapters = {datetime.timedelta: PgINTERVAL_Adapter()}
    default_pytype = datetime.timedelta


class DECIMAL(dbtypes.SQL92DECIMAL):
    """An exact numeric of selectable precision."""
    
    # "In addition to ordinary numeric values, the numeric type allows the
    # special value NaN, meaning "not-a-number". Any operation on NaN yields
    # another NaN. When writing this value as a constant in a SQL command,
    # you must put quotes around it, for example UPDATE table SET x = 'NaN'.
    # On input, the string NaN is recognized in a case-insensitive manner."
    
    synonyms = ['NUMERIC']
    _precision = max_precision = 1000


class MONEY(dbtypes.FrozenPrecisionType):
    """A currency amount."""
    default_pytype = dbtypes.SQL92DECIMAL.default_pytype


class INET(dbtypes.FrozenByteType):
    """An IPv4 or IPv6 host address, and optionally the subnet."""
    # "The inet type holds an IPv4 or IPv6 host address, and optionally
    # the identity of the subnet it is in, all in one field. The subnet
    # identity is represented by stating how many bits of the host address
    # represent the network address (the "netmask"). If the netmask is 32
    # and the address is IPv4, then the value does not indicate a subnet,
    # only a single host. In IPv6, the address length is 128 bits, so 128
    # bits specify a unique host address. Note that if you want to accept
    # networks only, you should use the cidr type rather than inet.
    #
    # The input format for this type is address/y where address is an IPv4
    # or IPv6 address and y is the number of bits in the netmask. If the /y
    # part is left off, then the netmask is 32 for IPv4 and 128 for IPv6,
    # so the value represents just a single host. On display, the /y
    # portion is suppressed if the netmask specifies a single host."
    
    variable = False
    encoding = 'utf8'
    
    default_pytype = str
    default_adapters = {str: adapters.str_to_SQL92VARCHAR(),
                        unicode: adapters.unicode_to_SQL92VARCHAR(),
                        None: adapters.Pickler(),
                        }


class PgTypeSet(dbtypes.DatabaseTypeSet):
    
    known_types = {'float': [FLOAT4, FLOAT8],
                   'varchar': [TEXT, VARCHAR, VARBIT, BYTEA, NAME],
                   'char': [CHAR, BIT],
                   'int': [INT2, INT4, INT8],
                   'bool': [BOOLEAN],
                   'datetime': [TIMESTAMP, TIMESTAMPTZ],
                   'date': [DATE],
                   'time': [TIME],
                   'timedelta': [INTERVAL],
                   'numeric': [DECIMAL],
                   'other': [MONEY, INET],
                   }



class PgDeparser(deparse.SQLDeparser):
    
    like_escapes = [("%", r"\\%"), ("_", r"\\_")]
    
    def builtins_icontainedby(self, op1, op2):
        if op1.value is not None:
            # Looking for text in a field. Use ILike (reverse terms).
            return self.get_expr(op2.sql + " ILIKE '%" +
                                 self.escape_like(op1.sql) + "%'",
                                 bool)
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
        return self.get_expr(x.sql + " ILIKE '" +
                             self.escape_like(y.sql) + "%'", bool)
    
    def builtins_iendswith(self, x, y):
        return self.get_expr(x.sql + " ILIKE '%" +
                             self.escape_like(y.sql) + "'", bool)
    
    def builtins_ieq(self, x, y):
        # ILIKE with no wildcards should behave like ieq.
        return self.get_expr(x.sql + " ILIKE '" +
                             self.escape_like(y.sql) + "'", bool)
    
    def builtins_year(self, x):
        return self.get_expr("date_part('year', " + x.sql + ")", int)
    
    def builtins_month(self, x):
        return self.get_expr("date_part('month', " + x.sql + ")", int)
    
    def builtins_day(self, x):
        return self.get_expr("date_part('day', " + x.sql + ")", int)
    
    def builtins_now(self):
        neg, h, m = adapters.localtime_offset()
        sign = ""
        if neg:
            sign = "-"
        offset = "%s:%s" % (h, m)
        return self.get_expr("(NOW() AT TIME ZONE INTERVAL '%s%s')"
                             % (sign, offset), datetime.datetime)
    
    def builtins_utcnow(self):
        return self.get_expr("NOW()", datetime.datetime)
    
    def builtins_today(self):
        neg, h, m = adapters.localtime_offset()
        sign = ""
        if neg:
            sign = "-"
        offset = "%s:%s" % (h, m)
        return self.get_expr("date_trunc('day', NOW() AT TIME ZONE INTERVAL '%s%s')"
                             % (sign, offset), datetime.date)


class PgIndexSet(geniusql.IndexSet):
    
    def __delitem__(self, key):
        """Drop the specified index."""
        # PG doesn't use DROP INDEX .. ON ..
        self.table.schema.db.execute_ddl('DROP INDEX %s;' % self[key].qname)


class PgTable(geniusql.Table):
    
    implicit_pkey_indices = True
    
    def __init__(self, name, qname, schema, created=False, description=None):
        geniusql.Table.__init__(self, name=name, qname=qname, schema=schema,
                                created=created, description=description)
        self.qname = self.schema.qname + "." + self.qname
    
    def _grab_new_ids(self, idkeys, conn):
        newids = {}
        for idkey in idkeys:
            col = self[idkey]
            seq = self.schema.qname + "." + col.sequence_name
            # Using currval instead of "SELECT last_value FROM %s;"
            # avoids the need for permissions on the sequence.
            data, _ = self.schema.db.fetch("SELECT currval('%s');" % seq, conn)
            newids[idkey] = data[0][0]
        return newids
    
    def drop_primary(self):
        """Remove any PRIMARY KEY for this Table."""
        db = self.schema.db
        
        # Get the OID of the table
        data, _ = db.fetch("SELECT oid FROM pg_class WHERE "
                           "relname = '%s'" % self.name)
        table_OID = data[0][0]
        
        data, _ = db.fetch("SELECT conname, * FROM pg_constraint WHERE conrelid "
                           "= %s AND contype = 'p'" % table_OID)
        for row in data:
            constraint_name = row[0]
            db.execute('ALTER TABLE %s DROP CONSTRAINT "%s";'
                       % (self.qname, constraint_name))


class PgSchema(geniusql.Schema):
    
    tableclass = PgTable
    indexsetclass = PgIndexSet
    
    discover_pg_tables = False
    
    def __init__(self, db, name=None):
        if name is None:
            name = 'public'
        geniusql.Schema.__init__(self, db, name)
    
    def _get_tables(self, conn=None):
        data, _ = self.db.fetch("SELECT oid FROM pg_class WHERE relname = "
                                " 'pg_class' and relkind='r'", conn=conn)
        pgclass_OID = data[0][0]
        
        data, _ = self.db.fetch("SELECT oid FROM pg_namespace WHERE "
                                "nspname = '%s'" % self.name, conn=conn)
        nsoid = data[0][0]
        
        data, _ = self.db.fetch(
            "SELECT c.relname, d.description FROM pg_class c LEFT JOIN "
            "(SELECT description, objoid FROM pg_description WHERE "
            "classoid = %s) AS d ON c.oid = d.objoid WHERE c.relnamespace = "
            "%s and c.relkind = 'r';" % (pgclass_OID, nsoid), conn=conn)
        return [self.tableclass(name, self.db.quote(name), self,
                                created=True, description=description)
                for name, description in data
                if self.discover_pg_tables or not name.startswith("pg_")]
    
    def _get_table(self, tablename, conn=None):
        if (not self.discover_pg_tables) and tablename.startswith("pg_"):
            raise errors.MappingError(
                "Table %r not found. Set schema.discover_pg_tables to True "
                "if you want to discover Postgres system tables (pg_*)." %
                tablename)
        
        data, _ = self.db.fetch(
            "SELECT oid FROM pg_class WHERE relname = 'pg_class'", conn=conn)
        pgclass_OID = data[0][0]
        
        data, _ = self.db.fetch(
            "SELECT oid FROM pg_namespace WHERE nspname = '%s'" % self.name,
            conn=conn)
        nsoid = data[0][0]
        
        data, _ = self.db.fetch(
            "SELECT c.oid, c.relname, c.relkind FROM pg_class c WHERE "
            "c.relnamespace = %s AND c.relname = '%s' AND c.relkind in ('r', 'v')" %
            (nsoid, tablename), conn=conn)
        for table_OID, name, kind in data:
            if name == tablename:
                if kind == 'r':
                    t = self.tableclass(name, self.db.quote(name),
                                        self, created=True)
                else:
                    t = self.viewclass(name, self.db.quote(name),
                                       self, created=True)
                
                # Get the description of the table, if any
                data, _ = self.db.fetch("SELECT description FROM pg_description "
                                        "WHERE objoid = %s and classoid = %s" %
                                        (table_OID, pgclass_OID), conn=conn)
                for cell, in data:
                    t.description = cell
                    break
                
                return t
        raise errors.MappingError("Table %r not found." % tablename)
    
    def _get_columns(self, table, conn=None):
        data, _ = self.db.fetch(
            "SELECT oid FROM pg_namespace WHERE nspname = '%s'" % self.name,
            conn=conn)
        nsoid = data[0][0]
        
        # Get the OID of the table
        data, _ = self.db.fetch(
            "SELECT c.oid FROM pg_class c WHERE c.relnamespace = %s AND "
            "c.relname = '%s' AND c.relkind in ('r', 'v')" %
            (nsoid, table.name), conn=conn)
        table_OID = data[0][0]
        
        # Get index data so we can set col.key if pg_index.indisprimary
        data, _ = self.db.fetch(
            "SELECT indkey FROM pg_index WHERE indrelid = %s AND indisprimary"
            % table_OID, conn=conn)
        if data:
            # indkey is an "array" (we get a space-separated string of ints).
            # These will equal pg_attribute.attnum, below.
            indices = map(int, data[0][0].split(" "))
        else:
            indices = []
        
        # Get column data
        sql = ("SELECT attname, atttypid, attnum, attlen, atttypmod "
               "FROM pg_attribute WHERE attisdropped = False AND "
               "attrelid = %s" % table_OID)
        data, _ = self.db.fetch(sql, conn=conn)
        cols = []
        typeset = self.db.typeset
##        print
##        print self.name, table.name, ">>",
        for row in data:
            name = row[0]
            if name in ('tableoid', 'cmax', 'xmax', 'cmin', 'xmin',
                        'oid', 'ctid'):
                # This is a column which PostgreSQL defines automatically
                continue
##            print name,
            
            # Data type
            dbtype, _ = self.db.fetch("SELECT typname, typlen FROM pg_type "
                                      "WHERE oid = %s" % row[1], conn=conn)
            try:
                dbtypetype = typeset.canonicalize(dbtype[0][0].upper())
            except KeyError, x:
                x.args += ("%s.%s" % (table.name, name),)
                raise
            dbtype = dbtypetype()
            
            c = geniusql.Column(dbtype.default_pytype, dbtype,
                                None, key=row[2] in indices,
                                name=row[0], qname=self.db.quote(row[0]))
            c.adapter = dbtype.default_adapter(c.pytype)
            
            if dbtypetype in (FLOAT4, FLOAT8):
                dbtype.precision = int(row[3])
            elif dbtypetype in (MONEY, DECIMAL):
                dbtype.precision = int((row[4] >> 16) & 65535)
                dbtype.scale = int((row[4] & 65535) - 4)
            
            if dbtypetype is VARCHAR:
                # See http://archives.postgresql.org/pgsql-interfaces/2004-07/msg00021.php
                bytes = int(row[4] - 4)
                if bytes > 0:
                    dbtype.bytes = bytes
                else:
                    raise ValueError("Column %r has illegal size %r" % (name, bytes))
            else:
                bytes = int(row[3])
                if bytes > 0:
                    dbtype.bytes = bytes
            
            # Default value
            default, _ = self.db.fetch(
                "SELECT adsrc FROM pg_attrdef WHERE adnum = %s AND adrelid = %s"
                % (row[2], table_OID), conn=conn)
            if default:
                default = default[0][0]
                if default.startswith("nextval("):
                    # Grab seqname from "nextval('seqname'::[text|regclass])"
                    c.autoincrement = True
                    sname = seq_name.search(default).group(1)
                    if (sname.startswith(self.name + ".") or
                        sname.startswith(self.qname + ".")):
                        sname = sname.split(".", 1)[1]
                    # Don't stick the schema name into c.sequence_name...
                    c.sequence_name = sname
                    # ...but do use the schema name to get min_value
                    sqname = self.qname + "." + sname
                    c.initial = self.db.fetch("SELECT min_value FROM %s" %
                                              sqname, conn=conn)[0][0][0]
                    c.default = None
                else:
                    # adsrc is always a string, so we must cast it using
                    # our guessed type. Be sure to strip any ::typename
                    defval = default.split("::", 1)[0]
                    try:
                        # String defaults have quotes we need to strip
                        defval = defval.strip("'")
                        c.default = c.adapter.pull(defval, c.dbtype)
                    except ValueError:
                        # The default is probably a function like 'now()'.
                        # Keep the whole unmunged string for now.
                        # TODO: set default to an equivalent lambda?
                        c.default = default
            else:
                c.default = None
            
            cols.append(c)
        return cols
    
    def _get_indices(self, table, conn=None):
        data, _ = self.db.fetch("SELECT oid FROM pg_namespace WHERE "
                                "nspname = '%s'" % self.name, conn=conn)
        nsoid = data[0][0]
        
        # Get the OID of the table
        data, _ = self.db.fetch("SELECT c.oid FROM pg_class c WHERE "
                                "c.relnamespace = %s AND "
                                "c.relname = '%s' AND c.relkind = 'r'" %
                                (nsoid, table.name), conn=conn)
        table_OID = data[0][0]
        
        indices = []
        data, _ = self.db.fetch(
            "SELECT pg_class.relname, indkey, indisprimary, "
            "indisunique FROM pg_index LEFT JOIN pg_class "
            "ON pg_index.indexrelid = pg_class.oid WHERE "
            "pg_index.indrelid = %s" % table_OID, conn=conn)
        for row in data:
            iname = row[0]
            q_iname = self.db.quote(iname)
            uniq = bool(row[3])
            # indkey is an "array" (we get a space-separated string of ints).
            cols = map(int, row[1].split(" "))
            for col in cols:
                d, _ = self.db.fetch("SELECT attname FROM pg_attribute "
                                     "WHERE attrelid = %s AND attnum = %s"
                                     % (table_OID, col), conn=conn)
                if not d:
                    # This is probably an index that was added by hand,
                    # without reference to a single existing column.
                    indices.append(geniusql.Index(iname, q_iname, table.name,
                                                  "<unknown>", uniq))
                else:
                    attname = d[0][0]
                    indices.append(geniusql.Index(iname, q_iname, table.name,
                                                  attname, uniq))
        
        return indices
    
    def columnclause(self, column):
        """Return a clause for the given column for CREATE or ALTER TABLE.
        
        This will be of the form "name type [DEFAULT [x | nextval('seq')]]".
        
        PostgreSQL creates the sequence in a separate statement.
        """
        if column.autoincrement:
            default = "nextval('%s.%s')" % (self.qname, column.sequence_name)
        else:
            default = column.default or ""
            if isinstance(default, str):
                if issubclass(column.pytype, basestring):
                    default = column.adapter.push(default, column.dbtype)
            else:
                default = column.adapter.push(default, column.dbtype)
        
        if default:
            default = " DEFAULT %s" % default
        
        return '%s %s%s' % (column.qname, column.dbtype.ddl(), default)
    
    def sequence_name(self, tablename, columnkey):
        "Return the SQL sequence name for the given table name and column key."
        # If you want to use a map from your ORM's property names
        # to DB sequence names, override this method (that's why
        # the tablename must be included in the args).
        sname = "%s_%s_seq" % (tablename, columnkey)
        maxlen = self.db.sql_name_max_length
        if maxlen and len(sname) > maxlen:
            # Postgres (8.2 anyway) seems to truncate the table name to fit.
            sname = "_%s_seq" % columnkey
            sname = tablename[:maxlen - len(sname)] + sname
        return self.db.sql_name(sname)
    
    def index_name(self, table, columnkey):
        """Return the SQL index name for the given table and column key."""
        col = table[columnkey]
        if col.key:
            return self.db.sql_name("%s_pkey" % col.name)
        else:
            return self.db.sql_name("%s_%s_idx" % (table.name, col.name))
    
    def create_sequence(self, table, column):
        """Create a SEQUENCE for the given column."""
        if column.sequence_name is not None:
            self.db.execute_ddl("CREATE SEQUENCE %s.%s START %s;" %
                                (self.qname, column.sequence_name,
                                 column.initial))
    
    def drop_sequence(self, column):
        """Drop a SEQUENCE for the given column."""
        if column.sequence_name is not None:
            self.db.execute_ddl("DROP SEQUENCE %s.%s;" %
                                (self.qname, column.sequence_name))
    
    def create(self):
        if self.name != "public":
            self.db.execute_ddl("CREATE SCHEMA %s" % self.qname)
        self.clear()
    
    def drop(self, restrict=False):
        """Drop this schema (and any contained objects) from the database.
        
        WARNING: This method's default is to drop any objects owned by the
        schema using the CASCADE parameter to DROP SCHEMA. This is contrary
        to the PostgreSQL default! If you wish to drop with the RESTRICT
        parameter instead, set the 'restrict' argument to True.
        """
        if self.name != "public":
            if restrict:
                restrict = 'RESTRICT'
            else:
                restrict = 'CASCADE'
            self.db.execute_ddl("DROP SCHEMA %s %s;" % (self.qname, restrict))
        self.clear()


class PgDatabase(geniusql.Database):
    
    sql_name_max_length = 63
    quote_all = True
    poolsize = 10
    encoding = 'SQL_ASCII'
    
    deparser = PgDeparser
    schemaclass = PgSchema
    typeset = PgTypeSet()
    
    def quote(self, name):
        if self.quote_all:
            name = '"' + name.replace('"', '""') + '"'
        return name
    
    def sql_name(self, name):
        name = geniusql.Database.sql_name(self, name)
        if not self.quote_all:
            name = name.lower()
        return name
    
    def schema(self, name="public"):
        return self.schemaclass(self, name)
    
    def create(self):
        c = self.connections._get_conn(master=True)
        encoding = self.encoding
        if encoding:
            encoding = " WITH ENCODING '%s'" % encoding
        self.execute_ddl("CREATE DATABASE %s%s" % (self.qname, encoding), c)
        self.connections._del_conn(c)
    
    def drop(self):
        c = self.connections._get_conn(master=True)
        self.execute_ddl("DROP DATABASE %s;" % self.qname, c)
        self.connections._del_conn(c)
    
    def _get_schemas(self, conn=None):
        """Return a list of schema names."""
        data, _ = self.fetch("SELECT nspname FROM pg_namespace;", conn=conn)
        return [name for name, in data if name != 'information_schema'
                and not name.startswith('pg_')]


