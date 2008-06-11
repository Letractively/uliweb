import datetime
from types import FunctionType
from geniusql import logic, codewalk

# Comparison operator order from opcode.cmp_op:
#            0   1   2   3  4   5
#            <  <=  ==  !=  >  >=
# Comparison operator order when terms are swapped:
#            >  =>  ==  !=  <  <=
reverseop = (4,  5,  2,  3, 0,  1)


__all__ = [
    'SQLExpression', 'Sentinel',
    'cannot_represent', 'kw_arg', 'SQLDecompiler',
    ]


class SQLExpression(object):
    """Wraps a column or other expression for use in SQLDecompiler's stack.
    
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
        if isinstance(other, SQLExpression):
            return cmp(self.sql, other.sql)
        raise TypeError("can't compare %s to %s" % (type(self), type(other)),
                        other)
    
    def __repr__(self):
        return ("%s.%s(%r, dbtype=%s)" %
                (self.__module__, self.__class__.__name__, self.sql,
                 self.dbtype.__class__.__name__))


# Stack sentinels
class Sentinel(object):
    
    def __init__(self, name):
        self.name = name
    
    def __repr__(self):
        return 'Stack Sentinel: %s' % self.name

kw_arg = Sentinel('Keyword Arg')
# cannot_represent exists so that a portion of an Expression can be
# labeled imperfect. For example, the function "iscurrentweek"
# rarely has an SQL equivalent. All rows (which match the rest of the
# Expression) will be recalled; they can then be compared in expr(unit).
cannot_represent = Sentinel('Cannot Repr')


class SQLDecompiler(codewalk.LambdaDecompiler):
    """Produce SQL from a supplied logic.Expression object.
    
    Attributes of each argument in the Expression's function signature
    will be mapped to table columns. Keyword arguments should be bound
    using Expression.bind_args before calling this decompiler.
    """
    
    # Whether or not the SQL perfectly matches the Python Expression.
    # In many cases, a provider may be able to return an imperfect subset
    # of the rows; they should generate the SQL for that and set imperfect
    # to True. Once the decompiler is running, no code should set imperfect
    # to False.
    # Note that this is not the same as cannot_represent, which is the stack
    # value for an imperfect SUBexpression. But in general, this base class
    # will set imperfect for you when computing AND and OR, and when the
    # final result is examined. You should only have to set imperfect
    # when you put actual SQL on the stack that is imperfect.
    imperfect = False
    
    # Some constants are function or class objects,
    # which should not be coerced.
    no_coerce = (FunctionType,
                 type,
                 type(len),       # <type 'builtin_function_or_method'>
                 )
    
    # SQL comparison operators (matching the order of opcode.cmp_op).
    sql_cmp_op = ('<', '<=', '=', '!=', '>', '>=', 'in', 'not in')
    
    # SQL binary operators; a map from values in codewalk.binary_operators
    # to their SQL equivalents. The default map is isomorphic.
    sql_bin_op = dict([(v, v) for v in codewalk.binary_repr.itervalues()])
    
    # These are not adapter.push(bool) (which are used on one side of 
    # a comparison). Instead, these are used when the whole (sub)expression
    # is True or False, e.g. "WHERE TRUE", or "WHERE TRUE and 'a'.'b' = 3".
    bool_true = "TRUE"
    bool_false = "FALSE"
    
    def __init__(self, tables, expr, typeset):
        self.tables = tables
        self.expr = expr
        self.typeset = typeset
        
        self.groups = []
        
        # Cache coerced booleans
        self.true_expr = self.const(True, self.bool_true)
        self.false_expr = self.const(False, self.bool_false)
        
        booldbtype = self.typeset.database_type(bool)
        booladapter = booldbtype.default_adapter(bool)
        self.T = self.const(True, booladapter.push(True, booldbtype))
        self.F = self.const(False, booladapter.push(False, booldbtype))
        
        self.none_expr = SQLExpression("NULL", "expr0", None, type(None))
        
        codewalk.LambdaDecompiler.__init__(self, expr.func)
    
    exprcount = 0
    
    def get_expr(self, sql, pytype, adapter=None):
        """Return an SQLExpression for the given sql of the given pytype."""
        self.exprcount += 1
        name = "expr%s" % self.exprcount
        
        dbtype = self.typeset.database_type(pytype)
        e = SQLExpression(sql, name, dbtype, pytype)
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
    
    def append_expr(self, sql, pytype, agg=None):
        """Syntactic sugar for self.stack.append(self.get_expr(sql, pytype))."""
        e = self.get_expr(sql, pytype)
        if agg is not None:
            e.aggregate = agg
        self.stack.append(e)
    
    def code(self):
        """Walk self and return a suitable WHERE clause."""
        self.imperfect = False
        self.walk()
        # After walk(), self.stack should be reduced to a single string,
        # which is the SQL representation of our Expression.
        result = self.stack[0]
        if result is cannot_represent:
            # The entire expression could not be evaluated.
            result = self.true_expr
            self.imperfect = True
        elif result == self.T:
            result = self.true_expr
        elif result == self.F:
            result = self.false_expr
        return result.sql
    
    _ignore_final_build = False
    
    def field_list(self):
        """Walk self and return a list of field objects."""
        self._ignore_final_build = True
        self.walk()
        return self.stack
    
    def visit_instruction(self, op, lo=None, hi=None):
        # Get the instruction pointer for the current instruction.
        ip = self.cursor - 3
        if hi is None:
            ip += 1
            if lo is None:
                ip += 1
        
        terms = self.targets.get(ip)
        if terms:
            clause = self.stack[-1]
            while terms:
                term, oper = terms.pop()
                if term is cannot_represent:
                    # Use TRUE for the term, so all records are returned.
                    term = self.true_expr
                    self.imperfect = True
                if clause is cannot_represent:
                    # Use TRUE for the clause, so all records are returned.
                    clause = self.true_expr
                    self.imperfect = True
                
                # Blurg. SQL Server is *so* picky.
                if term == self.T:
                    term = self.true_expr
                elif term == self.F:
                    term = self.false_expr
                if clause == self.T:
                    clause = self.true_expr
                elif clause == self.F:
                    clause = self.false_expr
                
                agg = term.aggregate or clause.aggregate
                clause = self.get_expr("(%s) %s (%s)" %
                                       (term.sql, oper.upper(), clause.sql),
                                       bool)
                clause.aggregate = agg
            
            # Replace TOS with the new clause, so that further
            # combinations have access to it.
            self.stack[-1] = clause
            if self.verbose:
                self.debug("clause:", clause.sql, "\n")
            
            if op == 1:
                # Py2.4: The current instruction is POP_TOP, which means
                # the previous is probably JUMP_*. If so, we're going to
                # pop the value we just placed on the stack and lose it.
                # We need to replace the entry that the JUMP_* made in
                # self.targets with our new TOS.
                target = self.targets[self.last_target_ip]
                target[-1] = ((clause, target[-1][1]))
                if self.verbose:
                    self.debug("newtarget:", self.last_target_ip, target)
    
    def visit_LOAD_DEREF(self, lo, hi):
        raise ValueError("Illegal reference found in %s." % self.expr)
    
    def visit_LOAD_GLOBAL(self, lo, hi):
        raise ValueError("Illegal global found in %s." % self.expr)
    
    def visit_LOAD_FAST(self, lo, hi):
        arg_index = lo + (hi << 8)
        if arg_index < self.co_argcount:
            # We've hit a reference to a positional arg, which in our case
            # implies a reference to a DB table. Append the (qname, table)
            # tuple for later unpacking inside visit_LOAD_ATTR.
            self.stack.append(self.tables[arg_index])
        else:
            # Since lambdas don't support local bindings,
            # any remaining local name must be a keyword arg.
            self.stack.append(kw_arg)
    
    def visit_LOAD_ATTR(self, lo, hi):
        name = self.co_names[lo + (hi << 8)]
        tos = self.stack.pop()
        if isinstance(tos, tuple):
            # The name in question refers to a DB column (see visit_LOAD_FAST).
            alias, table = tos
            col = table[name]
            atom = SQLExpression('%s.%s' % (alias, col.qname),
                                 name, col.dbtype, col.pytype)
            atom.adapter = col.adapter
        else:
            # 'tos.name' will reference an attribute of the tos object.
            # Stick the tos and name in a tuple for later processing
            # (for example, in visit_CALL_FUNCTION).
            atom = (tos, name)
        self.stack.append(atom)
    
    def visit_LOAD_CONST(self, lo, hi):
        val = self.co_consts[lo + (hi << 8)]
        if not isinstance(val, self.no_coerce):
            val = self.const(val)
        self.stack.append(val)
    
    def visit_BUILD_TUPLE(self, lo, hi):
        if self.cursor == len(self._bytecode) - 1 and self._ignore_final_build:
            # When building a field list, ignore the last BUILD_TUPLE.
            return
        
        terms = []
        agg = False
        for i in range(lo + (hi << 8)):
            e = self.stack.pop()
            terms.append(e.sql)
            agg |= e.aggregate
        e = SQLExpression("(" + ", ".join(terms) + ")",
                          "tuple", None, None, True)
        e.aggregate = agg
        self.stack.append(e)
    
    visit_BUILD_LIST = visit_BUILD_TUPLE
    
    def visit_CALL_FUNCTION(self, lo, hi):
        agg = False
        
        kwargs = {}
        for i in xrange(hi):
            val = self.stack.pop()
            key = self.stack.pop()
            kwargs[key] = val
            agg |= (val.aggregate or key.aggregate)
        kwargs = [k.sql + "=" + v.sql for k, v in kwargs.iteritems()]
        
        args = []
        for i in xrange(lo):
            arg = self.stack.pop()
            agg |= arg.aggregate
            args.append(arg)
        args.reverse()
        
        if kwargs:
            args += kwargs
        
        func = self.stack.pop()
        
        # Handle function objects.
        if isinstance(func, tuple):
            # A function which was an attribute of another object;
            # for example, "x.Field.startswith". The tuple will be of
            # the form (tos, name) where "tos" is the object and 'name'
            # is the name of the desired attribute of that object.
            # See visit_LOAD_ATTR.
            tos, name = func
            dispatch = getattr(self, "attr_" + name, None)
            if dispatch:
                e = dispatch(tos, *args)
                # attr_* methods don't have to check the agg of their args.
                e.aggregate |= agg
                self.stack.append(e)
                return
        elif logic.builtins.get(func.__name__, None) is func:
            dispatch = getattr(self, "builtins_" + func.__name__, None)
            if dispatch:
                e = dispatch(*args)
                # attr_* methods don't have to check the agg of their args.
                e.aggregate |= agg
                self.stack.append(e)
                return
        else:
            funcname = func.__module__ + "_" + func.__name__
            funcname = funcname.replace(".", "_")
            if funcname.startswith("_"):
                funcname = "func" + funcname
            dispatch = getattr(self, funcname, None)
            if dispatch:
                e = dispatch(*args)
                # attr_* methods don't have to check the agg of their args.
                e.aggregate |= agg
                self.stack.append(e)
                return
        
        self.stack.append(cannot_represent)
    
    def visit_COMPARE_OP(self, lo, hi):
        op2, op1 = self.stack.pop(), self.stack.pop()
        if op1 is cannot_represent or op2 is cannot_represent:
            self.stack.append(cannot_represent)
            return
        
        agg = op1.aggregate or op2.aggregate
        op = lo + (hi << 8)
        if op in (6, 7):     # in, not in
            value = self.containedby(op1, op2)
            if op == 7:
                value.sql = "NOT " + value.sql
            value.agg = agg
            self.stack.append(value)
        elif op1.sql == 'NULL':
            if op in (2, 8):    # '==', is
                self.append_expr(op2.sql + " IS NULL", bool, agg=agg)
            elif op in (3, 9):  # '!=', 'is not'
                self.append_expr(op2.sql + " IS NOT NULL", bool, agg=agg)
            else:
                raise ValueError("Non-equality Null comparisons not allowed.")
        elif op2.sql == 'NULL':
            if op in (2, 8):    # '==', 'is'
                self.append_expr(op1.sql + " IS NULL", bool, agg=agg)
            elif op in (3, 9):  # '!=', 'is not'
                self.append_expr(op1.sql + " IS NOT NULL", bool, agg=agg)
            else:
                raise ValueError("Non-equality Null comparisons not allowed.")
        elif 0 <= op <= 5:
            try:
                sql = op1.adapter.compare_op(op1, op, self.sql_cmp_op[op], op2)
            except TypeError:
                try:
                    rop = reverseop[op]
                    sql = op1.adapter.compare_op(op2, rop, self.sql_cmp_op[rop], op1)
                except TypeError:
                    self.stack.append(cannot_represent)
                    return
            self.append_expr(sql, bool, agg=agg)
        else:
            import opcode
            raise ValueError("Operator %r not handled." % opcode.cmp_op[op])
    
    def visit_BINARY_SUBSCR(self):
        # The only BINARY_SUBSCR used in Expressions should be kwargs[key].
        name = self.stack.pop()
        tos = self.stack.pop()
        if tos is not kw_arg:
            raise ValueError("Subscript %s of %s object not allowed."
                             % (name, tos))
        # name, since formed in LOAD_CONST, may have extraneous quotes.
        name = name.sql.strip("'\"")
        value = self.expr.kwargs[name]
        if not isinstance(value, self.no_coerce):
            value = self.const(value)
        self.stack.append(value)
    
    def visit_UNARY_NOT(self):
        op = self.stack.pop()
        if op is cannot_represent:
            self.stack.append(cannot_represent)
        else:
            self.append_expr("NOT (" + op.sql + ")", bool, op.aggregate)
    
    # --------------------------- Dispatchees --------------------------- #
    
    # Notice these are ordered pairs. Escape \ before introducing new ones.
    # Values in these two lists should be strings encoded with self.encoding.
    like_escapes = [("%", r"\%"), ("_", r"\_")]
    
    def escape_like(self, value):
        """Prepare a string value for use in a LIKE comparison."""
        if not isinstance(value, str):
            value = value.encode(self.encoding)
        # Notice we strip leading and trailing quote-marks.
        value = value.strip("'\"")
        for pat, repl in self.like_escapes:
            value = value.replace(pat, repl)
        return value
    
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
                return self.false_expr
    
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
        return cannot_represent
    
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
        x.aggregate = True
        x.name = "min_%s" % x.name
        x.sql = "MIN(" + x.sql + ")"
        return x
    
    def func__builtin___max(self, x):
        x.aggregate = True
        x.name = "max_%s" % x.name
        x.sql = "MAX(" + x.sql + ")"
        return x
    
    def builtins_count(self, x):
        e = self.get_expr("COUNT(" + x.sql + ")", int)
        e.aggregate = True
        return e
    
    #                           Binary operations                         #
    
    # Resultant type for a binary operation between two types.
    result_type = {}
    
    def binary_op(self, op):
        op2, op1 = self.stack.pop(), self.stack.pop()
        if op1 is cannot_represent or op2 is cannot_represent:
            self.stack.append(cannot_represent)
            return
        
        agg = op1.aggregate or op2.aggregate
        
        try:
            newsql = op1.adapter.binary_op(op1, op, self.sql_bin_op[op], op2)
        except TypeError:
            self.stack.append(cannot_represent)
            return
        
        newpytype = self.result_type[(op1.pytype, op, op2.pytype)]
        
        # re-use op1
        op1.sql = newsql
        if newpytype != op1.pytype:
            op1.pytype = newpytype
            op1.dbtype = self.typeset.database_type(newpytype)
            op1.adapter = op1.dbtype.default_adapter(newpytype)
        if not op1.name.startswith("expr_"):
            op1.name = "expr_%s" % op1.name
        # Cascade aggregate flag outward
        op1.aggregate = agg
        self.stack.append(op1)

# Add visit_BINARY_* methods.
for k, v in codewalk.binary_repr.iteritems():
    setattr(SQLDecompiler, "visit_" + k,
            lambda self, op=v: self.binary_op(op))
del k, v

def _binary_operation_result_types():
    """Return a dict of (type(A), op, type(B)): type(op(A, B)) for known types."""
    results = {}
    
    knowntypes = [3, 3L, 3.0, 'a', u'b']
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
    
    ops = [(symbol, codewalk.binary_operators[name])
           for name, symbol in codewalk.binary_repr.iteritems()]
    
    for A in knowntypes:
        for B in knowntypes:
            for symbol, op in ops:
                try:
                    result = op(A, B)
                except TypeError:
                    pass
                else:
                    results[(type(A), symbol, type(B))] = type(result)
    
    return results
SQLDecompiler.result_type = _binary_operation_result_types()

