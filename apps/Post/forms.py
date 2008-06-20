from uliweb.core import Form
from uliweb.i18n import ugettext_lazy as _

Form.Form.layout_class = Form.CSSLayout

class ContentForm(Form.Form):
    content = Form.TextAreaField(label=_('Content:'), required=True)

