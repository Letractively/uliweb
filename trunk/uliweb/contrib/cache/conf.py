from uliweb.form import *

class ManageForm(Form):
    type = SelectField(label='Cache Type:', default='dbm', choices=[('dbm', 'File Based'), ('ext:database', 'Database Based')], key='ORM/type')
    url = StringField(label='Connection URL(For Database):', default='sqlite:///cache.db', key='ORM/url')
    table_name = StringField(label='Table name(For Database):', default='uliweb_cache', key='ORM/table_name')
    data_dir = StringField(label='Cache Path(File Based):', default='./cache', key='ORM/data_dir')
    timeout = IntField(label='Timeout:', required=True, default=3600, key='ORM/timeout')
