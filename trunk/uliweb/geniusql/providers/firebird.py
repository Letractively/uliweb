# See http://www.firebirdsql.org/index.php?op=devel&sub=engine&id=SQL_conformance&nosb=1
# for lots of conformance info.
# 
# This module ALWAYS assumes dialect 3.

import datetime
import threading
import time

import geniusql
from geniusql import adapters, conns, dbtypes, deparse, errors, sqlwriters, typerefs
from geniusql import isolation as _isolation

import kinterbasdb

# Use datetime instead of mxDateTime
kinterbasdb.init(type_conv=200)


# ------------------------------- Adapters ------------------------------- #


class Firebird_str_to_SQL92VARCHAR(adapters.str_to_SQL92VARCHAR):
    
    # Notice these are ordered pairs. Escape \ before introducing new ones.
    # Values in these two lists should be strings encoded with self.encoding.
    # From http://www.firebirdsql.org/manual/qsg10-firebird-sql.html:
    # "Strings in Firebird are delimited by a pair of single quote (apostrophe)
    # symbols  - 'I am a string' - (ASCII code 39, not 96)...Double quotes
    # cannot be used as string delimiters in Firebird SQL statements."
    escapes = [("'", "''")]

class Firebird_unicode_to_SQL92VARCHAR(adapters.unicode_to_SQL92VARCHAR):
    escapes = [("'", "''")]

class Firebird_Pickler(adapters.Pickler):
    escapes = [("'", "''")]


class Firebird_any_to_BLOB(adapters.Adapter):
    
    def __init__(self, pytype):
        self.pytype = pytype
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        return "'%s'" % str(value)
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        return self.pytype(value)



class Firebird_datetime_adapter(adapters.datetime_to_SQL92TIMESTAMP):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        # This isn't necessary for UPDATE, but it is for binary operations.
        return ("CAST('%04d-%02d-%02d %02d:%02d:%02d' AS TIMESTAMP)" %
                (value.year, value.month, value.day,
                 value.hour, value.minute, value.second))
    
    def binary_op(self, op1, op, sqlop, op2):
        # See http://www.ibphoenix.com/main.nfs?a=ibphoenix&s=1154534295:6&page=ibp_60_sql_date_fs
        if op2.pytype is datetime.datetime:
            if op == "-":
                return ("((%s - %s) * CAST(86400 AS DOUBLE PRECISION))"
                        % (op1.sql, op2.sql))
        elif op2.pytype is datetime.timedelta:
            return ("(%s %s (CAST(%s AS DOUBLE PRECISION) / 86400))"
                    % (op1.sql, op, op2.sql))
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


class Firebird_date_adapter(adapters.date_to_SQL92DATE):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        # This isn't necessary for UPDATE, but it is for binary operations.
        return ("CAST('%04d-%02d-%02d' AS DATE)" %
                (value.year, value.month, value.day))
    
    def binary_op(self, op1, op, sqlop, op2):
        # See http://www.ibphoenix.com/main.nfs?a=ibphoenix&s=1154534295:6&page=ibp_60_sql_date_fs
        if op2.pytype is datetime.date:
            if op == "-":
                return "((%s - %s) * 86400)" % (op1.sql, op2.sql)
        elif op2.pytype is datetime.timedelta:
            return "(%s %s (%s / 86400))" % (op1.sql, op, op2.sql)
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


class Firebird_timedelta_adapter(adapters.timedelta_to_SQL92DECIMAL):
    
    def pull(self, value, dbtype):
        if value is None:
            return None
        # TIMESTAMP - TIMESTAMP => DECIMAL(18, 9) Days + Fraction of day
        # DATE - DATE =>           DECIMAL(9, 0) representing # of Days
        # However, in binary_op (below) we multiplied them all by 86400.
        if isinstance(value, tuple):
            value = normalize(value, float)[0]
        days, seconds = divmod(value, 86400)
        return datetime.timedelta(int(days), int(round(seconds)))
    
    def binary_op(self, op1, op, sqlop, op2):
        # See http://www.ibphoenix.com/main.nfs?a=ibphoenix&s=1154534295:6&page=ibp_60_sql_date_fs
        if op2.pytype is datetime.timedelta:
            return "(%s %s %s)" % (op1.sql, op, op2.sql)
        elif op == "+":
            if op2.pytype is datetime.date:
                return "((%s / 86400) + %s)" % (op1.sql, op2.sql)
            elif op2.pytype is datetime.datetime:
                return ("((CAST(%s AS DOUBLE PRECISION) / 86400) + %s)"
                        % (op1.sql, op2.sql))
        raise TypeError("unsupported operand type(s) for %s: "
                        "%r and %r" % (op, op1.pytype, op2.pytype))


class Firebird_time_adapter(adapters.time_to_SQL92TIME):
    
    def push(self, value, dbtype):
        if value is None:
            return 'NULL'
        # This isn't necessary for UPDATE, but it is for binary operations.
        return ("CAST('%02d:%02d:%02d' AS TIME)" %
                (value.hour, value.minute, value.second))


_power_of_ten = [10 ** x for x in xrange(20)]
del x

def normalize(dectuple, newtype):
    """Normalize the given (val, scale) tuple into (newtype(val), scale)."""
    value, scale = dectuple
    if scale:
        value = newtype(value) / _power_of_ten[-scale]
    return value, scale


if typerefs.decimal:
    class Firebird_decimal_adapter(adapters.decimal_to_SQL92DECIMAL):
        def pull(self, value, dbtype):
            if value is None:
                return None
            if isinstance(value, tuple):
                return normalize(value, typerefs.decimal)[0]
            return typerefs.decimal(str(value))

    class Firebird_decimal_Decimal_adapter(adapters.decimal_to_SQL92DECIMAL):
        def pull(self, value, dbtype):
            if value is None:
                return None
            if isinstance(value, tuple):
                return normalize(value, typerefs.decimal.Decimal)[0]
            return typerefs.decimal.Decimal(str(value))

if typerefs.fixedpoint:
    class Firebird_fixedpoint_adapter(adapters.fixedpoint_to_SQL92DECIMAL):
        def pull(self, value, dbtype):
            if value is None:
                return None
            fp = typerefs.fixedpoint.FixedPoint
            if isinstance(value, tuple):
                value, scale = normalize(value, float)
                return fp(value, -scale)
            elif isinstance(value, basestring):
                # Unicode really screws up fixedpoint; for example:
                # >>> fixedpoint.FixedPoint(u'111111111111111111111111111.1')
                # FixedPoint('111111111111111104952008704.00', 2)
                value = str(value)
                
                scale = 0
                atoms = value.rsplit(".", 1)
                if len(atoms) > 1:
                    scale = len(atoms[-1])
                return fp(value, scale)
            else:
                return fp(value)

class Firebird_int_adapter(adapters.int_to_SQL92INTEGER):
    def pull(self, value, dbtype):
        if value is None:
            return None
        if isinstance(value, tuple):
            return normalize(value, int)[0]
        return int(value)

class Firebird_long_adapter(adapters.int_to_SQL92INTEGER):
    def pull(self, value, dbtype):
        if value is None:
            return None
        if isinstance(value, tuple):
            return normalize(value, long)[0]
        return long(value)

class Firebird_number_to_SQL92DECIMAL(adapters.number_to_SQL92DECIMAL):
    def pull(self, value, dbtype):
        if value is None:
            return None
        if isinstance(value, tuple):
            return normalize(value, self.pytype)[0]
        return self.pytype(value)



# ---------------------------- Database types ---------------------------- #


# See http://www.ibexpert.info/documentation/%20%203.%20Database%20Objects/%20%203.%20Field/%20%203.%20Datatype/387.html
# <data_type> = {
#   {SMALLINT | INTEGER | FLOAT | DOUBLE PRECISION} [<array_dim>]
# | {DECIMAL | NUMERIC} [(precision [, scale])] [<array_dim]
# | DATE [<array_dim>]
# | {CHAR | CHARACTER | CHARACTER VARYING | VARCHAR}
#       [(int)] [<array_dim>] [CHARACTER SET charname]
# | {NCHAR | NATIONAL CHARACTER | NATIONAL CHAR}
#       [VARYING] [(int)] [<array_dim>]
# | BLOB [SUB_TYPE {int | subtype_name}) (SEGMENT SIZE int]
#       [CHARACTER SET charname]
# | BLOB [(seglen [, subtype])]
# }

class SMALLINT(dbtypes.SQL92SMALLINT):
    synonyms = ['SHORT']
    default_adapters = {int: Firebird_int_adapter(),
                        long: Firebird_int_adapter(),
                        bool: adapters.bool_to_SQL92BIT(),
                        }

class INTEGER(dbtypes.SQL92INTEGER):
    synonyms = ['LONG']
    default_adapters = {int: Firebird_int_adapter(),
                        long: Firebird_int_adapter(),
                        bool: adapters.bool_to_SQL92BIT(),
                        }

##class INT64(dbtypes.SQL92INTEGER):
##    _bytes = max_bytes = 8
##    default_adapters = {int: Firebird_int_adapter(),
##                        long: Firebird_int_adapter(),
##                        bool: adapters.bool_to_SQL92BIT(),
##                        }


class FLOAT(dbtypes.SQL92REAL):
    pass

class DOUBLE(dbtypes.SQL92DOUBLE):
    """Base class for SQL 92 DOUBLE PRECISION types."""
    synonyms = ['DOUBLE PRECISION']
    
    def ddl(self):
        """Return the type for use in CREATE or ALTER statements."""
        return "DOUBLE PRECISION"


class NUMERIC(dbtypes.SQL92DECIMAL):
    # Depending on the dialect, FB will convert NUMERIC to another type
    # if the precision or scale are not specified.
    
    # SQL dialect 1 only allows max_precision of 15, but dialect 3 is 18
    max_precision = 18
    max_scale = 18
    
    # Grr. INT64 is an alias for NUMERIC(18, 0).
    # See http://www.ibphoenix.com/downloads/OpenFeaturesDetailed.pdf
    synonyms = ['INT64']
    
    default_adapters = {int: Firebird_number_to_SQL92DECIMAL(int),
                        long: Firebird_number_to_SQL92DECIMAL(long),
                        float: Firebird_number_to_SQL92DECIMAL(float),
                        datetime.timedelta: Firebird_timedelta_adapter(),
                        }
    if typerefs.fixedpoint:
        default_adapters[typerefs.fixedpoint.FixedPoint] = Firebird_fixedpoint_adapter()
    if typerefs.decimal:
        if hasattr(typerefs.decimal, "Decimal"):
            default_adapters[typerefs.decimal.Decimal] = Firebird_decimal_Decimal_adapter()
        else:
            default_adapters[typerefs.decimal] = Firebird_decimal_adapter()



class CHAR(dbtypes.SQL92CHAR):
    synonyms = ['CHARACTER']
    
    max_bytes = 32767
    
    # See http://www.volny.cz/iprenosil/interbase/ip_ib_indexcalculator.htm
    # In Firebird 1.5:
    #     VARCHAR(255) with UTF8 encoding results in a key size of 1020
    #     VARCHAR(255) with ASCII encoding results in a key size of 256
    # Either will cause an error when such a column is used as the
    # PRIMARY KEY, which is limited to 256. So here, we default to 63,
    # the max for UTF8 (which is our default encoding).
    _bytes = 63
    
    default_adapters = dbtypes.SQL92CHAR.default_adapters.copy()
    default_adapters.update({str: Firebird_str_to_SQL92VARCHAR(),
                             unicode: Firebird_unicode_to_SQL92VARCHAR(),
                             None: Firebird_Pickler,
                             })

class VARCHAR(dbtypes.SQL92VARCHAR):
    synonyms = ['CHARACTER VARYING', 'CHAR VARYING', 'VARYING']
    max_bytes = 32767
    # See http://www.volny.cz/iprenosil/interbase/ip_ib_indexcalculator.htm
    # In Firebird 1.5, VARCHAR(255) results in a key size of 256 (which will
    # cause an error when such a column is used as the PRIMARY KEY).
    _bytes = 63
    
    # Although Firebird allows VARCHAR of 32767, 255 is usually the max
    # for which an index can be created.
    # TODO: this needs some serious work, so that the full size can be
    # allowed while only allowing indices of 255.
    default_adapters = dbtypes.SQL92CHAR.default_adapters.copy()
    default_adapters.update({str: Firebird_str_to_SQL92VARCHAR(),
                             unicode: Firebird_unicode_to_SQL92VARCHAR(),
                             None: Firebird_Pickler(),
                             })

class NCHAR(dbtypes.SQL92CHAR):
    # 'The only difference to the NCHAR/VARCHAR datatype is that
    # NCHAR/VARCHAR automatically defines a special character set for
    # this table column: "CHARACTER SET ISO8859_1"'
    default_pytype = unicode
    max_bytes = 32767
    # See http://www.volny.cz/iprenosil/interbase/ip_ib_indexcalculator.htm
    # In Firebird 1.5, VARCHAR(255) results in a key size of 256 (which will
    # cause an error when such a column is used as the PRIMARY KEY).
    _bytes = 63
    
    default_adapters = dbtypes.SQL92CHAR.default_adapters.copy()
    default_adapters.update({str: Firebird_str_to_SQL92VARCHAR(),
                             unicode: Firebird_unicode_to_SQL92VARCHAR(),
                             None: Firebird_Pickler(),
                             })

class NVARCHAR(dbtypes.SQL92VARCHAR):
    default_pytype = unicode
    max_bytes = 32767
    # See http://www.volny.cz/iprenosil/interbase/ip_ib_indexcalculator.htm
    # In Firebird 1.5, VARCHAR(255) results in a key size of 256 (which will
    # cause an error when such a column is used as the PRIMARY KEY).
    _bytes = 63
    
    default_adapters = dbtypes.SQL92CHAR.default_adapters.copy()
    default_adapters.update({str: Firebird_str_to_SQL92VARCHAR(),
                             unicode: Firebird_unicode_to_SQL92VARCHAR(),
                             None: Firebird_Pickler(),
                             })


class DATE(dbtypes.SQL92DATE):
    # 'SQL dialect 1: DATE also includes a time slice
    # (equivalent to TIMESTAMP in dialect 3).'
    
    # 'Valid dates are from January 1, 100 AD through February 28, 32,767 AD.
    # Note: for DATE arithmetic purposes, DATE 0 (the integer value of zero)
    # as a DATE in InterBase/Firebird is November 17, 1898.'
    _min = datetime.date(100, 1, 1)
##    _max = datetime.date(32767, 2, 28)
    _max = datetime.date(9999, 12, 31)
    default_adapters = {datetime.date: Firebird_date_adapter()}

class TIME(dbtypes.SQL92TIME):
    default_adapters = {datetime.time: Firebird_time_adapter()}

class TIMESTAMP(dbtypes.SQL92TIMESTAMP):
    # 'The range is from January 1,100 AD to February 28, 32768 AD.'
    _min = datetime.datetime(100, 1, 1)
##    _max = datetime.datetime(32768, 2, 28, 23, 59, 59)
    _max = datetime.datetime(9999, 12, 31, 23, 59, 59)
    default_adapters = {datetime.datetime: Firebird_datetime_adapter()}



class ComparableInfinity(object):
    
    def __cmp__(self, other):
        if isinstance(other, self.__class__):
            return False
        return True

class BLOB(dbtypes.TEXT):
    # 'It is important when using blobs in a database, to consider the
    # database page size carefully. Blobs are created as part of a data
    # row, but because a blob could be of unlimited length, what is
    # actually stored with the data row is a BlobID, the data for the
    # blob is stored separately on special blob pages elsewhere in the
    # database.'
    # 
    # Max Blob Size:
    # 
    # 1Kb page size =>  64 Mb
    # 2Kb page size => 512 Mb
    # 4Kb page size =>   4 Gb
    # 8Kb page size =>  32 Gb
    # 16kb page size => Big enough :-).
    # TEXT has no hard byte limit.
    _bytes = max_bytes = ComparableInfinity()


class FirebirdTypeSet(dbtypes.DatabaseTypeSet):
    
    # Firebird doesn't have true or false keywords.
    expr_true = "1=1"
    expr_false = "1=0"
    
    known_types = {'float': [FLOAT, DOUBLE],
                   'varchar': [VARCHAR, BLOB],
                   'char': [CHAR, BLOB],
                   'int': [SMALLINT, INTEGER],
                   'bool': [SMALLINT],
                   'datetime': [TIMESTAMP],
                   'date': [DATE],
                   'time': [TIME],
                   'timedelta': [],
                   'numeric': [NUMERIC],
                   'other': [],
                   }
    
    def dbtype_for_str(self, hints):
        # The bytes hint shall not reflect the usual 4-byte base for varchar.
        bytes = int(hints.get('bytes', 63))
        if bytes == 0:
            # Use the maximum bytes.
            bytes = max([0] + [dbtype.max_bytes
                               for dbtype in self.known_types['varchar']])
        for dbtype in self.known_types['varchar']:
            if bytes <= dbtype.max_bytes:
                return dbtype(bytes=bytes)
        raise ValueError("%r is greater than the maximum bytes %r."
                         % (bytes, dbtype.max_bytes))


class FirebirdSQLDeparser(deparse.SQLDeparser):
    
    like_escapes = [("\\", r"\\"), ("%", r"\%"), ("_", r"\_")]
    
    # --------------------------- Dispatchees --------------------------- #
    
    def attr_startswith(self, tos, arg):
        return self.get_expr(tos.sql + " STARTING WITH " + arg.sql, bool)
    
    def attr_endswith(self, tos, arg):
        return self.get_expr(tos.sql + " LIKE '%" +
                             self.escape_like(arg.sql) +
                             "' ESCAPE '\\'", bool)
    
    def containedby(self, op1, op2):
        if op1.value is not None:
            # Looking for text in a field. Use Like (reverse terms).
            like = self.escape_like(op1.sql)
            return self.get_expr(op2.sql + " LIKE '%" + like +
                                 "%' ESCAPE '\\'", bool)
        else:
            # Looking for field in (a, b, c)
            atoms = []
            for x in op2.value:
                adapter = op1.dbtype.default_adapter(type(x))
                atoms.append(adapter.push(x, op1.dbtype))
            if atoms:
                return self.get_expr(op1.sql + " IN (" + ", ".join(atoms) + ")", bool)
            else:
                # Nothing will match the empty list, so return none.
                return self.false_expr
    
    # Firebird has no LOWER function, but it does have an UPPER. Funky.
    
    def builtins_icontainedby(self, op1, op2):
        if op1.value is not None:
            # Looking for text in a field.
            return self.get_expr(op2.sql + " CONTAINING " + op1.sql, bool)
        else:
            # Looking for field in (a, b, c).
            # Force all args to uppercase for case-insensitive comparison.
            atoms = []
            for x in op2.value:
                adapter = op1.dbtype.default_adapter(type(x))
                atoms.append(adapter.push(x.upper(), op1.dbtype))
            return self.get_expr("UPPER(%s) IN (%s)" %
                                 (op1.sql, ", ".join(atoms)), bool)
    
    def builtins_istartswith(self, x, y):
        return self.get_expr("UPPER(" + x.sql + ") LIKE '" +
                             self.escape_like(y.sql) +
                             "%' ESCAPE '\\'", bool)
    
    def builtins_iendswith(self, x, y):
        return self.get_expr("UPPER(" + x.sql + ") LIKE '%" +
                             self.escape_like(y.sql) +
                             "' ESCAPE '\\'", bool)
    
    def builtins_ieq(self, x, y):
        return self.get_expr("UPPER(" + x.sql + ") = UPPER(" + y.sql + ")",
                             bool)
    
    def builtins_today(self):
        return self.get_expr("CURRENT_DATE", datetime.date)
    
    def builtins_now(self):
        return self.get_expr("CURRENT_TIMESTAMP", datetime.datetime)
    
    builtins_utcnow = None
    
    def builtins_year(self, x):
        return self.get_expr("EXTRACT(YEAR FROM %s)" % x.sql, int)
    
    def builtins_month(self, x):
        return self.get_expr("EXTRACT(MONTH FROM %s)" % x.sql, int)
    
    def builtins_day(self, x):
        return self.get_expr("EXTRACT(DAY FROM %s)" % x.sql, int)
    
    # Firebird 1.5 has no LENGTH function
    func__builtin___len = None


class Firebird2SQLDeparser(FirebirdSQLDeparser):
    
    def func__builtin___len(self, x):
        return self.get_expr("CHAR_LENGTH(" + x.sql + ")", int)


class Firebird_SELECT(sqlwriters.SELECT):
    
    def _get_sql(self):
        """Return an SQL SELECT statement."""
        atoms = ["SELECT"]
        append = atoms.append
        if self.distinct:
            append('DISTINCT')
        # Firebird uses 'FIRST' instead of 'LIMIT'
        if self.limit is not None:
            append('FIRST %d' % self.limit)
        # ...and 'SKIP' instead of 'OFFSET'
        if self.offset is not None:
            append('SKIP %d' % self.offset)
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
        else:
            # Use the trick of selecting scalars from a known single-row table
            # See http://www.cvalde.net/document/DateTimeFunctions.htm
            append("FROM rdb$database")
        return " ".join(atoms)
    sql = property(_get_sql, doc="The SQL string for this SELECT statement.")


class FirebirdSelectWriter(sqlwriters.SelectWriter):
    
    statement_class = Firebird_SELECT
    
    def wrap(self, join):
        """Return the given Join with each node wrapped."""
        t1, t2 = join.table1, join.table2
        
        if isinstance(t1, geniusql.Join):
            wt1 = self.wrap(t1)
        else:
            # Firebird 1.5 won't accept the same table twice in a JOIN
            # unless *both* table names are aliased.
            wt1 = self.db.joinwrapper(t1)
            self.aliascount += 1
            alias = "t%d" % self.aliascount
            wt1.alias = self.db.quote(t1.schema.table_name(alias))
            self.seen[t1.name] = None
        
        if isinstance(t2, geniusql.Join):
            wt2 = self.wrap(t2)
        else:
            wt2 = self.db.joinwrapper(t2)
            self.aliascount += 1
            alias = "t%d" % self.aliascount
            wt2.alias = self.db.quote(t2.schema.table_name(alias))
            self.seen[t2.name] = None
        
        newjoin = geniusql.Join(wt1, wt2, join.leftbiased)
        # if the original Join had a custom reference path,
        # copy it to the new Join instance
        newjoin.path = join.path
        return newjoin
    
    def joinname(self, tablewrapper):
        """Quoted table name for use in JOIN clause."""
        if tablewrapper.alias:
            # Firebird doesn't use the "AS" keyword
            return "%s %s" % (tablewrapper.qname, tablewrapper.alias)
        else:
            return tablewrapper.qname
    
    def deparse_attributes(self):
        dep = self.db.deparser(self.tablenames, self.query.attributes,
                               self.db.typeset)
##        dep.verbose = True
        
        for atom in dep.field_list():
            if atom.name in self.output_cols:
                bare_name = atom.name
                index = 1
                while atom.name in self.output_cols:
                    atom.name = '%s%s' % (bare_name, index)
                    index += 1
            
            # Here's where we extend the superclass. 'foo' AS expr5
            # will return CHAR columns, not VARCHAR, so we CAST
            # if value is not None (table refs will be None).
            if isinstance(atom.dbtype, VARCHAR) and atom.value is not None:
                atom.sql = "CAST(%s AS %s)" % (atom.sql, atom.dbtype.ddl())
            
            qname = self.db.quote(atom.name)
            self.statement.input.append('%s AS %s' % (atom.sql, qname))
            self.statement.output.append((atom.name, atom.name, qname, atom))
            if not atom.aggregate:
                self.statement.groupby.append(atom.sql)
            
            self.output_cols[atom.name] = atom


class FirebirdTable(geniusql.Table):
    
    def _add_column(self, column):
        """Internal function to add the column to the database."""
        coldef = self.schema.columnclause(column)
        # FB doesn't recognize the keyword "COLUMN" in "ADD".
        self.schema.db.execute_ddl("ALTER TABLE %s ADD %s;" %
                                   (self.qname, coldef))
    
    def _drop_column(self, column):
        """Internal function to drop the column from the database."""
        # FB doesn't recognize the keyword "COLUMN" in "DROP".
        self.schema.db.execute_ddl("ALTER TABLE %s DROP %s;" %
                                   (self.qname, column.qname))
    
    def _rename(self, oldcol, newcol):
        # FB doesn't use the keyword "RENAME".
        self.schema.db.execute_ddl("ALTER TABLE %s ALTER COLUMN %s TO %s;" %
                                   (self.qname, oldcol.qname, newcol.qname))
    
    def insert(self, **kwargs):
        """Insert a row and return {idcolkey: newid}."""
        newids = {}
        values = {}
        for key, col in self.iteritems():
            if col.autoincrement:
                # This advances the generator and returns its new value.
                sql = ("SELECT GEN_ID(%s, 1) FROM RDB$DATABASE;"
                       % col.sequence_name)
                data, _ = self.schema.db.fetch(sql)
                newid = col.adapter.pull(data[0][0], col.dbtype)
                newids[key] = newid
                values[key] = newid
            elif key in kwargs:
                values[key] = kwargs[key]
        
        self.schema.db.insert((self, values))
        
        return newids
    
    def drop_primary(self):
        """Remove any PRIMARY KEY for this Table."""
        db = self.schema.db
        
        data, _ = db.fetch(
            "SELECT RDB$CONSTRAINT_NAME FROM RDB$RELATION_CONSTRAINTS "
            "WHERE (RDB$CONSTRAINT_TYPE = 'PRIMARY KEY') "
            "AND (RDB$RELATION_NAME = '%s')" % self.name)
        for row in data:
            db.execute('ALTER TABLE %s DROP CONSTRAINT %s;'
                       % (self.qname, row[0].rstrip()))


class FirebirdConnectionManager(conns.ConnectionManager):
    
    default_isolation = kinterbasdb.isc_tpb_read_committed
    _no_iso_tpb = (
        kinterbasdb.isc_tpb_version3
        + kinterbasdb.isc_tpb_shared
        + kinterbasdb.isc_tpb_nowait
        + kinterbasdb.isc_tpb_write
        + kinterbasdb.isc_tpb_rec_version
        )
    isolation_levels = ["READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"]
    
    def _get_conn(self):
        conn = kinterbasdb.connect(host=self.db.host,
                                   database=self.db.name,
                                   user=self.db.user,
                                   password=self.db.password,
                                   charset=self.db.encoding,
                                   )
        # Set the default TPB (for implicit transactions).
        conn.default_tpb = self._no_iso_tpb + self.default_isolation
        
        # Remove converters for FIXED so we can mix fixedpoint and decimal
        conn.set_type_trans_in({'FIXED': None})
        conn.set_type_trans_out({'FIXED': None})
        
        if self.initial_sql:
            conn.cursor().execute(self.initial_sql)
            conn.commit()
        return conn
    
    def _del_conn(self, conn):
        try:
            conn.close()
        except kinterbasdb.ProgrammingError, exc:
            # ProgrammingError: ('Connection is already closed.', ...)
            if exc.args[0] == 'Connection is already closed.':
                pass
            else:
                raise
    
    def isolate(self, isolation=None):
        """isolate() is not implemented for Firebird."""
        raise NotImplementedError("Firebird does not allow arbitrary re-isolation.")
    
    def _start_transaction(self, conn, isolation=None):
        """Start a transaction."""
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
            
            if isolation == "READ COMMITTED":
                isolation = kinterbasdb.isc_tpb_read_committed
            elif isolation == "REPEATABLE READ":
                isolation = kinterbasdb.isc_tpb_concurrency
            else:
                isolation = kinterbasdb.isc_tpb_consistency
        self.db.log("START TRANSACTION;")
        
        try:
            conn.begin(self._no_iso_tpb + isolation)
        except Exception, x:
            if self.db.is_connection_error(x):
                self.reset(conn)
                conn.begin(self._no_iso_tpb + isolation)
            else:
                raise
    
    def rollback(self):
        """Roll back the current transaction, if any."""
        try:
            conn = self.transactions.pop(self.id())
        except KeyError:
            pass
        else:
            self.db.log("ROLLBACK;")
            conn.rollback()
    
    def commit(self):
        """Commit the current transaction, if any."""
        try:
            conn = self.transactions.pop(self.id())
        except KeyError:
            pass
        else:
            self.db.log("COMMIT;")
            conn.commit()


class FirebirdSchema(geniusql.Schema):
    
    tableclass = FirebirdTable
    
    def _get_tables(self, conn=None):
        data, _ = self.db.fetch(
            "SELECT RDB$RELATION_NAME FROM RDB$RELATIONS "
            "WHERE RDB$SYSTEM_FLAG=0 AND RDB$VIEW_BLR IS NULL;", conn=conn)
        return [self.tableclass(name.strip(), self.db.quote(name.strip()),
                                self, created=True)
                for name, in data]
    
    def _get_table(self, tablename, conn=None):
        data, _ = self.db.fetch(
            "SELECT RDB$RELATION_NAME FROM RDB$RELATIONS "
            "WHERE RDB$SYSTEM_FLAG=0 AND RDB$VIEW_BLR IS NULL "
            "AND RDB$RELATION_NAME = '%s';" % tablename, conn=conn)
        for name, in data:
            name = name.strip()
            if name == tablename:
                return self.tableclass(name, self.db.quote(name),
                                       self, created=True)
        raise errors.MappingError("Table %r not found." % tablename)
    
    def _get_columns(self, table, conn=None):
        # FB pads table names to CHAR(31)
        tablename = table.name.ljust(31, " ")
        
        # Get Primary Key names first
        data, _ = self.db.fetch(
            "SELECT S.RDB$FIELD_NAME AS COLUMN_NAME "
            "FROM RDB$RELATION_CONSTRAINTS RC "
            "LEFT JOIN RDB$INDICES I ON (I.RDB$INDEX_NAME = RC.RDB$INDEX_NAME) "
            "LEFT JOIN RDB$INDEX_SEGMENTS S ON (S.RDB$INDEX_NAME = I.RDB$INDEX_NAME) "
            "WHERE (RC.RDB$CONSTRAINT_TYPE = 'PRIMARY KEY') "
            "AND (I.RDB$RELATION_NAME = '%s')" % tablename, conn=conn)
        pks = [row[0].rstrip() for row in data]
        
        # Now get the rest of the col data
        data, _ = self.db.fetch(
            "SELECT RF.RDB$FIELD_NAME, T.RDB$TYPE_NAME, F.RDB$FIELD_LENGTH, "
            "RF.RDB$DEFAULT_SOURCE, F.RDB$FIELD_PRECISION, F.RDB$FIELD_SCALE "
            "FROM RDB$RELATION_FIELDS RF LEFT JOIN RDB$FIELDS F "
            "ON F.RDB$FIELD_NAME = RF.RDB$FIELD_SOURCE "
            "LEFT JOIN RDB$TYPES T ON T.RDB$TYPE = F.RDB$FIELD_TYPE "
            "WHERE RF.RDB$RELATION_NAME='%s' AND "
            "T.RDB$FIELD_NAME='RDB$FIELD_TYPE';" % tablename, conn=conn)
        cols = []
        for name, dbtype, fieldlen, default, prec, scale in data:
            # FB pads name and type values to 31 chars.
            name, dbtype = name.rstrip(), dbtype.rstrip()
            
            dbtype = self.db.typeset.canonicalize(dbtype)()
            if prec:
                dbtype.precision = prec
                if scale:
                    dbtype.scale = abs(scale)
            else:
                dbtype.bytes = fieldlen
            
##            # Grr. INTEGER may actually have been declared as NUMERIC.
##            # See http://www.ibphoenix.com/main.nfs?a=ibphoenix&page=ibp_60_exact_num_fs
##            if scale and isinstance(dbtype, (SMALLINT, INTEGER)):
##                dbtype = "NUMERIC"
            
            key = (name in pks)
            
            # Column(pytype, dbtype, default=None, key=False, name, qname)
            col = geniusql.Column(dbtype.default_pytype, dbtype, None,
                                  key, name, self.db.quote(name))
            col.adapter = dbtype.default_adapter(col.pytype)
            cols.append(col)
            
            # RDB$RELATION_FIELDS.RDB$DEFAULT_SOURCE = None | "DEFAULT x"
            if default:
                default = default[len("DEFAULT "):]
                default = col.adapter.pull(default, col.dbtype)
        return cols
    
    def _get_indices(self, table, conn=None):
        data, _ = self.db.fetch(
            "SELECT I.RDB$INDEX_NAME, S.RDB$FIELD_NAME, I.RDB$UNIQUE_FLAG "
            "FROM RDB$INDICES I LEFT JOIN RDB$INDEX_SEGMENTS S "
            "ON (S.RDB$INDEX_NAME = I.RDB$INDEX_NAME) "
            "WHERE I.RDB$RELATION_NAME = '%s';" % table.name.ljust(31, " "),
            conn=conn)
        
        indices = []
        for name, colname, unique in data:
            name = name.rstrip()
            colname = colname.rstrip()
            unique = bool(unique)
            ind = geniusql.Index(name, self.db.quote(name),
                                 table.name, colname, unique)
            indices.append(ind)
        
        return indices
    
    def columnclause(self, column):
        """Return a clause for the given column for CREATE or ALTER TABLE.
        
        This will be of the form "name type [DEFAULT x] [NOT NULL]".
        
        Firebird needs the sequence created in a separate SQL statement.
        """
        default = column.default or ""
        if default:
            default = column.adapter.push(default, column.dbtype)
            default = " DEFAULT %s" % default
        
        notnull = ""
        if column.key:
            # Firebird PK's must be NOT NULL
            notnull = " NOT NULL"
        
        return '%s %s%s%s' % (column.qname, column.dbtype.ddl(), default, notnull)
    
    def sequence_name(self, tablename, columnkey):
        "Return the SQL sequence name for the given table name and column key."
        # If you want to use a map from your ORM's property names
        # to DB sequence names, override this method (that's why
        # the tablename must be included in the args).
        return self.db.sql_name("%s_%s_seq" % (tablename, columnkey))
    
    def create_sequence(self, table, column):
        """Create a SEQUENCE for the given column."""
        if column.sequence_name is not None:
            self.db.execute_ddl("CREATE GENERATOR %s;" % column.sequence_name)
            self.db.execute_ddl("SET GENERATOR %s TO %s;" %
                                (column.sequence_name, column.initial - 1))
    
    def drop_sequence(self, column):
        """Drop a SEQUENCE for the given column."""
        if column.sequence_name is not None:
            self.db.execute_ddl("DROP GENERATOR %s;" % column.sequence_name)


class FirebirdDatabase(geniusql.Database):
    
    selectwriter = FirebirdSelectWriter
    deparser = FirebirdSQLDeparser
    
    typeset = FirebirdTypeSet()
    connectionmanager = FirebirdConnectionManager
    
    schemaclass = FirebirdSchema
    multischema = False
    
    sql_name_max_length = 31
    
    # See http://www.destructor.de/firebird/charsets.htm
    # This worked fine as lowercase in FB 1.5; must be upper for FB 2.0
    encoding = 'UTF8'
    
    def __init__(self, **kwargs):
        geniusql.Database.__init__(self, **kwargs)
        
        # Obtain the server version in order to grab proper delegates.
        import kinterbasdb.services
        svcCon = kinterbasdb.services.connect(host=self.host, user=self.user,
                                              password=self.password)
        self._server_version = svcCon.getServerVersion()
        
        if "Firebird 2" in self._server_version:
            self.deparser = Firebird2SQLDeparser
    
    #                               Naming                               #
    
    def quote(self, name):
        """Return name, quoted for use in an SQL statement."""
        return '"' + name.replace('"', '""') + '"'
    
    deadlock_timeout = 10
    
    def is_connection_error(self, exc):
        """If the given exception instance is a connection error, return True.
        
        This should return True for errors which arise from broken connections;
        for example, if the database server has dropped the connection socket,
        or is unreachable.
        """
        if isinstance(exc, kinterbasdb.OperationalError):
            # OperationalError: (-902, 'begin transaction: \n  Unable to complete '
            #   'network request to host "localhost".\n  Error writing data to '
            #   the connection.\n  An established connection was aborted by the '
            #   software in your host machine.', 'SELECT 42 FROM rdb$database;')
            msg = exc.args[1]
            if 'Unable to complete network request' in msg:
                return True
        elif isinstance(exc, kinterbasdb.ProgrammingError):
            # ProgrammingError: (0, 'Invalid connection state.  The connection '
            #   'must be open to perform this operation.', ...)
            msg = exc.args[1]
            if 'Invalid connection state' in msg:
                return True
        return False
    
    def execute(self, sql, conn=None):
        """Return a native response for the given SQL."""
        try:
            if conn is None:
                conn = self.connections.get()
            if isinstance(sql, unicode):
                sql = sql.encode(self.encoding)
            self.log(sql)
            cur = conn.cursor()
            
            start = time.time()
            while True:
                try:
                    try:
                        cur.execute(sql)
                    except Exception, x:
                        if self.is_connection_error(x):
                            self.connections.reset(conn)
                            cur = conn.cursor()
                            start = time.time()
                            cur.execute(sql)
                        else:
                            raise
                    
                    # If we're not in a transaction, we need to auto-commit.
                    # This prevents "Previous transaction still active" errors.
                    if not self.connections.in_transaction():
                        conn.commit()
                    
                    return
                except Exception, x:
                    if self.is_timeout_error(x) and self.deadlock_timeout:
                        if time.time() - start < self.deadlock_timeout:
                            time.sleep(0.000001)
                            continue
                    raise
        except Exception, x:
            x.args += (sql,)
            # Dereference the connection so that release() is called back.
            conn = None
            raise
    
    def fetch(self, sql, conn=None):
        """Return rowdata, columns (name, type) for the given sql.
        
        sql should be an SQL string
        rowdata will be an iterable of iterables containing the result values.
        columns will be an iterable of (column name, data type) pairs.
        """
        try:
            if conn is None:
                conn = self.connections.get()
            if isinstance(sql, unicode):
                sql = sql.encode(self.encoding)
            self.log(sql)
            try:
                cur = conn.cursor()
                cur.execute(sql)
            except Exception, x:
                if self.is_connection_error(x):
                    self.connections.reset(conn)
                    cur = conn.cursor()
                    cur.execute(sql)
                else:
                    raise
            
            data = cur.fetchall()
            desc = cur.description
            cur.close()
            
            # If we're not in a transaction, we need to auto-commit.
            # This prevents "Previous transaction still active" errors.
            if not self.connections.in_transaction():
                conn.commit()
        except Exception, x:
            x.args += (sql,)
            # Dereference the connection so that release() is called back.
            conn = None
            raise
        return data, desc
    
    def is_timeout_error(self, exc):
        """If the given exception instance is a lock timeout, return True.
        
        This should return True for errors which arise from transaction
        locking timeouts; for example, if the database prevents 'dirty
        reads' by raising an error.
        """
        # ProgrammingError: (-901,
        # 'isc_dsql_execute: \n  lock conflict on no wait transaction',
        # 'UPDATE "testVet" SET "City" = \'Tehachapi\', ... ;')
        if isinstance(exc, kinterbasdb.ProgrammingError):
            return "lock conflict" in exc.args[1]
        # Firebird 2 changed this to
        # TransactionConflict: (-901,
        # 'isc_dsql_execute: \n  lock conflict on no wait transaction',
        if isinstance(exc, kinterbasdb.TransactionConflict):
            return "lock conflict" in exc.args[1]
        return False
    
    def version(self):
        return ("KInterbasDB Version: %r\nServer Version: %r"
                % (kinterbasdb.__version__, self._server_version))
    
    def create(self):
        # Firebird DB 'names' are actually filesystem paths.
        if "Firebird 2" in self._server_version:
            # Bah. At least for KInterbasDB Version: (3, 2, 0, 'final', 0),
            #   Server Version: 'WI-V2.0.3.12981 Firebird 2.0', the db name
            #   MUST be in single-quotes (not double), and the charset MUST
            #   be in double-quotes (not single).
            sql = ("CREATE DATABASE '%s' USER '%s' PASSWORD '%s' "
                   'DEFAULT CHARACTER SET "%s";'
                   % (self.name, self.user, self.password, self.encoding))
        else:
            sql = ("CREATE DATABASE %s USER '%s' PASSWORD '%s' "
                   "DEFAULT CHARACTER SET '%s';"
                   % (self.qname, self.user, self.password, self.encoding))
        
        # Use the kinterbasdb helper methods for cleaner create and drop.
        # We also use dialect 3 *always* to help with quoted identifiers.
        # Note that DATE has no time in dialect 3 (use TIMESTAMP instead).
        if isinstance(sql, unicode):
            sql = sql.encode(self.encoding)
        self.log(sql)
        conn = kinterbasdb.create_database(sql, 3)
        conn.close()
    
    def drop(self):
        # Must shut down all connections to avoid
        # "being accessed by other users" error.
        self.connections.shutdown()
        
        conn = self.connections._get_conn()
        conn.drop_database()
        # For some reason, the conn is already closed...
##        conn.close()


