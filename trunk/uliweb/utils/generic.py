#coding=utf-8
from uliweb.i18n import gettext_lazy as _
from uliweb.form import SelectField

class ReferenceSelectField(SelectField):
    def __init__(self, model, value_field=None, key_field='id', condition=None, label='', default=None, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, empty='', **kwargs):
        SelectField.__init__(self, label=label, default=default, choices=[], required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, empty=empty, **kwargs)
        self.model = model
        self.value_field = value_field
        self.key_field = key_field
        self.condition = condition
    
    def get_choices(self):
        from uliweb.orm import get_model
        
        model = get_model(self.model)
        if not self.value_field:
            if hasattr(model, 'Meta'):
                self.value_field = getattr(model.Meta, 'display_field', 'id')
        else:
            self.value_field = 'id'
            
        return list(model.all().values(self.key_field, self.value_field))
    
    def to_python(self, data):
        return int(data)

class ManyToManySelectField(ReferenceSelectField):
    def __init__(self, model, value_field=None, key_field='id', condition=None, label='', default=None, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, **kwargs):
        ReferenceSelectField.__init__(self, model=model, value_field=value_field, key_field=key_field, condition=condition, label=label, default=default, required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, empty=True, multiple=True, **kwargs)
  
def get_fields(model, fields, meta):
    if fields:
        fields_list = [(x, getattr(model, x)) for x in fields]
    elif hasattr(model, meta):
        fields_list = [(x, getattr(model, x)) for x in getattr(model, meta).fields]
    else:
        fields_list = [(x, y) for x, y in model._fields_list]
    
    return fields_list

def make_form_field(field, model, field_cls=None, builds_args_map=None):
    import uliweb.orm as orm
    import uliweb.form as form
    
    field_type = None
    prop = field['prop']
    
    kwargs = dict(label=prop.verbose_name or prop.property_name, default=prop.default, 
        name=prop.property_name, required=prop.required, help_string=prop.hint)
    if field['disabled']:
        kwargs['disabled'] = None
    if field['hidden']:
        field_type = form.HiddenField
        
    if field_cls:
        field_type = field_cls
    else:
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
                field_type = form.StringField
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
        else:
            raise Exception, "Can't support the Property [%s=%s]" % (field['name'], prop.__class__.__name__)
        
    if field_type:
        build_args = builds_args_map.get(field_type, {})
        kwargs.update(build_args)
        f = field_type(**kwargs)
    
        return f

def make_view_field(prop, obj, types_convert_map=None, fields_convert_map=None):
    import uliweb.orm as orm
    from uliweb.utils.common import get_choice
    from uliweb.utils.textconvert import text2html

    types_convert_map = types_convert_map or {}
    fields_convert_map = fields_convert_map or {}
    default_convert_map = {orm.TextProperty:lambda v,o:text2html(v)}
    
    value = prop.get_value_for_datastore(obj)
    display = value
        
    if prop.property_name in fields_convert_map:
        convert = fields_convert_map.get(prop.property_name, None)
    else:
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
            if prop.choices is not None:
                display = get_choice(prop.choices, value)
        
    if isinstance(display, unicode):
        display = display.encode('utf-8')
    if display is None:
        display = ''
    
    return {'label':prop.verbose_name or prop.property_name, 'value':value, 'display':display}

class AddView(object):
    success_msg = _('The information has been saved successfully!')
    fail_msg = _('There are somethings wrong.')
    builds_args_map = {}
    
    def __init__(self, model, ok_url, form=None, success_msg=None, fail_msg=None, 
        data=None, default_data=None, fields=None, form_cls=None, form_args=None,
        disabled_fields=None, hidden_fields=None, saving_data_process=None):

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
        self.disabled_fields = disabled_fields or []
        self.hidden_fields = hidden_fields or []
        self.saving_data_process = saving_data_process
        
    def get_fields(self, meta='AddForm'):
        f = []
        for field_name, prop in get_fields(self.model, self.fields, meta):
            d = {'name':field_name, 
                'prop':prop, 
                'disabled':field_name in self.disabled_fields,
                'hidden':field_name in self.hidden_fields}
            f.append(d)
            
        return f
    
    def make_form(self):
        import uliweb.orm as orm
        import uliweb.form as form
        
        if self.form:
            return self.form
        
        if isinstance(self.model, str):
            self.model = orm.get_model(self.model)
            
        if self.form_cls:
            DummyForm = self.form_cls
            if not hasattr(DummyForm, 'form_buttons'):
                DummyForm.form_buttons = form.Submit(value=_('Create'), _class=".submit")
           
        else:
            class DummyForm(form.Form):
                form_buttons = form.Submit(value=_('Create'), _class=".submit")
            
        for f in self.get_fields():
            field = make_form_field(f, self.model, builds_args_map=self.builds_args_map)
            
            if field:
                DummyForm.add_field(field.name, field, True)
        
        return DummyForm(data=self.data, **self.form_args)
    
    def make_field(self, field, model, field_cls=None):
        import uliweb.orm as orm
        import uliweb.form as form
        
        field_type = None
        prop = field['prop']
        
        kwargs = dict(label=prop.verbose_name or prop.property_name, default=prop.default, 
            name=prop.property_name, required=prop.required, help_string=prop.hint)
        if field['disabled']:
            kwargs['disabled'] = None
        if field['hidden']:
            field_type = form.HiddenField
            
        if field_cls:
            field_type = field_cls
        else:
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
                    field_type = form.StringField
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
            else:
                raise Exception, "Can't support the Property [%s=%s]" % (field['name'], prop.__class__.__name__)
            
        if field_type:
            build_args = self.builds_args_map.get(field_type, {})
            kwargs.update(build_args)
            f = field_type(**kwargs)
        
            return f

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
                
                if self.saving_data_process:
                    self.saving_data_process(d)
                    
                self.save(d)
                        
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
    
    def __init__(self, model, condition, ok_url, **kwargs):
        AddView.__init__(self, model, ok_url, **kwargs)
        self.condition = condition
        
    def run(self):
        from uliweb import request, function
        from uliweb import redirect
        import uliweb.orm as orm
        
        if isinstance(self.model, str):
            self.model = orm.get_model(self.model)
        
        flash = function('flash')
        
        obj = self.query()
        
        if not self.form:
            self.form = self.make_form(obj)
        
        if request.method == 'POST':
            flag = self.form.validate(request.values, request.files)
            if flag:
                data = self.form.data.copy()
                if self.saving_data_process:
                    self.saving_data_process(data, obj)
                r = self.save(obj, data)
                
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
            DummyForm = self.form_cls
            if not hasattr(DummyForm, 'form_buttons'):
                DummyForm.form_buttons = form.Submit(value=_('Save'), _class=".submit")
           
        else:
            class DummyForm(form.Form):
                form_buttons = form.Submit(value=_('Save'), _class=".submit")
            
        fields_list = self.get_fields('EditForm')
        fields_name = [x['name'] for x in fields_list]
        if 'id' not in fields_name:
            d = {'name':'id', 'prop':self.model.id, 'disabled':False, 'hidden':False}
            fields_list.insert(0, d)
            fields_name.insert(0, 'id')
        
        data = self.data or obj.to_dict(fields_name, convert=False)
        
        for f in fields_list:
            if f['name'] == 'id':
                f['hidden'] = True
            elif isinstance(f['prop'], orm.IntegerProperty) and 'autoincrement' in f['prop'].kwargs:
                f['hidden'] = True
                
            field = make_form_field(f, self.model, builds_args_map=self.builds_args_map)
            
            if field:
                DummyForm.add_field(field.name, field, True)
                
                if isinstance(f['prop'], orm.ManyToMany):
                    value = getattr(obj, f['name']).ids()
                    data[f['name']] = value
        
        return DummyForm(data=data, **self.form_args)
        
    
class DetailView(object):
    types_convert_map = {}
    fields_convert_map = {}
    
    def __init__(self, model, condition, fields=None, types_convert_map=None, fields_convert_map=None):
        self.model = model
        self.condition = condition
        self.fields = fields
        if self.types_convert_map:
            self.types_convert_map = types_convert_map
        if self.fields_convert_map:
            self.fields_convert_map = fields_convert_map or {}
            
    def run(self):
        from uliweb.orm import get_model
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
        
        obj = self.query()
        view_text = self.render(obj)
        
        return {'object':obj, 'view':''.join(view_text)}
    
    def query(self):
        return self.model.get(self.condition)
    
    def render(self, obj):
        view_text = ['<table class="table">']
        for field_name, prop in get_fields(self.model, self.fields, 'DetailView'):
            field = make_view_field(prop, obj, self.types_convert_map, self.fields_convert_map)
            
            if field:
                view_text.append('<tr><th align="right" valign="top" width=150>%s</th><td>%s</td></tr>' % (field["label"], field["display"]))
                
        view_text.append('</table>')
        return view_text

class DeleteView(object):
    def __init__(self, model, condition, ok_url):
        self.model = model
        self.condition = condition
        self.ok_url = ok_url
        
    def run(self):
        from uliweb.orm import get_model
        from uliweb import redirect
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
        
        self.model.filter(self.condition).delete()
        
        return redirect(self.ok_url)
        
class ListView(object):
    def __init__(self, model, condition=None, query=None, pageno=0, order_by=None, 
        fields=None, rows_per_page=10, types_convert_map=None, 
        fields_convert_map=None, id=None):
            
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
        
    def run(self, head=True, body=True):
        from uliweb.orm import get_model
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
            
        if not self.id:
            self.id = self.model.tablename
        
        #create table header
        table = self.table_info()
        query = self.query(self.model, self.condition, offset=self.pageno*self.rows_per_page, limit=self.rows_per_page, order_by=self.order_by)
        if head:
            return {'table':self.render(table, query, head=head, body=body), 'info':{'total':query.count(), 'rows_per_page':self.rows_per_page, 'pageno':self.pageno}}
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
            s = ['<table class="table" id=%s>' % self.id]
            s.append('<thead><tr>')
            for i, field_name in enumerate(table['fields_name']):
                kwargs = {}
                x = table['fields_list'][i]
                if 'width' in x:
                    kwargs['width'] = x['width']
                kwargs['align'] = x.get('align', 'left')
                s.append(str(Tag('th', field_name, **kwargs)))
            s.append('</tr></thead>')
            s.append('<tbody>')
        
        if body:
            #create table body
            for record in query:
                s.append('<tr>')
                for i, f in enumerate(table['fields_list']):
                    kwargs = {}
                    x = table['fields_list'][i]
                    v = make_view_field(getattr(self.model, x['name']), record, self.types_convert_map, self.fields_convert_map)
                    s.append(str(Tag('td', v['display'], **kwargs)))
                s.append('</tr>')
        
        if head:
            s.append('</tbody>')
            s.append('</table>')
        
        return '\n'.join(s)
    
    def query(self, model, condition=None, offset=None, limit=None, order_by=None, fields=None):
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
            fields_list = [(x, getattr(self.model, x)) for x in self.fields]
        elif hasattr(self.model, 'Table'):
            fields_list = [(x['name'], getattr(self.model, x['name'])) for x in self.model.Table.fields]
            is_table = True
        else:
            fields_list = [(x, y) for x, y in self.model._fields_list]
        
        for i, (x, y) in enumerate(fields_list):
            t['fields_name'].append(str(y.verbose_name or x))
            
            if is_table:
                t['fields_list'].append(self.model.Table.fields[i])
            else:
                t['fields_list'].append({'name':x})
        return t
    