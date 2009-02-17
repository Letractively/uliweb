from uliweb.form import *
from uliweb.i18n import ugettext_lazy as _

class ContentForm(Form):
    content = TextField(label=_('Content:'), required=True)

