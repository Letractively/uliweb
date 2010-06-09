import os
from uliweb.core.dispatch import bind
from uliweb.core.SimpleFrame import expose
from werkzeug.exceptions import Forbidden

__all__ = ['save_file', 'get_filename', 'get_url']

@bind('startup_installed')
def install(sender):
    url = sender.settings.UPLOAD.URL_SUFFIX.rstrip('/')
    expose('%s/<path:filename>' % url, static=True)(file_serving)
 
def file_serving(filename):
    from uliweb.utils.filedown import filedown
    from uliweb.utils import files
    from uliweb.core.SimpleFrame import local
    from uliweb import application
    
    fname = _get_normal_filename(filename)
    s = application.settings.GLOBAL
    fname = files.encoding_filename(fname, s.HTMLPAGE_ENCODING, s.FILESYSTEM_ENCODING)
    return filedown(local.request.environ, fname)
    
def _get_normal_filename(filename, path_to=None, subfolder=''):
    from uliweb import application
    
    path = path_to or application.settings.UPLOAD.TO_PATH
    if subfolder:
        path = os.path.join(path, subfolder).replace('\\', '/')
    fname = os.path.normpath(filename)
    f = os.path.join(path, fname).replace('\\', '/')
    if not f.startswith(path):
        raise Forbidden("You can not visit unsafe files.")
    return f

def save_file(filename, fobj, path_to=None, replace=False, subfolder=''):
    from uliweb import application
    from uliweb.utils import files
    
    assert hasattr(fobj, 'read'), "fobj parameter should be a file-like object"
    fname = _get_normal_filename(filename, path_to, subfolder)
    s = application.settings.GLOBAL
    fname = files.encoding_filename(fname, s.HTMLPAGE_ENCODING, s.FILESYSTEM_ENCODING)
    
    filename = files.save_file(fname, fobj, replace, application.settings.UPLOAD.BUFFER_SIZE)
    return files.encoding_filename(filename, s.FILESYSTEM_ENCODING, s.HTMLPAGE_ENCODING)

def save_file_field(field, path_to=None, replace=False, subfolder='', filename=None):
    if field:
        filename = filename or field.data.filename
        fname = save_file(filename, field.data.file, path_to, replace, subfolder)
        field.data.filename = fname
        
def save_image_field(field, path_to=None, resize_to=None, replace=False, subfolder='', filename=None):
    if field:
        if resize_to:
            from uliweb.utils.image import resize_image
            field.data.file = resize_image(field.data.file, resize_to)
        filename = filename or field.data.filename
        fname = save_file(filename, field.data.file, path_to, replace, subfolder)
        field.data.filename = fname
        
def get_filename(filename, path_to=None, subfolder=''):
    return _get_normal_filename(filename, path_to, subfolder)

def delete_filename(filename, path_to=None, subfolder=''):
    f = _get_normal_filename(filename, path_to, subfolder)
    if os.path.exists:
        os.remove(f)

def get_url(filename, path_to=None, subfolder=''):
    import urllib
    from uliweb import application
    
    if isinstance(filename, unicode):
        filename = filename.encode('utf-8')
    filename = urllib.quote_plus(filename)
    return _get_normal_filename(filename, application.settings.UPLOAD.URL_SUFFIX, subfolder)
