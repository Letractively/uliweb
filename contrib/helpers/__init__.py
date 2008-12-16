def before_render_template(env, writer, static_suffix, **widgets):
    from uliweb.core import js
    from uliweb.core.SimpleFrame import url_for
    import htmlwidgets

    htmlbuf = js.HtmlBuf(write=writer, static_suffix=static_suffix)
    env['htmlbuf'] = htmlbuf
    for k, v in widgets.items():
        env[k] = v

def after_render_template(text, vars, env):
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
