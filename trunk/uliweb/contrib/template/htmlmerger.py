from uliweb.core.template import template
import re

r_links = re.compile('<link\s.*?\s+href\s*=\s*"?(.*?)["\s>]|<script\s.*?\s+src\s*=\s*"?(.*?)["\s>]', re.I)
r_head = re.compile('(?i)<head>(.*?)</head>', re.DOTALL)

def merge(text, collection, vars, env):
    b = r_head.search(text)
    if b:
        head = b.group()
        start, end = b.span()
        links = []
        for v in r_links.findall(head):
            link = v[0] or v[1]
            links.append(link)
        result = assemble(_clean_collection(collection, links, vars, env))
        if result['toplinks'] or result['bottomlinks'] or result['codes']:
            top = result['toplinks'] or ''
            bottom = (result['bottomlinks'] or '') + (result['codes'] or '')
            return (text[:start] + '<head>' + top + head[6:-7] + 
                bottom + '</head>' + text[end:])
    else:
        result = assemble(_clean_collection(collection, [], vars, env))
        if result['toplinks'] or result['bottomlinks'] or result['codes']:
            top = result['toplinks'] or ''
            bottom = (result['bottomlinks'] or '') + (result['codes'] or '')
            return top + bottom + text
        
    return text

def _clean_collection(collection, existlinks, vars, env):
    """
    >>> collection = {
    ...     'form':{
    ...         'toplinks':['js/mootools.js'],
    ...         'bottomlinks':['css/form.css'],
    ...         'codes':['code', 'code2'],
    ...     },
    ...     'xxxx':{
    ...         'toplinks':['js/mootools.js'],
    ...         'bottomlinks':['css/form.css'],
    ...         'codes':['code2', '{{=name}}'],
    ...     },
    ... }
    >>> vars = {'name':'limodou'}
    >>> sorted(_clean_collection(collection, [], vars, {}).items())
    [('bottomlinks', ['css/form.css']), ('codes', ['code2', 'limodou', 'code']), ('toplinks', ['js/mootools.js'])]
    """
    r = {'toplinks':[], 'bottomlinks':[], 'codes':[]}
    links = {}
    codes = {}
    for i in collection.values():
        #process links, link could be (order, link) or link
        for _type in ['toplinks', 'bottomlinks']:
            t = i.get(_type, [])
            if not isinstance(t, (tuple, list)):
                t = [t]
            for link in t:
                #link will also be template string
                link = template(link, vars, env)
                if not link in r[_type] and not link in existlinks:
                    r[_type].append(link)
        #process codes, code will not have order
        t = i.get('codes', [])
        if not isinstance(t, (tuple, list)):
            t = [t]
        for code in t:
            #code will also be template string
            code = template(code, vars, env)
            if not code in r['codes']:
                r['codes'].append(code)
    return r

def assemble(links):
    toplinks = []
    bottomlinks = []
    codes = []
    for _type, result in [('toplinks', toplinks), ('bottomlinks', bottomlinks)]:
        for link in links[_type]:
            if link.endswith('.js'):
                result.append('<script type="text/javascript" src="%s"></script>' % link)
            elif link.endswith('.css'):
                result.append('<link rel="stylesheet" type="text/css" href="%s"/>' % link)
            else:
                raise Exception('The link %s should be ended with ".css" or ".js"' % link)
    for code in links['codes']:
        codes.append(code)
    return {'toplinks':'\n'.join(toplinks), 'bottomlinks':'\n'.join(bottomlinks),
        'codes':'\n'.join(codes)}
        
if __name__ == '__main__':
    collection = {
        'form':{
            'toplinks':['js/mootools.js', 'js/jxlib.js'],
            'bottomlinks':['css/form.css'],
            'codes':['code', 'code2'],
        },
        'xxxx':{
            'toplinks':['js/mootools.js'],
            'bottomlinks':['css/form.css'],
            'codes':['code2', '{{=name}}'],
        },
    }
    vars = {'name':'limodou'}
#    print sorted(_clean_collection(collection, [], vars, {}).items())
    a = """<html><head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<title>title</title>
<style type="text/css">
.error{color:#FF0000;font-size:12px}
</style>
<script type="text/javascript" src="/ui/scripts/global.js"></script>
<script language="javascript" src="js/mootools.js"></script>
<script LANGUAGE="JavaScript" src="/js/g_spjs.js"></script>
<link rel="stylesheet" type="text/css" href="/static/css/haml-forms.css">
<link rel="stylesheet" type="text/css" href="/static/css/my_layout.css"/>
<!--[if lte IE 7]>
<link rel="stylesheet" type="text/css" href="/static/css/patches/patch_my_layout.css">
<![endif]-->
<script language="javascript">
<!--
var allkey="";
//-->
</script>
</head>
<body>
"""
    print merge(a, collection, vars, {})
    
    