#coding=utf-8
from uliweb.i18n import gettext_lazy as _
from uliweb.form import SelectField, BaseField

class ReferenceSelectField(SelectField):
    def __init__(self, model, display_field=None, value_field='id', condition=None, query=None, label='', default=0, required=False, validators=None, name='', html_attrs=None, help_string='', build=None, empty='', **kwargs):
        SelectField.__init__(self, label=label, default=default, choices=[], required=required, validators=validators, name=name, html_attrs=html_attrs, help_string=help_string, build=build, empty=empty, **kwargs)
        self.model = model
        self.display_field = display_field
        self.value_field = value_field
        self.condition = condition
        self.query = query
    
    def get_choices(self):
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
        r = list(query.values(self.value_field, self.display_field))
        return r
    
    def to_python(self, data):
        return int(data)

class ManyToManySelectField(ReferenceSelectField):
    def __init__(self, model, display_field=None, value_field='id', 
            condition=None, query=None, label='', default=None, 
            required=False, validators=None, name='', html_attrs=None, 
            help_string='', build=None, **kwargs):
        ReferenceSelectField.__init__(self, model=model, display_field=display_field, 
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
    
    kwargs = dict(label=prop.verbose_name or prop.property_name, default=prop.default_value(), 
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
            if isinstance(prop, orm.Property) and prop.choices is not None:
                display = get_choice(prop.choices, value)
            if prop.__class__ is orm.TextProperty:
                from uliweb.utils.textconvert import text2html
                display = text2html(value)
        
    if isinstance(display, unicode):
        display = display.encode('utf-8')
    if display is None:
        display = ''
        
    return {'label':label, 'value':value, 'display':display}

class AddView(object):
    success_msg = _('The information has been saved successfully!')
    fail_msg = _('There are somethings wrong.')
    builds_args_map = {}
    meta = 'AddForm'
    
    def __init__(self, model, ok_url, form=None, success_msg=None, fail_msg=None, 
        data=None, default_data=None, fields=None, form_cls=None, form_args=None,
        disabled_fields=None, hidden_fields=None, pre_save=None, post_save=None,
        post_created_form=None, layout=None):

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
        self.pre_save = pre_save
        self.post_save = post_save
        self.post_created_form = post_created_form
        
        #add layout support
        self.layout = layout
        
    def get_fields(self):
        f = []
        for field_name, prop in get_fields(self.model, self.fields, self.meta):
            d = {'name':field_name, 
                'prop':prop, 
                'disabled':field_name in self.disabled_fields,
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
                r = self.save(obj, data)
                if self.post_save:
                    r = r or self.post_save(obj, data)
                
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
            d = {'name':'id', 'prop':self.model.id, 'disabled':False, 'hidden':False}
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
        
    
class DetailView(object):
    types_convert_map = {}
    fields_convert_map = {}
    meta = 'DetailView'
    
    def __init__(self, model, condition=None, obj=None, fields=None, types_convert_map=None, fields_convert_map=None):
        self.model = model
        self.condition = condition
        self.obj = obj
        self.fields = fields
        if self.types_convert_map:
            self.types_convert_map = types_convert_map
        if self.fields_convert_map:
            self.fields_convert_map = fields_convert_map or {}
            
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
        view_text = ['<table class="table">']
        for field_name, prop in get_fields(self.model, self.fields, self.meta):
            field = make_view_field(prop, obj, self.types_convert_map, self.fields_convert_map)
            
            if field:
                view_text.append('<tr><th align="right" valign="top" width=150>%s</th><td>%s</td></tr>' % (field["label"], field["display"]))
                
        view_text.append('</table>')
        return view_text

class DeleteView(object):
    def __init__(self, model, ok_url, condition=None, obj=None):
        self.model = model
        self.condition = condition
        self.obj = obj
        self.ok_url = ok_url
        
    def run(self):
        from uliweb.orm import get_model
        from uliweb import redirect
        
        if isinstance(self.model, str):
            self.model = get_model(self.model)
        
        if self.obj:
            self.obj.delete()
        else:
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
            s.append('<thead>')
#            s.append('<tr>')
#            for i, field_name in enumerate(table['fields_name']):
#                kwargs = {}
#                x = table['fields_list'][i]
#                if 'width' in x:
#                    kwargs['width'] = x['width']
#                kwargs['align'] = x.get('align', 'left')
#                s.append(str(Tag('th', field_name, **kwargs)))
#            s.append('</tr>')
            s.extend(self.create_table_head(table))
            s.append('</thead>')
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
                s.append(str(Tag('th', field['name'], **kwargs)))
                
                i = j
            clear_fields(fields)
            s.append('</tr>\n')
            n = len(fields)
            y += 1
            
        return s
        
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
    