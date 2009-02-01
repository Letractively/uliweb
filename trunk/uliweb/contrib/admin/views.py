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