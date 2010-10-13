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
    
def make_form_field(prop, model, field_cls=None, builds_args_map=None, disabled=False, hidden=False):
    import uliweb.orm as orm
    import uliweb.form as form

    field_type = None
    builds_args_map = builds_args_map or {}
    field = None
    
    kwargs = dict(label=prop.verbose_name or prop.property_name, default=prop.default, 
        name=prop.property_name, required=prop.required, help_string=prop.hint)
    if disabled:
        kwargs['disabled'] = None
    if hidden:
        field_type = form.HiddenField
        
    if field_cls:
        field_type = field_cls
    else:
        if isinstance(prop, orm.BlobProperty):
            pass
        elif isinstance(prop, orm.TextProperty):
            field_type = form.TextField
        elif isinstance(prop, orm.CharProperty) or isinstance(prop, orm.StringProperty):
            if prop.choices is not None:
                field_type = form.SelectField
                kwargs['choices'] = prop.get_choices()
            else:
                field_type = form.StringField
        elif isinstance(prop, orm.BooleanProperty):
            field_type = form.BooleanField
        elif isinstance(prop, orm.DateProperty):
            if not prop.auto_now and not prop.auto_now_add:
                field_type = form.DateField
        elif isinstance(prop, orm.TimeProperty):
            if not prop.auto_now and not prop.auto_now_add:
                field_type = form.TimeField
        elif isinstance(prop, orm.DateTimeProperty):
            if not prop.auto_now and not prop.auto_now_add:
                field_type = form.DateTimeField
        elif isinstance(prop, orm.DecimalProperty):
            field_type = form.StringField
        elif isinstance(prop, orm.FloatProperty):
            field_type = form.FloatField
        elif isinstance(prop, orm.IntegerProperty):
            if 'autoincrement' not in prop.kwargs:
                if prop.choices is not None:
                    field_type = form.SelectField
                    kwargs['choices'] = prop.get_choices()
                    kwargs['datetype'] = int
                else:
                    field_type = form.IntField
        elif isinstance(prop, orm.ManyToMany):
            kwargs['model'] = prop.reference_class
            field_type = ManyToManySelectField
        elif isinstance(prop, orm.ReferenceProperty) or isinstance(prop, orm.OneToOneProperty):
            #field_type = form.IntField
            kwargs['model'] = prop.reference_class
            field_type = ReferenceSelectField
        
    if field_type:
        build_args = builds_args_map.get(field_type, {})
        kwargs.update(build_args)
        field = field_type(**kwargs)
    
    return field

def make_add_form(model, fields=None, form_cls=None, data=None, builds_args_map=None, disabled_fields=None, **kwargs):
    import uliweb.orm as orm
    import uliweb.form as form
    
    disabled_fields = disabled_fields or []
    
    if isinstance(model, str):
        model = orm.get_model(model)
        
    if form_cls:
        DummyForm = form_cls
        if not hasattr(DummyForm, 'form_buttons'):
            DummyForm.form_buttons = form.Submit(value=_('Create'), _class=".submit")
       
    else:
        class DummyForm(form.Form):
            form_buttons = form.Submit(value=_('Create'), _class=".submit")
        
    if fields:
        fields_list = [(x, getattr(model, x)) for x in fields]
    elif hasattr(model, 'AddForm'):
        fields_list = [(x, getattr(model, x)) for x in model.AddForm.fields]
    else:
        fields_list = [(x, y) for x, y in model._fields_list]
    
    for field_name, prop in fields_list:
        field = make_form_field(prop, model, builds_args_map=builds_args_map, disabled=field_name in disabled_fields)
        
        if field:
            DummyForm.add_field(field.name, field, True)
    
    data = data or {}
    return DummyForm(data=data, **kwargs)

def view_add_object(model, ok_url, form=None, success_msg=None, fail_msg=None, data=None, **kwargs):
    from uliweb import request, function
    from uliweb.orm import get_model
    from uliweb import redirect
    
    flash = function('flash')
    data = data or {}
    
    if not form:
        form = make_add_form(model, data=data, **kwargs)
    
    if request.method == 'POST':
        flag = form.validate(request.params)
        if flag:
            obj = get_model(model)(**form.data)
            obj.save()
            
            #process manytomany property
            for k, v in obj._manytomany.iteritems():
                if k in form.data:
                    value = form.data[k]
                    if value:
                        getattr(obj, k).add(*value)
                    
            msg = success_msg or _('The information has been saved successfully!')
            flash(msg)
            return redirect(ok_url)
        else:
            msg = fail_msg or _('There are somethings wrong.')
            flash(msg, 'error')
            return {'form':form}
    else:
        return {'form':form}
    
def make_edit_form(model, obj, fields=None, form_cls=None, data=None, builds_args_map=None, disabled_fields=None, **kwargs):
    import uliweb.orm as orm
    import uliweb.form as form
    
    disabled_fields = disabled_fields or []
    
    if isinstance(model, str):
        model = orm.get_model(model)
        
    if form_cls:
        DummyForm = form_cls
        if not hasattr(DummyForm, 'form_buttons'):
            DummyForm.form_buttons = form.Submit(value=_('Save'), _class=".submit")
       
    else:
        class DummyForm(form.Form):
            form_buttons = form.Submit(value=_('Save'), _class=".submit")
        
    if fields:
        fields_list = [(x, getattr(model, x)) for x in fields]
    elif hasattr(model, 'EditForm'):
        fields_list = [(x, getattr(model, x)) for x in model.EditForm.fields]
    else:
        fields_list = [(x, y) for x, y in model._fields_list]
    fields_name = [x for x, y in fields_list]
    if 'id' not in fields_name:
        fields_list.insert(0, ('id', model.id))
        fields_name.insert(0, 'id')
    
    data = data or obj.to_dict(fields_name, convert=False)

    for field_name, prop in fields_list:
        hidden = False
        if field_name == 'id':
            hidden = True
        elif isinstance(prop, orm.IntegerProperty) and 'autoincrement' in prop.kwargs:
            hidden = True
            
        field = make_form_field(prop, model, builds_args_map=builds_args_map, disabled=field_name in disabled_fields, hidden=hidden)
        
        if field:
            DummyForm.add_field(field.name, field, True)
            
            if isinstance(prop, orm.ManyToMany):
                value = getattr(obj, field_name).ids()
                data[field_name] = value
    
    return DummyForm(data=data, **kwargs)

def view_edit_object(model, condition, ok_url, form=None, success_msg=None, fail_msg=None, data=None, **kwargs):
    from uliweb import request, function
    from uliweb import redirect
    import uliweb.orm as orm
    
    if isinstance(model, str):
        model = orm.get_model(model)

    flash = function('flash')

    obj = model.get(condition)
    data = data or {}
    
    if not form:
        form = make_edit_form(model, obj, data=data, **kwargs)
    
    if request.method == 'POST':
        flag = form.validate(request.values)
        if flag:
            obj.update(**form.data)
            r = obj.save()
            
            #process manytomany property
            for k, v in obj._manytomany.iteritems():
                if k in form.data:
                    field = getattr(obj, k)
                    value = form.data[k]
                    if value:
                        r = r or getattr(obj, k).update(*value)
            
            if r:
                msg = success_msg or _('The information has been saved successfully!')
            else:
                msg = _("The object has not been changed.")
            flash(msg)
            return redirect(ok_url)
        else:
            msg = fail_msg or _('There are somethings wrong.')
            flash(msg, 'error')
            return {'form':form, 'object':obj}
    else:
        return {'form':form, 'object':obj}
    
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

def view_object(model, condition, fields=None, types_convert_map={}, fields_convert_map={}):
    from uliweb.orm import get_model
    
    if isinstance(model, str):
        model = get_model(model)

    obj = model.get(condition)
    
    if fields:
        fields_list = [(x, getattr(model, x)) for x in fields]
    elif hasattr(model, 'ViewDetail'):
        fields_list = [(x, getattr(model, x)) for x in model.ViewDetail.fields]
    else:
        fields_list = [(x, y) for x, y in model._fields_list]
    
    view_text = ['<table class="table corner">']
    for field_name, prop in fields_list:
        field = make_view_field(prop, obj, types_convert_map, fields_convert_map)
        
        if field:
            view_text.append('<tr><th align="right" valign="top" width=150>%s</th><td>%s</td></tr>' % (field["label"], field["display"]))
            
    view_text.append('</table>')
        
    return {'object':obj, 'view':''.join(view_text)}

def view_delete_object(model, condition):
    from uliweb.orm import get_model
    
    if isinstance(model, str):
        model = get_model(model)

    obj = model.get(condition)
    obj.delete()
    
    return {}

def view_list_objects_table(model, fields=None):
    from uliweb.orm import get_model
    
    t = {'fields_name':[], 'fields_list':[]}
    R = get_model(model)
    is_table = False

    if getattr(R, 'Table', None):
        fields_list = [(x['name'], getattr(R, x['name'])) for x in R.Table.fields]
        is_table = True
    elif fields:
        fields_list = [(x, getattr(R, x)) for x in fields]
    else:
        fields_list = R._fields_list
        
    for i, (x, y) in enumerate(fields_list):
        t['fields_name'].append(str(y.verbose_name or x))
        
        if is_table:
            t['fields_list'].append(R.Table.fields[i])
        else:
            t['fields_list'].append({'name':x})
    return t

def view_list_objects(model, condition=None, offset=None, limit=None, order_by=None, fields=None):
    from uliweb.orm import get_model
    
    if isinstance(model, str):
        model = get_model(model)
    
    query = model.filter(condition)
    if offset is not None:
        query.offset(int(offset))
    if limit is not None:
        query.limit(int(limit))
    if order_by is not None:
        query.order_by(order_by)
    return query.count(), query

def simple_view_list_objects(model, condition=None, pageno=0, order_by=None, fields=None, rows_per_page=10,
        types_convert_map=None, fields_convert_map=None):
    from uliweb.core.html import Tag
    
    from uliweb.orm import get_model
    
    if isinstance(model, str):
        model = get_model(model)
    
    #create table header
    table = view_list_objects_table(model, fields)
    s = ['<table class="table">']
    s.append('<thead><tr>')
    for i, f in enumerate(table['fields_name']):
        kwargs = {}
        x = table['fields_list'][i]
        if 'width' in x:
            kwargs['width'] = x['width']
        kwargs['align'] = x.get('align', 'left')
        s.append(str(Tag('th', f, **kwargs)))
    s.append('</tr></thead>')
    
    count, query = view_list_objects(model, condition, offset=pageno*rows_per_page, limit=rows_per_page, order_by=order_by)
    #create table body
    s.append('<tbody>')
    for row in query:
        s.append('<tr>')
        for i, f in enumerate(table['fields_list']):
            kwargs = {}
            x = table['fields_list'][i]
            v = make_view_field(getattr(model, x['name']), row, types_convert_map, fields_convert_map)
            s.append(str(Tag('td', v['display'], **kwargs)))
        s.append('</tr>')
    s.append('</tbody>')
    s.append('</table>')
    return {'table':'\n'.join(s), 'info':{'total':count, 'rows_per_page':rows_per_page, 'pageno':pageno}}