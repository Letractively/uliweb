from uliweb.core.dispatch import bind

@bind('prepare_template_env')
def prepare_template_env(sender, env):
    from uliweb.utils.textconvert import text2html
    env['text2html'] = text2html
