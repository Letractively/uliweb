from uliweb.core import Form
from uliweb.i18n import ugettext_lazy as _

#Form.Form.layout_class = Form.CSSLayout

class RegisterForm(Form.Form):
    username = Form.TextField(label=_('Username:'), required=True)
    password = Form.PasswordField(label=_('Password:'), required=True)
    password1 = Form.PasswordField(label=_('Password again:'), required=True)

class LoginForm(Form.Form):
    username = Form.TextField(label=_('Username:'), required=True)
    password = Form.PasswordField(label=_('Password:'), required=True)

