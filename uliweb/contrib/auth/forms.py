from uliweb.form import *
from uliweb.i18n import ugettext_lazy as _

#Form.layout_class = Form.CSSLayout

class RegisterForm(Form):
    username = StringField(label=_('Username:'), required=True)
    password = PasswordField(label=_('Password:'), required=True)
    password1 = PasswordField(label=_('Password again:'), required=True)
    next = HiddenField()
    
    def validate(self, all_data):
        if all_data.password != all_data.password1:
            raise ValidationError, 'Passwords are not matched'
    

class LoginForm(Form):
    username = StringField(label=_('Username:'), required=True)
    password = PasswordField(label=_('Password:'), required=True)
    next = HiddenField()
    
