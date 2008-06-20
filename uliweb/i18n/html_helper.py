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
