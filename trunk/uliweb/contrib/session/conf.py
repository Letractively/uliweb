from uliweb.form import *

class ManageForm(Form):
    type = SelectField(label='Session Type:', default='dbm', choices=[('dbm', 'File Based'), ('ext:database', 'Database Based')], key='ORM/type')
    url = StringField(label='Connection URL(For Database):', default='sqlite:///session.db', key='ORM/url')
    table_name = StringField(label='Table name(For Database):', default='uliweb_session', key='ORM/table_name')
    data_dir = StringField(label='Session Path(File Based):', default='./session', key='ORM/data_dir')
    timeout = IntField(label='Timeout:', required=True, default=300, key='ORM/timeout')
    cookie_expires = IntField(label='Cookie Expire Time:', required=True, default=300, key='ORM/cookie_expires')
