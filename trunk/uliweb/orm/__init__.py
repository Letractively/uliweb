# This module is used for wrapping SqlAlchemy to a simple ORM
# Author: limodou <limodou@gmail.com>
# 2008.06.11


__all__ = ['Field', 'get_connection', 'Model', 'migrate_table',
    'set_auto_bind', 'set_auto_migrate', 'set_debug_query', 
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
__auto_migrate__ = False
__debug_query__ = None

import decimal
import threading
import datetime
from sqlalchemy import *

class Error(Exception):pass
class ReservedWordError(Error):pass
class ModelInstanceError(Error):pass
class DuplicatePropertyError(Error):
  """Raised when a property is duplicated in a model definition."""
class BadValueError(Error):pass
class KindError(Error):pass
class ConfigurationError(Error):pass

_SELF_REFERENCE = object()

def set_auto_bind(flag):
    global __auto_bind__
    __auto_bind__ = flag
    
def set_auto_migrate(flag):
    global __auto_migrate__
    __auto_migrate__ = flag
    
def set_debug_query(flag):
    global __debug_query__
    __debug_query__ = flag

def get_connection(connection='', default=True, debug=None, **args):
    global __default_connection__
    if debug is None:
        debug = __debug_query__
    
    if default and __default_connection__:
        return __default_connection__
    
    db = create_engine(connection, strategy='threadlocal')
    if default:
        __default_connection__ = db
    if debug:
        db.echo = debug
    metadata = MetaData(db)
    db.metadata = metadata
    return db

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
        if name == 'Model':
            return
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
                attr.__property_config__(cls, attr_name)
                
        if 'id' not in cls.properties:
            cls.properties['id'] = f = Field(int, autoincrement=True, key=True)
            f.__property_config__(cls, 'id')
            setattr(cls, 'id', f)

        fields_list = [(k, v) for k, v in cls.properties.items()]
        fields_list.sort(lambda x, y: cmp(x[1].creation_counter, y[1].creation_counter))
        cls._fields_list = fields_list
        
        if __auto_bind__:
            cls.bind(auto_create=__auto_migrate__)
        
class Property(object):
    data_type = str
    field_class = String
    creation_counter = 0

    def __init__(self, verbose_name=None, name=None, default=None,
         required=False, validator=None, choices=None, max_length=None, **kwargs):
        self.verbose_name = verbose_name
        self.property_name = None
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
        
    def create(self):
        args = self.kwargs.copy()
        args['key'] = self.name
        args['default'] = self.default_value()
        args['primary_key'] = self.kwargs.pop('key', False)
        args['autoincrement'] = self.kwargs.pop('autoincrement', False)
        args['index'] = self.kwargs.pop('index', False)
        args['unique'] = self.kwargs.pop('unique', False)
        args['nullable'] = self.kwargs.pop('nullable', True)
        f_type = self._create_type()
        return Column(self.property_name, f_type, **args)

    def _create_type(self):
        if self.max_length:
            f_type = self.field_class(self.max_length)
        else:
            f_type = self.field_class
        return f_type
    
    def __property_config__(self, model_class, property_name):
        self.model_class = model_class
        self.property_name = property_name
        if not self.name:
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
        if isinstance(value, unicode):
            return value.encode('utf-8')
        else:
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
    field_class = String
    
    def empty(self, value):
        return not value

class UnicodeProperty(StringProperty):
    data_type = unicode
    field_class = Unicode
    
    def convert(self, value):
        if isinstance(value, str):
            return unicode(value, 'utf-8')
        else:
            return self.data_type(value)
    
class TextProperty(StringProperty):
    field_class = Text
    
class BlobProperty(StringProperty):
    field_class = BLOB
    
class DateTimeProperty(Property):
    data_type = datetime.datetime
    field_class = DateTime
    
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
    field_class = Date
    
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
    field_class = Time
    
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
    field_class = Integer
    
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
    field_class = Float
    
    def __init__(self, verbose_name=None, default=0.0, **kwds):
        super(FloatProperty, self).__init__(verbose_name, default=default, **kwds)
   
    def _create_type(self):
        if self.max_length:
            precision = self.max_length
        if self.kwargs.get('precision', None):
            precision = self.kwargs.pop('precision')
        length = 2
        if self.kwargs.get('length', None):
            length = self.kwargs.pop('length')
        
        f_type = self.field_class(**dict(precision=precision, length=length))
        return f_type
    
    def validate(self, value):
        value = super(FloatProperty, self).validate(value)
        if value is not None and not isinstance(value, float):
            raise BadValueError('Property %s must be a float' % self.name)
        return value
    
class DecimalProperty(Property):
    """A float property."""

    data_type = decimal.Decimal
    field_class = Numeric
    
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
    field_class = Boolean
    
    def __init__(self, verbose_name=None, default=False, **kwds):
        super(BooleanProperty, self).__init__(verbose_name, default=default, **kwds)
    
    def validate(self, value):
        value = super(BooleanProperty, self).validate(value)
        if value is not None and not isinstance(value, bool):
            raise BadValueError('Property %s must be a bool' % self.name)
        return value

class PickleProperty(Property):
    data_type = None
    field_class = PickleType

    def validate(self, value):
        return value
    
#    def get_value_for_datastore(self, model_instance):
#        value = super(TimeProperty, self).get_value_for_datastore(model_instance)
#        if value is not None:
#            import cPickle
#            value = cPickle.loads(value)
#        return value
#
#    def make_value_from_datastore(self, value):
#        if value is not None:
#            import cPickle
#            value = cPickle.dumps(value)
#        return value
    
class FileProperty(Property):
    data_type = None
    field_class = BLOB
    
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
    field_class = Integer

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
        
    def create(self):
        args = self.kwargs.copy()
        args['key'] = self.name
        args['default'] = self.default_value()
        args['primary_key'] = self.kwargs.pop('key', False)
        args['autoincrement'] = self.kwargs.pop('autoincrement', False)
        args['index'] = self.kwargs.pop('index', False)
        args['unique'] = self.kwargs.pop('unique', False)
        args['nullable'] = self.kwargs.pop('nullable', True)
        f_type = self._create_type()
        return Column(self.property_name, f_type, ForeignKey("%s.id" % self.reference_class.tablename), **args)
    
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
                d = self.reference_class.c[id_field]
                instance = self.reference_class.get(d==reference_id)
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
                d = self.__model.c[self.__reference_id]
                return self.__model.filter(d==_id)
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
                if isinstance(v, DateTimeProperty) and v.auto_now:
                    d[k] = v.default_value()
                if (x is not None and t is not None) and repr(t) != repr(x):
                    d[k] = x
        
        return d
            
    def is_saved(self):
        return bool(self.id) 
            
    def put(self):
        d = self._get_data()
        if d:
            if not self.id:
                obj = self.table.insert().execute(**d)
                setattr(self, 'id', obj.lastrowid)
            else:
                self.table.update(self.table.c.id == self.id).execute(**d)
            self._set_saved()
        return self
    
    save = put
    
    def delete(self):
        self.table.delete(self.table.c.id==self.id).execute()
        self.id = None
        self._old_values = {}
            
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
            if __auto_migrate__:
                import migrate.changeset
                
            if not hasattr(cls, '_created') or force:
                cls.db = db or get_connection()
                cls.metadata = metadata = cls.db.metadata
#                cls.table = table = schema.table(cls.tablename)
                cols = []
                for k, f in cls.properties.items():
                    cols.append(f.create())
                cls.table = Table(cls.tablename, metadata, *cols)
                
                if auto_create:
                    cls.create(migrate=__auto_migrate__)
                cls.c = cls.table.c
                cls.columns = cls.table.c
                cls._created = True
        finally:
            cls._lock.release()
            
    @classmethod
    def create(cls, migrate=False):
        cls._c_lock.acquire()
        try:
            if not cls.table.exists():
                cls.table.create(checkfirst=True)
            else:
                if migrate:
                    migrate_table(cls.table)
        finally:
            cls._c_lock.release()
            
    @classmethod
    def get(cls, condition=None, **kwargs):
        if isinstance(condition, int):
            for obj in cls.filter(cls.c.id==condition):
                return obj
        else:
            for obj in cls.filter(condition):
                return obj
    
    @classmethod
    def all(cls):
        r = cls.table.select().execute()
        for obj in r:
            d = [(str(x), y) for x, y in obj.items()]
            o = cls(**dict(d))
            o._set_saved()
            yield o
        
    @classmethod
    def filter(cls, condition=None, **kwargs):
        r = select([cls.table], condition, **kwargs).execute()
        for obj in r:
            d = [(str(x), y) for x, y in obj.items()]
            o = cls(**dict(d))
            o._set_saved()
            yield o
            
    @classmethod
    def remove(cls, condition=None, **kwargs):
        if isinstance(condition, int):
            cls.table.delete(cls.c.id==condition, **kwargs).execute()
        if isinstance(condition, (tuple, list)):
            cls.table.delete(cls.c.id.in_(condition)).execute()
        else:
            cls.table.delete(condition, **kwargs).execute()
            
    @classmethod
    def count(cls, condition=None, **kwargs):
        obj = cls.table.count(condition, **kwargs).execute()
        count = 0
        if obj:
            r = obj.fetchone()
            if r:
                count = r[0]
        else:
            count = 0
        return count
            
def migrate_table(table):
    def compare_column(a, b):
        return ((a.key == b.key) 
#            and issubclass(b.type.__class__, a.type.__class__)
            and (bool(a.nullable) == bool(b.nullable))
            and (bool(a.primary_key) == bool(b.primary_key))
            )
    
    metadata = MetaData(table.bind)
    _t = Table(table.name, metadata, autoload=True)
    t = {}
    for k in _t.c.keys():
        t[k] = _t.c[k]
    for k in table.c.keys():
        v = table.c[k]
        if k in t:
            if not compare_column(v, t[k]):
                t[k].alter(v)
            del t[k]
        elif not k in t:
            r = v.copy()
            r.create(_t)
    for k, v in t.items():
        t[k].drop()

if __name__ == '__main__':
#    set_debug_query(True)
    set_auto_bind(True)         #auto bind table to db and schema
    set_auto_migrate(True)     #if you changed model, then automatically change the table
    get_connection('sqlite://')
    
    class Test(Model):
        username = Field(str)
        year = Field(int)
        
    class Test1(Model):
        test = Reference(Test)
        name = Field(str)
        
    a1 = Test(username='limodou1').save() #use nomally insert
    a2 = Test(username='limodou2').save() #use nomally insert
    a3 = Test(username='limodou3').save() #use nomally insert
    
    b1 = Test1(name='zoom', test=a1).save()
    b2 = Test1(name='aaaa', test=a1).save()
    b3 = Test1(name='bbbb', test=a2).save()
#    print a
#    a.username = 'zoom'
#    a.save()
#    print a
#    a.delete()
#    for o in Test.filter(order_by=[desc(Test.c.username)]):
#        print o
#        
#    print b2.test.username
    for o in a1.test1_set:
        print o
#    for k in Test1.filter():
#        print k
