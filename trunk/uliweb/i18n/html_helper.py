def make_select_languages(languages):
    if not isinstance(languages, (tuple, list, dict)):
        raise Exception, 'langages should be 2-element tuple or list or a dict'
    
    from uliweb.i18n import get_language, format_locale
    
    if isinstance(languages, (tuple, list)):
        languages = dict(languages)
        
    lang = get_language()
    
    s = []
    s.append('''<script type="text/javascript">
function SetCookie( name, value, expires, path, domain, secure ) 
{
var today = new Date();
today.setTime( today.getTime() );
path='/';
if ( expires )
{
expires = expires * 1000 * 60 * 60 * 24;
}
var expires_date = new Date( today.getTime() + (expires) );

document.cookie = name + "=" +escape( value ) +
( ( expires ) ? ";expires=" + expires_date.toGMTString() : "" ) + 
( ( path ) ? ";path=" + path : "" ) + 
( ( domain ) ? ";domain=" + domain : "" ) +
( ( secure ) ? ";secure" : "" );
window.location.reload();
}
</script>''')
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
