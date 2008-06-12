from types import FunctionType

from geniusql import logic


__all__ = ['Join', 'Query', 'Statement']



class Query(object):
    """A query with relation, attributes, and restriction expressions.
    
    relation: Either a single Table object, or a Join (of Tables).
    attributes:
        SELECT:
            If the relation is a single Table, this value must be a
            sequence of column names for that Table. If the relation
            is a Join, this must be a sequence of sequences of column
            names. That is:
                [(table1.col1.name, table1.col2.name, ...),
                 (table2.col1.name, ...),
                 ...]
            The order of sequences must match the order of tables given in
            the relation (and therefore the restriction args, if applicable).
            A final option is to pass a lambda (or Expression) which returns
            the attributes as a tuple or list; e.g.:
                lambda t1, t2: (t1.a, t1.b - now(), t1.c + t2.a)
            This allows access to binary operations and builtin functions.
        INSERT/UPDATE:
            If the relation is a single Table, this value must be a
            dict whose keys are column names for that Table, and whose
            values or either scalars or Expressions (or lambdas)
            representing the new values for those columns. For example:
                {'Name': 'Ali Bayan',
                 'Age': (lambda t: now() - t.Birthdate),
                 ...
                 }
            If the relation is a Join, this must be a list of such dicts,
            one per table, in the same order as the tables in the relation.
        DELETE:
            This should be a single empty list.
    restriction: an Expression (or lambda) to restrict the rows returned;
        if given, this will be used to construct a WHERE clause. The args
        must be in the same order as the tables in the relation.
    """
    
    def __init__(self, relation, attributes, restriction=None):
        self.relation = relation
        
        if isinstance(attributes, FunctionType):
            attributes = logic.Expression(attributes)
        self.attributes = attributes
        
        if restriction is None:
            restriction = logic.Expression(lambda *args: True)
        elif not isinstance(restriction, logic.Expression):
            restriction = logic.Expression(restriction)
        self.restriction = restriction
    
    def from_genexp(cls, expr):
        # this would allow consumers to write:
        #     select(([t1.a, t1.b + t2.a] for t1, t2 in relation if t1.a > 13))
        from geniusql import genexp
        dep = genexp.GenexpParser(expr)
        dep.verbose = True
        dep.walk()
        
        newq = cls(dep.relation, dep.attributes, dep.restriction)
        return newq
    from_genexp = classmethod(from_genexp)


class Join(object):
    """A join between two tables."""
    
    def __init__(self, table1, table2, leftbiased=None):
        self.table1 = table1
        self.table2 = table2
        self.leftbiased = leftbiased
        self.path = None
    
    def __str__(self):
        if self.leftbiased is None:
            op = "&"
        elif self.leftbiased is True:
            op = "<<"
        else:
            op = ">>"
        if isinstance(self.table1, Join):
            name1 = str(self.table1)
        elif isinstance(self.table1, type):
            name1 = self.table1.__name__
        else:
            name1 = repr(self.table1)
        
        if isinstance(self.table2, Join):
            name2 = str(self.table2)
        elif isinstance(self.table2, type):
            name2 = self.table2.__name__
        else:
            name2 = repr(self.table2)
        
        return "(%s %s %s)" % (name1, op, name2)
    __repr__ = __str__
    
    def __iter__(self):
        return JoinIterator(self)
    
    def __lshift__(self, other):
        return Join(self, other, leftbiased=True)
    __rrshift__ = __lshift__
    
    def __rshift__(self, other):
        return Join(self, other, leftbiased=False)
    __rlshift__ = __rshift__
    
    def __add__(self, other):
        return Join(self, other)
    __and__ = __add__
    
    def __radd__(self, other):
        return Join(other, self)
    __rand__ = __radd__
    
    def __eq__(self, other):
        return (self.table1 == other.table1 and
                self.table2 == other.table2 and
                self.leftbiased == other.leftbiased and
                self.path == other.path)


class JoinIterator(object):
    
    def __init__(self, join):
        if isinstance(join.table1, Join):
            t1 = list(join.table1)
        else:
            t1 = [join.table1]
        
        if isinstance(join.table2, Join):
            t2 = list(join.table2)
        else:
            t2 = [join.table2]
        
        self.tableiter = iter(t1 + t2)
    
    def __iter__(self):
        return self
    
    def next(self):
        return self.tableiter.next()


class Statement(object):
    """A relational statement, including query, order, limit, offset, and distinct.
    
    query: a Query instance, or a tuple of arguments to form a Query.
    
    order: if given, this will be used to construct an ORDER BY clause.
        If the relation is a single Table, this value may be a sequence
        of column names for the Table. If the relation is a Join, this must
        be an Expression (or lambda) which returns a tuple or list of
        attributes; the args must be in the same order as the tables in the
        relation.
    """
    
    def __init__(self, query, order=None, limit=None, offset=None, distinct=None):
        if not isinstance(query, Query):
            query = Query(*query)
        self.query = query
        
        self.order = order
        self.limit = limit
        self.offset = offset
        self.distinct = distinct

