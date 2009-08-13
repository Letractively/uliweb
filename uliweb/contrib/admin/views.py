#coding=utf-8
from uliweb.core.SimpleFrame import expose
from uliweb.contrib.admin.menu import bind_menu
from uliweb.utils.common import log

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
 
from uliweb.utils.pyini import Ini
import os

@expose("/admin/build")
@bind_menu('Build')
def admin_build():
    from uliweb.utils.common import pkg
    
    contrib_path = pkg.resource_filename('uliweb.contrib', '')
    apps_dirs = [(application.apps_dir, ''), (contrib_path, 'uliweb.contrib')]
    catalogs, apps = get_apps(application, apps_dirs)
    
    from forms import GenericForm
    
    f = GenericForm(method="post")
    
    if request.method == 'GET':
        ini = Ini(os.path.join(application.apps_dir, 'settings.ini'))
        ini_to_form(f, ini)
        
    else:
        r = f.validate(request.params)
        if r:
            ini = Ini(os.path.join(application.apps_dir, 'settings.ini'))
            flag = form_to_ini(f, ini)
            if flag:
                ini.save()
        
    return {'catalogs':catalogs, 'generic_form':f}

@expose('/admin/app_edit')
def admin_edit_app():
    ini = Ini(os.path.join(application.apps_dir, 'settings.ini'))
    flag = False
    module = request.GET['module']
    
    if request.GET['action'] == 'add':
        if not ini.GLOBAL.get('INSTALLED_APPS'):
            ini.GLOBAL.INSTALLED_APPS = application.apps
        if module not in ini.GLOBAL.INSTALLED_APPS:
            ini.GLOBAL.INSTALLED_APPS.append(module)
            flag = True
    else:
        if not ini.GLOBAL.get('INSTALLED_APPS'):
            ini.GLOBAL.INSTALLED_APPS = application.apps
        if module in ini.GLOBAL.INSTALLED_APPS:
            ini.GLOBAL.INSTALLED_APPS.remove(module)
            flag = True
    
    print ini.GLOBAL.INSTALLED_APPS
    if flag:
        ini.save()
    return 'ok'
    
def ini_to_form(form, ini):
    for k, obj in form.fields.items():
        if 'key' in obj.kwargs:
            key = obj.kwargs['key']
            v = get_var(key, ini)
            if v:
                getattr(form, k).data = v

def form_to_ini(form, ini):
    flag = False
    for k, obj in form.fields.items():
        if 'key' in obj.kwargs:
            key = obj.kwargs['key']
            v = get_var(key, ini)
            value = getattr(form, k).data
            if v != value:
                flag = True
                set_var(key, value, ini)
                
    return flag
    
def get_var(key, ini_obj):
    s = key.split('/')
    obj = ini_obj
    for i in s:
        k = obj.get(i)
        if k:
            obj = k
        else:
            return None
    return obj

def set_var(key, value, ini_obj):
    s = key.split('/')
    obj = ini_obj
    for i in s[:-1]:
        k = obj.add(i)
        if k:
            obj = k
        else:
            return
    obj[s[-1]] = value
   
def get_apps(application, apps_dirs):
    catalogs = {}
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
                if info['module'] in application.apps:
                    info['selected'] = True
                else:
                    info['selected'] = False
                    
                    
                apps[p] = info
                d = catalogs.setdefault(info['catalog'], [])
                d.append(info)
    return catalogs, apps

@expose('/admin/app_conf')
def admin_app_conf():
    
    from uliweb.utils.common import pkg
    
    contrib_path = pkg.resource_filename('uliweb.contrib', '')
    apps_dirs = [(application.apps_dir, ''), (contrib_path, 'uliweb.contrib')]
    catalogs, apps = get_apps(application, apps_dirs)
    
    app = apps.get(request.GET['id'])
    
    conf_py = os.path.join(app['path'], 'conf.py')
    form = '<h3>Nothing need to configure!</h3>'
    if os.path.exists(conf_py):
        try:
            mod = __import__(app['module'] + '.conf', {}, {}, [''])
            f = getattr(mod, 'ManageForm')
            if f:
                form = f(action=url_for(admin_app_conf)+'?id=%s' % app['name'], method='post')
                if request.method == 'POST':
                    ini = Ini(os.path.join(application.apps_dir, 'settings.ini'))
                    r = form.validate(request.POST)
                    flag = form_to_ini(form, ini)
                    if flag:
                        ini.save()
                elif request.method == 'GET':
                    ini_to_form(form, application.settings)
        
        except ImportError:
            log.exception(e)
    
    return form
                
def get_app_info(name, app_path):
    info_ini = os.path.join(app_path, 'info.ini')
    
    catalog = 'No Catalog'
    desc = ''
    title = name.capitalize()
    icon = 'app_icon.png'
    author = ''
    version = ''
    homepage = ''
    
    if os.path.exists(info_ini):
        ini = Ini(info_ini)
        catalog = ini.info.get('catalog', catalog) or catalog
        desc = ini.info.get('description', desc) or desc
        title = ini.info.get('title', title) or title
        icon = ini.info.get('icon', icon) or icon
        icon_file = os.path.join(app_path, 'static', icon)
        author = ini.info.get('author', author) or author
        version = ini.info.get('version', version) or version
        homepage = ini.info.get('homepage', homepage) or homepage
        
    return {'catalog':catalog, 'desc':desc, 'title':title, 'name':name, 
            'path':app_path, 'icon':icon, 'author':author, 
            'version':version, 'homepage':homepage} 