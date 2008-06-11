"""Logic functions for Geniusql."""

import datetime as _datetime


def icontains(a, b):
    """Case-insensitive test b in a. Note the operand order."""
    return icontainedby(b, a)

def icontainedby(a, b):
    """Case-insensitive test a in b. Note the operand order."""
    if isinstance(b, basestring):
        # Looking for text in a string.
        if a is None or b is None:
            return False
        return a.lower() in b.lower()
    else:
        # Looking for field in (a, b, c).
        # Force all args to lowercase for case-insensitive comparison.
        if a is None or not b:
            return False
        return a.lower() in [x.lower() for x in b]

def istartswith(a, b):
    """True if a starts with b (case-insensitive), False otherwise."""
    if a is None or b is None:
        return False
    return a.lower().startswith(b.lower())

def iendswith(a, b):
    """True if a ends with b (case-insensitive), False otherwise."""
    if a is None or b is None:
        return False
    return a.lower().endswith(b.lower())

def ieq(a, b):
    """True if a == b (case-insensitive), False otherwise."""
    if a is None or b is None:
        return False
    return (a.lower() == b.lower())

def year(value):
    """The year attribute of a date."""
    if isinstance(value, (_datetime.date, _datetime.datetime)):
        return value.year
    else:
        return None

def month(value):
    """The month attribute of a date."""
    if isinstance(value, (_datetime.date, _datetime.datetime)):
        return value.month
    else:
        return None

def day(value):
    """The day attribute of a date."""
    if isinstance(value, (_datetime.date, _datetime.datetime)):
        return value.day
    else:
        return None

def now():
    """Late-bound datetime.datetime.now(). Taint this when early binding."""
    return _datetime.datetime.now()
now.irreducible = True

def utcnow():
    """Late-bound datetime.datetime.utcnow(). Taint this when early binding."""
    return _datetime.datetime.utcnow()
utcnow.irreducible = True

def today():
    """Late-bound datetime.date.today(). Taint this when early binding."""
    return _datetime.date.today()
today.irreducible = True

def iscurrentweek(value):
    """If value is in the current week, return True, else False."""
    if isinstance(value, (_datetime.date, _datetime.datetime)):
        return _datetime.date.today().strftime('%W%Y') == value.strftime('%W%Y')
    else:
        return False
iscurrentweek.irreducible = True

def count(values):
    """Return a count of the given values."""
    return len(values)

def alias(value, key):
    """Output the given value using the given key (instead of the default key)."""
    # TODO: This probably isn't correct, but it's not supported in non-DB
    # stores yet. Once that support is written, this will probably change.
    return (value, key)
alias.irreducible = True


def init():
    """Inject this module's functions into the logic module's globals."""
    from geniusql import logic
    for name, obj in globals().iteritems():
        if isinstance(obj, type(today)):
            logic.builtins[name] = obj
