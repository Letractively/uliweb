#coding=utf-8
from __future__ import with_statement
from uliweb.i18n import gettext_lazy as _
from uliweb.form import SelectField, BaseField
import os, sys
import time
from uliweb.orm import get_model, Model, Result, do_
import uliweb.orm as orm
from uliweb import redirect, json, functions, UliwebError, Storage
from sqlalchemy.sql import Select
from uliweb.contrib.upload import FileServing, FilenameConverter
from uliweb.utils.common import safe_unicode, safe_str
from uliweb.core.html import Builder
from uliweb.utils.sorteddict import SortedDict

__default_fields_builds__ = {}
class __default_value__(object):pass

def get_fileds_builds(section='GENERIC_FIELDS_MAPPING'):
    if not __default_fields_builds__:
        from uliweb import settings
        from uliweb.utils.common import import_attr
        import uliweb.form as form
        
        if settings and section in settings:
            for k, v in settings[section].iteritems():
                if v.get('build', None):
                    v['build'] = import_attr(v['build'])
                __default_fields_builds__[getattr(form, k)] = v
    return __default_fields_builds__

def get_sort_field(model, sort_field='sort', order_name='asc'):
    from uliweb import request
    
    model = get_model(model)
    if request.values.getlist('sort'):
        sort_fields = request.values.getlist('sort')
        order_by = []
        orders = request.values.getlist('order')
        for i, f in enumerate(sort_fields):
            if orders[i] == 'asc':
                order_by.append(model.c[f])
            else:
                order_by.append(model.c[f].desc())
    else:
        order_by = None
        
    return order_by
    
class ReferenceSelectField(SelectField):
    def __init__(self, model, group_field=None, value_field='id', condition=None, 
        query=None, label='', default=None, required=False, validators=None, 
        name='', html_attrs=None, help_string='', build=None, empty='', 
        get_display=None, **kwargs):
        super(ReferenceSelectField, self).__init__(label=label, default=default, choices=None, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, empty=empty, **kwargs)
        self.model = model
        self.group_field = group_field
        self.value_field = value_field
        self.condition = condition
        self.query = query
        self.get_display = get_display or unicode
        
    def get_choices(self):
        if self.choices:
            if callable(self.choices):
                return self.choices()
            else:
                return self.choices
            
        model = get_model(self.model)
        if not self.group_field:
            if hasattr(model, 'Meta'):
                self.group_field = getattr(model.Meta, 'group_field', None)
            else:
                self.group_field = None
           
        if self.query:
            query = self.query
        else:
            query = model.all()
            if hasattr(model, 'Meta') and hasattr(model.Meta, 'order_by'):
                _order = model.Meta.order_by
                if not isinstance(_order, (list, tuple)):
                    _order = [model.Meta.order_by]
                for x in _order:
                    if x.startswith('-'):
                        f = model.c[x[1:]].desc()
                    else:
                        if x.startswith('+'):
                            x = x[1:]
                        f = model.c[x].asc()
                    query = query.order_by(f)
        if self.condition is not None:
            query = query.filter(self.condition)
        if self.group_field:
            query = query.order_by(model.c[self.group_field].asc())
        if self.group_field:
            r = [(x.get_display_value(self.group_field), getattr(x, self.value_field), self.get_display(x)) for x in query]
        else:
            r = [(getattr(x, self.value_field), self.get_display(x)) for x in query]
        return r
    
    def to_python(self, data):
        attr = getattr(get_model(self.model), self.value_field)
        return attr.validate(data)

class ManyToManySelectField(ReferenceSelectField):
    def __init__(self, model, group_field=None, value_field='id', 
            condition=None, query=None, label='', default=[], 
            required=False, validators=None, name='', html_attrs=None, 
            help_string='', build=None, get_display=None, **kwargs):
        super(ManyToManySelectField, self).__init__(model=model, group_field=group_field, 
            value_field=value_field, condition=condition, query=query, label=label, 
            default=default, required=required, validators=validators, name=name, 
            html_attrs=html_attrs, help_string=help_string, build=build, 
            empty=None, multiple=True, get_display=get_display, **kwargs)
            
class RemoteField(BaseField):
    """
    Fetch remote data
    """
    def __init__(self, label='', default=None, required=False, validators=None, 
        name='', html_attrs=None, help_string='', build=None, alt='', url='', 
        datatype=int, **kwargs):
        _attrs = {'url':url, 'alt':alt, '_class':'rselect'}
        _attrs.update(html_attrs or {})
        BaseField.__init__(self, label=label, default=default, required=required, 
            validators=validators, name=name, html_attrs=_attrs, help_string=help_string, 
            build=build, datatype=datatype, **kwargs)
        
class GenericReference(orm.Property):
    property_type = 'compound'
    def __init__(self, verbose_name=None, table_fieldname='table_id', 
        object_fieldname='object_id', **attrs):
        """
        Definition of GenericRelation property
        """
            
        super(GenericReference, self).__init__(
            verbose_name=verbose_name, **attrs)
    
        self.table_fieldname = table_fieldname
        self.object_fieldname = object_fieldname
        self.table = get_model('tables')

    def create(self, cls):
        pass
    
    def pre_create(self, cls):
        if self.table_fieldname not in cls.properties:
            prop = orm.Field(orm.PKTYPE())
            cls.add_property(self.table_fieldname, prop)
        if self.object_fieldname not in cls.properties:
            prop = orm.Field(orm.PKTYPE())
            cls.add_property(self.object_fieldname, prop)
            
    def __property_config__(self, model_class, property_name):
        """Loads all of the references that point to this model.
        """
        super(GenericReference, self).__property_config__(model_class, property_name)
            
#    def filter(self, model):
#        model = get_model(model)
#        table_id = self.table.get_table(model.tablename).id
#        return self.model_class.filter(self.model_class.c[self.table_fieldname]==table_id)
        
    def filter(self, obj):
        if isinstance(obj, (tuple, list)):
            if len(obj) != 2:
                raise ValueError("GenericReference filter need a model instance or a tuple")
            table_id = self.table.get_table(obj[0]).id
            obj_id = obj[1]
        else:
            if not isinstance(obj, orm.Model):
                raise ValueError("obj should an instance of Model, but %r found" % obj)
            table_id = self.table.get_table(obj.__class__.tablename).id
            obj_id = obj.id
        return self.model_class.filter(self.model_class.c[self.table_fieldname]==table_id).filter(self.model_class.c[self.object_fieldname]==obj_id)

    def __get__(self, model_instance, model_class):
        """Get reference object.
    
        This method will fetch unresolved entities from the datastore if
        they are not already loaded.
    
        Returns:
            ReferenceProperty to Model object if property is set, else None.
        """
        if model_instance:
            table_id, object_id = self.get_value_for_datastore(model_instance)
            if not table_id and not object_id:
                return None
            model = self.table.get_model(table_id)
            return model.get(object_id)
        else:
            return self
    
    def __set__(self, model_instance, value):
        if model_instance is None:
            return
        
        if value:
            if isinstance(value, (tuple, list)):
                if not len(value) == 2:
                    raise ValueError("The value of GenericRelation should be two-elements tuple/list, or instance of Model, but %r found" % value)
                
                table_id, object_id = value
                if isinstance(table_id, (str, unicode)):
                    table_id = self.table.get_table(table_id).id
            elif isinstance(value, orm.Model):
                table_id = self.table.get_table(value.tablename).id
                object_id = value.id
            else:
                raise ValueError("The value of GenericRelation should be two-elements tuple/list, or instance of Model, but %r found" % value)
        
            model_instance.properties[self.table_fieldname].__set__(model_instance, table_id)
            model_instance.properties[self.object_fieldname].__set__(model_instance, object_id)
        setattr(model_instance, self._attr_name(), value)
    
    def get_value_for_datastore(self, model_instance):
        """Get key of reference rather than reference itself."""
        table_id = getattr(model_instance, self.table_fieldname, None)
        object_id = getattr(model_instance, self.object_fieldname, None)
        return table_id, object_id
    
    def get_display_value(self, value):
        return unicode(value)
    
class GenericRelation(orm.Property):
    property_type = 'compound'
    """Generic Relation difinition
    """

    def __init__(self, model, reference_fieldname='table_id', **attrs):
        """Constructor for reverse reference.

        Constructor does not take standard values of other property types.

        """
        super(GenericRelation, self).__init__(**attrs)
        self._model = model
        self.reference_fieldname = reference_fieldname
        self.table = get_model('tables')

    def create(self, cls):
        pass

    def __get__(self, model_instance, model_class):
        """Fetches collection of model instances of this collection property."""
        if model_instance is not None:      #model_instance is B's
            table_id = self.table.get_table(self.model_class.tablename).id
            model = get_model(self._model)
            return model.filter(model.c[self.reference_fieldname]==table_id)
        else:
            return self

    def __set__(self, model_instance, value):
        """Not possible to set a new collection."""
        raise ValueError('Virtual property is read-only')

def get_fields(model, fields, meta=None):
    """
    Acording to model and fields to get fields list
    Each field element is a two elements tuple, just like:
        (name, field_obj)
    """
    model = get_model(model)
    if fields is not None:
        f = fields
    elif meta and hasattr(model, meta):
        m = getattr(model, meta)
        if hasattr(m, 'fields'):
            f = m.fields
        else:
            f = model._fields_list
    else:
        f = model._fields_list
        
    fields_list = []
    for x in f:
        field = {}
        if isinstance(x, str):  #so x is field_name
            field['name'] = x
        elif isinstance(x, tuple):
            field['name'] = x[0]
            field['field'] = x[1]
        elif isinstance(x, dict):
            field = x.copy()
        else:
            raise UliwebError('Field definition is not right, it should be just like (field_name, form_field_obj)')
        
        if 'prop' not in field:
            if hasattr(model, field['name']):
                field['prop'] = getattr(model, field['name'])
            else:
                field['prop'] = None
        
        fields_list.append((field['name'], field))
    return fields_list

def get_layout(model, meta):
    f = None
    if hasattr(model, meta):
        m = getattr(model, meta)
        if hasattr(m, 'layout'):
            f = m.layout
    return f

def get_url(ok_url, *args, **kwargs):
    if callable(ok_url):
        return ok_url(*args, **kwargs)
    else:
        return ok_url.format(*args, **kwargs)

def get_obj_url(obj):
    from uliweb import settings
    from uliweb.core.html import Tag
    
    if hasattr(obj, 'get_url'):
        display = obj.get_url()
    else:
        url_prefix = settings.get_var('MODEL_URL/'+obj.tablename)
        if url_prefix:
            if url_prefix.endswith('/'):
                url_prefix = url_prefix[:-1]
            display = str(Tag('a', unicode(obj), href=url_prefix+'/'+str(obj.id)))
        else:
            display = unicode(obj)
    return display
    
def to_json_result(success, msg='', d=None, json_func=None, **kwargs):
    json_func = json_func or json
    
    t = {'success':success, 'message':safe_str(msg), 'data':d}
    t.update(kwargs)
    return json_func(t)
    
def make_form_field(field, model, field_cls=None, builds_args_map=None):
    import uliweb.form as form
    from uliweb.form.validators import IS_LENGTH_LESSTHAN
    
    model = get_model(model)
    field_type = None
    if isinstance(field, (str, unicode)):
        prop = getattr(model, field)
        if not prop:
            raise UliwebError("Can't find attribute in Model(%r)" % model)
        field = {'prop':prop}
    elif 'field' in field and isinstance(field['field'], BaseField): #if the prop is already Form.BaseField, so just return it
        return field['field']
    
    prop = field['prop']
    label = field.get('verbose_name', None) or prop.verbose_name or prop.property_name
    hint = field.get('hint', '') or prop.hint
    placeholder = field.get('placeholder', '') or prop.placeholder
    kwargs = dict(label=label, name=prop.property_name, 
        required=prop.required, help_string=hint, placeholder=placeholder)
    html_attrs = field.get('extra', {}).get('html_attrs', {}) or prop.extra.get('html_attrs', {})
    kwargs['html_attrs'] = html_attrs
    
    v = prop.default_value()
#    if v is not None:
    kwargs['default'] = v
        
    if field['static']:
        field_type = form.StringField
        kwargs['required'] = False
        kwargs['static'] = True
        if prop.choices is not None:
            kwargs['choices'] = prop.get_choices()
        
    if field['hidden']:
        field_type = form.HiddenField
        
    if 'required' in field:
        kwargs['required'] = field['required']
        
    if field_cls:
        field_type = field_cls
    elif not field_type:
        cls = prop.__class__
        if cls is orm.BlobProperty:
            pass
        elif cls is orm.TextProperty:
            field_type = form.TextField
        elif cls is orm.CharProperty or cls is orm.StringProperty:
            if prop.choices is not None:
                field_type = form.SelectField
                kwargs['choices'] = prop.get_choices()
            else:
                field_type = form.UnicodeField
        elif cls is orm.BooleanProperty:
            field_type = form.BooleanField
        elif cls is orm.DateProperty:
#            if not prop.auto_now and not prop.auto_now_add:
            field_type = form.DateField
        elif cls is orm.TimeProperty:
#            if not prop.auto_now and not prop.auto_now_add:
            field_type = form.TimeField
        elif cls is orm.DateTimeProperty:
#            if not prop.auto_now and not prop.auto_now_add:
            field_type = form.DateTimeField
        elif cls is orm.DecimalProperty:
            field_type = form.StringField
            if prop.choices is not None:
                field_type = form.SelectField
                kwargs['choices'] = prop.get_choices()
        elif cls is orm.FloatProperty:
            field_type = form.FloatField
        elif cls is orm.IntegerProperty:
            if 'autoincrement' not in prop.kwargs:
                if prop.choices is not None:
                    field_type = form.SelectField
                    kwargs['choices'] = prop.get_choices()
                    kwargs['datetype'] = int
                else:
                    field_type = form.IntField
        elif cls is orm.ManyToMany:
            kwargs['model'] = prop.reference_class
            field_type = ManyToManySelectField
        elif cls is orm.ReferenceProperty or cls is orm.OneToOne:
            #field_type = form.IntField
            kwargs['model'] = prop.reference_class
            kwargs['value_field'] = prop.reference_fieldname
            field_type = ReferenceSelectField
        elif cls is orm.FileProperty:
            field_type = form.FileField
        else:
            raise Exception, "Can't support the Property [%s=%s]" % (field['name'], prop.__class__.__name__)
       
    if field_type:
        build_args = builds_args_map.get(field_type, {})
        #add settings.ini configure support
        #so you could add options in settings.ini like this
        #  [GENERIC_FIELDS_MAPPING]
        #  FormFieldClassName = {'build':'model.NewFormFieldTypeClassName', **other args}
        #  
        #  e.g.
        #  [GENERIC_FIELDS_MAPPING]
        #  DateField = {'build':'jquery.widgets.DatePicker'}
        if not build_args:
            build_args = get_fileds_builds().get(field_type, {})
        kwargs.update(build_args)
        
        #add max_length validator
        if issubclass(prop.__class__, (orm.StringProperty, orm.CharProperty, orm.UnicodeProperty)):
            v = kwargs.setdefault('validators', [])
            if isinstance(prop.max_length, int):
                v.append(IS_LENGTH_LESSTHAN(prop.max_length+1))
        
        f = field_type(**kwargs)
    
        return f

def make_view_field(field, obj=None, types_convert_map=None, fields_convert_map=None, value=__default_value__):
    from uliweb.utils.textconvert import text2html
    from uliweb.core.html import Tag
    
    old_value = value

    types_convert_map = types_convert_map or {}
    fields_convert_map = fields_convert_map or {}
    default_convert_map = {orm.TextProperty:lambda v,o:text2html(v)}
    
    if isinstance(field, dict) and 'prop' in field and field.get('prop'):
        prop = field['prop']
    else:
        prop = field
        
    #not real Property instance, then return itself, so if should return
    #just like {'label':xxx, 'value':xxx, 'display':xxx}
    if not isinstance(prop, orm.Property):  
        if old_value is __default_value__:
            value = prop.get('value', '')
        display = prop.get('display', value)
        label = prop.get('label', '') or prop.get('verbose_name', '')
        name = prop.get('name', '')
        convert = prop.get('convert', None)
    else:
        if old_value is __default_value__:
            if isinstance(obj, Model):
                value = prop.get_value_for_datastore(obj)
            else:
                value = obj[prop.property_name]
        display = prop.get_display_value(value)
        name = prop.property_name
        
        if isinstance(field, dict):
            initial = field.get('verbose_name', None)
        else:
            initial = ''
        label = initial or prop.verbose_name or prop.property_name
        
    if name in fields_convert_map:
        convert = fields_convert_map.get(name, None)
    else:
        if isinstance(prop, orm.Property):
            convert = types_convert_map.get(prop.__class__, None)
            if not convert:
                convert = default_convert_map.get(prop.__class__, None)
        
    if convert:
        display = convert(value, obj)
    else:
        if value is not None:
            if isinstance(prop, orm.ManyToMany):
                s = []
                #support value parameter, the old value is already stored in "old_value" variable
                if old_value is not __default_value__:
                    query = prop.reference_class.filter(prop.reference_class.c[prop.reversed_fieldname].in_(old_value))
                else:
                    query = getattr(obj, prop.property_name).all()
                for x in query:
                    s.append(get_obj_url(x))
                display = ' '.join(s)
            elif isinstance(prop, orm.ReferenceProperty) or isinstance(prop, orm.OneToOne):
                try:
                    if old_value is not __default_value__:
                        d = prop.reference_class.c[prop.reference_fieldname]
                        v = prop.reference_class.get(d==old_value)
                    if not isinstance(obj, Model):
                        d = prop.reference_class.c[prop.reference_fieldname]
                        v = prop.reference_class.get(d==value)
                    else:
                        v = getattr(obj, prop.property_name)
                except orm.Error:
                    display = obj.get_datastore_value(prop.property_name)
                    v = None
                if isinstance(v, Model):
                    display = get_obj_url(v)
                else:
                    display = str(v)
            elif isinstance(prop, orm.FileProperty):
                url = functions.get_href(value)
                if url:
                    display = str(Tag('a', value, href=url))
                else:
                    display = ''
#            if isinstance(prop, orm.Property) and prop.choices is not None:
#                display = prop.get_display_value(value)
            if prop.__class__ is orm.TextProperty:
                display = text2html(value)
        
    if isinstance(display, unicode):
        display = display.encode('utf-8')
    if display is None:
        display = ''
        
    return Storage({'label':label, 'value':value, 'display':display, 'name':name})

def get_view_field(model, field_name, obj=None, types_convert_map=None, fields_convert_map=None, value=__default_value__):
    m = get_model(model)
    field = getattr(m, field_name)
    r = make_view_field(field, obj=obj, types_convert_map=types_convert_map, fields_convert_map=fields_convert_map, value=value)
    return r
    
def get_field_display(model, field_name, obj=None, types_convert_map=None, fields_convert_map=None, value=__default_value__):
    m = get_model(model)
    field = getattr(m, field_name)
    return make_view_field(field, obj=obj, types_convert_map=types_convert_map, fields_convert_map=fields_convert_map, value=value)['display']

def get_model_display(model, obj, fields=None, types_convert_map=None, fields_convert_map=None, data=None):
    data = data or {}
    r = Storage({})
    for name, field in get_fields(model, fields):
        value = data.get(name, __default_value__)
        r[name] = make_view_field(field, obj=obj, types_convert_map=types_convert_map, fields_convert_map=fields_convert_map, value=value)
    return r

class AddView(object):
    success_msg = _('The information has been saved successfully!')
    fail_msg = _('There are somethings wrong.')
    builds_args_map = {}
    
    def __init__(self, model, ok_url=None, ok_template=None, form=None, success_msg=None, 
        fail_msg=None, use_flash=True,
        data=None, default_data=None, fields=None, form_cls=None, form_args=None,
        static_fields=None, hidden_fields=None, pre_save=None, post_save=None,
        post_created_form=None, layout=None, file_replace=True, template_data=None, 
        success_data=None, fail_data=None, meta='AddForm', get_form_field=None, post_fail=None,
        types_convert_map=None, fields_convert_map=None, json_func=None,
        file_convert=True):

        self.model = get_model(model)
        self.meta = meta
        self.ok_url = ok_url
        self.ok_template = ok_template
        if success_msg:
            self.success_msg = success_msg
        if fail_msg:
            self.fail_msg = fail_msg
        self.use_flash = use_flash
        self.data = data or {}
        self.template_data = template_data or {}
        
        #default_data used for create object
        self.default_data = default_data or {}
        self.get_form_field = get_form_field
        self.layout = layout
        self.fields = fields
        self.form_cls = form_cls
        self.form_args = form_args or {}
        self.static_fields = static_fields or []
        self.hidden_fields = hidden_fields or []
        self.pre_save = pre_save
        self.post_save = post_save
        self.post_created_form = post_created_form
        self.post_fail = post_fail
        self.file_replace = file_replace
        self.success_data = success_data
        self.fail_data = fail_data
        self.types_convert_map = types_convert_map or {}
        self.fields_convert_map = fields_convert_map or {}
        self.json_func = json_func or json
        self.file_convert = file_convert
        self.form = self.make_form(form)
        
    def get_fields(self):
        f = []
        for field_name, prop in get_fields(self.model, self.fields, self.meta):
            d = prop.copy()
            d['static'] = field_name in self.static_fields
            d['hidden'] = field_name in self.hidden_fields
            f.append(d)
            
        return f
    
    def get_layout(self):
        if self.layout:
            return self.layout
        if hasattr(self.model, self.meta):
            m = getattr(self.model, self.meta)
            if hasattr(m, 'layout'):
                return getattr(m, 'layout')
            
    def prepare_static_data(self, data):
        """
        If user defined static fields, then process them with visiable value
        """
        d = data.copy()
        for f in self.get_fields():
            if f['static'] and f['name'] in d:
                d[f['name']] = make_view_field(f, None, self.types_convert_map, self.fields_convert_map, d[f['name']])['display']
        return d
    
    def make_form(self, form):
        from uliweb.form import Form, Button
        
        if form:
            return form
        
        if self.form_cls:
            class DummyForm(self.form_cls):pass
            if not hasattr(DummyForm, 'form_buttons'):
                DummyForm.form_buttons = Button(value=_('Create'), _class="btn btn-primary", type='submit')
           
        else:
            class DummyForm(Form):
                form_buttons = Button(value=_('Create'), _class="btn btn-primary", type='submit')
            
        #add layout support
        layout = self.get_layout()
        DummyForm.layout = layout
        
        for f in self.get_fields():
            flag = False
            if self.get_form_field:
                field = self.get_form_field(f['name'])
                if field:
                    flag = True
            if not flag:
                field = make_form_field(f, self.model, builds_args_map=self.builds_args_map)
            
            if field:
                DummyForm.add_field(f['name'], field, True)
        
        if self.post_created_form:
            self.post_created_form(DummyForm, self.model)
            
        return DummyForm(data=self.data, **self.form_args)
    
    def process_files(self, data):
        flag = False
    
        fields_list = self.get_fields()
        for f in fields_list:
            if isinstance(f['prop'], orm.FileProperty):
                if f['name'] in data and data[f['name']]:
                    fobj = data[f['name']]
                    data[f['name']] = functions.save_file(fobj['filename'], 
                        fobj['file'], replace=self.file_replace, 
                        convert=self.file_convert)
                    flag = True
                    
        return flag
    
    def on_success_data(self, obj, data):
        if self.success_data is True:
            return obj.to_dict()
        elif callable(self.success_data):
            return self.success_data(obj, data)
        else:
            return None
    
    def on_fail_data(self, obj, errors, data):
        if callable(self.fail_data):
            return self.fail_data(obj, errors, data)
        else:
            return errors

    def on_success(self, d, json_result=False):
        from uliweb import response

        if self.pre_save:
            self.pre_save(d)
            
        r = self.process_files(d)
        obj = self.save(d)
        
        if self.post_save:
            self.post_save(obj, d)
                
        if json_result:
            return to_json_result(True, self.success_msg, self.on_success_data(obj, d), json_func=self.json_func)
        else:
            if self.use_flash:
                functions.flash(self.success_msg)
            if self.ok_url:
                return redirect(get_url(self.ok_url, id=obj.id))
            else:
                response.template = self.ok_template
                return d
        
    def on_fail(self, d, json_result=False):
        import logging
        
        log = logging.getLogger('uliweb.app')
        log.debug(self.form.errors)
        if json_result:
            return to_json_result(False, self.fail_msg, self.on_fail_data(None, self.form.errors, d), json_func=self.json_func)
        else:
            if self.use_flash:
                functions.flash(self.fail_msg, 'error')
            return d
    
    def init_form(self):
        if not self.form:
            self.form = self.make_form()
            
    def display(self, json_result=False):
        d = self.template_data.copy()
        d.update({'form':self.form})
        return d
    
    def _get_data(self):
        from uliweb import request
        from json import loads
        
        #add json data process
        if 'application/json' in request.content_type:
            data = (loads(request.data), )
        else:
            data = request.values, request.files
        return data
    
    def execute(self, json_result=False):
        flag = self.form.validate(*self._get_data())
        if flag:
            d = self.default_data.copy()
            d.update(self.form.data)
            return self.on_success(d, json_result)
        else:
            d = self.template_data.copy()
            data = self.prepare_static_data(self.form.data)
            self.form.bind(data)
            d.update({'form':self.form})
            if self.post_fail:
                self.post_fail(d)
            return self.on_fail(d, json_result)
        
    def run(self, json_result=False):
        from uliweb import request
        
        if request.method == 'POST':
            return self.execute(json_result)
        else:
            data = self.prepare_static_data(self.form.data)
            self.form.bind(data)
            return self.display(json_result)
        
    def save(self, data):
        obj = self.model(**data)
        obj.save()
        
#        self.save_manytomany(obj, data)
        return obj
        
    def save_manytomany(self, obj, data):
        #process manytomany property
        for k, v in obj._manytomany.iteritems():
            if k in data:
                value = data[k]
                if value:
                    getattr(obj, k).add(*value)

class EditView(AddView):
    success_msg = _('The information has been saved successfully!')
    fail_msg = _('There are somethings wrong.')
    builds_args_map = {}
    
    def __init__(self, model, ok_url=None, condition=None, obj=None, meta='EditForm', **kwargs):
        self.model = get_model(model)
        self.condition = condition
        self.obj = obj or self.query()
        
        AddView.__init__(self, model, ok_url, meta=meta, **kwargs)
        
        #set obj to form.object
        self.form.object = self.obj
        
    def display(self, json_result=False):
        d = self.template_data.copy()
        d.update({'form':self.form, 'object':self.obj})
        return d
    
    def execute(self, json_result=False):
        flag = self.form.validate(*self._get_data())
        if flag:
            d = self.default_data.copy()
            d.update(self.form.data)
            return self.on_success(d, json_result)
        else:
            d = self.template_data.copy()
            
            new_d = self.prepare_static_data(self.form.data)
            self.form.bind(new_d)
            
            d.update({'form':self.form, 'object':self.obj})
            if self.post_fail:
                self.post_fail(d, self.obj)
            return self.on_fail(d, json_result)

    def on_success(self, d, json_result):
        from uliweb import response
        
        if self.pre_save:
            self.pre_save(self.obj, d)
        #process file field
        r = self.process_files(d)
        r = self.save(self.obj, d) or r
        if self.post_save:
            r = self.post_save(self.obj, d) or r
        
        if r:
            msg = self.success_msg
        else:
            msg = _("The object has not been changed.")
        
        if json_result:
            return to_json_result(True, msg, self.on_success_data(self.obj, d), modified=r, json_func=self.json_func)
        else:
            if self.use_flash:
                functions.flash(msg)
            if self.ok_url:
                return redirect(get_url(self.ok_url, self.obj.id))
            else:
                response.template = self.ok_template
                return d
            
    def on_fail(self, d, json_result=False):
        import logging
        
        log = logging.getLogger('uliweb.app')
        log.debug(self.form.errors)
        if json_result:
            return to_json_result(False, self.fail_msg, self.on_fail_data(self.obj, self.form.errors, d), json_func=self.json_func)
        else:
            if self.use_flash:
                functions.flash(self.fail_msg, 'error')
            return d

    def prepare_static_data(self, data):
        """
        If user defined static fields, then process them with visiable value
        """
        d = self.obj.to_dict()
        d.update(data.copy())
        for f in self.get_fields():
            if f['static'] and f['name'] in d:
                v = make_view_field(f, self.obj, self.types_convert_map, self.fields_convert_map, d[f['name']])
                d[f['name']] = v['display']
        return d

    def run(self, json_result=False):
        from uliweb import request
        
        if request.method == 'POST':
            return self.execute(json_result)
        else:
            d = self.prepare_static_data(self.form.data)
            self.form.bind(d)
            return self.display(json_result)
        
    def save(self, obj, data):
        obj.update(**data)
        r = obj.save()
#        r1 = self.save_manytomany(obj, data)
#        return r or r1
        return r
        
    def save_manytomany(self, obj, data):
        #process manytomany property
        r = False
        for k, v in obj._manytomany.iteritems():
            if k in data:
                field = getattr(obj, k)
                value = data[k]
                if value:
                    r = getattr(obj, k).update(*value) or r
                else:
                    getattr(obj, k).clear()
        return r
        
    def query(self):
        return self.model.get(self.condition)
    
    def make_form(self, form):
        from uliweb.form import Form, Button
        
        if form:
            return form

        if self.form_cls:
            class DummyForm(self.form_cls):pass
            if not hasattr(DummyForm, 'form_buttons'):
                DummyForm.form_buttons = Button(value=_('Save'), _class="btn btn-primary", type='submit')
           
        else:
            class DummyForm(Form):
                form_buttons = Button(value=_('Save'), _class="btn btn-primary", type='submit')
            
        fields_list = self.get_fields()
        fields_name = [x['name'] for x in fields_list]
#        if 'id' not in fields_name:
#            d = {'name':'id', 'prop':self.model.id, 'static':False, 'hidden':False}
#            fields_list.insert(0, d)
#            fields_name.insert(0, 'id')
        
        data = self.obj.to_dict(fields_name, convert=False).copy()
        data.update(self.data)
        
        #add layout support
        layout = self.get_layout()
        DummyForm.layout = layout

        for f in fields_list:
            if f['name'] == 'id':
                f['hidden'] = True
            elif isinstance(f['prop'], orm.IntegerProperty) and 'autoincrement' in f['prop'].kwargs:
                f['hidden'] = True
                
            flag = False
            if self.get_form_field:
                field = self.get_form_field(f['name'], self.obj)
                if field:
                    flag = True
            if not flag:
                field = make_form_field(f, self.model, builds_args_map=self.builds_args_map)
            
            if field:
                DummyForm.add_field(f['name'], field, True)
                
                if isinstance(f['prop'], orm.ManyToMany):
                    value = getattr(self.obj, f['name']).ids()
                    data[f['name']] = value
        
        if self.post_created_form:
            self.post_created_form(DummyForm, self.model, self.obj)
        
        return DummyForm(data=data, **self.form_args)

from uliweb.core import uaml
from uliweb.core.html import begin_tag, end_tag, u_str

class DetailWriter(uaml.Writer):
    def __init__(self, get_field):
        self.get_field = get_field
        
    def do_static(self, indent, value, **kwargs):
        name = kwargs.get('name', None)
        if name:
            f = self.get_field(name)
            f['display'] = f['display'] or '&nbsp;'
            return indent * ' ' + '<div class="static"><label>%(label)s:</label><span class="value">%(display)s</span></div>' % f
        else:
            return ''
        
    def do_td_field(self, indent, value, **kwargs):
        name = kwargs.pop('name', None)
        if name:
            f = self.get_field(name)
            f['display'] = f['display'] or '&nbsp;'
            if 'width' not in kwargs:
                kwargs['width'] = 200
            td = begin_tag('td', **kwargs) + u_str(f['display']) + end_tag('td')
            return '<th align=right width=200>%(label)s</th>' % f + td
        else:
            return '<th>&nbsp;</th><td>&nbsp;</td>'
        
        
class DetailLayout(object):
    def __init__(self, layout_file, get_field, model=None, writer=None, **kwargs):
        self.layout_file = layout_file
        self.writer = writer or DetailWriter(get_field)
        self.model = model
        self.kwargs = kwargs
        
    def get_text(self):
        from uliweb import application
        f = file(application.get_file(self.layout_file, dir='templates'), 'rb')
        text = f.read()
        f.close()
        return text
    
    def render(self):
        return uaml.Parser(self.get_text(), self.writer)
    
    def __str__(self):
        return str(self.render())

class DetailTableLayout(object):
    def __init__(self, layout, get_field, model=None, table_class='table'):
        self.layout = layout
        self.get_field = get_field
        self.model = model
        self.table_class = table_class
        
    def line(self, fields, n):
        from uliweb.core.html import Tag
        
        _x = 0
        for _f in fields:
            if isinstance(_f, (str, unicode)):
                _x += 1
            elif isinstance(_f, dict):
                _x += _f.get('colspan', 1)
            else:
                raise Exception, 'Colume definition is not right, only support string or dict'
        
        tr = Tag('tr')
        with tr:
            for x in fields:
                _span = n / _x
                if isinstance(x, (str, unicode)):
                    f = self.get_field(x)
                elif isinstance(x, dict):
                    f = self.get_field(x['name'])
                    _span = _span * x.get('colspan', 1)
                
                with tr.td(colspan=_span, width='%d%%' % (100*_span/n,)):
                    with tr.div:
                        with tr.span(_class='view-label'):
                            tr << '<b>' + f['label'] + ': </b>'
                        if isinstance(x, dict) and x.get('break'):
                            tr << '<br/>'
                        with tr.span(_class='view-content'):
                            tr << f['display']
                
        return tr
        
    
    def render(self):
        from uliweb.core.html import Builder
        from uliweb.form.layout import min_times

        m = []
        for line in self.layout:
            if isinstance(line, (tuple, list)):
                _x = 0
                for f in line:
                    if isinstance(f, (str, unicode)):
                        _x += 1
                    elif isinstance(f, dict):
                        _x += f.get('colspan', 1)
                    else:
                        raise Exception, 'Colume definition is not right, only support string or dict'
                m.append(_x)
            else:
                m.append(1)
        n = min_times(m)
        
        buf = Builder('begin', 'body', 'end')
        table = None
        fieldset = None
        first = True
        for fields in self.layout:
            if not isinstance(fields, (tuple, list)):
                if isinstance(fields, (str, unicode)) and fields.startswith('--') and fields.endswith('--'):
                    #THis is a group line
                    if table:
                        buf.body << '</tbody></table>'
                    if fieldset:
                        buf.body << '</fieldset>'
                    title = fields[2:-2].strip()
                    if title:
                        fieldset = True
                        buf.body << '<fieldset><legend>%s</legend>' % title
                    
                    buf.body << '<table class="%s"><tbody>' % self.table_class
                    table = True
                    first = False
                    continue
                else:
                    fields = [fields]
            if first:
                first = False
                buf.begin << '<table class="%s">' % self.table_class
                buf.body << '<tbody>'
                table = True
            buf.body << self.line(fields, n)
        #close the tags
        if table:
            buf.end << '</table>'
            buf.body << '</tbody>'
        if fieldset:
            buf.body << '</fieldset>'
            
        return buf
    
    def __str__(self):
        return str(self.render())
    
class DetailView(object):
    def __init__(self, model, condition=None, obj=None, fields=None, 
        types_convert_map=None, fields_convert_map=None, table_class_attr='table',
        layout_class=None, layout=None, layout_kwargs=None, template_data=None, meta='DetailView'):
        self.model = get_model(model)
        self.meta = meta
        self.condition = condition
        if not obj:
            self.obj = self.query()
        else:
            self.obj = obj
        
        self.fields = fields
        self.types_convert_map = types_convert_map or {}
        self.fields_convert_map = fields_convert_map or {}
        self.table_class_attr = table_class_attr
        self.layout = layout or get_layout(model, meta)
        self.layout_class = layout_class
        if isinstance(self.layout, (str, unicode)):
            self.layout_class = layout_class or DetailLayout
        elif isinstance(self.layout, (tuple, list)):
            self.layout_class = layout_class or DetailTableLayout
        self.template_data = template_data or {}
        self.result_fields = Storage({})
        self.r = self.result_fields
        self.f = Storage({})    #结果字段
        self.layout_kwargs = layout_kwargs or {}
        
    def run(self):
        text = self.render()
        result = self.template_data.copy()
        result.update({'object':self.obj, 'view':text, 'view_obj':self})
        return result
    
    def query(self):
        return self.model.get(self.condition)
    
    def render(self):
        if self.layout:
            fields = dict(get_fields(self.model, self.fields, self.meta))
            def get_field(name):
                prop = fields[name]
                return make_view_field(prop, self.obj, self.types_convert_map, self.fields_convert_map)
            
            return self.layout_class(self.layout, get_field, self.model, **self.layout_kwargs).render()
        else:
            return self._render()
        
    def _render(self):
        b = Builder('begin', 'body', 'end')
        b.begin << '<table class="%s">' % self.table_class_attr
        
        text = []
        for field_name, prop in get_fields(self.model, self.fields, self.meta):
            field = make_view_field(prop, self.obj, self.types_convert_map, self.fields_convert_map)
            if field:
                text.append('<tr><th align="right" width=150>%s</th><td>%s</td></tr>' % (field["label"], field["display"]))
                self.result_fields[field_name] = field
                self.f[field_name] = field['display']
        b.body << '\n'.join(text)

        b.end << '</table>'
        return b

    def body(self):
        text = []
        for field_name, prop in get_fields(self.model, self.fields, self.meta):
            field = make_view_field(prop, self.obj, self.types_convert_map, self.fields_convert_map)
            if field:
                text.append('<tr><th align="right" width=150>%s</th><td>%s</td></tr>' % (field["label"], field["display"]))
                self.result_fields[field_name] = field
                self.f[field_name] = field['display']
        return '\n'.join(text)

class DeleteView(object):
    success_msg = _('The object has been deleted successfully!')

    def __init__(self, model, ok_url='', fail_url='', condition=None, obj=None, 
        pre_delete=None, post_delete=None, validator=None, json_func=None, 
        use_flash=True, use_delete_fieldname=None, success_data=None,
        fail_data=None):
        self.model = get_model(model)
        self.condition = condition
        self.obj = obj
        self.validator = validator
        self.json_func = json_func or json
        if not obj:
            self.obj = self.model.get(self.condition)
        else:
            self.obj = obj
        
        self.ok_url = ok_url
        self.fail_url = fail_url
        self.pre_delete = pre_delete
        self.post_delete = post_delete
        self.use_flash = use_flash
        self.use_delete_fieldname = use_delete_fieldname
        self.success_data = success_data
        self.fail_data = fail_data
        
    def run(self, json_result=False):
        if self.validator:
            msg = self.validator(self.obj)
            if msg:
                if json_result:
                    return to_json_result(False, msg, self.on_fail_data(self.obj, {}, {}), json_func=self.json_func)
                else:
                    if self.use_flash:
                        functions.flash(msg, 'error')
                    return redirect(self.fail_url)
                
        if self.pre_delete:
            self.pre_delete(self.obj)
        self.delete(self.obj)
        if self.post_delete:
            self.post_delete()
        
        if json_result:
            return to_json_result(True, self.success_msg, self.on_success_data(None, {}), json_func=self.json_func)
        else:
            if self.use_flash:
                functions.flash(self.success_msg)
            return redirect(self.ok_url)
    
    def on_success_data(self, obj, data):
        if callable(self.success_data):
            return self.success_data(obj, data)
        else:
            return None

    def on_fail_data(self, obj, errors, data):
        if callable(self.fail_data):
            return self.fail_data(obj, errors, data)
        else:
            return errors

    def delete(self, obj):
        if obj:
            self.delete_manytomany(obj)
            if self.use_delete_fieldname:
                setattr(obj, self.use_delete_fieldname, True)
                obj.save()
            else:
                obj.delete()
        
    def delete_manytomany(self, obj):
        for k, v in obj._manytomany.iteritems():
            getattr(obj, k).clear()
  
class GenericFileServing(FileServing):
    options = {
        'x_sendfile' : ('GENERIC/X_SENDFILE', None),
        'x_header_name': ('GENERIC/X_HEADER_NAME', None),
        'x_file_prefix': ('GENERIC/X_FILE_PREFIX', '/gdownload'),
        'to_path': ('GENERIC/TO_PATH', './files'),
        'buffer_size': ('GENERIC/BUFFER_SIZE', 4096),
        '_filename_converter': ('UPLOAD/FILENAME_CONVERTER',  FilenameConverter),
    }

class SimpleListView(object):
    def __init__(self, fields=None, query=None, 
        pageno=0, rows_per_page=10, id='listview_table', fields_convert_map=None, 
        table_class_attr='table', table_width=False, pagination=True, total_fields=None, 
        template_data=None, default_column_width=100, total=None, manual=False, render=None):
        """
        Pass a data structure to fields just like:
            [
                {'name':'field_name', 'verbose_name':'Caption', 'width':100},
                ...
            ]
        
        total_fields definition:
            ['field1', 'field2']
            
            or 
            
            [{'name':'fields', 'cal':'sum' or 'avg' or None, #if None then don't
                #calculate at each row iterate, default cal = sum
                'render':str function(value, total_sum)]
        """
        self.fields = fields
        self._query = query
        self.pageno = pageno
        self.rows_per_page = rows_per_page
        self.rows_num = 0
        self.id = id
        self.table_class_attr = table_class_attr
        self.fields_convert_map = fields_convert_map or {}
        self.total = total or 0
        self.table_width = table_width
        self.pagination = pagination
        self.create_total_infos(total_fields)
        self.template_data = template_data or {}
        self.default_column_width = default_column_width
        self.manual = manual
        self.downloader = GenericFileServing()
        self.render_func = render
        
        self.init()
        
    def init(self):
        from uliweb import request
        
        if 'page' in request.values:
            self.pageno = int(request.values.get('page')) - 1
        if 'rows' in request.values:
            self.rows_per_page = int(request.values.get('rows'))
        
        #create table header
        self.table_info = self.get_table_info()
        
    def create_total_infos(self, total_fields):
        if total_fields:
            self.total_fields = {}
            for x in total_fields['fields']:
                if isinstance(x, (str, unicode)):
                    self.total_fields[x] = {}
                elif isinstance(x, dict):
                    self.total_fields[x['name']] = x
                else:
                    raise Exception, "Can't support this type (%r) at define total_fields for field %s" % (type(x), x)
            total_fields['fields']
            self.total_field_name = total_fields.get('total_field_name', _('Total'))
        else:
            self.total_fields = {}
            self.total_field_name = None
        self.total_sums = {}
            
    def cal_total(self, record):
        if self.total_fields:
            for f in self.total_fields:
                if isinstance(record, (tuple, list)):
                    i = self.table_info['fields'].index(f)
                    v = record[i]
                elif isinstance(record, dict):
                    v = record.get(f)
                else:
                    v = getattr(record, f)
                x = self.total_fields[f]
                cal = x.get('cal', 'sum')
                #if cal is None, then do nothing
                if cal:
                    self.total_sums[f] = self.total_sums.setdefault(f, 0) + v
                
    def get_total(self):
        s = []
        if self.total_fields:
            for i, f in enumerate(self.table_info['fields']):
                if i == 0:
                    v = self.total_field_name
                else:
                    if f in self.total_fields:
                        v = self.total_sums.get(f, 0)
                        #process cal and render
                        x = self.total_fields[f]
                        cal = x.get('cal', 'sum')
                        if cal == 'sum':
                            pass
                        elif cal == 'avg':
                            v = v * 1.0 / self.rows_num
                        render = x.get('render', None)
                        if render:
                            v = render(v, self.total_sums)
                        else:
                            v = str(v)
                    else:
                        v = ''
                s.append(v)
        return s

    def render_total(self, json=False):
        s = []
        if self.total_fields:
            if json:
                for v in self.get_total():
                    v = str(v)
                    s.append(v)
                return dict(zip(self.table_info['fields'], s))
            else:
                s.append('<tr class="sum">')
                for v in self.get_total():
                    v = str(v) or '&nbsp;'
                    s.append('<td>%s</td>' % v)
                s.append('</tr>')
                return ''.join(s)
        return ''
    
    def query_all(self):
        return self.query_range(0, pagination=False)
    
    def query(self):
        return self.query_range(self.pageno, self.pagination)
    
    def query_range(self, pageno=0, pagination=True):
        if callable(self._query):
            query_result = self._query()
        else:
            query_result = self._query
            
        def repeat(data, begin, n):
            result = []
            no_data_flag = False
            i = 0
            while (begin > 0 and i < begin) or (begin == -1):
                try:
                    result.append(data.next())
                    i += 1
                    n += 1
                except StopIteration:
                    no_data_flag = True
                    break
            return no_data_flag, n, result
        
        if self.manual:
            if isinstance(query_result, (list, tuple)):
                if not self.total:
                    self.total = len(query_result)
                return query_result
            else:
                if not self.total:
                    flag, self.total, result = repeat(query_result, -1, self.total)
                else:
                    result = query_result
                return result
        else:
            self.total = 0
            if pagination:
                if isinstance(query_result, (list, tuple)):
                    self.total = len(query_result)
                    result = query_result[pageno*self.rows_per_page : (pageno+1)*self.rows_per_page]
                    return result
                else:
                    #first step, skip records before pageno*self.rows_per_page
                    flag, self.total, result = repeat(query_result, pageno*self.rows_per_page, self.total)
                    if flag:
                        return []
                    
                    #second step, get the records
                    flag, self.total, result = repeat(query_result, self.rows_per_page, self.total)
                    if flag:
                        return result
                    
                    #third step, skip the rest records, and get the really total
                    flag, self.total, r = repeat(query_result, -1, self.total)
                    return result
            else:
                if isinstance(query_result, (list, tuple)):
                    self.total = len(query_result)
                    return query_result
                else:
                    flag, self.total, result = repeat(query_result, -1, self.total)
                    return result
        
    def download(self, filename, timeout=3600, action=None, query=None, fields_convert_map=None, type=None, domain=None):
        """
        Default domain option is PARA/DOMAIN
        """
        from uliweb import settings
        
        fields_convert_map = fields_convert_map or self.fields_convert_map
        
        t_filename = self.get_real_file(filename)
        if os.path.exists(t_filename):
            if timeout and os.path.getmtime(t_filename) + timeout > time.time():
                return self.downloader.download(filename, action)
            
        if not query:
            query = self.query_all()
        if not type:
            type = os.path.splitext(filename)[1]
            if type:
                type = type[1:]
            else:
                type = 'csv'
        if type in ('xlt', 'xls'):
            if not domain:
                domain = settings.get_var('PARA/DOMAIN')
            return self.download_xlt(filename, query, action, fields_convert_map, domain, not_tempfile=bool(timeout))
        else:
            return self.download_csv(filename, query, action, fields_convert_map, not_tempfile=bool(timeout))
       
    def get_data(self, query, fields_convert_map, encoding='utf-8', plain=True):

        fields_convert_map = fields_convert_map or {}
        d = self.fields_convert_map.copy() 
        d.update(fields_convert_map)
        
        if isinstance(query, Select):
            query = do_(query)
        
        def get_value(name, value, record):
            convert = d.get(name)
            if convert:
                value = convert(value, record)
            return safe_unicode(value, encoding)
        
        for record in query:
            self.cal_total(record)
            row = []
            if not isinstance(record, (orm.Model, dict)):
                if not isinstance(record, (tuple, list)):
                    record = list(record)
                record = dict(zip(self.table_info['fields'], record))
            if isinstance(record, orm.Model):
                model = record.__class__
            else:
                model = None
                
            for i, x in enumerate(self.table_info['fields_list']):
                if model:
                    if hasattr(model, x['name']):
                        field = getattr(model, x['name'])
                    else:
                        field = x
                else:
                    field = x
                    field['value'] = record[x['name']]
                v = make_view_field(field, record, fields_convert_map=d)
                value = v['display']
                #value = safe_unicode(v['display'], encoding)
                row.append(value)
                
            yield row
        total = self.get_total()
        if total:
            row = []
            for x in total:
                v = x
                if isinstance(x, str):
                    v = safe_unicode(x, encoding)
                row.append(v)
            yield row

    def get_real_file(self, filename):
        t_filename = self.downloader.get_filename(filename)
        return t_filename
    
    def get_download_file(self, filename, not_tempfile):
        import tempfile
        
        t_filename = self.get_real_file(filename)
        dirname = os.path.dirname(t_filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        #bfile is display filename
        bfile = os.path.basename(t_filename)
        #tfile is template filename and it's the real filename
        if not not_tempfile:
            tfile = tempfile.NamedTemporaryFile(suffix = ".tmp", prefix = bfile+'_', dir=dirname, delete = False)
        else:
            tfile = open(t_filename, 'wb')
        #ufile is internal url filename
        ufile = os.path.join(os.path.dirname(filename), os.path.basename(tfile.name))
        return tfile, bfile, ufile
    
    def download_xlt(self, filename, data, action, fields_convert_map=None, domain=None, not_tempfile=False):
        from uliweb.utils.xlt import ExcelWriter
        from uliweb import request, settings
        
        fields_convert_map = fields_convert_map or {}
        tfile, bfile, ufile = self.get_download_file(filename, not_tempfile)
        if not domain:
            domain = settings.get_var('GENERIC/DOWNLOAD_DOMAIN', request.host_url)
        default_encoding = settings.get_var('GLOBAL/DEFAULT_ENCODING', 'utf-8')
        w = ExcelWriter(header=self.table_info['fields_list'], data=self.get_data(data, 
            fields_convert_map, default_encoding, plain=False), 
            encoding=default_encoding, domain=domain)
        w.save(tfile.name)
        return self.downloader.download(bfile, action=action, x_filename=ufile, 
            real_filename=tfile.name)
        
    def download_csv(self, filename, data, action, fields_convert_map=None, not_tempfile=False):
        from uliweb import settings
        from uliweb.utils.common import simple_value, safe_unicode
        import csv
        
        fields_convert_map = fields_convert_map or {}
        tfile, bfile, ufile = self.get_download_file(filename, not_tempfile)

        encoding = settings.get_var('GENERIC/CSV_ENCODING', sys.getfilesystemencoding() or 'utf-8')
        default_encoding = settings.get_var('GLOBAL/DEFAULT_ENCODING', 'utf-8')
        with tfile as f:
            w = csv.writer(f)
            row = [safe_unicode(x, default_encoding) for x in self.table_info['fields_name']]
            w.writerow(simple_value(row, encoding))
            for row in self.get_data(data, fields_convert_map, default_encoding):
                w.writerow(simple_value(row, encoding))
        return self.downloader.download(bfile, action=action, x_filename=ufile, 
            real_filename=tfile.name)
        
    def run(self, head=True, body=True, json_result=False):
        result = self.template_data.copy()
        result.update(self.render(json_result=json_result))
        return result
    
    def json(self):
        return self.run(json_result=True)
    
    def render(self, json_result=False):
        result = {
            'table_id':self.id, 
            'pageno':self.pageno+1,
            'page':self.pageno+1,
            'page_rows':self.rows_per_page,
            }
        if not json_result:
            s = Builder('begin', 'colgroup', 'head', 'body', 'end')
            s.begin << '<table class="%s" id=%s>' % (self.table_class_attr, self.id)
            with s.colgroup.colgroup:
                s.colgroup << self.create_table_colgroup()
            with s.head.thead:
                s.head << self.create_table_head()
        
            s.body << '<tbody>'
            for r in self.objects():
                render_func = self.render_func or self.default_body_render
                data = []
                for f in self.table_info['fields_list']:
                    data.append( (f['name'], r[f['name']]) )
                s.body << render_func(data, r.get('_obj_', {}))
            s.body << '</tbody>'
            s.end << '</table>'
            
            result['table'] = s
        else:
            s = []
            for r in self.objects():
                render_func = self.render_func or self.json_body_render
                data = []
                for f in self.table_info['fields_list']:
                    data.append( (f['name'], r[f['name']]) )
                s.append(render_func(data, r.get('_obj_', {})))
            result['rows'] = s
        result['total'] = self.total
        return result

    def objects(self):
        """
        Return a generator of all processed data, it just like render
        but it'll not return a table or json format data but just
        data. And the data will be processed by fields_convert_map if passed.
        """
        self.rows_num = 0
        query = self.query()
        if isinstance(query, Select):
            query = do_(query)
        for record in query:
            self.rows_num += 1
            r = self.object(record)
            self.cal_total(record)
            yield r
        total = self.render_total(True)
        if total:
            yield total
            
    def object(self, record):
        r = SortedDict()
        if not isinstance(record, dict):
            record = dict(zip(self.table_info['fields'], record))
        for i, x in enumerate(self.table_info['fields_list']):
            v = self.make_view_field(x, record, self.fields_convert_map)
            r[x['name']] = v['display']
        r['_obj_'] = record
        return r

    def json_body_render(self, data, record):
        d = dict(data)
        if 'id' not in d and hasattr(record, 'id'):
            d['id'] = getattr(record, 'id')
        return d
        
    def default_body_render(self, data, record):
        s = ['<tr>']
        for k, v in data:
            s.append('<td>%s</td>' % v)
        s.append('</tr>')
        return ''.join(s)

    def make_view_field(self, field, record, fields_convert_map):
        fields_convert_map = fields_convert_map or {}
        convert = None
        name = field['name']
        label = field.get('verbose_name', None) or field['name']
        if name in fields_convert_map:
            convert = fields_convert_map.get(name, None)
        value = record[name]
            
        if convert:
            display = convert(value, record)
        else:
            display = value
            
        if isinstance(display, unicode):
            display = display.encode('utf-8')
        if display is None:
            display = '&nbsp;'
            
        return {'label':label, 'value':value, 'display':display}
        
    def create_table_colgroup(self):
        s = []
        for f in self.table_info['fields_list']:
            s.append('<col width="%s"></col>\n' % f.get('width_str', '*'))
        return ''.join(s)
    
    def create_table_head(self):
        from uliweb.core.html import Tag
        from uliweb.utils.common import simple_value

        s = []
        fields = []
        max_rowspan = 0
        for i, f in enumerate(self.table_info['fields_name']):
            _f = list(f.split('/'))
            max_rowspan = max(max_rowspan, len(_f))
            fields.append((_f, i))
        
        def get_field(fields, i, m_rowspan):
            f_list, col = fields[i]
            field = {'name':f_list[0], 'col':col, 'width':self.table_info['fields_list'][col].get('width', 0), 'colspan':1, 'rowspan':1, 'title':self.table_info['fields_list'][col].get('help_string', '')}
            if len(f_list) == 1:
                field['rowspan'] = m_rowspan
            return field
        
        def remove_field(fields, i):
            del fields[i][0][0]
        
        def clear_fields(fields):
            for i in range(len(fields)-1, -1, -1):
                if len(fields[i][0]) == 0:
                    del fields[i]
                    
        n = len(fields)
        y = 0
        while n>0:
            i = 0
            s.append('<tr>')
            while i<n:
                field = get_field(fields, i, max_rowspan-y)
                remove_field(fields, i)
                j = i + 1
                while j<n:
                    field_n = get_field(fields, j, max_rowspan-y)
                    if simple_value(field['name']) == simple_value(field_n['name']) and field['rowspan'] == field_n['rowspan']:
                        #combine
                        remove_field(fields, j)
                        field['colspan'] += 1
                        field['width'] += field_n['width']
                        j += 1
                    else:
                        break
                kwargs = {}
                kwargs['align'] = 'left'
                if field['colspan'] > 1:
                    kwargs['colspan'] = field['colspan']
                    kwargs['align'] = 'center'
                if field['rowspan'] > 1:
                    kwargs['rowspan'] = field['rowspan']
#                _f = self.table_info['fields_list'][field['col']]
                kwargs['width'] = field['width']
                if not kwargs['width']:
                    kwargs['width'] = self.default_column_width
                _f = self.table_info['fields_list'][field['col']]
                kwargs['field'] = _f['name']
                if kwargs.get('rowspan', 1) + y != max_rowspan:
                    kwargs.pop('width', None)
                    kwargs.pop('field', None)
                
                s.append(str(Tag('th', field['name'], **kwargs)))
                
                i = j
            clear_fields(fields)
            s.append('</tr>\n')
            n = len(fields)
            y += 1
            
        return s
        
    def get_columns(self, frozen=None):
        from uliweb.utils.common import simple_value
    
        columns = []
        if frozen:
            columns = [[]]
        fields = []
        max_rowspan = 0
        for i, f in enumerate(self.table_info['fields_name']):
            _f = list(f.split('/'))
            max_rowspan = max(max_rowspan, len(_f))
            fields.append((_f, i))
        
        def get_field(fields, i, m_rowspan):
            f_list, col = fields[i]
            field = {'name':f_list[0], 'col':col, 'width':self.table_info['fields_list'][col].get('width', 0), 'colspan':1, 'rowspan':1, 'title':self.table_info['fields_list'][col].get('help_string', '')}
            if len(f_list) == 1:
                field['rowspan'] = m_rowspan
            return field
        
        def remove_field(fields, i):
            del fields[i][0][0]
        
        def clear_fields(fields):
            for i in range(len(fields)-1, -1, -1):
                if len(fields[i][0]) == 0:
                    del fields[i]
                    
        n = len(fields)
        y = 0
        while n>0:
            s = []
            i = 0
            while i<n:
                field = get_field(fields, i, max_rowspan-y)
                remove_field(fields, i)
                j = i + 1
                while j<n:
                    field_n = get_field(fields, j, max_rowspan-y)
                    if simple_value(field['name']) == simple_value(field_n['name']) and field['rowspan'] == field_n['rowspan']:
                        #combine
                        remove_field(fields, j)
                        field['colspan'] += 1
                        field['width'] += field_n['width']
                        j += 1
                    else:
                        break
                _f = self.table_info['fields_list'][field['col']].copy()
                kwargs = {}
                kwargs['field'] = _f.pop('name')
                _f.pop('verbose_name', None)
                _f.pop('prop', None)
                kwargs['title'] = simple_value(field['name'])
                span = False
                if field['colspan'] > 1:
                    kwargs['colspan'] = field['colspan']
                    span = True
                if field['rowspan'] > 1:
                    kwargs['rowspan'] = field['rowspan']
                    span = True
                #find the bottom column
                if kwargs.get('rowspan', 1) + y != max_rowspan:
                    _f.pop('width', None)
                    kwargs.pop('field', None)
                    _f.pop('title', None)
                else:
                    kwargs['width'] = _f.pop('width', self.default_column_width)
                kwargs.update(_f)
                frozen_flag = kwargs.pop('frozen', False)
                if frozen is None or frozen_flag is frozen:
                    s.append(kwargs)
                
                i = j
            clear_fields(fields)
            n = len(fields)
            y += 1
            if frozen:
                columns[0].extend(s)
            else:
                columns.append(s)
            
        return columns

    def get_table_info(self):
        t = {'fields_name':[], 'fields':[]}
        t['fields_list'] = self.fields
        
        for x in self.fields:
            t['fields_name'].append(x['verbose_name'])
            t['fields'].append(x['name'])
            
            w = x.get('width')
            if w:
                if isinstance(w, int):
                    width = '%dpx' % w
                else:
                    width = w
            else:
                width = '*'
            x['width_str'] = width

        return t
    
class ListView(SimpleListView):
    def __init__(self, model, condition=None, query=None, pageno=0, order_by=None, 
        fields=None, rows_per_page=10, types_convert_map=None, pagination=True,
        fields_convert_map=None, id='listview_table', table_class_attr='table', table_width=True,
        total_fields=None, template_data=None, default_column_width=100, 
        meta='Table', render=None):
        """
        If pageno is None, then the ListView will not paginate 
        """
        
        self.model = get_model(model)
        self.meta = meta
        self.condition = condition
        self.pageno = pageno
        self.order_by = order_by
        self.fields = fields
        self.rows_per_page = rows_per_page
        self.types_convert_map = types_convert_map or {}
        self.fields_convert_map = fields_convert_map or {}
        self.id = id
        self.rows_num = 0
        self._query = query
        self.table_width = table_width
        self.table_class_attr = table_class_attr
        self.total = 0
        self.pagination = pagination
        self.create_total_infos(total_fields)
        self.template_data = template_data or {}
        self.default_column_width = default_column_width
        self.downloader = GenericFileServing()
        self.render_func = render
        
        self.init()
        
    def init(self):
        super(ListView, self).init()
        
        if not self.id:
            self.id = self.model.tablename
        
        #create table header
        self.table_info = self.get_table_info()
        
    def query(self):
        if self._query is None or isinstance(self._query, (orm.Result, Select)): #query result
            offset = self.pageno*self.rows_per_page
            limit = self.rows_per_page
            query = self.query_model(self.model, self.condition, offset=offset, limit=limit, order_by=self.order_by)
            if isinstance(query, Select):
                self.total = self.model.count(query._whereclause)
            else:
                self.total = query.count()
        else:
            query = self.query_range(self.pageno, self.pagination)
        return query
    
    def object(self, record):
        r = SortedDict()
        for i, x in enumerate(self.table_info['fields_list']):
            if hasattr(self.model, x['name']):
                field = getattr(self.model, x['name'])
            else:
                field = x
            v = make_view_field(field, record, self.types_convert_map, self.fields_convert_map)
            r[x['name']] = v['display']
        r['_obj_'] = record
        return r
        
#    def get_field_display(self, record, field_name):
#        if hasattr(self.model, field_name):
#            field = getattr(self.model, field_name)
#        else:
#            for x in self.table_info['fields_list']:
#                if x['name'] == field_name:
#                    field = x
#        v = make_view_field(field, record, self.types_convert_map, self.fields_convert_map)
#        return v
#    
    def query_all(self):
        """
        Query all records without limit and offset.
        """
        return self.query_model(self.model, self.condition, order_by=self.order_by)
    
    def query_model(self, model, condition=None, offset=None, limit=None, order_by=None, fields=None):
        """
        Query all records with limit and offset, it's used for pagination query.
        """
        if self._query is not None:
            query = self._query
            if condition is not None and isinstance(query, Result):
                query = query.filter(condition)
        else:
            query = model.filter(condition)
        if self.pagination:
            if offset is not None:
                query = query.offset(int(offset))
            if limit is not None:
                query = query.limit(int(limit))
        if order_by is not None:
            if isinstance(order_by, (tuple, list)):
                for order in order_by:
                    query = query.order_by(order)
            else:
                query = query.order_by(order_by)
        return query
        
    def get_table_info(self):
        t = {'fields_name':[], 'fields_list':[], 'fields':[]}
    
        if self.fields:
            fields = self.fields
        elif hasattr(self.model, self.meta):
            fields = getattr(self.model, self.meta).fields
        else:
            fields = [x for x, y in self.model._fields_list]
            
        def get_table_meta_field(name):
            if hasattr(self.model, self.meta):
                for f in getattr(self.model, self.meta).fields:
                    if isinstance(f, dict):
                        if name == f['name']:
                            return f
                    elif isinstance(f, str):
                        return None
            
        fields_list = []
        for x in fields:
            if isinstance(x, (str, unicode)):
                name = x
                d = {'name':x}
                f = get_table_meta_field(name)
                if f:
                    d = f
            elif isinstance(x, dict):
                name = x['name']
                d = x
            if 'verbose_name' not in d:
                if hasattr(self.model, name):
                    d['verbose_name'] = getattr(self.model, name).verbose_name or name
                else:
                    d['verbose_name'] = name
            
            #process field width
            w = d.get('width')
            if w:
                if isinstance(w, int):
                    width = '%dpx' % w
                else:
                    width = w
            else:
                width = '*'
            d['width_str'] = width
            
            t['fields_list'].append(d)
            t['fields_name'].append(d['verbose_name'])
            t['fields'].append(name)
            
        return t
    
class QueryView(object):
    success_msg = _('The information has been saved successfully!')
    fail_msg = _('There are somethings wrong.')
    builds_args_map = {}
    meta = 'QueryForm'
    
    def __init__(self, model, ok_url, form=None, success_msg=None, fail_msg=None, 
        data=None, fields=None, form_cls=None, form_args=None,
        static_fields=None, hidden_fields=None, post_created_form=None, 
        layout=None, get_form_field=None, links=None):

        self.model = model
        self.ok_url = ok_url
        self.form = form
        if success_msg:
            self.success_msg = success_msg
        if fail_msg:
            self.fail_msg = fail_msg
        self.data = data or {}
        self.get_form_field = get_form_field
        
        #default_data used for create object
#        self.default_data = default_data or {}
        
        self.fields = fields or []
        self.form_cls = form_cls
        self.form_args = form_args or {}
        self.static_fields = static_fields or []
        self.hidden_fields = hidden_fields or []
        self.post_created_form = post_created_form
        self.links = links or []
        
        #add layout support
        self.layout = layout
        
    def get_fields(self):
        f = []
        for field_name, prop in get_fields(self.model, self.fields, self.meta):
            d = prop.copy()
            d['static'] = field_name in self.static_fields
            d['hidden'] = field_name in self.hidden_fields
            d['required'] = False
            f.append(d)
        return f
    
    def get_layout(self):
        if self.layout:
            return self.layout
        if hasattr(self.model, self.meta):
            m = getattr(self.model, self.meta)
            if hasattr(m, 'layout'):
                return getattr(m, 'layout')
    
    def make_form(self):
        import uliweb.form as form
        from uliweb.form.layout import QueryLayout
        
        if self.form:
            return self.form
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
            
        if self.form_cls:
            class DummyForm(self.form_cls):pass
            if not hasattr(DummyForm, 'form_buttons'):
                DummyForm.form_buttons = form.Button(value=_('Query'), _class="btn btn-primary", type='submit')
            if not hasattr(DummyForm, 'layout_class'):
                DummyForm.layout_class = QueryLayout
            if not hasattr(DummyForm, 'form_method'):
                DummyForm.form_method = 'GET'
#            if not hasattr(DummyForm, 'form_action') or not DummyForm.form_action:
#                DummyForm.form_action = request.path
        else:
            class DummyForm(form.Form):
                layout_class = QueryLayout
                form_method = 'GET'
                form_buttons = form.Button(value=_('Query'), _class="btn btn-primary", type='submit')
#                form_action = request.path
            
        #add layout support
        layout = self.get_layout()
        DummyForm.layout = layout
        
        for f in self.get_fields():
            flag = False
            if self.get_form_field:
                field = self.get_form_field(f['name'])
                if field:
                    flag = True
            if not flag:
                field = make_form_field(f, self.model, builds_args_map=self.builds_args_map)
            if field:
                DummyForm.add_field(f['name'], field, True)
        
        if self.post_created_form:
            self.post_created_form(DummyForm, self.model)
            
        form = DummyForm(data=self.data, **self.form_args)
        form.links = self.links
        return form
    
    def run(self):
        from uliweb import request
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
            
        if not self.form:
            self.form = self.make_form()
        
        flag = self.form.validate(request.values)
        if flag:
#            d = self.default_data.copy()
            if self.data:
                for k, v in self.data.iteritems():
                    if not self.form.data.get(k):
                        self.form.data[k] = v
            return self.form.data.copy()
        else:
            return {}
        
