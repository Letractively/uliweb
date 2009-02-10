import os
from uliweb.utils.common import log
from uliweb.core.plugin import plugin
from uliweb.core.SimpleFrame import expose
from werkzeug.exceptions import Forbidden

__all__ = ['save_file', 'get_filename', 'get_url']

@plugin('prepare_default_env')
def prepare_default_env(sender, env):
    url = sender.settings.UPLOAD.URL_SUFFIX.rstrip('/')
    expose('%s/<path:filename>' % url, static=True)(file_serving)
 
def file_serving(filename):
    from uliweb.core.FileApp import return_file
    from uliweb.utils import files
    fname = _get_normal_filename(filename)
    s = application.settings.GLOBAL
    fname = files.encoding_filename(fname, s.HTMLPAGE_ENCODING, s.FILESYSTEM_ENCODING)
    return return_file(fname)
    
def _get_normal_filename(filename, path_to=None):
    path = path_to or application.settings.UPLOAD.TO_PATH
    fname = os.path.normpath(filename)
    f = os.path.join(path, fname).replace('\\', '/')
    if not f.startswith(path):
        raise Forbidden("You can not visit unsafe files.")
    return f

def save_file(filename, fobj, path_to=None, replace=False):
    from uliweb.utils import files
    assert hasattr(fobj, 'read'), "fobj parameter should be a file-like object"
    fname = _get_normal_filename(filename, path_to)
    s = application.settings.GLOBAL
    fname = files.encoding_filename(fname, s.HTMLPAGE_ENCODING, s.FILESYSTEM_ENCODING)
    filename = files.save_file(fname, fobj, path_to, replace, application.settings.UPLOAD.BUFFER_SIZE)
    return files.encoding_filename(filename, s.FILESYSTEM_ENCODING, s.HTMLPAGE_ENCODING)
        
def get_filename(filename, path_to=None):
    return _get_normal_filename(filename, path_to)

def get_url(filename, path_to=None):
    import urllib
    filename = urllib.quote_plus(filename)
    return _get_normal_filename(filename, application.settings.UPLOAD.URL_SUFFIX)