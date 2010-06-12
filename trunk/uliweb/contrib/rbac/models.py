from uliweb.orm import *
from uliweb.core import dispatch

User = get_model('user')

class Role(Model):
    name = Field(str, max_length=80, required=True)
    description = Field(str, max_length=255)
    reserve = Field(bool)
    users = ManyToMany(User, collection_name='roles')
    
class Permission(Model):
    name = Field(str, max_length=80, required=True)
    description = Field(str, max_length=255)
    roles = ManyToMany(Role, collection_name='permissions')
    
