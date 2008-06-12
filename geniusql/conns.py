"""Objects for managing database connections and transactions with Geniusql."""

__all__ = [
    'ConnectionManager',
    'ConnectionFactory', 'ConnectionPool', 'ConnectionWrapper',
    'SingleConnection',
    ]

import Queue
import threading
import time
import weakref

from geniusql import errors, isolation as _isolation


class ConnectionWrapper(object):
    """Connection object wrapper, so it can be used as a weak reference."""
    
    def __init__(self, conn=None):
        self.conn = conn
    
    def __getattr__(self, attr):
        return getattr(self.conn, attr)


class ConnectionFactoryBase(object):
    """A base class for connection factories."""
    
    def __init__(self, open, close, retry=5):
        self.open = open
        self.close = close
        if isinstance(retry, (list, tuple)):
            self.iterations = retry
        else:
            self.iterations = [x + 1 for x in range(retry)]
    
    def _create(self):
        """Return an (unwrapped) connection."""
        exc = None
        for i in self.iterations:
            try:
                return self.open()
            except errors.OutOfConnectionsError, exc:
                time.sleep(i)
        
        if exc:
            args = exc.args
        else:
            args = ["No connection found in %r iterations." % self.iterations]
        raise errors.OutOfConnectionsError(*args)


class ConnectionFactory(ConnectionFactoryBase):
    """A connection factory which creates a new connection for each request."""
    
    def __init__(self, open, close, retry=5):
        ConnectionFactoryBase.__init__(self, open, close, retry)
        self.refs = {}
    
    def __call__(self):
        """Return a (wrapped) connection."""
        conn = self._create()
        w = ConnectionWrapper(conn)
        self.refs[weakref.ref(w, self._release)] = w.conn
        return w
    
    def _release(self, ref):
        """Release a connection."""
        self.close(self.refs.pop(ref))
    
    def reset(self, conn):
        """Reset a (failed) connection."""
        self.close(conn.conn)
        conn.conn = self._create()
    
    def shutdown(self):
        """Release all database connections."""
        # Empty self.refs.
        while self.refs:
            ref, conn = self.refs.popitem()
            self.close(conn)


class ConnectionPool(ConnectionFactoryBase):
    """A database connection factory which keeps a pool of connections."""
    
    def __init__(self, open, close, retry=5, size=10):
        ConnectionFactoryBase.__init__(self, open, close, retry)
        self.refs = {}
        self.pool = Queue.Queue(size)
    
    def __call__(self):
        """Return a (wrapped) connection from the pool."""
        try:
            conn = self.pool.get_nowait()
        except Queue.Empty:
            conn = self._create()
        
        # Okay, this is freaky. If we wrap here, all goes well.
        # If we wrap on Queue.put(), mysql crashes after 1700
        # or so inserts (when migrating Access tables to MySQL).
        # Go figure.
        w = ConnectionWrapper(conn)
        self.refs[weakref.ref(w, self._release)] = w.conn
        return w
    
    def _release(self, ref):
        """Release a connection."""
        conn = self.refs.pop(ref)
        try:
            self.pool.put_nowait(conn)
            return
        except Queue.Full:
            pass
        self.close(conn)
    
    def reset(self, conn):
        """Reset a (failed) connection."""
        refkey = None
        for ref, bareconn in self.refs.items():
            if bareconn is conn.conn:
                refkey = ref
                break
        
        # The 'conn' is actually a ConnectionWrapper instance.
        self.close(conn.conn)
        # Pop the weakref out in case _create raises OutOfConnectionsError.
        self.refs.pop(refkey, None)
        
        conn.conn = self._create()
        
        # Replace the bare conn in self.refs.
        if refkey is None:
            refkey = weakref.ref(conn, self._release)
        self.refs[refkey] = conn.conn
    
    def shutdown(self):
        """Release all database connections."""
        # Empty the pool.
        while True:
            try:
                self.pool.get(block=False)
            except Queue.Empty:
                break
        
        # Empty self.refs.
        while self.refs:
            ref, conn = self.refs.popitem()
            self.close(conn)


class ConnectionPerThread(ConnectionFactoryBase):
    """A database connection factory which uses one connection per thread.
    
    This is useful for SQLite; from http://www.sqlite.org/c_interface.html:
        
        "If SQLite is compiled with the THREADSAFE preprocessor macro set
        to 1, then it is safe to use SQLite from two or more threads of
        the same process at the same time. But each thread should have
        its own sqlite* pointer returned from sqlite_open. It is never safe
        for two or more threads to access the same sqlite* pointer at the
        same time.
        
        In precompiled SQLite libraries available on the website, the Unix
        versions are compiled with THREADSAFE turned off but the windows
        versions are compiled with THREADSAFE turned on. If you need
        something different that this you will have to recompile."
    
    See also http://www.sqlite.org/faq.html#q8
    """
    
    def __init__(self, open, close, retry=5):
        ConnectionFactoryBase.__init__(self, open, close, retry)
        self.refs = {}
    
    def __call__(self):
        """Return the connection for the current thread."""
        threadid = threading._get_ident()
        try:
            return self.refs[threadid]
        except KeyError:
            conn = self._create()
            self.refs[threadid] = conn
            return ConnectionWrapper(conn)
    
    def reset(self, conn):
        """Reset a (failed) connection."""
        refkey = None
        for ref, bareconn in self.refs.items():
            if bareconn is conn.conn:
                refkey = ref
                break
        
        # The 'conn' is actually a ConnectionWrapper instance.
        self.close(conn.conn)
        conn.conn = self._create()
        
        # Replace the bare conn in self.refs.
        if refkey is not None:
            self.refs[refkey] = conn.conn
    
    def shutdown(self):
        """Release all database connections."""
        # Empty the conn map.
        while self.refs:
            threadid, conn = self.refs.popitem()
            self.close(conn)


class SingleConnection(ConnectionFactoryBase):
    """A single database connection for all consumers.
    
    Use this when your database cannot handle multiple connections at once,
    but can handle multiple threads using the same connection.
    """
    
    def __init__(self, open, close, retry=5):
        ConnectionFactoryBase.__init__(self, open, close, retry)
        # Delay opening the connection, because the
        # SM may need to create the database first.
        self._conn = None
    
    def __call__(self):
        """Return our only connection."""
        if self._conn is None:
            self._conn = self._create()
        return ConnectionWrapper(self._conn)
    
    def reset(self, conn):
        """Reset a (failed) connection."""
        # The 'conn' is actually a ConnectionWrapper instance.
        self.close(conn.conn)
        conn.conn = self._conn = self._create()
    
    def shutdown(self):
        """Release all database connections."""
        if self._conn is not None:
            self.close(self._conn)
            self._conn = None


class ConnectionManager(object):
    
    retry = 5
    poolsize = 10
    implicit_trans = False
    
    # Change this to 'error' if you don't want autocommit on schema ops.
    contention = 'commit'
    
    # The "default_isolation" value should be a value native to the DB.
    default_isolation = None
    
    # The values in "isolation_levels" should match the names of
    # IsolationLevel objects in isolation.py
    isolation_levels = ["READ UNCOMMITTED", "READ COMMITTED",
                        "REPEATABLE READ", "SERIALIZABLE"]
    
    # Any SQL to execute per connection (inside _get_conn)
    # before returning the connection to the caller.
    initial_sql = None
    
    def __init__(self, db):
        self.transactions = {}
        self.db = db
        self._set_factory()
    
    def _set_factory(self):
        if self.poolsize > 0:
            self._factory = ConnectionPool(self._get_conn, self._del_conn,
                                           self.retry, self.poolsize)
        else:
            self._factory = ConnectionFactory(self._get_conn, self._del_conn,
                                              self.retry)
    
    def shutdown(self):
        """Release all database connections."""
        self._factory.shutdown()
    
    def _get_conn(self):
        """Create and return a connection object."""
        # Override this with the connection call for your DB. Example:
        #     return libpq.PQconnectdb(self.connstring)
        raise NotImplementedError
    
    def _del_conn(self, conn):
        """Close a connection object."""
        # Override this with the close call (if any) for your DB.
        conn.close()
    
    def get(self, isolation=None):
        """Return the (possibly new) connection for the current transaction.
        
        If we are already in a transaction, this returns the connection for
        that transaction. The "current transaction" context is determined by
        self.id(); by default, this is the current thread ID (but subclasses
        are free to change this). If there is no "current transaction", then
        a new connection object is obtained (usually from a pool).

        If self.implicit_trans is True, a new connection will automatically
        call "START TRANSACTION". It will also be associated with self.id(),
        and any subsequent calls to this method will then return the same
        connection object. If self.implicit_trans is False, new connections
        won't be STARTed or stored.
        """
        key = self.id()
        if key in self.transactions:
            conn = self.transactions[key]
            if isinstance(conn, errors.TransactionLock):
                raise conn
        else:
            conn = self._factory()
            if self.implicit_trans:
                self._start_transaction(conn, isolation)
                # We MUST execute START before putting the conn in
                # self.transactions so that dead connections have a chance
                # to reconnect.
                self.transactions[key] = conn
        return conn
    
    def reset(self, conn):
        """Reset the given (failed) connection."""
        # If in a transaction, error, but first remove the conn from
        # self.transactions (in a thread-safe way).
        for key, txconn in self.transactions.items():
            if txconn is conn:
                self.transactions.pop(key, None)
                raise errors.TransactionDisconnected()
        
        self._factory.reset(conn)
    
    def id(self):
        """The current transaction id."""
        return threading._get_ident()
    
    def start(self, isolation=None):
        """Start a transaction. Not needed if self.implicit_trans is True."""
        key = self.id()
        if key in self.transactions:
            conn = self.transactions[key]
            if isinstance(conn, errors.TransactionLock):
                raise conn
        else:
            conn = self._factory()
            self._start_transaction(conn, isolation)
            # We MUST execute START before putting the conn in
            # self.transactions so that dead connections have a chance
            # to reconnect.
            self.transactions[key] = conn
    
    def _start_transaction(self, conn, isolation=None):
        """Start a transaction."""
        self.db.execute("START TRANSACTION;", conn)
        self.isolate(conn, isolation)
    
    def isolate(self, conn, isolation=None):
        """Set the isolation level of the given connection.
        
        If 'isolation' is None, our default_isolation will be used for new
        connections. Valid values for the 'isolation' argument may be native
        values for your particular database. However, it is recommended you
        pass items from the global 'levels' list instead; these will be
        automatically replaced with native values.
        
        For many databases, this must be executed after START TRANSACTION.
        """
        if isolation is None:
            isolation = self.default_isolation
        
        if isinstance(isolation, _isolation.IsolationLevel):
            # Map the given IsolationLevel object to a native value.
            isolation = isolation.name
            if isolation not in self.isolation_levels:
                raise ValueError("IsolationLevel %r not allowed by %s. "
                                 "Try one of %r instead."
                                 % (isolation, self.__class__.__name__,
                                    self.isolation_levels))
        
        # This is SQL92 syntax, and should work with most DB's.
        self.db.execute("SET TRANSACTION ISOLATION LEVEL %s;" % isolation, conn)
    
    def rollback(self):
        """Roll back the current transaction, if any."""
        key = self.id()
        if key in self.transactions:
            self.db.execute("ROLLBACK;", self.transactions[key])
            del self.transactions[key]
        else:
            # This is critical in order to support polygonal SM structures
            # (same store being called twice by separate proxies).
            pass
    
    def commit(self):
        """Commit the current transaction, if any."""
        try:
            conn = self.transactions.pop(self.id())
        except KeyError:
            # This is critical in order to support polygonal SM structures
            # (same store being called twice by separate proxies).
            pass
        else:
            self.db.execute("COMMIT;", conn)
    
    def lock(self, msg=None):
        """Deny transactions during schema operations (DDL statements).
        
        Any code which calls this should also call 'unlock' in a try/finally:
        
        db.connections.lock('dropping storage')
        try:
            db.execute("DROP TABLE %s;" % tablename)
        finally:
            db.connections.unlock()
        """
        key = self.id()
        if key in self.transactions:
            if isinstance(self.transactions[key], errors.TransactionLock):
                return
            if self.contention == 'error':
                raise errors.TransactionLock("Schema operations are not "
                                             "allowed inside transactions.")
            self.commit()
        
        if msg is None:
            msg = "Transactions not allowed at the moment."
        self.transactions[key] = errors.TransactionLock(msg)
    
    def unlock(self):
        """Allow transactions."""
        key = self.id()
        trans = self.transactions.get(key, None)
        if trans is None:
            return
        if not isinstance(trans, errors.TransactionLock):
            raise errors.TransactionLock("Unlock called inside transaction.")
        del self.transactions[key]
    
    def in_transaction(self):
        """Return True if the current context is in a transaction.
        
        This also returns True if the current context is executing DDL
        statements, or is barred from starting a transaction for some
        other reason.
        """
        trans = self.transactions.get(self.id())
        if trans is None or isinstance(trans, errors.TransactionLock):
            return False
        return True

