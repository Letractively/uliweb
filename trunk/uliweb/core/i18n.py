import gettext as gettext_module
import os.path
import copy
import threading
import sys

sys.path.insert(0, '../..')
from uliweb.utils.lazystr import lazy

_active_locale = threading.local()

_translations = {}
_localedir = None
_domain = 'uliweb'
_default_lang = None

def set_default_language(lang):
    global _default_lang
    if not isinstance(lang, (tuple, list)):
        lang = [lang]
    _default_lang = lang
    
def set_language(lang):
    if not isinstance(lang, (tuple, list)):
        lang = [lang]
    _active_locale.locale = lang
    
def get_language():
    return getattr(_active_locale, 'locale', None)

def find(domain, localedir, languages, all=0):
    # now normalize and expand the languages
    nelangs = []
    languages = languages or []
    for lang in languages:
        for nelang in gettext_module._expand_lang(lang):
            if nelang not in nelangs:
                nelangs.append(nelang)
    # select a language
    if all:
        result = []
    else:
        result = None
    for dir in localedir:
        for lang in nelangs:
            mofile = os.path.join(dir, 'locale', lang, 'LC_MESSAGES', '%s.mo' % domain)
            if os.path.exists(mofile):
                if all:
                    result.append(mofile)
                else:
                    return mofile
    return result


def translation(domain, localedir=None, languages=None,
                class_=None, fallback=False, codeset=None):
    
    if class_ is None:
        class_ = gettext_module.GNUTranslations
        
    localedir = localedir or _localedir
    languages = languages or getattr(_active_locale, 'locale', None) or _default_lang
    
    mofiles = find(domain, localedir, languages, all=1)
    if not mofiles:
        if fallback:
            return gettext_module.NullTranslations()
        raise IOError(gettext_module.ENOENT, 'No translation file found for domain', domain)
    # TBD: do we need to worry about the file pointer getting collected?
    # Avoid opening, reading, and parsing the .mo file after it's been done
    # once.
    result = gettext_module.NullTranslations()
    for mofile in mofiles:
        key = os.path.abspath(mofile)
        t = _translations.get(key)
        if t is None:
            t = _translations.setdefault(key, class_(open(mofile, 'rb')))
        # Copy the translation object to allow setting fallbacks and
        # output charset. All other instance data is shared with the
        # cached object.
        t = copy.copy(t)
        if codeset:
            t.set_output_charset(codeset)
        if result is None:
            result = t
        else:
            result.add_fallback(t)
    return result

def install(domain, localedir=None, unicode=True, codeset='utf-8', names=None):
    global _domain, _localedir
    _domain = domain
    _localedir = localedir
    
    import __builtin__
    __builtin__.__dict__['_'] = unicode and ugettext_lazy or gettext_lazy
    
#    t = translation(domain, localedir, fallback=True, codeset=codeset)
#    t.install(unicode, names)
    
def dgettext(domain, message):
    try:
        t = translation(domain)
    except IOError:
        return message
    return t.gettext(message)

def ldgettext(domain, message):
    try:
        t = translation(domain)
    except IOError:
        return message
    return t.lgettext(message)

def dngettext(domain, msgid1, msgid2, n):
    try:
        t = translation(domain)
    except IOError:
        if n == 1:
            return msgid1
        else:
            return msgid2
    return t.ngettext(msgid1, msgid2, n)

def ldngettext(domain, msgid1, msgid2, n):
    try:
        t = translation(domain)
    except IOError:
        if n == 1:
            return msgid1
        else:
            return msgid2
    return t.lngettext(msgid1, msgid2, n)

def gettext(message):
    return dgettext(_domain, message)

def lgettext(message):
    return ldgettext(_domain, message)

def ngettext(msgid1, msgid2, n):
    return dngettext(_domain, msgid1, msgid2, n)

def lngettext(msgid1, msgid2, n):
    return ldngettext(_domain, msgid1, msgid2, n)

def ugettext(message):
    try:
        t = translation(_domain)
    except IOError:
        return message
    print 'message', t.ugettext(message).encode('gbk')
    return t.ugettext(message)

def ungettext(msgid1, msgid2, n):
    try:
        t = translation(_domain)
    except IOError:
        if n == 1:
            return msgid1
        else:
            return msgid2
    return t.ungettext(msgid1, msgid2, n)

ngettext_lazy = lazy(ngettext)
gettext_lazy = lazy(gettext)
ugettext_lazy = lazy(ugettext)
ungettext_lazy = lazy(ungettext)

if __name__ == '__main__':
    localedir = ['d:/project/svn/uliweb/apps/Post']
    install('uliweb', localedir)
    print 'lang=', get_language()
    print _('Content:') + 'aaaa'
    set_language('zh')
    print 'lang=', get_language()
    print _('Content:').encode('gbk')
    set_language('en')
    print 'lang=', get_language()
    print _('Content:')
    
    