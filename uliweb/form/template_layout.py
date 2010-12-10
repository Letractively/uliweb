from __future__ import with_statement

from layout import Layout
from uliweb.core import uaml
from uliweb.core.html import Tag, begin_tag, end_tag, u_str

class FormWriter(uaml.Writer):
    field_classes = {
        ('Text', 'Password', 'TextArea'):'type-text',
        ('Button', 'Submit', 'Reset'):'type-button',
        ('Select', 'RadioSelect'):'type-select',
        ('Radio', 'Checkbox'):'type-check',
        }

    def __init__(self, form):
        self.form = form
        
    def get_class(self, f):
        name = f.build.__name__
        _class = 'type-text'
        for k, v in self.field_classes.items():
            if name in k:
                _class = v
                break
        return _class

    def get_widget_name(self, f):
        return f.build.__name__

    def is_hidden(self, f):
        return self.get_widget_name(f) == 'Hidden'

    def do_title(self, indent, value, **kwargs):
        return indent * ' ' + '<h2>%s</h2>' % value
    
    def begin_form(self, indent, value, **kwargs):
        if kwargs.get('class', None):
            self.form.html_attrs['_class'] = kwargs['class']
        return indent * ' ' + self.form.form_begin
    
    def close_form(self, indent):
        return indent * ' ' + self.form.form_end
    
    def begin_buttons(self, indent, value, **kwargs):
        kwargs['_class'] = 'type-button'
        return indent * ' ' + begin_tag('div', **kwargs)
    
    def close_buttons(self, indent):
        return indent * ' ' + end_tag('div')
    
    def do_button(self, indent, value, **kwargs):
        return indent * ' ' + str(Tag('input', None, **{'value':value, 'type':'submit'}))
    
    def do_field(self, indent, value, **kwargs):
        field_name = kwargs['name']
        field = getattr(self.form, field_name)
        error = field.error
        obj = self.form.fields[field_name]
        help_string = kwargs.get('help_string', None) or field.help_string
        if 'label' in kwargs:
            label = kwargs['label']
        else:
            label = obj.label
        if label:
            obj.label = label
            label_text = obj.get_label(_class='field')
        else:
            label_text = ''
        
        _class = self.get_class(obj)
        if error:
            _class = _class + ' error'
        
        if self.is_hidden(obj):
            return str(field)
        
        div = Tag('div', _class=_class)
        with div:
            if error:
                div.strong(error, _class="message")
            if self.get_widget_name(obj) == 'Checkbox':
                div << field
                div << label_text
                div << help_string
            else:
                div << label_text
                div << help_string
                div << field
        return indent*' ' + str(div)
    
    def do_td_field(self, indent, value, **kwargs):
        field_name = kwargs.get('name', None)
        field = getattr(self.form, field_name)
        obj = self.form.fields[field_name]
        if 'label' in kwargs:
            label = kwargs['label']
        else:
            label = obj.label
        if label:
            obj.label = label
            label_text = obj.get_label(_class='field')
        else:
            label_text = ''
            
        display = field.data or '&nbsp;'
        return indent * ' ' + '<th align=right width=200>%s</th><td width=200>%s</td>' % (label_text, u_str(display))
        
    def do_static(self, indent, value, **kwargs):
        field_name = kwargs.get('name', None)
        field = getattr(self.form, field_name)
        label = kwargs.get('label', None)
        obj = self.form.fields[field_name]
        if label:
            obj.label = label
        label = obj.get_label(_class='field')
            
        display = field.data or '&nbsp;'
        return indent * ' ' + '<div class="view"><label>%s:</label><span class="value">%s</span></div>' % (label, u_str(display))
    
class TemplateLayout(Layout):
    def __init__(self, form, layout=None, writer=None):
        self.form = form
        self.layout = layout
        self.writer = FormWriter(form)

    def html(self):
        from uliweb import application
        f = file(application.get_file(self.layout, dir='templates'), 'rb')
        text = f.read()
        f.close()
        return str(uaml.Parser(text, self.writer))
