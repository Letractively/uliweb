#coding=utf-8
from __future__ import with_statement
from uliweb.i18n import gettext_lazy as _
from uliweb.form import SelectField, BaseField
import os, sys
import time

__default_fields_builds__ = {}

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

class ReferenceSelectField(SelectField):
    def __init__(self, model, group_field=None, value_field='id', condition=None, query=None, label='', default=None, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, empty='', **kwargs):
        super(ReferenceSelectField, self).__init__(label=label, default=default, choices=None, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, empty=empty, **kwargs)
        self.model = model
        self.group_field = group_field
        self.value_field = value_field
        self.condition = condition
        self.query = query
        
    def get_choices(self):
        if self.choices:
            if callable(self.choices):
                return self.choices()
            else:
                return self.choices
            
        from uliweb.orm import get_model
        
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
        if self.condition is not None:
            query = query.filter(self.condition)
        if self.group_field:
            query = query.order_by(model.c[self.group_field].asc())
        if self.group_field:
            r = [(x.get_display_value(self.group_field), getattr(x, self.value_field), unicode(x)) for x in query]
        else:
            r = [(getattr(x, self.value_field), unicode(x)) for x in query]
        return r
    
    def to_python(self, data):
        return int(data)

class ManyToManySelectField(ReferenceSelectField):
    def __init__(self, model, group_field=None, value_field='id', 
            condition=None, query=None, label='', default=[], 
            required=False, validators=None, name='', html_attrs=None, 
            help_string='', build=None, **kwargs):
        super(ManyToManySelectField, self).__init__(model=model, group_field=group_field, 
            value_field=value_field, condition=condition, query=query, label=label, 
            default=default, required=required, validators=validators, name=name, 
            html_attrs=html_attrs, help_string=help_string, build=build, 
            empty=None, multiple=True, **kwargs)
            
def get_fields(model, fields, meta):
    if fields is not None:
        f = fields
    elif hasattr(model, meta):
        f = getattr(model, meta).fields
    else:
        f = model._fields_list
        
    fields_list = []
    for x in f:
        if isinstance(x, str):  #so x is field_name
            fields_list.append((x, getattr(model, x)))
        elif isinstance(x, tuple):
            fields_list.append(x)   #x should be a tuple, just like (field_name, form_field_obj)
        else:
            raise Exception, 'Field definition is not right, it should be just like (field_name, form_field_obj)'
    return fields_list

def get_url(ok_url, *args):
    if callable(ok_url):
        return ok_url(*args)
    else:
        return ok_url
    
def make_form_field(field, model, field_cls=None, builds_args_map=None):
    import uliweb.orm as orm
    import uliweb.form as form
    
    field_type = None
    prop = field['prop']
    if isinstance(prop, BaseField): #if the prop is already Form.BaseField, so just return it
        return prop
    
    kwargs = dict(label=prop.verbose_name or prop.property_name, 
        name=prop.property_name, required=prop.required, help_string=prop.hint)
    
    v = prop.default_value()
#    if v is not None:
    kwargs['default'] = v
        
    if field['static']:
        field_type = form.StringField
        kwargs['required'] = False
        kwargs['static'] = True
        
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
            if not prop.auto_now and not prop.auto_now_add:
                field_type = form.DateField
        elif cls is orm.TimeProperty:
            if not prop.auto_now and not prop.auto_now_add:
                field_type = form.TimeField
        elif cls is orm.DateTimeProperty:
            if not prop.auto_now and not prop.auto_now_add:
                field_type = form.DateTimeField
        elif cls is orm.DecimalProperty:
            field_type = form.StringField
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
        f = field_type(**kwargs)
    
        return f

def make_view_field(prop, obj, types_convert_map=None, fields_convert_map=None):
    import uliweb.orm as orm
    from uliweb.utils.textconvert import text2html
    from uliweb.core.html import Tag
    from uliweb import settings

    types_convert_map = types_convert_map or {}
    fields_convert_map = fields_convert_map or {}
    default_convert_map = {orm.TextProperty:lambda v,o:text2html(v)}
    
    #not real Property instance, then return itself, so if should return
    #just like {'label':xxx, 'value':xxx, 'display':xxx}
    if not isinstance(prop, orm.Property):  
        value = prop.get('value', '')
        display = prop.get('display', '')
        label = prop.get('label', '')
        name = prop.get('name', '')
        convert = prop.get('convert', None)
    else:
        value = prop.get_value_for_datastore(obj)
        display = value
        name = prop.property_name
        label = prop.verbose_name or prop.property_name
        
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
                for x in getattr(obj, prop.property_name).all():
                    if hasattr(x, 'get_url'):
                        s.append(x.get_url())
                    else:
                        url_prefix = settings.get_var('MODEL_URL/'+x.tablename)
                        if url_prefix:
                            if url_prefix.endswith('/'):
                                url_prefix = url_prefix[:-1]
                            s.append(str(Tag('a', unicode(x), href=url_prefix+'/'+str(x.id))))
                        else:
                            s.append(unicode(x))
                display = ' '.join(s)
            elif isinstance(prop, orm.ReferenceProperty) or isinstance(prop, orm.OneToOne):
                try:
                    v = getattr(obj, prop.property_name)
                except orm.Error:
                    display = obj.get_datastore_value(prop.property_name)
                    v = None
                if v:
                    if hasattr(v, 'get_url'):
                        display = v.get_url()
                    else:
                        url_prefix = settings.get_var('MODEL_URL/'+v.tablename)
                        if url_prefix:
                            if url_prefix.endswith('/'):
                                url_prefix = url_prefix[:-1]
                            display = str(Tag('a', unicode(v), href=url_prefix+'/'+str(v.id)))
                        else:
                            display = unicode(v)
            elif isinstance(prop, orm.FileProperty):
                from uliweb.contrib.upload import get_url
                filename = getattr(obj, prop.property_name)
                url = get_url(filename)
                if url:
                    display = str(Tag('a', filename, href=url))
                else:
                    display = ''
            if isinstance(prop, orm.Property) and prop.choices is not None:
                display = prop.get_display_value(value)
            if prop.__class__ is orm.TextProperty:
                display = text2html(value)
        
    if isinstance(display, unicode):
        display = display.encode('utf-8')
    if display is None:
        display = '&nbsp;'
        
    return {'label':label, 'value':value, 'display':display}

class AddView(object):
    success_msg = _('The information has been saved successfully!')
    fail_msg = _('There are somethings wrong.')
    builds_args_map = {}
    meta = 'AddForm'
    
    def __init__(self, model, ok_url, form=None, success_msg=None, fail_msg=None, 
        data=None, default_data=None, fields=None, form_cls=None, form_args=None,
        static_fields=None, hidden_fields=None, pre_save=None, post_save=None,
        post_created_form=None, layout=None, file_replace=True, template_data=None):

        self.model = model
        self.ok_url = ok_url
        self.form = form
        if success_msg:
            self.success_msg = success_msg
        if fail_msg:
            self.fail_msg = fail_msg
        self.data = data or {}
        self.template_data = template_data or {}
        
        #default_data used for create object
        self.default_data = default_data or {}
        
        self.fields = fields
        self.form_cls = form_cls
        self.form_args = form_args or {}
        self.static_fields = static_fields or []
        self.hidden_fields = hidden_fields or []
        self.pre_save = pre_save
        self.post_save = post_save
        self.post_created_form = post_created_form
        self.file_replace = file_replace
        
        #add layout support
        self.layout = layout
        
    def get_fields(self):
        f = []
        for field_name, prop in get_fields(self.model, self.fields, self.meta):
            d = {'name':field_name, 
                'prop':prop, 
                'static':field_name in self.static_fields,
                'hidden':field_name in self.hidden_fields}
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
        import uliweb.orm as orm
        import uliweb.form as form
        
        if self.form:
            return self.form
        
        if isinstance(self.model, str):
            self.model = orm.get_model(self.model)
            
        if self.form_cls:
            class DummyForm(self.form_cls):pass
            if not hasattr(DummyForm, 'form_buttons'):
                DummyForm.form_buttons = form.Submit(value=_('Create'), _class=".submit")
           
        else:
            class DummyForm(form.Form):
                form_buttons = form.Submit(value=_('Create'), _class=".submit")
            
        #add layout support
        layout = self.get_layout()
        DummyForm.layout = layout
        
        for f in self.get_fields():
            field = make_form_field(f, self.model, builds_args_map=self.builds_args_map)
            
            if field:
                DummyForm.add_field(f['name'], field, True)
        
        if self.post_created_form:
            self.post_created_form(DummyForm, self.model)
            
        return DummyForm(data=self.data, **self.form_args)
    
    def process_files(self, data):
        from uliweb.contrib.upload import save_file
        import uliweb.orm as orm
        
        flag = False
    
        fields_list = self.get_fields()
        for f in fields_list:
            if isinstance(f['prop'], orm.FileProperty):
                if f['name'] in data:
                    fobj = data[f['name']]
                    if fobj:
                        data[f['name']] = save_file(fobj['filename'], fobj['file'], replace=self.file_replace)
                        flag = True
                    
        return flag
    
    def on_success(self, d):
        from uliweb import function
        from uliweb import redirect
        flash = function('flash')

        if self.pre_save:
            self.pre_save(d)
            
        r = self.process_files(d)
        
        obj = self.save(d)
        
        if self.post_save:
            self.post_save(obj, d)
                
        flash(self.success_msg)
        return redirect(get_url(self.ok_url, obj.id))
    
    def run(self):
        from uliweb import request, function
        from uliweb.orm import get_model
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
            
        flash = function('flash')
        
        if not self.form:
            self.form = self.make_form()
        
        result = self.template_data.copy()
        if request.method == 'POST':
            flag = self.form.validate(request.values, request.files)
            if flag:
                d = self.default_data.copy()
                d.update(self.form.data)
                return self.on_success(d)
            else:
                flash(self.fail_msg, 'error')
                
        result.update({'form':self.form})
        return result
        
    def save(self, data):
        obj = self.model(**data)
        obj.save()
        
        self.save_manytomany(obj, data)
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
    meta = 'EditForm'
    
    def __init__(self, model, ok_url, condition=None, obj=None, **kwargs):
        AddView.__init__(self, model, ok_url, **kwargs)
        self.condition = condition
        self.obj = obj
        
    def run(self):
        from uliweb import request, function
        from uliweb import redirect
        import uliweb.orm as orm
        
        if isinstance(self.model, str):
            self.model = orm.get_model(self.model)
        
        flash = function('flash')
        
        if not self.obj:
            obj = self.query()
        else:
            obj = self.obj
        
        if not self.form:
            self.form = self.make_form(obj)
            
        #binding obj to self.form.object
        self.form.object = obj
        
        result = self.template_data.copy()
        if request.method == 'POST':
            flag = self.form.validate(request.values, request.files)
            if flag:
                data = self.form.data.copy()
                if self.pre_save:
                    self.pre_save(obj, data)
                #process file field
                r = self.process_files(data)
                r = self.save(obj, data) or r
                if self.post_save:
                    r = self.post_save(obj, data) or r
                
                if r:
                    msg = self.success_msg
                else:
                    msg = _("The object has not been changed.")
                flash(msg)
                return redirect(get_url(self.ok_url, obj.id))
            else:
                flash(self.fail_msg, 'error')
        result.update({'form':self.form, 'object':obj})
        return result
        
    def save(self, obj, data):
        obj.update(**data)
        r = obj.save()
        
        r1 = self.save_manytomany(obj, data)
        return r or r1
        
    def save_manytomany(self, obj, data):
        #process manytomany property
        r = False
        for k, v in obj._manytomany.iteritems():
            if k in data:
                field = getattr(obj, k)
                value = data[k]
                if value:
                    r = r or getattr(obj, k).update(*value)
                else:
                    getattr(obj, k).clear()
        return r
        
    def query(self):
        return self.model.get(self.condition)
    
    def make_form(self, obj):
        import uliweb.orm as orm
        import uliweb.form as form
        
        if self.form:
            return self.form

        if self.form_cls:
            class DummyForm(self.form_cls):pass
            if not hasattr(DummyForm, 'form_buttons'):
                DummyForm.form_buttons = form.Submit(value=_('Save'), _class=".submit")
           
        else:
            class DummyForm(form.Form):
                form_buttons = form.Submit(value=_('Save'), _class=".submit")
            
        fields_list = self.get_fields()
        fields_name = [x['name'] for x in fields_list]
#        if 'id' not in fields_name:
#            d = {'name':'id', 'prop':self.model.id, 'static':False, 'hidden':False}
#            fields_list.insert(0, d)
#            fields_name.insert(0, 'id')
        
        data = obj.to_dict(fields_name, convert=False).copy()
        data.update(self.data)
        
        for f in fields_list:
            if f['name'] == 'id':
                f['hidden'] = True
            elif isinstance(f['prop'], orm.IntegerProperty) and 'autoincrement' in f['prop'].kwargs:
                f['hidden'] = True
                
            field = make_form_field(f, self.model, builds_args_map=self.builds_args_map)
            
            if field:
                DummyForm.add_field(f['name'], field, True)
                
                if isinstance(f['prop'], orm.ManyToMany):
                    value = getattr(obj, f['name']).ids()
                    data[f['name']] = value
        
        if self.post_created_form:
            self.post_created_form(DummyForm, self.model, obj)
            
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
    def __init__(self, layout_file, get_field, writer=None):
        self.layout_file = layout_file
        self.writer = writer or DetailWriter(get_field)
        
    def get_text(self):
        from uliweb import application
        f = file(application.get_file(self.layout_file, dir='templates'), 'rb')
        text = f.read()
        f.close()
        return text
    
    def __str__(self):
        return str(uaml.Parser(self.get_text(), self.writer))
    
class DetailView(object):
    types_convert_map = {}
    fields_convert_map = {}
    meta = 'DetailView'
    
    def __init__(self, model, condition=None, obj=None, fields=None, 
        types_convert_map=None, fields_convert_map=None, table_class_attr='table width100',
        layout_class=None, layout=None, template_data=None):
        self.model = model
        self.condition = condition
        self.obj = obj
        self.fields = fields
        if self.types_convert_map:
            self.types_convert_map = types_convert_map
        if self.fields_convert_map:
            self.fields_convert_map = fields_convert_map or {}
        self.table_class_attr = table_class_attr
        self.layout_class = layout_class or DetailLayout
        self.layout = layout
        self.template_data = template_data or {}
        
    def run(self):
        from uliweb.orm import get_model
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
        
        if not self.obj:
            obj = self.query()
        else:
            obj = self.obj
        view_text = self.render(obj)
        
        result = self.template_data.copy()
        result.update({'object':obj, 'view':''.join(view_text)})
        return result
    
    def query(self):
        return self.model.get(self.condition)
    
    def render(self, obj):
        if self.layout:
            fields = dict(get_fields(self.model, self.fields, self.meta))
            def get_field(name):
                prop = fields[name]
                return make_view_field(prop, obj, self.types_convert_map, self.fields_convert_map)
            
            return str(self.layout_class(self.layout, get_field))
        else:
            return self._render(obj)
        
    def _render(self, obj):
        view_text = ['<table class="%s">' % self.table_class_attr]
        for field_name, prop in get_fields(self.model, self.fields, self.meta):
            field = make_view_field(prop, obj, self.types_convert_map, self.fields_convert_map)
            
            if field:
                view_text.append('<tr><th align="right" width=150>%s</th><td>%s</td></tr>' % (field["label"], field["display"]))
                
        view_text.append('</table>')
        return view_text

class DeleteView(object):
    success_msg = _('The object has been deleted successfully!')

    def __init__(self, model, ok_url, condition=None, obj=None, pre_delete=None, post_delete=None):
        self.model = model
        self.condition = condition
        self.obj = obj
        self.ok_url = ok_url
        self.pre_delete = pre_delete
        self.post_delete = post_delete
        
    def run(self):
        from uliweb.orm import get_model
        from uliweb import redirect, function
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
        
        if not self.obj:
            obj = self.model.get(self.condition)
        else:
            obj = self.obj
            
        if self.pre_delete:
            self.pre_delete(obj)
        self.delete(obj)
        if self.post_delete:
            self.post_delete()
        
        flash = function('flash')
        flash(self.success_msg)
        return redirect(self.ok_url)
    
    def delete(self, obj):
        if obj:
            self.delete_manytomany(obj)
            obj.delete()
        
    def delete_manytomany(self, obj):
        for k, v in obj._manytomany.iteritems():
            getattr(obj, k).clear()
        
class SimpleListView(object):
    def __init__(self, fields=None, query=None, cache_file=None,  
        pageno=0, rows_per_page=10, id='listview_table', fields_convert_map=None, 
        table_class_attr='table', table_width=False, pagination=True, total_fields=None, template_data=None):
        """
        Pass a data structure to fields just like:
            [
                {'name':'field_name', 'verbose_name':'Caption', 'width':100},
                ...
            ]
        """
        self.fields = fields
        self._query = query
        self.pageno = pageno
        self.rows_per_page = rows_per_page
        self.id = id
        self.table_class_attr = table_class_attr
        self.fields_convert_map = fields_convert_map
        self.cache_file = cache_file
        self.total = 0
        self.table_width = table_width
        self.pagination = pagination
        self.create_total_infos(total_fields)
        self.template_data = template_data or {}
        
    def create_total_infos(self, total_fields):
        if total_fields:
            self.total_fields = total_fields['fields']
            self.total_field_name = total_fields.get('total_field_name', _('Total'))
        else:
            self.total_fields = []
            self.total_field_name = None
        self.total_sums = {}
            
    def cal_total(self, table, record):
        if self.total_fields:
            for f in self.total_fields:
                if isinstance(record, (tuple, list)):
                    i = table['fields'].index(f)
                    v = record[i]
                elif isinstance(record, dict):
                    v = record.get(f)
                else:
                    v = getattr(record, f)
                self.total_sums[f] = self.total_sums.setdefault(f, 0) + v
                
    def get_total(self, table):
        s = []
        if self.total_fields:
            for i, f in enumerate(table['fields']):
                if i == 0:
                    v = self.total_field_name
                else:
                    if f in self.total_fields:
                        v = self.total_sums.get(f, 0)
                    else:
                        v = ''
                s.append(v)
        return s

    def render_total(self, table):
        s = []
        if self.total_fields:
            s.append('<tr class="sum">')
            for v in self.get_total(table):
                v = str(v) or '&nbsp;'
                s.append('<td>%s</td>' % v)
            s.append('</tr>')
        return s
    
    def query_all(self):
        return self.query(pagination=False)
    
    def query(self, pageno=0, pagination=True):
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
        
        self.total = 0
        if pagination:
            if isinstance(query_result, (list, tuple)):
                self.total = len(query_result)
                return query_result[pageno*self.rows_per_page : (pageno+1)*self.rows_per_page]
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
                
        
    def download(self, filename, timeout=3600, inline=False, download=False, query=None, fields_convert_map=None):
        from uliweb.utils.filedown import filedown
        from uliweb import request, settings
        from uliweb.utils.common import simple_value, safe_unicode
        from uliweb.orm import Model
        import tempfile
        import csv
        fields_convert_map = fields_convert_map or {}
        
        if os.path.exists(filename):
            if timeout and os.path.getmtime(filename) + timeout > time.time():
                return filedown(request.environ, filename, inline=inline, download=download)
            
        table = self.table_info()
        if not query:
            query = self.query_all()
        path = settings.get_var('GENERIC/DOWNLOAD_DIR', 'files')
        encoding = settings.get_var('GENERIC/CSV_ENCODING', sys.getfilesystemencoding() or 'utf-8')
        default_encoding = settings.get_var('GLOBAL/DEFAULT_ENCODING', 'utf-8')
        t_filename = os.path.join(path, filename)
        r_filename = os.path.basename(filename)
        dirname = os.path.dirname(t_filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with tempfile.NamedTemporaryFile(suffix = ".tmp", prefix = "workload_", dir=dirname, delete = False) as f:
            t_filename = f.name
            w = csv.writer(f)
            row = [safe_unicode(x, default_encoding) for x in table['fields_name']]
            w.writerow(simple_value(row, encoding))
            for record in query:
                self.cal_total(table, record)
                row = []
                if isinstance(record, dict):
                    for x in table['fields']:
                        row.append(record[x]) 
                elif isinstance(record, Model):
                    row = []
                    for x in table['fields']:
                        if hasattr(record, x):
                            row.append(safe_unicode(record.get_display_value(x), default_encoding))
                        else:
                            row.append('')
                elif not isinstance(record, (tuple, list)):
                    row = list(record)
                else:
                    row = record
                if fields_convert_map:
                    for i, x in enumerate(table['fields']):
                        convert = fields_convert_map.get(x)
                        if convert:
                            row[i] = convert(row[i], record)
                w.writerow(simple_value(row, encoding))
            total = self.get_total(table)
            if total:
                row = []
                for x in total:
                    v = x
                    if isinstance(x, str):
                        v = safe_unicode(x, default_encoding)
                    row.append(v)
                w.writerow(simple_value(row, encoding))
        return filedown(request.environ, r_filename, real_filename=t_filename, inline=inline, download=download)
        
    def run(self, head=True, body=True):
        #create table header
        table = self.table_info()
            
        query = self.query(self.pageno, self.pagination)
        result = self.template_data.copy()
        if head:
            result.update({'table':self.render(table, head=head, body=body, query=query), 'info':{'total':self.total, 'rows_per_page':self.rows_per_page, 'pageno':self.pageno, 'id':self.id}})
        else:
            result.update({'table':self.render(table, head=head, body=body, query=query)})
        return result

    def render(self, table, head=True, body=True, query=None):
        """
        table is a dict, just like
        table = {'fields_name':[fieldname,...],
            'fields_list':[{'name':fieldname,'width':100,'align':'left'},...],
            'total':10,
        """
        from uliweb.core.html import Tag

        s = []
        if head:
            if self.table_width:
                width = ' width="%dpx"' % table['width']
            else:
                width = ''
                
            s = ['<table class="%s" id=%s%s>' % (self.table_class_attr, self.id, width)]
            s.append('<thead>')
            s.extend(self.create_table_head(table))
            s.append('</thead>')
            s.append('<tbody>')
        
        if body:
            #create table body
            for record in query:
                s.append('<tr>')
                if not isinstance(record, dict):
                    record = dict(zip(table['fields'], record))
                for i, x in enumerate(table['fields_list']):
                    v = self.make_view_field(x, record, self.fields_convert_map)
                    s.append(str(Tag('td', v['display'])))
                s.append('</tr>')
                self.cal_total(table, record)
            s.extend(self.render_total(table))
        
        if head:
            s.append('</tbody>')
            s.append('</table>')
        
        return '\n'.join(s)
    
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
        
    def create_table_head(self, table):
        from uliweb.core.html import Tag

        s = []
        fields = []
        max_rowspan = 0
        for i, f in enumerate(table['fields_name']):
            _f = list(f.split('/'))
            max_rowspan = max(max_rowspan, len(_f))
            fields.append((_f, i))
        
        def get_field(fields, i, m_rowspan):
            f_list, col = fields[i]
            field = {'name':f_list[0], 'col':col, 'width':table['fields_list'][col].get('width', 0), 'colspan':1, 'rowspan':1}
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
                    if field['name'] == field_n['name'] and field['rowspan'] == field_n['rowspan']:
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
                if field['width']:
                    kwargs['width'] = field['width']
#                else:
#                    kwargs['width'] = '100'
                s.append(str(Tag('th', field['name'], **kwargs)))
                
                i = j
            clear_fields(fields)
            s.append('</tr>\n')
            n = len(fields)
            y += 1
            
        return s
        
    def table_info(self):
        t = {'fields_name':[], 'fields':[]}
        t['fields_list'] = self.fields
        
        w = 0
        for x in self.fields:
            t['fields_name'].append(x['verbose_name'])
            t['fields'].append(x['name'])
            w += x.get('width', 0)
            
        t['width'] = w
        return t
    
class ListView(SimpleListView):
    def __init__(self, model, condition=None, query=None, pageno=0, order_by=None, 
        fields=None, rows_per_page=10, types_convert_map=None, pagination=True,
        fields_convert_map=None, id='listview_table', table_class_attr='table', table_width=True,
        total_fields=None, template_data=None):
        """
        If pageno is None, then the ListView will not paginate 
        """
        from uliweb.orm import get_model
            
        self.model = get_model(model)
        self.condition = condition
        self.pageno = pageno
        self.order_by = order_by
        self.fields = fields
        self.rows_per_page = rows_per_page
        self.types_convert_map = types_convert_map
        self.fields_convert_map = fields_convert_map
        self.id = id
        self._query = query
        self.table_width = table_width
        self.table_class_attr = table_class_attr
        self.total = 0
        self.pagination = pagination
        self.create_total_infos(total_fields)
        self.template_data = template_data or {}
        
    def run(self, head=True, body=True):
        import uliweb.orm as orm
        
        if isinstance(self.model, str):
            self.model = orm.get_model(self.model)
            
        if not self.id:
            self.id = self.model.tablename
        
        #create table header
        table = self.table_info()
            
        if not self._query or isinstance(self._query, orm.Result): #query result
            offset = self.pageno*self.rows_per_page
            limit = self.rows_per_page
            query = self.query_model(self.model, self.condition, offset=offset, limit=limit, order_by=self.order_by)
            self.total = query.count()
        else:
            query = self.query(self.pageno, self.pagination)
        result = self.template_data.copy()
        if head:
            result.update({'table':self.render(table, query, head=head, body=body), 'info':{'total':self.total, 'rows_per_page':self.rows_per_page, 'pageno':self.pageno, 'id':self.id}})
        else:
            result.update({'table':self.render(table, query, head=head, body=body)})
        return result

    def render(self, table, query, head=True, body=True):
        """
        table is a dict, just like
        table = {'fields_name':[fieldname,...],
            'fields_list':[{'name':fieldname,'width':100,'align':'left'},...],
            'count':10,
        """
        from uliweb.core.html import Tag

        s = []
        if head:
            if self.table_width:
                width = ' width="%dpx"' % table['width']
            else:
                width = ''
            s = ['<table class="%s" id=%s%s>' % (self.table_class_attr, self.id, width)]
            s.append('<thead>')
            s.extend(self.create_table_head(table))
            s.append('</thead>')
            s.append('<tbody>')
        
        if body:
            #create table body
            for record in query:
                s.append('<tr>')
                for i, x in enumerate(table['fields_list']):
                    if hasattr(self.model, x['name']):
                        field = getattr(self.model, x['name'])
                    else:
                        field = x
                    v = make_view_field(field, record, self.types_convert_map, self.fields_convert_map)
                    s.append(str(Tag('td', v['display'])))
                s.append('</tr>')
                self.cal_total(table, record)
            s.extend(self.render_total(table))
                
        if head:
            s.append('</tbody>')
            s.append('</table>')
        
        return '\n'.join(s)
    
    def query_all(self):
        return self.query_model(self.model, self.condition, order_by=self.order_by)
    
    def query_model(self, model, condition=None, offset=None, limit=None, order_by=None, fields=None):
        if self._query:
            query = self._query.filter(condition)
        else:
            query = model.filter(condition)
        if offset is not None:
            query.offset(int(offset))
        if limit is not None:
            query.limit(int(limit))
        if order_by is not None:
            if isinstance(order_by, (tuple, list)):
                for order in order_by:
                    query.order_by(order)
            else:
                query.order_by(order_by)
        return query
        
    def table_info(self):
        t = {'fields_name':[], 'fields_list':[], 'fields':[]}
    
        if self.fields:
            fields = self.fields
        elif hasattr(self.model, 'Table'):
            fields = self.model.Table.fields
        else:
            fields = [x for x, y in self.model._fields_list]
            
        w = 0
        fields_list = []
        for x in fields:
            if isinstance(x, (str, unicode)):
                name = x
                d = {'name':x}
            elif isinstance(x, dict):
                name = x['name']
                d = x
            if 'verbose_name' not in d:
                if hasattr(self.model, name):
                    d['verbose_name'] = getattr(self.model, name).verbose_name or name
                else:
                    d['verbose_name'] = name
            t['fields_list'].append(d)
            t['fields_name'].append(d['verbose_name'])
            t['fields'].append(name)
            w += d.get('width', 100)
            
        t['width'] = w
        return t
    
class QueryView(object):
    success_msg = _('The information has been saved successfully!')
    fail_msg = _('There are somethings wrong.')
    builds_args_map = {}
    meta = 'QueryForm'
    
    def __init__(self, model, ok_url, form=None, success_msg=None, fail_msg=None, 
        data=None, default_data=None, fields=None, form_cls=None, form_args=None,
        static_fields=None, hidden_fields=None, post_created_form=None, layout=None):

        self.model = model
        self.ok_url = ok_url
        self.form = form
        if success_msg:
            self.success_msg = success_msg
        if fail_msg:
            self.fail_msg = fail_msg
        self.data = data or {}
        
        #default_data used for create object
        self.default_data = default_data or {}
        
        self.fields = fields or []
        self.form_cls = form_cls
        self.form_args = form_args or {}
        self.static_fields = static_fields or []
        self.hidden_fields = hidden_fields or []
        self.post_created_form = post_created_form
        
        #add layout support
        self.layout = layout
        
    def get_fields(self):
        f = []
        for field_name, prop in get_fields(self.model, self.fields, self.meta):
            d = {'name':field_name, 
                'prop':prop, 
                'static':field_name in self.static_fields,
                'hidden':field_name in self.hidden_fields,
                'required':False}
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
        import uliweb.orm as orm
        import uliweb.form as form
        from uliweb.form.layout import QueryLayout
        
        if self.form:
            return self.form
        
        if isinstance(self.model, str):
            self.model = orm.get_model(self.model)
            
        if self.form_cls:
            class DummyForm(self.form_cls):pass
            if not hasattr(DummyForm, 'form_buttons'):
                DummyForm.form_buttons = form.Submit(value=_('Query'), _class=".submit")
            if not hasattr(DummyForm, 'layout_class'):
                DummyForm.layout_class = QueryLayout
            if not hasattr(DummyForm, 'form_method'):
                DummyForm.form_method = 'GET'
        else:
            class DummyForm(form.Form):
                layout_class = QueryLayout
                form_method = 'GET'
                form_buttons = form.Submit(value=_('Query'), _class=".submit")
            
        #add layout support
        layout = self.get_layout()
        DummyForm.layout = layout
        
        for f in self.get_fields():
            field = make_form_field(f, self.model, builds_args_map=self.builds_args_map)
            
            if field:
                DummyForm.add_field(f['name'], field, True)
        
        if self.post_created_form:
            self.post_created_form(DummyForm, self.model)
            
        return DummyForm(data=self.data, **self.form_args)
    
    def run(self):
        from uliweb import request, function
        from uliweb.orm import get_model
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
            
        flash = function('flash')
        
        if not self.form:
            self.form = self.make_form()
        
        flag = self.form.validate(request.values)
        if flag:
            d = self.default_data.copy()
            d.update(self.form.data)
            return d
        else:
            return {}
        
