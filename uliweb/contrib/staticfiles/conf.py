from uliweb.form import *

class ManageForm(Form):
    static_url = StringField(label='Static URL prefix:', required=True, key='staticfiles/STATIC_URL')