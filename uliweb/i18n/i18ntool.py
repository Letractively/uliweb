import os

def getfiles(path):
    files_list = []
    if os.path.exists(os.path.abspath(os.path.normcase(path))):
        if os.path.isfile(path):
            files_list.append(path)
        else:
            for root, dirs, files in os.walk(path):
                for f in files:
                    filename = os.path.join(root, f)
                    if '.svn' in filename or (not filename.endswith('.py') and not filename.endswith('.html')):
                        continue
                    files_list.append(filename)
    return files_list

def _get_outputfile(apps_dir, appname='', locale='en'):
    if appname:
        output = os.path.join(apps_dir, appname, 'locale', locale, 'LC_MESSAGES', 'uliweb.pot')
    else:
        output = os.path.join(apps_dir, '..', 'locale', locale, 'LC_MESSAGES', 'uliweb.pot')
    return output

def _get_apps(apps_dir):
    try:
        import apps.settings as settings
        if hasattr(settings, 'INSTALLED_APPS'):
            return getattr(settings, 'INSTALLED_APPS')
    except ImportError:
        pass
    s = []
    for p in os.listdir(apps_dir):
        if os.path.isdir(os.path.join(apps_dir, p)) and p not in ['.svn', 'CVS'] and not p.startswith('.') and not p.startswith('_'):
            s.append(p)
    return s

def make_extract(apps_directory):
    apps_dir = apps_directory
    def action(appname=('a', ''), all=False, locale=('l', 'en'), whole=('w', False), merge=('m', False)):
        """
        extract i18n message catalog form app or all apps
        """
        from pygettext import extrace_files
        from po_merge import merge
        path = ''
        if appname:
            path = os.path.join(apps_dir, appname)
            files = getfiles(path)
            output = _get_outputfile(apps_dir, appname, locale)
            try:
                extrace_files(files, output)
                print 'Success! output file is %s' % output
                if merge:
                    merge(output[:-4]+'.po', output)
            except:
                raise
        elif all:
            apps = _get_apps(apps_dir)
            for appname in apps:
                path = os.path.join(apps_dir, appname)
                files = getfiles(path)
                output = _get_outputfile(apps_dir, appname, locale=locale)
                try:
                    extrace_files(files, output)
                    print 'Success! output file is %s' % output
                    if merge:
                        merge(output[:-4]+'.po', output)
                except:
                    raise
        elif whole:
            path = apps_dir
            files = getfiles(path)
            output = _get_outputfile(apps_dir, locale=locale)
            try:
                extrace_files(files, output)
                print 'Success! output file is %s' % output
                if merge:
                    merge(output[:-4]+'.po', output)
            except:
                raise
    
    return action

def update():
    pass