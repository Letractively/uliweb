# Any otherwise-unattributed quotes in this module are probably from:
# http://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt

import datetime
import math

from geniusql import adapters, errors, typerefs


class FixedTimeZone(datetime.tzinfo):
    """Fixed offset in minutes east from UTC."""
    
    def __init__(self, offset):
        self._offset = offset
    
    def utcoffset(self, dt):
        return datetime.timedelta(minutes = self._offset)
    
    def tzname(self, dt):
        return "FixedTimeZone%s" % self._offset
    
    def dst(self, dt):
        return datetime.timedelta(0)
    
    def __repr__(self):
        cls = self.__class__
        return "%s.%s(%r)" % (cls.__module__, cls.__name__, self._offset)



# ---------------------------- Base classes ---------------------------- #


class DatabaseType(object):
    """A database type, such as 'REAL' or 'DATE' (with optional details).
    
    DatabaseType is a place to collect information about each type used by
    each provider; all providers should provide a separate subclass of this
    for each (canonical) type they provide.
    
    Each Column (and SQLExpression) should get its own instance of a
    provider-specific subclass of this class.
    """
    
    # These are class-level attributes and should not be overridden or copied
    # (they're only used at the class level, so it wouldn't make much sense).
    default_pytype = None
    default_adapters = None
    synonyms = []
    
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    
    def __repr__(self):
        attrs = ", ".join(["%s=%r" % (k, getattr(self, k))
                           for k in self.__dict__])
        return "%s.%s(%s)" % (self.__module__, self.__class__.__name__, attrs)
    
    def __copy__(self):
        return self.__class__(**self.__dict__)
    copy = __copy__
    
    def ddl(self):
        """Return the type for use in CREATE or ALTER statements."""
        return self.__class__.__name__
    
    def default_adapter(self, pytype):
        """Return a default adapter instance for the given pytype, dbtype."""
        # Use try for the common case where the pytype is in the dict.
        try:
            return self.default_adapters[pytype]
        except KeyError:
            defaults = self.default_adapters
            if None in defaults:
                return defaults[None]
            for p in pytype.__bases__:
                if p in defaults:
                    return defaults[p]
        
        raise TypeError("%s has no default adapter for %s. Looked for: "
                        "%s, None, %s" %
                        (self, pytype, pytype,
                         ", ".join([repr(x) for x in pytype.__bases__])))


class FrozenByteType(DatabaseType):
    """DatabaseType which specifies a frozen 'bytes' attribute.
    
    A FrozenByteType does not imply that the type is a fixed-byte
    type like CHAR as opposed to a variable-byte type like VARCHAR
    (that difference is specified in the "variable" attribute).
    Instead, a Frozen* type implies that the byte limit is not
    user-specifiable; for example, Microsoft Access' MEMO type
    is always 65535 bytes, and takes no size argument in DDL.
    """
    
    _bytes = max_bytes = 255
    def _get_bytes(self):
        return self._bytes
    def _set_bytes(self, value):
        pass
    bytes = property(_get_bytes, _set_bytes,
                     doc="The bytes used for all instances of this type.")


class AdjustableByteType(DatabaseType):
    """DatabaseType which specifies an adjustable 'bytes' attribute."""
    
    # The maximum allowable maximum.
    max_bytes = 255
    
    _bytes = 255
    def _get_bytes(self):
        return self._bytes
    def _set_bytes(self, value):
        if value is not None:
            if value < 1:
                raise ValueError("%r is less than min bytes 1." % value)
            elif value > self.max_bytes:
                raise ValueError("%r is greater than max bytes %r." %
                                 (value, self.max_bytes))
        self._bytes = value
    bytes = property(_get_bytes, _set_bytes,
                     doc="The maximum bytes specifiable for "
                         "each instance of this type.")
    
    def ddl(self):
        """Return the type for use in CREATE or ALTER statements."""
        return "%s(%s)" % (self.__class__.__name__, self.bytes)


class FrozenPrecisionType(DatabaseType):
    """DatabaseType which specifies a frozen 'precision' attribute."""
    
    _precision = max_precision = 53
    def _get_precision(self):
        return self._precision
    def _set_precision(self, value):
        pass
    precision = property(_get_precision, _set_precision,
                         doc="The frozen precision in binary digits (bits).")


class AdjustablePrecisionType(DatabaseType):
    """DatabaseType which specifies an adjustable 'precision' attribute."""
    
    # Max binary precision for floating-point columns. Python floats are
    # implemented using C doubles; actual precision depends on platform
    # (but is usually 53 binary digits, see adapters.maxfloat_digits).
    # Many commercial DB's DOUBLE is 53 binary-digit precision.
    max_precision = 53
    
    _precision = 53
    def _get_precision(self):
        return self._precision
    def _set_precision(self, value):
        if value is not None:
            if value < 1:
                raise ValueError("%r: %r is less than min precision 1." %
                                 (self, value))
            elif value > self.max_precision:
                raise ValueError("%r: %r is greater than max precision %r." %
                                 (self, value, self.max_precision))
        self._precision = value
    precision = property(_get_precision, _set_precision,
                         doc="The set precision in binary digits (bits).")
    
    def ddl(self):
        """Return the type for use in CREATE or ALTER statements."""
        return "%s(%s)" % (self.__class__.__name__, self.precision)


class FixedRangeType(DatabaseType):
    """DatabaseType which represents values within a fixed range."""
    _min = None
    _max = None
    
    def range(self):
        """Return self.max - self.min."""
        return self._max - self._min
    
    def min(self):
        """Return the minimum value allowed."""
        return self._min
    
    def max(self):
        """Return the maximum value allowed."""
        return self._max



# --------------------------- Concrete types --------------------------- #

# SQL92 types: INTEGER (INT), SMALLINT, NUMERIC, DECIMAL, FLOAT, REAL,
#   DOUBLE PRECISION (DOUBLE), BIT, BIT VARYING, DATE, TIME, TIMESTAMP,
#   CHARACTER (CHAR), CHARACTER VARYING (VARCHAR), INTERVAL

class TEXT(FrozenByteType):
    """DatabaseType for string types whose byte-length is not adjustable.
    
    A Frozen*Type does not imply that the type is a fixed-byte
    type like CHAR as opposed to a variable-byte type like VARCHAR
    (that difference is specified in the "variable" attribute).
    Instead, a Frozen* type implies that the type takes no size
    argument in DDL; for example, Microsoft Access' MEMO type
    is always 65535 bytes, and is not user-specifiable.
    """
    
    # CHAR vs VARCHAR
    variable = True
    encoding = 'utf8'
    
    default_pytype = str
    default_adapters = {str: adapters.str_to_SQL92VARCHAR(),
                        unicode: adapters.unicode_to_SQL92VARCHAR(),
                        float: adapters.number_to_TEXT(float),
                        int: adapters.number_to_TEXT(int),
                        long: adapters.number_to_TEXT(long),
                        
                        # Adapters for DB's with no native date/time types.
                        # Fortunately, the adapters for native types work
                        # just as well for TEXT.
                        datetime.datetime: adapters.datetime_to_SQL92TIMESTAMP(),
                        datetime.date: adapters.date_to_SQL92DATE(),
                        datetime.time: adapters.time_to_SQL92TIME(),
                        datetime.timedelta: adapters.timedelta_to_SQL92DECIMAL(),
                        
                        None: adapters.Pickler(),
                        }
    if typerefs.decimal:
        if hasattr(typerefs.decimal, "Decimal"):
            default_adapters[typerefs.decimal.Decimal] = adapters.decimal_to_TEXT()
        else:
            default_adapters[typerefs.decimal] = adapters.decimal_to_TEXT()
    if typerefs.fixedpoint:
        default_adapters[typerefs.fixedpoint.FixedPoint] = adapters.fixedpoint_to_TEXT()


class SQL92VARCHAR(AdjustableByteType):
    """DatabaseType for adjustable-byte string types."""
    
    # CHAR vs VARCHAR
    variable = True
    encoding = 'utf8'
    
    default_pytype = str
    default_adapters = {str: adapters.str_to_SQL92VARCHAR(),
                        unicode: adapters.unicode_to_SQL92VARCHAR(),
                        float: adapters.number_to_TEXT(float),
                        int: adapters.number_to_TEXT(int),
                        long: adapters.number_to_TEXT(long),
                        datetime.timedelta: adapters.timedelta_to_SQL92DECIMAL(),  #??
                        None: adapters.Pickler(),
                        }
    if typerefs.decimal:
        if hasattr(typerefs.decimal, "Decimal"):
            default_adapters[typerefs.decimal.Decimal] = adapters.decimal_to_TEXT()
        else:
            default_adapters[typerefs.decimal] = adapters.decimal_to_TEXT()
    if typerefs.fixedpoint:
        default_adapters[typerefs.fixedpoint.FixedPoint] = adapters.fixedpoint_to_TEXT()


class SQL92CHAR(SQL92VARCHAR):
    variable = False


class SQL92INTEGER(FrozenByteType):
    """A base class for DatabaseTypes which conform to SQL92 INTEGER.
    
    "INTEGER specifies the data type exact numeric, with binary or
    decimal precision and scale of 0. The choice of binary versus
    decimal precision is implementation-defined, but shall be the
    same as SMALLINT."
    """
    
    default_pytype = int
    default_adapters = {int: adapters.int_to_SQL92INTEGER(),
                        long: adapters.int_to_SQL92INTEGER(),
                        bool: adapters.bool_to_SQL92BIT(),
                        }
    signed = True
    _bytes = max_bytes = 4
    
    def range(self):
        """Return self.max - self.min."""
        return 2 ** (self.bytes * 8)
    
    def min(self):
        """Return the minimum value allowed."""
        if self.signed:
            return 0 - (self.range() / 2)
        else:
            return 0
    
    def max(self):
        """Return the maximum value allowed."""
        if self.signed:
            return (self.range() / 2) - 1
        else:
            return self.range() - 1


class SQL92SMALLINT(SQL92INTEGER):
    """Base class for SQL 92 SMALLINT types.
    
    "The precision of SMALLINT shall be less than or equal to the
    precision of INTEGER."
    """
    _bytes = max_bytes = 2


class SQL92FLOAT(AdjustablePrecisionType):
    """Base class for SQL 92 FLOAT types.
    
    "FLOAT specifies the data type approximate numeric, with binary
    precision equal to or greater than the value of the specified
    <precision>. The maximum value of <precision> is implementation-
    defined. <precision> shall not be greater than this value."
    """
    default_pytype = float


class SQL92REAL(FrozenPrecisionType):
    """Base class for SQL 92 REAL types.
    
    "REAL specifies the data type approximate numeric, with implementation-
    defined precision."
    """
    default_pytype = float
    # By "precision" here, we mean the number of binary digits
    # which can be safely round-tripped to the DB and back.
    # Even though almost every DB will use 32 bits to represent this
    # number (1 sign bit, 8 exponent bits, and 24 significand bits),
    # we're only interested in the significand bits; therefore, the
    # max() for this type should be (2 ** 24) - 1.
    # See http://babbage.cs.qc.edu/IEEE-754/Decimal.html
    _precision = max_precision = 24
    default_adapters = {float: adapters.float_to_SQL92REAL()}
    if typerefs.fixedpoint:
        default_adapters[typerefs.fixedpoint.FixedPoint] = adapters.fixedpoint_to_SQL92REAL()
    if typerefs.decimal:
        if hasattr(typerefs.decimal, "Decimal"):
            default_adapters[typerefs.decimal.Decimal] = adapters.decimal_to_SQL92REAL()
        else:
            default_adapters[typerefs.decimal] = adapters.decimal_to_SQL92REAL()

class SQL92DOUBLE(SQL92REAL):
    """Base class for SQL 92 DOUBLE PRECISION types.
    
    "DOUBLE PRECISION specifies the data type approximate numeric,
    with implementation-defined precision that is greater than the
    implementation-defined precision of REAL."
    """
    _precision = max_precision = 53
    default_adapters = {float: adapters.float_to_SQL92DOUBLE()}
    if typerefs.fixedpoint:
        default_adapters[typerefs.fixedpoint.FixedPoint] = adapters.fixedpoint_to_SQL92DOUBLE()
    if typerefs.decimal:
        if hasattr(typerefs.decimal, "Decimal"):
            default_adapters[typerefs.decimal.Decimal] = adapters.decimal_to_SQL92DOUBLE()
        else:
            default_adapters[typerefs.decimal] = adapters.decimal_to_SQL92DOUBLE()


class SQL92DECIMAL(AdjustablePrecisionType):
    """Base class for SQL 92 DECIMAL types.
    
    For exact numeric types, 'precision' and 'scale' refer to decimal digits.
    
    SQL 92 says:
        "NUMERIC specifies the data type exact numeric, with the decimal
        precision and scale specified by the <precision> and <scale>."
        
        "DECIMAL specifies the data type exact numeric, with the decimal
        scale specified by the <scale> and the implementation-defined
        decimal precision equal to or greater than the value of the
        specified <precision>."
    
    In terms of adaptation, there's not much difference between these.
    Plenty of databases make them synonyms anyway.
    """
    scale = None
    max_scale = 1000
    
    _precision = 18
    max_precision = 1000
    
    if typerefs.decimal:
        if hasattr(typerefs.decimal, "Decimal"):
            default_pytype = typerefs.decimal.Decimal
        else:
            default_pytype = typerefs.decimal
    elif typerefs.fixedpoint:
        default_pytype = typerefs.fixedpoint.FixedPoint
    else:
        default_pytype = float
    
    default_adapters = {int: adapters.number_to_SQL92DECIMAL(int),
                        long: adapters.number_to_SQL92DECIMAL(long),
                        float: adapters.number_to_SQL92DECIMAL(float),
                        datetime.timedelta: adapters.timedelta_to_SQL92DECIMAL(),
                        }
    if typerefs.fixedpoint:
        default_adapters[typerefs.fixedpoint.FixedPoint] = adapters.fixedpoint_to_SQL92DECIMAL()
    if typerefs.decimal:
        if hasattr(typerefs.decimal, "Decimal"):
            default_adapters[typerefs.decimal.Decimal] = adapters.decimal_to_SQL92DECIMAL()
        else:
            default_adapters[typerefs.decimal] = adapters.decimal_to_SQL92DECIMAL()
    
    def range(self):
        """Return self.max - self.min."""
        return (10 ** self.precision) * 2
    
    def min(self):
        """Return the minimum value allowed."""
        prec = -((10 ** self.precision) - 1)
        return prec / (10 ** self.scale)
    
    def max(self):
        """Return the maximum value allowed."""
        prec = (10 ** self.precision) - 1
        return prec / (10 ** self.scale)
    
    def ddl(self):
        """Return the type for use in CREATE or ALTER statements."""
        if self.precision is not None:
            if self.scale is not None:
                return "%s(%s, %s)" % (self.__class__.__name__,
                                       self.precision, self.scale)
            return "%s(%s)" % (self.__class__.__name__, self.precision)
        return self.__class__.__name__


class SQL92TIMESTAMP(FixedRangeType):
    default_pytype = datetime.datetime
    default_adapters = {datetime.datetime: adapters.datetime_to_SQL92TIMESTAMP()}

class SQL92DATE(FixedRangeType):
    default_pytype = datetime.date
    default_adapters = {datetime.date: adapters.date_to_SQL92DATE()}

class SQL92TIME(DatabaseType):
    default_pytype = datetime.time
    default_adapters = {datetime.time: adapters.time_to_SQL92TIME()}


class SQL92BIT(DatabaseType):
    """DatabaseType which uses boolean values (0, 1, Null)."""
    default_pytype = bool
    default_adapters = {bool: adapters.bool_to_SQL92BIT()}



# SQL99 types: CLOB, BLOB, BOOLEAN, ARRAY, ROW

class SQL99BOOLEAN(DatabaseType):
    """DatabaseType which uses boolean values (True, False, Null).
    
    ANSI SQL:1999 says something like:
    "The data type boolean comprises the distinct truth values
    true and false. Unless prohibited by a NOT NULL constraint,
    the boolean data type also supports the unknown truth value as
    the null value. This specification does not make a distinction
    between the null value of the boolean data type and the unknown
    truth value that is the result of an SQL <predicate>, <search
    condition>, or <boolean value expression>; they may be used
    interchangeably to mean exactly the same thing."
    """
    default_pytype = bool
    default_adapters = {bool: adapters.bool_to_SQL99BOOLEAN()}



# ----------------------------- Type Sets ----------------------------- #


def getCoerceName(pytype):
    """Return the name of the coercion method for a given Python type."""
    mod = pytype.__module__
    if mod == "__builtin__":
        xform = "%s" % pytype.__name__
    else:
        xform = "%s_%s" % (mod, pytype.__name__)
    xform = xform.replace(".", "_")
    return xform


class DatabaseTypeSet(object):
    """Determine the best database type for a given column + Python type.
    
    When Geniusql is asked to create database tables, it must choose an
    appropriate column data type for each Column based on the
    type (and hints) of that property. This class recommends such
    database types by returning a new instance of DatabaseType.
    """
    
    known_types = None
    
    # You should REALLY check into your DB's encoding and override this.
    encoding = 'utf8'
    auto_pickle = True
    
    def __copy__(self):
        newset = self.__class__()
        newset.update(self)
        newset.known_types = self.known_types.copy()
        return newset
    copy = __copy__
    
    def canonicalize(self, dbtypename):
        """Return the canonical DatabaseType for the given synonym.
        
        In order to avoid large amounts of code (in each provider module!)
        that merely looks up synonyms, database types MUST be
        canonicalized for all Column and SQLExpression objects.
        
        Note that the caller is responsible to strip out any metadata from
        the supplied type name; for example, "NUMERIC(18, 2)" should
        (usually) be reduced to "NUMERIC" before calling this function.
        However, this is not mandatory; some providers may need to use
        such metadata to select the most appropriate type.
        """
        for typeset in self.known_types.itervalues():
            for dbtype in typeset:
                if (dbtypename == dbtype.__name__
                    or dbtypename in dbtype.synonyms):
                    return dbtype
        raise KeyError("No canonical name found for %r." % dbtypename)
    
    def database_type(self, pytype, hints=None):
        """Return a DatabaseType instance for the given Python type.
        
        hints: if provided, this should be a dict of property attributes
            which can be used to distinguish between similar database types.
            Canonical keys include 'bytes', 'precision', 'scale', and 'signed'.
            To coerce a particular type, provide a DatabaseType instance in
            'dbtype'.
        """
        if hints is None:
            hints = {}
        elif 'dbtype' in hints:
            return hints['dbtype']

        xform = "dbtype_for_" + getCoerceName(pytype)
        try:
            xform = getattr(self, xform)
        except AttributeError:
            # Assume we'll use a VARCHAR type and pickle the values.
            if self.auto_pickle:
                return self.dbtype_for_str(hints)
            else:
                raise TypeError("%r is not handled by %s. Tried %r" %
                                (pytype, self.__class__, xform))
        return xform(hints)
    
    def dbtype_for_float(self, hints):
        """Return a DatabaseType for floats of the given binary precision."""
        # Note that 'precision' is binary digits, not decimal digits or bytes.
        # For example, most DOUBLE PRECISION types are implemented as
        # 64 bits ~= 53 binary precision ~= 14 decimal precision
        precision = int(hints.get('precision', adapters.maxfloat_digits))
        if precision == 0:
            # Use the maximum precision.
            precision = max([0] + [dbtype.max_precision
                                   for dbtype in self.known_types['float']])
        for dbtype in self.known_types['float']:
            if precision <= dbtype.max_precision:
                return dbtype(precision=precision)
        
        # Unable to find a compatible floating-point type. Try to find a
        # compatible fixed-point type instead (which usually allow higher
        # precision). Rather than do all sorts of complicated calculations
        # and extensive analysis of IEEE 754 representation, we just follow
        # http://download-west.oracle.com/docs/html/A85397_01/sql_elem.htm
        # and multiply bits by 0.30103 to get decimal precision.
        dec_prec = int(math.ceil(precision * 0.30103))
        # However, floating-point numbers essentially have no scale.
        # For example, given a binary precision of 23, we get a decimal
        # precision of (23 * 0.30103 =) 7, but that needs to allow both
        # 1000000 and 0.0000001, so we actually need DECIMAL(14, 7).
        return self.decimal_type(precision=dec_prec * 2, scale=dec_prec)
    
    def dbtype_for_str(self, hints):
        # The bytes hint shall not reflect the usual 4-byte base for varchar.
        bytes = int(hints.get('bytes', 255))
        if bytes == 0:
            # Use the maximum bytes.
            bytes = max([0] + [dbtype.max_bytes
                               for dbtype in self.known_types['varchar']])
        for dbtype in self.known_types['varchar']:
            if bytes <= dbtype.max_bytes:
                return dbtype(bytes=bytes)
        raise ValueError("%r is greater than the maximum bytes %r."
                         % (bytes, dbtype.max_bytes))
    
    def dbtype_for_unicode(self, hints):
        return self.dbtype_for_str(hints)
    
    def dbtype_for_bool(self, hints):
        return self.known_types['bool'][0]()
    
    # These are not adapter.push(bool) (which are used on one side of 
    # a comparison). Instead, these are used when the whole (sub)expression
    # is True or False, e.g. "WHERE TRUE", or "WHERE TRUE and 'a'.'b' = 3".
    expr_true = "TRUE"
    expr_false = "FALSE"
    
    # Because True and False get used so much in deparsing,
    # we include a memoized function for obtaining SQLExpressions.
    _adapted_bools = None
    def bool_exprs(self, exprclass):
        """Return SQLExpressions for expr_true, expr_false, comp_true and comp_false.
        
        expr_true and expr_false are used when a (sub)expression is True or
        False; for example, "WHERE TRUE and a.b = 3".
        
        comp_true and comp_false are used in comparisons; for example,
        "WHERE x.y == TRUE".
        
        In many databases, these are equivalent. Microsoft SQL Server is a
        notable exception, requiring "(1=1)" for expr_true, but "TRUE" for
        comp_true.
        """
        t = self.database_type(bool)
        adapter = t.default_adapter(bool)
        
        expr_true = exprclass(self.expr_true, '', t, bool)
        expr_true.adapter = adapter
        expr_true.value = True
        
        expr_false = exprclass(self.expr_false, '', t, bool)
        expr_false.adapter = adapter
        expr_false.value = False
        
        if self._adapted_bools is None:
            comp_true = adapter.push(True, t)
            comp_false = adapter.push(False, t)
            self._adapted_bools = (comp_true, comp_false)
        else:
            comp_true, comp_false = self._adapted_bools
        
        comp_true = exprclass(comp_true, '', t, bool)
        comp_true.adapter = adapter
        comp_true.value = True
        
        comp_false = exprclass(comp_false, '', t, bool)
        comp_false.adapter = adapter
        comp_false.value = False
        
        return (expr_true, expr_false, comp_true, comp_false)
    
    def dbtype_for_datetime_datetime(self, hints):
        return self.known_types['datetime'][0]()
    
    def dbtype_for_datetime_date(self, hints):
        return self.known_types['date'][0]()
    
    def dbtype_for_datetime_time(self, hints):
        return self.known_types['time'][0]()
    
    def dbtype_for_datetime_timedelta(self, hints):
        try:
            # If your DB has an INTERVAL datatype, you should provide a
            # native INTERVAL type. You'll also have to update the date
            # arithmetic inside the deparser and add a timedelta adapter.
            return self.known_types['timedelta'][0]()
        except (KeyError, IndexError):
            # Fallback for DB's which do not have an INTERVAL data type.
            # Use decimal instead of float to avoid rounding errors.
            # Using precision of 12 should allow +/- 31688 years.
            return self.decimal_type(12, 0)
    
    def numeric_max_precision(self):
        return max([0] + [t.max_precision for t in self.known_types['numeric']])
    
    def numeric_max_scale(self):
        return max([0] + [t.max_scale for t in self.known_types['numeric']])
    
    def decimal_type(self, precision, scale):
        if scale > precision:
            scale = precision
        
        for dbtype in self.known_types['numeric']:
            if (precision <= dbtype.max_precision and
                (scale is None or scale <= dbtype.max_scale)):
                return dbtype(precision=precision, scale=scale)
        
        # Use a VARCHAR type (add 1 char for the decimal point and 1 for sign).
        bytes = precision + 1
        if scale:
            bytes += 1
        dbtype = self.dbtype_for_str({'bytes': bytes})
        
        errors.warn("The given precision and scale (%s, %s) is greater than "
                    "the maximum numeric precision and/or scale (%s/%s). "
                    "Using %s instead."
                    % (precision, scale, self.numeric_max_precision(),
                       self.numeric_max_scale(), dbtype))
        return dbtype
    
    if typerefs.decimal:
        if hasattr(typerefs.decimal, "Decimal"):
            def dbtype_for_decimal_Decimal(self, hints):
                precision = int(hints.get('precision', 0))
                if precision == 0:
                    precision = self.numeric_max_precision()
                # Assume most people use decimal for money; default scale = 2.
                scale = int(hints.get('scale', 2))
                return self.decimal_type(precision, scale)
        else:
            def dbtype_for_decimal(self, hints):
                precision = int(hints.get('precision', 0))
                if precision == 0:
                    precision = self.numeric_max_precision()
                # Assume most people use decimal for money; default scale = 2.
                scale = int(hints.get('scale', 2))
                return self.decimal_type(precision, scale)
    
    if typerefs.fixedpoint:
        def dbtype_for_fixedpoint_FixedPoint(self, hints):
            # Note that fixedpoint has no theoretical precision limit.
            precision = int(hints.get('precision', 0))
            if precision == 0:
                precision = self.numeric_max_precision()
            # Assume most people use fixedpoint for money; default scale = 2.
            scale = int(hints.get('scale', 2))
            return self.decimal_type(precision, scale)
    
    def dbtype_for_long(self, hints):
        # Assume most people want signed numbers.
        signed = hints.get('signed', True)
        
        if 'bytes' in hints:
            bytes = int(hints['bytes'])
            maxprec = int(math.ceil(math.log(2 ** (bytes * 8), 10)))
        else:
            maxprec = self.numeric_max_precision()
            bytes = int(math.ceil(math.log(10 ** maxprec, 2) / 8))
        
        for dbtype in self.known_types['int']:
            if bytes <= dbtype.max_bytes and signed == dbtype.signed:
                return dbtype(bytes=bytes)
        
        return self.decimal_type(precision=maxprec, scale=0)
    
    def dbtype_for_int(self, hints):
        # Assume most people want signed numbers; maxint_bytes assumes it.
        signed = hints.get('signed', True)
        bytes = int(hints.get('bytes', adapters.maxint_bytes))
        
        for dbtype in self.known_types['int']:
            if bytes <= dbtype.max_bytes and signed == dbtype.signed:
                return dbtype(bytes=bytes)
        
        maxprec = int(math.ceil(math.log(2 ** (bytes * 8), 10)))
        return self.decimal_type(precision=maxprec, scale=0)

