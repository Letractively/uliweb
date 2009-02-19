#coding=utf-8
from uliweb.core.SimpleFrame import expose

@expose('/admin')
def index():
    return {}

@expose('/admin/appsinfo')
def appsinfo():
    return {'apps':application.apps}

@expose('/admin/urls')
def urls():
    u = []
    for r in application.url_map.iter_rules():
        u.append((r.rule, r.endpoint))
    u.sort()
    
    return {'urls':u}

@expose("/admin/global")
def globals_():
#    glob = globals()
#    glo = [ (key,glob[key]) for key in glob.keys() if callable(glob[key]) ]
#    un = [(key, str(glob[key]) or "none") for key in glob.keys() if not callable(glob[key]) ]
#    glo.extend(un)
#    glob = sorted(glob)
    
    return {"glo":env}
 
