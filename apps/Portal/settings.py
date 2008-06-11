from utils.plugin import plugin

@plugin('prepare_template_env')
def prepare_template_env(env):
    from utils.rst import to_html
    def rst2html(filename):
        return to_html(file(env.get_file(filename)).read())
    env['rst2html'] = rst2html
    