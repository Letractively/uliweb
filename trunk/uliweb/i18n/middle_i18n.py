import re

from uliweb.i18n import set_language, format_locale

accept_language_re = re.compile(r'''
        ([A-Za-z]{1,8}(?:-[A-Za-z]{1,8})*|\*)   # "en", "en-au", "x-y-z", "*"
        (?:;q=(0(?:\.\d{,3})?|1(?:.0{,3})?))?   # Optional "q=1.00", "q=0.8"
        (?:\s*,\s*|$)                            # Multiple accepts per header.
        ''', re.VERBOSE)

def get_language_from_request(request, config):
    #check session first
    if hasattr(request, 'session'):
        lang = request.session.get('uliweb_language')
        if lang:
            return lang

    lang = request.cookies.get(config.LANGUAGE_COOKIE_NAME)
    if lang:
        return lang

    accept = request.environ['HTTP_ACCEPT_LANGUAGE']
    languages = config.get('LANGUAGES', {})
    for accept_lang, unused in parse_accept_lang_header(accept):
        if accept_lang == '*':
            break

        normalized = format_locale(accept_lang)
        if not normalized:
            continue
        
        if normalized in languages:
            return normalized

    return config.get('LANGUAGE_CODE')

def parse_accept_lang_header(lang_string):
    """
    Parses the lang_string, which is the body of an HTTP Accept-Language
    header, and returns a list of (lang, q-value), ordered by 'q' values.

    Any format errors in lang_string results in an empty list being returned.
    """
    result = []
    pieces = accept_language_re.split(lang_string)
    if pieces[-1]:
        return []
    for i in range(0, len(pieces) - 1, 3):
        first, lang, priority = pieces[i : i + 3]
        if first:
            return []
        priority = priority and float(priority) or 1.0
        result.append((lang, priority))
    result.sort(lambda x, y: -cmp(x[1], y[1]))
    return result

class I18nMiddle(object):
    def __init__(self, application, config):
        self.config = config
        
    def process_request(self, request):
        lang = get_language_from_request(request, self.config)
        if lang:
            set_language(lang)