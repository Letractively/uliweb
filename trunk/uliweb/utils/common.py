import os

class MyPkg(object):
    @staticmethod
    def resource_filename(module, path):
        mod = __import__(module)
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
        print 'Info : Copy [%s] to [%s]' % (inf, dist)
  
def extract_dirs(mod, path, dst, verbose=False):
    if not os.path.exists(dst):
        os.makedirs(dst)
        if verbose:
            print 'Info : Make directory', dst
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
                print "Warn : %s does not exist, SKIP" % f
            continue
        dd = os.path.join(dst, os.path.basename(f))
        if exact:
            shutil.rmtree(dd, True)
        if not os.path.exists(dd):
            os.makedirs(dd)
            if verbose:
                print 'Info : Make directory', dst
            
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
                    print "Info : Copy [%s] to [%s]" % (fpath, dd)

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
                print "Warn : %s does not exist, SKIP" % f
            continue
        if verbose:
            print "Info : Processing %s" % f
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
