"""Geniusql architectural classes.

The Column and Index classes model corresponding database objects, and are
intentionally simple. They should rarely contain any SQL or "smarts" of
any kind, besides the "qname", the quoted name, of the column or index.
At most, subclasses and consumers might put implementation-specific data
into them.

The IndexSet, Table, and Schema objects are all dict-like containers,
and therefore have a key for each value. Those keys should equate to things
at the consumer layer; for example, a Schema may possess a pair of the
form {'YoYo': Table('yoyo')} -- the key is the "friendly" name, but the
Table.name is a lowercase version of that, because that's what the database
uses in SQL to refer to that table.
"""

import threading

import geniusql
from geniusql import errors, typerefs
from geniusql import dbtypes
from geniusql import conns
from geniusql import deparse
from geniusql import isolation
from geniusql import logic
from geniusql import sqlwriters

__all__ = [
    'Index', 'IndexSet', 'Column', 'Table', 'View', 'Schema', 'Database', 'Dataset',
    ]

class Bijection(dict):
    """Bijective dict. Each key maps to only one value (and vice-versa)."""
    
    def key_for(self, obj):
        """For the given value, return its corresponding key."""
        for key, val in self.iteritems():
            if val is obj:
                return key
        raise ValueError("The given object could not be found: %r" % obj)
    
    def alias(self, oldname, newname):
        """Move the object at the given, existing key to the new key.
        
        Consumer code should call this method when user-supplied object
        names do not match the names in the database.
        """
        if oldname == newname:
            return
        
        obj = self[oldname]
        if newname in self:
            dict.__delitem__(self, newname)
        dict.__delitem__(self, oldname)
        dict.__setitem__(self, newname, obj)


class Index(object):
    """An index on a table column (or columns) in a database."""
    
    def __init__(self, name, qname, tablename, colname, unique=True):
        self.name = name
        self.qname = qname
        self.tablename = tablename
        self.colname = colname
        self.unique = unique
    
    def __repr__(self):
        return ("%s.%s(%r, %r, %r, %r, unique=%r)" %
                (self.__module__, self.__class__.__name__,
                 self.name, self.qname, self.tablename,
                 self.colname, self.unique))
    
    def __copy__(self):
        return self.__class__(self.name, self.qname, self.tablename,
                              self.colname, self.unique)
    copy = __copy__


class IndexSet(Bijection):
    
    def __new__(cls, table):
        return dict.__new__(cls)
    
    def __init__(self, table):
        dict.__init__(self)
        self.table = table
    
    def __getstate__(self):
        return self.items()
    
    def __setstate__(self, state):
        self.update(state)
    
    def __setitem__(self, key, index):
        """Create the specified index."""
        t = self.table
        if t.created:
            t.schema.db.execute_ddl('CREATE INDEX %s ON %s (%s);' %
                                    (index.qname, t.qname,
                                     t.schema.db.quote(index.colname)))
        dict.__setitem__(self, key, index)
    
    def __delitem__(self, key):
        """Drop the specified index."""
        t = self.table
        if t.created:
            t.schema.db.execute_ddl('DROP INDEX %s ON %s;' %
                                    (self[key].qname, t.qname))
        dict.__delitem__(self, key)


class Column(object):
    """A column in a table or view in a database.
    
    name: the SQL name for this table (unquoted).
    qname: the SQL name for this table (quoted).
    
    pytype: the Python type (the actual type object, not its name).
    dbtype: a DatabaseType instance.
    adapter: the object whose push and pull methods will convert Python
        values to and from SQL for values in this Column.
    
    default: default Python value for this column for new rows.
    key: True if this column is part of the table's primary key.
    
    autoincrement: if True, uses the database's built-in sequencing.
    sequence_name: for databases that use separate statements to create and
        drop sequences, this stores the name of the sequence.
    initial: if autoincrement, holds the initial value for the sequence.
    """
    
    def __init__(self, pytype, dbtype, default=None, key=False,
                 name=None, qname=None):
        self.pytype = pytype
        self.dbtype = dbtype
        self.adapter = None
        
        self.name = name
        self.qname = qname
        self.default = default
        self.key = key
        
        # If autoincrement, the initial value should be put in self.initial.
        self.autoincrement = False
        self.sequence_name = None
        self.initial = 1
    
    def __repr__(self):
        return ("%s.%s(%r, %r, default=%r, key=%r, name=%r, qname=%r)" %
                (self.__module__, self.__class__.__name__,
                 self.pytype, self.dbtype, self.default, self.key,
                 self.name, self.qname)
                )
    
    def __copy__(self):
        newcol = self.__class__(self.pytype, self.dbtype.copy(),
                                self.default, self.key,
                                self.name, self.qname)
        newcol.autoincrement = self.autoincrement
        newcol.initial = self.initial
        newcol.adapter = self.adapter
        return newcol
    copy = __copy__


class Table(Bijection):
    """A table in a database; a dict of Column objects.
    
    Values in this dict must be instances of Column (or a subclass of it).
    Keys should be consumer-friendly names for each Column value.
    
    name: the SQL name for this table (unquoted).
    qname: the SQL name for this table (quoted).
    schema: the schema for this table.
    created: whether or not this Table has a concrete implementation in the
        database. If False (the default), then changes to Table items can be
        made with impunity. If True, then appropriate ALTER TABLE commands
        are executed whenever a consumer adds or deletes items from the
        Table, or calls methods like 'rename'.
    indices: a dict-like IndexSet of Index objects.
    references: a dict of the form:
        {name: (near Column key, far Table key, far Column key)}.
    """
    
    implicit_pkey_indices = False
    
    def __new__(cls, name, qname, schema, created=False, description=None):
        return dict.__new__(cls)
    
    def __init__(self, name, qname, schema, created=False, description=None):
        dict.__init__(self)
        
        self.name = name
        self.qname = qname
        self.schema = schema
        self.created = created
        self.description = description
        
        self.indices = schema.indexsetclass(self)
        self.references = {}
    
    def __repr__(self):
        name = getattr(self, "name", "<unknown>")
        qname = getattr(self, "qname", "<unknown>")
        return ("%s.%s(%r, %r)" %
                (self.__module__, self.__class__.__name__, name, qname))
    
    def __copy__(self):
        # Don't set 'created' when copying!
        newtable = self.__class__(self.name, self.qname, self.schema)
        for key, c in self.iteritems():
            dict.__setitem__(newtable, key, c.copy())
        for key, i in self.indices.iteritems():
            dict.__setitem__(newtable.indices, key, i.copy())
        return newtable
    copy = __copy__
    
    def __getstate__(self):
        return (self.name, self.qname, self.items(), self.indices)
    
    def __setstate__(self, state):
        self.name, self.qname, items, self.indices = state
        self.update(items)
        self.indices.table = self
    
    def create(self):
        """Create this table in the database."""
        fields = []
        pk, pkindices = [], []
        for key, column in self.iteritems():
            if column.autoincrement:
                # Columns created using schema.column() can't make their own
                # sequence names because the tablename isn't available.
                # So we do it here if needed.
                if column.sequence_name is None:
                    column.sequence_name = self.schema.sequence_name(self.name, key)
                # This may or may not be a no-op, depending on the DB.
                self.schema.create_sequence(self, column)
            
            fields.append(self.schema.columnclause(column))
            if column.key:
                pk.append(column.qname)
                if self.implicit_pkey_indices:
                    pkindices.append(column.name)
        
        if pk:
            pk = ", PRIMARY KEY (%s)" % ", ".join(pk)
        else:
            pk = ""
        
        # Just to be sure...
        try:
            self.schema.db.execute_ddl('DROP TABLE %s;' % self.qname)
        except:
            pass
        self.schema.db.execute_ddl('CREATE TABLE %s (%s%s);' %
                                   (self.qname, ", ".join(fields), pk))
        # Set table.created to True, which should "turn on"
        # any future ALTER TABLE statements.
        self.created = True
        
        for index in self.indices.itervalues():
            if index.colname in pkindices:
                # Skip this index since the database has already implicitly
                # created an index for the primary key.
                continue
            self.schema.db.execute_ddl('CREATE INDEX %s ON %s (%s);' %
                                       (index.qname, self.qname,
                                        self.schema.db.quote(index.colname)))
    
    def drop(self):
        """Drop this table from the database."""
        self.schema.db.execute_ddl('DROP TABLE %s;' % self.qname)
        for col in self.itervalues():
            if col.autoincrement:
                self.schema.drop_sequence(col)
    
    # ------------------------ Column management ------------------------ #
    
    def _add_column(self, column):
        """Internal function to add the column to the database."""
        coldef = self.schema.columnclause(column)
        self.schema.db.execute("ALTER TABLE %s ADD COLUMN %s;" %
                               (self.qname, coldef))
    
    def __setitem__(self, key, column):
        if column.name is None:
            column.name = self.schema.column_name(self.name, key)
            column.qname = self.schema.db.quote(column.name)
        
        if not self.created:
            dict.__setitem__(self, key, column)
            return
        
        if key in self:
            del self[key]
        
        if column.autoincrement:
            # Columns created using schema.column() can't make their own
            # sequence names because the tablename isn't available.
            # So we do it here if needed.
            if column.sequence_name is None:
                column.sequence_name = self.schema.sequence_name(self.name, key)
            # This may or may not be a no-op, depending on the DB.
            self.schema.create_sequence(self, column)
        self._add_column(column)
        dict.__setitem__(self, key, column)
    
    def _drop_column(self, column):
        """Internal function to drop the column from the database."""
        self.schema.db.execute_ddl("ALTER TABLE %s DROP COLUMN %s;" %
                                   (self.qname, column.qname))
    
    def __delitem__(self, key):
        if key in self.indices:
            del self.indices[key]
        
        if not self.created:
            dict.__delitem__(self, key)
            return
        
        column = self[key]
        self._drop_column(column)
        if column.autoincrement:
            # This may or may not be a no-op, depending on the DB.
            self.schema.drop_sequence(column)
        dict.__delitem__(self, key)
    
    def _rename(self, oldcol, newcol):
        # Override this to do the actual rename at the DB level.
        self.schema.db.execute_ddl("ALTER TABLE %s RENAME COLUMN %s TO %s;" %
                                   (self.qname, oldcol.qname, newcol.qname))
    
    def rename(self, oldkey, newkey):
        """Rename a Column. This will change the table name in the database."""
        oldcol = self[oldkey]
        
        if not self.created:
            dict.__delitem__(self, oldkey)
            dict.__setitem__(self, newkey, oldcol)
            return
        
        oldname = oldcol.name
        newname = self.schema.column_name(self.name, newkey)
        
        if oldname != newname:
            newcol = oldcol.copy()
            newcol.name = newname
            newcol.qname = self.schema.db.quote(newname)
            self._rename(oldcol, newcol)
        
        # Use the superclass calls to avoid DROP COLUMN/ADD COLUMN.
        dict.__delitem__(self, oldkey)
        dict.__setitem__(self, newkey, newcol)
    
    def add_index(self, columnkey):
        """Add and return a new Index for the given column key.
        
        The new Index object will possess the same key as the column.
        The actual SQL name of the new Index will be determined by
        Schema.index_name.
        """
        name = self.schema.index_name(self, columnkey)
        i = Index(name, self.schema.db.quote(name), self.name,
                  self[columnkey].name)
        # This won't call CREATE INDEX if self.created is False.
        self.indices[columnkey] = i
        return i
    
    def set_primary(self):
        """Set the PRIMARY KEY for this Table, using its Column.key values.
        
        If self already possesses a primary key, this method will DROP it.
        This is intended to be used with install or repair scripts.
        """
        self.drop_primary()
        pk = [column.qname for column in self.itervalues() if column.key]
        if pk:
            self.schema.db.execute("ALTER TABLE %s ADD PRIMARY KEY (%s);" %
                                   (self.qname, ", ".join(pk)))
    
    def drop_primary(self):
        """Remove any PRIMARY KEY for this Table."""
        raise NotImplementedError
    
    # ---------------------------- OLTP/CRUD ---------------------------- #
    
    def id_clause(self, **kwargs):
        """Return an SQL expression for the identifiers of the given table."""
        ids = dict([(k, v) for k, v in kwargs.iteritems() if self[k].key])
        try:
            return logic.filter(**ids)
        except Exception, x:
            x.args += (kwargs, )
            raise
    
    def insert(self, **kwargs):
        """Insert a row and return it, including any new identifiers."""
        idkeys = []
        values = {}
        for key, col in self.iteritems():
            if col.autoincrement and kwargs.get(key) is None:
                # Skip this field, since we're using a sequencer
                idkeys.append(key)
                continue
            if key in kwargs:
                values[key] = kwargs[key]
        
        conn = self.schema.db.connections.get()
        self.schema.db.insert((self, values), conn)
        
        # Note that the 'kwargs' dict has already been copied simply
        # by being passed as kwargs. So modifying it in-place won't
        # mangle the caller's original dict.
        if idkeys:
            for k, v in self._grab_new_ids(idkeys, conn).iteritems():
                col = self[k]
                kwargs[k] = col.adapter.pull(v, col.dbtype)
        return kwargs
    
    def _grab_new_ids(self, idkeys, conn):
        # Override this to fetch and return new autoincrement values.
        raise NotImplementedError
    
    def save(self, **kwargs):
        """Update a row (or rows) using the given identifiers in kwargs.
        
        Any columns in the kwargs provided which are 'key' columns
        will be used to determine which rows to update. All matching
        rows will be updated using the other (non-key) columns.
        Any autoincrement columns will be skipped.
        
        Usually, kwarg values will be coerced (via column.adapter.push)
        to the proper SQL for you. But for any kwarg value that is a lambda
        or logic.Expression, the SQL will be deparsed from that value.
        For example, to do full-text searching in PostgreSQL using Tsearch2,
        you can write:
        
            table.save(ID=3, fti=lambda t: to_tsvector('default', t.title))
        
        which (assuming you have registered the to_tsvector function in
        logic.builtins) will result in the SQL:
        
            UPDATE table SET fti = to_tsvector('default', title) WHERE ID = 3
        """
        # Skip sequenced fields
        parms = dict([(k, v) for k, v in kwargs.iteritems()
                      if not self[k].autoincrement])
        if parms:
            w = self.id_clause(**kwargs)
            self.schema.db.save((self, parms, w))
    
    def save_all(self, data, restriction=None, **kwargs):
        """Update all rows (with 'data' dict) which match the given restriction.
        
        This differs from the 'save' method by allowing you to specify
        matching rows using any restriction, not just primary key identities.
        """
        if data:
            w = logic.combine(restriction, kwargs)
            self.schema.db.save((self, data, w))
    
    def delete(self, **kwargs):
        """Delete all rows which match the given identifier kwargs."""
        self.schema.db.delete((self, [], self.id_clause(**kwargs)))
    
    def delete_all(self, restriction=None, **kwargs):
        """Delete all rows which match the given restriction."""
        self.schema.db.delete((self, [], logic.combine(restriction, kwargs)))
    
    def select(self, restriction=None, **kwargs):
        """Return a single data dict matching the given restriction (or None)."""
        try:
            return self._select_lazy(restriction, **kwargs).next()
        except StopIteration:
            return None
    
    def select_all(self, restriction=None, order=None, limit=None, **kwargs):
        """Return a list of all data dicts matching the given restriction."""
        return list(self._select_lazy(restriction, order, limit, **kwargs))
    
    def _select_lazy(self, restriction=None, order=None, limit=None, **kwargs):
        """Yield data dicts matching the given restriction."""
        restriction = logic.combine(restriction, kwargs)
        
        attrs = self.keys()
        dataset = self.schema.db.select((self, attrs, restriction),
                                        order=order, limit=limit,
                                        strict=False)
        if dataset.statement.imperfect:
            if restriction is None:
                raise ValueError("Could not generate perfect SQL.")
            
            # Run a dummy object through our restriction before yielding.
            # Since the results are imperfect (a larger subset of the data),
            # we need to do our own limiting.
            seen = 0
            for row in dataset:
                row = dict(zip(attrs, row))
                if not restriction(_ImperfectDummy(**row)):
                    continue
                yield row
                seen += 1
                if seen >= limit:
                    return
        else:
            for row in dataset:
                yield dict(zip(attrs, row))
    
    
    # ------------------------------ Joins ------------------------------ #
    
    def __lshift__(self, other):
        return geniusql.Join(self, other, leftbiased=True)
    __rrshift__ = __lshift__
    
    def __rshift__(self, other):
        return geniusql.Join(self, other, leftbiased=False)
    __rlshift__ = __rshift__
    
    def __and__(self, other):
        return geniusql.Join(self, other)
    
    def __rand__(self, other):
        return geniusql.Join(other, self)


class View(Bijection):
    """A view in a database; a dict of Column objects for a query.
    
    Values in this dict must be instances of Column (or a subclass of it).
    Keys should be consumer-friendly names for each Column value.
    
    name: the SQL name for this view (unquoted).
    qname: the SQL name for this view (quoted).
    schema: the schema for this view.
    created: whether or not this View has a concrete implementation in the
        database. If False (the default), then changes to View items can be
        made with impunity. If True, then appropriate ALTER VIEW commands (or
        the equivalent DROP and re-CREATE commands) are executed whenever a
        consumer adds or deletes items from the View, or calls methods like
        'rename'.
    statement: a Statement instance. Setting this value automatically
        populates self.items with Column objects based on the statement's
        output.
    """
    
    def __new__(cls, name, qname, schema, created=False, description=None,
                statement=None):
        return dict.__new__(cls)
    
    def __init__(self, name, qname, schema, created=False, description=None,
                 statement=None):
        dict.__init__(self)
        
        self.name = name
        self.qname = qname
        self.schema = schema
        self.created = created
        self.description = description
        self.statement = statement
    
    def __repr__(self):
        name = getattr(self, "name", "<unknown>")
        qname = getattr(self, "qname", "<unknown>")
        return ("%s.%s(%r, %r)" %
                (self.__module__, self.__class__.__name__, name, qname))
    
    def __copy__(self):
        # Don't set 'created' when copying!
        newview = self.__class__(self.name, self.qname, self.schema,
                                 statement=self.statement)
        for key, c in self.iteritems():
            dict.__setitem__(newview, key, c.copy())
        return newview
    copy = __copy__
    
    def __getstate__(self):
        return (self.name, self.qname, self.items(), self.statement)
    
    def __setstate__(self, state):
        self.name, self.qname, items, self.statement = state
        self.update(items)
    
    def _get_statement(self):
        return self._statement
    def _set_statement(self, value):
        self._statement = value
        if value is None:
            return
        
        db = self.schema.db
        self.sqlstatement = db.selectwriter(db, self._statement).statement
        if self.sqlstatement.imperfect:
            raise ValueError("The given restriction could not safely be "
                             "translated to SQL.",
                             self._statement.query.restriction)
        
        # Make new Column objects for self, using the SELECT output names.
        dict.clear(self)
        for colkey, name, qname, col in self.sqlstatement.output:
            col.name = name
            col.qname = qname
            col.key = False
            col.autoincrement = False
            col.sequence_name = None
            col.initial = 1
            dict.__setitem__(self, colkey, col)
    statement = property(_get_statement, _set_statement,
        doc="The Statement instance for the source of this View.")
    
    def create(self):
        """Create this view in the database."""
        self.schema.db.execute_ddl('CREATE VIEW %s AS %s;' %
                                   (self.qname, self.sqlstatement.sql))
        
        # Set self.created to True, which should "turn on"
        # any future ALTER VIEW statements.
        self.created = True
    
    def drop(self):
        """Drop this view from the database."""
        self.schema.db.execute_ddl('DROP VIEW %s;' % self.qname)
    
    # ------------------------ Column management ------------------------ #
    
    def __setitem__(self, key, column):
        if column.name is None:
            column.name = self.schema.column_name(self.name, key)
            column.qname = self.schema.db.quote(column.name)
        
        dict.__setitem__(self, key, column)
        if self.created:
            # DROP and CREATE (self.create auto-drops)
            self.create()
    
    def __delitem__(self, key):
        dict.__delitem__(self, key)
        if self.created:
            # DROP and CREATE (self.create auto-drops)
            self.create()
    
    def rename(self, oldkey, newkey):
        """Rename a Column. This will change the table name in the database."""
        oldcol = self[oldkey]
        oldname = oldcol.name
        newname = self.schema.column_name(self.name, newkey)
        if oldname != newname:
            newcol = oldcol.copy()
            newcol.name = newname
            newcol.qname = self.schema.db.quote(newname)
            if self.created:
                # DROP and CREATE (self.create auto-drops)
                self.create()
        
        # Use the superclass calls to avoid further SQL.
        dict.__delitem__(self, oldkey)
        dict.__setitem__(self, newkey, newcol)
    
    # ---------------------------- OLTP/CRUD ---------------------------- #
    
    def select(self, restriction=None, **kwargs):
        """Return a single data dict matching the given restriction (or None)."""
        try:
            return self._select_lazy(restriction, **kwargs).next()
        except StopIteration:
            return None
    
    def select_all(self, restriction=None, order=None, limit=None, **kwargs):
        """Return a list of all data dicts matching the given restriction."""
        return list(self._select_lazy(restriction, order, limit, **kwargs))
    
    def _select_lazy(self, restriction=None, order=None, limit=None, **kwargs):
        """Yield data dicts matching the given restriction."""
        restriction = logic.combine(restriction, kwargs)
        
        attrs = self.keys()
        dataset = self.schema.db.select((self, attrs, restriction),
                                        order=order, limit=limit,
                                        strict=False)
        if dataset.statement.imperfect:
            if restriction is None:
                raise ValueError("Could not generate perfect SQL.")
            
            # Run a dummy object through our restriction before yielding.
            # Since the results are imperfect (a larger subset of the data),
            # we need to do our own limiting.
            seen = 0
            for row in dataset:
                row = dict(zip(attrs, row))
                if not restriction(_ImperfectDummy(**row)):
                    continue
                yield row
                seen += 1
                if seen >= limit:
                    return
        else:
            for row in dataset:
                yield dict(zip(attrs, row))
    
    
    # ------------------------------ Joins ------------------------------ #
    
    def __lshift__(self, other):
        return geniusql.Join(self, other, leftbiased=True)
    __rrshift__ = __lshift__
    
    def __rshift__(self, other):
        return geniusql.Join(self, other, leftbiased=False)
    __rlshift__ = __rshift__
    
    def __and__(self, other):
        return geniusql.Join(self, other)
    
    def __rand__(self, other):
        return geniusql.Join(other, self)


class _ImperfectDummy(object):
    """A dummy object for resolving imperfect queries."""
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)


class Schema(Bijection):
    """A dict for managing a set of tables.
    
    Values in this dict must be instances of Table. Keys should be
    consumer-friendly names for each Table value. For example, it's
    easiest to use all lowercase table names in MySQL; however, a
    geniusql consumer might want their code to use TitledNames to
    refer to each table.
    
    This is a subclass of Bijection, so each key must map to one
    and only one Table object (and vice-versa).
    
    When a consumer adds and deletes items from a Schema object,
    appropriate CREATE TABLE/DROP TABLE commands are executed.
    This means that a Table object to be added should have all
    of its columns populated before adding it to the Schema.
    """
    
    name = None
    qname = None
    
    tableclass = Table
    viewclass = View
    indexsetclass = IndexSet
    
    def __new__(cls, db, name=None):
        return dict.__new__(cls)
    
    def __init__(self, db, name=None):
        dict.__init__(self)
        
        self.db = db
        # Although __init__ should set this instance's "name" attribute,
        # allow subclasses to pull that information from other sources
        # if necessary.
        if name is not None:
            self.name = self.db.sql_name(name)
            self.qname = self.db.quote(name)
        self._discover_lock = threading.Lock()
    
    def __repr__(self):
        name = getattr(self, "name", "<unknown>")
        return "%s.%s(%r)" % (self.__module__, self.__class__.__name__, name)
    
    #                              Discovery                              #
    
    def _get_tables(self, conn=None):
        raise NotImplementedError
    
    def _get_table(self, tablename, conn=None):
        # Fallback behavior. This is slow and should be optimized by each DB.
        for t in self._get_tables(conn):
            if t.name == tablename:
                return t
        raise errors.MappingError("Table % not found." % tablename)
    
    def _get_columns(self, table, conn=None):
        raise NotImplementedError
    
    def _get_indices(self, table, conn=None):
        raise NotImplementedError
    
    def _discover_table(self, table, conn=None):
        """Populate the columns and indices of the given Table object."""
        for col in self._get_columns(table, conn):
            # Use the superclass call to avoid ALTER TABLE
            if col.name in table:
                dict.__delitem__(table, col.name)
            dict.__setitem__(table, col.name, col)
        
        if hasattr(table, "indices"):
            for idx in self._get_indices(table, conn):
                # Use the superclass call to avoid CREATE INDEX
                if idx.name in table.indices:
                    dict.__delitem__(table.indices, idx.name)
                dict.__setitem__(table.indices, idx.name, idx)
    
    def discover(self, tablename, conn=None):
        """Attach a new Table or View from the underlying DB to self (and return it).
        
        tablename: the database's name for the table. This may be different
        from the schema's key for the table.
        
        Table/View objects (and their Column and Index subobjects) will be
        added to self using keys that match the database's names.
        Consumers should call the "alias(oldname, newname)" method
        of Schema, Table, and IndexSet in order to re-map the
        discovered objects using consumer-friendly names.
        
        If no such table/view exists, a MappingError should be raised.
        """
        self._discover_lock.acquire()
        try:
            table = self._get_table(tablename)
            self._discover_table(table, conn)
            
            # Use the superclass calls to avoid CREATE TABLE
            if table.name in self:
                dict.__delitem__(self, table.name)
            dict.__setitem__(self, table.name, table)
            
            return table
        finally:
            self._discover_lock.release()
    
    def discover_all(self, ignore=None, conn=None):
        """(Re-)populate self (all table items) from the underlying DB.
        
        ignore: a list of table names to ignore (e.g., system tables) or None.
        
        Table objects (and their Column and Index subobjects) will be
        added to self using keys that match the database's names.
        Consumers should call the "alias(oldname, newname)" method
        of Schema, Table, and IndexSet in order to re-map the
        discovered objects using consumer-friendly names.
        
        This method is idempotent, but that doesn't mean cheap. Try not
        to call it very often (once at app startup is usually enough).
        If you already know the names of all the tables you want to
        discover, it's often faster to skip this method and just use
        the discover(tablename) method for each known name instead.
        """
        ignore = ignore or []
        
        self._discover_lock.acquire()
        try:
            for table in self._get_tables(conn):
                if table.name in ignore:
                    continue
                self._discover_table(table, conn)
                
                # Use the superclass calls to avoid CREATE TABLE
                if table.name in self:
                    dict.__delitem__(self, table.name)
                dict.__setitem__(self, table.name, table)
        finally:
            self._discover_lock.release()
    
    def column_name(self, tablename, columnkey):
        "Return the SQL column name for the given table name and column key."
        # If you want to use a map from your ORM's property names
        # to DB column names, override this method (that's why
        # the tablename must be included in the args).
        return self.db.sql_name(columnkey)
    
    def sequence_name(self, tablename, columnkey):
        "Return the SQL sequence name for the given table name and column key."
        # If you want to use a map from your ORM's property names
        # to DB sequence names, override this method (that's why
        # the tablename must be included in the args).
        return None
    
    def index_name(self, table, columnkey):
        "Return the SQL index name for the given table and column key."
        return self.db.sql_name("i_%s_%s" % (table.name, table[columnkey].name))
    
    def column(self, pytype=unicode, dbtype=None, default=None,
               key=False, autoincrement=False, hints=None):
        """Return a Column object from the given arguments."""
        col = Column(pytype, dbtype, default, key)
        col.autoincrement = autoincrement
        
        if col.dbtype is None:
            col.dbtype = self.db.typeset.database_type(pytype, hints or {})
        col.adapter = col.dbtype.default_adapter(pytype)
        
        return col
    
    prefix = ""
    
    def table_name(self, key):
        """Return the SQL table name for the given key."""
        # If you want to use a map from your ORM's class names
        # to DB table names, override this method.
        return self.db.sql_name(self.prefix + key)
    
    def table(self, name):
        """Create and return a Table object for the given name."""
        name = self.table_name(name)
        return self.tableclass(name, self.db.quote(name), self)
    
    def view(self, name, statement):
        """Create and return a View object for the given name and statement."""
        name = self.table_name(name)
        return self.viewclass(name, self.db.quote(name), schema=self,
                              statement=statement)
    
    def create_sequence(self, table, column):
        """Create a SEQUENCE for the given column."""
        # By default, this does nothing. Databases which require a separate
        # statement to create a sequence generator should override this.
        pass
    
    def drop_sequence(self, column):
        """Drop a SEQUENCE for the given column."""
        # By default, this does nothing. Databases which require a separate
        # statement to drop a sequence generator should override this.
        pass
    
    def columnclause(self, column):
        """Return a clause for the given column for CREATE or ALTER TABLE.
        
        This will be of the form "name type [DEFAULT x]".
        
        Most subclasses will override this to add autoincrement support.
        """
        ddltype = column.dbtype.ddl()
        
        default = column.default or ""
        if default:
            default = column.adapter.push(default, column.dbtype)
            default = " DEFAULT %s" % default
        
        return "%s %s%s" % (column.qname, ddltype, default)
    
    def __setitem__(self, key, table):
        if key in self:
            del self[key]
        table.create()
        dict.__setitem__(self, key, table)
    
    def __delitem__(self, key):
        table = self[key]
        table.drop()
        dict.__delitem__(self, key)
    
    def _rename(self, oldtable, newtable):
        # Override this to do the actual rename at the DB level.
        raise NotImplementedError
        newtable.created = True
    
    def rename(self, oldkey, newkey):
        """Rename a Table."""
        oldtable = self[oldkey]
        oldname = oldtable.name
        newname = self.db.table_name(newkey)
        
        if oldname != newname:
            newtable = oldtable.copy()
            newtable.schema = self.schema
            newtable.name = newname
            newtable.qname = self.db.quote(newname)
            self._rename(oldtable, newname)
        
        # Use the superclass calls to avoid DROP TABLE/CREATE TABLE.
        dict.__delitem__(self, oldkey)
        dict.__setitem__(self, newkey, newtable)
    
    def create(self):
        """Create this schema in the database."""
        self.clear()
    
    def drop(self):
        """Drop this schema (and any contained objects) from the database."""
        # Must shut down all connections to avoid
        # "being accessed by other users" error.
        self.db.connections.shutdown()
        
        seen = {}
        
        # DROP views first to avoid dependency issues.
        views = [(k, v) for k, v in self.items() if isinstance(v, View)]
        for key, view in views:
            # We might have multiple keys pointing at the same table.
            if view.name in seen:
                dict.__delitem__(self, key)
            else:
                del self[key]
                seen[view.name] = None
        
        # Now drop remaining objects (tables).
        for key, table in self.items():
            # We might have multiple keys pointing at the same table.
            if table.name in seen:
                dict.__delitem__(self, key)
            else:
                del self[key]
                seen[table.name] = None


class Database(object):
    
    __metaclass__ = geniusql._AttributeDocstrings
    
    name = None
    qname = None
    
    typeset = dbtypes.DatabaseTypeSet()
    deparser = deparse.SQLDeparser
    joinwrapper = sqlwriters.TableWrapper
    selectwriter = sqlwriters.SelectWriter
    updatewriter = sqlwriters.UpdateWriter
    deletewriter = sqlwriters.DeleteWriter
    insertwriter = sqlwriters.InsertWriter
    connectionmanager = conns.ConnectionManager
    schemaclass = Schema
    
    multischema = True
    multischema__doc = """If True, instances of this Database class
    may spawn multiple Schema instances. This is False, for example,
    when the underlying engine binds connections to individual files.
    In most applications (that use a single schema) this presents no
    problems; applications that need to handle more than one schema
    at a time should inspect this value to determine whether they
    need a separate Database instance per Schema instance.
    """
    
    pks_must_be_indexed = True
    pks_must_be_indexed__doc = """If True, the underlying database
    implements primary keys by creating an index. Geniusql allows
    you to define pk's without indexes, but not all databases do.
    """
    
    ordered_views = True
    ordered_views__doc = """If True, the underlying database allows
    VIEWs to contain an ORDER BY clause. If False, ordering will
    have to be provided when selecting from the view rather than
    inside the view itself."""
    
    def __init__(self, **kwargs):
        # Although __init__ should set this instance's "name" attribute,
        # allow subclasses to pull that information from other kwargs
        # or other sources if necessary.
        self.name = kwargs.get('name', None)
        if self.name:
            self.qname = self.quote(self.name)
        
        self.connections = self.connectionmanager(self)
        
        # Override attributes on self and children using kwargs.
        children = []
        for k, v in kwargs.iteritems():
            if "." in k:
                # Defer subkeys in case the child is replaced wholesale
                children.append((k, v))
            else:
                setattr(self, k, v)
        
        for k, v in children:
            namespace, name = k.split(".", 1)
            childobj = getattr(self, namespace)
            setattr(childobj, name, v)
    
    def version(self):
        """Return a string containing version info for this database."""
        raise NotImplementedError
    
    def log(self, msg):
        pass
    
    def schema(self, name=None):
        return self.schemaclass(self, name)
    
    def create(self):
        """Create this database."""
        self.execute_ddl("CREATE DATABASE %s;" % self.qname)
    
    def drop(self):
        """Drop this database."""
        # Must shut down all connections to avoid
        # "being accessed by other users" error.
        self.connections.shutdown()
        self.execute_ddl("DROP DATABASE %s;" % self.qname)
    
    #                              Discovery                              #
    
    def _get_dbinfo(self, conn=None):
        return {}
    
    def discover_dbinfo(self, conn=None):
        """Set attributes on self with actual DB metadata, where possible."""
        for k, v in self._get_dbinfo(conn).iteritems():
            setattr(self, k, v)
    
    def _get_schemas(self, conn=None):
        """Return a list of schema names."""
        raise NotImplementedError
    
    def discover_schemas(self, conn=None):
        """Return a list of Schema objects."""
        if self.multischema:
            return [self.schema(name) for name in self._get_schemas(conn)]
        else:
            return self.schema()
    
    #                               Naming                               #
    
    sql_name_max_length = 64
    sql_name_caseless = False
    
    def quote(self, name):
        """Return name, quoted for use in an SQL statement."""
        # This base class doesn't use "quote",
        # but most subclasses will.
        return name
    
    def sql_name(self, key):
        """Return the native SQL version of key (unquoted)."""
        if self.sql_name_caseless:
            key = key.lower()
        
        maxlen = self.sql_name_max_length
        if maxlen and len(key) > maxlen:
            errors.warn("The name '%s' is longer than the maximum of "
                        "%s characters." % (key, maxlen))
            key = key[:maxlen]
        
        return key
    
    def is_timeout_error(self, exc):
        """If the given exception instance is a lock timeout, return True.
        
        This should return True for errors which arise from locking
        timeouts; for example, if the database prevents 'dirty reads'
        by raising an error.
        """
        # You should definitely override this for your database.
        return False
    
    def is_connection_error(self, exc):
        """If the given exception instance is a connection error, return True.
        
        This should return True for errors which arise from broken connections;
        for example, if the database server has dropped the connection socket,
        or is unreachable.
        """
        # You should definitely override this for your database.
        return False
    
    def execute(self, sql, conn=None):
        """Return a native response for the given SQL."""
        if isinstance(sql, unicode):
            sql = sql.encode(self.typeset.encoding)
        self.log(sql)
        
        if conn is None:
            conn = self.connections.get()
        
        try:
            return conn.query(sql)
        except Exception, x:
            if self.is_connection_error(x):
                self.connections.reset(conn)
                return conn.query(sql)
            raise
    
    def execute_ddl(self, sql, conn=None):
        """Return a native response for the given DDL statement.
        
        In general, DDL statements should lock out other statements
        (especially those isolated in other transactions). Use this
        method to perform a locked DDL statement.
        """
        self.connections.lock("Transaction denied due to DDL: %r" % sql)
        try:
            if conn is None:
                # Important: use _factory(), not get(), to avoid the lock
                conn = self.connections._factory()
            self.execute(sql, conn)
        finally:
            self.connections.unlock()
    
    def fetch(self, sql, conn=None):
        """Return (rowdata, (colname, coltype)) for the given sql.
        
        sql should be a SQL string.
        
        rowdata will be an iterable of iterables containing the result values.
        columns will be an iterable of (column name, data type) pairs.
        
        This base class uses _sqlite syntax.
        """
        res = self.execute(sql, conn)
        return res.row_list, res.col_defs
    
    def select(self, query, order=None, limit=None, offset=None,
               distinct=False, strict=True):
        """Return a Dataset of matching data, coerced to Python types.
        
        strict: if True (the default), a ValueError is raised whenever
            the query.restriction cannot be perfectly translated to SQL.
            IMPORTANT: if 'strict' is False, the returned Dataset may
            contain rows that do not match the given query restriction!
            Therefore, the caller is responsible for checking the boolean
            Dataset.statement.imperfect flag; if True, each returned row
            must be verified, typically by forming complete objects from
            each returned row and passing them into the query restriction
            (as positional arguments).
        """
        if not isinstance(query, geniusql.Query):
            query = geniusql.Query(*query)
        
        statement = geniusql.Statement(query, order=order, limit=limit,
                                       offset=offset, distinct=distinct)
        sqlstatement = self.selectwriter(self, statement).statement
        if sqlstatement.imperfect:
            if strict:
                raise ValueError("The given restriction could not safely "
                                 "be translated to SQL.",
                                 statement.query.restriction)
            elif limit or offset:
                raise ValueError("The given restriction could not safely "
                                 "be translated to SQL. Imperfect SQL is "
                                 "not yet supported with limit or offset.",
                                 statement.query.restriction, limit, offset)
        
        data, _ = self.fetch(sqlstatement.sql)
        d = Dataset(sqlstatement, data)
        return d
    
    def save(self, query):
        """Execute the given query as an UPDATE statement."""
        if not isinstance(query, geniusql.Query):
            query = geniusql.Query(*query)
        
        sel = self.updatewriter(self, query).statement
        if sel.imperfect:
            raise ValueError("The given restriction could not safely be "
                             "translated to SQL.", query.restriction)
        self.execute(sel.sql)
    
    def delete(self, query):
        """Execute the given query as a DELETE statement."""
        if not isinstance(query, geniusql.Query):
            query = geniusql.Query(*query)
        
        sel = self.deletewriter(self, query).statement
        if sel.imperfect:
            raise ValueError("The given restriction could not safely be "
                             "translated to SQL.", query.restriction)
        self.execute(sel.sql)
    
    def insert(self, query, conn=None):
        """Execute the given query as an INSERT statement."""
        if not isinstance(query, geniusql.Query):
            query = geniusql.Query(*query)
        
        sel = self.insertwriter(self, query).statement
        self.execute(sel.sql, conn)
    
    def insert_into(self, name, query, limit=None, distinct=False):
        """INSERT matching data INTO a new table and return the Table.
        
        The 'name' argument will be used to name the new table in the
        database. The new table will be returned, and will also be added
        to the schema; the key will be the provided name. If you want to
        use a different key for this table, call schema.alias(name, newkey)
        after this method.
        """
        if not isinstance(query, geniusql.Query):
            query = geniusql.Query(*query)
        
        relation = query.relation
        if isinstance(relation, geniusql.Join):
            if isinstance(relation.table1, geniusql.Join):
                schema = relation.table2.schema
            else:
                schema = relation.table1.schema
        elif isinstance(relation, Schema):
            # This is how we say we want to SELECT scalars (no FROM clause)
            schema = relation
        else:
            schema = relation.schema
        
        statement = geniusql.Statement(query, limit=limit, distinct=distinct)
        sqlstatement = self.selectwriter(self, statement).statement
        newtable = sqlstatement.result_table(schema, name)
        
        selsql = sqlstatement.sql
        if sqlstatement.imperfect:
            if limit:
                raise ValueError("The given restriction could not safely "
                                 "be translated to SQL. Imperfect SQL is "
                                 "not yet supported with limit.",
                                 statement.query.restriction, limit)
            else:
                errors.warn("The requested INSERT INTO could not produce perfect "
                            "SQL. The creation of the new table could take a "
                            "long time, since it must fetch each row and INSERT "
                            "it into the new table manually. %r" % selsql)
            
            # CREATE TABLE
            newtable.schema[name] = newtable
            # SELECT ALL
            data, _ = self.fetch(selsql)
            
            output_keys = [names[0] for names in sqlstatement.output]
            for row in Dataset(sqlstatement, data):
                row = dict(zip(output_keys, row))
                # Run a dummy object through our restriction before inserting.
                if not query.restriction(_ImperfectDummy(**row)):
                    continue
                # INSERT INTO
                newtable.insert(**row)
        else:
            # CREATE TABLE
            newtable.schema[name] = newtable
            qnames = [names[2] for names in sqlstatement.output]
            sql = ("INSERT INTO %s (%s) %s" %
                   (newtable.qname, ", ".join(qnames), selsql))
            self.execute(sql)
        
        return newtable



# ------------------------------- Datasets ------------------------------- #


class Dataset(object):
    """A populated relation; the result of a SELECT.
    
    IMPORTANT: This is designed to be used with layers built on top of
    Geniusql that wish to do their own objectification of the returned
    rows. The iterator skips checking the 'imperfect' flag on the
    statement, under the assumption that the caller will do so itself.
    """
    
    def __init__(self, statement, data):
        self.statement = statement
        self.data = data
        # pre-fetch cols and cache in an optimal format.
        self.cols = [coldata[3] for coldata in statement.output]
    
    def __iter__(self):
        """Return an iterator over self."""
        return DatasetIterator(self)
    
    def scalar(self, col=0):
        """Return the Nth value (0-based) of the first row of these results."""
        for row in self:
            return row[col]


class DatasetIterator(object):
    """An iterator for Dataset objects."""
    
    def __init__(self, dataset):
        self.dataset = dataset
        self.dataiter = iter(dataset.data)
    
    def __iter__(self):
        """Return an iterator over self."""
        return self
    
    def next(self):
        """Return the next row in the sequence (without checking imperfect!).
        
        This is designed to be used with layers built on top of Geniusql
        that wish to do their own objectification of the returned rows.
        This method skips checking the 'imperfect' flag on the statement,
        under the assumption that the caller will do so itself.
        """
        raw_row = self.dataiter.next()
        return [col.adapter.pull(val, col.dbtype) for val, col
                in zip(raw_row, self.dataset.cols)]

