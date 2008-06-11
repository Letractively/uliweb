"""References to optional types (such as fixedpoint and decimal).

If a given type module cannot be imported, the module name will be None.

Rather than have each module that needs to (optionally) handle various
types do the ImportError dance, they can just import this module and do:

    if typerefs.decimal:
        handle_decimal()
"""


try:
    # Builtin in Python 2.6?
    decimal
except NameError:
    try:
        # Module in Python 2.3+
        import decimal
    except ImportError:
        decimal = None

try:
    import fixedpoint
except ImportError:
    fixedpoint = None

try:
    # Builtin in Python 2.4+
    set
except NameError:
    try:
        # Module in Python 2.3
        from sets import Set as set
    except ImportError:
        set = None
