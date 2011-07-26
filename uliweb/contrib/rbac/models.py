from uliweb.orm import *

class Permission(Model):
    name = Field(str, max_length=80, required=True)
    description = Field(str, max_length=255)
    props = Field(PICKLE)
    
class Role(Model):
    name = Field(str, max_length=80, required=True)
    description = Field(str, max_length=255)
    reserve = Field(bool)
    users = ManyToMany('user', collection_name='user_roles')
    permissions = ManyToMany('permission', through='role_perm_rel', collection_name='perm_roles')
    
class Role_Perm_Rel(Model):
    role = Reference('role')
    permission = Reference('permission')
    props = Field(PICKLE)
    
    
