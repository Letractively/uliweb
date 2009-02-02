from uliweb.form import *

Form.layout_class = CSSLayout

class NoteForm(Form):
    message = TextField(label='Message:', required=True)
    username = StringField(label='Username:', required=True)
    homepage = StringField(label='Homepage:')
    email = StringField(label='Email:')

