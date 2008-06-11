"""Adapters from Python to SQL (and back) for the geniusql package.

Adaptation is tricky because semantic adaptation and (server-specific)
syntactic adaptation need to be taken care of for every value in both
directions. For example, when we convert a datetime.date to SQL, we
must both convert the Python value to a string (for example, of the
form '2004-03-01') and apply server-specific formatting (for example,
'#2004-03-01#' for Microsoft Access).

This is an extremely thorny issue and really requires the user to manually
form and apply custom adapters completely by hand. However, in the vast
majority of cases, a reasonable set of default adapters can be generated
by Geniusql. For example, a Column of pytype "datetime.date" can default
to a DateAdapter (but an MSAccess_Date adapter if necessary), based
entirely on the Python type.

This is different than each column or expression's dbtype, which should be
parameterizable to the hilt so that the user can tweak the defaults easily.
That is, the user should be able to write things like:

    col = schema.column(str)
    col.dbtype.encoding = 'ASCII'

...rather than passing all such settings as args to the column() call,
or forcing the user to select a DatabaseType subclass with the desired
characteristics. In short, each Column.adapter is an object that may be
shared among multiple Column (or SQLExpression, etc) objects, whereas
each Column.dbtype should be an isolated DatabaseType instance (not
shared with any other object).
"""

import datetime
try:
    import cPickle as pickle
except ImportError:
    import pickle

from geniusql import typerefs


import sys
# Determine max bytes for int on this system.
maxint_bytes = 1
while True:
    # Signed values have half the max of unsigned (hence the "-1").
    if sys.maxint <= 2 ** ((maxint_bytes * 8) - 1):
        break
    maxint_bytes += 1
# Determine max binary digits for float on this system. Crude but effective.
maxfloat_digits = 2
while True:
    L = (2 ** (maxfloat_digits + 1)) - 1
    if int(float(L)) != L:
        break
    maxfloat_digits += 1
del L, sys



# ------------------------------- Adapters ------------------------------- #


def localtime_offset():
    """Return (neg, h, m) representing the offset from UTC to local time.
    
    neg: If True, the (h, m) values are negative (for example, if the local
        DST timezone is west of UTC).
    """
    import time
    if time.daylight and time.localtime().tm_isdst:
        offset = time.altzone
    else:
        offset = time.timezone
    h, m = divmod(abs(offset), 3600)
    m, s = divmod(m, 60)
    # "altzone...is negative if the local DST timezone is east of UTC",
    # which is the opposite of what we want.
    neg = (offset >= 0)
    return neg, h, m


class Adapter(object):
    """Logic to convert Python values to database values.
    
    Adapters encapsulate all of the logic to express Python values
    in SQL, and to translate retrieved database values to Python.
    
    Simple adapters are not difficult to construct (just remember to
    convert Python None to SQL "NULL"). More complicated adapters can,
    however, be built. For example, given an existing database schema
    that stores dates in a VARCHAR field of the form 'YYYYMMDD', you
    would have to construct a custom Adapter to transform to and from
    Python datetime.date objects. Although it might be possible to use
    the default Adapter and do the transformations in Python on your own,
    that approach would disallow (or cause to fail silently!) many
    comparisons and binary operations in SQL.
    
    Therefore, each Adapter possesses its own binary_op and compare_op
    methods which should return the appropriate SQL. For example:
    
        return "(CAST %s AS FLOAT) %s %s" % (op1.sql, sqlop, op2.sql)
    
    This must be performed in the Adapter (as opposed to the DatabaseType
    or Deparser) in order to support custom transformations like our
    date example, above:
    
        sql1 = ("(CASE WHEN NOT ISNULL(%s) THEN "
                "(CAST (SUBSTRING(%s, 0, 4) + '-' + "
                       "SUBSTRING(%s, 4, 2) + '-' + "
                       "SUBSTRING(%s, 6, 2)) AS DATE)"
                " END)"
                % op1.sql)
    """
    
    def push(self, value, dbtype):
        """Coerce the given Python value to SQL."""
        raise NotImplementedError
    
    def pull(self, value, dbtype):
        """Coerce the given database value to a Python value."""
        raise NotImplementedError
    
    def binary_op(self, op1, op, sqlop, op2):
        """Return the SQL for a binary operation (or raise TypeError).
        
        op1 and op2 will be SQLExpression objects.
        op will be a value from codewalk.binary_repr. Use it to switch
            based on the operator (since sqlop will be provider-specific).
        sqlop will be the matching SQL for the given operator.
        """
        return "%s %s %s" % (op1.sql, sqlop, op2.sql)
    
    def compare_op(self, op1, op, sqlop, op2):
        """Return the SQL for a comparison operation (or raise TypeError).
        
        op1 and op2 will be SQLExpression objects.
        op will be a value from opcode.cmp_op. Use it to switch
            based on the operator (since sqlop will be provider-specific).
        sqlop will be the matching SQL for the given operator.
        """
        return "%s %s %s" % (op1.sql, sqlop, op2.sql)


class bool_to_SQL92BIT(Adapter):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        if value:
            return '1'
        return '0'
    
    def pull(self, value, dbtype):
        # sqlite 2 will return a string, either '0' or '1';
        # sqlite 3 will return an int.
        # This construction should handle both.
        if value is None:
            return None
        return bool(int(value))


class bool_to_SQL99BOOLEAN(Adapter):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        if value:
            return 'TRUE'
        return 'FALSE'
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        if value in ('false', 'False'):
            return False
        return bool(value)


# The great thing about these 3 date coercers is that you can use
# them with (VAR)CHAR/TEXT columns just as well as with DATETIME, etc.
# and comparisons will still work!
class datetime_to_SQL92TIMESTAMP(Adapter):
    
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
                  value[11:13], value[14:16], value[17:19],
                  value[20:26] or 0)
        return datetime.datetime(*map(int, chunks))


class date_to_SQL92DATE(Adapter):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        return "'%04d-%02d-%02d'" % (value.year, value.month, value.day)
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        # These are in order for a reason: datetime is a subclass of date!
        if isinstance(value, datetime.datetime):
            # Psycopg might do this when adding date + timedelta, for instance.
            return value.date()
        elif isinstance(value, datetime.date):
            return value
        
        chunks = (value[0:4], value[5:7], value[8:10])
        return datetime.date(*map(int, chunks))


class time_to_SQL92TIME(Adapter):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        return "'%02d:%02d:%02d'" % (value.hour, value.minute, value.second)
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        if isinstance(value, datetime.time):
            return value
        chunks = (value[0:2], value[3:5], value[6:8])
        return datetime.time(*map(int, chunks))


class timedelta_to_SQL92DECIMAL(Adapter):
    """Adapter for storing datetime.timedelta values in whole seconds.
    
    SQL-92 defines an INTERVAL type, but few commercial databases
    implement it in a reasonable manner. This adapter stores the
    value (days * 86400) + seconds in a DECIMAL field instead,
    which should work with most databases. Note that a custom
    binary_op method MUST be written for each DB which subclasses
    this adapter; there is no default because each RDBMS implements
    date (and especially date interval) arithmetic in its own way.
    
    This adapter uses whole seconds only to avoid problems many
    databases exhibit when comparing two FLOATs for equality in SQL.
    """
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        dec_val = (value.days * 86400) + value.seconds
        return repr(dec_val)
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        days, seconds = divmod(long(value), 86400)
        return datetime.timedelta(int(days), int(seconds))


class float_to_SQL92REAL(Adapter):
    """Adapter from Python float to SQL92-compliant REAL."""
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        # Very important we use repr here so we get all 17 decimal digits.
        return repr(value)
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        return float(value)

class float_to_SQL92DOUBLE(float_to_SQL92REAL):
    """Adapter from Python float to SQL92-compliant DOUBLE."""
    pass


class int_to_SQL92INTEGER(Adapter):
    
    # INTEGER is usually 2 bytes.
    def __init__(self, bytehint=4):
        if maxint_bytes >= bytehint:
            self.pytype = int
        else:
            self.pytype = long
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        return str(value)
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        return self.pytype(value)


class int_to_SQL92SMALLINT(int_to_SQL92INTEGER):
    
    # SMALLINT is usually 2 bytes.
    def __init__(self, bytehint=2):
        if maxint_bytes >= bytehint:
            self.pytype = int
        else:
            self.pytype = long


class str_to_SQL92VARCHAR(Adapter):
    
    # Default escapes for string values.
    escapes = [("'", "''"), ("\\", r"\\")]
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        # This is re-used by unicode_to_SQL92VARCHAR, below
        if not isinstance(value, str):
            value = value.encode(dbtype.encoding)
        for pat, repl in self.escapes:
            value = value.replace(pat, repl)
        return "'" + value + "'"
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        if isinstance(value, unicode):
            return value.encode(dbtype.encoding)
        else:
            return str(value)


class unicode_to_SQL92VARCHAR(str_to_SQL92VARCHAR):
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        if isinstance(value, unicode):
            return value
        if isinstance(value, (basestring, buffer)):
            return unicode(value, dbtype.encoding)
        return unicode(value)


class Pickler(Adapter):
    
    # Default escapes for string values.
    escapes = [("'", "''"), ("\\", r"\\")]
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        # dumps with protocol 0 uses the 'raw-unicode-escape' encoding.
        # We can't use protocol 1 or 2 (which would use UTF-8) because
        # that introduces null bytes into the SQL, which is a no-no.
        value = pickle.dumps(value)
        
        # Now, take pains to re-encode it with dbtype.encoding. As far
        # as I know, Firebird is the only DB that really needs the value
        # re-encoded, but the others seem to survive with this step.
        value = unicode(value, 'raw-unicode-escape').encode(dbtype.encoding)
        
        for pat, repl in self.escapes:
            value = value.replace(pat, repl)
        return "'" + value + "'"
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        # Coerce to str for pickle.loads restriction.
        if isinstance(value, unicode):
            value = value.encode('raw-unicode-escape')
        else:
            # Now, take pains to re-decode it with dbtype.encoding. As far
            # as I know, MySQL is the only DB that really needs the value
            # re-decoded, but the others seem to survive with this step.
            value = unicode(value, dbtype.encoding).encode('raw-unicode-escape')
        return pickle.loads(value)


def normalize_decimal(value):
    """Return the given decimal value, normalized for SQL.
    
    Normalization is by stripping trailing zeros after the decimal point.
    This is critical to allow comparisons between "1", "1.", and "1.0".
    """
    value = str(value)
    if "." in value:
        value = value.rstrip('0')
    else:
        value += "."
    return "'%s'" % value


class number_to_TEXT(Adapter):
    """Adapt a numeric Python type (int|long|float) to a TEXT dbtype."""
    
    def __init__(self, pytype):
        self.pytype = pytype
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        if issubclass(self.pytype, float):
            return "'%r'" % value
        return "'%s'" % str(value)
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        return self.pytype(value)
    
    def binary_op(self, op1, op, sqlop, op2):
        """Return the SQL for a binary operation (or raise TypeError).
        
        op1 and op2 will be SQLExpression objects.
        op will be a value from codewalk.binary_repr.
        sqlop will be the matching SQL for the given operator.
        """
        raise TypeError("Numbers stored in TEXT columns cannot be operated upon.")
    
    def compare_op(self, op1, op, sqlop, op2):
        """Return the SQL for a comparison operation (or raise TypeError).
        
        op1 and op2 will be SQLExpression objects.
        op will be a value from opcode.cmp_op.
        sqlop will be the matching SQL for the given operator.
        """
        if sqlop not in ('=', '!='):
            raise TypeError("Numbers stored in TEXT columns cannot be "
                            "compared except for (in)equality.")
        if op1.value is None:
            val1 = op1.sql
        else:
            val1 = "'%s'" % op1.value
        if op2.value is None:
            val2 = op2.sql
        else:
            val2 = "'%s'" % op2.value
        return "%s %s %s" % (val1, sqlop, val2)


class number_to_SQL92DECIMAL(Adapter):
    """Adapt a numeric Python type (int|long|float) to SQL92DECIMAL."""
    
    def __init__(self, pytype):
        self.pytype = pytype
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        if issubclass(self.pytype, float):
            # Make sure we get all 17 decimal digits.
            return "'" + repr(value) + "'"
        return str(value)
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        return self.pytype(value)


if typerefs.decimal:
    class decimal_to_SQL92DECIMAL(Adapter):
        def push(self, value, dbtype):
            if value is None:
                return 'NULL'
            return str(value)
        
        if hasattr(typerefs.decimal, "Decimal"):
            _decimal_type = typerefs.decimal.Decimal
        else:
            _decimal_type = typerefs.decimal
        
        def pull(self, value, dbtype):
            if value is None:
                return None
            # pywin32 build 205 began support for returning
            # COM Currency objects as decimal objects.
            # See http://pywin32.cvs.sourceforge.net/pywin32/pywin32/CHANGES.txt?view=markup
            if not isinstance(value, self._decimal_type):
                return self._decimal_type(str(value))
            return value
    
    class decimal_to_TEXT(decimal_to_SQL92DECIMAL):
        def push(self, value, dbtype):
            if value is None:
                return 'NULL'
            return normalize_decimal(value)
        
        def binary_op(self, op1, op, sqlop, op2):
            raise TypeError("Numbers stored in TEXT columns cannot be operated upon.")
        
        def compare_op(self, op1, op, sqlop, op2):
            if sqlop not in ('=', '!='):
                raise TypeError("Numbers stored in TEXT columns cannot be "
                                "compared except for (in)equality.")
            if op1.value is None:
                val1 = op1.sql
            else:
                val1 = normalize_decimal(op1.value)
            if op2.value is None:
                val2 = op2.sql
            else:
                val2 = normalize_decimal(op2.value)
            return "%s %s %s" % (val1, sqlop, val2)
    
    class decimal_to_SQL92REAL(Adapter):
        """Adapter from Python decimal to SQL92-compliant REAL."""
        
        def push(self, value, dbtype):
            if value is None:
                return 'NULL'
            return str(value)
        
        if hasattr(typerefs.decimal, "Decimal"):
            _decimal_type = typerefs.decimal.Decimal
        else:
            _decimal_type = typerefs.decimal
        
        def pull(self, value, dbtype):
            if value is None:
                return None
            if isinstance(value, float):
                value = repr(value)
            return self._decimal_type(value)
    
    class decimal_to_SQL92DOUBLE(decimal_to_SQL92REAL):
        """Adapter from Python decimal to SQL92-compliant DOUBLE."""
        pass


if typerefs.fixedpoint:
    class fixedpoint_to_SQL92DECIMAL(Adapter):
        def push(self, value, dbtype):
            if value is None:
                return 'NULL'
            return str(value)
        def pull(self, value, dbtype):
            if value is None:
                return None
            if (isinstance(value, basestring) or
                (typerefs.decimal and
                 isinstance(value, typerefs.decimal.Decimal))):
                # Unicode really screws up fixedpoint; for example:
                # >>> fixedpoint.FixedPoint(u'111111111111111111111111111.1')
                # FixedPoint('111111111111111104952008704.00', 2)
                value = str(value)
                
                scale = 0
                atoms = value.rsplit(".", 1)
                if len(atoms) > 1:
                    scale = len(atoms[-1])
                return typerefs.fixedpoint.FixedPoint(value, scale)
            else:
                return typerefs.fixedpoint.FixedPoint(value)
    
    class fixedpoint_to_TEXT(fixedpoint_to_SQL92DECIMAL):
        def push(self, value, dbtype):
            if value is None:
                return 'NULL'
            if not isinstance(value, typerefs.fixedpoint.FixedPoint):
                value = typerefs.fixedpoint.FixedPoint(value)
            return normalize_decimal(value)
        
        def binary_op(self, op1, op, sqlop, op2):
            raise TypeError("Numbers stored in TEXT columns cannot be operated upon.")
        
        def compare_op(self, op1, op, sqlop, op2):
            if sqlop not in ('=', '!='):
                raise TypeError("Numbers stored in TEXT columns cannot be "
                                "compared except for (in)equality.")
            if op1.value is None:
                val1 = op1.sql
            else:
                val1 = normalize_decimal(op1.value)
            if op2.value is None:
                val2 = op2.sql
            else:
                val2 = normalize_decimal(op2.value)
            return "%s %s %s" % (val1, sqlop, val2)
    
    class fixedpoint_to_SQL92REAL(Adapter):
        """Adapter from Python fixedpoint to SQL92-compliant REAL."""
        
        def push(self, value, dbtype):
            if value is None:
                return 'NULL'
            return str(value)
        
        def pull(self, value, dbtype):
            if value is None:
                return None
            if isinstance(value, float):
                value = repr(value)
            return typerefs.fixedpoint.FixedPoint(value)
    
    class fixedpoint_to_SQL92DOUBLE(fixedpoint_to_SQL92REAL):
        """Adapter from Python fixedpoint to SQL92-compliant DOUBLE."""
        pass

