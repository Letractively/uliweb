from uliweb.core import Form

Form.Form.layout_class = Form.CSSLayout

class ContentForm(Form.Form):
    content = Form.TextAreaField(label='Content:', required=True)

