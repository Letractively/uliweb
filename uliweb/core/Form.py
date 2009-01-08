#coding=utf-8
import os
import cgi
import datetime
import time

DEFAULT_FORM_CLASS = 'form'
DEFAULT_CHARSET = 'utf-8'
REQUIRED_CAPTION = '(*)'

__id = 0

def capitalize(s):
    t = s.split('_')
    return ' '.join([x.capitalize() for x in t])

def get_id():
    global __id
    __id += 1
    return __id

class D(dict):
    def __getattr__(self, key): 
        try: 
            return self[key]
        except KeyError, k: 
            return None
        
    def __setattr__(self, key, value): 
        self[key] = value
        
    def __delattr__(self, key):
        try: 
            del self[key]
        except KeyError, k: 
            raise AttributeError, k

###############################################################
# Validator
###############################################################

class ValidationError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)

def _get_choices_keys(choices):
    if isinstance(choices, dict):
        keys = set(choices.keys())
    elif isinstance(choices, (list, tuple)):
        keys = set([])
        for v in choices:
            if isinstance(v, (list, tuple)):
                keys.add(v[0])
            else:
                keys.add(v)
    else:
        raise ValidationError, 'Choices need a dict, tuple or list data.'
    return keys

def IS_IN_SET(choices, error_message='Select a valid choice. That choice is not one of the available choices.'):
    '''
    choices should be a list or a tuple, e.g. [1,2,3]
    '''
    def f(data, all_data=None):
        if data not in _get_choices_keys(choices):
            raise ValidationError, error_message
    return f

def IS_NUMBER(error_message='Please enter an integer'):
    def f(data, all_data=None):
        if not data.isdigit():
            raise ValidationError, error_message
    return f

##################################################################
#  HTML Helper
##################################################################

def _str(v, encoding=None):
    if not encoding:
        encoding = DEFAULT_CHARSET
    if isinstance(v, str):
        pass
    elif isinstance(v, unicode):
        v = v.encode(encoding)
    else:
        v = str(v)
    return v

def _create_kwargs(args, nocreate_if_none=['id', 'for']):
    """
    Make python dict to k="v" format
    
    >>> print _create_kwargs({'name':'title'})
     name="title"
    >>> print _create_kwargs({'_class':'color', 'id':'title'})
     class="color" id="title"
    >>> print _create_kwargs({'_class':'color', 'id':None})
     class="color"
    >>> print _create_kwargs({'_class':'color', 'checked':None})
     class="color" checked
    >>> print _create_kwargs({'_class':'color', '_for':None})
     class="color"
    
    """
    if not args:
        return ''
    s = ['']
    for k, v in args.items():
        if k.startswith('_'):
            k = k[1:]
        if v is None:
            if k not in nocreate_if_none:
                s.append(k)
        else:
            s.append('%s="%s"' % (k, cgi.escape(_str(v))))
    return ' '.join(s)

class Buf(object):
    def __init__(self, begin='', end=''):
        self.buf = []
        self.begin = begin
        self.end = end

    def __lshift__(self, obj):
        if obj:
            if isinstance(obj, (tuple, list)):
                self.buf.extend(obj)
            else:
                self.buf.append(obj)
                obj = [obj]
            return obj[0]
        else:
            return None

    def __str__(self):
        return self.html()

    def html(self):
        s = [self.begin]
        s.extend(self.buf)
        s.append(self.end)
        s = filter(None, s)
        return '\n'.join([str(x) for x in s])

class Tag(Buf):
    """
    Creating a tag. For example:
        
        >>> print Tag('br/').html()
        <br/>
        >>> print Tag('a', 'Hello', href="/")
        <a href="/">
        Hello
        </a>
    """
    def __init__(self, tag, *children, **args):
        self.tag = tag
        self.buf = list(children)
        if tag.endswith('/'):
            self.begin = '<%s%s>' % (tag, _create_kwargs(args))
            self.end = ''
        else:
            self.begin = '<%s%s>' % (tag, _create_kwargs(args))
            self.end = '</%s>' % tag

    def html(self):
        if not self.tag.endswith('/'):
            b = '\n'.join([_str(x) for x in self.buf])
            if not b:
                s = [self.begin+self.end]
            else:
                s = [self.begin, b, self.end]
        else:
            s = [self.begin]
        return '\n'.join(s)

class Build(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def html(self):
        raise Exception, 'Not implemented'

    def __str__(self):
        return self.html()

class Text(Build):
    type = 'text'

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def html(self):
        args = self.kwargs.copy()
        args.setdefault('type', self.type)
        return str(Tag('input', **args))

class Password(Text): type = 'password'
class TextArea(Build):
    def __init__(self, value='', **kwargs):
        self.kwargs = kwargs
        self.value = value

    def html(self):
        args = self.kwargs
        args.setdefault('rows', 5)
        args.setdefault('cols', 40)
        return str(Tag('textarea', self.value, **args))
class Hidden(Text): type = 'hidden'
class Button(Text): type = 'button'
class Submit(Text): type = 'submit'
class Reset(Text): type = 'reset'
class File(Text): type = 'file'
class Radio(Text): type = 'radio'
class Select(Build):
    def __init__(self, choices, value=None, **kwargs):
        self.choices = choices
        self.value = value
        self.kwargs = kwargs

    def html(self):
        s = []
        for v, caption in self.choices:
            args = {'value': v}
            if v == self.value:
                args['selected'] = None
            s.append(str(Tag('option', caption, **args)))
        return str(Tag('select', '\n'.join(s), **self.kwargs))
    
class RadioSelect(Select):
    _id = 0
    def __init__(self, choices, value=None, **kwargs):
        Select.__init__(self, choices, value, **kwargs)

    def html(self):
        s = []
        for v, caption in self.choices:
            args = {'value': v}
            id = args.setdefault('id', 'radio_%d' % self.get_id())
            args['name'] = self.kwargs.get('name')
            if v == self.value:
                args['checked'] = None
            s.append(str(Radio(**args)))
            s.append(str(Tag('label', caption, _for=id)))
        return ''.join(s)
    
    def get_id(self):
        RadioSelect._id += 1
        return self._id
    
class Checkbox(Build):
    def __init__(self, value=False, **kwargs):
        self.value = value
        self.kwargs = kwargs

    def html(self):
        args = self.kwargs.copy()
        if self.value:
            args.setdefault('checked', None)
        args.setdefault('type', 'checkbox')
        return str(Tag('input', **args))

###############################################################
# Form Helper
###############################################################

class BaseField(object):
    default_build = Text
    field_css_class = 'field'
    default_validators = []
    default_datatype = None
    creation_counter = 0

    def __init__(self, label='', default=None, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, datatype=None, multiple=False, idtype=None, **kwargs):
        self.label = label
        self._default = default
        self.validators = validators or []
        self.name = name
        self.required = required
        self.kwargs = kwargs
        self.html_attrs = html_attrs or {}
        self.datatype = datatype or self.default_datatype
        self.idtype = idtype
        if '_class' in self.html_attrs:
            self.html_attrs['_class'] = ' '.join([self.html_attrs['_class'], self.field_css_class])
        else:
            self.html_attrs['_class'] = ' '.join([self.field_css_class])
        
        self.multiple = multiple
        self.build = build or self.default_build
        self.help_string = help_string
        BaseField.creation_counter += 1
        self.creation_counter = BaseField.creation_counter
        if 'id' in self.kwargs:
            self._id = self.kwargs.pop('id')
        else:
            self._id = None

    def _get_default(self):
        return self._default
    default = property(_get_default)
    
    def to_python(self, data):
        """
        Convert a data to python format. 
        """
        if data is None:
            return data
        if self.datatype:
            return self.datatype(data)
        else:
            return data

    def html(self, data='', py=True):
        """
        Convert data to html value format.
        """
        if py:
            value = self.to_html(data)
        else:
            value = data
        return str(self.build(name=self.name, value=value, id=self.id, **self.html_attrs))

    def get_label(self, **kwargs):
        if not self.label:
            label = capitalize(self.name)
        else:
            label = self.label
        if self.required:
            label += str(Tag('span', REQUIRED_CAPTION, _class='field_required'))
        return str(Tag('label', label, _for=self.id, **kwargs))
    
    @property
    def id(self):
        if self._id:
            return self._id
        else:
            if self.idtype == 'name':
                id = 'field_' + self.name
            elif self.idtype:
                id = 'field_' + str(get_id())
            else:
                id = None
            return id
        
    def parse_data(self, request, all_data):
        if self.multiple:
            all_data[self.name] = request.getall(self.name)
        else:
            all_data[self.name] = request.get(self.name, None)

    def get_data(self, all_data):
        return all_data.get(self.name, None)

    def to_html(self, data):
        return _str(data)

    def validate(self, data, all_data=None):
        if isinstance(data, cgi.FieldStorage):
            if data.file:
                v = data.filename
            else:
                raise Exception, 'Unsupport type %s' % type(data)
        else:
            v = data
        if not v:
            if not self.required:
                return True, self.default
#                if self.default is not None:
#                    return True, self.default
#                else:
#                    return True, data
            else:
                return False, 'This field is required.'
        try:
            if isinstance(data, list):
                v = []
                for i in data:
                    v.append(self.to_python(i))
                data = v
            else:
                data = self.to_python(data)
        except:
            return False, "Can't convert %r to %s." % (data, self.__class__.__name__)
        try:
            for v in self.default_validators + self.validators:
                v(data, all_data)
        except ValidationError, e:
            return False, e.message
        return True, data
    
class StringField(BaseField):
    """
    >>> a = StringField(name='title', label='Title:', required=True, id='field_title')
    >>> print a.html('Test')
    <input class="field" type="text" id="field_title" value="Test" name="title"></input>
    >>> print a.get_label()
    <label for="field_title">
    Title:<span class="field_required">
    (*)
    </span>
    </label>
    >>> a.validate('')
    (False, 'This field is required.')
    >>> a.validate('Hello')
    (True, 'Hello')
    >>> a.to_python('Hello')
    'Hello'
    >>> a = StringField(name='title', label='Title:', required=True)
    >>> print a.html('')
    <input class="field" type="text" value="" name="title"></input>
    >>> print a.get_label()
    <label>
    Title:<span class="field_required">
    (*)
    </span>
    </label>
    >>> a.idtype = 'name'
    >>> print a.html('')
    <input class="field" type="text" id="field_title" value="" name="title"></input>
    >>> print a.get_label()
    <label for="field_title">
    Title:<span class="field_required">
    (*)
    </span>
    </label>
    
    """
    default_datatype = str
    def __init__(self, label='', default='', required=False, validators=None, name='', html_attrs=None, help_string='', build=None, **kwargs):
        BaseField.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)

class UnicodeField(BaseField):
    """
    >>> a = UnicodeField(name='title', label='Title:', required=True, id='field_title')
    >>> print a.html('Test')
    <input class="field" type="text" id="field_title" value="Test" name="title"></input>
    >>> print a.get_label()
    <label for="field_title">
    Title:<span class="field_required">
    (*)
    </span>
    </label>
    >>> a.validate('')
    (False, 'This field is required.')
    >>> a.validate('Hello')
    (True, u'Hello')
    >>> a.to_python('Hello')
    u'Hello'
    >>> a.to_python('中国')
    u'\u4e2d\u56fd'
    
    """
    def __init__(self, label='', default='', required=False, validators=None, name='', html_attrs=None, help_string='', build=None, encoding='utf-8', **kwargs):
        BaseField.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)
        self.encoding = encoding

    def to_python(self, data):
        """
        Convert a data to python format. 
        """
        if data is None:
            return data
        return unicode(data, self.encoding)
  
class PasswordField(StringField):
    """
    >>> a = PasswordField(name='password', label='Password:', required=True, id='field_password')
    >>> print a.html('Test')
    <input class="field" type="password" id="field_password" value="Test" name="password"></input>
    
    """
    default_build = Password

class HiddenField(StringField):
    """
    >>> a = HiddenField(name='id', id='field_id')
    >>> print a.html('Test')
    <input class="field" type="hidden" id="field_id" value="Test" name="id"></input>
    
    """
    default_build = Hidden

class ListField(StringField):
    """
    >>> a = ListField(name='list', id='field_list')
    >>> print a.html(['a', 'b'])
    <input class="field" type="text" id="field_list" value="a b" name="list"></input>
    >>> print a.validate('a b')
    (True, ['a', 'b'])
    >>> print a.validate('')
    (True, [])
    >>> a = ListField(name='list', id='field_list', delimeter=',')
    >>> print a.validate('a,b,c')
    (True, ['a', 'b', 'c'])
    >>> a = ListField(name='list', id='field_list', delimeter=',', datatype=int)
    >>> print a.validate('1,b,c')
    (False, "Can't convert '1,b,c' to ListField.")
    >>> print a.validate('1,2,3')
    (True, [1, 2, 3])
    
    """
    def __init__(self, label='', default=None, required=False, validators=None, name='', delimeter=' ', html_attrs=None, help_string='', build=None, datatype=str, **kwargs):
        BaseField.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)
        self.delimeter = delimeter
        self._default = default or []
        self.datatype = datatype

    def to_python(self, data):
        return [self.datatype(x) for x in data.split(self.delimeter)]

    def to_html(self, data):
        return self.delimeter.join([_str(x) for x in data])

class BooleanField(BaseField):
    """
    >>> a = BooleanField(name='bool', id='field_bool')
    >>> print a.html('Test')
    <input checked class="field" type="checkbox" name="bool" id="field_bool"></input>
    >>> print a.validate('on')
    (True, True)
    >>> print a.validate('')
    (True, False)
    >>> print a.validate(None)
    (True, False)
    
    """
    default_build = Checkbox

    def __init__(self, label='', default=False, name='', html_attrs=None, help_string='', build=None, **kwargs):
        BaseField.__init__(self, label=label, default=default, required=False, validators=None, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)

    def to_python(self, data):
        if data.lower() in ('on', 'true', 'yes', 'ok'):
            return True
        else:
            return False

    def html(self, data, py=True):
        if data:
            return str(self.build(checked=None, id='field_'+self.name, name=self.name, **self.html_attrs))
        else:
            return str(self.build(id='field_'+self.name, name=self.name, **self.html_attrs))

    def to_html(self, data):
        if data is True:
            return 'on'
        else:
            return ''

class TextField(StringField):
    """
    >>> a = TextField(name='text', id='field_text')
    >>> print a.html('Test')
    <textarea id="field_text" rows="5" class="field" name="text" cols="40">
    Test
    </textarea>
    
    """
    default_build = TextArea

    def __init__(self, label='', default='', required=False, validators=None, name='', html_attrs=None, help_string='', build=None, rows=5, cols=40, **kwargs):
        BaseField.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)
        self.rows = rows
        self.cols = cols
        
    def html(self, data='', py=True):
        if py:
            value = self.to_html(data)
        else:
            value = data
        return str(self.build(self.to_html(data), id='field_'+self.name, name=self.name, **self.html_attrs))

class IntField(BaseField):
    """
    >>> a = IntField(name='int', id='field_int')
    >>> print a.html('Test')
    <input class="field" type="text" id="field_int" value="Test" name="int"></input>
    >>> print a.validate('')
    (True, 0)
    >>> print a.validate(None)
    (True, 0)
    >>> print a.validate('aaaa')
    (False, "Can't convert 'aaaa' to IntField.")
    >>> print a.validate('122')
    (True, 122)
    >>> a = BaseField(name='int', id='field_int', datatype=int)
    >>> print a.html('Test')
    <input class="field" type="text" id="field_int" value="Test" name="int"></input>
    >>> print a.validate('122')
    (True, 122)

    """
    def __init__(self, label='', default=0, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, **kwargs):
        BaseField.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)

    def to_python(self, data):
        return int(data)

    def to_html(self, data):
        return str(data)

class SelectField(BaseField):
    """
    >>> a = SelectField(name='select', id='field_select', default='a', choices=[('a', 'AAA'), ('b', 'BBB')])
    >>> print a.html('a')
    <select class="field" name="select" id="field_select">
    <option selected value="a">
    AAA
    </option>
    <option value="b">
    BBB
    </option>
    </select>
    >>> print a.validate('')
    (True, 'a')
    >>> print a.validate('aaaaaaa')
    (False, 'Select a valid choice. That choice is not one of the available choices.')
    >>> print a.validate('b')
    (True, 'b')
    >>> a = SelectField(name='select', id='field_select', choices=[(1, 'AAA'), (2, 'BBB')], datatype=int)
    >>> print a.validate('')
    (True, 1)
    >>> print a.validate('2')
    (True, 2)
    """
    default_build = Select

    def __init__(self, label='', default=None, choices=None, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, **kwargs):
        BaseField.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)
        self.choices = choices or []
        if self.choices:
            self._default = default or self.choices[0][0]
        self.validators.append(IS_IN_SET(self.choices))

    def html(self, data, py=True):
        if py:
            value = self.to_html(data)
        else:
            value = data
        return str(self.build(self.choices, data, id=self.id, name=self.name, **self.html_attrs))

class RadioSelectField(SelectField):
    """
    >>> a = RadioSelectField(name='select', id='field_select', default='a', choices=[('a', 'AAA'), ('b', 'BBB')])
    >>> print a.html('a')
    <input checked type="radio" id="radio_1" value="a" name="select"></input><label for="radio_1">
    AAA
    </label><input type="radio" id="radio_2" value="b" name="select"></input><label for="radio_2">
    BBB
    </label>
    >>> print a.validate('')
    (True, 'a')
    >>> print a.validate('aaaaaaa')
    (False, 'Select a valid choice. That choice is not one of the available choices.')
    >>> print a.validate('b')
    (True, 'b')
    
    """
    default_build = RadioSelect
    
class FileField(BaseField):
    """
    >>> a = FileField(name='file', id='field_file')
    >>> print a.html('a')
    <input class="field" type="file" id="field_file" name="file"></input>
    """
    
    default_build = File
    
    def to_python(self, data):
        d = D({})
        d['filename'] = data.filename
        d['file'] = data.file
        data.file.seek(0, os.SEEK_END)
        d['length'] = data.file.tell()
        data.file.seek(0, os.SEEK_SET)
        return d
    
    def html(self, data, py=True):
        if py:
            value = self.to_html(data)
        else:
            value = data
        return str(self.build(name=self.name, id=self.id, **self.html_attrs))
    
DEFAULT_DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d',  # '2006-10-25', '10/25/2006', '10/25/06'
    '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'
)
class DateField(StringField):
    """
    >>> a = DateField(name='date', id='field_date')
    >>> print a.html(datetime.date(2009, 1, 1))
    <input class="field field_date" type="text" id="field_date" value="2009-01-01" name="date"></input>
    >>> print a.validate('2009-01-01')
    (True, datetime.date(2009, 1, 1))
    >>> print a.validate('2009/01/01')
    (True, datetime.date(2009, 1, 1))
    >>> a = DateField(name='date', id='field_date', default='now')
    """
    field_css_class = 'field field_date'

    def __init__(self, label='', default=None, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, format=None, **kwargs):
        BaseField.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)
        if not format:
            self.formats = DEFAULT_DATE_INPUT_FORMATS
        else:
            self.formats = format
            if not isinstance(format, (list, tuple)):
                self.formats = [format]

    def _get_default(self):
        if self._default == 'now':
            return datetime.date(*datetime.datetime.now().timetuple()[:3])
        else:
            return self._default
    default = property(_get_default)

    def to_python(self, data):
        for format in self.formats:
            try:
                return datetime.date(*time.strptime(data, format)[:3])
            except ValueError:
                continue
        raise ValidationError, "The data is not a valid data format."
    
    def to_html(self, data):
        if data:
            return data.strftime(self.formats[0])
        else:
            return ''
    
DEFAULT_TIME_INPUT_FORMATS = (
    '%H:%M:%S',     # '14:30:59'
    '%H:%M',        # '14:30'
)
class TimeField(StringField):
    """
    >>> a = TimeField(name='time', id='field_time')
    >>> print a.html(datetime.time(14, 30, 59))
    <input class="field field_time" type="text" id="field_time" value="14:30:59" name="time"></input>
    >>> print a.validate('14:30:59')
    (True, datetime.time(14, 30, 59))
    >>> print a.validate('14:30')
    (True, datetime.time(14, 30))
    >>> print a.validate('')
    (True, None)
    >>> a = TimeField(name='time', id='field_time', default='now')
    """
    field_css_class = 'field field_time'
    
    def __init__(self, label='', default=None, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, format=None, **kwargs):
        BaseField.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)
        if not format:
            self.formats = DEFAULT_TIME_INPUT_FORMATS
        else:
            self.formats = format
            if not isinstance(format, (list, tuple)):
                self.formats = [format]
        self._default = default

    def _get_default(self):
        if self._default == 'now':
            return datetime.time(*datetime.datetime.now().timetuple()[3:6])
        else:
            return self._default
    default = property(_get_default)
    
    def to_python(self, data):
        for format in self.formats:
            try:
                return datetime.time(*time.strptime(data, format)[3:6])
            except ValueError:
                continue
        raise ValidationError, "The data is not a valid time format."
    
    def to_html(self, data):
        if data:
            return data.strftime(self.formats[0])
        else:
            return ''

class FormMetaclass(type):
    def __new__(cls, name, bases, attrs):
        fields = {}
        for field_name, obj in attrs.items():
            if isinstance(obj, BaseField):
                if not obj.name:
                    obj.name = field_name
                fields[field_name] = obj

        f = {}
        for base in bases[::-1]:
            if hasattr(base, 'fields'):
                f.update(base.fields)

        f.update(fields)
        attrs['_fields'] = f

        fields_list = [(k, v) for k, v in fields.items()]
        fields_list.sort(lambda x, y: cmp(x[1].creation_counter, y[1].creation_counter))
        attrs['fields_list'] = fields_list

        return type.__new__(cls, name, bases, attrs)

class Layout(object):
    def __init__(self, form, layout=None):
        self.form = form
        self.layout = layout
        
    def html(self):
        return ''
    
    def __str__(self):
        return self.html()
    
class TableLayout(Layout):
    def line(self, label, input, help_string='', error=None):
        tr = Tag('tr')
        tr << Tag('td', label)
        td = tr << Tag('td', input)
        if error:
            td << Tag('br/')
            td << Tag('span', error, _class='error')
        td = tr << Tag('td', help_string)
        return tr

    def single_line(self, element):
        tr = Tag('tr')
        tr << Tag('td', element, colspan=3)
        return tr

    def buttons_line(self, buttons):
        tr = Tag('tr')
        tr << Tag('td', buttons, colspan=3, _class="buttons")
        return tr
        
    def html(self):
        buf = Buf()
        buf << self.form.form_begin
        table = buf << Tag('table')
        tbody = table << Tag('tbody')

        for name, obj in self.form.fields_list:
            f = self.form.f[name]
            if isinstance(obj, HiddenField):
                tbody << f
            else:
                tbody << self.line(f.label, f, f.help_string, f.error)
        
        tbody << self.buttons_line(self.form.buttons)
        buf << self.form.form_end
        return str(buf)
    
class FieldProxy(object):
    def __init__(self, form, field):
        self.form = form
        self.field = field
        
    @property
    def label(self):
        return self.field.get_label()
    
    @property
    def help_string(self):
        return self.field.help_string
    
    @property
    def error(self):
        return self.form._errors.get(self.field.name, '')
    
    @property
    def html(self):
        default = self.field.to_html(self.field.default)
        return self.field.html(self.form._data.get(self.field.name, default), self.form._py)
    
    def __str__(self):
        return self.html
    
    @property
    def value(self):
        return self.form._data.get(self.field.name, self.field.default)
    
class Form(object):
    """
    >>> class F(Form):
    ...     title = StringField(lable='Title:')
    >>> form = F()
    >>> print form.form_begin
    <form action="" class="form" method="post" enctype="multipart/form-data">
    >>> form = F(action='post')
    >>> print form.form_begin
    <form action="post" class="form" method="post" enctype="multipart/form-data">
    >>> print form.form_end
    </form>
    """

    __metaclass__ = FormMetaclass

    layout_class = TableLayout
    layout = None

    def __init__(self, action='', method='post', buttons='default', 
            validators=None, html_attrs=None, data=None, errors=None, 
            py=True, idtype='name', layout_class=None, **kwargs):
        self.action = action
        self.method = method
        self.kwargs = kwargs
        self._buttons = buttons
        self.validators = validators or []
        self.html_attrs = html_attrs or {}
        self.idtype = idtype
        if layout_class:
            self.layout_class = Form.layout_class
        for name, obj in self.fields_list:
            obj.idtype = self.idtype
        if '_class' in self.html_attrs:
            self.html_attrs['_class'] = self.html_attrs['_class'] + ' ' + DEFAULT_FORM_CLASS
        else:
            self.html_attrs['_class'] = DEFAULT_FORM_CLASS
            
        self.binding(data, errors, py)

    def validate(self, request):
        """
        request should provide get() and getall() functions
        """

        all_data = {}
        for k, v in self._fields.items():
            v.parse_data(request, all_data)

        errors = {}
        new_data = {}

        #gather all fields
        for field_name, field in self._fields.items():
            new_data[field_name] = field.get_data(all_data)

        #validate and gather the result
        result = D({})
        for field_name, field in self._fields.items():
            flag, value = field.validate(new_data[field_name], new_data)
            if not flag:
                if isinstance(value, dict):
                    errors.update(value)
                else:
                    errors[field_name] = value
            else:
                result[field_name] = value

        if self.validators:
            #validate global
            try:
                for v in self.validators:
                    v(new_data)
            except ValidationError, e:
                errors['_'] = e.message

        if errors:
            return False, errors
        else:
            return True, result

    def __str__(self):
        return self.html()
    
    @property
    def form_begin(self):
        args = self.html_attrs.copy()
        args['action'] = self.action
        args['method'] = self.method
        args['enctype'] = "multipart/form-data"
        form = Tag('form', **args)
        return form.begin
    
    @property
    def form_end(self):
        return '</form>'
    
    @property
    def buttons(self):
        if self._buttons == 'default':
            b = Buf()
            b << [Submit(value='Submit'), Reset(value='Reset')]
        else:
            b = self._buttons
        return str(b)
    
    def binding(self, data=None, errors=None, py=True):
        if data is None:
            self._data = {}
        else:
            self._data = data
        if errors is None:
            self._errors = {}
        else:
            self._errors = errors
        if py is None:
            self._py = True
        else:
            self._py = py
        self.f = D({})
        for name, obj in self.fields_list:
            self.f[name] = FieldProxy(self, obj)

    def html(self, data=None, errors=None, layout_class=None, py=True):
        self.binding(data, errors, py)
        cls = layout_class or self.layout_class
        layout = cls(self, self.layout)
        return str(layout)

class CSSLayout(Layout):
    def line(self, obj, label, input, help_string='', error=None):
        div = Tag('div', _class='field')
        if isinstance(obj, BooleanField):
            div << input
            div << label
        else:
            div << label
            div << input
        if error:
            div << Tag('span', error, _class='error')
        return div

    def single_line(self, element):
        div = Tag('div')
        div << element
        return div

    def buttons_line(self, buttons):
        div = Tag('div', _class="buttons")
        div << buttons
        return div

    def html(self):
        buf = Buf()
        buf << self.form.form_begin
        root = buf
    
        for name, obj in self.form.fields_list:
            f = self.form.f[name]
            if isinstance(obj, HiddenField):
                root << f
            else:
                root << self.line(obj, f.label, f, f.help_string, f.error)
        
        root << self.buttons_line(self.form.buttons)
        buf << self.form.form_end
        return str(buf)
    
def test():
    """
    >>> class F(Form):
    ...     title = StringField(label='Title:', required=True, help_string='Title help string')
    ...     content = TextField(label='Content:')
    ...     password = PasswordField(label='Password:')
    ...     age = IntField(label='Age:')
    ...     id = HiddenField()
    ...     tag = ListField(label='Tag:')
    ...     public = BooleanField(label='Public:')
    ...     format = SelectField(label='Format:', choices=[('rst', 'reStructureText'), ('text', 'Plain Text')], default='rst')
    ...     radio = RadioSelectField(label='Radio:', choices=[('rst', 'reStructureText'), ('text', 'Plain Text')], default='rst')
    ...     file = FileField(label='file')
    >>> f = F()
    >>> class F(Form):
    ...     title = StringField(label='Title:', required=True, help_string='Title help string')
    """

#if __name__ == '__main__':
#    import doctest
#    doctest.testmod()
