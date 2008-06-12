"""Geniusql, a Python database library."""

__version__ = "1.0alpha"


class _AttributeDocstrings(type):
    """Metaclass for declaring docstrings for class attributes."""
    # The full docstring for this type is down in the __init__ method so
    # that it doesn't show up in help() for every consumer class.
    
    def __init__(cls, name, bases, dct):
        '''Metaclass for declaring docstrings for class attributes.
        
        Base Python doesn't provide any syntax for setting docstrings on
        'data attributes' (non-callables). This metaclass allows class
        definitions to follow the declaration of a data attribute with
        a docstring for that attribute; the attribute docstring will be
        popped from the class dict and folded into the class docstring.
        
        The naming convention for attribute docstrings is: <attrname> + "__doc".
        For example:
        
            class Thing(object):
                """A thing and its properties."""
                
                __metaclass__ = geniusql._AttributeDocstrings
                
                height = 50
                height__doc = """The height of the Thing in inches."""
        
        In which case, help(Thing) starts like this:
        
            >>> help(mod.Thing)
            Help on class Thing in module pkg.mod:
            
            class Thing(__builtin__.object)
             |  A thing and its properties.
             |  
             |  height [= 50]:
             |      The height of the Thing in inches.
             | 
        
        The benefits of this approach over hand-edited class docstrings:
            1. Places the docstring nearer to the attribute declaration.
            2. Makes attribute docs more uniform ("name (default): doc").
            3. Reduces mismatches of attribute _names_ between
               the declaration and the documentation.
            4. Reduces mismatches of attribute default _values_ between
               the declaration and the documentation.
        
        The benefits of a metaclass approach over other approaches:
            1. Simpler ("less magic") than interface-based solutions.
            2. __metaclass__ can be specified at the module global level
               for classic classes.
        
        For various formatting reasons, you should write multiline docs
        with a leading newline and not a trailing one:
            
            response__doc = """
            The response object for the current thread. In the main thread,
            and any threads which are not HTTP requests, this is None."""
        
        The type of the attribute is intentionally not included, because
        that's not How Python Works. Quack.
        '''
        type.__init__(name, bases, dct)
        
        newdoc = [cls.__doc__ or ""]
        
        dctnames = dct.keys()
        dctnames.sort()
        
        for name in dctnames:
            if name.endswith("__doc"):
                # Remove the magic doc attribute.
                if hasattr(cls, name):
                    delattr(cls, name)
                
                # Get an inspect-style docstring if possible (usually so).
                val = dct[name]
                try:
                    import inspect
                    val = inspect.getdoc(property(doc=val)).strip()
                except:
                    pass
                
                # Indent the docstring.
                val = '\n'.join(['    ' + line.rstrip()
                                 for line in val.split('\n')])
                
                # Get the default value.
                attrname = name[:-5]
                try:
                    attrval = getattr(cls, attrname)
                except AttributeError:
                    attrval = "missing"
                
                # Add the complete attribute docstring to our list.
                newdoc.append("%s [= %r]:\n%s" % (attrname, attrval, val))
        
        # Add our list of new docstrings to the class docstring.
        cls.__doc__ = "\n\n".join(newdoc)


from geniusql import errors, typerefs
from geniusql import adapters
from geniusql import conns
from geniusql import deparse
from geniusql import isolation
from geniusql.queries import *
from geniusql import sqlwriters
from geniusql import providers
from geniusql.objects import *


def db(provider, **options):
    """Return a Database and Schema object for the given provider.
    
    provider: A 'shortcut name' registered in geniusql.providers.registry.
    
    This function does not call CREATE DATABASE (although it may open a
    database connection).
    """
    return providers.registry.open(provider, **options)

