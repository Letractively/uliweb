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
    def __init__(self, model, display_field=None, value_field='id', condition=None, query=None, label='', default=None, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, empty='', **kwargs):
        super(ReferenceSelectField, self).__init__(label=label, default=default, choices=[], required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, empty=empty, **kwargs)
        self.model = model
        self.display_field = display_field
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
        if not self.display_field:
            if hasattr(model, 'Meta'):
                self.display_field = getattr(model.Meta, 'display_field', 'id')
            else:
                self.display_field = 'id'
           
        if self.query:
            query = self.query
        else:
            query = model.all()
        if self.condition is not None:
            query = query.filter(self.condition)
        r = [(getattr(x, self.value_field), unicode(x)) for x in query]
        return r
    
    def to_python(self, data):
        return int(data)

class ManyToManySelectField(ReferenceSelectField):
    def __init__(self, model, display_field=None, value_field='id', 
            condition=None, query=None, label='', default=[], 
            required=False, validators=None, name='', html_attrs=None, 
            help_string='', build=None, **kwargs):
        super(ManyToManySelectField, self).__init__(model=model, display_field=display_field, 
            value_field=value_field, condition=condition, query=query, label=label, 
            default=default, required=required, validators=validators, name=name, 
            html_attrs=html_attrs, help_string=help_string, build=build, 
            empty=None, multiple=True, **kwargs)
            
def get_fields(model, fields, meta):
    if fields:
        fields_list = []
        for x in fields:
            if isinstance(x, str):  #so x is field_name
                fields_list.append((x, getattr(model, x)))
            elif isinstance(x, tuple):
                fields_list.append(x)   #x should be a tuple, just like (field_name, form_field_obj)
            else:
                raise Exception, 'Field definition is not right, it should be just like (field_name, form_field_obj)'
    elif hasattr(model, meta):
        fields_list = []
        for x in getattr(model, meta).fields:
            if isinstance(x, str):  #so x is field_name
                fields_list.append((x, getattr(model, x)))
            elif isinstance(x, tuple):
                fields_list.append(x)   #x should be a tuple, just like (field_name, form_field_obj)
            else:
                raise Exception, 'Field definition is not right, it should be just like (field_name, form_field_obj)'
            
    else:
        fields_list = [(x, y) for x, y in model._fields_list]
    
    return fields_list

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
    if v is not None:
        kwargs['default'] = v
        
    if field['static']:
        field_type = form.StringField
        kwargs['required'] = False
        kwargs['static'] = True
        
    if field['hidden']:
        field_type = form.HiddenField
        
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
                        s.append(unicode(x))
                display = ' '.join(s)
            elif isinstance(prop, orm.ReferenceProperty) or isinstance(prop, orm.OneToOne):
                v = getattr(obj, prop.property_name)
                if hasattr(v, 'get_url'):
                    display = v.get_url()
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
        post_created_form=None, layout=None, file_replace=True):

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
    
    def run(self):
        from uliweb import request, function
        from uliweb.orm import get_model
        from uliweb import redirect
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
            
        flash = function('flash')
        
        if not self.form:
            self.form = self.make_form()
        
        if request.method == 'POST':
            flag = self.form.validate(request.values, request.files)
            if flag:
                d = self.default_data.copy()
                d.update(self.form.data)
                
                if self.pre_save:
                    self.pre_save(d)
                    
                r = self.process_files(d)
                
                obj = self.save(d)
                
                if self.post_save:
                    self.post_save(obj, d)
                        
                flash(self.success_msg)
                return redirect(self.ok_url)
            else:
                flash(self.fail_msg, 'error')
                return {'form':self.form}
        else:
            return {'form':self.form}
        
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
                return redirect(self.ok_url)
            else:
                flash(self.fail_msg, 'error')
                return {'form':self.form, 'object':obj}
        else:
            return {'form':self.form, 'object':obj}
        
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
        if 'id' not in fields_name:
            d = {'name':'id', 'prop':self.model.id, 'static':False, 'hidden':False}
            fields_list.insert(0, d)
            fields_name.insert(0, 'id')
        
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
        types_convert_map=None, fields_convert_map=None, table_class_attr='table',
        layout_class=None, layout=None):
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
        
    def run(self):
        from uliweb.orm import get_model
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
        
        if not self.obj:
            obj = self.query()
        else:
            obj = self.obj
        view_text = self.render(obj)
        
        return {'object':obj, 'view':''.join(view_text)}
    
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
                view_text.append('<tr><th align="right" width=150>%s</th><td width=150>%s</td></tr>' % (field["label"], field["display"]))
                
        view_text.append('</table>')
        return view_text

class DeleteView(object):
    success_msg = _('The object has been deleted successfully!')

    def __init__(self, model, ok_url, condition=None, obj=None):
        self.model = model
        self.condition = condition
        self.obj = obj
        self.ok_url = ok_url
        
    def run(self):
        from uliweb.orm import get_model
        from uliweb import redirect, function
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
        
        self.delete()
        
        flash = function('flash')
        flash(self.success_msg)
        return redirect(self.ok_url)
    
    def delete(self):
        if not self.obj:
            obj = self.model.get(self.condition)
        else:
            obj = self.obj
            
        if obj:
            self.delete_manytomany(obj)
            obj.delete()
        
    def delete_manytomany(self, obj):
        for k, v in obj._manytomany.iteritems():
            getattr(obj, k).clear()
        
class SimpleListView(object):
    def __init__(self, fields=None, query=None, cache_file=None,  
        pageno=0, rows_per_page=10, id='listview_table', fields_convert_map=None, 
        table_class_attr='table', table_width=False, pagination=True):
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
                
        
    def download(self, filename, timeout=3600, inline=False, download=False):
        from uliweb.utils.filedown import filedown
        from uliweb import request, settings
        from uliweb.utils.common import simple_value, safe_unicode
        import csv
        
        if os.path.exists(filename):
            if not timeout or os.path.getmtime(filename) + timeout < time.time():
                return filedown(request.environ, filename, inline=inline, download=download)
            
        table = self.table_info()
        query = self.query(pagination=False)
        
        path = settings.get_var('GENERIC/DOWNLOAD_DIR', 'files')
        encoding = settings.get_var('GENERIC/ENCODING', sys.getfilesystemencoding() or 'utf-8')
        default_encoding = settings.get_var('GLOBAL/DEFAULT_ENCODING', 'utf-8')
        filename = os.path.join(path, filename)
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(filename, 'wb') as f:
            w = csv.writer(f)
            row = [safe_unicode(x, default_encoding) for x in table['fields_name']]
            w.writerow(simple_value(row, encoding))
            for record in query:
                row = []
                if isinstance(record, dict):
                    for x in table['fields']:
                        row.append(record[x]) 
                else:
                    row = record
                w.writerow(simple_value(row, encoding))
        return filedown(request.environ, filename, inline=inline, download=download)
        
    def run(self, head=True, body=True):
        #create table header
        table = self.table_info()
            
        query = self.query(self.pageno, self.pagination)
        if head:
            return {'table':self.render(table, head=head, body=body, query=query), 'info':{'total':self.total, 'rows_per_page':self.rows_per_page, 'pageno':self.pageno, 'id':self.id}}
        else:
            return {'table':self.render(table, head=head, body=body, query=query)}

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
        fields_convert_map=None, id='listview_table', table_class_attr='table', table_width=True):
        """
        If pageno is None, then the ListView will not paginate 
        """
            
        self.model = model
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
        if head:
            return {'table':self.render(table, query, head=head, body=body), 'info':{'total':self.total, 'rows_per_page':self.rows_per_page, 'pageno':self.pageno, 'id':self.id}}
        else:
            return {'table':self.render(table, query, head=head, body=body)}

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
        
        if head:
            s.append('</tbody>')
            s.append('</table>')
        
        return '\n'.join(s)
    
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
            query.order_by(order_by)
        return query
        
    def table_info(self):
        t = {'fields_name':[], 'fields_list':[]}
        is_table = False
    
        if self.fields:
            fields_list = []
            for x in self.fields:
                if isinstance(x, (str, unicode)):
                    if hasattr(self.model, x):
                        fields_list.append((x, getattr(self.model, x)))
                    else:
                        raise Exception, "Can't find the field [%s] in Model(%s)" % (x, self.model.tablename)
                elif isinstance(x, dict):
                    if 'label' not in x:
                        x['label'] = x.get('verbose_name', '')
                    fields_list.append((x['name'], x))
                else:
                    raise Exception, "Can't support the field [%r]" % x
        elif hasattr(self.model, 'Table'):
            fields_list = [(x['name'], getattr(self.model, x['name'])) for x in self.model.Table.fields]
            is_table = True
        else:
            fields_list = [(x, y) for x, y in self.model._fields_list]
        
        w = 0
        for i, (x, y) in enumerate(fields_list):
            if isinstance(y, dict):
                t['fields_name'].append(str(y['verbose_name'] or x))
            else:
                t['fields_name'].append(str(y.verbose_name or x))
            
            if is_table:
                t['fields_list'].append(self.model.Table.fields[i])
                w += self.model.Table.fields[i].get('width', 100)
            else:
                t['fields_list'].append({'name':x})
                w += 100
        t['width'] = w
        return t
    