from types import FunctionType

import geniusql
from geniusql import errors, Join, logic


__all__ = ['TableWrapper', 'SQLStatement', 'SQLWriter',
           'SELECT', 'SelectWriter', 'UPDATE', 'UpdateWriter',
           'DELETE', 'DeleteWriter', 'INSERT', 'InsertWriter',
           ]


class TableWrapper(object):
    """Table class wrapper, for use in parsing joins (allowing aliases)."""
    
    def __init__(self, table):
        self.table = table
        self.qname = table.qname
        # *quoted* alias
        self.alias = ""


# ------------------ Writer and statement base classes ------------------ #


class SQLStatement(object):
    input = None
    fromclause = ""
    whereclause = ""
    imperfect = False
    sql = ""


class SQLWriter(object):
    """Database delegate (base class) for writing SQL from a set of objects.
    
    db: a Database instance.
    query: a Query instance.
    """
    
    statement_class = SQLStatement
    
    def __init__(self, db, query):
        self.db = db
        self.query = query
        
        self.seen = {}
        self.aliascount = 0
        
        self.statement = self.statement_class()
        
        self.process_relation()
        self.process_where()
        self.unpack_attributes()
    
    def process_relation(self):
        # Create a new join tree where each table is wrapped.
        # Then we can tag the wrappers with "alias" metadata with impunity.
        relation = self.query.relation
        if isinstance(relation, Join):
            self.tables = self.wrap(relation)
            self.statement.fromclause = self.joinclause(self.tables)
        elif isinstance(relation, geniusql.Schema):
            # This is how we say we want to SELECT scalars (no FROM clause)
            self.tables = []
            self.statement.fromclause = ""
        else:
            self.tables = [self.db.joinwrapper(relation)]
            self.statement.fromclause = relation.qname
        self.tablenames = [(t.alias or t.qname, t.table) for t in self.tables]
    
    def process_where(self):
        """Return an SQL WHERE clause, and an 'imperfect' flag."""
        dep = self.db.deparser(self.tablenames, self.query.restriction,
                               self.db.typeset)
##        dep.verbose = True
        self.statement.whereclause = dep.code()
        if dep.imperfect:
            self.statement.imperfect = True
    
    def wrap(self, join):
        """Return the given Join with each node wrapped."""
        t1, t2 = join.table1, join.table2
        
        if isinstance(t1, Join):
            wt1 = self.wrap(t1)
        else:
            wt1 = self.db.joinwrapper(t1)
            if t1.name in self.seen:
                self.aliascount += 1
                alias = "t%d" % self.aliascount
                wt1.alias = self.db.quote(t1.schema.table_name(alias))
            else:
                self.seen[t1.name] = None
        
        if isinstance(t2, Join):
            wt2 = self.wrap(t2)
        else:
            wt2 = self.db.joinwrapper(t2)
            if t2.name in self.seen:
                self.aliascount += 1
                alias = "t%d" % self.aliascount
                wt2.alias = self.db.quote(t2.schema.table_name(alias))
            else:
                self.seen[t2.name] = None
        
        newjoin = Join(wt1, wt2, join.leftbiased)
        # if the original Join had a custom reference path,
        # copy it to the new Join instance
        newjoin.path = join.path
        return newjoin
    
    def joinname(self, tablewrapper):
        """Quoted table name for use in JOIN clause."""
        if tablewrapper.alias:
            return "%s AS %s" % (tablewrapper.qname, tablewrapper.alias)
        else:
            return tablewrapper.qname
    
    def onclause(self, A, B, path=None):
        """Return 'A.x = B.y' for tables A and B (or None).
        
        The returned value (if not None) is suitable for use in the 'ON'
        portion of an SQL JOIN clause.
        """
        if path is None:
            path = B.table.schema.key_for(B.table)
        
        if isinstance(path, logic.Expression):
            dep = self.db.deparser(self.tablenames, path, self.db.typeset)
##            dep.verbose = True
            dep.walk()
            atom = dep.stack[0]
            if dep.imperfect:
                self.statement.imperfect = True
            return atom.sql
        else:
            ref = A.table.references.get(path, None)
            if ref:
                nearkey, _, farkey = ref
                near = '%s.%s' % (A.alias or A.qname, A.table[nearkey].qname)
                far = '%s.%s' % (B.alias or B.qname, B.table[farkey].qname)
                return "%s = %s" % (near, far)
    
    def joinclause(self, join):
        """Return an SQL FROM clause for the given (wrapped) Join."""
        t1, t2 = join.table1, join.table2
        if isinstance(t1, Join):
            name1 = self.joinclause(t1)
            tlist1 = iter(t1)
        else:
            # t1 is a Table class wrapper.
            name1 = self.joinname(t1)
            tlist1 = [t1]
        
        if isinstance(t2, Join):
            name2 = self.joinclause(t2)
            tlist2 = iter(t2)
        else:
            # t2 is a Table class wrapper.
            name2 = self.joinname(t2)
            tlist2 = [t2]
        
        j = {None: "INNER", True: "LEFT", False: "RIGHT"}[join.leftbiased]
        
        # Find a reference between the two halves.
        for A in tlist1:
            for B in tlist2:
                on = self.onclause(A, B, join.path)
                if on:
                    return "(%s %s JOIN %s ON %s)" % (name1, j, name2, on)
                
                on = self.onclause(B, A, join.path)
                if on:
                    return "(%s %s JOIN %s ON %s)" % (name1, j, name2, on)
        
        raise errors.ReferenceError("No reference found between %s and %s."
                                    % (name1, name2))
    
    def unpack_attributes(self):
        raise NotImplementedError



# -------------------------- SELECT statements -------------------------- #


class SELECT(SQLStatement):
    """A SELECT SQL statement. Usually produced by an SQLWriter.
    
    input: a list of SQL expressions, one for each column in the
        SELECT clause. These will include any "expr AS name" alias.
    output: a list of tuples of the form:
        (column key,
         SQL name (or alias),
         quoted SQL name (or alias),
         source Column object)
        One per output column.
    """
    output = None
    groupby = None
    orderby = None
    distinct = False
    limit = None
    offset = None
    into = ""
    
    def __init__(self):
        self.input = []
        self.output = []
        self.groupby = []
    
    def _get_sql(self):
        """Return an SQL SELECT statement."""
        atoms = ["SELECT"]
        append = atoms.append
        if self.distinct:
            append('DISTINCT')
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
        if self.limit is not None:
            append("LIMIT %d" % self.limit)
        if self.offset is not None:
            append("OFFSET %d" % self.offset)
        return " ".join(atoms)
    sql = property(_get_sql, doc="The SQL string for this SELECT statement.")
    
    def result_table(self, schema, name):
        """Return a new Table object for the result of this SELECT.
        
        This is too expensive to do when you don't need it, so it's
        a separate function here. Try not to call it more than once
        for a given SelectWriter instance.
        """
        newtable = schema.table(name)
        for colkey, name, qname, col in self.output:
            newcol = col.copy()
            newcol.name = name
            newcol.qname = qname
            newcol.key = False
            newcol.autoincrement = False
            newcol.sequence_name = None
            newcol.initial = 1
            newtable[colkey] = newcol
        return newtable


class SelectWriter(SQLWriter):
    """Database delegate for writing SELECT statements.
    
    db: a Database instance.
    statement: pass in an instance of geniusql.Statement (which is DB-agnostic)
        and it will be transformed into a DB-specific SQLStatement.
    """
    
    statement_class = SELECT
    
    def __init__(self, db, statement, into=""):
        self.output_cols = {}
        
        SQLWriter.__init__(self, db, statement.query)
        
        # Yes, we're trading one statement object for another here,
        # but the former is a DB-agnostic Statement and the latter
        # is a DB-specific SQLStatement.
        self.statement.distinct = statement.distinct
        self.statement.limit = statement.limit
        self.statement.offset = statement.offset
        self.statement.into = into
        
        order = statement.order
        if order is None:
            self.statement.orderby = None
        elif isinstance(order, FunctionType):
            order = logic.Expression(order)
            self.deparse_order(order)
        elif isinstance(order, logic.Expression):
            self.deparse_order(order)
        elif isinstance(order, basestring):
            raise TypeError("The 'order' value %r is not one of the allowed "
                            "types (list, lambda, None, or Expression)." %
                            order)
        else:
            if isinstance(statement.query.relation, Join):
                raise ValueError("order must be an Expression when "
                                 "selecting from multiple tables.")
            else:
                # 'relation' is a single Table object.
                ob = []
                for key in order:
                    # Handle embedded "ASC"/"DESC" atoms
                    atoms = key.rsplit(" ", 1)
                    key = statement.query.relation[atoms.pop(0)].qname
                    if atoms:
                        key += " " + atoms[0]
                    ob.append(key)
                self.statement.orderby = ob
    
    def unpack_attributes(self):
        if isinstance(self.query.attributes, logic.Expression):
            self.deparse_attributes()
            return
        
        if isinstance(self.query.relation, Join):
            for t, attrs in zip(self.tables, self.query.attributes):
                # Add columns from the given table to our result table.
                alias = t.alias or t.qname
                table = t.table
                for colkey in attrs:
                    col = table[colkey]
                    if colkey in self.output_cols:
                        # Get the key for the table.
                        colkey = '%s_%s' % (table.schema.key_for(table), colkey)
                        colname = '%s_%s' % (table.name, col.name)
                        colqname = self.db.quote(colname)
                        selname = '%s.%s AS %s' % (alias, col.qname, colqname)
                    else:
                        colname = col.name
                        colqname = col.qname
                        selname = '%s.%s' % (alias, colqname)
                    self.statement.input.append(selname)
                    self.statement.output.append((colkey, colname, colqname, col))
                    self.output_cols[colkey] = col
        else:
            # 'relation' is a single Table object.
            for colkey in self.query.attributes:
                col = self.query.relation[colkey]
                self.statement.input.append(col.qname)
                self.statement.output.append((colkey, col.name, col.qname, col))
                self.output_cols[colkey] = col
    
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
            
            qname = self.db.quote(atom.name)
            self.statement.input.append('%s AS %s' % (atom.sql, qname))
            self.statement.output.append((atom.name, atom.name, qname, atom))
            if not atom.aggregate:
                self.statement.groupby.append(atom.sql)
            
            self.output_cols[atom.name] = atom
    
    def deparse_order(self, order):
        dep = self.db.deparser(self.tablenames, order, self.db.typeset)
##        dep.verbose = True
        self.statement.orderby = [atom.sql for atom in dep.field_list()]



# -------------------------- UPDATE statements -------------------------- #


class UPDATE(SQLStatement):
    """An UPDATE SQL statement. Usually produced by an UpdateWriter.
    
    input: a dict of SQL expressions, one for each column in the
        SET clause. Keys will be quoted column names and values
        will be the new values (in SQL syntax) for the columns.
    """
    
    def __init__(self):
        self.input = {}
    
    def _get_sql(self):
        """Return an SQL UPDATE statement."""
        atoms = ["UPDATE", self.fromclause, "SET"]
        atoms.append(', '.join(["%s = %s" % (k, v)
                                for k, v in self.input.iteritems()]))
        if self.whereclause:
            atoms.append("WHERE")
            atoms.append(self.whereclause)
        return " ".join(atoms)
    sql = property(_get_sql, doc="The SQL string for this UPDATE statement.")


class UpdateWriter(SQLWriter):
    """Database delegate for writing UPDATE statements.
    
    db: a Database instance.
    query: a Query instance.
    """
    
    statement_class = UPDATE
    
    def unpack_attributes(self):
        if isinstance(self.query.relation, Join):
            for t, attrs in zip(self.tables, self.query.attributes):
                # Add columns from the given table to our result table.
                alias, table = t
                for colkey, val in attrs.iteritems():
                    col = table[colkey]
                    fullkey = '%s.%s' % (alias, col.qname)
                    if isinstance(val, FunctionType):
                        val = logic.Expression(val)
                        val = self.deparse_attribute(val)
                    elif isinstance(val, logic.Expression):
                        val = self.deparse_attribute(val)
                    else:
                        val = col.adapter.push(val, col.dbtype)
                    self.statement.input[fullkey] = val
        else:
            # 'relation' is a single Table object.
            for colkey, val in self.query.attributes.iteritems():
                col = self.query.relation[colkey]
                if isinstance(val, FunctionType):
                    val = logic.Expression(val)
                    val = self.deparse_attribute(val)
                elif isinstance(val, logic.Expression):
                    val = self.deparse_attribute(val)
                else:
                    val = col.adapter.push(val, col.dbtype)
                self.statement.input[col.qname] = val
    
    def deparse_attribute(self, value):
        dep = self.db.deparser(self.tablenames, value, self.db.typeset)
##        dep.verbose = True
        code = dep.code()
        if dep.imperfect:
            raise ValueError("The given attribute expression could not be "
                             "safely translated to SQL.", value)
        return code



# -------------------------- DELETE statements -------------------------- #


class DELETE(SQLStatement):
    """A DELETE SQL statement. Usually produced by a DeleteWriter.
    
    input: a list of SQL expressions, one for each column in the DELETE clause.
    """
    
    def __init__(self):
        self.input = []
    
    def _get_sql(self):
        """Return an SQL DELETE statement."""
        atoms = ["DELETE"]
        append = atoms.append
        append(', '.join(self.input))
        if self.fromclause:
            append("FROM")
            append(self.fromclause)
            if self.whereclause:
                append("WHERE")
                append(self.whereclause)
        return " ".join(atoms)
    sql = property(_get_sql, doc="The SQL string for this DELETE statement.")


class DeleteWriter(SQLWriter):
    """Database delegate for writing DELETE statements.
    
    db: a Database instance.
    query: a Query instance.
    
    For now, query.attributes should be empty, since many databases do not
    allow any attribute list in DELETE statements.
    """
    
    statement_class = DELETE
    
    def unpack_attributes(self):
        pass



# -------------------------- INSERT statements -------------------------- #


class INSERT(SQLStatement):
    """An INSERT SQL statement. Usually produced by an InsertWriter.
    
    input: a dict of SQL expressions, one for each column in the
        SET clause. Keys will be quoted column names and values
        will be the new values (in SQL syntax) for the columns.
    """
    
    def __init__(self):
        self.input = {}
    
    def _get_sql(self):
        """Return an SQL INSERT statement."""
        keys, values = zip(*self.input.items())
        atoms = ["INSERT INTO", self.fromclause,
                 '(%s)' % ', '.join(keys), "VALUES",
                 '(%s)' % ', '.join(values)]
        return " ".join(atoms)
    sql = property(_get_sql, doc="The SQL string for this INSERT statement.")


class InsertWriter(SQLWriter):
    """Database delegate for writing INSERT statements.
    
    db: a Database instance.
    query: a Query instance.
    """
    
    statement_class = INSERT
    
    def unpack_attributes(self):
        if isinstance(self.query.relation, Join):
            for t, attrs in zip(self.tables, self.query.attributes):
                # Add columns from the given table to our result table.
                alias, table = t
                for colkey, val in attrs.iteritems():
                    col = table[colkey]
                    fullkey = '%s.%s' % (alias, col.qname)
                    if isinstance(val, FunctionType):
                        val = logic.Expression(val)
                        val = self.deparse_attribute(val)
                    elif isinstance(val, logic.Expression):
                        val = self.deparse_attribute(val)
                    else:
                        val = col.adapter.push(val, col.dbtype)
                    self.statement.input[fullkey] = val
        else:
            # 'relation' is a single Table object.
            for colkey, val in self.query.attributes.iteritems():
                col = self.query.relation[colkey]
                if isinstance(val, FunctionType):
                    val = logic.Expression(val)
                    val = self.deparse_attribute(val)
                elif isinstance(val, logic.Expression):
                    val = self.deparse_attribute(val)
                else:
                    val = col.adapter.push(val, col.dbtype)
                self.statement.input[col.qname] = val
    
    def deparse_attribute(self, value):
        dep = self.db.deparser(self.tablenames, value, self.db.typeset)
##        dep.verbose = True
        code = dep.code()
        if dep.imperfect:
            raise ValueError("The given attribute expression could not be "
                             "safely translated to SQL.", value)
        return code
