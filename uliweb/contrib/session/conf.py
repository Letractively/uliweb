from uliweb.form import *

class ManageForm(Form):
    type = SelectField(label='Session Type:', default='dbm', choices=[('dbm', 'File Based'), ('ext:database', 'Database Based')], key='SESSION/type')
    url = StringField(label='Connection URL(For Database):', default='sqlite:///session.db', key='SESSION/url')
    table_name = StringField(label='Table name(For Database):', default='uliweb_session', key='SESSION/table_name')
    data_dir = StringField(label='Session Path(File Based):', default='./session', key='SESSION/data_dir')
    timeout = IntField(label='Timeout:', required=True, default=300, key='SESSION/timeout')
    cookie_expires = IntField(label='Cookie Expire Time:', required=True, default=300, key='SESSION/cookie_expires')
