from uliweb.core.dispatch import bind

##################################################
# insert rst2html function to template environment
##################################################
@bind('prepare_template_env')
def prepare_template_env(sender, env):
    from uliweb.utils.rst import to_html
    from uliweb.core.SimpleFrame import errorpage
    def rst2html(filename):
        f = env.get_file(filename)
        if f:
            return to_html(file(f).read())
        else:
            errorpage("Can't find the file %s" % filename)
    env['rst2html'] = rst2html
    
