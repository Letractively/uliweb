#coding=utf-8
from uliweb.i18n import gettext_lazy as _

def make_form_field(prop, field_cls=None, builds_type_map=None, disabled=False, hidden=False):
    import uliweb.orm as orm
    import uliweb.form as form

    field_type = None
    builds_type_map = builds_type_map or {}
    field = None
    
    kwargs = dict(label=prop.verbose_name or prop.name, default=prop.default, 
        name=prop.name, required=prop.required, help_string=prop.hint)
    if disabled:
        kwargs['disabled'] = None
    if hidden:
        field_type = form.HiddenField
        
    if field_cls:
        field_type = field_cls
    else:
        if isinstance(prop, orm.ManyToMany):
            pass
        elif isinstance(prop, orm.BlobProperty):
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
        elif isinstance(prop, orm.ReferenceProperty) or isinstance(prop, orm.OneToOneProperty):
            field_type = form.IntField
        
    if field_type:
        build_type = builds_type_map.get(field_type, None)
        field = field_type(build=build_type, **kwargs)
    
    return field
    
def make_add_form(model, fields=None, form_cls=None, data=None, builds_type_map=None, disabled_fields=None, **kwargs):
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
        field = make_form_field(prop, builds_type_map=builds_type_map, disabled=field_name in disabled_fields)
        
        if field:
            DummyForm.add_field(field.name, field, True)
    
    data = data or {}
    return DummyForm(data=data, **kwargs)

def view_add_object(model, ok_url, form=None, success_msg=None, fail_msg=None, data=None, **kwargs):
    from uliweb import request
    from uliweb.orm import get_model
    from uliweb.contrib.flashmessage import flash
    from uliweb import redirect
    
    data = data or {}
    
    if not form:
        form = make_add_form(model, data=data, **kwargs)
    
    if request.method == 'POST':
        flag = form.validate(request.params)
        if flag:
            obj = get_model(model)(**form.data)
            obj.save()
            msg = success_msg or _('The information has been saved successfully!')
            flash(msg)
            return redirect(ok_url)
        else:
            msg = fail_msg or _('There are somethings wrong.')
            flash(msg, 'error')
            return {'form':form}
    else:
        return {'form':form}
    
def make_edit_form(model, obj, fields=None, form_cls=None, data=None, builds_type_map=None, disabled_fields=None, **kwargs):
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
    
    for field_name, prop in fields_list:
        hidden = False
        if field_name == 'id':
            hidden = True
        elif isinstance(prop, orm.IntegerProperty) and 'autoincrement' in prop.kwargs:
            hidden = True
            
        field = make_form_field(prop, builds_type_map=builds_type_map, disabled=field_name in disabled_fields, hidden=hidden)
        
        if field:
            DummyForm.add_field(field.name, field, True)
    
    data = data or obj.to_dict(fields_name, convert=False)
    return DummyForm(data=data, **kwargs)

def view_edit_object(model, condition, ok_url, form=None, success_msg=None, fail_msg=None, data=None, **kwargs):
    from uliweb import request
    from uliweb.orm import get_model
    from uliweb.contrib.flashmessage import flash
    from uliweb import redirect
    import uliweb.orm as orm
    from uliweb.core import dispatch
    
    if isinstance(model, str):
        model = orm.get_model(model)

    obj = model.get(condition)
    data = data or {}
    
    if not form:
        form = make_edit_form(model, obj, data=data, **kwargs)
    
    if request.method == 'POST':
        flag = form.validate(request.params)
        if flag:
            obj.update(**form.data)
            if obj.save():
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
    
def make_view_field(prop, obj, types_convert_map={}, fields_convert_map={}):
    import uliweb.orm as orm
    from uliweb.utils.common import get_choice

    default_convert_map = {orm.TextProperty:lambda v:'<br/>'.join(v.splitlines())}
    
    value = prop.get_value_for_datastore(obj)
    display = value
        
    if prop.name in fields_convert_map:
        convert = fields_convert_map.get(prop.name, None)
    else:
        convert = types_convert_map.get(prop.__class__, None)
        if not convert:
            convert = default_convert_map.get(prop.__class__, None)
        
    if convert:
        display = convert(value)
    else:
        if value is not None:
            if isinstance(prop, orm.ManyToMany):
                s = []
                for x in getattr(obj, prop.name).all():
                    if hasattr(x, 'get_url'):
                        s.append(x.get_url())
                    else:
                        s.append(unicode(x))
                display = ' '.join(s)
            elif isinstance(prop, orm.ReferenceProperty) or isinstance(prop, orm.OneToOne):
                v = getattr(obj, prop.name)
                if hasattr(v, 'get_url'):
                    display = v.get_url()
                else:
                    display = unicode(x)
            if prop.choices is not None:
                display = get_choice(prop.choices, value)
        
    if isinstance(display, unicode):
        display = display.encode('utf-8')
    if display is None:
        display = ''
    
    return {'label':prop.verbose_name or prop.name, 'value':value, 'display':display}

def view_object(model, condition, fields=None, types_convert_map={}, fields_convert_map={}):
    from uliweb.orm import get_model
    
    if isinstance(model, str):
        model = get_model(model)

    print model._fields_list
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