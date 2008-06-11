"""Exception classes for Geniusql."""


class GeniusqlError(Exception):
    """Base class for errors which occur within Geniusql."""
    def __init__(self, *args):
        Exception.__init__(self)
        self.args = args
    
    def __str__(self):
        return u'\n'.join([unicode(arg) for arg in self.args])


class ReferenceError(GeniusqlError):
    """Exception raised when a reference between Tables cannot be found."""
    pass


class MappingError(GeniusqlError):
    """Exception raised when a Table name cannot be mapped to storage.
    
    This exception should be raised when a consumer attempts to build
    a map between a Table class and existing internal storage structures.
    Other exceptions may be raised when trying to find such a map after
    it has already (supposedly) been created. That is, the questions
    "do we have a map?" and "can we create a map?" are distinct.
    The latter should raise this exception whenever possible.
    The behavior of the former is not specified.
    """
    pass

class OutOfConnectionsError(GeniusqlError):
    """Exception raised when a database store has run out of connections."""
    pass

class TransactionLock(Exception):
    """Exception raised when a transaction is requested but not allowed.
    
    This is also used as a sentinel by a Database, to signal that a
    given thread should not start a new transaction because the thread
    is currently performing schema changes (DDL statements).
    """
    pass

class TransactionDisconnected(GeniusqlError):
    """Exception raised when a connection has been lost during a transaction.
    
    Normally, connections are automatically reset when errors occur. However,
    when a connection is lost during a transaction, it is assumed that any
    statements were rolled back when the connection was dropped; therefore,
    it is almost always unsafe to retry the current statement or proceed
    with the remaining statements; instead, this exception is raised.
    """
    pass


class FeatureWarning(UserWarning):
    """Warning about functionality which is not supported by all databases."""
    pass


def warn(msg, category=FeatureWarning, stacklevel=1):
    """Issue a warning, or maybe ignore it or raise an exception."""
    import warnings
    warnings.warn(msg, category, stacklevel + 1)

