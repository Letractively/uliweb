def make_select_languages(languages, url):
    if not isinstance(languages, (tuple, list, dict)):
        raise Exception, 'langages should be 2-element tuple or list or a dict'
    
    from uliweb.i18n import get_language, format_locale
    
    if isinstance(languages, (tuple, list)):
        languages = dict(languages)
        
    lang = get_language()
    
    s = []
    s.append('''<script type="text/javascript">
function SetCookie(name, value)
{
var expdate = new Date();
var argv = SetCookie.arguments;
var argc = SetCookie.arguments.length;
var expires = (argc > 2) ? argv[2] : null;
var path = (argc > 3) ? argv[3] : null;
var domain = (argc > 4) ? argv[4] : null;
var secure = (argc > 5) ? argv[5] : false;
if(expires!=null) expdate.setTime(expdate.getTime() + ( expires * 1000 ));
document.cookie = name + "=" + escape (value) +((expires == null) ? "" : ("; expires="+ expdate.toGMTString()))
+((path == null) ? "" : ("; path=" + path)) +((domain == null) ? "" : ("; domain=" + domain))
+((secure == true) ? "; secure" : "");
window.location.href = "%s";
}
</script>''' % url)
    s.append('''<form class="lang_dropdown" action="javascript:SetCookie('uliweb_language',this.document.changelang.lang.value)" name="changelang" method="post">
<label for="lang">Change Language:</label>
<select onchange="this.form.submit()" id="lang" name="lang">''')
    for k, v in sorted(languages.items()):
        k = format_locale(k)
        if k == lang:
            select = 'selected="selected" '
        else:
            select = ''
        s.append('<option %svalue="%s">%s</option>' % (select, k, v))
    s.append('''</select>
</form>''')
    return ''.join(s)
