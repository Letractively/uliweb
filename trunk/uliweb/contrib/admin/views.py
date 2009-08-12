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
 
@expose("/admin/build")
@bind_menu('Build')
def admin_build():
    from uliweb.utils.common import pkg
    
    contrib_path = pkg.resource_filename('uliweb.contrib', '')
    apps_dirs = [(application.apps_dir, ''), (contrib_path, 'uliweb.contrib')]
    apps = get_apps(apps_dirs)
    return {'apps':apps}

from uliweb.utils.pyini import Ini
import os

def get_apps(apps_dirs):
    apps = {}
    
    for path, parent_module in apps_dirs:
        for p in os.listdir(path):
            app_path = os.path.join(path, p)
            if os.path.isdir(app_path) and p not in ['.svn', 'CVS'] and not p.startswith('.') and not p.startswith('_'):
                info = get_app_info(p, app_path)
                if parent_module:
                    info['module'] = parent_module + '.' + p
                else:
                    info['module'] = p
                d = apps.setdefault(info['catalog'], [])
                d.append(info)
                
    return apps
                
def get_app_info(name, app_path):
    info_ini = os.path.join(app_path, 'info.ini')
    
    catalog = 'No Catalog'
    desc = ''
    title = name.capitalize()
    
    if os.path.exists(info_ini):
        ini = Ini(info_ini)
        catalog = ini.info.get('catalog', catalog) or catalog
        desc = ini.info.get('description', desc) or desc
        title = ini.info.get('title', title) or title
        
    return {'catalog':catalog, 'desc':desc, 'title':title, 'name':name, 'path':app_path} 