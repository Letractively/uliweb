def make_select_languages(action, languages):
    
    <form action="/i18n/setlang/" method="post">
    <input name="next" type="hidden" value="/next/page/" />
    <select name="language">
    {% for lang in LANGUAGES %}
    <option value="{{ lang.0 }}">{{ lang.1 }}</option>
    {% endfor %}
    </select>
    <input type="submit" value="Go" />
    </form>


#this function is referenced from Django
def set_language():
    """
    Redirect to a given url while setting the chosen language in the
    session or cookie. The url and the language code need to be
    specified in the request parameters.

    Since this view changes how the user will see the rest of the site, it must
    only be accessed as a POST request. If called as a GET request, it will
    redirect to the page in the request (the 'next' parameter) without changing
    any state.
    """
    next = request.params.get('next')
    if not next:
        next = request.environ.get('HTTP_REFERER')
    if not next:
        next = '/'
    if request.method == 'POST':
        lang_code = request.POST.get('language', None)
        if lang_code:
            response.set_cookie(config.LANGUAGE_COOKIE_NAME, lang_code)
    redirect(next)
