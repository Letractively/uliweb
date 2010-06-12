import uliweb
from uliweb.orm import get_model

Role = get_model('role')

r = uliweb.settings.get('ROLES', {})
for name, description in r.items():
    Role(name=name, description=description, reserve=True).save()

from rbac import permissions

p = uliweb.settings.get('PERMISSIONS', {})
for name, v in p.items():
    if isinstance(v, tuple):
        description, roles = v
    else:
        description, roles = v, []
    permissions.add(name=name, description=description, roles=roles).save()
    

