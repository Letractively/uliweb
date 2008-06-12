from utils import Form

Form.Form.layout_class = Form.CSSLayout

class NoteForm(Form.Form):
    message = Form.TextAreaField(label='Message:', required=True)
    username = Form.TextField(label='Username:', required=True)
    homepage = Form.TextField(label='Homepage:')
    email = Form.TextField(label='Email:')

