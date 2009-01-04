#coding=utf-8
import os
import cgi

DEFAULT_FORM_CLASS = 'form'
DEFAULT_CHARSET = 'utf-8'

def capitalize(s):
    t = s.split('_')
    return ' '.join([x.capitalize() for x in t])

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

def _create_kwargs(args):
    if not args:
        return ''
    s = ['']
    for k, v in args.items():
        if k.startswith('_'):
            k = k[1:]
        if v is None:
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
    def __init__(self, tag, *children, **args):
        self.tag = tag
        self.buf = list(children)
        if tag.endswith('/'):
            self.begin = '<%s%s/>' % (tag, _create_kwargs(args))
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

class TextInput(Build):
    type = 'text'

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def html(self):
        args = self.kwargs.copy()
        args.setdefault('type', self.type)
        return str(Tag('input', **args))

class PasswordInput(TextInput): type = 'password'
class TextAreaInput(Build):
    def __init__(self, value='', **kwargs):
        self.kwargs = kwargs
        self.value = value

    def html(self):
        args = self.kwargs
        args.setdefault('rows', 5)
        args.setdefault('cols', 40)
        return str(Tag('textarea', self.value, **args))
class HiddenInput(TextInput): type = 'hidden'
class ButtonInput(TextInput): type = 'button'
class SubmitInput(TextInput): type = 'submit'
class ResetInput(TextInput): type = 'reset'
class FileInput(TextInput): type = 'file'
class RadioInput(TextInput): type = 'radio'
class SelectInput(Build):
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
class RadioSelectInput(SelectInput):
    _id = 0
    def __init__(self, choices, value=None, **kwargs):
        SelectInput.__init__(self, choices, value, **kwargs)

    def html(self):
        s = []
        for v, caption in self.choices:
            args = {'value': v}
            id = args.setdefault('id', 'radio_%d' % self.get_id())
            args['name'] = self.kwargs.get('name')
            if v == self.value:
                args['checked'] = None
            s.append(str(RadioInput(**args)))
            s.append(str(Tag('label', caption, _for=id)))
        return ''.join(s)
    def get_id(self):
        RadioSelectInput._id += 1
        return self._id
class CheckboxInput(Build):
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

class Field(object):
    default_build = TextInput
    default_validators = []
    default_datatype = None
    field_css_class = 'field_text'

    creation_counter = 0

    def __init__(self, label='', default=None, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, datatype=None, multiple=False, **kwargs):
        self.label = label
        self.default = default
        self.validators = validators or []
        self.name = name
        self.required = required
        self.kwargs = kwargs
        self.html_attrs = html_attrs or {}
        self.datatype = datatype or self.default_datatype
        self.multiple = multiple
        if '_class' in self.html_attrs:
            self.html_attrs['_class'] = ' '.join([self.html_attrs['_class'], self.field_css_class])
        else:
            self.html_attrs['_class'] = ' '.join([self.field_css_class])
        self.build = build or self.default_build
        self.help_string = help_string

        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

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

    #todo: if py=True is needed
    def html(self, data='', py=True):
        """
        Convert data to html value format.
        """
        if py:
            value = self.to_html(data)
        else:
            value = data
        return str(self.build(name=self.name, value=value, id='field_'+self.name, **self.html_attrs))

    def get_label(self, **kwargs):
        if not self.label:
            label = capitalize(self.name)
        else:
            label = self.label
        if self.required:
            label += str(Tag('span', '(required)', _class='field_required'))
        return str(Tag('label', label, _for='field_'+self.name, **kwargs))

    def get_data(self, all_data):
        return all_data.get(self.name, None)

    def to_html(self, data):
        return _str(data)

    def validate(self, data, all_data=None):
        #todo process file input, this one only supports cgi.FieldStorage now
        if isinstance(data, cgi.FieldStorage):
            if data.file:
                v = data.filename
            else:
                raise Exception, 'Unsupport type %s' % type(data)
        else:
            v = data
        if not v:
            if not self.required:
                if self.default is not None:
                    return True, self.default
                else:
                    return True, data
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

class TextField(Field):
    def __init__(self, label='', default='', required=False, validators=None, name='', html_attrs=None, help_string='', build=None, **kwargs):
        Field.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)

class PasswordField(TextField):
    default_build = PasswordInput
    field_css_class = 'field_password'

class HiddenField(TextField):
    default_build = HiddenInput

class TextListField(TextField):
    def __init__(self, label='', default=None, required=False, validators=None, name='', delimeter=' ', html_attrs=None, help_string='', build=None, **kwargs):
        Field.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)
        self.delimeter = delimeter
        self.default = default or []

    def to_python(self, data):
        return data.split(self.delimeter)

    def to_html(self, data):
        return self.delimeter.join([_str(x) for x in data])

class BooleanField(Field):
    field_css_class = 'field_checkbox'
    default_build = CheckboxInput

    def __init__(self, label='', default=False, name='', html_attrs=None, help_string='', build=None, **kwargs):
        Field.__init__(self, label=label, default=default, required=False, validators=None, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)


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

class TextAreaField(Field):
    default_build = TextAreaInput
    field_css_class = 'field_textarea'

    def __init__(self, label='', default='', required=False, validators=None, name='', html_attrs=None, help_string='', build=None, **kwargs):
        Field.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)

    def html(self, data='', py=True):
        self.html_attrs.setdefault('rows', 5)
        self.html_attrs.setdefault('cols', 40)
        return str(self.build(self.to_html(data), id='field_'+self.name, name=self.name, **self.html_attrs))

class IntField(Field):
    default_validators = [IS_NUMBER()]
    def __init__(self, label='', default=0, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, **kwargs):
        Field.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)

    def to_python(self, data):
        return int(data)

    def to_html(self, data):
        return str(data)

class SelectField(Field):
    field_css_class = 'field_select'
    default_build = SelectInput

    def __init__(self, label='', default=None, choices=None, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, **kwargs):
        Field.__init__(self, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, **kwargs)
        self.choices = choices or []
        if self.choices:
            self.default = default or self.choices[0][0]
        self.validators.append(IS_IN_SET(self.choices))

    def html(self, data, py=True):
        return str(self.build(self.choices, data, id='field_'+self.name, name=self.name, **self.html_attrs))

class RadioSelectField(SelectField):
    field_css_class = 'field_radio'
    default_build = RadioSelectInput
    
class FileField(TextField):
    default_build = FileInput
    field_css_class = 'field_file'
    
    def to_python(self, data):
        d = {}
        d['filename'] = data.filename
        d['file'] = data.file
        data.file.seek(0, os.SEEK_END)
        d['length'] = data.file.tell()
        data.file.seek(0, os.SEEK_SET)
        return d
    
class DateField(TextField):
    field_css_class = 'field_date'
    
    def to_python(self, data):
        return int(data)
    
    def to_html(self, data):
        return str(data)
    
class TimeField(TextField):
    field_css_class = 'field_time'
    
class FormMetaclass(type):
    def __new__(cls, name, bases, attrs):
        fields = {}
        for field_name, obj in attrs.items():
            if isinstance(obj, Field):
                obj.name = field_name
                fields[field_name] = obj

        f = {}
        for base in bases[::-1]:
            if hasattr(base, 'fields'):
                f.update(base.fields)

        f.update(fields)
        attrs['fields'] = f

        field_list = [(k, v) for k, v in fields.items()]
        field_list.sort(lambda x, y: cmp(x[1].creation_counter, y[1].creation_counter))
        attrs['field_list'] = field_list

        return type.__new__(cls, name, bases, attrs)

class Layout(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.root = Tag('table')
        self.buf = self.root << Tag('tbody')

    def line(self, obj, data, error=None, py=True):
        tr = self.buf << Tag('tr')
        tr << Tag('td', obj.get_label())
        td = tr << Tag('td', obj.html(data, py))
        if error:
            td << Tag('br/')
            td << Tag('span', error, _class='error')
        td = tr << Tag('td', obj.help_string)

    def single_line(self, element):
        tr = self.buf << Tag('tr')
        tr << Tag('td', element, colspan=3)

    def buttons_line(self, buttons):
        tr = self.buf << Tag('tr')
        tr << Tag('td', buttons, colspan=3, _class="buttons")

    def __str__(self):
        return str(self.root)

class Form(object):

    __metaclass__ = FormMetaclass

    layout_class = Layout

    def __init__(self, action='', method='post', buttons='default', validators=None, html_attrs=None, **kwargs):
        self.action = action
        self.method = method
        self.kwargs = kwargs
        self.buttons = buttons
        self.validators = validators or []
        self.html_attrs = html_attrs or {}
        if '_class' in self.html_attrs:
            self.html_attrs['_class'] = self.html_attrs['_class'] + ' ' + DEFAULT_FORM_CLASS
        else:
            self.html_attrs['_class'] = DEFAULT_FORM_CLASS

    def validate(self, get_func_or_dict):
        if callable(get_func_or_dict):
            func = get_func_or_dict
        else:
            func = get_func_or_dict.get

        all_data = {}
        for k in self.fields.keys():
            all_data[k] = func(k, None)

        errors = {}
        new_data = {}

        #gather all fields
        for field_name, field in self.fields.items():
            new_data[field_name] = field.get_data(all_data)

        #validate and gather the result
        result = D({})
        for field_name, field in self.fields.items():
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

    def html(self, data=None, errors=None, layout=None, py=True):
        data = data or {}
        errors = errors or {}
        args = self.html_attrs.copy()
        args['action'] = self.action
        args['method'] = self.method
        args['enctype'] = "multipart/form-data"
        form = Tag('form', **args)
        layout = layout or self.layout_class()
        for name, obj in self.field_list:
            default = obj.to_html(obj.default)
            if isinstance(obj, HiddenField):
                form << obj.html(data.get(name, default), py)
            else:
                layout.line(obj, data.get(name, default), errors.get(name, ''), py)

        _class = self.html_attrs['_class']
        div = form << Tag('div', _class=_class)
        div << layout
        if self.buttons == 'default':
            b = Buf()
            b << [SubmitInput(value='Submit'), ResetInput(value='Reset')]
            layout.buttons_line(b)
        else:
            layout.buttons_line(self.buttons)
        return '\n<!-- create form -->\n' + str(form) + '\n<!-- create form end -->\n'

class CSSLayout(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.root = self.buf = Tag('div')

    def line(self, obj, data, error=None, py=True):
        div = self.buf << Tag('div', _class='field')
        if isinstance(obj, BooleanField):
            div << obj.get_label(_class='check_box')
        else:
            div << obj.get_label()
        div << obj.html(data, py)
        if error:
            div << Tag('span', error, _class='error')
#        td = tr << Tag('td', help_string)

    def single_line(self, element):
        div = self.buf << Tag('div')
        div << element

    def buttons_line(self, buttons):
        div = self.buf << Tag('div', _class="buttons")
        div << buttons

    def __str__(self):
        return str(self.root)

if __name__ == '__main__':
    class F(Form):
        title = TextField(label='Title:', required=True, help_string='Title help string')
        content = TextAreaField(label='Content:')
        password = PasswordField(label='Password:')
        age = IntField(label='Age:')
        id = HiddenField()
        tag = TextListField(label='Tag:')
        public = BooleanField(label='Public:')
        format = SelectField(label='Format:', choices=[('rst', 'reStructureText'), ('text', 'Plain Text')], default='rst')
        radio = RadioSelectField(label='Radio:', choices=[('rst', 'reStructureText'), ('text', 'Plain Text')], default='rst')
        file = FileField(label='file')
        
#    print F.fields
    f = F()
    print f.html()
#    d = {'title':'title', 'age':'12', 'tag':''}
#    print f.validate(d)
#    d = {'title':u'中国', 'id':333, 'tag':'python', 'public':True, 'format':'text'}
#    flag, data = f.validate(d)
#    print flag, data
#    print str(TextAreaInput())

#    print f.html(d, layout=CSSLayout(), py=False)
