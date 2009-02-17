def register(app, var, env, theme=None):
    if theme not in ['crispin', 'delicious']:
        theme = 'crispin'
    return {'toplinks':[
        '{{=url_for_static("mootools/mootools.js")}}',
        '{{=url_for_static("mootools/jxlib/jxlib.standalone.js")}}',
        '{{=url_for_static("mootools/jxlib/themes/%s/jxtheme.css")}}' % theme,
        ]}

#class JxLib(js.Snippet):
#    jslink = ['mootools/mootools.js', 'mootools/jxlib/jxlib.standalone.js']
#    _csslink = 'mootools/jxlib/themes/%s/jxtheme.css'
#    
#    def __init__(self, theme='crispin'):
#        if theme not in ['crispin', 'delicious']:
#            theme = 'crispin'
#        self.theme = theme
#        JxLib.csslink = JxLib._csslink % self.theme
#    
#    def image(self, filename):
#        return 'jxlib/theme/%s/images/%s' % (self.theme, filename)
