# This module is used for wrapping geniusql to a simple ORM
# Author: limodou <limodou@gmail.com>
# 2008.06.11

import sys

sys.path.insert(0, '../../..')

__all__ = ['Field', 'get_connection', 'Model', 'migirate_table',
    'set_auto_bind', 'set_auto_migirate', 'set_debug_log', 
    'blob', 'text',
    'BlobProperty', 'BooleanProperty', 'DateProperty', 'DateTimeProperty',
    'TimeProperty', 'DecimalProperty', 'FileProperty', 'FloatProperty',
    'IntegerProperty', 'Property', 'PickleProperty', 'StringProperty',
    'TextProperty', 'UnicodeProperty', 'Reference', 'ReferenceProperty',
    'SelfReference', 'SelfReferenceProperty',
    'ReservedWordError', 'BadValueError', 'DuplicatePropertyError', 
    'ModelInstanceError', 'KindError', 'ConfigurationError']

__default_connection__ = None  #global connection instance
__auto_bind__ = False
__auto_migirate__ = False
__debug_log__ = None

import re
import geniusql
import decimal
import threading
import datetime

_SELF_REFERENCE = object()

def set_auto_bind(flag):
    global __auto_bind__
    __auto_bind__ = flag
    
def set_auto_migirate(flag):
    global __auto_migirate__
    __auto_migirate__ = flag
    
def set_debug_log(log):
    global __debug_log__
    __debug_log__ = log

def get_connection(connection='', default=True, **args):
    global __default_connection__
    global __orm__
    
    if default:
        if __default_connection__:
            return __default_connection__
        
    if not connection.startswith('gae'):
        db = DB(connection, **args)
    if db:
        if default:
            __default_connection__ = db
        db.__default_connection__ = __default_connection__
        db.__auto_bind__ = __auto_bind__
        db.__auto_migirate__ = __auto_migirate__
        db.__debug_log__ = __debug_log__

    return db

def _default_sql_log(message):
    sys.stdout.write("[Debug] SQL -- %s\n" % message)

class Error(Exception):pass
class ReservedWordError(Error):pass
class ModelInstanceError(Error):pass
class DuplicatePropertyError(Error):
  """Raised when a property is duplicated in a model definition."""
class BadValueError(Error):pass
class KindError(Error):pass
class ConfigurationError(Error):pass

def DB(connection='', **args):
    d = parse(connection, **args)
    provider = d.pop('provider')
    if provider == 'sqlite':
        if d.get('db', None):
            d['name'] = d['db']
        else:
            d['name'] = ':memory:'
    elif provider == 'firebird':
        if d.get('passwd', None):
            d['password'] = d['passwd']
    elif provider == 'mysql':
        d['encoding'] = d.setdefault('encoding', 'utf8')
    db = geniusql.db(provider, **d)
    if provider == 'sqlite':
        db.create()
    db._schema = db.schema()
    db._schema.create()
    
    if __debug_log__:
        if __debug_log__ is True:
            log = _default_sql_log
        else:
            log = __debug_log__
        setattr(db, 'log', log)
        
    return db

r_spec = re.compile('(?P<provider>.*?)://(?:(?P<user>.*?)(?::(?P<password>.*?))?@)?(?:(?P<url>.*?)(?:\?(?P<arguments>.*))?)?$')
def parse(connection, **args):
    """
    A connection should be formatted like:
        provider://<user:password@>host:port/dbname<?arg1=value1&arg2=value2>
        
        <> can be optional
        
        for provider, they are: 
        
            sqlite, access, firebird, mysql, postgres, psycopg, sqlserver
        
        For sqlite:
        sqlite:///absolute/path/to/databasefile
        sqlite://relative/path/to/databasefile
        sqlite://   #in-memory database
        sqlite      #also in-memory database
        gae         #GAE
    """
    b = r_spec.match(connection)
    if b:
        d = b.groupdict()
        url = d.pop('url')
        if url:
            if d['provider'] == 'sqlite':
                d['db'] = url
                d['host'] = None
                d['port'] = None
            else:
                a, db = url.split('/')
                d['db'] = db
                if ':' in a:
                    d['host'], d['port'] = a.split(':')
                    d['port'] = int(d['port'])
                else:
                    d['host'], d['port'] = a, None
        else:
            d['db'] = url
            d['host'] = None
            d['port'] = None
        argus = d.pop('arguments')
        if argus:
            x = dict([i.split('=') for i in argus.split('&')])
            d.update(x)    
    else:
        d = {'provider':connection}
    #clear empty key
    for k, v in d.copy().items():
        if not v:
            del d[k]
            
    d.update(args)
    return d

class SQLStorage(dict):
    """
    a dictionary that let you do d['a'] as well as d.a
    """
    def __getattr__(self, key): return self[key]
    def __setattr__(self, key, value):
        if self.has_key(key):
            raise SyntaxError, 'Object exists and cannot be redefined'
        self[key] = value
    def __repr__(self): return '<SQLStorage ' + dict.__repr__(self) + '>'

def check_reserved_word(f):
    if f in ['put', 'save'] or f in dir(Model):
        raise ReservedWordError(
            "Cannot define property using reserved word '%s'. " % f
            )
    
class ModelMetaclass(type):
    def __init__(cls, name, bases, dct):
        super(ModelMetaclass, cls).__init__(name, bases, dct)
        cls._set_tablename()
        
        cls.properties = {}
        defined = set()
        for base in bases:
            if hasattr(base, 'properties'):
                property_keys = base.properties.keys()
                duplicate_properties = defined.intersection(property_keys)
                if duplicate_properties:
                    raise DuplicatePropertyError(
                        'Duplicate properties in base class %s already defined: %s' %
                        (base.__name__, list(duplicate_properties)))
                defined.update(property_keys)
                cls.properties.update(base.properties)
        
        for attr_name in dct.keys():
            attr = dct[attr_name]
            if isinstance(attr, Property):
                check_reserved_word(attr_name)
                if attr_name in defined:
                    raise DuplicatePropertyError('Duplicate property: %s' % attr_name)
                defined.add(attr_name)
                cls.properties[attr_name] = attr
                attr.name = attr_name
                attr.__property_config__(cls, attr_name)
                
        if 'id' not in cls.properties:
            cls.properties['id'] = f = Field(int, autoincrement=True, key=True)
            f.__property_config__(cls, 'id')
            f.name = 'id'
            setattr(cls, 'id', f)

        fields_list = [(k, v) for k, v in cls.properties.items()]
        fields_list.sort(lambda x, y: cmp(x[1].creation_counter, y[1].creation_counter))
        cls._fields_list = fields_list
        
        if cls.__class__.__name__ != 'Model' and __auto_bind__:
            cls.bind(auto_create=__auto_migirate__)
        
class Property(object):
    data_type = str
    creation_counter = 0

    def __init__(self, verbose_name=None, name=None, default=None,
         required=False, validator=None, choices=None, max_length=None, **kwargs):
        self.verbose_name = verbose_name
        self.name = name
        self.default = default
        self.required = required
        self.validator = validator
        self.choices = choices
        self.max_length = max_length
        self.kwargs = kwargs
        self.creation_counter = Property.creation_counter
        self.value = None
        Property.creation_counter += 1

    def __property_config__(self, model_class, property_name):
        self.model_class = model_class
        if self.name is None:
            self.name = property_name

    def __get__(self, model_instance, model_class):
        if model_instance is None:
            return self

        try:
            return getattr(model_instance, self._attr_name())
        except AttributeError:
            return None
        
    def __set__(self, model_instance, value):
        if model_instance is None:
            return
        
        value = self.validate(value)
        #add value to model_instance._changed_value, so that you can test if
        #a object really need to save
        setattr(model_instance, self._attr_name(), value)

    def default_value(self):
        return self.default

    def validate(self, value):
        if self.empty(value):
            if self.required:
                raise BadValueError('Property %s is required' % self.name)
        else:
            if self.choices:
                match = False
                for choice in self.choices:
                    if choice == value:
                        match = True
                if not match:
                    raise BadValueError('Property %s is %r; must be one of %r' %
                        (self.name, value, self.choices))
        if value is not None and not isinstance(value, self.data_type):
            try:
                value = self.convert(value)
            except TypeError, err:
                raise BadValueError('Property %s must be convertible '
                    'to a string or unicode (%s)' % (self.name, err))
        
        if self.validator is not None:
            self.validator(value)
        return value

    def empty(self, value):
        return value is None

    def get_value_for_datastore(self, model_instance):
        return self.__get__(model_instance, model_instance.__class__)

    def make_value_from_datastore(self, value):
        return value
    
    def convert(self, value):
        return self.data_type(value)
    
    def __repr__(self):
        return ("<Property 'type':%r, 'verbose_name':%r, 'name':%r, " 
            "'default':%r, 'required':%r, 'validator':%r, "
            "'chocies':%r, 'max_length':%r, 'kwargs':%r>"
            % (self.data_type, 
            self.verbose_name,
            self.name,
            self.default,
            self.required,
            self.validator,
            self.choices,
            self.max_length,
            self.kwargs)
            )
            
    def _attr_name(self):
        return '_' + self.name + '_'
    
class StringProperty(Property):
    data_type = str
    
    def empty(self, value):
        return not value

class UnicodeProperty(StringProperty):
    data_type = unicode
    
class TextProperty(StringProperty): pass

class BlobProperty(StringProperty): pass

class DateTimeProperty(Property):
    data_type = datetime.datetime
    
    DEFAULT_DATETIME_INPUT_FORMATS = (
        '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
        '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
        '%Y-%m-%d',              # '2006-10-25'
        '%Y/%m/%d %H:%M:%S',     # '2006/10/25 14:30:59'
        '%Y/%m/%d %H:%M',        # '2006/10/25 14:30'
        '%Y/%m/%d ',             # '2006/10/25 '
        '%m/%d/%Y %H:%M:%S',     # '10/25/2006 14:30:59'
        '%m/%d/%Y %H:%M',        # '10/25/2006 14:30'
        '%m/%d/%Y',              # '10/25/2006'
        '%m/%d/%y %H:%M:%S',     # '10/25/06 14:30:59'
        '%m/%d/%y %H:%M',        # '10/25/06 14:30'
        '%m/%d/%y',              # '10/25/06'
    )
    
    def __init__(self, verbose_name=None, auto_now=False, auto_now_add=False,
             **kwds):
        super(DateTimeProperty, self).__init__(verbose_name, **kwds)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

    def validate(self, value):
        value = super(DateTimeProperty, self).validate(value)
        if value and not isinstance(value, self.data_type):
            raise BadValueError('Property %s must be a %s' %
                (self.name, self.data_type.__name__))
        return value

    def default_value(self):
        if self.auto_now or self.auto_now_add:
            return self.now()
        return Property.default_value(self)

    def get_value_for_datastore(self, model_instance):
        if self.auto_now:
            return self.now()
        else:
            return super(DateTimeProperty,
                self).get_value_for_datastore(model_instance)

    @staticmethod
    def now():
        return datetime.datetime.now()

    def convert(self, value):
        import time
        for format in self.DEFAULT_DATETIME_INPUT_FORMATS:
            try:
                return datetime.datetime(*time.strptime(value, format)[:6])
            except ValueError:
                continue
    
class DateProperty(DateTimeProperty):
    data_type = datetime.date

    def get_value_for_datastore(self, model_instance):
        value = super(DateProperty, self).get_value_for_datastore(model_instance)
        if value is not None:
            value = datetime.datetime(value.year, value.month, value.day)
        return value

    def make_value_from_datastore(self, value):
        if value is not None:
            value = value.date()
        return value

class TimeProperty(DateTimeProperty):
    """A time property, which stores a time without a date."""

    data_type = datetime.time
    
    def get_value_for_datastore(self, model_instance):
        value = super(TimeProperty, self).get_value_for_datastore(model_instance)
        if value is not None:
            value = datetime.time(value.hour, value.minute, value.second,
                value.microsecond)
        return value

    def make_value_from_datastore(self, value):
        if value is not None:
            value = datetime.datetime(1970, 1, 1,
                value.hour, value.minute, value.second,
                value.microsecond)
        return value

class IntegerProperty(Property):
    """An integer property."""

    data_type = int
    
    def validate(self, value):
        value = super(IntegerProperty, self).validate(value)
        if value is None:
            return value
        if not isinstance(value, (int, long)) or isinstance(value, bool):
            raise BadValueError('Property %s must be an int, not a %s'
                % (self.name, type(value).__name__))
        return value

class FloatProperty(Property):
    """A float property."""

    data_type = float

    def __init__(self, verbose_name=None, default=0.0, **kwds):
        super(FloatProperty, self).__init__(verbose_name, default=default, **kwds)
   
    def validate(self, value):
        value = super(FloatProperty, self).validate(value)
        if value is not None and not isinstance(value, float):
            raise BadValueError('Property %s must be a float' % self.name)
        return value
    
class DecimalProperty(Property):
    """A float property."""

    data_type = decimal.Decimal

    def __init__(self, verbose_name=None, default='0.0', **kwds):
        super(DecimalProperty, self).__init__(verbose_name, default=default, **kwds)
   
    def validate(self, value):
        value = super(DecimalProperty, self).validate(value)
        if value is not None and not isinstance(value, decimal.Decimal):
            raise BadValueError('Property %s must be a float' % self.name)
        return value

class BooleanProperty(Property):
    """A boolean property."""

    data_type = bool

    def __init__(self, verbose_name=None, default=False, **kwds):
        super(BooleanProperty, self).__init__(verbose_name, default=default, **kwds)
    
    def validate(self, value):
        value = super(BooleanProperty, self).validate(value)
        if value is not None and not isinstance(value, bool):
            raise BadValueError('Property %s must be a bool' % self.name)
        return value

class PickleProperty(Property):
    data_type = None

    def validate(self, value):
        return value
    
    def get_value_for_datastore(self, model_instance):
        value = super(TimeProperty, self).get_value_for_datastore(model_instance)
        if value is not None:
            import cPickle
            value = cPickle.loads(value)
        return value

    def make_value_from_datastore(self, value):
        if value is not None:
            import cPickle
            value = cPickle.dumps(value)
        return value
    
class FileProperty(Property):
    data_type = None
    
    def validate(self, value):
        value = super(IntegerProperty, self).validate(value)
        if value is None:
            return value
        if not hasattr(value, 'read') or not hasattr(value, 'write'):
            raise BadValueError('Property %s must be an int or long, not a %s'
                % (self.name, type(value).__name__))
        return value
    
    def get_value_for_datastore(self, model_instance):
        value = super(TimeProperty, self).get_value_for_datastore(model_instance)
        import cStringIO
        buf = cStringIO.StringIO()
        if value is not None:
            buf.write(value)
        return buf
    
    def make_value_from_datastore(self, value):
        if value is not None:
            value = value.read()
        return value
    

class ReferenceProperty(Property):
    """A property that represents a many-to-one reference to another model.
    """

    def __init__(self, reference_class=None, verbose_name=None, collection_name=None, 
        reference_fieldname=None, **attrs):
        """Construct ReferenceProperty.

        Args:
            reference_class: Which model class this property references.
            verbose_name: User friendly name of property.
            collection_name: If provided, alternate name of collection on
                reference_class to store back references.    Use this to allow
                a Model to have multiple fields which refer to the same class.
            reference_fieldname used to specify which fieldname of reference_class
                should be referenced
        """
        super(ReferenceProperty, self).__init__(verbose_name, **attrs)

        self.collection_name = collection_name
        self.reference_fieldname = reference_fieldname

        if reference_class is None:
            reference_class = Model
        if not ((isinstance(reference_class, type) and
                         issubclass(reference_class, Model)) or
                        reference_class is _SELF_REFERENCE):
            raise KindError('reference_class must be Model or _SELF_REFERENCE')
        self.reference_class = self.data_type = reference_class

    def __property_config__(self, model_class, property_name):
        """Loads all of the references that point to this model.
        """
        super(ReferenceProperty, self).__property_config__(model_class, property_name)

        if self.reference_class is _SELF_REFERENCE:
            self.reference_class = self.data_type = model_class

        if self.collection_name is None:
            self.collection_name = '%s_set' % (model_class.tablename)
        if hasattr(self.reference_class, self.collection_name):
            raise DuplicatePropertyError('Class %s already has property %s'
                 % (self.reference_class.__name__, self.collection_name))
        setattr(self.reference_class, self.collection_name,
            _ReverseReferenceProperty(model_class, property_name, self.__id_attr_name()))

    def __get__(self, model_instance, model_class):
        """Get reference object.

        This method will fetch unresolved entities from the datastore if
        they are not already loaded.

        Returns:
            ReferenceProperty to Model object if property is set, else None.
        """
        if model_instance is None:
            return self
        if hasattr(model_instance, self.__id_attr_name()):
            reference_id = getattr(model_instance, self._attr_name())
        else:
            reference_id = None
        if reference_id is not None:
            #this will cache the reference object
            resolved = getattr(model_instance, self.__resolved_attr_name())
            if resolved is not None:
                return resolved
            else:
                id_field = self.__id_attr_name()
                d = {id_field:reference_id}
                instance = self.reference_class.get(**d)
                if instance is None:
                    raise Error('ReferenceProperty failed to be resolved')
                setattr(model_instance, self.__resolved_attr_name(), instance)
                return instance
        else:
            return None

    def __set__(self, model_instance, value):
        """Set reference."""
        value = self.validate(value)
        if value is not None:
            if isinstance(value, int):
                setattr(model_instance, self._attr_name(), value)
                setattr(model_instance, self.__resolved_attr_name(), None)
            else:
                setattr(model_instance, self._attr_name(), value.id)
                setattr(model_instance, self.__resolved_attr_name(), value)
        else:
            setattr(model_instance, self._attr_name(), None)
            setattr(model_instance, self.__resolved_attr_name(), None)

    def get_value_for_datastore(self, model_instance):
        """Get key of reference rather than reference itself."""
        return getattr(model_instance, self.__id_attr_name())

    def validate(self, value):
        """Validate reference.

        Returns:
            A valid value.

        Raises:
            BadValueError for the following reasons:
                - Value is not saved.
                - Object not of correct model type for reference.
        """
        if isinstance(value, int):
            return value

        if value is not None and not value.is_saved():
            raise BadValueError(
                    '%s instance must be saved before it can be stored as a '
                    'reference' % self.reference_class.__class__.__name__)

        value = super(ReferenceProperty, self).validate(value)

        if value is not None and not isinstance(value, self.reference_class):
            raise KindError('Property %s must be an instance of %s' %
                    (self.name, self.reference_class.__class__.__name__))

        return value

    def __id_attr_name(self):
        """Get attribute of referenced id.
        #todo add id function or key function to model
        """
        if not self.reference_fieldname:
            self.reference_fieldname = 'id'
        return self.reference_fieldname

    def __resolved_attr_name(self):
        """Get attribute of resolved attribute.

        The resolved attribute is where the actual loaded reference instance is
        stored on the referring model instance.

        Returns:
            Attribute name of where to store resolved reference model instance.
        """
        return '_RESOLVED' + self._attr_name()


Reference = ReferenceProperty

def SelfReferenceProperty(verbose_name=None, collection_name=None, **attrs):
    """Create a self reference.
    """
    if 'reference_class' in attrs:
        raise ConfigurationError(
                'Do not provide reference_class to self-reference.')
    return ReferenceProperty(_SELF_REFERENCE, verbose_name, collection_name, **attrs)

SelfReference = SelfReferenceProperty

class _ReverseReferenceProperty(Property):
    """The inverse of the Reference property above.

    We construct reverse references automatically for the model to which
    the Reference property is pointing to create the one-to-many property for
    that model.    For example, if you put a Reference property in model A that
    refers to model B, we automatically create a _ReverseReference property in
    B called a_set that can fetch all of the model A instances that refer to
    that instance of model B.
    """

    def __init__(self, model, reference_id, reversed_id):
        """Constructor for reverse reference.

        Constructor does not take standard values of other property types.

        Args:
            model: Model that this property is a collection of.
            property: Foreign property on referred model that points back to this
                properties entity.
        """
        self.__model = model
        self.__reference_id = reference_id    #B Reference(A) this is B's id
        self.__reversed_id = reversed_id    #A's id

    def __get__(self, model_instance, model_class):
        """Fetches collection of model instances of this collection property."""
        if model_instance is not None:
            _id = getattr(model_instance, self.__reversed_id, None)
            if _id is not None:
                b_id = self.__reference_id
                d = {b_id:_id}
                return self.__model.filter(**d)
            else:
                return []
        else:
            return self

    def __set__(self, model_instance, value):
        """Not possible to set a new collection."""
        raise BadValueError('Virtual property is read-only')

class blob(type):pass
class text(type):pass

_fields_mapping = {
    basestring:StringProperty,
    str:StringProperty,
    unicode: UnicodeProperty,
    text:TextProperty,
    blob:BlobProperty,
    file:FileProperty,
    int:IntegerProperty,
    float:FloatProperty,
    datetime.datetime:DateTimeProperty,
    datetime.date:DateProperty,
    datetime.time:TimeProperty,
    decimal.Decimal:DecimalProperty,
}
def Field(type, **kwargs):
    t = _fields_mapping.get(type, PickleProperty)
    return t(**kwargs)

class Model(object):

    __metaclass__ = ModelMetaclass
    
    _lock = threading.Lock()
    _c_lock = threading.Lock()
    
    def __init__(self, **kwargs):
        self._old_values = {}
        for prop in self.properties.values():
            if prop.name in kwargs:
                value = kwargs[prop.name]
            else:
                value = prop.default_value()
            prop.__set__(self, value)
        
    def _set_saved(self):
        self._old_values = self.to_dict()
        
    def to_dict(self):
        d = {}
        for k, v in self.properties.items():
            t = getattr(self, k, None)
            if isinstance(t, Model):
                t = t.id
            d[k] = t
        return d
            
    def _get_data(self):
        """
        Get the changed property, it'll be used to save the object
        """
        if self.id is None:
            d = {}
            for k in self.properties.keys():
                v = getattr(self, k, None)
                if isinstance(v, Model):
                    v = v.id
                if v is not None:
                    d[k] = v
        else:
            d = {}
            d['id'] = self.id
            for k, v in self.properties.items():
                t = self._old_values.get(k, None)
                x = getattr(self, k, None)
                if isinstance(x, Model):
                    x = x.id
                if (x is not None and t is not None) and repr(t) != repr(x):
                    d[k] = x
        
        return d
            
    def is_saved(self):
        return bool(self.id) 
            
    def put(self):
        d = self._get_data()
        if d:
            if not self.id:
                obj = self.table.insert(**d)
                setattr(self, 'id', obj['id'])
            else:
                self.table.save(**d)
            self._set_saved()
        return self
    
    save = put
    
    def delete(self):
        self.table.delete(id=self.id)
        self.id = None
        self._old_values = {}
            
#    def __getattr__(self, name):
#        if name.startswith('reference_'):
#            b_id = name[10:]
#            def _f(b, restriction=None, order=None, limit=None, self=self, b_id=b_id, **kwargs):
#                return self._reference(b, b_id=b_id, restriction=restriction, 
#                    order=order, limit=limit, **kwargs)
#            setattr(self, name, _f)
#            return _f
#        else:
#            raise AttributeError, 'Name %s does not exist' % name
        
#    def foreign(self, b):
#        r = self._reference(b, None)
#        if r:
#            try:
#                return r.next()
#            except StopIteration:
#                return None
#    
#    def reference(self, b, restriction=None, order=None, limit=None, **kwargs):
#        return self._reference(b, None, restriction, order, limit, **kwargs)
#    
#    def _reference(self, b, b_id=None, restriction=None, order=None, limit=None, **kwargs):
#        from geniusql import logic
#        condition = None
#        if restriction:
#            condition = logic.Expression(restriction)
#        if not issubclass(b, Model):
#            raise ModelInstanceException("First argument must be Model class")
#        #find reference between a and b
#        b_id = b_id
#        ref_flag = None
#        if not b_id:
#            c = None
#            d = {}
#            #B -> A (B has a reference to A)
#            for k, v in b.table.references.items():
#                if v[1] == self.tablename:
#                    b_id = v[0]
#                    d = {b_id:self.id}
#                    ref_flag = 'B->A'
#                    break
#            #A -> B (A has a reference to B)
#            if not ref_flag:
#                for k, v in self.table.references.items():
#                    if v[1] == b.tablename:
#                        b_id = v[2]
#                        d = {b_id:getattr(self, v[0], None)}
#                        ref_flag = 'A->B'
#                        break
#        else:
#            d = {b_id:self.id}
#            
#        if b_id:
#            c = logic.filter(**d)
#            if condition:
#                condition = condition + c
#            else:
#                condition = c
#            cls = b
#            for obj in cls.table._select_lazy(condition, order, limit, **kwargs):
#                o = cls(**obj)
#                o._set_saved()
#                yield o
#        else:
#            raise StopIteration

    def __repr__(self):
        s = []
        for k, v in self._fields_list:
            s.append('%r:%r' % (k, getattr(self, k, None)))
        return ('<%s {' % self.__class__.__name__) + ','.join(s) + '}>'
           
    #classmethod========================================================

    @classmethod
    def _set_tablename(cls, appname=None):
        if not hasattr(cls, '__tablename__'):
            name = cls.__name__.lower()
        else:
            name = cls.__tablename__
        if appname:
            name = appname.lower() + '_' + name
        cls.tablename = name
        
    @classmethod
    def bind(cls, db=None, auto_create=False, force=False):
        cls._lock.acquire()
        try:
            if not db and not __default_connection__:
                return
            if not hasattr(cls, '_created') or force:
                cls.db = db or get_connection()
                cls.schema = schema = cls.db._schema
                cls.table = table = schema.table(cls.tablename)
                for k, f in cls.properties.items():
                    args = {}
                    args['dbtype'] = f.kwargs.get('dbtype', None)
                    args['default'] = f.default_value()
                    args['key'] = f.kwargs.get('key', None)
                    args['autoincrement'] = f.kwargs.get('autoincrement', None)
                    args['hints'] = hints = f.kwargs.get('hints', {})
                    
                    if f.max_length:
                        if f.data_type is float or f.data_type is decimal.Decimal:
                            hints['precision'] = f.max_length
                            scale = f.kwargs.get('scale', None)
                            if scale:
                                hints['scale'] = scale
                        else:
                            hints['bytes'] = f.max_length
                            
                    column = schema.column(f.data_type, **args)
                    table[k] = column
#                    if isinstance(f, Reference):
#                        cls.add_reference(k, f.tablename, f.ref_field)
                dict.__setitem__(schema, cls.tablename, table)
                if auto_create:
                    cls.create(migirate=True)
                table.created = True
                cls._created = True
        finally:
            cls._lock.release()
            
    @classmethod
    def is_existed(cls):
        try:
            cls.schema._get_table(cls.tablename)
            return True
        except geniusql.errors.MappingError:
            return False
    
    @classmethod
    def create(cls, force=False, migirate=False):
        cls._c_lock.acquire()
        try:
            f = cls.is_existed()
            if not f or (f and force):
                cls.table.create()
            if f and migirate and not force:
                migirate_table(cls.table, cls.schema)
        finally:
            cls._c_lock.release()
            
#    @classmethod
#    def add_reference(cls, fieldname, tablename, ref_field):
#        cls.table.references[tablename] = (fieldname, tablename, ref_field)
#        cls.table.add_index(fieldname)
        
    @classmethod
    def get(cls, restriction=None, **kwargs):
        if isinstance(restriction, int):
            obj = cls.table.select(id=restriction)
        else:
            obj = cls.table.select(restriction, **kwargs)
        o = None
        if obj:
            o = cls(**obj)
            o._set_saved()
        return o
    
    @classmethod
    def filter(cls, restriction=None, order=None, limit=None, **kwargs):
        for obj in cls.table._select_lazy(restriction, order, limit, **kwargs):
            o = cls(**obj)
            o._set_saved()
            yield o
            
    @classmethod
    def remove(cls, restriction=None, **kwargs):
        if isinstance(restriction, int):
            obj = cls.table.delete(id=restriction)
        else:
            obj = cls.table.delete_all(restriction, **kwargs)
            
def migirate_table(table, schema):
    def compare_column(a, b):
        return ((a.pytype is b.pytype) and (a.dbtype.__class__.__name__ == b.dbtype.__class__.__name__)
            and (a.default == b.default) and (a.key == b.key))

    t = schema.discover(table.name)
    
    for k, v in table.items():
        if k in t:
            if not compare_column(v, t[k]):
                table[k] = v
            dict.__delitem__(t, k)
        elif not k in t:
            table._add_column(v)
    for k, v in t.items():
        del t[k]
    
if __name__ == '__main__':
    set_debug_log(True)
    set_auto_bind(True)         #auto bind table to db and schema
    set_auto_migirate(True)     #if you changed model, then automatically change the table

    db = get_connection('sqlite')
    db.create()
    
    class Test(Model):
        username = Field(str)
        year = Field(int)
        salery = Field(decimal.Decimal, max_length=16)
    
    Test.table.insert(username='tttttt')
    Test(username='limodou').save() #use nomally insert
    Test(username='xxxxxxx').save()
    print list(Test.filter())       #filter will return a generator of Test instance
    t = Test(username='zoom', year=30)  #or create an table instance
    t.put()         #save it
    print list(Test.filter())
    t.username += 'add'
    print t
    t.delete()  #remove an object from table
    print list(Test.filter())
    t = Test.get(username='limodou')    #get a single object
    print t
    
#    class Test(Model):
#        username = Field(str)
#        year = Field(int)
#        age = Field(int)
#        
#    print list(Test.select_all())
