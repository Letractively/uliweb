from uliweb.core.plugin import plugin

@plugin('before_render_template')
def before_render_template(sender, env, out):
    from uliweb.core import js
    
    htmlbuf = js.HtmlBuf(write=out.noescape, static_suffix=sender.settings.get('STATIC_SUFFIX', '/static/'))
    env['htmlbuf'] = htmlbuf
    
@plugin('after_render_template')
def after_render_template(sender, text, vars, env):
    import re
    r_links = re.compile('<link\s.*?\shref\s*=\s*"?(.*?)["\s>]|<script\s.*?\ssrc\s*=\s*"?(.*?)["\s>]', re.I)
    if 'htmlbuf' in env:
        htmlbuf = env['htmlbuf']
        if htmlbuf.modified:
            b = re.search('(?i)</head>', text)
            if b:
                pos = b.start()
                #find links
                links = [x or y for x, y in r_links.findall(text[:pos])]
                htmlbuf.remove_links(links)
                t = htmlbuf.render()
                if t:
                    return ''.join([text[:pos], t, text[pos:]])
            else:
                return t+text
    return text
