import datetime
import sys
import traceback
from types import FunctionType, NoneType
from geniusql import logic, astwalk

# Comparison operator order from opcode.cmp_op:
#            0   1   2   3  4   5
#            <  <=  ==  !=  >  >=
# Comparison operator order when terms are swapped:
#            >  =>  ==  !=  <  <=
reverseop = {'<': '>', '<=': '>=', '==': '==', '!=': '!=', '>': '<', '>=': '<='}


__all__ = [
    'SQLExpression', 'Sentinel',
    'CannotRepresent', 'kw_arg', 'SQLDeparser',
    ]


class SQLExpression(object):
    """Wraps a column or other expression for use in SQLDeparser.
    
    sql: the expression to be placed in the SQL for this expression.
        This should not contain an alias ("AS" clause); that will be
        provided by the consumer, usually via the 'name' attribute.
    name: the name of the expression; may be used as an alias (with "AS").
        This should *not* be quoted/escaped, as it may need to be merged
        with other strings before being used (for example, "expr_" + name).
        Consumers must quote the name attribute appropriately (usually
        via db.quote(e.name)) before inserting it into SQL.
    value: If not None, the expression is a "constant"; that is, we already
        know its defined Python value (and that it does not have any basis
        in column values).
    aggregate: If True, the expression represents an aggregated value
        such as MAX(colref). This flag is used by consumers to write
        GROUP BY clauses.
    """
    
    def __init__(self, sql, name, dbtype, pytype, value=None):
        self.sql = sql
        self.name = name
        
        self.dbtype = dbtype
        self.pytype = pytype
        self.adapter = None
        
        self.value = value
        self.aggregate = False
    
    def __cmp__(self, other):
        return cmp(self.sql, other.sql)
    
    def __repr__(self):
        return ("%s.%s(%r, dbtype=%s)" %
                (self.__module__, self.__class__.__name__, self.sql,
                 self.dbtype.__class__.__name__))


class SQLTableRef(object):
    
    def __init__(self, table, alias):
        self.table = table
        self.alias = alias


# AST Sentinels
class Sentinel(object):
    
    def __init__(self, name):
        self.name = name
    
    def __repr__(self):
        return 'AST Sentinel: %s' % self.name

kw_arg = Sentinel('Keyword Arg')
# CannotRepresent exists so that a portion of an Expression can be
# labeled imperfect. For example, the function "iscurrentweek"
# rarely has an SQL equivalent. All rows (which match the rest of the
# Expression) will be recalled; they can then be compared in expr(unit).
class CannotRepresent(Exception):
    pass


ast_to_sql_cache = {}

class SQLDeparser(astwalk.ASTDeparser):
    """Produce SQL from a supplied logic.Expression object.
    
    Attributes of each argument in the Expression's function signature
    will be mapped to table columns. Keyword arguments should be bound
    using Expression.bind_args before calling this deparser.
    """
    
    # Whether or not the SQL perfectly matches the Python Expression.
    # In many cases, a provider may be able to return an imperfect subset
    # of the rows; they should generate the SQL for that and set imperfect
    # to True. Once the deparser is running, no code should set imperfect
    # to False.
    # Note that this is not the same as CannotRepresent, which is the
    # exception raised for an imperfect SUBexpression. But in general,
    # this base class will set imperfect for you when computing AND
    # and OR, and when the final result is examined. You should only
    # have to set imperfect when you return an SQLExpression that is
    # imperfect.
    imperfect = False
    
    # Some constants are function or class objects,
    # which should not be coerced.
    no_coerce = (FunctionType,
                 type,
                 type(len),       # <type 'builtin_function_or_method'>
                 )
    
    # SQL comparison operators (matching the order of opcode.cmp_op).
    sql_cmp_op = {'<': '<',
                  '<=': '<=',
                  '==': '=',
                  '!=': '!=',
                  '>': '>',
                  '>=': '>=',
                  'in': 'in',
                  'not in': 'not in',
                  }
    
    # SQL binary operators; a map from values in astwalk.binary_operators
    # to their SQL equivalents. The default map is isomorphic.
    sql_bin_op = dict([(k, k) for k in astwalk.repr_to_op])
    
    none_expr = SQLExpression("NULL", "expr0", None, NoneType)
    
    def __init__(self, tables, expr, typeset):
        self.tables = tables
        self.expr = expr
        self.typeset = typeset
        
        self.groups = []
        
        # Cache coerced booleans and None
        b = self.typeset.bool_exprs(SQLExpression)
        self.expr_true, self.expr_false, self.comp_true, self.comp_false = b
        for boolexpr in b:
            self.exprcount += 1
            boolexpr.name = "expr%s" % self.exprcount
        
        astwalk.ASTDeparser.__init__(self, expr.ast)
    
    exprcount = 0
    
    def get_expr(self, sql, pytype, adapter=None):
        """Return an SQLExpression for the given sql of the given pytype."""
        self.exprcount += 1
        dbtype = self.typeset.database_type(pytype)
        e = SQLExpression(sql, "expr%s" % self.exprcount, dbtype, pytype)
        e.adapter = adapter or dbtype.default_adapter(pytype)
        return e
    
    def const(self, value, sql=None):
        """Return an SQLExpression for the given constant value."""
        if value is None:
            return self.none_expr
        
        e = self.get_expr(sql, type(value))
        e.value = value
        if sql is None:
            e.sql = e.adapter.push(value, e.dbtype)
        return e
    
    def code(self):
        """Walk self and return a suitable WHERE clause."""
        root = self.ast.root
        rootrepr = repr(root)
        tablenames = tuple([table.name for alias, table in self.tables])
        
        # Grab the completed SQL from a cache, if available
        try:
            sql, imp = ast_to_sql_cache[(self.typeset, rootrepr, tablenames)]
        except KeyError:
            pass
        else:
            self.imperfect = imp
            return sql
        
        self.imperfect = False
        
        try:
            result = self.walk(root)
            # After walk(), the result should be a single string,
            # which is the SQL representation of our Expression.
        except CannotRepresent:
            # The entire expression could not be evaluated.
            result = self.expr_true
            self.imperfect = True
        else:
            if result == self.comp_true:
                result = self.expr_true
            elif result == self.comp_false:
                result = self.expr_false
        
        # Cache the result
        ast_to_sql_cache[(self.typeset, rootrepr, tablenames)] = (result.sql, self.imperfect)
        
        return result.sql
    
    def field_list(self):
        """Walk self and return a list of field objects."""
        self.imperfect = False
        root = self.ast.root
        
        # When building a field list, ignore the last BUILD_TUPLE.
        if not isinstance(root, (astwalk.ast.Tuple, astwalk.ast.List)):
            raise ValueError("Attribute AST roots must be Tuple or List, "
                             "not %s" % root.__class__.__name__)
        result = []
        for term in root.getChildren():
            self.aggregate = False
            e = self.walk(term)
            e.aggregate = self.aggregate
            result.append(e)
        return result
    
    def walk(self, node):
        """Walk the AST and return a string of code."""
        nodetype = node.__class__.__name__
        method = getattr(self, "visit_" + nodetype)
        args = node.getChildren()
        if self.verbose:
            self.debug(nodetype, args)
        return method(*args)
    
    def visit_And(self, *terms):
        newterms = []
        for term in terms:
            try:
                term = self.walk(term)
            except CannotRepresent:
                self.imperfect = True
                # Use TRUE for the term, so all records are returned.
                term = self.expr_true
            else:
                # Blurg. SQL Server is *so* picky.
                if term == self.comp_true:
                    term = self.expr_true
                elif term == self.comp_false:
                    term = self.expr_false
            newterms.append("(%s)" % term.sql)
        clause = self.get_expr(" AND ".join(newterms), bool)
        
        if self.verbose:
            self.debug("clause:", clause.sql, "\n")
        
        return clause
    
    def visit_Or(self, *terms):
        newterms = []
        for term in terms:
            try:
                term = self.walk(term)
            except CannotRepresent:
                self.imperfect = True
                # Use TRUE for the term, so all records are returned.
                term = self.expr_true
            else:
                # Blurg. SQL Server is *so* picky.
                if term == self.comp_true:
                    term = self.expr_true
                elif term == self.comp_false:
                    term = self.expr_false
            newterms.append("(%s)" % term.sql)
        clause = self.get_expr(" OR ".join(newterms), bool)
        
        if self.verbose:
            self.debug("clause:", clause.sql, "\n")
        
        return clause
    
    def visit_Name(self, name):
        if name in self.ast.args:
            # We've hit a reference to a positional arg, which in our case
            # implies a reference to a DB table.
            alias, table = self.tables[self.ast.args.index(name)]
            return SQLTableRef(table, alias)
        else:
            # Since lambdas don't support local bindings,
            # any remaining local name must be a keyword arg.
            return kw_arg
    
    def visit_Getattr(self, expr, attrname):
        expr = self.walk(expr)
        if isinstance(expr, SQLTableRef):
            # The name in question refers to a DB column (see visit_Name).
            col = expr.table[attrname]
            atom = SQLExpression('%s.%s' % (expr.alias, col.qname),
                                 attrname, col.dbtype, col.pytype)
            atom.adapter = col.adapter
        else:
            # 'expr.name' will reference an attribute of the expr object.
            # Stick the expr and name in a tuple for later processing
            # (for example, in visit_CallFunc).
            atom = (expr, attrname)
        return atom
    
    def visit_Const(self, value):
        if not isinstance(value, self.no_coerce):
            value = self.const(value)
        return value
    
    def visit_Tuple(self, *terms):
        val = []
        newterms = []
        for term in terms:
            term = self.walk(term)
            val.append(term.value)
            newterms.append(term.sql)
        return SQLExpression("(" + ", ".join(newterms) + ")",
                             "tuple", None, None, tuple(val))
    
    # Assume all DB's have a tuple () syntax but no list [] syntax
    visit_List = visit_Tuple
    
    def visit_CallFunc(self, func, *args):
        # e.g. CallFunc(Name('min'), [Getattr(Name('v'), 'Date')], None, None)
        dstar_args = args[-1]
        star_args = args[-2]
        
        posargs = []
        kwargs = {}
        for arg in args[:-2]:
            if isinstance(arg, astwalk.ast.Keyword):
                kwargs[arg.name] = self.walk(arg.value)
            else:
                posargs.append(self.walk(arg))
        
        func = self.walk(func)
        
        # Handle function objects.
        if isinstance(func, tuple):
            # A function which was an attribute of another object;
            # for example, "x.Field.startswith". The tuple will be of
            # the form (obj, name). See visit_GetAttr.
            obj, name = func
            dispatch = getattr(self, "attr_" + name, None)
            if dispatch:
                return dispatch(obj, *posargs)
            raise CannotRepresent("No handler found for function %r.%r." %
                                  (obj, name))
        
        if logic.builtins.get(func.__name__, None) is func:
            dispatch = getattr(self, "builtins_" + func.__name__, None)
            if dispatch:
                return dispatch(*posargs)
        
        funcname = func.__module__ + "_" + func.__name__
        funcname = funcname.replace(".", "_")
        if funcname.startswith("_"):
            funcname = "func" + funcname
        dispatch = getattr(self, funcname, None)
        if dispatch:
            return dispatch(*posargs)
        
        raise CannotRepresent(func)
    
    # Validity for a comparison operation between two types.
    compare_types = {}
    
    def visit_Compare(self, op1, *ops):
        op1 = self.walk(op1)
        
        newterms = []
        i = 0
        while i < len(ops):
            op, op2 = ops[i:i+2]
            i += 2
            op2 = self.walk(op2)
            
            if not self.compare_types.get((op1.pytype, op, op2.pytype), False):
                raise CannotRepresent("No comparison function %r between %r and %r" %
                                      (op, op1, op2))
            
            if op == 'in':
                term = self.containedby(op1, op2)
            elif op == 'not in':
                term = self.containedby(op1, op2)
                term.sql = "NOT " + term.sql
            elif op1.sql == 'NULL':
                if op in ('==', 'is'):
                    term = self.get_expr(op2.sql + " IS NULL", bool)
                elif op in ('!=', 'is not'):
                    term = self.get_expr(op2.sql + " IS NOT NULL", bool)
                else:
                    raise ValueError("Non-equality Null comparisons not allowed.")
            elif op2.sql == 'NULL':
                if op in ('==', 'is'):
                    term = self.get_expr(op1.sql + " IS NULL", bool)
                elif op in ('!=', 'is not'):
                    term = self.get_expr(op1.sql + " IS NOT NULL", bool)
                else:
                    raise ValueError("Non-equality Null comparisons not allowed.")
            elif op in reverseop:
                try:
                    sql = op1.adapter.compare_op(op1, op, self.sql_cmp_op[op], op2)
                except TypeError, exc:
                    if self.verbose:
                        self.debug("".join(traceback.format_exception(*sys.exc_info())))
                    rop = reverseop[op]
                    try:
                        sql = op1.adapter.compare_op(op2, rop, self.sql_cmp_op[rop], op1)
                    except TypeError, exc:
                        if self.verbose:
                            self.debug("".join(traceback.format_exception(*sys.exc_info())))
                        raise CannotRepresent("No comparison function %r "
                                              "between %r and %r." %
                                              (op, op1, op2))
                term = self.get_expr(sql, bool)
            else:
                raise ValueError("Operator %r not handled." % op)
            
            newterms.append("(%s)" % term.sql)
            op1 = op2
        return self.get_expr(" and ".join(newterms), bool)
    
    def visit_Subscript(self, expr, flags, *subs):
        expr = self.walk(expr)
        # The only Subscript used in Expressions should be kwargs[key].
        if expr is not kw_arg:
            raise ValueError("Subscript %r of %s object not allowed." %
                             (subs, expr))
        if len(subs) > 1:
            raise ValueError("Multiple subscripts %r of %s not supported."  %
                             (subs, expr))
        
        name = subs[0].value
        
        value = self.expr.kwargs[name]
        if not isinstance(value, self.no_coerce):
            value = self.const(value)
        return value
    
    def visit_Not(self, expr):
        expr = self.walk(expr)
        return self.get_expr("NOT (" + expr.sql + ")", bool)
    
    # --------------------------- Dispatchees --------------------------- #
    
    # Notice these are ordered pairs. Escape \ before introducing new ones.
    # Values in these two lists should be strings encoded with self.encoding.
    like_escapes = [("%", r"\%"), ("_", r"\_")]
    
    def escape_like(self, sql):
        """Prepare a string value for use in a LIKE comparison."""
        # Notice we strip leading and trailing quote-marks.
        sql = sql.strip("'\"")
        for pat, repl in self.like_escapes:
            sql = sql.replace(pat, repl)
        return sql
    
    def attr_startswith(self, tos, arg):
        return self.get_expr(tos.sql + " LIKE '" + self.escape_like(arg.sql) + "%'", bool)
    
    def attr_endswith(self, tos, arg):
        return self.get_expr(tos.sql + " LIKE '%" + self.escape_like(arg.sql) + "'", bool)
    
    def containedby(self, op1, op2):
        if op1.value is not None:
            # Looking for text in a field. Use Like (reverse terms).
            like = self.escape_like(op1.sql)
            return self.get_expr(op2.sql + " LIKE '%" + like + "%'", bool)
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
                return self.expr_false
    
    def builtins_icontainedby(self, op1, op2):
        if op1.value is not None:
            # Looking for text in a field. Use Like (reverse terms).
            return self.get_expr("LOWER(" + op2.sql + ") LIKE '%" +
                                 self.escape_like(op1.sql).lower()
                                 + "%'", bool)
        else:
            # Looking for field in (a, b, c).
            # Force all args to lowercase for case-insensitive comparison.
            atoms = []
            for x in op2.value:
                adapter = op1.dbtype.default_adapter(type(x))
                atoms.append(adapter.push(x.lower(), op1.dbtype))
            return self.get_expr("LOWER(%s) IN (%s)" %
                                 (op1.sql, ", ".join(atoms)), bool)
    
    def builtins_icontains(self, x, y):
        return self.builtins_icontainedby(y, x)
    
    def builtins_istartswith(self, x, y):
        return self.get_expr("LOWER(" + x.sql + ") LIKE '" +
                             self.escape_like(y.sql) + "%'", bool)
    
    def builtins_iendswith(self, x, y):
        return self.get_expr("LOWER(" + x.sql + ") LIKE '%" +
                             self.escape_like(y.sql) + "'", bool)
    
    def builtins_ieq(self, x, y):
        return self.get_expr("LOWER(" + x.sql + ") = LOWER(" + y.sql + ")", bool)
    
    def builtins_now(self):
        """Return a datetime.datetime for the current time in the local TZ."""
        return self.get_expr("NOW()", datetime.datetime)
    
    def builtins_utcnow(self):
        """Return a datetime.datetime for the current time in the UTC TZ."""
        raise CannotRepresent("utcnow not implemented")
    
    def builtins_today(self):
        """Return a datetime.datetime for the current time in the local TZ."""
        return self.get_expr("CURRENT_DATE", datetime.date)
    
    def builtins_year(self, x):
        return self.get_expr("YEAR(" + x.sql + ")", int)
    
    def builtins_month(self, x):
        return self.get_expr("MONTH(" + x.sql + ")", int)
    
    def builtins_day(self, x):
        return self.get_expr("DAY(" + x.sql + ")", int)
    
    def func__builtin___len(self, x):
        return self.get_expr("LENGTH(" + x.sql + ")", int)
    
    def func__builtin___min(self, x):
        self.aggregate = True
        x.name = "min_%s" % x.name
        x.sql = "MIN(" + x.sql + ")"
        return x
    
    def func__builtin___max(self, x):
        self.aggregate = True
        x.name = "max_%s" % x.name
        x.sql = "MAX(" + x.sql + ")"
        return x
    
    def builtins_count(self, x):
        self.aggregate = True
        return self.get_expr("COUNT(" + x.sql + ")", int)
    
    def func__builtin___reversed(self, x):
        # Assume reversed is always used for DESC ordering.
        x.sql += " DESC"
        return x
    # For version of Python which did not possess the 'reversed' builtin.
    builtins_reversed = func__builtin___reversed
    
    def builtins_alias(self, x, y):
        # We don't need to modify x.sql here; SelectWriter.deparse_attributes
        # will include the " AS name" clause for us.
        x.name = y.sql.strip("\"'")
        return x
    
    #                           Binary operations                         #
    
    # Resultant type for a binary operation between two types.
    result_type = {}
    
    def binary_op(self, left, op, right):
        left = self.walk(left)
        right = self.walk(right)
        
        try:
            newsql = left.adapter.binary_op(left, op,
                                            self.sql_bin_op[op], right)
        except TypeError:
            raise CannotRepresent("No binary function %r between %r and %r" %
                                  (op, left, right))
        
        newpytype = self.result_type[(left.pytype, op, right.pytype)]
        
        # re-use left
        left.sql = newsql
        if newpytype != left.pytype:
            left.pytype = newpytype
            left.dbtype = self.typeset.database_type(newpytype)
            left.adapter = left.dbtype.default_adapter(newpytype)
        if not left.name.startswith("expr_"):
            left.name = "expr_%s" % left.name
        return left


def _binary_operation_result_types():
    """Return a dict of (type(A), op, type(B)): type(op(A, B)) for known types."""
    results = {}
    
    knowntypes = [3, 3L, 3.0, 'a', u'b', True]
    try:
        import datetime
        knowntypes.extend([datetime.date(2004, 1, 1),
                           datetime.datetime(2004, 1, 31),
                           datetime.timedelta(3)])
    except ImportError:
        pass
    try:
        import decimal
        knowntypes.append(decimal.Decimal(3))
    except ImportError:
        pass
    
    for A in knowntypes:
        for B in knowntypes:
            for symbol, op in astwalk.repr_to_op.iteritems():
                try:
                    result = op(A, B)
                except TypeError:
                    pass
                else:
                    results[(type(A), symbol, type(B))] = type(result)
    
    return results
SQLDeparser.result_type = _binary_operation_result_types()

def _comparison_operation_types():
    """Return a dict of {(type(A), op, type(B)): can compare?} for known types."""
    results = {}
    
    knowntypes = [3, 3L, 3.0, 'a', u'b', None, True]
    numtypes = [int, long, float]
    try:
        import datetime
        knowntypes.extend([datetime.date(2004, 1, 1),
                           datetime.datetime(2004, 1, 31),
                           datetime.timedelta(3)])
        datetypes = [datetime.date, datetime.datetime, datetime.timedelta]
    except ImportError:
        datetypes = []
    
    try:
        import decimal
        knowntypes.append(decimal.Decimal(3))
        numtypes.append(decimal.Decimal)
    except ImportError:
        pass
    
    import operator, opcode
    
    for A in knowntypes:
        # All types should allow unrestricted containment comparisons.
        # The type of each element in the list will have to be checked
        # inside the Deparser.
        # Note we use contains for 'in and 'not in', since they should
        # error (or not) similarly.
        for symbol, op in [('in', operator.contains),
                           ('not in', operator.contains)]:
            results[(type(A), symbol, list)] = True
            results[(type(A), symbol, tuple)] = True
        
        for B in knowntypes:
            # Python versions previous to 2.6 allowed comparisons between
            # unrelated types, like 'abc' > 12. Manually munge known
            # incompatibilities in the results by special-casing the
            # comparison operators for dissimilar types.
            for symbol, op in [('<', operator.lt), ('<=', operator.le),
                               ('>', operator.gt), ('>=', operator.ge)]:
                if type(A) in numtypes and type(B) in numtypes:
                    results[(type(A), symbol, type(B))] = True
                elif type(A) in [str, unicode] and type(B) in [str, unicode]:
                    results[(type(A), symbol, type(B))] = True
                elif type(A) in datetypes or type(B) in datetypes:
                    # The datetime types are very strict about comparisons.
                    try:
                        result = op(A, B)
                    except TypeError:
                        results[(type(A), symbol, type(B))] = False
                    else:
                        results[(type(A), symbol, type(B))] = True
                else:
                    results[(type(A), symbol, type(B))] = False
            
            # However, all types should allow equality comparison.
            for symbol, op in [('==', operator.eq), ('!=', operator.ne),
                               ('is', operator.is_), ('is not', operator.is_not)]:
                try:
                    result = op(A, B)
                except TypeError:
                    results[(type(A), symbol, type(B))] = False
                else:
                    results[(type(A), symbol, type(B))] = True
    
    return results
SQLDeparser.compare_types = _comparison_operation_types()

