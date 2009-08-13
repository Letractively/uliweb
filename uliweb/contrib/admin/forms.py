from uliweb.form import *

class GenericForm(Form):
    debug = BooleanField(label='Debug:', key='GLOBAL/DEBUG')
    time_zone = StringField(label='Time Zone:', key='GLOBAL/TIME_ZONE', default='UTC')
    
