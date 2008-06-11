# Use libpq directly to avoid all of the DB-API overhead.
from pyPgSQL import libpq

from geniusql import conns, errors
from geniusql.providers import postgres


class PyPgConnectionManager(conns.ConnectionManager):
    
    default_isolation = "READ COMMITTED"
    
    def _get_conn(self, master=False):
        if master:
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
            conn = libpq.PQconnectdb(connstr)
            if self.initial_sql:
                conn.query(self.initial_sql)
            return conn
        except libpq.DatabaseError, x:
            msg = x.args[0]
            if (msg.startswith('could not connect') or
                msg.startswith('server closed the connection unexpectedly') or
                msg.startswith('timeout expired')
                ):
                    raise errors.OutOfConnectionsError(*x.args)
            raise
    
    def _del_conn(self, conn):
        try:
            conn.finish()
        except libpq.InterfaceError, exc:
            if exc.args == ('PgConnection object is closed',):
                pass
            else:
                raise
    
    def reset(self, conn):
        """Reset the given (failed) connection."""
        # If in a transaction, error, but first remove the conn from
        # self.transactions (in a thread-safe way).
        for key, txconn in self.transactions.items():
            if txconn is conn:
                self.transactions.pop(key, None)
                raise errors.TransactionDisconnected()
        
        if conn.status == libpq.CONNECTION_OK:
            conn.reset()
        else:
            self._factory.reset(conn)


class PyPgDatabase(postgres.PgDatabase):
    
    connectionmanager = PyPgConnectionManager
    
    def __init__(self, **opts):
        postgres.PgDatabase.__init__(self, **opts)
        connstr = opts.get('connections.Connect', None)
        if connstr:
            for atom in connstr.split(" "):
                k, v = atom.split("=", 1)
                if k == 'dbname':
                    self.name = v
                    self.qname = self.quote(v)
    
    def _get_dbinfo(self, conn=None):
        dbinfo = {}
        try:
            data, _ = self.fetch("SELECT pg_encoding_to_char(encoding) "
                                 "FROM pg_database;", conn=conn)
            dbinfo['encoding'] = data[0][0]
        except libpq.DatabaseError, x:
            if "does not exist" not in x.args[0]:
                raise
        return dbinfo
    
    def is_connection_error(self, exc):
        """If the given exception instance is a connection error, return True.
        
        This should return True for errors which arise from broken connections;
        for example, if the database server has dropped the connection socket,
        or is unreachable.
        """
        if isinstance(exc, libpq.OperationalError):
            # OperationalError: server closed the connection unexpectedly
            #   This probably means the server terminated abnormally
            #   before or while processing the request.
            # OperationalError: no connection to the server\n
            msg = exc.args[0]
            return (msg.startswith('no connection to the server') or
                    msg.startswith('server closed the connection unexpectedly'))
        elif isinstance(exc, libpq.InterfaceError):
            # InterfaceError: PgConnection object is closed
            msg = exc.args[0]
            return msg.startswith('PgConnection object is closed')
        return False
    
    def execute_ddl(self, sql, conn=None):
        """Return a native response for the given DDL statement.
        
        In general, DDL statements should lock out other statements
        (especially those isolated in other transactions). Use this
        method to perform a locked DDL statement.
        """
        try:
            postgres.PgDatabase.execute_ddl(self, sql, conn)
        except libpq.OperationalError, x:
            if x.args:
                msg = x.args[0]
                if "already exists" in msg or "does not exist" in msg:
                    raise errors.MappingError(*x.args)
            raise
    
    def fetch(self, sql, conn=None):
        """Return rowdata, columns(name, type) for the given sql.
        
        sql should be a SQL string.
        
        rowdata will be an iterable of iterables containing the result values.
        columns will be an iterable of (column name, data type) pairs.
        """
        res = self.execute(sql, conn)
        
        columns = []
        if res.resultType != libpq.EMPTY_QUERY:
            for index in xrange(res.nfields):
                columns.append((res.fname(index), res.ftype(index)))
        
        data = [[res.getvalue(row, col) for col in xrange(res.nfields)]
                for row in xrange(res.ntuples)]
        res.clear()
        
        return data, columns
    
    def version(self):
        c = self.connections._get_conn(master=True)
        v = c.version
        self.connections._del_conn(c)
        return str(v)

