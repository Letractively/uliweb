# Use _psycopg directly to avoid overhead.
try:
    # If possible, you should copy the _psycopg.pyd file into a top level
    # so this SM can avoid importing the entire package.
    import _psycopg
except ImportError:
    from psycopg2 import _psycopg

from geniusql import conns, errors
from geniusql.providers import postgres


class PsycoPgConnectionManager(conns.ConnectionManager):
    
    default_isolation = "READ COMMITTED"
    
    def _get_conn(self, master=False):
        if master:
            # Commit any pending transaction in the current thread.
            if self.in_transaction():
                self.commit()
            
            # Must shut down all connections to avoid
            # "being accessed by other users" error.
            self.shutdown()
            
            connstr = ""
            for atom in self.Connect.split(" "):
                k, v = atom.split("=", 1)
                if k == 'dbname':
                    v = 'template1'
                connstr += "%s=%s " % (k, v)
        else:
            connstr = self.Connect
        
        try:
            c = _psycopg.connect(connstr)
            # Allow statements like CREATE DATABASE to run outside a transaction.
            c.set_isolation_level(0)
            if self.initial_sql:
                cursor.execute(self.initial_sql)
            return c
        except _psycopg.DatabaseError, x:
            if x.args[0].startswith('could not connect'):
                raise errors.OutOfConnectionsError(*x.args)
            raise
    
    def _del_conn(self, conn):
        conn.close()


class PsycoPgSchema(postgres.PgSchema):
    
    def _get_dbinfo(self, conn=None):
        dbinfo = {}
        try:
            data, _ = self.db.fetch("SELECT pg_encoding_to_char(encoding) "
                                    "FROM pg_database;", conn=conn)
            dbinfo['encoding'] = data[0][0]
        except _psycopg.DatabaseError, x:
            if "does not exist" not in x.args[0]:
                raise
        return dbinfo


class PsycoPgDatabase(postgres.PgDatabase):
    
    connectionmanager = PsycoPgConnectionManager
    schemaclass = PsycoPgSchema
    
    def version(self):
        c = self.connections._get_conn(master=True)
        data, _ = self.fetch("SELECT version();", c)
        v, = data[0]
        c.close()
        return "%s\npsycopg version: %s" % (v, _psycopg.__version__)
    
    def is_connection_error(self, exc):
        """If the given exception instance is a connection error, return True.
        
        This should return True for errors which arise from broken connections;
        for example, if the database server has dropped the connection socket,
        or is unreachable.
        """
        if isinstance(exc, _psycopg.OperationalError):
            # OperationalError: connection not open
            msg = exc.args[0]
            return msg.startswith('connection not open')
        return False
    
    def execute(self, sql, conn=None):
        """Return a native response for the given SQL."""
        if conn is None:
            conn = self.connections.get()
        if isinstance(sql, unicode):
            sql = sql.encode(self.encoding)
        self.log(sql)
        
        cursor = conn.cursor()
        try:
            try:
                cursor.execute(sql)
            except Exception, x:
                if self.is_connection_error(x):
                    cursor.close()
                    self.connections.reset(conn)
                    cursor = conn.cursor()
                    return cursor.execute(sql)
                raise
        finally:
            cursor.close()
    
    def fetch(self, sql, conn=None):
        """Return rowdata, columns(name, type) for the given sql.
        
        sql should be a SQL string.
        
        rowdata will be an iterable of iterables containing the result values.
        columns will be an iterable of (column name, data type) pairs.
        """
        if conn is None:
            conn = self.connections.get()
        if isinstance(sql, unicode):
            sql = sql.encode(self.encoding)
        self.log(sql)
        
        cursor = conn.cursor()
        try:
            try:
                cursor.execute(sql)
            except Exception, x:
                if self.is_connection_error(x):
                    cursor.close()
                    self.connections.reset(conn)
                    cursor = conn.cursor()
                    cursor.execute(sql)
                else:
                    raise
            data = cursor.fetchall()
            coldefs = cursor.description
        finally:
            cursor.close()
        
        return data, coldefs

