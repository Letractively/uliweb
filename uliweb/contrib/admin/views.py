#coding=utf-8
from uliweb.core.SimpleFrame import expose
from uliweb.contrib.admin.menu import bind_menu

@expose('/admin')
@bind_menu('Settings', weight=10)
def admin_index():
    return {}

@expose('/admin/appsinfo')
@bind_menu('Apps Info', weight=20)
def admin_appsinfo():
    return {'apps':application.apps}

@expose('/admin/urls')
@bind_menu('Urls', weight=30)
def admin_urls():
    u = []
    for r in application.url_map.iter_rules():
        if r.methods:
            methods = ' '.join(list(r.methods))
        else:
            methods = ''
        u.append((r.rule, methods, r.endpoint))
    u.sort()
    
    return {'urls':u}

@expose("/admin/global")
@bind_menu('View Global', weight=40)
def admin_globals():
#    glob = globals()
#    glo = [ (key,glob[key]) for key in glob.keys() if callable(glob[key]) ]
#    un = [(key, str(glob[key]) or "none") for key in glob.keys() if not callable(glob[key]) ]
#    glo.extend(un)
#    glob = sorted(glob)
    
    return {"glo":env}
 
