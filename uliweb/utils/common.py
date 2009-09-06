import os, sys

def import_func(path):
    module, func = path.rsplit('.', 1)
    mod = __import__(module, {}, {}, [''])
    return getattr(mod, func)

def myimport(module):
    m = module.split('.')
    mod = __import__(module)
    for i in m[1:]:
        mod = getattr(mod, i)
    return mod

class MyPkg(object):
    @staticmethod
    def resource_filename(module, path):
        mod = myimport(module)
        p = os.path.dirname(mod.__file__)
        if path:
            return os.path.join(p, path)
        else:
            return p
    
    @staticmethod
    def resource_listdir(module, path):
        d = MyPkg.resource_filename(module, path)
        return os.listdir(d)
    
    @staticmethod
    def resource_isdir(module, path):
        d = MyPkg.resource_filename(module, path)
        return os.path.isdir(d)

try:
    import pkg_resources as pkg
except:
    pkg = MyPkg

def extract_file(module, path, dist, verbose=False):
    outf = os.path.join(dist, os.path.basename(path))
#    d = pkg.get_distribution(module)
#    if d.has_metadata('zip-safe'):
#        f = open(outf, 'wb')
#        f.write(pkg.resource_string(module, path))
#        f.close()
#        if verbose:
#            print 'Info : Extract %s/%s to %s' % (module, path, outf)
#    else:
    import shutil

    inf = pkg.resource_filename(module, path)
    shutil.copy2(inf, dist)
    if verbose:
        log.info('Info : Copy [%s] to [%s]' % (inf, dist))
  
def extract_dirs(mod, path, dst, verbose=False):
    if not os.path.exists(dst):
        os.makedirs(dst)
        if verbose:
            log.info('Info : Make directory', dst)
    for r in pkg.resource_listdir(mod, path):
        if r in ['.svn', '_svn']:
            continue
        fpath = os.path.join(path, r)
        if pkg.resource_isdir(mod, fpath):
            extract_dirs(mod, fpath, os.path.join(dst, r), verbose)
        else:
            ext = os.path.splitext(fpath)[1]
            if ext in ['.pyc', '.pyo', '.bak', '.tmp']:
                continue
            extract_file(mod, fpath, dst, verbose)

def copy_dir(d, dst, verbose, exact=False):
    import shutil

    for f in d:
        if not os.path.exists(f):
            if verbose:
                log.warn("Warn : %s does not exist, SKIP" % f)
            continue
        dd = os.path.join(dst, os.path.basename(f))
        if exact:
            shutil.rmtree(dd, True)
        if not os.path.exists(dd):
            os.makedirs(dd)
            if verbose:
                log.info('Info : Make directory', dst)
            
        for r in os.listdir(f):
            if r in ['.svn', '_svn']:
                continue
            fpath = os.path.join(f, r)
            if os.path.isdir(fpath):
                copy_dir([fpath], dd, verbose)
            else:
                ext = os.path.splitext(fpath)[1]
                if ext in ['.pyc', '.pyo', '.bak', '.tmp']:
                    continue
                shutil.copy2(fpath, dd)
                if verbose:
                    log.info("Info : Copy [%s] to [%s]" % (fpath, dd))

def copy_dir_with_check(d, dst, verbose=False, check=True):
    import shutil
    
    def _md5(filename):
        import md5
        a = md5.new()
        a.update(file(filename, 'rb').read())
        return a.digest()

    for f in d:
        if not os.path.exists(f):
            if verbose:
                log.warn("Warn : %s does not exist, SKIP" % f)
            continue
        if verbose:
            log.info("Info : Processing %s" % f)
        for r in os.listdir(f):
            if r in ['.svn', '_svn']:
                continue
            fpath = os.path.join(f, r)
            if os.path.isdir(fpath):
                dd = os.path.join(dst, r)
                if not os.path.exists(dd):
                    os.makedirs(dd)
                    if verbose:
                        print 'Info : Make directory', dst
                copy_dir([fpath], dd, verbose, check)
            else:
                ext = os.path.splitext(fpath)[1]
                if ext in ['.pyc', '.pyo', '.bak', '.tmp']:
                    continue
                if check:
                    df = os.path.join(dst, r)
                    if os.path.exists(df):
                        a = _md5(fpath)
                        b = _md5(df)
                        if a != b:
                            print ("Error: Target file %s is already existed, and "
                                "it not same as source one %s, so copy failed" % (fpath, dst))
                    else:
                        shutil.copy2(fpath, dst)
                else:
                    shutil.copy2(fpath, dst)

log = None
FORMAT = "%(levelname)-8s %(asctime)-15s %(filename)s,%(lineno)d] %(message)s"

def get_logger(format=FORMAT, datafmt=None):
    global log
    import logging
    handler = logging.StreamHandler()
    fmt = logging.Formatter(format, datafmt)
    handler.setFormatter(fmt)
    
    log = logging.getLogger('uliweb')
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    return log

get_logger()

def check_apps_dir(apps_dir):
    if not os.path.exists(apps_dir):
        log.error("Error: Can't find the apps_dir [%s], please check it out", apps_dir)
        sys.exit(1)

def is_pyfile_exist(dir, pymodule):
    path = os.path.join(dir, '%s.py' % pymodule)
    if not os.path.exists(path):
        path = os.path.join(dir, '%s.pyc' % pymodule)
        if not os.path.exists(path):
            path = os.path.join(dir, '%s.pyo' % pymodule)
            if not os.path.exists(path):
                return False
    return True
    
def wrap_func(des, src):
    des.__name__ = src.__name__
    des.func_globals.update(src.func_globals)
    des.__doc__ = src.__doc__
    des.__module__ = src.__module__
    des.__dict__.update(src.__dict__)
    return des

def sort(alist, default=500):
    """
    Sort a list, each element could be a tuple (order, value) or just a value
    for example:
        ['abc', (50, 'cde')]
    you can put a default argument to it, if there is no order of a element, then
    the order of this element will be the default value.
    All elements will be sorted according the order value, and the same order
    value elements will be sorted in the definition of the element
    
    >>> sort(['a', 'c', 'b'])
    ['a', 'c', 'b']
    >>> sort([(100, 'a'), 'c', 'd', (50, 'b')])
    ['b', 'a', 'c', 'd']
    >>> sort([(100, 'a'), (100, 'c'), 'd', (100, 'b')])
    ['a', 'c', 'b', 'd']
    
    """
    d = {}
    for v in alist:
        if isinstance(v, (tuple, list)):
            n, s = v[0], v[1]
        else:
            n, s = default, v
        p = d.setdefault(n, [])
        p.append(s)
    t = []
    for k in sorted(d.keys()):
        t.extend(d[k])
    return t

if __name__ == '__main__':
    log.info('Info: info')
    try:
        1/0
    except:
        log.exception('1/0')
